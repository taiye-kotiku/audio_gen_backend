# main.py
import os
import aiohttp
import asyncio
import subprocess
import uuid
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from auth import authenticate_user, create_access_token, get_admin_user, load_users, save_users
import bcrypt
import json
import time

load_dotenv()

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CONFIG_FILE = "config.json"


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"ELEVENLABS_API_KEY": ""}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

# Load config on startup
config = load_config()

app = FastAPI()

origins = [
    "https://steady-unicorn-1c78fe.netlify.app",  # your frontend domain
    "http://localhost:3000",                        # for local dev
]

# Allow React frontend to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")

# Global dictionary to track progress
progress_dict = {}


# Concurrency controls
global_semaphore = asyncio.Semaphore(15)  # total across all dashboards

# ------------------ AUTH ------------------
@app.post("/token")
async def login(email: str = Form(...), password: str = Form(...)):
    user = authenticate_user(email, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user["email"]})

    # mark user active
    mark_session_active(token, user["email"])

    return {
        "access_token": token,
        "token_type": "bearer",
        "is_admin": user["is_admin"],
        "voice_id": user.get("voice_id", "6sFKzaJr574YWVu4UuJF")  # 👈 return last voice ID
    }


# ------------------ HISTORY ------------------
HISTORY_FILE = "history.json"

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def add_history_entry(email: str, entry: dict):
    history = load_history()
    if email not in history:
        history[email] = []
    history[email].append(entry)
    save_history(history)

# Track active sessions (by token instead of just email)
active_sessions = {}

def mark_session_active(token: str, email: str):
    active_sessions[token] = {"email": email, "last_seen": time.time()}

def get_active_sessions(minutes: int = 5):
    now = time.time()
    cutoff = now - (minutes * 60)
    
    # Clean up and return only genuinely active sessions
    active = {}
    tokens_to_delete = []
    
    for token, session_data in active_sessions.items():
        if session_data["last_seen"] >= cutoff:
            active[token] = session_data
        else:
            tokens_to_delete.append(token)
            
    # Clean up inactive sessions from the global dictionary
    for token in tokens_to_delete:
        active_sessions.pop(token, None)
            
    return active


# ------------------ ADMIN ------------------
@app.get("/admin/list-users/")
async def list_users(admin=Depends(get_admin_user)):
    users = load_users()
    return [{"email": u["email"], "is_admin": u["is_admin"]} for u in users]

@app.post("/admin/add-user/")
async def add_user(
    email: str = Form(...),
    password: str = Form(...),
    is_admin: bool = Form(False),
    admin=Depends(get_admin_user)
):
    users = load_users()
    if any(u["email"] == email for u in users):
        raise HTTPException(status_code=400, detail="User already exists")
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    users.append({"email": email, "password_hash": password_hash, "is_admin": is_admin})
    save_users(users)
    return JSONResponse({"message": f"User {email} added successfully"})

@app.post("/admin/remove-user/")
async def remove_user(email: str = Form(...), admin=Depends(get_admin_user)):
    users = load_users()
    users = [u for u in users if u["email"] != email]
    save_users(users)
    return JSONResponse({"message": f"User {email} removed successfully"})

@app.post("/admin/set-api-key/")
async def set_api_key(api_key: str = Form(...), admin=Depends(get_admin_user)):
    config["ELEVENLABS_API_KEY"] = api_key
    save_config(config)
    return {"message": "API key updated successfully"}


@app.get("/admin/active-users/")
async def active_users_endpoint(admin=Depends(get_admin_user)):
    sessions = get_active_sessions()
    
    # Count unique emails from remaining active sessions
    active_emails = set()
    for session_data in sessions.values():
        active_emails.add(session_data["email"])
    
    unique_user_count = len(active_emails)

    print(f"[DEBUG] Active users: {unique_user_count}") 
    
    return {
        "count": unique_user_count,
        "sessions": [{"token": t, "email": s["email"]} for t, s in sessions.items()]
    }

# ------------------ HELPERS ------------------
def split_text(text: str, max_length: int = 4500):
    paragraphs = text.split("\n\n")
    chunks, current = [], ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_length:
            current += para + "\n\n"
        else:
            if current.strip():
                chunks.append(current.strip())
            if len(para) > max_length:
                sentences = para.split(". ")
                temp = ""
                for s in sentences:
                    if len(temp) + len(s) + 2 <= max_length:
                        temp += s + ". "
                    else:
                        chunks.append(temp.strip())
                        temp = s + ". "
                if temp.strip():
                    chunks.append(temp.strip())
            else:
                chunks.append(para.strip())
            current = ""
    if current.strip():
        chunks.append(current.strip())
    return chunks

# ------------------ TTS ------------------
async def tts_request(session, text, chunk_id, custom_id, voice_id, retries: int = 3):
    if not config.get("ELEVENLABS_API_KEY"):
        raise HTTPException(status_code=500, detail="ElevenLabs API key not configured")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "xi-api-key": config["ELEVENLABS_API_KEY"],
        "Content-Type": "application/json",
    }
    payload = {"text": text, "model_id": "eleven_multilingual_v2"}

    part_filename = f"{custom_id}_part{chunk_id}_{uuid.uuid4().hex}.mp3"
    output_file = os.path.join(OUTPUT_DIR, part_filename)

    for attempt in range(1, retries + 1):
        try:
            async with global_semaphore:  # 👈 throttle globally
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        err = await response.text()
                        print(f"ElevenLabs error (attempt {attempt}): {err}")
                        if attempt == retries:
                            raise HTTPException(status_code=500, detail=f"ElevenLabs error: {err}")
                        await asyncio.sleep(2 * attempt)
                        continue

                    data = await response.read()
                    with open(output_file, "wb") as f:
                        f.write(data)

            if custom_id in progress_dict:
                progress_dict[custom_id]["done"] += 1

            return (chunk_id, output_file)
        except Exception as e:
            print(f"Error in tts_request attempt {attempt}: {e}")
            if attempt == retries:
                raise HTTPException(status_code=500, detail=f"Chunk {chunk_id} failed: {str(e)}")
            await asyncio.sleep(2 * attempt)

def merge_audios_ffmpeg(files, output_file, custom_id):
    """
    Merge list of mp3 files (in order) into output_file using ffmpeg concat.
    Uses a per-job file list to avoid collisions.
    """
    # create a unique file list name so concurrent jobs don't clash
    list_filename = f"file_list_{custom_id}_{uuid.uuid4().hex}.txt"
    file_list_path = os.path.join(OUTPUT_DIR, list_filename)

    # write absolute paths in the list
    with open(file_list_path, "w", encoding="utf-8") as f:
        for p in files:
            f.write(f"file '{os.path.abspath(p)}'\n")

    try:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", file_list_path, "-c", "copy", output_file],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        # capture ffmpeg output for easier debugging
        print("ffmpeg error:", e.stderr)
        raise HTTPException(status_code=500, detail=f"ffmpeg failed: {e.stderr}")
    finally:
        # cleanup file list only (keep parts by default)
        try:
            os.remove(file_list_path)
        except Exception:
            pass

# ------------------ ENDPOINTS ------------------
@app.post("/generate-audio/")
async def generate_audio(
    file: UploadFile = File(...),
    custom_id: str = Form("output"),
    voice_id: str = Form("6sFKzaJr574YWVu4UuJF"),
    email: str = Form(None)  # 👈 frontend passes logged-in user email
):
    # ---------------- save last-used voice ID ----------------
    if email:
        users = load_users()
        for u in users:
            if u["email"] == email:
                u["voice_id"] = voice_id  # update or add field
        save_users(users)

    # ---------------- continue as before ----------------
    text = (await file.read()).decode("utf-8").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text file is empty")

    chunks = split_text(text)
    total_chunks = len(chunks)
    progress_dict[custom_id] = {"done": 0, "total": total_chunks}

    local_semaphore = asyncio.Semaphore(5)  # 👈 per-dashboard/job

    async with aiohttp.ClientSession() as session:
        async def process_chunk(i, chunk):
            async with local_semaphore:  # 👈 throttle per job
                return await tts_request(session, chunk, i + 1, custom_id, voice_id)

        tasks = [process_chunk(i, chunk) for i, chunk in enumerate(chunks)]
        results = await asyncio.gather(*tasks)

    results_sorted = sorted(results, key=lambda t: t[0])
    audio_files = [p for (_, p) in results_sorted]

    final_file = os.path.join(OUTPUT_DIR, f"{custom_id}.mp3")
    merge_audios_ffmpeg(audio_files, final_file, custom_id)

    progress_dict[custom_id]["done"] = progress_dict[custom_id]["total"]
    if email:
        entry = {
            "custom_id": custom_id,
            "voice_id": voice_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "file_path": f"/outputs/{custom_id}.mp3",
            "text_preview": text[:200]  # store first 200 chars
        }
        add_history_entry(email, entry)

    return {"message": "Success", "file_path": final_file}

@app.get("/progress/{custom_id}")
def get_progress(custom_id: str):
    if custom_id not in progress_dict:
        raise HTTPException(status_code=404, detail="No progress found")
    data = progress_dict[custom_id]
    percent = int((data["done"] / data["total"]) * 100) if data["total"] else 100
    return {"done": data["done"], "total": data["total"], "percent": percent}

@app.post("/heartbeat/")
async def heartbeat(token: str = Form(...), email: str = Form(...)):
    mark_session_active(token, email)
    print(f"HEARTBEAT RECEIVED: Token={token[:8]}..., Email={email}, Last Seen={active_sessions[token]['last_seen']}")
    return {"status": "ok"}


# ------------------ HISTORY ENDPOINT ------------------
@app.get("/user/history/")
async def get_user_history(email: str):
    """Get history for a specific user"""
    history = load_history()
    user_history = history.get(email, [])
    
    # Return in reverse chronological order (newest first)
    user_history.reverse()
    return user_history
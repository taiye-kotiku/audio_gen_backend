import os
import aiohttp
import asyncio
import subprocess
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from auth import authenticate_user, create_access_token, get_admin_user, load_users, save_users
import bcrypt

load_dotenv()


ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "sk_a31b9940b467d14ec9114c01e7e73a3c75906e25cd19ba35")
VOICE_ID = "6sFKzaJr574YWVu4UuJF"

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = FastAPI()

# Allow React frontend to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")
# Global dictionary to track progress
progress_dict = {}



@app.post("/token")
async def login(email: str = Form(...), password: str = Form(...)):
    user = authenticate_user(email, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user["email"]})
    return {"access_token": token, "token_type": "bearer", "is_admin": user["is_admin"]}

@app.get("/admin/list-users/")
async def list_users(admin=Depends(get_admin_user)):
    users = load_users()
    return [{"email": u["email"], "is_admin": u["is_admin"]} for u in users]

@app.post("/admin/add-user/")
async def add_user(email: str = Form(...), password: str = Form(...), is_admin: bool = Form(False), admin=Depends(get_admin_user)):
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

# TTS request with retry and progress update
async def tts_request(session, text, chunk_id, custom_id, retries: int = 3):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "Accept": "audio/mpeg",
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {"text": text, "model_id": "eleven_multilingual_v2"}
    output_file = os.path.join(OUTPUT_DIR, f"{custom_id}_part{chunk_id}.mp3")

    for attempt in range(1, retries + 1):
        try:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    err = await response.text()
                    print(f"❌ ElevenLabs error: {err}, retrying...")
                    if attempt == retries:
                        raise HTTPException(status_code=500, detail=f"ElevenLabs error: {err}")
                    await asyncio.sleep(3 * attempt)
                    continue
                data = await response.read()
                with open(output_file, "wb") as f:
                    f.write(data)

            # Update progress
            progress_dict[custom_id]["done"] += 1
            return output_file
        except Exception as e:
            if attempt == retries:
                raise HTTPException(status_code=500, detail=f"Chunk {chunk_id} failed: {str(e)}")
            await asyncio.sleep(2 * attempt)

# Merge function
def merge_audios_ffmpeg(files, output_file):
    file_list_path = os.path.join(OUTPUT_DIR, "file_list.txt")
    with open(file_list_path, "w", encoding="utf-8") as f:
        for file in files:
            f.write(f"file '{os.path.abspath(file)}'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", file_list_path, "-c", "copy", output_file],
        check=True,
        capture_output=True,
        text=True
    )

# Generate audio endpoint
@app.post("/generate-audio/")
async def generate_audio(file: UploadFile = File(...), custom_id: str = Form("output")):
    text = (await file.read()).decode("utf-8").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text file is empty")

    chunks = split_text(text)
    total_chunks = len(chunks)
    progress_dict[custom_id] = {"done": 0, "total": total_chunks}

    async with aiohttp.ClientSession() as session:
        tasks = [tts_request(session, chunk, i + 1, custom_id) for i, chunk in enumerate(chunks)]
        audio_files = await asyncio.gather(*tasks)

    final_file = os.path.join(OUTPUT_DIR, f"{custom_id}.mp3")
    merge_audios_ffmpeg(audio_files, final_file)

    # Mark progress as complete
    progress_dict[custom_id]["done"] = progress_dict[custom_id]["total"]

    return {"message": "Success", "file_path": final_file}

# Progress endpoint
@app.get("/progress/{custom_id}")
def get_progress(custom_id: str):
    if custom_id not in progress_dict:
        raise HTTPException(status_code=404, detail="No progress found")
    data = progress_dict[custom_id]
    percent = int((data["done"] / data["total"]) * 100)
    return {"done": data["done"], "total": data["total"], "percent": percent}


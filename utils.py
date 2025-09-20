from pydub import AudioSegment
import re
import json
import os

CONFIG_FILE = "config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"ELEVENLABS_API_KEY": ""}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


# Split text into safe chunks (<= 5000 chars, prefer paragraphs)
def split_text(text, max_length=4900):
    paragraphs = text.split("\n\n")
    chunks, current = [], ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_length:
            current += para + "\n\n"
        else:
            if current:
                chunks.append(current.strip())
            if len(para) > max_length:
                # fallback: split by sentence if paragraph too long
                sentences = re.split(r'(?<=[.!?]) +', para)
                temp = ""
                for s in sentences:
                    if len(temp) + len(s) + 1 <= max_length:
                        temp += s + " "
                    else:
                        chunks.append(temp.strip())
                        temp = s + " "
                if temp:
                    chunks.append(temp.strip())
                current = ""
            else:
                current = para + "\n\n"

    if current.strip():
        chunks.append(current.strip())
    return chunks


# Merge MP3 files into one
def merge_audios(audio_files, output_file):
    combined = AudioSegment.empty()
    for f in audio_files:
        combined += AudioSegment.from_file(f, format="mp3")
    combined.export(output_file, format="mp3")

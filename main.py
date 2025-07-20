import os
import re
import subprocess

import whisper

# === Configurations ===
VIDEO_FILE = "video.avi"
AUDIO_FILE = "audio.wav"
SEGMENTS_FILE = "segments.txt"
OUTPUT_DIR = "clips"
FINAL_OUTPUT = "output.mp4"
WORD = "нет"


# === Functions ===
def extract_audio():
    print("[1] Extracting audio...")
    cmd = [
        "ffmpeg", "-y", "-i", VIDEO_FILE,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1", AUDIO_FILE
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("✅ Audio saved as", AUDIO_FILE)


# Format time to HH:MM:SS.MS
def format_time(seconds):
    total_ms = int(seconds * 100)
    ms = total_ms % 100
    s = int(seconds)
    hours = s // 3600
    minutes = (s % 3600) // 60
    seconds = s % 60
    return f"{hours:02}:{minutes:02}:{seconds:02}.{ms:02}"


# Transcribe audio and detect segments with the word
# noinspection PyArgumentList
def transcribe():
    print(f"[2] Transcribing and detecting segments with word: {WORD}")
    model = whisper.load_model("base")
    result = model.transcribe(AUDIO_FILE, language="ru")
    found = []

    word_regex = re.compile(rf"\b{re.escape(WORD)}\b", re.IGNORECASE)

    for segment in result["segments"]:
        if word_regex.search(segment["text"]):
            start = max(segment["start"] - 0.1, 0)  # Beginning of the segment
            end = segment["end"] + 0.0  # End of the segment
            found.append((start, end))
            print(f"🎯 Found {WORD}: {format_time(start)} --> {format_time(end)}")

    with open(SEGMENTS_FILE, "w", encoding="utf-8") as f:
        for start, end in found:
            f.write(f"{format_time(start)} {format_time(end)}\n")

    print(f"✅ {len(found)} segments saved to {SEGMENTS_FILE}")
    return found


# Cut clips
def cut_clips(segments):
    print("[3] Cutting clips...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for idx, (start, end) in enumerate(segments, 1):
        output = os.path.join(OUTPUT_DIR, f"clip{idx:03}.mp4")
        cmd = [
            "ffmpeg", "-y", "-i", VIDEO_FILE,
            "-ss", format_time(start), "-to", format_time(end),
            "-c:v", "libx264", "-crf", "23", "-preset", "fast",
            "-c:a", "aac", "-b:a", "128k",
            output
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✂️ Clip saved: {output}")


# Concatenate clips
def concatenate_clips():
    print("[4] Concatenating clips...")

    txt_path = "files.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        for file in sorted(os.listdir(OUTPUT_DIR)):
            if file.endswith(".mp4"):
                f.write(f"file '{os.path.join(OUTPUT_DIR, file).replace(os.sep, '/')}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", txt_path,
        "-c:v", "libx264", "-crf", "23", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k", "-ac", "2",
        FINAL_OUTPUT
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print("❌ Error during concatenation:")
        print(result.stderr.decode())
    else:
        print(f"✅ Final video created: {FINAL_OUTPUT}")


# === Main script ===
if __name__ == "__main__":
    if not os.path.exists(VIDEO_FILE):
        print(f"❌ File not found: {VIDEO_FILE}")
        exit(1)

    extract_audio()
    segments = transcribe()

    if segments:
        cut_clips(segments)
        concatenate_clips()
    else:
        print(f"⚠️ No segments found with {WORD}.")

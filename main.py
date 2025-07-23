import os
import re
import subprocess
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

import whisper

# === Configurations ===
VIDEO_FILE = "yesman.mkv"
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


def format_time(seconds):
    total_ms = int(seconds * 100)
    ms = total_ms % 100
    s = int(seconds)
    hours = s // 3600
    minutes = (s % 3600) // 60
    seconds = s % 60
    return f"{hours:02}:{minutes:02}:{seconds:02}.{ms:02}"


def transcribe():
    print(f"[2] Transcribing and detecting segments with word {WORD}")
    model = whisper.load_model("base")
    result = model.transcribe(AUDIO_FILE, language="ru")
    found = []

    word_regex = re.compile(rf"\b{re.escape(WORD)}\b", re.IGNORECASE)

    for segment in result["segments"]:
        if word_regex.search(segment["text"]):
            start = max(segment["start"] - 0.0, 0)  # Adjust start time
            end = segment["end"] + 0.0  # Adjust end time
            found.append((start, end))
            print(f"🎯 Found {WORD}: {format_time(start)} --> {format_time(end)}")

    with open(SEGMENTS_FILE, "w", encoding="utf-8") as f:
        for start, end in found:
            f.write(f"{format_time(start)} {format_time(end)}\n")

    print(f"✅ {len(found)} segments saved to {SEGMENTS_FILE}")
    return found


def cut_clips_with_counter(segments):
    print("[3] Cutting clips with counter overlay...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for idx, (start, end) in enumerate(segments, 1):
        raw_clip = os.path.join(OUTPUT_DIR, f"raw_clip{idx:03}.mp4")
        final_clip = os.path.join(OUTPUT_DIR, f"clip{idx:03}.mp4")

        # Step 1: Cut clip
        cmd_cut = [
            "ffmpeg", "-y", "-i", VIDEO_FILE,
            "-ss", format_time(start), "-to", format_time(end),
            "-c:v", "libx264", "-crf", "23", "-preset", "fast",
            "-c:a", "aac", "-b:a", "128k",
            raw_clip
        ]
        subprocess.run(cmd_cut, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        FONT_PATH = "C\\:/Windows/Fonts/arial.ttf"  # Replace with your font path

        cmd_overlay = [
            "ffmpeg", "-y", "-i", raw_clip,
            "-vf",
            f"drawtext=fontfile='{FONT_PATH}':text='Count\\: {idx}':fontcolor=white:fontsize=44:x=10:y=10:box=1:boxcolor=black@0.5",
            "-c:v", "libx264", "-crf", "23", "-preset", "fast",
            "-c:a", "aac", "-b:a", "128k",
            final_clip
        ]
        subprocess.run(cmd_overlay, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        os.remove(raw_clip)
        print(f"✂️ Clip with counter saved as {final_clip}")


def concatenate_clips():
    print("[4] Concatenating clips...")

    txt_path = "files.txt"
    clip_paths = []

    for file in sorted(os.listdir(OUTPUT_DIR)):
        if file.endswith(".mp4"):
            full_path = os.path.join(OUTPUT_DIR, file).replace(os.sep, "/")
            if os.path.exists(full_path):
                clip_paths.append(full_path)

    if not clip_paths:
        print("❌ No clips found to concatenate.")
        return

    with open(txt_path, "w", encoding="utf-8") as f:
        for path in clip_paths:
            f.write(f"file '{path}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", txt_path,
        "-c:v", "libx264", "-crf", "23", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k", "-ac", "2",
        FINAL_OUTPUT
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    os.remove(txt_path)

    if result.returncode != 0:
        print("❌ Error during concatenation:")
        print(result.stderr.decode())
    else:
        print(f"✅ Final video created as {FINAL_OUTPUT}")


# === Main script ===
if __name__ == "__main__":
    if not os.path.exists(VIDEO_FILE):
        print(f"❌ File not found: {VIDEO_FILE}")
        exit(1)

    extract_audio()
    segments = transcribe()

    if segments:
        cut_clips_with_counter(segments)
        concatenate_clips()
    else:
        print(f"⚠️ No segments found with word {WORD}.")

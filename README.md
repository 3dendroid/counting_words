# 🎬 Video Word Extractor

This script detects and extracts video segments where **any specific word** is spoken, using OpenAI Whisper for transcription and ffmpeg for video processing.

## 📌 Description

This project allows you to:

1. Extract audio from a video file.
2. Transcribe speech using the Whisper model.
3. Find time segments where a **target word** (e.g., "yes", "да", "hello", etc.) is spoken.
4. Cut video clips around those moments.
5. Concatenate the clips into a final highlight reel.

✅ Supports any word in any language (if supported by Whisper).

## 🚀 Installation

```bash
git clone https://github.com/your-repo/video-word-extractor.git
cd video-word-extractor
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
```

## 📦 Dependencies

- [ffmpeg](https://ffmpeg.org/) (must be installed and added to your system `PATH`)
- [openai/whisper](https://github.com/openai/whisper)
- `torch`, `subprocess`, `os`, `re`

## 🛠 Usage

1. Place your video file in the root folder and update its name in the script (`VIDEO_FILE`).
2. Set the target word in the `WORD` variable.
3. Run the script:

```bash
python main.py
```

4. Output:
   - Individual clips saved in the `clips/` folder.
   - Final merged video saved as `output.mp4`.

## ✏️ Configuration

In `main.py`, you can customize:

```python
WORD = "yes"              # ← The word to search for in the transcript
VIDEO_FILE = "video.avi"  # ← Your video filename
```

You can change `"yes"` to any word or phrase you want.

## 📄 License

MIT License
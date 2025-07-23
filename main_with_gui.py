import os
import re
import subprocess
import warnings

import whisper
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout,
    QFileDialog, QComboBox, QLineEdit, QProgressBar
)

warnings.filterwarnings("ignore", category=UserWarning)


class Worker(QThread):
    progress = Signal(int)
    finished = Signal(bool)

    def __init__(self, video_file, language, word, output_path="output.mp4"):
        super().__init__()
        self.video_file = video_file
        self.language = language
        self.word = word
        self.output_path = output_path
        self._is_stopped = False

    def stop(self):
        self._is_stopped = True

    def run(self):
        audio_file = "audio.wav"
        output_dir = "clips"
        final_output = self.output_path

        def format_time(seconds):
            total_ms = int(seconds * 100)
            ms = total_ms % 100
            s = int(seconds)
            hours = s // 3600
            minutes = (s % 3600) // 60
            seconds = s % 60
            return f"{hours:02}:{minutes:02}:{seconds:02}.{ms:02}"

        try:
            self.progress.emit(10)
            subprocess.run([
                "ffmpeg", "-y", "-i", self.video_file,
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", audio_file
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if self._is_stopped: return

            self.progress.emit(25)
            model = whisper.load_model("base")
            result = model.transcribe(audio_file, language=self.language)
            found = []

            word_regex = re.compile(rf"\b{re.escape(self.word)}\b", re.IGNORECASE)
            for segment in result["segments"]:
                if word_regex.search(segment["text"]):
                    start = max(segment["start"] - 0.0, 0)
                    end = segment["end"] + 0.0
                    found.append((start, end))
            if self._is_stopped: return

            # Check if any segments were found
            if not found:
                self.finished.emit(False)
                return

            self.progress.emit(50)
            os.makedirs(output_dir, exist_ok=True)
            for idx, (start, end) in enumerate(found, 1):
                raw_clip = os.path.join(output_dir, f"raw_clip{idx:03}.mp4")
                final_clip = os.path.join(output_dir, f"clip{idx:03}.mp4")

                subprocess.run([
                    "ffmpeg", "-y", "-i", self.video_file,
                    "-ss", format_time(start), "-to", format_time(end),
                    "-c:v", "libx264", "-crf", "23", "-preset", "fast",
                    "-c:a", "aac", "-b:a", "128k", raw_clip
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if self._is_stopped: return

                font_path = "C\\:/Windows/Fonts/arial.ttf"
                subprocess.run([
                    "ffmpeg", "-y", "-i", raw_clip,
                    "-vf", f"drawtext=fontfile='{font_path}':text='Count\\: {idx}':"
                           f"fontcolor=white:fontsize=44:x=10:y=10:box=1:boxcolor=black@0.5",
                    "-c:v", "libx264", "-crf", "23", "-preset", "fast",
                    "-c:a", "aac", "-b:a", "128k", final_clip
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                os.remove(raw_clip)

            if self._is_stopped: return

            self.progress.emit(80)
            with open("files.txt", "w", encoding="utf-8") as f:
                for file in sorted(os.listdir(output_dir)):
                    if file.endswith(".mp4"):
                        f.write(f"file '{os.path.join(output_dir, file).replace(os.sep, '/')}'\n")

            subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", "files.txt",
                "-c:v", "libx264", "-crf", "23", "-preset", "fast",
                "-c:a", "aac", "-b:a", "128k", "-ac", "2", final_output
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            self.progress.emit(100)
            self.finished.emit(True)

        except Exception:
            self.finished.emit(False)

        finally:
            # Delete temporary files
            if os.path.exists(audio_file):
                os.remove(audio_file)
            if os.path.exists("files.txt"):
                os.remove("files.txt")
            if os.path.exists(output_dir):
                for f in os.listdir(output_dir):
                    os.remove(os.path.join(output_dir, f))
                os.rmdir(output_dir)


class WordClipApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Word Clip Extractor")
        self.setWindowIcon(QIcon("logo.ico"))
        self.video_file = ""
        self.output_path = ""

        self.label_file = QLabel("Video file: not selected", alignment=Qt.AlignLeft)
        self.button_browse = QPushButton("Choose video file")

        self.button_output = QPushButton("Choose output file")
        self.button_output.clicked.connect(self.select_output_file)

        self.label_instruction = QLabel(
            "How to use:\n1. Choose video file\n2. Choose output file\n3. Select language\n4. Input keyword\n5. Click 'Start'",
            alignment=Qt.AlignLeft
        )

        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["ru", "en", "de", "fr", "es"])

        self.input_word = QLineEdit()
        self.input_word.setPlaceholderText("Enter keyword")

        self.button_start = QPushButton("Start")
        self.button_stop = QPushButton("Stop")
        self.button_stop.setEnabled(False)

        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setFixedHeight(25)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #aaa;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #05B8CC;
                width: 10px;
            }
        """)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)
        layout.addWidget(self.label_file)
        layout.addWidget(self.button_browse)
        layout.addWidget(self.button_output)
        layout.addWidget(self.label_instruction)
        layout.addWidget(self.combo_lang)
        layout.addWidget(self.input_word)
        layout.addWidget(self.button_start)
        layout.addWidget(self.button_stop)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)
        self.button_browse.clicked.connect(self.select_file)
        self.button_start.clicked.connect(self.start_process)
        self.button_stop.clicked.connect(self.stop_process)

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select video file", "", "Video Files (*.mp4 *.mkv *.mov)")
        if path:
            self.video_file = path
            self.label_file.setText(f"Video file: {os.path.basename(path)}")

    def select_output_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save output file", "", "Video Files (*.mp4)")
        if path:
            if not path.endswith(".mp4"):
                path += ".mp4"
            self.output_path = path
            self.button_output.setText(f"Output: {os.path.basename(path)}")

    def start_process(self):
        if not self.video_file or not self.input_word.text():
            return

        self.button_start.setEnabled(False)
        self.button_stop.setEnabled(True)
        self.progress_bar.setValue(0)
        self.label_file.setText(f"Processing {os.path.basename(self.video_file)}...")

        self.worker = Worker(
            video_file=self.video_file,
            language=self.combo_lang.currentText(),
            word=self.input_word.text().strip(),
            output_path=self.output_path or "output.mp4"
        )
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def stop_process(self):
        if hasattr(self, "worker") and self.worker.isRunning():
            self.worker.stop()
            self.worker.terminate()
            self.button_start.setEnabled(True)
            self.button_stop.setEnabled(False)
            self.label_file.setText("❌ Process was manually stopped.")

    def on_finished(self, success: bool):
        self.button_start.setEnabled(True)
        self.button_stop.setEnabled(False)
        if success:
            self.label_file.setText("✅ Done! Output saved")
        else:
            self.label_file.setText("❌ An error occurred during processing.")


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    win = WordClipApp()
    win.resize(300, 200)
    win.show()
    sys.exit(app.exec())

# pyinstaller --noconfirm --onefile --windowed --icon=logo.ico main_with_gui.py

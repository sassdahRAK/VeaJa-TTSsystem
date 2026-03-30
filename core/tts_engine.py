"""
Cross-platform TTS engine using pyttsx3.
Runs in a QThread so it never blocks the UI.
"""

import sys
import pyttsx3
from PyQt6.QtCore import QThread, pyqtSignal


class TTSWorker(QThread):
    """Runs TTS playback in a background thread."""

    started_speaking = pyqtSignal()
    finished_speaking = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, text: str, rate: int = 175, volume: float = 1.0,
                 voice_id: str = None):
        super().__init__()
        self._text = text
        self._rate = rate
        self._volume = volume
        self._voice_id = voice_id
        self._stop_requested = False

    def run(self):
        try:
            self.started_speaking.emit()
            engine = pyttsx3.init()
            engine.setProperty("rate", self._rate)
            engine.setProperty("volume", self._volume)

            if self._voice_id:
                engine.setProperty("voice", self._voice_id)

            engine.say(self._text)
            engine.runAndWait()
            engine.stop()
        except Exception as exc:
            self.error_occurred.emit(str(exc))
        finally:
            self.finished_speaking.emit()

    def stop(self):
        self._stop_requested = True
        self.terminate()
        self.wait(500)


class TTSEngine:
    """
    High-level TTS manager.
    Keeps one worker alive at a time; replaces it on each speak() call.
    """

    def __init__(self):
        self._worker: TTSWorker | None = None
        self._rate = 175
        self._volume = 1.0
        self._voice_id: str | None = None
        self._voices: list[dict] = []
        self._load_voices()

    # ------------------------------------------------------------------ #
    # Voice discovery
    # ------------------------------------------------------------------ #

    def _load_voices(self):
        try:
            engine = pyttsx3.init()
            raw = engine.getProperty("voices")
            self._voices = [
                {"id": v.id, "name": v.name, "lang": getattr(v, "languages", [])}
                for v in raw
            ]
            engine.stop()
        except Exception:
            self._voices = []

    def get_voices(self) -> list[dict]:
        return self._voices

    # ------------------------------------------------------------------ #
    # Playback
    # ------------------------------------------------------------------ #

    def speak(self, text: str,
              on_start=None, on_finish=None, on_error=None) -> TTSWorker:
        """Start speaking; returns the worker (caller can connect extra signals)."""
        self.stop()

        worker = TTSWorker(text, self._rate, self._volume, self._voice_id)
        if on_start:
            worker.started_speaking.connect(on_start)
        if on_finish:
            worker.finished_speaking.connect(on_finish)
        if on_error:
            worker.error_occurred.connect(on_error)

        self._worker = worker
        worker.start()
        return worker

    def stop(self):
        if self._worker and self._worker.isRunning():
            self._worker.stop()
        self._worker = None

    def is_speaking(self) -> bool:
        return bool(self._worker and self._worker.isRunning())

    # ------------------------------------------------------------------ #
    # Settings
    # ------------------------------------------------------------------ #

    def set_rate(self, rate: int):
        self._rate = max(50, min(400, rate))

    def set_volume(self, volume: float):
        self._volume = max(0.0, min(1.0, volume))

    def set_voice(self, voice_id: str | None):
        self._voice_id = voice_id

    def get_rate(self) -> int:
        return self._rate

    def get_volume(self) -> float:
        return self._volume

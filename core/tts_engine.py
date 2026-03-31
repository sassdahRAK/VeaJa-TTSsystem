"""
TTS engine — two backends:
  1. EdgeTTSWorker  (default)  — Microsoft neural voices via edge-tts.
                                 Sounds very human. Requires internet.
                                 Streams sentence-by-sentence so first audio
                                 starts within ~1-2 s even for very long text.
  2. Pyttsx3Worker (fallback) — SAPI5 system voices (offline).

Signals emitted (in order):
  preparing_speech  — synthesis of first sentence has started (show "Processing…")
  started_speaking  — first sentence is actually playing  (show "Speaking…")
  finished_speaking — all done or stopped
  error_occurred    — something went wrong
"""

import asyncio
import os
import re
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, Future

import pyttsx3
import pygame
from PyQt6.QtCore import QThread, pyqtSignal

# ── Initialise pygame mixer once at import time ───────────────────────────────
try:
    pygame.mixer.init()
    _PYGAME_OK = True
except Exception:
    _PYGAME_OK = False

# ── Built-in list of neural voices exposed in the UI ─────────────────────────
EDGE_TTS_VOICES = [
    {"id": "en-US-AriaNeural",    "name": "Aria  — US Female  (Neural)"},
    {"id": "en-US-JennyNeural",   "name": "Jenny — US Female  (Neural)"},
    {"id": "en-US-GuyNeural",     "name": "Guy   — US Male    (Neural)"},
    {"id": "en-US-DavisNeural",   "name": "Davis — US Male    (Neural)"},
    {"id": "en-GB-SoniaNeural",   "name": "Sonia — UK Female  (Neural)"},
    {"id": "en-GB-RyanNeural",    "name": "Ryan  — UK Male    (Neural)"},
    {"id": "en-AU-NatashaNeural", "name": "Natasha — AU Female (Neural)"},
    {"id": "en-AU-WilliamNeural", "name": "William — AU Male   (Neural)"},
]


# ─────────────────────────────────────────────────────────────────────────────
# Sentence splitter
# ─────────────────────────────────────────────────────────────────────────────

def _split_sentences(text: str) -> list[str]:
    """
    Split text into sentence-sized chunks.
    Short fragments (< 40 chars) are merged with the next sentence
    to avoid too many tiny synthesis requests.
    """
    parts = re.split(r'(?<=[.!?…])\s+', text.strip())
    chunks: list[str] = []
    buf = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if buf:
            if len(buf) < 40:
                buf = buf + " " + part
                continue
            chunks.append(buf)
        buf = part
    if buf:
        chunks.append(buf)
    return chunks if chunks else [text]


# ═════════════════════════════════════════════════════════════════════════════
# Backend 1 — Edge-TTS + pygame  (neural, online, streamed sentence-by-sentence)
# ═════════════════════════════════════════════════════════════════════════════

class EdgeTTSWorker(QThread):
    """
    Streams long text as sentences so audio begins within ~1 s.

    Timeline:
      click → preparing_speech → [synthesise s1] → started_speaking
           → play s1 / synthesise s2 in parallel
           → play s2 / synthesise s3 in parallel  …
           → finished_speaking
    """

    preparing_speech  = pyqtSignal()   # synthesis started — show "Processing…"
    started_speaking  = pyqtSignal()   # first audio playing — show "Speaking…"
    finished_speaking = pyqtSignal()
    error_occurred    = pyqtSignal(str)

    def __init__(self, text: str, voice: str = "en-US-AriaNeural",
                 rate: str = "+0%", volume: float = 1.0):
        super().__init__()
        self._text       = text
        self._voice      = voice
        self._rate       = rate
        self._volume     = volume
        self._stop_event = threading.Event()

    # ── Main thread body ──────────────────────────────────────────────────────

    def run(self):
        sentences = _split_sentences(self._text)
        tmp_files: list[str] = []

        try:
            self.preparing_speech.emit()

            # Pre-fetch: synthesise sentence[i+1] while sentence[i] is playing.
            with ThreadPoolExecutor(max_workers=1) as pool:
                # Kick off synthesis of the first sentence immediately.
                next_future: Future = pool.submit(self._synthesise, sentences[0])

                for i, _sentence in enumerate(sentences):
                    if self._stop_event.is_set():
                        break

                    # Wait for current sentence's audio file.
                    tmp_path = next_future.result()

                    # While we waited, kick off the next sentence in parallel.
                    if i + 1 < len(sentences) and not self._stop_event.is_set():
                        next_future = pool.submit(
                            self._synthesise, sentences[i + 1]
                        )

                    if tmp_path is None or self._stop_event.is_set():
                        break

                    tmp_files.append(tmp_path)

                    # First sentence ready → audio is about to start.
                    if i == 0:
                        self.started_speaking.emit()

                    # Play this sentence.
                    pygame.mixer.music.load(tmp_path)
                    pygame.mixer.music.set_volume(self._volume)
                    pygame.mixer.music.play()

                    while pygame.mixer.music.get_busy():
                        if self._stop_event.is_set():
                            pygame.mixer.music.stop()
                            break
                        self.msleep(40)

                    try:
                        pygame.mixer.music.unload()
                    except Exception:
                        pass

        except Exception as exc:
            self.error_occurred.emit(str(exc))
        finally:
            # Clean up all temp files.
            for f in tmp_files:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except Exception:
                    pass
            self.finished_speaking.emit()

    # ── Per-sentence synthesis (runs in thread-pool, NOT the QThread) ─────────

    def _synthesise(self, sentence: str) -> str | None:
        """Synthesise one sentence to a temp MP3. Returns path or None."""
        try:
            import edge_tts
        except ImportError:
            self.error_occurred.emit(
                "edge-tts not installed. Run: pip install edge-tts"
            )
            return None

        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()

        async def _gen():
            communicate = edge_tts.Communicate(sentence, self._voice,
                                               rate=self._rate)
            await communicate.save(tmp.name)

        try:
            asyncio.run(_gen())
            return tmp.name
        except Exception as exc:
            self.error_occurred.emit(f"EdgeTTS error: {exc}")
            try:
                os.remove(tmp.name)
            except Exception:
                pass
            return None

    # ── Stop (called from main thread) ────────────────────────────────────────

    def stop(self):
        self._stop_event.set()
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self.wait(1500)


# ═════════════════════════════════════════════════════════════════════════════
# Backend 2 — pyttsx3 / SAPI5  (offline fallback)
# ═════════════════════════════════════════════════════════════════════════════

class Pyttsx3Worker(QThread):
    """Offline TTS using the system SAPI5 / espeak engine."""

    preparing_speech  = pyqtSignal()
    started_speaking  = pyqtSignal()
    finished_speaking = pyqtSignal()
    error_occurred    = pyqtSignal(str)

    def __init__(self, text: str, rate: int = 175, volume: float = 1.0,
                 voice_id: str | None = None):
        super().__init__()
        self._text     = text
        self._rate     = rate
        self._volume   = volume
        self._voice_id = voice_id
        self._engine: pyttsx3.Engine | None = None

    def run(self):
        try:
            self.preparing_speech.emit()
            engine = pyttsx3.init()
            self._engine = engine
            engine.setProperty("rate",   self._rate)
            engine.setProperty("volume", self._volume)
            if self._voice_id:
                engine.setProperty("voice", self._voice_id)
            self.started_speaking.emit()
            engine.say(self._text)
            engine.runAndWait()
        except Exception as exc:
            self.error_occurred.emit(str(exc))
        finally:
            try:
                if self._engine:
                    self._engine.stop()
            except Exception:
                pass
            self._engine = None
            self.finished_speaking.emit()

    def stop(self):
        try:
            if self._engine:
                self._engine.stop()
        except Exception:
            pass
        self.terminate()
        self.wait(500)


# ═════════════════════════════════════════════════════════════════════════════
# High-level TTSEngine  (used by AppController)
# ═════════════════════════════════════════════════════════════════════════════

class TTSEngine:
    """
    Manages one active worker at a time.

    Prefers EdgeTTS (neural, human-like) when edge-tts + pygame are available.
    Falls back to pyttsx3 automatically.
    """

    def __init__(self):
        self._worker = None

        # Edge-TTS settings
        self._edge_voice = "en-US-AriaNeural"
        self._edge_rate  = "+0%"
        self._volume     = 1.0

        # pyttsx3 fallback settings
        self._rate        = 175
        self._voice_id: str | None = None
        self._pyttsx3_voices: list[dict] = []

        self._edge_available = self._check_edge_tts()
        if not self._edge_available:
            self._load_pyttsx3_voices()

    # ── Backend detection ─────────────────────────────────────────────────────

    @staticmethod
    def _check_edge_tts() -> bool:
        try:
            import edge_tts  # noqa: F401
            return _PYGAME_OK
        except ImportError:
            return False

    def is_edge_available(self) -> bool:
        return self._edge_available

    # ── Voice discovery ───────────────────────────────────────────────────────

    def _load_pyttsx3_voices(self):
        try:
            engine = pyttsx3.init()
            raw = engine.getProperty("voices")
            self._pyttsx3_voices = [
                {"id": v.id, "name": v.name}
                for v in raw
            ]
            engine.stop()
        except Exception:
            self._pyttsx3_voices = []

    def get_voices(self) -> list[dict]:
        return EDGE_TTS_VOICES if self._edge_available else self._pyttsx3_voices

    # ── Playback ──────────────────────────────────────────────────────────────

    def speak(self, text: str,
              on_preparing=None, on_start=None,
              on_finish=None, on_error=None):
        self.stop()

        if self._edge_available:
            worker = EdgeTTSWorker(
                text,
                voice=self._edge_voice,
                rate=self._edge_rate,
                volume=self._volume,
            )
        else:
            worker = Pyttsx3Worker(
                text, self._rate, self._volume, self._voice_id
            )

        if on_preparing:
            worker.preparing_speech.connect(on_preparing)
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

    # ── Settings ──────────────────────────────────────────────────────────────

    def set_voice(self, voice_id: str | None):
        if self._edge_available:
            if voice_id:
                self._edge_voice = voice_id
        else:
            self._voice_id = voice_id

    def set_rate(self, rate: int):
        self._rate = max(50, min(400, rate))
        pct = round((self._rate - 175) / 175 * 100)
        pct = max(-50, min(100, pct))
        sign = "+" if pct >= 0 else ""
        self._edge_rate = f"{sign}{pct}%"

    def set_volume(self, volume: float):
        self._volume = max(0.0, min(1.0, volume))

    def get_rate(self) -> int:
        return self._rate

    def get_volume(self) -> float:
        return self._volume

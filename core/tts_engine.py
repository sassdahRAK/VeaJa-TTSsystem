"""
TTS engine — two backends:
  1. EdgeTTSWorker  — Microsoft neural voices (online, human-like).
                      Streams sentence-by-sentence → first audio in ~1 s.
                      Supports pause / resume via pygame.
                      Saves combined reading session as a single MP3 file.
  2. Pyttsx3Worker  — SAPI5 system voices (offline fallback, no pause support).

Signal lifecycle (in order):
  preparing_speech  → synthesis started          → show "Processing…"
  started_speaking  → first sentence playing     → show "Speaking…"
  paused_speaking   → audio paused               → show "Paused"
  resumed_speaking  → audio resumed              → show "Speaking…"
  finished_speaking → all done / stopped
  error_occurred    → something went wrong
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

# ── Neural voice catalogue ────────────────────────────────────────────────────
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
    Fragments shorter than 40 chars are merged with the next sentence
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
# Backend 1 — Edge-TTS + pygame  (neural, online)
# ═════════════════════════════════════════════════════════════════════════════

class EdgeTTSWorker(QThread):
    """
    Sentence-streaming TTS worker with pause/resume and MP3 session save.

    Timeline:
      preparing_speech → [synthesise s1] → started_speaking
        → play s1 / synthesise s2 in parallel
        → play s2 / synthesise s3 in parallel …
        → finished_speaking
        → (if not stopped) combine all sentence MP3s → session_path
    """

    preparing_speech  = pyqtSignal()
    started_speaking  = pyqtSignal()
    paused_speaking   = pyqtSignal()
    resumed_speaking  = pyqtSignal()
    finished_speaking = pyqtSignal()
    error_occurred    = pyqtSignal(str)

    def __init__(self, text: str, voice: str = "en-US-AriaNeural",
                 rate: str = "+0%", volume: float = 1.0,
                 session_path: str | None = None):
        super().__init__()
        self._text         = text
        self._voice        = voice
        self._rate         = rate
        self._volume       = volume
        self._session_path = session_path    # where to save combined MP3

        self._stop_event  = threading.Event()
        self._pause_event = threading.Event()   # set = paused
        self._sentence_mp3s: list[str] = []     # ordered sentence files for combine

    # ── Main thread body ──────────────────────────────────────────────────────

    def run(self):
        sentences   = _split_sentences(self._text)
        tmp_files: list[str] = []

        try:
            self.preparing_speech.emit()

            with ThreadPoolExecutor(max_workers=1) as pool:
                next_future: Future = pool.submit(self._synthesise, sentences[0])

                for i, _sentence in enumerate(sentences):
                    if self._stop_event.is_set():
                        break

                    tmp_path = next_future.result()

                    # Pre-fetch next sentence while this one plays
                    if i + 1 < len(sentences) and not self._stop_event.is_set():
                        next_future = pool.submit(self._synthesise, sentences[i + 1])

                    if tmp_path is None or self._stop_event.is_set():
                        break

                    tmp_files.append(tmp_path)
                    self._sentence_mp3s.append(tmp_path)

                    if i == 0:
                        self.started_speaking.emit()

                    pygame.mixer.music.load(tmp_path)
                    pygame.mixer.music.set_volume(self._volume)
                    pygame.mixer.music.play()

                    # ── Playback loop — handles stop and pause ──────────────
                    while pygame.mixer.music.get_busy():
                        if self._stop_event.is_set():
                            pygame.mixer.music.stop()
                            break

                        if self._pause_event.is_set():
                            pygame.mixer.music.pause()
                            self.paused_speaking.emit()
                            # Wait until unpaused or stopped
                            while self._pause_event.is_set():
                                if self._stop_event.is_set():
                                    pygame.mixer.music.stop()
                                    break
                                self.msleep(40)
                            else:
                                # Unpaused cleanly → resume
                                pygame.mixer.music.unpause()
                                self.resumed_speaking.emit()
                            if self._stop_event.is_set():
                                break

                        self.msleep(40)
                    # ────────────────────────────────────────────────────────

                    try:
                        pygame.mixer.music.unload()
                    except Exception:
                        pass

                    if self._stop_event.is_set():
                        break

        except Exception as exc:
            self.error_occurred.emit(str(exc))
        finally:
            # Save combined session MP3 (even partial sessions are useful)
            if self._session_path and self._sentence_mp3s:
                self._combine_mp3s(self._sentence_mp3s, self._session_path)

            # Clean up sentence temp files
            for f in tmp_files:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except Exception:
                    pass

            self.finished_speaking.emit()

    # ── Per-sentence synthesis (pool thread) ──────────────────────────────────

    def _synthesise(self, sentence: str) -> str | None:
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
            communicate = edge_tts.Communicate(sentence, self._voice, rate=self._rate)
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

    # ── Combine sentence MP3s into one session file ───────────────────────────

    def _combine_mp3s(self, sources: list[str], dest: str):
        """
        Concatenate CBR MP3 segments by binary append.
        edge-tts always outputs CBR MP3, so frame boundaries are clean.
        No external tools (ffmpeg / pydub) required.
        """
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as out:
                for src in sources:
                    if os.path.exists(src):
                        with open(src, "rb") as f:
                            out.write(f.read())
        except Exception as exc:
            self.error_occurred.emit(f"Audio save error: {exc}")

    # ── Control (called from main thread) ─────────────────────────────────────

    def pause(self):
        """Signal the playback loop to pause at the current position."""
        self._pause_event.set()

    def resume(self):
        """Signal the playback loop to resume from the paused position."""
        self._pause_event.clear()

    def stop(self):
        """Terminate playback immediately."""
        self._stop_event.set()
        self._pause_event.clear()   # unblock the inner pause wait
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self.wait(1500)


# ═════════════════════════════════════════════════════════════════════════════
# Backend 2 — pyttsx3 / SAPI5  (offline fallback, no pause support)
# ═════════════════════════════════════════════════════════════════════════════

class Pyttsx3Worker(QThread):
    """Offline TTS via system SAPI5 / espeak. Pause is not supported."""

    preparing_speech  = pyqtSignal()
    started_speaking  = pyqtSignal()
    paused_speaking   = pyqtSignal()   # never emitted — here for interface parity
    resumed_speaking  = pyqtSignal()   # never emitted
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

    def pause(self):
        pass   # SAPI5 has no reliable pause API

    def resume(self):
        pass

    def stop(self):
        try:
            if self._engine:
                self._engine.stop()
        except Exception:
            pass
        self.terminate()
        self.wait(500)


# ═════════════════════════════════════════════════════════════════════════════
# High-level TTSEngine
# ═════════════════════════════════════════════════════════════════════════════

class TTSEngine:
    """
    Manages one active worker at a time.
    Prefers EdgeTTS (neural, human-like). Falls back to pyttsx3.
    """

    def __init__(self):
        self._worker: EdgeTTSWorker | Pyttsx3Worker | None = None

        # Edge-TTS settings
        self._edge_voice    = "en-US-AriaNeural"
        self._edge_rate     = "+0%"
        self._volume        = 1.0
        self._force_offline = False   # user can override to force pyttsx3

        # pyttsx3 fallback settings
        self._rate        = 175
        self._voice_id: str | None = None
        self._pyttsx3_voices: list[dict] = []

        self._edge_available = self._check_edge_tts()
        self._load_pyttsx3_voices()   # always load so offline mode has voices

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

    def _use_edge(self) -> bool:
        """True when EdgeTTS is available AND not forced offline."""
        return self._edge_available and not self._force_offline

    def set_forced_offline(self, offline: bool):
        """Force pyttsx3 even if edge-tts is installed (user preference)."""
        self._force_offline = offline

    def supports_pause(self) -> bool:
        """True only when EdgeTTS backend is active."""
        return self._use_edge()

    # ── Voice discovery ───────────────────────────────────────────────────────

    def _load_pyttsx3_voices(self):
        try:
            engine = pyttsx3.init()
            raw = engine.getProperty("voices")
            self._pyttsx3_voices = [{"id": v.id, "name": v.name} for v in raw]
            engine.stop()
        except Exception:
            self._pyttsx3_voices = []

    def get_voices(self) -> list[dict]:
        return EDGE_TTS_VOICES if self._use_edge() else self._pyttsx3_voices

    # ── Playback ──────────────────────────────────────────────────────────────

    def speak(self, text: str,
              on_preparing=None, on_start=None,
              on_finish=None, on_error=None,
              on_paused=None, on_resumed=None,
              session_path: str | None = None):
        self.stop()

        if self._use_edge():
            worker = EdgeTTSWorker(
                text,
                voice=self._edge_voice,
                rate=self._edge_rate,
                volume=self._volume,
                session_path=session_path,
            )
        else:
            worker = Pyttsx3Worker(text, self._rate, self._volume, self._voice_id)

        if on_preparing: worker.preparing_speech.connect(on_preparing)
        if on_start:     worker.started_speaking.connect(on_start)
        if on_finish:    worker.finished_speaking.connect(on_finish)
        if on_error:     worker.error_occurred.connect(on_error)
        if on_paused:    worker.paused_speaking.connect(on_paused)
        if on_resumed:   worker.resumed_speaking.connect(on_resumed)

        self._worker = worker
        worker.start()
        return worker

    def stop(self):
        if self._worker and self._worker.isRunning():
            self._worker.stop()
        self._worker = None

    def pause(self):
        if self._worker and self._worker.isRunning():
            self._worker.pause()

    def resume(self):
        if self._worker and self._worker.isRunning():
            self._worker.resume()

    def is_speaking(self) -> bool:
        return bool(self._worker and self._worker.isRunning())

    def is_paused(self) -> bool:
        if isinstance(self._worker, EdgeTTSWorker):
            return self._worker._pause_event.is_set()
        return False

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

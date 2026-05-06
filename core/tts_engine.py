"""
TTS engine — two backends:
  1. EdgeTTSWorker  — Microsoft neural voices (online, human-like).
                      Streams sentence-by-sentence → first audio in ~1 s.
                      Supports pause / resume via pygame.
                      Saves combined reading session as a single MP3 file.
  2. Pyttsx3Worker  — System voices (offline fallback).
                      Both Linux (espeak) and Windows (SAPI5) use a true
                      producer-consumer pipeline: a background thread renders
                      each sentence to a WAV file while pygame plays the
                      previous one — first audio plays immediately.

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
import shutil
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, Future

import pyttsx3
import pygame
from PyQt6.QtCore import QThread, pyqtSignal

from config.settings import (
    EDGE_TTS_TIMEOUT_S, MAX_SENTENCE_AUDIO_BYTES,
    MAX_SENTENCE_QUEUE,
    EDGE_TTS_MAX_RETRIES, EDGE_TTS_RETRY_DELAY_S,
)

# ── Initialise pygame mixer once at import time ───────────────────────────────
try:
    pygame.mixer.init()
    _PYGAME_OK = True
except Exception:
    _PYGAME_OK = False

# ── Neural voice catalogue — organised by language ────────────────────────────
# Each entry: {"id": "<edge-tts voice id>", "name": "<display name>", "lang": "<iso code>"}
EDGE_TTS_VOICES_ALL: list[dict] = [
    # English
    {"id": "en-US-AriaNeural",      "name": "Aria     — US Female  (Neural)", "lang": "en"},
    {"id": "en-US-JennyNeural",     "name": "Jenny    — US Female  (Neural)", "lang": "en"},
    {"id": "en-US-GuyNeural",       "name": "Guy      — US Male    (Neural)", "lang": "en"},
    {"id": "en-US-DavisNeural",     "name": "Davis    — US Male    (Neural)", "lang": "en"},
    {"id": "en-GB-SoniaNeural",     "name": "Sonia    — UK Female  (Neural)", "lang": "en"},
    {"id": "en-GB-RyanNeural",      "name": "Ryan     — UK Male    (Neural)", "lang": "en"},
    {"id": "en-AU-NatashaNeural",   "name": "Natasha  — AU Female  (Neural)", "lang": "en"},
    {"id": "en-AU-WilliamNeural",   "name": "William  — AU Male    (Neural)", "lang": "en"},
    # French
    {"id": "fr-FR-DeniseNeural",    "name": "Denise   — FR Female  (Neural)", "lang": "fr"},
    {"id": "fr-FR-HenriNeural",     "name": "Henri    — FR Male    (Neural)", "lang": "fr"},
    {"id": "fr-CA-SylvieNeural",    "name": "Sylvie   — CA Female  (Neural)", "lang": "fr"},
    {"id": "fr-CA-JeanNeural",      "name": "Jean     — CA Male    (Neural)", "lang": "fr"},
    # Khmer
    {"id": "km-KH-SreymomNeural",   "name": "Sreymom  — KH Female  (Neural)", "lang": "km"},
    {"id": "km-KH-PisethNeural",    "name": "Piseth   — KH Male    (Neural)", "lang": "km"},
    # Chinese
    {"id": "zh-CN-XiaoxiaoNeural",  "name": "Xiaoxiao — CN Female  (Neural)", "lang": "zh"},
    {"id": "zh-CN-YunxiNeural",     "name": "Yunxi    — CN Male    (Neural)", "lang": "zh"},
    {"id": "zh-TW-HsiaoChenNeural", "name": "HsiaoChen— TW Female  (Neural)", "lang": "zh"},
    {"id": "zh-TW-YunJheNeural",    "name": "YunJhe   — TW Male    (Neural)", "lang": "zh"},
    # Japanese
    {"id": "ja-JP-NanamiNeural",    "name": "Nanami   — JP Female  (Neural)", "lang": "ja"},
    {"id": "ja-JP-KeitaNeural",     "name": "Keita    — JP Male    (Neural)", "lang": "ja"},
    # Korean
    {"id": "ko-KR-SunHiNeural",     "name": "SunHi    — KR Female  (Neural)", "lang": "ko"},
    {"id": "ko-KR-InJoonNeural",    "name": "InJoon   — KR Male    (Neural)", "lang": "ko"},
    # Thai
    {"id": "th-TH-PremwadeeNeural", "name": "Premwadee— TH Female  (Neural)", "lang": "th"},
    {"id": "th-TH-NiwatNeural",     "name": "Niwat    — TH Male    (Neural)", "lang": "th"},
    # Hindi
    {"id": "hi-IN-SwaraNeural",     "name": "Swara    — IN Female  (Neural)", "lang": "hi"},
    {"id": "hi-IN-MadhurNeural",    "name": "Madhur   — IN Male    (Neural)", "lang": "hi"},
    # Arabic
    {"id": "ar-EG-SalmaNeural",     "name": "Salma    — EG Female  (Neural)", "lang": "ar"},
    {"id": "ar-EG-ShakirNeural",    "name": "Shakir   — EG Male    (Neural)", "lang": "ar"},
    {"id": "ar-SA-ZariyahNeural",   "name": "Zariyah  — SA Female  (Neural)", "lang": "ar"},
    {"id": "ar-SA-HamedNeural",     "name": "Hamed    — SA Male    (Neural)", "lang": "ar"},
    # German
    {"id": "de-DE-KatjaNeural",     "name": "Katja    — DE Female  (Neural)", "lang": "de"},
    {"id": "de-DE-ConradNeural",    "name": "Conrad   — DE Male    (Neural)", "lang": "de"},
    # Spanish
    {"id": "es-ES-ElviraNeural",    "name": "Elvira   — ES Female  (Neural)", "lang": "es"},
    {"id": "es-ES-AlvaroNeural",    "name": "Alvaro   — ES Male    (Neural)", "lang": "es"},
    {"id": "es-MX-DaliaNeural",     "name": "Dalia    — MX Female  (Neural)", "lang": "es"},
    {"id": "es-MX-JorgeNeural",     "name": "Jorge    — MX Male    (Neural)", "lang": "es"},
    # Portuguese
    {"id": "pt-BR-FranciscaNeural", "name": "Francisca— BR Female  (Neural)", "lang": "pt"},
    {"id": "pt-BR-AntonioNeural",   "name": "Antonio  — BR Male    (Neural)", "lang": "pt"},
    {"id": "pt-PT-RaquelNeural",    "name": "Raquel   — PT Female  (Neural)", "lang": "pt"},
    {"id": "pt-PT-DuarteNeural",    "name": "Duarte   — PT Male    (Neural)", "lang": "pt"},
    # Russian
    {"id": "ru-RU-SvetlanaNeural",  "name": "Svetlana — RU Female  (Neural)", "lang": "ru"},
    {"id": "ru-RU-DmitryNeural",    "name": "Dmitry   — RU Male    (Neural)", "lang": "ru"},
    # Vietnamese
    {"id": "vi-VN-HoaiMyNeural",    "name": "HoaiMy   — VN Female  (Neural)", "lang": "vi"},
    {"id": "vi-VN-NamMinhNeural",   "name": "NamMinh  — VN Male    (Neural)", "lang": "vi"},
    # Indonesian
    {"id": "id-ID-GadisNeural",     "name": "Gadis    — ID Female  (Neural)", "lang": "id"},
    {"id": "id-ID-ArdiNeural",      "name": "Ardi     — ID Male    (Neural)", "lang": "id"},
]

# Legacy alias — keeps any code that imports EDGE_TTS_VOICES working
EDGE_TTS_VOICES = [v for v in EDGE_TTS_VOICES_ALL if v["lang"] == "en"]


def get_voices_for_lang(lang: str) -> list[dict]:
    """Return Edge-TTS voices for the given ISO 639-1 language code."""
    matched = [v for v in EDGE_TTS_VOICES_ALL if v["lang"] == lang]
    return matched if matched else EDGE_TTS_VOICES   # fall back to English


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
    word_highlight    = pyqtSignal(int, int)   # (char_start, char_end) in full text

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
        self._word_idx: int = 0                 # pointer for word-highlight scan

    # ── Main thread body ──────────────────────────────────────────────────────

    def run(self):
        sentences  = _split_sentences(self._text)

        if len(sentences) > MAX_SENTENCE_QUEUE:
            self.error_occurred.emit(
                f"Warning: Text too long ({len(sentences)} sentences). "
                f"Reading the first {MAX_SENTENCE_QUEUE} sentences only."
            )
            sentences = sentences[:MAX_SENTENCE_QUEUE]

        tmp_files: list[str] = []

        char_offsets: list[int] = []
        search_pos = 0
        for s in sentences:
            idx = self._text.find(s, search_pos)
            char_offsets.append(idx if idx != -1 else search_pos)
            search_pos = (idx if idx != -1 else search_pos) + len(s)

        try:
            self.preparing_speech.emit()

            with ThreadPoolExecutor(max_workers=1) as pool:
                next_future: Future = pool.submit(self._synthesise, sentences[0])

                for i, _sentence in enumerate(sentences):
                    if self._stop_event.is_set():
                        break

                    tmp_path, boundaries = next_future.result()

                    if i + 1 < len(sentences) and not self._stop_event.is_set():
                        next_future = pool.submit(self._synthesise, sentences[i + 1])

                    if tmp_path is None or self._stop_event.is_set():
                        break

                    try:
                        if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) < 64:
                            continue
                    except OSError:
                        continue

                    tmp_files.append(tmp_path)
                    self._sentence_mp3s.append(tmp_path)

                    if i == 0:
                        self.started_speaking.emit()

                    self._word_idx = 0

                    try:
                        pygame.mixer.music.load(tmp_path)
                        pygame.mixer.music.set_volume(self._volume)
                        pygame.mixer.music.play()
                    except Exception as load_exc:
                        self.error_occurred.emit(f"Audio load error: {load_exc}")
                        continue

                    sentence_char_offset = char_offsets[i]

                    while pygame.mixer.music.get_busy():
                        if self._stop_event.is_set():
                            pygame.mixer.music.stop()
                            break

                        if self._pause_event.is_set():
                            pygame.mixer.music.pause()
                            self.paused_speaking.emit()
                            while self._pause_event.is_set():
                                if self._stop_event.is_set():
                                    pygame.mixer.music.stop()
                                    break
                                self.msleep(40)
                            else:
                                pygame.mixer.music.unpause()
                                self.resumed_speaking.emit()
                            if self._stop_event.is_set():
                                break

                        if boundaries:
                            pos_ms = pygame.mixer.music.get_pos()
                            if pos_ms >= 0:
                                self._emit_word_highlight(
                                    boundaries, sentence_char_offset, pos_ms
                                )

                        self.msleep(40)

                    try:
                        pygame.mixer.music.unload()
                    except Exception:
                        pass

                    if self._stop_event.is_set():
                        break

        except Exception as exc:
            self.error_occurred.emit(str(exc))
        finally:
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass

            if self._session_path and self._sentence_mp3s:
                self._combine_mp3s(self._sentence_mp3s, self._session_path)

            for f in tmp_files:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except Exception:
                    pass

            if not self.isInterruptionRequested():
                self.finished_speaking.emit()

    # ── Word highlight helper ──────────────────────────────────────────────────

    def _emit_word_highlight(self, boundaries: list[dict],
                             sentence_offset: int, pos_ms: int):
        if not boundaries:
            return
        while (self._word_idx + 1 < len(boundaries) and
               boundaries[self._word_idx + 1]["offset_ms"] <= pos_ms):
            self._word_idx += 1
        wb = boundaries[self._word_idx]
        if wb["offset_ms"] <= pos_ms:
            start = sentence_offset + wb["text_offset"]
            end   = start + wb["word_length"]
            self.word_highlight.emit(start, end)

    # ── Per-sentence synthesis (pool thread) ──────────────────────────────────

    def _synthesise(self, sentence: str) -> tuple[str | None, list[dict]]:
        try:
            import edge_tts
        except ImportError:
            self.error_occurred.emit(
                "edge-tts not installed. Run: pip install edge-tts"
            )
            return None, []

        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()

        word_boundaries: list[dict] = []

        async def _gen():
            communicate = edge_tts.Communicate(sentence, self._voice, rate=self._rate)
            audio = bytearray()
            async for event in communicate.stream():
                if len(audio) > MAX_SENTENCE_AUDIO_BYTES:
                    raise RuntimeError(
                        f"Audio buffer exceeded {MAX_SENTENCE_AUDIO_BYTES // 1024} KB "
                        "— sentence may be malformed or stream is corrupted."
                    )
                if event["type"] == "audio":
                    audio.extend(event["data"])
                elif event["type"] == "WordBoundary":
                    word_boundaries.append({
                        "offset_ms":   event["offset"]   // 10_000,
                        "duration_ms": event["duration"] // 10_000,
                        "text":        event["text"],
                        "text_offset": event["text_offset"],
                        "word_length": event["word_length"],
                    })
            with open(tmp.name, "wb") as fout:
                fout.write(bytes(audio))

        import time as _time
        delay = EDGE_TTS_RETRY_DELAY_S
        for attempt in range(1, EDGE_TTS_MAX_RETRIES + 1):
            word_boundaries.clear()
            try:
                asyncio.run(
                    asyncio.wait_for(_gen(), timeout=EDGE_TTS_TIMEOUT_S)
                )
                return tmp.name, word_boundaries
            except asyncio.TimeoutError:
                if attempt < EDGE_TTS_MAX_RETRIES:
                    _time.sleep(delay)
                    delay *= 2
                    continue
                self.error_occurred.emit(
                    f"EdgeTTS timed out after {EDGE_TTS_MAX_RETRIES} attempts "
                    f"({EDGE_TTS_TIMEOUT_S}s each). Check your internet connection."
                )
            except Exception as exc:
                self.error_occurred.emit(f"EdgeTTS error: {exc}")
                break
        try:
            os.remove(tmp.name)
        except Exception:
            pass
        return None, []

    # ── Combine sentence MP3s into one session file ───────────────────────────

    def _combine_mp3s(self, sources: list[str], dest: str):
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as out:
                for src in sources:
                    if os.path.exists(src):
                        with open(src, "rb") as f:
                            shutil.copyfileobj(f, out)
        except Exception as exc:
            self.error_occurred.emit(f"Audio save error: {exc}")

    # ── Control (called from main thread) ─────────────────────────────────────

    def pause(self):
        self._pause_event.set()

    def resume(self):
        self._pause_event.clear()

    def stop(self):
        """
        Signal the worker to stop immediately without blocking the main thread.
        
        Non-blocking: We set the stop event and stop pygame immediately,
        then schedule a cleanup check via QTimer to avoid freezing the UI.
        """
        self._stop_event.set()
        self._pause_event.clear()
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        
        # Schedule non-blocking cleanup after 800ms
        from PyQt6.QtCore import QTimer
        def _cleanup():
            if self.isRunning():
                self.terminate()
                self.wait(300)
        QTimer.singleShot(800, _cleanup)


# ═════════════════════════════════════════════════════════════════════════════
# Backend 2 — pyttsx3 save-to-file + pygame  (offline, same pattern as Edge)
# ═════════════════════════════════════════════════════════════════════════════

class Pyttsx3Worker(QThread):
    """
    Offline TTS using the same architecture as EdgeTTSWorker:

      1. pyttsx3.save_to_file()  — render each sentence to a WAV file
      2. pygame.mixer.music      — play the WAV file with full stop/pause/resume

    This gives us the same smooth, instantly-stoppable playback as online mode.
    Stop/pause/resume just control pygame — no engine teardown needed.

    Pause IS supported because pygame.mixer.music.pause() works on WAV files.
    """

    preparing_speech  = pyqtSignal()
    started_speaking  = pyqtSignal()
    paused_speaking   = pyqtSignal()
    resumed_speaking  = pyqtSignal()
    finished_speaking = pyqtSignal()
    error_occurred    = pyqtSignal(str)

    def __init__(self, text: str, rate: int = 175, volume: float = 1.0,
                 voice_id: str | None = None,
                 cached_wavs: list[str] | None = None,
                 engine_ref=None,
                 pyttsx3_lock=None):
        super().__init__()
        self._text         = text
        self._rate         = rate
        self._volume       = volume
        self._voice_id     = voice_id
        self._cached_wavs  = cached_wavs
        self._engine_ref   = engine_ref
        self._pyttsx3_lock = pyttsx3_lock   # threading.Lock — serializes espeak access
        self._stop_flag    = threading.Event()
        self._pause_flag   = threading.Event()

    # ── Worker thread body ────────────────────────────────────────────────────

    def run(self):
        # ── Windows SAPI5: use pipeline renderer ──────────────────────────────
        if sys.platform == "win32":
            self._run_windows_sapi()
            return

        # ── Linux / macOS: pipeline render + play ─────────────────────────────
        # Use cached WAVs if available (same text → instant replay)
        if self._cached_wavs:
            self._play_wav_list(list(self._cached_wavs), owns_files=False)
            return

        # Pipeline: render sentences in a background thread, play as they arrive
        self._run_pipeline()

    def _run_pipeline(self):
        """
        True producer-consumer pipeline for Linux/macOS offline TTS.

        A background producer thread renders sentences one-by-one to WAV
        files using pyttsx3/espeak, putting each path into a queue as soon
        as it is ready.  The main worker thread (consumer) plays each WAV
        via pygame the moment it arrives — so sentence 1 starts playing
        while sentence 2 is still being rendered.

        espeak thread-safety: pyttsx3.init() + runAndWait() are called
        exclusively inside the producer thread, which holds the global
        pyttsx3_lock for each sentence.  The lock is released between
        sentences so other parts of the app can access espeak if needed.
        """
        import queue as _queue

        wav_queue: _queue.Queue = _queue.Queue()
        all_rendered_files: list[str] = []
        render_error: list[str] = []

        self.preparing_speech.emit()

        chunks = _split_sentences(self._text)
        if len(chunks) > MAX_SENTENCE_QUEUE:
            self.error_occurred.emit(
                f"Text too long ({len(chunks)} sentences). "
                f"Reading the first {MAX_SENTENCE_QUEUE}."
            )
            chunks = chunks[:MAX_SENTENCE_QUEUE]

        # ── Producer: pyttsx3 renders WAVs sentence-by-sentence ───────────────
        def _producer():
            lock = self._pyttsx3_lock
            try:
                for sentence in chunks:
                    sentence = sentence.strip()
                    if not sentence or self._stop_flag.is_set():
                        break

                    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                    tmp.close()

                    # Hold the lock only for this one sentence render
                    if lock:
                        lock.acquire()
                    try:
                        engine = pyttsx3.init()
                        engine.setProperty("rate",   self._rate)
                        engine.setProperty("volume", 1.0)
                        if self._voice_id:
                            engine.setProperty("voice", self._voice_id)
                        engine.save_to_file(sentence, tmp.name)
                        engine.runAndWait()
                        try:
                            engine.stop()
                            del engine
                        except Exception:
                            pass
                    except Exception as exc:
                        render_error.append(str(exc))
                        try:
                            os.remove(tmp.name)
                        except Exception:
                            pass
                        if lock:
                            lock.release()
                        continue
                    finally:
                        if lock and lock.locked():
                            try:
                                lock.release()
                            except RuntimeError:
                                pass  # already released in except branch

                    if os.path.exists(tmp.name) and os.path.getsize(tmp.name) > 64:
                        wav_queue.put(tmp.name)
                    else:
                        try:
                            os.remove(tmp.name)
                        except Exception:
                            pass

            except Exception as exc:
                render_error.append(str(exc))
            finally:
                wav_queue.put(None)   # sentinel — consumer knows we're done

        producer_thread = threading.Thread(target=_producer, daemon=True,
                                           name="espeak-producer")
        producer_thread.start()

        # ── Consumer: plays WAVs as they arrive ───────────────────────────────
        started = False
        owns_files = True

        try:
            while True:
                try:
                    wav_path = wav_queue.get(timeout=0.05)
                except Exception:
                    if self._stop_flag.is_set():
                        break
                    continue

                if wav_path is None:   # sentinel
                    break

                all_rendered_files.append(wav_path)

                if self._stop_flag.is_set():
                    break

                if not started:
                    self.started_speaking.emit()
                    started = True

                try:
                    pygame.mixer.music.load(wav_path)
                    pygame.mixer.music.set_volume(self._volume)
                    pygame.mixer.music.play()
                except Exception as exc:
                    self.error_occurred.emit(f"Audio playback error: {exc}")
                    continue

                while pygame.mixer.music.get_busy():
                    if self._stop_flag.is_set():
                        pygame.mixer.music.stop()
                        break
                    if self._pause_flag.is_set():
                        pygame.mixer.music.pause()
                        self.paused_speaking.emit()
                        while self._pause_flag.is_set():
                            if self._stop_flag.is_set():
                                pygame.mixer.music.stop()
                                break
                            self.msleep(40)
                        else:
                            pygame.mixer.music.unpause()
                            self.resumed_speaking.emit()
                        if self._stop_flag.is_set():
                            break
                    self.msleep(40)

                try:
                    pygame.mixer.music.unload()
                except Exception:
                    pass

                if self._stop_flag.is_set():
                    break

        except Exception as exc:
            if not self._stop_flag.is_set():
                self.error_occurred.emit(f"Unexpected TTS error: {exc}")
        finally:
            producer_thread.join(timeout=3.0)
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            except Exception:
                pass

            if render_error and not self._stop_flag.is_set():
                self.error_occurred.emit(f"TTS render error: {render_error[0]}")

            # Store in cache for instant replay on restart
            if all_rendered_files and self._engine_ref is not None and not self._stop_flag.is_set():
                try:
                    self._engine_ref.store_wav_cache(self._text, all_rendered_files)
                    owns_files = False
                except Exception:
                    owns_files = True

            if owns_files:
                for f in all_rendered_files:
                    try:
                        if os.path.exists(f):
                            os.remove(f)
                    except Exception:
                        pass

            self.finished_speaking.emit()

    def _play_wav_list(self, wav_files: list[str], owns_files: bool = True):
        """Play a pre-rendered list of WAV files via pygame (cache replay path)."""
        try:
            self.preparing_speech.emit()
            self.started_speaking.emit()

            for wav_path in wav_files:
                if self._stop_flag.is_set():
                    break
                if not os.path.exists(wav_path) or os.path.getsize(wav_path) < 64:
                    continue
                try:
                    pygame.mixer.music.load(wav_path)
                    pygame.mixer.music.set_volume(self._volume)
                    pygame.mixer.music.play()
                except Exception as exc:
                    self.error_occurred.emit(f"Audio playback error: {exc}")
                    continue

                while pygame.mixer.music.get_busy():
                    if self._stop_flag.is_set():
                        pygame.mixer.music.stop()
                        break
                    if self._pause_flag.is_set():
                        pygame.mixer.music.pause()
                        self.paused_speaking.emit()
                        while self._pause_flag.is_set():
                            if self._stop_flag.is_set():
                                pygame.mixer.music.stop()
                                break
                            self.msleep(40)
                        else:
                            pygame.mixer.music.unpause()
                            self.resumed_speaking.emit()
                        if self._stop_flag.is_set():
                            break
                    self.msleep(40)

                try:
                    pygame.mixer.music.unload()
                except Exception:
                    pass

                if self._stop_flag.is_set():
                    break

        except Exception as exc:
            if not self._stop_flag.is_set():
                self.error_occurred.emit(f"Unexpected TTS error: {exc}")
        finally:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            except Exception:
                pass
            if owns_files:
                for f in wav_files:
                    try:
                        if os.path.exists(f):
                            os.remove(f)
                    except Exception:
                        pass
            self.finished_speaking.emit()

    def _run_windows_sapi(self):
        """
        Windows offline TTS — pipeline version:
          Producer: SAPI5 SpFileStream renders each sentence to a temp WAV
          Consumer: pygame plays each WAV as soon as it's ready

        User hears the first sentence immediately instead of waiting for
        all sentences to render first.
        """
        import queue as _queue

        # Use cached WAVs if available (instant replay)
        if self._cached_wavs:
            self._play_wav_list(list(self._cached_wavs), owns_files=False)
            return

        wav_queue: _queue.Queue = _queue.Queue()
        all_rendered_files: list[str] = []
        render_error: list[str] = []

        self.preparing_speech.emit()

        chunks = _split_sentences(self._text)
        if len(chunks) > MAX_SENTENCE_QUEUE:
            self.error_occurred.emit(
                f"Text too long ({len(chunks)} sentences). "
                f"Reading the first {MAX_SENTENCE_QUEUE}."
            )
            chunks = chunks[:MAX_SENTENCE_QUEUE]

        # ── Producer: SAPI5 renders WAVs ──────────────────────────────────────
        def _producer():
            try:
                import comtypes.client
                import comtypes

                voice = comtypes.client.CreateObject("SAPI.SpVoice")
                sapi_rate = max(-10, min(10, int((self._rate - 175) / 25)))
                voice.Rate   = sapi_rate
                voice.Volume = max(0, min(100, int(self._volume * 100)))

                if self._voice_id:
                    try:
                        for v in voice.GetVoices():
                            if v.Id == self._voice_id:
                                voice.Voice = v
                                break
                    except Exception:
                        pass

                SSFMCreateForWrite = 3

                for sentence in chunks:
                    sentence = sentence.strip()
                    if not sentence or self._stop_flag.is_set():
                        break
                    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                    tmp.close()
                    try:
                        stream = comtypes.client.CreateObject("SAPI.SpFileStream")
                        stream.Open(tmp.name, SSFMCreateForWrite, False)
                        old_stream = voice.AudioOutputStream
                        voice.AudioOutputStream = stream
                        voice.Speak(sentence, 0)
                        stream.Close()
                        voice.AudioOutputStream = old_stream
                        if os.path.exists(tmp.name) and os.path.getsize(tmp.name) > 64:
                            wav_queue.put(tmp.name)
                        else:
                            try:
                                os.remove(tmp.name)
                            except Exception:
                                pass
                    except Exception as exc:
                        render_error.append(str(exc))
                        try:
                            os.remove(tmp.name)
                        except Exception:
                            pass

                try:
                    del voice
                except Exception:
                    pass

            except Exception as exc:
                render_error.append(f"Failed to initialize SAPI5: {exc}")
            finally:
                wav_queue.put(None)   # sentinel

        producer_thread = threading.Thread(target=_producer, daemon=True,
                                           name="sapi5-producer")
        producer_thread.start()

        # ── Consumer: plays WAVs as they arrive ───────────────────────────────
        started = False
        owns_files = True

        try:
            while True:
                try:
                    wav_path = wav_queue.get(timeout=0.05)
                except Exception:
                    if self._stop_flag.is_set():
                        break
                    continue

                if wav_path is None:
                    break

                all_rendered_files.append(wav_path)

                if self._stop_flag.is_set():
                    break

                if not started:
                    self.started_speaking.emit()
                    started = True

                try:
                    pygame.mixer.music.load(wav_path)
                    pygame.mixer.music.set_volume(self._volume)
                    pygame.mixer.music.play()
                except Exception as exc:
                    self.error_occurred.emit(f"Audio playback error: {exc}")
                    continue

                while pygame.mixer.music.get_busy():
                    if self._stop_flag.is_set():
                        pygame.mixer.music.stop()
                        break
                    if self._pause_flag.is_set():
                        pygame.mixer.music.pause()
                        self.paused_speaking.emit()
                        while self._pause_flag.is_set():
                            if self._stop_flag.is_set():
                                pygame.mixer.music.stop()
                                break
                            self.msleep(40)
                        else:
                            pygame.mixer.music.unpause()
                            self.resumed_speaking.emit()
                        if self._stop_flag.is_set():
                            break
                    self.msleep(40)

                try:
                    pygame.mixer.music.unload()
                except Exception:
                    pass

                if self._stop_flag.is_set():
                    break

        except Exception as exc:
            if not self._stop_flag.is_set():
                self.error_occurred.emit(f"Unexpected TTS error: {exc}")
        finally:
            producer_thread.join(timeout=2.0)
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            except Exception:
                pass

            if render_error and not self._stop_flag.is_set():
                self.error_occurred.emit(f"TTS render error: {render_error[0]}")

            if all_rendered_files and self._engine_ref is not None and not self._stop_flag.is_set():
                try:
                    self._engine_ref.store_wav_cache(self._text, all_rendered_files)
                    owns_files = False
                except Exception:
                    owns_files = True

            if owns_files:
                for f in all_rendered_files:
                    try:
                        if os.path.exists(f):
                            os.remove(f)
                    except Exception:
                        pass

            self.finished_speaking.emit()

    # ── Pause / resume — NOW SUPPORTED via pygame ─────────────────────────────

    def pause(self):
        self._pause_flag.set()

    def resume(self):
        self._pause_flag.clear()

    # ── Stop ──────────────────────────────────────────────────────────────────

    def stop(self):
        """
        Instantly stop playback. Non-blocking.
        All platforms now use pygame for playback, so we stop it directly.
        """
        self._stop_flag.set()
        self._pause_flag.clear()
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass


# ═════════════════════════════════════════════════════════════════════════════
# High-level TTSEngine
# ═════════════════════════════════════════════════════════════════════════════

class TTSEngine:
    """
    Manages one active worker at a time.
    Prefers EdgeTTS (neural, human-like). Falls back to pyttsx3.

    Audio cache
    -----------
    For offline mode (Pyttsx3Worker), rendered WAV files are cached by a
    hash of (text + voice_id + rate).  On restart with the same text the
    cached files are replayed instantly — no re-render needed.
    Cache holds at most 1 entry (the most recent text) to keep disk use low.
    """

    def __init__(self):
        self._worker: EdgeTTSWorker | Pyttsx3Worker | None = None
        self._stopping: bool = False   # True while a worker is being torn down

        # Offline audio cache — {cache_key: [wav_path, ...]}
        self._wav_cache: dict[str, list[str]] = {}
        self._wav_cache_key: str = ""

        # Global lock — prevents concurrent pyttsx3.init() calls which
        # cause segfaults on Linux (espeak is not thread-safe).
        self._pyttsx3_lock = threading.Lock()

        # Edge-TTS settings
        self._edge_voice    = "en-US-AriaNeural"
        self._edge_rate     = "+0%"
        self._volume        = 1.0
        self._force_offline = False
        self._active_lang   = "en"

        # pyttsx3 fallback settings
        self._rate        = 175
        self._voice_id: str | None = None
        self._pyttsx3_voices: list[dict] = []

        self._edge_available = self._check_edge_tts()
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

    def _use_edge(self) -> bool:
        return self._edge_available and not self._force_offline

    def set_forced_offline(self, offline: bool):
        self._force_offline = offline

    def supports_pause(self) -> bool:
        return True   # both EdgeTTSWorker and Pyttsx3Worker now use pygame

    # ── Language selection ────────────────────────────────────────────────────

    def set_language(self, lang: str) -> None:
        """
        Switch the active language. Resets the voice to the first native
        speaker available for that language.
        """
        self._active_lang = lang
        voices = self.get_voices()
        if voices:
            self._edge_voice = voices[0]["id"]

    def get_active_language(self) -> str:
        return self._active_lang

    # ── Voice discovery ───────────────────────────────────────────────────────

    def _load_pyttsx3_voices(self):
        """Load system TTS voices in a daemon thread so startup never blocks."""
        def _load():
            with self._pyttsx3_lock:   # serialize — espeak is not thread-safe
                try:
                    engine = pyttsx3.init()
                    raw = engine.getProperty("voices") or []
                    self._pyttsx3_voices = [{"id": v.id, "name": v.name} for v in raw]

                    if self._pyttsx3_voices and not self._voice_id:
                        for v in self._pyttsx3_voices:
                            vid = v["id"].lower()
                            vname = v["name"].lower()
                            if "en-us" in vid or "en_us" in vid or "english (us)" in vname:
                                self._voice_id = v["id"]
                                break
                        if not self._voice_id:
                            for v in self._pyttsx3_voices:
                                vid = v["id"].lower()
                                vname = v["name"].lower()
                                if "en" in vid or "english" in vname:
                                    self._voice_id = v["id"]
                                    break
                        if not self._voice_id and self._pyttsx3_voices:
                            self._voice_id = self._pyttsx3_voices[0]["id"]

                    engine.stop()
                    del engine
                except Exception:
                    self._pyttsx3_voices = []

        t = threading.Thread(target=_load, daemon=True, name="pyttsx3-voice-loader")
        t.start()

    def get_voices(self) -> list[dict]:
        """Return voices for the currently selected language (Edge) or all system voices (offline)."""
        if self._use_edge():
            return get_voices_for_lang(self._active_lang)
        return self._pyttsx3_voices

    # ── Playback ──────────────────────────────────────────────────────────────

    def _wav_key(self, text: str) -> str:
        """Cache key: hash of text + voice + rate so any change invalidates it."""
        import hashlib
        raw = f"{text}|{self._voice_id}|{self._rate}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _clear_wav_cache(self):
        """Delete cached WAV files from disk and clear the in-memory index."""
        for path in self._wav_cache.get(self._wav_cache_key, []):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
        self._wav_cache.clear()
        self._wav_cache_key = ""

    def __del__(self):
        """Clean up cached WAV files when the engine is garbage collected."""
        try:
            self._clear_wav_cache()
        except Exception:
            pass

    def get_cached_wavs(self, text: str) -> list[str] | None:
        """
        Return cached WAV file list if text matches the last render,
        and all files still exist on disk.  Returns None on any mismatch.
        """
        key = self._wav_key(text)
        if key != self._wav_cache_key:
            return None
        files = self._wav_cache.get(key, [])
        if not files:
            return None
        # Verify files still exist (could have been cleaned up externally)
        if all(os.path.exists(f) and os.path.getsize(f) > 64 for f in files):
            return files
        return None

    def store_wav_cache(self, text: str, wav_files: list[str]):
        """Called by Pyttsx3Worker after rendering to cache the WAV paths."""
        # Evict old cache first
        self._clear_wav_cache()
        key = self._wav_key(text)
        self._wav_cache[key] = list(wav_files)
        self._wav_cache_key = key

    def speak(self, text: str,
              on_preparing=None, on_start=None,
              on_finish=None, on_error=None,
              on_paused=None, on_resumed=None,
              on_word_highlight=None,
              session_path: str | None = None):
        # Guard: if we're already in the middle of a stop(), don't start a new
        # worker until the previous one is fully torn down.
        if self._stopping:
            return None

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
            # Check if we have cached WAV files for this exact text
            cached = self.get_cached_wavs(text)
            worker = Pyttsx3Worker(
                text,
                rate=self._rate,
                volume=self._volume,
                voice_id=self._voice_id,
                cached_wavs=cached,
                engine_ref=self,
                pyttsx3_lock=self._pyttsx3_lock,   # prevent concurrent espeak access
            )

        if on_preparing:      worker.preparing_speech.connect(on_preparing)
        if on_start:          worker.started_speaking.connect(on_start)
        if on_finish:         worker.finished_speaking.connect(on_finish)
        if on_error:          worker.error_occurred.connect(on_error)
        if on_paused:         worker.paused_speaking.connect(on_paused)
        if on_resumed:        worker.resumed_speaking.connect(on_resumed)
        if on_word_highlight and isinstance(worker, EdgeTTSWorker):
            worker.word_highlight.connect(on_word_highlight)

        self._worker = worker
        worker.start()
        return worker

    def stop(self):
        w = self._worker
        self._worker = None   # clear first so we know this worker is orphaned
        if w and w.isRunning():
            self._stopping = True
            # Disconnect all signals before stopping so queued finished_speaking
            # from the dying worker doesn't fire into the app after stop().
            try:
                w.finished_speaking.disconnect()
                w.error_occurred.disconnect()
                w.started_speaking.disconnect()
                w.preparing_speech.disconnect()
                w.paused_speaking.disconnect()
                w.resumed_speaking.disconnect()
            except Exception:
                pass
            w.stop()
            # Clear _stopping immediately — both SAPI5 (Windows) and pygame
            # (Linux/macOS) stop synchronously. The worker thread may still be
            # winding down but signals are already disconnected so it's safe
            # to start a new worker right away.
            self._stopping = False
        else:
            self._stopping = False

    def _clear_stopping(self):
        self._stopping = False

    def pause(self):
        if self._worker and self._worker.isRunning():
            self._worker.pause()

    def resume(self):
        if self._worker and self._worker.isRunning():
            self._worker.resume()

    def is_speaking(self) -> bool:
        """True only when actively playing audio — False when paused or idle."""
        return bool(self._worker and self._worker.isRunning()) and not self.is_paused()

    def is_paused(self) -> bool:
        if isinstance(self._worker, EdgeTTSWorker):
            return self._worker._pause_event.is_set()
        if isinstance(self._worker, Pyttsx3Worker):
            return self._worker._pause_flag.is_set()
        return False

    # ── Settings ──────────────────────────────────────────────────────────────

    def set_voice(self, voice_id: str | None):
        if self._edge_available:
            if voice_id:
                valid_ids = {v["id"] for v in EDGE_TTS_VOICES_ALL}
                if voice_id in valid_ids:
                    self._edge_voice = voice_id
                else:
                    print(
                        f"[Veaja] Warning: unknown voice id '{voice_id}' — "
                        f"keeping current voice '{self._edge_voice}'.",
                        file=sys.stderr,
                    )
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

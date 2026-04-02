"""
Manages the last 3 reading sessions as MP3 files.
Saved to ~/.veaja/audio/ — oldest deleted automatically when a 4th is added.
"""

import json
import os
import time
from pathlib import Path

AUDIO_DIR   = Path.home() / ".veaja" / "audio"
INDEX_FILE  = AUDIO_DIR / "index.json"
MAX_SESSIONS = 3


class AudioHistory:
    def __init__(self):
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        self._sessions: list[str] = []   # ordered list of absolute path strings
        self._load_index()

    # ── Public API ────────────────────────────────────────────────────────────

    def next_session_path(self) -> str:
        """
        Reserve a new session file path (does not create the file).
        Prunes oldest sessions so the queue stays at MAX_SESSIONS.
        Returns the absolute path string for the new session MP3.
        """
        name = f"session_{int(time.time())}.mp3"
        path = str(AUDIO_DIR / name)

        # Prune: if already at max, remove oldest
        while len(self._sessions) >= MAX_SESSIONS:
            oldest = self._sessions.pop(0)
            try:
                os.remove(oldest)
            except OSError:
                pass

        self._sessions.append(path)
        self._save_index()
        return path

    def get_sessions(self) -> list[str]:
        """Return current session paths, oldest first."""
        return list(self._sessions)

    def get_latest(self) -> str | None:
        """Return the most recent session path, or None if empty."""
        return self._sessions[-1] if self._sessions else None

    # ── Index persistence ─────────────────────────────────────────────────────

    def _load_index(self):
        try:
            with open(INDEX_FILE, encoding="utf-8") as f:
                paths: list[str] = json.load(f)
            # Only keep paths that still exist on disk
            self._sessions = [p for p in paths if os.path.exists(p)]
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            self._sessions = []

    def _save_index(self):
        try:
            with open(INDEX_FILE, "w", encoding="utf-8") as f:
                json.dump(self._sessions, f, indent=2)
        except OSError:
            pass

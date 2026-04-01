"""
User profile: display name, avatar path, and preferences.
Stored at ~/.veaja/profile.json
"""

import json
import os
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

PROFILE_DIR  = Path.home() / ".veaja"
PROFILE_PATH = PROFILE_DIR / "profile.json"

DEFAULT_PROFILE: dict = {
    "version":        1,
    "app_name":       "Veaja",
    "logo_path":      None,    # null = use bundled logo
    "terms_accepted": False,
}


class ProfileManager(QObject):
    """Loads, saves, and emits profile changes."""

    profile_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._profile: dict = dict(DEFAULT_PROFILE)

    # ── Public API ────────────────────────────────────────────────────────────

    def load(self) -> dict:
        """Read profile from disk. Missing / invalid keys fall back to defaults."""
        try:
            with open(PROFILE_PATH, encoding="utf-8") as f:
                data = json.load(f)
            # Merge: defaults first, then saved values (forward-compatible)
            self._profile = {**DEFAULT_PROFILE, **data}
            # Validate logo_path — ignore if the file was deleted
            if self._profile["logo_path"] and \
               not os.path.exists(self._profile["logo_path"]):
                self._profile["logo_path"] = None
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            self._profile = dict(DEFAULT_PROFILE)
        return dict(self._profile)

    def get(self) -> dict:
        """Return current in-memory profile (call load() first)."""
        return dict(self._profile)

    def save(self, profile: dict):
        """Write profile to disk and emit profile_changed."""
        self._profile = {**DEFAULT_PROFILE, **profile}
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        with open(PROFILE_PATH, "w", encoding="utf-8") as f:
            json.dump(self._profile, f, indent=2, ensure_ascii=False)
        self.profile_changed.emit(dict(self._profile))

    def reset(self):
        """Reset to factory defaults and save."""
        self.save(dict(DEFAULT_PROFILE))

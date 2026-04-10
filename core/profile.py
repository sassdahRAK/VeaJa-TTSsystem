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

# Fix #5: bump this when adding new required fields so _migrate() can upgrade
# old profiles automatically without the user losing their settings.
CURRENT_PROFILE_VERSION = 1

DEFAULT_PROFILE: dict = {
    "version":         1,
    "app_name":        "Veaja",
    "logo_path":                 None,   # null = use bundled logo
    "overlay_use_profile_photo": False, # use custom photo as overlay logo
    "terms_accepted":  False,
    "highlight_color": "#FFD60A",    # word-highlight colour (yellow)
    "dark_mode":       None,         # None = follow system; True/False = user override
    # Voice settings (persisted by Voice Settings → Save)
    "speed":           175,          # TTS rate, range 50–400
    "overlay_shape":     "rectangle",  # "circle" | "rectangle"
    "overlay_anim_spin": True,         # spin logo while reading
    "overlay_anim_glow": False,        # glow border pulse with word timing
    "voice_index":       0,            # index into the current voice list
    "volume":          1.0,          # 0.0–1.0
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
        # Guarantee the directory exists before trying to open the file inside it.
        # On a fresh install (or if the user manually deleted ~/.veaja), the open()
        # below would raise FileNotFoundError without this guard.
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)

        try:
            with open(PROFILE_PATH, encoding="utf-8") as f:
                data = json.load(f)
            # Merge: defaults first, then saved values (forward-compatible)
            merged = {**DEFAULT_PROFILE, **data}

            # Fix #4 — schema validation: strip any keys that are not in
            # DEFAULT_PROFILE so stale or hand-edited fields don't accumulate.
            valid_keys = set(DEFAULT_PROFILE.keys())
            merged = {k: v for k, v in merged.items() if k in valid_keys}

            # Fix #5 — run migration so old profiles gain new required fields.
            self._profile = self._migrate(merged)

            # Validate logo_path:
            #   • Must be a str (guard against hand-edited JSON with a number/bool)
            #   • File must still exist on disk
            logo = self._profile.get("logo_path")
            if not isinstance(logo, str) or not os.path.exists(logo):
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

    # ── Migration (Fix #5) ────────────────────────────────────────────────────

    @staticmethod
    def _migrate(data: dict) -> dict:
        """Upgrade a saved profile to CURRENT_PROFILE_VERSION in-place.

        Add a new block here whenever DEFAULT_PROFILE gains a required field
        so that users upgrading from an older release don't lose their settings.

        Example for a future v2 upgrade:
            if v < 2:
                data.setdefault("new_field", DEFAULT_PROFILE["new_field"])
        """
        v = data.get("version", 0)
        if v < CURRENT_PROFILE_VERSION:
            # placeholder — no structural changes between v0 and v1
            data["version"] = CURRENT_PROFILE_VERSION
        return data

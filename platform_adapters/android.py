"""
platform_adapters.android
=========================
Android adapter — for future BeeWare Toga or Kivy deployment.

The UI layer on Android will be a separate Toga/Kivy app that shares
the core/ and services/ modules.  This adapter bridges the gap.

Status: STUB — not yet wired into the main app.
        Implement when targeting Android via BeeWare.
"""

from platform_adapters.base import BasePlatform


class AndroidPlatform(BasePlatform):
    @property
    def name(self) -> str:
        return "Android"

    @property
    def supports_system_tray(self) -> bool:
        return False   # Android has no system tray

    @property
    def supports_global_hotkeys(self) -> bool:
        return False   # Android sandboxing prevents global key capture

    @property
    def supports_clipboard_monitor(self) -> bool:
        # Android 10+ restricts background clipboard access
        return False

    @property
    def supports_pause_resume(self) -> bool:
        return True   # Android AudioManager supports pause/resume

    def preferred_tts_backends(self) -> list[str]:
        # Android has a built-in TTS engine (android.speech.tts)
        return ["android_tts", "edge_tts"]

    def get_config_dir(self) -> str:
        # BeeWare provides app.paths.data
        try:
            import toga
            return str(toga.App.app.paths.data)
        except Exception:
            from pathlib import Path
            return str(Path.home() / ".veaja")

    def read_clipboard(self) -> str:
        try:
            # BeeWare clipboard access
            import toga
            return toga.App.app.clipboard.get_text() or ""
        except Exception:
            return ""

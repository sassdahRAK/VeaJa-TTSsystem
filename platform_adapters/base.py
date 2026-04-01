"""
platform_adapters.base
======================
Abstract base class for all platform adapters.

Every platform MUST implement (or inherit the safe no-op) for each method.
New capabilities should be added here first, then overridden per-platform.

Cross-platform targets
----------------------
  Desktop : Windows (x64, ARM64), macOS (Intel, M-series), Linux x64/ARM
  Mobile  : Android (API 21+), iOS 15+ — via BeeWare Toga or Kivy
  Tablet  : iPadOS, Android tablets — same mobile adapters
"""


class BasePlatform:
    """
    Safe no-op base.  Subclasses override only what the platform supports.
    """

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        """Human-readable platform name."""
        return "Unknown"

    @property
    def supports_system_tray(self) -> bool:
        """True on Windows / macOS / Linux desktop."""
        return False

    @property
    def supports_global_hotkeys(self) -> bool:
        """True when pynput / platform hotkeys are available."""
        return False

    @property
    def supports_clipboard_monitor(self) -> bool:
        """True on desktop; False on sandboxed mobile."""
        return False

    @property
    def supports_pause_resume(self) -> bool:
        """True when the audio backend supports pause/resume (pygame)."""
        return False

    # ── System integration ────────────────────────────────────────────────────

    def open_url(self, url: str) -> None:
        """Open URL in system browser."""
        import webbrowser
        try:
            webbrowser.open(url)
        except Exception:
            pass

    def show_notification(self, title: str, body: str) -> None:
        """Show a system notification. No-op on unsupported platforms."""

    def get_config_dir(self) -> str:
        """Return the platform-appropriate config directory."""
        import os
        from pathlib import Path
        return str(Path.home() / ".veaja")

    def get_audio_dir(self) -> str:
        """Return the platform-appropriate audio storage directory."""
        import os
        from pathlib import Path
        return str(Path.home() / ".veaja" / "audio")

    # ── TTS backend selection ─────────────────────────────────────────────────

    def preferred_tts_backends(self) -> list[str]:
        """
        Ordered list of preferred TTS backends for this platform.
        First available backend in the list wins.
        """
        return ["edge_tts", "pyttsx3"]

    # ── Clipboard ─────────────────────────────────────────────────────────────

    def read_clipboard(self) -> str:
        """Return current clipboard text. Never raises."""
        return ""

    # ── Accessibility / selection ─────────────────────────────────────────────

    def simulate_copy(self) -> None:
        """
        Simulate Ctrl+C / Cmd+C to copy the current selection.
        Used by Ctrl+R hotkey to grab selected text.
        """

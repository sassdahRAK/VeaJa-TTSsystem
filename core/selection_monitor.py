"""
Cross-platform text-selection / clipboard monitor.

Strategy (no root/accessibility required):
  1. Watch QApplication.clipboard() for dataChanged.
  2. Optionally watch for Cmd+C (Mac) / Ctrl+C (Win/Linux) via pynput
     to fire even when clipboard content didn't technically change.

The controller connects to `text_ready` to get new text.
"""

import platform
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication


class SelectionMonitor(QObject):
    """Emits `text_ready(str)` whenever new text appears on the clipboard."""

    text_ready = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_text: str = ""
        self._clipboard = QApplication.clipboard()
        self._clipboard.dataChanged.connect(self._on_clipboard_change)

        # pynput hotkey listener (optional – degrades gracefully)
        self._pynput_listener = None
        self._start_pynput()

    # ------------------------------------------------------------------ #
    # Qt clipboard watcher
    # ------------------------------------------------------------------ #

    def _on_clipboard_change(self):
        text = self._clipboard.text().strip()
        if text and text != self._last_text:
            self._last_text = text
            self.text_ready.emit(text)

    # ------------------------------------------------------------------ #
    # pynput fallback: detect Cmd+C / Ctrl+C even when text unchanged
    # ------------------------------------------------------------------ #

    def _start_pynput(self):
        try:
            from pynput import keyboard

            system = platform.system()
            if system == "Darwin":
                hotkey_combo = "<cmd>+c"
            else:
                hotkey_combo = "<ctrl>+c"

            def _on_copy():
                # Small delay so clipboard is populated before we read it
                QTimer.singleShot(80, self._force_check)

            self._pynput_listener = keyboard.GlobalHotKeys(
                {hotkey_combo: _on_copy}
            )
            self._pynput_listener.daemon = True
            self._pynput_listener.start()
        except Exception:
            # pynput not available or no accessibility permission — clipboard
            # watcher above is still active.
            pass

    def _force_check(self):
        """Re-read clipboard even if content didn't change signal."""
        text = self._clipboard.text().strip()
        if text and text != self._last_text:
            self._last_text = text
            self.text_ready.emit(text)

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def stop(self):
        if self._pynput_listener:
            try:
                self._pynput_listener.stop()
            except Exception:
                pass

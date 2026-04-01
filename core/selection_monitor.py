"""
Cross-platform text-selection / clipboard monitor.

Strategy (no root/accessibility required):
  1. Watch QApplication.clipboard() for dataChanged.
  2. Watch for Cmd+C (Mac) / Ctrl+C (Win/Linux) via pynput to fire even when
     clipboard content didn't technically change (user copies the same text again).

Thread-safety note
------------------
pynput callbacks fire on a C-level thread that has no Qt event loop.
Calling ANY Qt API (QTimer, QClipboard, signals on QObject) directly from that
thread causes undefined behaviour / segfaults.

The fix: emit an internal pyqtSignal from the pynput thread.
Qt6 queues the delivery to the receiver's thread automatically, so the actual
clipboard read happens safely on the Qt main thread.

Debounce note
-------------
Without debouncing, rapid Cmd+C presses (or macOS firing dataChanged multiple
times for one copy operation) caused the overlay and main window to update
many times in quick succession, producing QTextCursor position errors.
A 250 ms cooldown window prevents this without losing any real events.
"""

import time
import platform
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer, Qt
from PyQt6.QtWidgets import QApplication

# Minimum milliseconds between two text_ready emissions.
_DEBOUNCE_MS = 250


class SelectionMonitor(QObject):
    """Emits `text_ready(str)` whenever new text appears on the clipboard.
    Emits `read_clipboard_hotkey()` when Ctrl+R / Cmd+R is pressed."""

    text_ready            = pyqtSignal(str)
    read_clipboard_hotkey = pyqtSignal()   # Ctrl+R → read current clipboard text

    # Internal thread-safe bridge signals from pynput thread.
    _pynput_copy_detected = pyqtSignal()
    _pynput_read_detected = pyqtSignal()   # bridge for Ctrl+R

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_text: str = ""
        self._last_emit_time: float = 0.0   # monotonic seconds of last emission

        self._clipboard = QApplication.clipboard()
        self._clipboard.dataChanged.connect(self._on_clipboard_change)

        # Wire the pynput bridge: QueuedConnection guarantees the slot
        # runs on the Qt main thread regardless of which thread emits.
        self._pynput_copy_detected.connect(
            self._schedule_force_check,
            Qt.ConnectionType.QueuedConnection,
        )
        self._pynput_read_detected.connect(
            self._on_read_hotkey_fired,
            Qt.ConnectionType.QueuedConnection,
        )

        self._pynput_listener = None
        self._start_pynput()

    # ------------------------------------------------------------------ #
    # Qt clipboard watcher  (already on Qt main thread)
    # ------------------------------------------------------------------ #

    @pyqtSlot()
    def _on_clipboard_change(self):
        text = self._clipboard.text().strip()
        if text and text != self._last_text:
            self._emit_if_allowed(text)

    # ------------------------------------------------------------------ #
    # pynput fallback — runs on pynput thread, must not touch Qt directly
    # ------------------------------------------------------------------ #

    def _start_pynput(self):
        try:
            from pynput import keyboard

            is_mac   = platform.system() == "Darwin"
            copy_key = "<cmd>+c" if is_mac else "<ctrl>+c"
            read_key = "<cmd>+r" if is_mac else "<ctrl>+r"

            _last_copy_time: list[float] = [0.0]
            _last_read_time: list[float] = [0.0]

            def _on_copy():
                now = time.monotonic()
                if now - _last_copy_time[0] < _DEBOUNCE_MS / 1000:
                    return
                _last_copy_time[0] = now
                self._pynput_copy_detected.emit()   # thread-safe ✓

            def _on_read():
                now = time.monotonic()
                if now - _last_read_time[0] < _DEBOUNCE_MS / 1000:
                    return
                _last_read_time[0] = now

                # Step 1: simulate Ctrl+C to copy the user's current selection.
                # Ctrl is still held (user pressed Ctrl+R), so we just press C.
                try:
                    from pynput.keyboard import Controller as _KbCtrl, Key
                    _kbd = _KbCtrl()
                    # Release any lingering modifiers first
                    for _k in (Key.ctrl, Key.ctrl_l, Key.ctrl_r):
                        try:
                            _kbd.release(_k)
                        except Exception:
                            pass
                    time.sleep(0.04)
                    # Fresh Ctrl+C
                    _kbd.press(Key.ctrl_l)
                    _kbd.press('c')
                    _kbd.release('c')
                    _kbd.release(Key.ctrl_l)
                    time.sleep(0.15)   # wait for OS to write clipboard
                except Exception:
                    pass

                self._pynput_read_detected.emit()   # thread-safe ✓

            self._pynput_listener = keyboard.GlobalHotKeys({
                copy_key: _on_copy,
                read_key: _on_read,
            })
            self._pynput_listener.daemon = True
            self._pynput_listener.start()
        except Exception:
            # pynput unavailable or no Accessibility permission.
            # The dataChanged watcher above is still active as fallback.
            pass

    # ------------------------------------------------------------------ #
    # Slots — these always run on the Qt main thread
    # ------------------------------------------------------------------ #

    @pyqtSlot()
    def _schedule_force_check(self):
        """
        Received on the Qt main thread from the pynput bridge signal.
        Wait 80 ms so the OS has time to write the new text to the clipboard
        before we read it, then do the check.
        """
        QTimer.singleShot(80, self._force_check)    # safe: Qt thread ✓

    @pyqtSlot()
    def _on_read_hotkey_fired(self):
        """Received on Qt main thread from the Ctrl+R pynput bridge."""
        QTimer.singleShot(80, self._emit_read_hotkey)

    @pyqtSlot()
    def _emit_read_hotkey(self):
        """Read clipboard and fire the public read_clipboard_hotkey signal."""
        text = self._clipboard.text().strip()
        if text:
            self.read_clipboard_hotkey.emit()

    @pyqtSlot()
    def _force_check(self):
        """Re-read clipboard even if the dataChanged signal did not fire."""
        text = self._clipboard.text().strip()
        if text and text != self._last_text:
            self._emit_if_allowed(text)

    # ------------------------------------------------------------------ #
    # Debounced emit helper
    # ------------------------------------------------------------------ #

    def _emit_if_allowed(self, text: str):
        """
        Emit text_ready only if enough time has passed since the last emission.

        This prevents QTextCursor position errors and UI flicker that occurred
        when dataChanged fired multiple times for a single copy operation, or
        when both the Qt clipboard watcher and the pynput path triggered for
        the same Cmd+C press.
        """
        now = time.monotonic()
        if now - self._last_emit_time < _DEBOUNCE_MS / 1000:
            # Too soon — update last_text so we don't re-emit stale text,
            # but skip the signal to avoid rapid-fire UI updates.
            self._last_text = text
            return
        self._last_text = text
        self._last_emit_time = now
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

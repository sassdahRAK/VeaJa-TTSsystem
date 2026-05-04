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

import sys
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
        self._shutting_down: bool = False   # Fix #6: block signals during teardown

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
        # Guard: skip immediately if clipboard contains non-text data (image, file, etc.)
        # Accessing image/file data on the main thread can cause a freeze.
        cb = self._clipboard
        mime = cb.mimeData()
        if mime is None or not mime.hasText():
            return
        text = cb.text().strip()
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
                if self._shutting_down:             # Fix #6: skip if tearing down
                    return
                now = time.monotonic()
                if now - _last_copy_time[0] < _DEBOUNCE_MS / 1000:
                    return
                _last_copy_time[0] = now
                self._pynput_copy_detected.emit()   # thread-safe ✓

            def _on_read():
                if self._shutting_down:             # Fix #6: skip if tearing down
                    return
                now = time.monotonic()
                if now - _last_read_time[0] < _DEBOUNCE_MS / 1000:
                    return
                _last_read_time[0] = now

                # Design: Ctrl+R means "read what is currently on the clipboard".
                #
                # Previous versions simulated a Ctrl+C keystroke here to copy
                # the user's current selection before reading.  That approach
                # caused a critical crash: when the VSCode (or any) terminal had
                # focus, the simulated Ctrl+C was delivered to the terminal as
                # SIGINT, raising KeyboardInterrupt in the Python process and
                # killing the app.
                #
                # The safe workflow is:
                #   1. Select text in any app
                #   2. Press Ctrl+C  (copies to clipboard; overlay pill appears)
                #   3. Press Ctrl+R  (reads what is now on the clipboard)
                #
                # No keystroke simulation needed — just signal the Qt thread.
                self._pynput_read_detected.emit()   # thread-safe ✓

            self._pynput_listener = keyboard.GlobalHotKeys({
                copy_key: _on_copy,
                read_key: _on_read,
            })
            self._pynput_listener.daemon = True
            self._pynput_listener.start()
        except Exception as exc:
            # pynput unavailable or no Accessibility permission.
            # The Qt dataChanged clipboard watcher above is still active as fallback,
            # but Ctrl+C / Ctrl+R global hotkeys will not work.
            print(
                f"[Veaja] Warning: global hotkey listener unavailable: {exc}\n"
                "         Ctrl+C copy detection via Qt clipboard is still active.\n"
                "         macOS: grant Accessibility access in System Settings → Privacy.",
                file=sys.stderr,
            )

    # ------------------------------------------------------------------ #
    # Slots — these always run on the Qt main thread
    # ------------------------------------------------------------------ #

    @pyqtSlot()
    def _schedule_force_check(self):
        """
        Received on the Qt main thread from the pynput bridge signal.

        Large text selections (multiple paragraphs) take longer for the OS
        to write to the clipboard. We use a two-stage check:
          1. After 150ms  — catches most normal copies
          2. After 400ms  — catches large selections that took longer to write

        The second check is a no-op if the text didn't change.
        """
        QTimer.singleShot(150, self._force_check)    # fast check
        QTimer.singleShot(400, self._force_check)    # safety net for large selections

    @pyqtSlot()
    def _on_read_hotkey_fired(self):
        """Received on Qt main thread from the Ctrl+R pynput bridge.

        Wrapped in BaseException to guard against KeyboardInterrupt leaking
        in from the pynput thread (e.g. a stray SIGINT) and crashing the slot.
        """
        try:
            QTimer.singleShot(80, self._emit_read_hotkey)
        except BaseException as exc:
            print(f"[Veaja] Warning: _on_read_hotkey_fired caught: {exc}",
                  file=sys.stderr)

    @pyqtSlot()
    def _emit_read_hotkey(self):
        """Read clipboard and fire the public read_clipboard_hotkey signal."""
        # Guard: skip if clipboard has no text (e.g. image was copied)
        mime = self._clipboard.mimeData()
        if mime is None or not mime.hasText():
            return
        text = self._clipboard.text().strip()
        if text:
            self.read_clipboard_hotkey.emit()
            QTimer.singleShot(500, self._clipboard.clear)

    @pyqtSlot()
    def _force_check(self):
        """Re-read clipboard even if the dataChanged signal did not fire.

        Also handles the case where the clipboard was partially written on the
        first check (large selections) — if the new text is longer than what
        we last emitted, emit again with the full text.
        """
        mime = self._clipboard.mimeData()
        if mime is None or not mime.hasText():
            return
        text = self._clipboard.text().strip()
        if not text:
            return
        # Emit if: new text, OR the text grew (clipboard was partially written before)
        if text != self._last_text or len(text) > len(self._last_text):
            self._emit_if_allowed(text)

    # ------------------------------------------------------------------ #
    # Debounced emit helper
    # ------------------------------------------------------------------ #

    def _emit_if_allowed(self, text: str):
        """
        Emit text_ready only if enough time has passed since the last emission,
        OR if the new text is longer than what was last emitted (large selection
        that was partially written to clipboard on the first check).
        """
        now = time.monotonic()
        text_grew = len(text) > len(self._last_text)
        too_soon  = (now - self._last_emit_time) < _DEBOUNCE_MS / 1000

        if too_soon and not text_grew:
            # Too soon and text didn't grow — skip to avoid rapid-fire UI updates
            self._last_text = text
            return

        self._last_text = text
        self._last_emit_time = now
        self.text_ready.emit(text)

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def stop(self):
        self._shutting_down = True          # Fix #6: block new signals before stopping
        if self._pynput_listener:
            try:
                self._pynput_listener.stop()
                # Give the daemon thread a moment to finish shutting down
                # before the process exits to avoid pynput teardown errors.
                time.sleep(0.05)
            except Exception:
                pass

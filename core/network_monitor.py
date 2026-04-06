"""
NetworkMonitor — periodically checks internet connectivity in a background
thread and emits connectivity_changed(bool) on the Qt main thread whenever
the state flips.  Uses a raw socket to 8.8.8.8:53 (Google DNS) which works
on any OS without requiring any extra packages.
"""

import socket
import threading

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


_CHECK_HOST = "8.8.8.8"
_CHECK_PORT = 53
_CHECK_TIMEOUT_S = 2


class NetworkMonitor(QObject):
    """Emits connectivity_changed(True) when internet comes up,
    connectivity_changed(False) when it goes down."""

    connectivity_changed = pyqtSignal(bool)   # True = online, False = offline

    def __init__(self, parent=None, interval_ms: int = 10_000):
        super().__init__(parent)
        self._online: bool | None = None      # unknown until first check
        self._lock = threading.Lock()

        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._schedule_check)
        self._timer.start()

        # Run the first check immediately so the UI is correct at startup
        self._schedule_check()

    # ------------------------------------------------------------------ #

    def is_online(self) -> bool:
        with self._lock:
            return bool(self._online)

    # ------------------------------------------------------------------ #

    def _schedule_check(self):
        threading.Thread(target=self._do_check, daemon=True).start()

    def _do_check(self):
        """Runs in a worker thread — never touches Qt objects directly."""
        try:
            socket.create_connection(
                (_CHECK_HOST, _CHECK_PORT), timeout=_CHECK_TIMEOUT_S
            ).close()
            is_online = True
        except OSError:
            is_online = False

        with self._lock:
            if is_online == self._online:
                return          # no change — nothing to emit
            self._online = is_online

        # Signal is emitted cross-thread; Qt's queued connection delivers it
        # safely on the main thread.
        self.connectivity_changed.emit(is_online)

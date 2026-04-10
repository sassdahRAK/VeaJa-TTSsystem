"""
NetworkMonitor — periodically checks internet connectivity in a background
thread and emits connectivity_changed(bool) on the Qt main thread whenever
the state flips.

Probe strategy
--------------
Multiple well-known DNS hosts are tried in order. The system is declared
ONLINE if ANY host responds. This prevents false "offline" reports on
networks that block Google DNS (corporate, government, some countries).

  8.8.8.8  — Google Public DNS
  1.1.1.1  — Cloudflare DNS
  9.9.9.9  — Quad9 DNS

No extra packages required — raw sockets only.
"""

import socket
import threading

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from config.settings import NETWORK_CHECK_TIMEOUT_S


# Ordered list of (host, port) probes. Declared ONLINE if any one succeeds.
_CHECK_HOSTS: list[tuple[str, int]] = [
    ("8.8.8.8", 53),   # Google DNS
    ("1.1.1.1", 53),   # Cloudflare DNS
    ("9.9.9.9", 53),   # Quad9 DNS
]


class NetworkMonitor(QObject):
    """Emits connectivity_changed(True) when internet comes up,
    connectivity_changed(False) when it goes down."""

    connectivity_changed = pyqtSignal(bool)   # True = online, False = offline

    def __init__(self, parent=None, interval_ms: int = 10_000):
        super().__init__(parent)
        self._online: bool | None = None      # unknown until first check
        self._lock = threading.Lock()
        self._check_running = False           # guard against overlapping probe threads

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
        with self._lock:
            if self._check_running:
                return          # previous probe still in flight — skip
            self._check_running = True
        threading.Thread(target=self._do_check, daemon=True).start()

    def _do_check(self):
        """Runs in a worker thread — never touches Qt objects directly.

        Tries each host in _CHECK_HOSTS in sequence and stops at the first
        successful connection. Reports offline only if ALL probes fail.
        """
        try:
            is_online = False
            for host, port in _CHECK_HOSTS:
                try:
                    socket.create_connection(
                        (host, port), timeout=NETWORK_CHECK_TIMEOUT_S
                    ).close()
                    is_online = True
                    break   # one success is enough
                except OSError:
                    continue   # try the next host

            with self._lock:
                if is_online == self._online:
                    return          # no change — nothing to emit
                self._online = is_online

            # Signal is emitted cross-thread; Qt's queued connection delivers it
            # safely on the main thread.
            self.connectivity_changed.emit(is_online)
        finally:
            with self._lock:
                self._check_running = False

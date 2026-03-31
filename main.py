"""
Veaja — cross-platform TTS desktop app.
Entry point and composition root.

WindowManager rules (wired here, in main):
  • Overlay appears  →  main window hides to tray
  • Overlay hides    →  main window comes back
  • Tray click       →  always show main window

Run:
    python3 main.py

macOS first run — grant Accessibility access when prompted:
    System Settings → Privacy & Security → Accessibility → add Terminal / Python
"""

import sys
import os
import platform

# ── Ensure project root is importable ───────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── Qt high-DPI (must be set before QApplication) ───────────────────────────
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from gui.splash_screen import SplashScreen
from services.app_controller import AppController
from services.window_manager import WindowManager


# ── App-level configuration ──────────────────────────────────────────────────

def _configure_app(app: QApplication) -> None:
    app.setApplicationName("Veaja")
    app.setApplicationDisplayName("Veaja")
    app.setOrganizationName("Veaja")
    app.setOrganizationDomain("veaja.app")
    

    system = platform.system()
    if system == "Darwin":
        app.setFont(QFont("SF Pro Text", 13))
        # Keep running in tray even when all windows are closed
        app.setQuitOnLastWindowClosed(False)
    elif system == "Windows":
        app.setFont(QFont("Segoe UI", 10))
    else:
        app.setFont(QFont("Ubuntu", 10))


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    _configure_app(app)

    # ── 1. Splash screen ─────────────────────────────────────────────────
    splash = SplashScreen()
    splash.show()
    app.processEvents()          # paint splash immediately before heavy init

    # ── 2. Build all app components ──────────────────────────────────────
    #    AppController creates: TTSEngine, MainWindow, OverlayWidget,
    #                           TrayIcon, SelectionMonitor, WindowManager
    controller = AppController(app)

    # ── 3. WindowManager — explicit reference so the rule is readable here
    #
    #    overlay shown  →  main window hides   (live in tray)
    #    overlay hidden →  main window returns
    #    tray click     →  always show main
    #
    wm: WindowManager = controller.window_manager

    # ── 4. Wire splash finish → show main window via WindowManager ───────
    splash.finished.connect(wm.show_main)
    splash.start_timer(delay_ms=2500)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

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

    # ── 1. Splash screen — read saved theme before building anything ─────
    _saved_dark: bool | None = None
    try:
        import json
        from core.profile import PROFILE_PATH
        with open(PROFILE_PATH, encoding="utf-8") as _f:
            _saved_dark = json.load(_f).get("dark_mode")
        if not isinstance(_saved_dark, bool):
            _saved_dark = None
    except Exception:
        pass

    splash = SplashScreen(saved_dark=_saved_dark)
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

    # ── 4. Wire splash finish → start app (loads profile, shows terms if new) ──
    splash.finished.connect(controller.start)
    splash.start_timer(delay_ms=2500)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

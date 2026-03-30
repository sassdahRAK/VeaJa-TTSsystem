"""
Veaja — cross-platform TTS desktop app.
Entry point: shows splash screen, then opens main window.

Run:
    python main.py

macOS first run — grant Accessibility access in:
    System Settings → Privacy & Security → Accessibility → add your terminal / Python
"""

import sys
import os
import platform

# ── Ensure project root is on sys.path ──────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── Qt high-DPI (must be set before QApplication) ───────────────────────────
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QCoreApplication
from PyQt6.QtGui import QFont

from gui.splash_screen import SplashScreen
from services.app_controller import AppController


def _configure_app(app: QApplication):
    app.setApplicationName("Veaja")
    app.setApplicationDisplayName("Veaja")
    app.setOrganizationName("Veaja")
    app.setOrganizationDomain("veaja.app")

    # Use system font on each platform
    system = platform.system()
    if system == "Darwin":
        app.setFont(QFont("SF Pro Text", 13))
    elif system == "Windows":
        app.setFont(QFont("Segoe UI", 10))
    else:
        app.setFont(QFont("Ubuntu", 10))


def main():
    # Enable high-DPI before creating QApplication
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    _configure_app(app)

    # ── Splash screen ────────────────────────────────────────────────────
    splash = SplashScreen()
    splash.show()
    app.processEvents()   # make splash paint immediately

    # ── App controller (builds all components) ───────────────────────────
    controller = AppController(app)

    # ── Wire splash → main window ────────────────────────────────────────
    splash.finished.connect(controller.start)
    splash.start_timer(delay_ms=2500)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

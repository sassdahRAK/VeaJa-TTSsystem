"""
Splash screen shown at launch.
Fades in on show, holds, then fades out before emitting `finished`.
Theme follows the user's saved preference (dark_mode in profile.json).
"""

import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPalette, QPixmap

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")

# Timing
_HOLD_MS = 2800
_FADE_MS = 480


def _system_is_dark() -> bool:
    palette = QPalette()
    return palette.color(QPalette.ColorRole.Window).lightness() < 128


class SplashScreen(QWidget):
    finished = pyqtSignal()

    def __init__(self, saved_dark: bool | None = None):
        super().__init__()
        # Use saved preference; fall back to system detection
        self._dark = saved_dark if isinstance(saved_dark, bool) else _system_is_dark()
        self._init_ui()
        self._init_animations()
        self.setWindowOpacity(0.0)

    # ------------------------------------------------------------------ #
    # Build UI
    # ------------------------------------------------------------------ #

    def _init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(860, 540)
        self._center()

        # Pure flat background — no border, no radius, matching role model
        bg         = "#000000" if self._dark else "#ffffff"
        name_color = "#cccccc" if self._dark else "#555555"

        self.setStyleSheet(f"background-color: {bg};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Centre block ──────────────────────────────────────────────────
        centre = QVBoxLayout()
        centre.setAlignment(Qt.AlignmentFlag.AlignCenter)
        centre.setSpacing(0)

        # Logo — large, no box frame, floats directly on background
        png_name = "logo_light.png" if self._dark else "logo_dark.png"
        png_path = os.path.join(ASSETS, png_name)
        self.logo = QLabel()
        self.logo.setFixedSize(320, 320)
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo.setStyleSheet("background: transparent; border: none;")
        if os.path.exists(png_path):
            px = QPixmap(png_path).scaled(
                320, 320,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.logo.setPixmap(px)
        else:
            self.logo.setText("V")
            self.logo.setStyleSheet(
                f"font-size: 120px; font-weight: bold; color: {name_color};"
                f" background: transparent; border: none;"
            )
        centre.addWidget(self.logo, 0, Qt.AlignmentFlag.AlignHCenter)
        centre.addSpacing(32)

        # App name — simple, light weight, muted colour like role model
        name_lbl = QLabel("Veaja")
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setStyleSheet(
            f"color: {name_color}; font-size: 22px;"
            f" font-weight: 300; letter-spacing: 6px;"
            f" background: transparent; border: none;"
        )
        centre.addWidget(name_lbl, 0, Qt.AlignmentFlag.AlignHCenter)

        root.addStretch(2)
        root.addLayout(centre)
        root.addStretch(3)

    # ------------------------------------------------------------------ #
    # Animations
    # ------------------------------------------------------------------ #

    def _init_animations(self):
        self._fade_in = QPropertyAnimation(self, b"windowOpacity")
        self._fade_in.setDuration(_FADE_MS)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._fade_out = QPropertyAnimation(self, b"windowOpacity")
        self._fade_out.setDuration(_FADE_MS)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out.finished.connect(self._on_fade_done)

    def start_timer(self, delay_ms: int = _HOLD_MS):
        """Fade in, hold, then fade out."""
        hold = max(delay_ms, _FADE_MS + 200)
        self._fade_in.start()
        QTimer.singleShot(hold, self._fade_out.start)

    def _on_fade_done(self):
        self.hide()
        self.finished.emit()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _center(self):
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width()  - self.width())  // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

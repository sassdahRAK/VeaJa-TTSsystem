"""
Splash screen shown at launch.
Large, official-looking window: logo, app name, tagline, animated progress bar.
Fades in on show, fades out before emitting `finished`.
"""

import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve,
    QSequentialAnimationGroup
)
from PyQt6.QtGui import QPalette, QColor, QPixmap


ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")

# Total display time before fade-out starts (ms)
_HOLD_MS    = 2600
# Fade-in / fade-out duration (ms)
_FADE_MS    = 420
# Progress bar fill duration — slightly shorter than hold so it completes first
_PROG_MS    = _HOLD_MS - 200


def _is_dark_mode() -> bool:
    palette = QPalette()
    return palette.color(QPalette.ColorRole.Window).lightness() < 128


class SplashScreen(QWidget):
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._dark = _is_dark_mode()
        self._init_ui()
        self._init_animations()
        # Start invisible so the fade-in plays on start_timer()
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
        self.setFixedSize(860, 520)
        self._center()

        bg         = "#0d0d0d" if self._dark else "#ffffff"
        text_color = "#ffffff" if self._dark else "#1a1a1a"
        bar_bg     = "#2a2a2a" if self._dark else "#e8e8e8"
        bar_fill   = "#ffffff" if self._dark else "#1a1a1a"

        self.setStyleSheet(f"background-color: {bg};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Centre content ────────────────────────────────────────────────
        centre = QVBoxLayout()
        centre.setAlignment(Qt.AlignmentFlag.AlignCenter)
        centre.setSpacing(0)

        # Logo
        png_name = "logo_light.png" if self._dark else "logo_dark.png"
        png_path = os.path.join(ASSETS, png_name)
        self.logo = QLabel()
        self.logo.setFixedSize(300, 300)
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if os.path.exists(png_path):
            px = QPixmap(png_path).scaled(
                300, 300,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.logo.setPixmap(px)
        else:
            self.logo.setText("V")
            self.logo.setStyleSheet(
                f"font-size: 120px; font-weight: bold; color: {text_color};"
            )
        centre.addWidget(self.logo, 0, Qt.AlignmentFlag.AlignHCenter)
        centre.addSpacing(18)

        # App name
        name_lbl = QLabel("Veaja")
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setStyleSheet(
            f"color: {text_color}; font-size: 30px;"
            f" font-weight: 300; letter-spacing: 8px;"
            f" background: transparent;"
        )
        centre.addWidget(name_lbl, 0, Qt.AlignmentFlag.AlignHCenter)

        root.addStretch(2)
        root.addLayout(centre)
        root.addStretch(3)

        # ── Bottom progress bar ───────────────────────────────────────────
        bottom = QWidget()
        bottom.setFixedHeight(28)
        bottom.setStyleSheet("background: transparent;")
        b_lay = QVBoxLayout(bottom)
        b_lay.setContentsMargins(60, 0, 60, 14)
        b_lay.setSpacing(0)

        self._prog = QProgressBar()
        self._prog.setRange(0, 1000)
        self._prog.setValue(0)
        self._prog.setTextVisible(False)
        self._prog.setFixedHeight(3)
        self._prog.setStyleSheet(f"""
            QProgressBar {{
                background: {bar_bg};
                border: none;
                border-radius: 1px;
            }}
            QProgressBar::chunk {{
                background: {bar_fill};
                border-radius: 1px;
            }}
        """)
        b_lay.addWidget(self._prog)

        root.addWidget(bottom)

        # ── Progress animation (QPropertyAnimation on value) ──────────────
        self._prog_anim = QPropertyAnimation(self._prog, b"value")
        self._prog_anim.setDuration(_PROG_MS)
        self._prog_anim.setStartValue(0)
        self._prog_anim.setEndValue(1000)
        self._prog_anim.setEasingCurve(QEasingCurve.Type.OutQuart)

    # ------------------------------------------------------------------ #
    # Animations
    # ------------------------------------------------------------------ #

    def _init_animations(self):
        # Fade-in
        self._fade_in = QPropertyAnimation(self, b"windowOpacity")
        self._fade_in.setDuration(_FADE_MS)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.InCubic)

        # Fade-out
        self._fade_out = QPropertyAnimation(self, b"windowOpacity")
        self._fade_out.setDuration(_FADE_MS)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_out.finished.connect(self._on_fade_done)

    def start_timer(self, delay_ms: int = _HOLD_MS):
        """Fade in, run progress bar, then fade out after `delay_ms` ms hold."""
        hold = max(delay_ms, _FADE_MS + 200)
        self._fade_in.start()
        self._prog_anim.start()
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

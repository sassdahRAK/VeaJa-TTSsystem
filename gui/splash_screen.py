"""
Splash screen shown at launch (img4 design).
Shows the Veaja logo centred on a pure white/black background,
with "Veaja" label below. Auto-closes after ~2.5 s then emits `finished`.
"""

import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPalette, QColor, QPixmap


ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")


def _is_dark_mode() -> bool:
    palette = QPalette()
    return palette.color(QPalette.ColorRole.Window).lightness() < 128


class SplashScreen(QWidget):
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._dark = _is_dark_mode()
        self._init_ui()
        self._init_fade()

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
        self.setFixedSize(520, 420)
        self._center()

        # Background
        bg = "#000000" if self._dark else "#FFFFFF"
        self.setStyleSheet(f"background-color: {bg};")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(24)
        layout.setContentsMargins(60, 60, 60, 60)

        # PNG logo — much lighter than SVG
        # logo_dark.png = dark face on white bg  → light mode splash (white bg)
        # logo_light.png = white face on dark bg → dark mode splash (black bg)
        png_path = os.path.join(ASSETS, "logo_light.png" if self._dark else "logo_dark.png")
        self.logo = QLabel()
        self.logo.setFixedSize(220, 220)
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if os.path.exists(png_path):
            px = QPixmap(png_path).scaled(
                220, 220,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.logo.setPixmap(px)
        else:
            self.logo.setText("Veaja")
            self.logo.setStyleSheet(
                "font-size: 72px; font-weight: bold; color: #E53935;"
            )

        layout.addWidget(self.logo, alignment=Qt.AlignmentFlag.AlignCenter)

        # App name label
        text_color = "#FFFFFF" if self._dark else "#1A1A1A"
        name_label = QLabel("Veaja")
        name_label.setStyleSheet(
            f"color: {text_color}; font-size: 22px; "
            f"font-weight: 300; letter-spacing: 6px;"
        )
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

    # ------------------------------------------------------------------ #
    # Fade-out animation
    # ------------------------------------------------------------------ #

    def _init_fade(self):
        self._fade = QPropertyAnimation(self, b"windowOpacity")
        self._fade.setDuration(500)
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade.finished.connect(self._on_fade_done)

    def start_timer(self, delay_ms: int = 2400):
        QTimer.singleShot(delay_ms, self._fade.start)

    def _on_fade_done(self):
        self.hide()
        self.finished.emit()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _center(self):
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

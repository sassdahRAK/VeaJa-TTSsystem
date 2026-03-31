"""
Veaja main settings / dashboard window.

Features:
  • Paste / type text and press Read
  • Voice selector, speed slider, volume slider
  • Dark / light theme toggle (syncs with system)
  • History list of last 20 items
  • Minimise to tray
"""

import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QSlider,
    QComboBox, QListWidget, QListWidgetItem,
    QFrame, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont, QPalette, QColor, QPixmap


ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
STYLES = os.path.join(os.path.dirname(__file__), "..", "styles")


def _is_dark_mode() -> bool:
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        return False
    return app.palette().color(QPalette.ColorRole.Window).lightness() < 128


class MainWindow(QMainWindow):
    # Signals to AppController
    read_requested  = pyqtSignal(str)
    stop_requested  = pyqtSignal()
    quit_requested  = pyqtSignal()
    theme_changed   = pyqtSignal(bool)   # True = dark

    def __init__(self, tts_engine=None):
        super().__init__()
        self._tts = tts_engine
        self._history: list[str] = []
        self._dark = _is_dark_mode()
        self._speaking = False

        self.setWindowTitle("Veaja")
        self.setMinimumSize(460, 640)
        self.resize(480, 660)
        self._center()
        self._build_ui()
        self._apply_theme()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(14)

        root.addLayout(self._header_row())
        root.addWidget(self._divider())
        root.addWidget(self._text_section())
        root.addLayout(self._controls_row())
        root.addWidget(self._divider())
        root.addWidget(self._voice_section())
        root.addWidget(self._divider())
        root.addWidget(self._history_section())

    # ─── Header ──────────────────────────────────────────────────────────

    def _header_row(self) -> QHBoxLayout:
        row = QHBoxLayout()

        # Logo (small) — QLabel with QPixmap, much lighter than QSvgWidget
        # logo_dark.png = dark face on white bg → light mode
        # logo_light.png = white face on dark bg → dark mode
        self._header_logo = QLabel()
        self._header_logo.setFixedSize(38, 38)
        self._header_logo.setScaledContents(False)
        self._reload_header_logo()
        row.addWidget(self._header_logo)

        title = QLabel("Veaja")
        title.setObjectName("appTitle")
        title.setFont(QFont("SF Pro Display", 20, QFont.Weight.Light))
        row.addWidget(title)

        row.addStretch()

        # Theme toggle
        self._theme_btn = QPushButton("☀" if self._dark else "☾")
        self._theme_btn.setObjectName("iconBtn")
        self._theme_btn.setFixedSize(32, 32)
        self._theme_btn.setToolTip("Toggle dark / light mode")
        self._theme_btn.clicked.connect(self._toggle_theme)
        row.addWidget(self._theme_btn)

        return row

    def _reload_header_logo(self):
        name = "logo_light.png" if self._dark else "logo_dark.png"
        path = os.path.join(ASSETS, name)
        if os.path.exists(path):
            px = QPixmap(path).scaled(
                38, 38,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._header_logo.setPixmap(px)

    # ─── Text input ──────────────────────────────────────────────────────

    def _text_section(self) -> QWidget:
        frame = QWidget()
        frame.setObjectName("card")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        lbl = QLabel("Text to read")
        lbl.setObjectName("sectionLabel")
        lay.addWidget(lbl)

        self._text_edit = QTextEdit()
        self._text_edit.setObjectName("textEdit")
        self._text_edit.setPlaceholderText(
            "Type or paste text here, or select text in any app…"
        )
        self._text_edit.setMinimumHeight(130)
        self._text_edit.setMaximumHeight(200)
        lay.addWidget(self._text_edit)

        return frame

    # ─── Read / Stop controls ────────────────────────────────────────────

    def _controls_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)

        self._read_btn = QPushButton("▶  Read")
        self._read_btn.setObjectName("readBtn")
        self._read_btn.setFixedHeight(44)
        self._read_btn.setFont(QFont("SF Pro Text", 13, QFont.Weight.Medium))
        self._read_btn.clicked.connect(self._on_read_clicked)
        row.addWidget(self._read_btn)

        self._stop_btn = QPushButton("■  Stop")
        self._stop_btn.setObjectName("stopBtn")
        self._stop_btn.setFixedHeight(44)
        self._stop_btn.setFixedWidth(100)
        self._stop_btn.setFont(QFont("SF Pro Text", 13))
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self.stop_requested)
        row.addWidget(self._stop_btn)

        return row

    # ─── Voice settings ──────────────────────────────────────────────────

    def _voice_section(self) -> QWidget:
        frame = QWidget()
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        lbl = QLabel("Voice settings")
        lbl.setObjectName("sectionLabel")
        lay.addWidget(lbl)

        # Voice selector
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Voice"))
        self._voice_combo = QComboBox()
        self._voice_combo.setObjectName("combo")
        self._voice_combo.currentIndexChanged.connect(self._on_voice_changed)
        row1.addWidget(self._voice_combo, 1)
        lay.addLayout(row1)

        # Speed
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Speed"))
        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(50, 400)
        self._speed_slider.setValue(175)
        self._speed_slider.setTickInterval(50)
        self._speed_slider.valueChanged.connect(self._on_speed_changed)
        row2.addWidget(self._speed_slider, 1)
        self._speed_label = QLabel("175")
        self._speed_label.setFixedWidth(36)
        self._speed_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        row2.addWidget(self._speed_label)
        lay.addLayout(row2)

        # Volume
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Volume"))
        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(100)
        self._vol_slider.valueChanged.connect(self._on_volume_changed)
        row3.addWidget(self._vol_slider, 1)
        self._vol_label = QLabel("100%")
        self._vol_label.setFixedWidth(36)
        self._vol_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        row3.addWidget(self._vol_label)
        lay.addLayout(row3)

        return frame

    # ─── History list ────────────────────────────────────────────────────

    def _history_section(self) -> QWidget:
        frame = QWidget()
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        row = QHBoxLayout()
        lbl = QLabel("Recent")
        lbl.setObjectName("sectionLabel")
        row.addWidget(lbl)
        row.addStretch()
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("linkBtn")
        clear_btn.clicked.connect(self._clear_history)
        row.addWidget(clear_btn)
        lay.addLayout(row)

        self._history_list = QListWidget()
        self._history_list.setObjectName("historyList")
        self._history_list.setMaximumHeight(130)
        self._history_list.itemDoubleClicked.connect(self._on_history_item)
        lay.addWidget(self._history_list)

        return frame

    # ─── Helpers ─────────────────────────────────────────────────────────

    def _divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("divider")
        return line

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def populate_voices(self, voices: list[dict]):
        self._voice_combo.blockSignals(True)
        self._voice_combo.clear()
        for v in voices:
            self._voice_combo.addItem(v["name"], v["id"])
        self._voice_combo.blockSignals(False)

    def set_text(self, text: str):
        """Called by AppController when clipboard/selection text arrives."""
        self._text_edit.setPlainText(text)
        self._add_history(text)

    def set_speaking(self, speaking: bool):
        self._speaking = speaking
        self._read_btn.setEnabled(not speaking)
        self._stop_btn.setEnabled(speaking)
        self._read_btn.setText("🔊 Speaking…" if speaking else "▶  Read")

    # ------------------------------------------------------------------ #
    # Slots
    # ------------------------------------------------------------------ #

    def _on_read_clicked(self):
        text = self._text_edit.toPlainText().strip()
        if text:
            self._add_history(text)
            self.read_requested.emit(text)

    def _on_voice_changed(self, index: int):
        if self._tts:
            self._tts.set_voice(self._voice_combo.itemData(index))

    def _on_speed_changed(self, value: int):
        self._speed_label.setText(str(value))
        if self._tts:
            self._tts.set_rate(value)

    def _on_volume_changed(self, value: int):
        self._vol_label.setText(f"{value}%")
        if self._tts:
            self._tts.set_volume(value / 100.0)

    def _on_history_item(self, item: QListWidgetItem):
        text = item.data(Qt.ItemDataRole.UserRole)
        if text:
            self._text_edit.setPlainText(text)

    def _add_history(self, text: str):
        short = text[:80] + ("…" if len(text) > 80 else "")
        if short in self._history:
            return
        self._history.insert(0, short)
        self._history = self._history[:20]
        item = QListWidgetItem(short)
        item.setData(Qt.ItemDataRole.UserRole, text)
        self._history_list.insertItem(0, item)
        if self._history_list.count() > 20:
            self._history_list.takeItem(20)

    def _clear_history(self):
        self._history.clear()
        self._history_list.clear()

    def _toggle_theme(self):
        self._dark = not self._dark
        self._theme_btn.setText("☀" if self._dark else "☾")
        self._reload_header_logo()
        self._apply_theme()
        self.theme_changed.emit(self._dark)

    # ------------------------------------------------------------------ #
    # Theme
    # ------------------------------------------------------------------ #

    def _apply_theme(self):
        qss_file = "dark.qss" if self._dark else "light.qss"
        path = os.path.join(STYLES, qss_file)
        if os.path.exists(path):
            with open(path, "r") as f:
                self.setStyleSheet(f.read())

    # ------------------------------------------------------------------ #
    # Window events
    # ------------------------------------------------------------------ #

    def closeEvent(self, event):
        event.ignore()
        self.hide()   # minimise to tray instead of quitting

    def _center(self):
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width()  - self.width())  // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

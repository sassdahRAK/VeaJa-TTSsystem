"""
Veaja main settings / dashboard window.

Features:
  • Paste / type text and press Read
  • Voice selector, speed slider, volume slider
  • Dark / light theme toggle (syncs with system)
  • History list of last 20 items
  • Minimise to tray
  • Profile avatar + name in header (editable via ProfileDialog)
  • Terms & Privacy button
  • Read button turns RED while speaking, ORANGE while paused
"""

import os
from enum import Enum, auto

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QSlider,
    QComboBox, QListWidget, QListWidgetItem,
    QFrame, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
# from PyQt6.QtGui import QIcon, QFont, QPalette, QColor, QPixmap, QPainter, QPainterPath, QRectF
# AFTER (fixed) — split into two imports
from PyQt6.QtGui import (
    QIcon, QFont, QPalette, QColor, QPixmap,
    QPainter, QPainterPath, QTextCursor, QTextCharFormat, QBrush
)
from PyQt6.QtCore import QRectF

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
STYLES = os.path.join(os.path.dirname(__file__), "..", "styles")


# ── Read state enum (shared with AppController via import) ────────────────────
class ReadState(Enum):
    IDLE       = auto()
    PROCESSING = auto()
    SPEAKING   = auto()
    PAUSED     = auto()


def _is_dark_mode() -> bool:
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        return False
    return app.palette().color(QPalette.ColorRole.Window).lightness() < 128


def _make_round_pixmap(path: str, size: int) -> QPixmap | None:
    """Load an image and clip it to a circle of the given size."""
    raw = QPixmap(path)
    if raw.isNull():
        return None
    raw = raw.scaled(size, size,
                     Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                     Qt.TransformationMode.SmoothTransformation)
    result = QPixmap(size, size)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    clip = QPainterPath()
    clip.addEllipse(QRectF(0, 0, size, size))
    painter.setClipPath(clip)
    x = (raw.width()  - size) // 2
    y = (raw.height() - size) // 2
    painter.drawPixmap(-x, -y, raw)
    painter.end()
    return result


class MainWindow(QMainWindow):
    # Signals to AppController
    read_requested    = pyqtSignal(str)
    pause_requested   = pyqtSignal()
    resume_requested  = pyqtSignal()
    stop_requested    = pyqtSignal()
    quit_requested    = pyqtSignal()
    theme_changed     = pyqtSignal(bool)   # True = dark
    terms_requested   = pyqtSignal()
    profile_requested = pyqtSignal()
    mode_changed      = pyqtSignal(bool)   # True = online, False = offline
    tour_requested    = pyqtSignal()

    def __init__(self, tts_engine=None):
        super().__init__()
        self._tts   = tts_engine
        self._history: list[str] = []
        self._dark  = _is_dark_mode()
        self._state = ReadState.IDLE
        self._logo_path: str | None = None          # persists across theme changes
        self._highlight_color: str = "#FFD60A"       # default yellow; customisable
        self._last_highlight_end: int = 0
        self._last_read_text: str = ""               # tracks what is currently playing

        self.setWindowTitle("Veaja")
        self.setMinimumSize(460, 660)
        self.resize(480, 680)
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

        # Avatar — shows logo or custom profile image
        self._header_logo = QLabel()
        self._header_logo.setFixedSize(38, 38)
        self._header_logo.setScaledContents(False)
        self._header_logo.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header_logo.setToolTip("Edit profile")
        self._header_logo.mousePressEvent = lambda _: self.profile_requested.emit()
        self._reload_header_logo()
        row.addWidget(self._header_logo)

        # App name (clickable to open profile)
        self._title_label = QLabel("Veaja")
        self._title_label.setObjectName("appTitle")
        self._title_label.setFont(QFont("SF Pro Display", 20, QFont.Weight.Light))
        self._title_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self._title_label.setToolTip("Edit profile")
        self._title_label.mousePressEvent = lambda _: self.profile_requested.emit()
        row.addWidget(self._title_label)

        row.addStretch()

        # Tutorial button
        self._tour_btn = QPushButton("?")
        self._tour_btn.setObjectName("iconBtn")
        self._tour_btn.setFixedSize(32, 32)
        self._tour_btn.setToolTip("Interactive tutorial")
        self._tour_btn.clicked.connect(self.tour_requested)
        row.addWidget(self._tour_btn)

        # Terms / Privacy button
        self._terms_btn = QPushButton("🔒")
        self._terms_btn.setObjectName("iconBtn")
        self._terms_btn.setFixedSize(32, 32)
        self._terms_btn.setToolTip("Privacy & Terms")
        self._terms_btn.clicked.connect(self.terms_requested)
        row.addWidget(self._terms_btn)

        # Theme toggle
        self._theme_btn = QPushButton("☀" if self._dark else "☾")
        self._theme_btn.setObjectName("iconBtn")
        self._theme_btn.setFixedSize(32, 32)
        self._theme_btn.setToolTip("Toggle dark / light mode")
        self._theme_btn.clicked.connect(self._toggle_theme)
        row.addWidget(self._theme_btn)

        return row

    def _reload_header_logo(self, logo_path: str | None = None):
        """
        Load avatar from custom path or fall back to bundled logo.
        When called without arguments (e.g. on theme toggle) the previously
        stored logo_path is used so a custom avatar is never lost.
        """
        # If a new path is provided, remember it; otherwise use whatever was stored.
        if logo_path is not None:
            self._logo_path = logo_path if (logo_path and os.path.exists(logo_path)) else None

        if self._logo_path and os.path.exists(self._logo_path):
            px = _make_round_pixmap(self._logo_path, 38)
        else:
            name = "logo_light.png" if self._dark else "logo_dark.png"
            path = os.path.join(ASSETS, name)
            px = _make_round_pixmap(path, 38) if os.path.exists(path) else None

        if px:
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
            "Type or paste text here, or select text in any app…  "
            "(Ctrl+R to read clipboard directly)"
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
        self._stop_btn.setFixedWidth(110)
        self._stop_btn.setFont(QFont("SF Pro Text", 13))
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._on_stop_clicked)
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

        # ── Online / Offline mode toggle ──────────────────────────────────
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode"))

        self._online_btn = QPushButton("🌐  Online (Neural)")
        self._online_btn.setObjectName("modeBtn")
        self._online_btn.setFixedHeight(32)
        self._online_btn.setCheckable(True)
        self._online_btn.setChecked(True)
        self._online_btn.clicked.connect(lambda: self._set_mode(online=True))

        self._offline_btn = QPushButton("💻  Offline (System)")
        self._offline_btn.setObjectName("modeBtn")
        self._offline_btn.setFixedHeight(32)
        self._offline_btn.setCheckable(True)
        self._offline_btn.setChecked(False)
        self._offline_btn.clicked.connect(lambda: self._set_mode(online=False))

        mode_row.addWidget(self._online_btn, 1)
        mode_row.addWidget(self._offline_btn, 1)
        lay.addLayout(mode_row)

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
        self.clear_highlight()
        self._text_edit.setPlainText(text)
        self._add_history(text)

    def set_read_state(self, state: ReadState):
        """Single method that updates all button visuals for the given state."""
        self._state = state
        btn  = self._read_btn
        stop = self._stop_btn

        if state == ReadState.IDLE:
            btn.setText("▶  Read")
            btn.setProperty("btnState", "idle")
            btn.setEnabled(True)
            stop.setText("■  Stop")
            stop.setEnabled(False)

        elif state == ReadState.PROCESSING:
            btn.setText("⏳ Processing…")
            btn.setProperty("btnState", "processing")
            btn.setEnabled(False)
            stop.setText("■  Stop")
            stop.setEnabled(True)

        elif state == ReadState.SPEAKING:
            btn.setText("⏸  Pause")
            btn.setProperty("btnState", "active")   # → red via QSS
            btn.setEnabled(True)
            stop.setText("■  Stop")
            stop.setEnabled(True)

        elif state == ReadState.PAUSED:
            btn.setText("▶  Resume")
            btn.setProperty("btnState", "paused")   # → orange via QSS
            btn.setEnabled(True)
            stop.setText("■  Stop")
            stop.setEnabled(True)

        # Force Qt to re-evaluate property-based QSS rules
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        btn.update()

    # Thin shims for backward compatibility (AppController uses set_read_state now)
    def set_processing(self, processing: bool):
        if processing:
            self.set_read_state(ReadState.PROCESSING)

    def set_speaking(self, speaking: bool):
        self.set_read_state(ReadState.SPEAKING if speaking else ReadState.IDLE)

    def apply_profile(self, profile: dict):
        """Update header with user's custom name and avatar."""
        name = profile.get("app_name", "Veaja") or "Veaja"
        self._title_label.setText(name)
        self.setWindowTitle(name)
        self._reload_header_logo(profile.get("logo_path"))
        # Custom highlight color (default yellow #FFD60A if not set)
        color = profile.get("highlight_color", "#FFD60A")
        if color:
            self._highlight_color = color

    # ------------------------------------------------------------------ #
    # Word highlight (called from AppController via word_highlight signal)
    # ------------------------------------------------------------------ #

    def highlight_word(self, start: int, end: int):
        """
        Cumulatively highlight the text from 0 … end in the user's chosen
        colour.  Only extends the highlighted region — never shrinks it —
        so the progress bar effect (0 → 100 %) feels smooth.
        """
        if end <= self._last_highlight_end or end <= start:
            return
        doc = self._text_edit.document()
        cursor = QTextCursor(doc)
        cursor.setPosition(self._last_highlight_end)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(self._highlight_color))
        cursor.setCharFormat(fmt)
        self._last_highlight_end = end

    def clear_highlight(self):
        """Remove all word highlighting and reset progress."""
        if self._last_highlight_end == 0:
            return
        doc = self._text_edit.document()
        cursor = QTextCursor(doc)
        cursor.select(QTextCursor.SelectionType.Document)
        fmt = QTextCharFormat()
        fmt.setBackground(QBrush())   # empty brush = no background
        cursor.setCharFormat(fmt)
        self._last_highlight_end = 0

    # ------------------------------------------------------------------ #
    # Slots
    # ------------------------------------------------------------------ #

    def _on_read_clicked(self):
        text = self._text_edit.toPlainText().strip()

        # If the text box content changed since we started reading, always
        # start fresh — regardless of whether we are SPEAKING or PAUSED.
        text_changed = bool(text) and (text != self._last_read_text)

        if not text_changed and self._state == ReadState.SPEAKING:
            self.pause_requested.emit()
        elif not text_changed and self._state == ReadState.PAUSED:
            self.resume_requested.emit()
        else:
            if text:
                self._last_read_text = text
                self._add_history(text)
                self.read_requested.emit(text)

    def mark_reading_started(self, text: str):
        """Called by AppController when TTS actually starts so we know what is playing."""
        self._last_read_text = text

    def _on_stop_clicked(self):
        if self._state == ReadState.PROCESSING:
            self.stop_requested.emit()    # cancel synthesis
        elif self._state == ReadState.SPEAKING:
            self.pause_requested.emit()   # first stop click = pause
        elif self._state == ReadState.PAUSED:
            self.stop_requested.emit()    # stop while paused = full stop
        else:
            self.stop_requested.emit()

    def _set_mode(self, online: bool):
        """Toggle between online (neural) and offline (system) mode."""
        self._online_btn.setChecked(online)
        self._offline_btn.setChecked(not online)
        self.mode_changed.emit(online)

    def set_online_mode(self, online: bool):
        """Called by AppController to reflect current engine state."""
        self._online_btn.setChecked(online)
        self._offline_btn.setChecked(not online)

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
            with open(path, encoding="utf-8") as f:
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

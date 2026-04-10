"""
Veaja main window — matches DesignWorkFlow web prototype exactly.

Sidebar: 240px, always contrasts content (dark in light mode, light in dark mode).
Pages: Dashboard | Voice Setting | View History | Tutorial | Ask a Question | Data Privacy
"""

import os
from enum import Enum, auto

from gui.icon_utils import svg_pixmap, svg_icon

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QStackedLayout,
    QLabel, QPushButton, QTextEdit, QSlider, QComboBox, QLineEdit,
    QFrame, QScrollArea, QCheckBox, QSizePolicy, QListWidget, QListWidgetItem,
    QGraphicsDropShadowEffect, QSizeGrip
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QPoint
from PyQt6.QtGui import (
    QPalette, QColor, QPixmap, QFont,
    QPainter, QPainterPath, QTextCursor, QTextCharFormat, QBrush
)
from PyQt6.QtCore import QRectF

from gui._window_shared import ASSETS, STYLES, _make_square_pixmap, _make_circle_pixmap  # noqa: E402


# ── Read state ─────────────────────────────────────────────────────────────────
class ReadState(Enum):
    IDLE       = auto()
    PROCESSING = auto()
    SPEAKING   = auto()
    PAUSED     = auto()


def _is_dark_mode() -> bool:
    import platform as _platform
    if _platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return val == 0   # 0 → dark mode, 1 → light mode
        except Exception:
            pass
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        return False
    return app.palette().color(QPalette.ColorRole.Window).lightness() < 128


# ── Drag-to-move title bar ────────────────────────────────────────────────────

class _DragBar(QWidget):
    """Title bar widget that handles window drag and double-click to maximize."""

    def __init__(self, main_window: "MainWindow", parent=None):
        super().__init__(parent)
        self._win = main_window
        self._drag_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self._win.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
            if self._win.isMaximized():
                # Snap out of maximized before dragging
                self._win.showNormal()
                if self._win._max_btn:
                    self._win._max_btn.setText("❐")
                # Recalculate so the window doesn't jump
                self._drag_pos = QPoint(self._win.width() // 2, self.height() // 2)
            self._win.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._win._toggle_maximize()


# ── Mixin imports ──
from gui.pages.dashboard_mixin import DashboardMixin    # noqa: E402
from gui.pages.settings_mixin import SettingsMixin      # noqa: E402
from gui.pages.history_mixin import HistoryMixin        # noqa: E402
from gui.pages.profile_mixin import ProfileMixin        # noqa: E402
from gui.pages.info_pages_mixin import InfoPagesMixin   # noqa: E402
from gui.theme_mixin import ThemeMixin                  # noqa: E402


# ══════════════════════════════════════════════════════════════════════════════
class MainWindow(DashboardMixin, SettingsMixin, HistoryMixin, ProfileMixin,
                 InfoPagesMixin, ThemeMixin, QMainWindow):

    # ── Signals ────────────────────────────────────────────────────────────────
    read_requested        = pyqtSignal(str)
    pause_requested       = pyqtSignal()
    resume_requested      = pyqtSignal()
    stop_requested        = pyqtSignal()
    quit_requested        = pyqtSignal()
    theme_changed         = pyqtSignal(bool)   # True = dark
    terms_requested       = pyqtSignal()
    profile_requested     = pyqtSignal()
    profile_save_requested  = pyqtSignal(dict)  # emitted when user saves profile page
    settings_save_requested = pyqtSignal(dict)  # emitted when user saves voice settings
    mode_changed           = pyqtSignal(bool)   # True = online
    shape_changed         = pyqtSignal(str)    # "circle" | "rectangle"
    anim_spin_changed     = pyqtSignal(bool)   # logo spin while reading
    anim_glow_changed     = pyqtSignal(bool)   # glow border pulse
    tour_requested        = pyqtSignal()

    def __init__(self, tts_engine=None):
        super().__init__()
        self._tts   = tts_engine
        self._history: list[str]       = []
        self._history_shorts: list[str] = []
        self._dark  = _is_dark_mode()
        self._state = ReadState.IDLE
        self._logo_path: str | None    = None
        self._highlight_color: str     = "#FFD60A"
        self._last_highlight_end: int  = 0
        self._last_read_text: str      = ""
        self._nav_btns: list[tuple[QPushButton, int]] = []

        # References set during build — needed by _apply_sidebar_theme
        self._sidebar_widget: QWidget  = None
        self._profile_frame: QWidget   = None
        self._profile_photo_frame: QWidget | None = None  # large frame on profile page
        self._pending_profile: dict    = {}               # working copy while editing

        # SVG icon labels/buttons — set during _build_sidebar, recolored in theme
        self._edit_icon_lbl: QLabel | None    = None
        self._tutorial_btn: QPushButton | None = None
        self._ask_btn: QPushButton | None      = None
        self._privacy_btn: QPushButton | None  = None

        self.setWindowTitle("Veaja")
        self.setMinimumSize(780, 580)
        self.resize(900, 660)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self._title_bar_height = 38
        self._title_bar_widget: QWidget | None = None
        self._title_bar_label: QLabel | None = None
        self._max_btn: QPushButton | None = None
        self._center()
        self._build_ui()
        self._apply_theme()

    # ════════════════════════════════════════════════════════════════════════ #
    #  UI CONSTRUCTION
    # ════════════════════════════════════════════════════════════════════════ #

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Custom title bar
        self._title_bar_widget = self._build_title_bar()
        root.addWidget(self._title_bar_widget)

        # Content row: sidebar + pages
        content_row = QWidget()
        content_row.setObjectName("contentRow")
        row_lay = QHBoxLayout(content_row)
        row_lay.setContentsMargins(0, 0, 0, 0)
        row_lay.setSpacing(0)

        self._sidebar_widget = self._build_sidebar()
        row_lay.addWidget(self._sidebar_widget)

        # Content stack (pages 0-6)
        self._content_stack = QStackedWidget()
        self._content_stack.setObjectName("contentStack")
        self._content_stack.addWidget(self._build_dashboard_page())  # 0
        self._content_stack.addWidget(self._build_settings_page())   # 1
        self._content_stack.addWidget(self._build_history_page())    # 2
        self._content_stack.addWidget(self._build_ask_page())        # 3
        self._content_stack.addWidget(self._build_privacy_page())    # 4
        self._content_stack.addWidget(self._build_tutorial_page())   # 5
        self._content_stack.addWidget(self._build_profile_page())    # 6
        row_lay.addWidget(self._content_stack, 1)

        root.addWidget(content_row, 1)

        # Bottom-right size grip for mouse resize
        grip = QSizeGrip(self)
        grip.setFixedSize(14, 14)
        grip.move(self.width() - 14, self.height() - 14)

    def _build_title_bar(self) -> QWidget:
        bar = _DragBar(self)
        bar.setObjectName("titleBar")
        bar.setFixedHeight(self._title_bar_height)

        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 0, 0, 0)
        lay.setSpacing(0)

        # App icon (small, displayed as circle)
        self._titlebar_icon = QLabel()
        self._titlebar_icon.setObjectName("titleBarIcon")
        self._titlebar_icon.setFixedSize(26, 26)
        self._titlebar_icon.setScaledContents(False)
        self._titlebar_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._reload_titlebar_icon()
        lay.addWidget(self._titlebar_icon)
        lay.addSpacing(8)

        # App name
        self._title_bar_label = QLabel("Veaja")
        self._title_bar_label.setObjectName("titleBarText")
        lay.addWidget(self._title_bar_label)

        lay.addStretch()

        # Window control buttons (standard width 46px each)
        self._min_btn = QPushButton("─")
        self._min_btn.setObjectName("titleBarMin")
        self._min_btn.setFixedSize(46, self._title_bar_height)
        self._min_btn.setCursor(Qt.CursorShape.ArrowCursor)
        self._min_btn.clicked.connect(self.showMinimized)

        self._max_btn = QPushButton("❐")
        self._max_btn.setObjectName("titleBarMax")
        self._max_btn.setFixedSize(46, self._title_bar_height)
        self._max_btn.setCursor(Qt.CursorShape.ArrowCursor)
        self._max_btn.clicked.connect(self._toggle_maximize)

        self._close_btn_tb = QPushButton("✕")
        self._close_btn_tb.setObjectName("titleBarClose")
        self._close_btn_tb.setFixedSize(46, self._title_bar_height)
        self._close_btn_tb.setCursor(Qt.CursorShape.ArrowCursor)
        self._close_btn_tb.clicked.connect(self.close)

        lay.addWidget(self._min_btn)
        lay.addWidget(self._max_btn)
        lay.addWidget(self._close_btn_tb)

        return bar

    def _reload_titlebar_icon(self):
        if not hasattr(self, "_titlebar_icon"):
            return
        from PyQt6.QtWidgets import QApplication as _QApp
        _app = _QApp.instance()
        dpr  = _app.primaryScreen().devicePixelRatio() if (_app and _app.primaryScreen()) else 1.0
        logical = 20   # icon size; container is 26 — gives 3 px padding each side
        phys    = int(logical * dpr)          # e.g. 25 at 125 % DPI

        stem = "logo_light" if self._dark else "logo_dark"
        for ext in (".png", ".svg"):
            p = os.path.join(ASSETS, stem + ext)
            if os.path.exists(p):
                raw = QPixmap(p)
                if raw.isNull():
                    continue
                # Scale to physical size for crisp rendering on HiDPI screens
                sq = raw.scaled(
                    phys, phys,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                if sq.width() != phys or sq.height() != phys:
                    x = (sq.width()  - phys) // 2
                    y = (sq.height() - phys) // 2
                    sq = sq.copy(x, y, phys, phys)
                sq.setDevicePixelRatio(dpr)   # logical = phys/dpr = 20 px
                circle = _make_circle_pixmap(sq)
                # circle inherits dpr from sq → logical size stays 20 px
                self._titlebar_icon.setPixmap(circle)
                return

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self._max_btn.setText("❐")
        else:
            self.showMaximized()
            self._max_btn.setText("❒")


    # ── Sidebar ────────────────────────────────────────────────────────────────

    def _build_sidebar(self) -> QWidget:
        sb = QWidget()
        sb.setObjectName("sidebar")
        sb.setFixedWidth(240)

        outer = QVBoxLayout(sb)
        outer.setContentsMargins(20, 16, 20, 28)
        outer.setSpacing(0)

        # Theme toggle — top-right (we put it in a row)
        top_row = QHBoxLayout()
        top_row.addStretch()
        self._theme_btn = QPushButton()
        self._theme_btn.setObjectName("themeBtn")
        self._theme_btn.setFixedSize(28, 28)
        self._theme_btn.setToolTip("Toggle theme")
        self._theme_btn.clicked.connect(self._toggle_theme)
        top_row.addWidget(self._theme_btn)
        outer.addLayout(top_row)

        # ── Profile section ───────────────────────────────────────────────
        profile_sec = QVBoxLayout()
        profile_sec.setSpacing(10)
        profile_sec.setContentsMargins(0, 10, 0, 20)

        # Square photo box
        self._profile_frame = QWidget()
        self._profile_frame.setObjectName("profileFrame")
        self._profile_frame.setFixedSize(82, 82)
        pf_lay = QVBoxLayout(self._profile_frame)
        pf_lay.setContentsMargins(0, 0, 0, 0)

        self._header_logo = QLabel()
        self._header_logo.setFixedSize(76, 76)
        self._header_logo.setScaledContents(True)
        self._header_logo.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._header_logo.mousePressEvent = lambda _: self._open_profile_page()
        pf_lay.addWidget(self._header_logo, 0, Qt.AlignmentFlag.AlignCenter)
        self._reload_header_logo()

        photo_row = QHBoxLayout()
        photo_row.addStretch()
        photo_row.addWidget(self._profile_frame)
        photo_row.addStretch()
        profile_sec.addLayout(photo_row)

        # Name + edit icon — both aligned to vertical centre
        name_row = QHBoxLayout()
        name_row.setSpacing(6)
        name_row.setContentsMargins(0, 0, 0, 0)
        name_row.addStretch()
        self._title_label = QLabel("Veaja")
        self._title_label.setObjectName("profileName")
        self._title_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
        self._title_label.setFixedHeight(22)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self._title_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self._title_label.mousePressEvent = lambda _: self._open_profile_page()
        name_row.addWidget(self._title_label, 0, Qt.AlignmentFlag.AlignVCenter)
        edit_ic = QLabel()
        edit_ic.setObjectName("editIcon")
        edit_ic.setFixedSize(16, 16)
        edit_ic.setScaledContents(True)
        edit_ic.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_ic.mousePressEvent = lambda _: self._open_profile_page()
        self._edit_icon_lbl = edit_ic
        name_row.addWidget(edit_ic, 0, Qt.AlignmentFlag.AlignVCenter)
        name_row.addStretch()
        profile_sec.addLayout(name_row)

        outer.addLayout(profile_sec)

        # ── Dashboard button ──────────────────────────────────────────────
        self._dash_btn = QPushButton("Dashboard")
        self._dash_btn.setObjectName("dashBtn")
        self._dash_btn.setFixedHeight(38)
        self._dash_btn.setCheckable(True)
        self._dash_btn.setChecked(True)
        self._dash_btn.clicked.connect(lambda: self._navigate(0))
        self._nav_btns.append((self._dash_btn, 0))
        outer.addWidget(self._dash_btn)
        outer.addSpacing(18)

        # ── Nav links ─────────────────────────────────────────────────────
        nav_col = QVBoxLayout()
        nav_col.setSpacing(10)
        nav_col.addWidget(self._nav_link("Voice Setting", 1))
        nav_col.addWidget(self._nav_link("View History",  2))
        outer.addLayout(nav_col)

        # Push help section toward bottom but cap so it never creates a huge gap
        outer.addSpacing(24)
        outer.addStretch(1)

        # ── Separator before Help ──────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        outer.addWidget(sep)
        outer.addSpacing(10)

        # ── Help section ──────────────────────────────────────────────────
        help_lbl = QLabel("Help")
        help_lbl.setObjectName("helpLabel")
        help_lbl.setFixedHeight(22)
        help_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        outer.addWidget(help_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        outer.addSpacing(10)

        help_col = QVBoxLayout()
        help_col.setSpacing(12)
        self._tutorial_btn = self._nav_link("  Tutorial",       5)
        self._ask_btn      = self._nav_link("  Ask a Question", 3)
        self._privacy_btn  = self._nav_link("  Data Privacy",   4)
        help_col.addWidget(self._tutorial_btn)
        help_col.addWidget(self._ask_btn)
        help_col.addWidget(self._privacy_btn)
        outer.addLayout(help_col)
        outer.addSpacing(8)

        return sb

    def _nav_link(self, label: str, page_idx: int) -> QPushButton:
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.setChecked(False)
        btn.setFixedHeight(28)
        btn.clicked.connect(lambda: self._navigate(page_idx))
        self._nav_btns.append((btn, page_idx))
        return btn

    def _navigate(self, page_idx: int):
        self._content_stack.setCurrentIndex(page_idx)
        for btn, idx in self._nav_btns:
            btn.setChecked(idx == page_idx)
        # Show edit icon only when NOT on the profile page (index 6)
        if self._edit_icon_lbl is not None:
            self._edit_icon_lbl.setVisible(page_idx != 6)

    def navigate_if_needed(self, page_idx: int, tab: int | None = None):
        """Used by TourOverlay for live-teach navigation."""
        self._navigate(page_idx)
        if tab is not None and page_idx == 0:
            self._switch_tab(tab)

    def _center(self):
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width()  - self.width())  // 2,
            (screen.height() - self.height()) // 2,
        )

    # ════════════════════════════════════════════════════════════════════════ #
    #  PUBLIC API (AppController-compatible)
    # ════════════════════════════════════════════════════════════════════════ #

    def populate_voices(self, voices: list[dict]):
        self._voice_combo.blockSignals(True)
        self._sound_input.blockSignals(True)
        self._voice_combo.clear()
        self._sound_input.clear()
        for v in voices:
            self._voice_combo.addItem(v["name"], v["id"])
            self._sound_input.addItem(v["name"], v["id"])
        self._voice_combo.blockSignals(False)
        self._sound_input.blockSignals(False)

    def set_text(self, text: str):
        self.clear_highlight()
        self._text_edit.setPlainText(text)
        short = text[:400] + ("…" if len(text) > 400 else "")
        self._overlay_text_view.setText(short)
        self._add_history(text)

    def set_read_state(self, state: ReadState):
        self._state = state
        btn = self._read_btn
        if state == ReadState.IDLE:
            btn.setText("Read")
            btn.setProperty("btnState", "idle")
            btn.setEnabled(True)
        elif state == ReadState.PROCESSING:
            btn.setText("⏳…")
            btn.setProperty("btnState", "processing")
            btn.setEnabled(False)
        elif state == ReadState.SPEAKING:
            btn.setText("⏸")
            btn.setProperty("btnState", "active")
            btn.setEnabled(True)
        elif state == ReadState.PAUSED:
            btn.setText("▶")
            btn.setProperty("btnState", "paused")
            btn.setEnabled(True)
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        btn.update()

    def set_processing(self, processing: bool):
        if processing:
            self.set_read_state(ReadState.PROCESSING)

    def set_speaking(self, speaking: bool):
        self.set_read_state(ReadState.SPEAKING if speaking else ReadState.IDLE)

    def apply_profile(self, profile: dict):
        name = profile.get("app_name", "Veaja") or "Veaja"
        if not any(c.isalnum() for c in name):   # reject names like "......."
            name = "Veaja"
        self._title_label.setText(name)
        self.setWindowTitle(name)
        if self._title_bar_label is not None:
            self._title_bar_label.setText(name)
        self._reload_header_logo(profile.get("logo_path"))  # redraws avatar with new name if needed
        color = profile.get("highlight_color", "#FFD60A")
        if color:
            self._highlight_color = color
        # Restore saved dark/light preference (None = already at system default)
        saved_dark = profile.get("dark_mode")
        if saved_dark is not None and isinstance(saved_dark, bool):
            if saved_dark != self._dark:
                self._toggle_theme()
        # Restore voice settings
        self._apply_voice_settings(profile)

    def _apply_voice_settings(self, profile: dict):
        """Restore Voice Settings controls and TTS engine state from a profile dict."""

        # Speed
        speed = profile.get("speed", 175)
        self._speed_slider.blockSignals(True)
        self._speed_slider.setValue(int(speed))
        self._speed_slider.blockSignals(False)
        if self._tts:
            self._tts.set_rate(int(speed))

        # Overlay shape
        shape = profile.get("overlay_shape", "rectangle")
        is_circle = (shape == "circle")
        self._shape_circle.blockSignals(True)
        self._shape_rect.blockSignals(True)
        self._shape_circle.setChecked(is_circle)
        self._shape_rect.setChecked(not is_circle)
        self._shape_circle.blockSignals(False)
        self._shape_rect.blockSignals(False)
        self.shape_changed.emit(shape)
        self._update_dashboard_pill_icon()

        # Animation overlay checkboxes
        if hasattr(self, "_anim_spin_chk"):
            spin = bool(profile.get("overlay_anim_spin", True))
            glow = bool(profile.get("overlay_anim_glow", False))
            self._anim_spin_chk.blockSignals(True)
            self._anim_glow_chk.blockSignals(True)
            self._anim_spin_chk.setChecked(spin)
            self._anim_glow_chk.setChecked(glow)
            self._anim_spin_chk.blockSignals(False)
            self._anim_glow_chk.blockSignals(False)
            self.anim_spin_changed.emit(spin)
            self.anim_glow_changed.emit(glow)

        # Volume
        vol_f = float(profile.get("volume", 1.0))
        self._vol_slider.blockSignals(True)
        self._vol_slider.setValue(int(vol_f * 100))
        self._vol_slider.blockSignals(False)
        if self._tts:
            self._tts.set_volume(vol_f)

        # Voice index (applied after voice list is populated)
        idx = int(profile.get("voice_index", 0))
        if self._sound_input.count() > 0:
            idx = min(idx, self._sound_input.count() - 1)
            self._sound_input.blockSignals(True)
            self._voice_combo.blockSignals(True)
            self._sound_input.setCurrentIndex(idx)
            self._voice_combo.setCurrentIndex(idx)
            self._sound_input.blockSignals(False)
            self._voice_combo.blockSignals(False)
            if self._tts:
                self._tts.set_voice(self._sound_input.itemData(idx))

    def mark_reading_started(self, text: str):
        self._last_read_text = text

    def set_online_mode(self, online: bool):
        self._online_btn.blockSignals(True)
        self._offline_btn.blockSignals(True)
        self._online_btn.setChecked(online)
        self._offline_btn.setChecked(not online)
        self._online_btn.blockSignals(False)
        self._offline_btn.blockSignals(False)

    # ════════════════════════════════════════════════════════════════════════ #
    #  WORD HIGHLIGHTING
    # ════════════════════════════════════════════════════════════════════════ #

    def highlight_word(self, start: int, end: int):
        if end <= self._last_highlight_end or end <= start:
            return
        doc    = self._text_edit.document()
        cursor = QTextCursor(doc)
        cursor.setPosition(self._last_highlight_end)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(self._highlight_color))
        cursor.setCharFormat(fmt)
        self._last_highlight_end = end

    def clear_highlight(self):
        if self._last_highlight_end == 0:
            return
        doc    = self._text_edit.document()
        cursor = QTextCursor(doc)
        cursor.select(QTextCursor.SelectionType.Document)
        fmt = QTextCharFormat()
        fmt.setBackground(QBrush())
        cursor.setCharFormat(fmt)
        self._last_highlight_end = 0

    # ════════════════════════════════════════════════════════════════════════ #
    #  SLOTS
    # ════════════════════════════════════════════════════════════════════════ #

    def _on_read_clicked(self):
        text = self._text_edit.toPlainText().strip()
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

    def _on_stop_clicked(self):
        if self._state in (ReadState.PROCESSING, ReadState.PAUSED):
            self.stop_requested.emit()
        elif self._state == ReadState.SPEAKING:
            self.pause_requested.emit()
        else:
            self.stop_requested.emit()

    def _on_voice_changed(self, index: int):
        if self._tts:
            self._tts.set_voice(self._voice_combo.itemData(index))
        if index >= 0:
            self._sound_input.blockSignals(True)
            self._sound_input.setCurrentIndex(index)
            self._sound_input.blockSignals(False)

    def _on_sound_combo_changed(self, index: int):
        if index >= 0:
            self._voice_combo.blockSignals(True)
            self._voice_combo.setCurrentIndex(index)
            self._voice_combo.blockSignals(False)
            if self._tts:
                self._tts.set_voice(self._sound_input.itemData(index))

    def _on_speed_changed(self, value: int):
        if self._tts:
            self._tts.set_rate(value)

    def _on_volume_changed(self, value: int):
        if self._tts:
            self._tts.set_volume(value / 100.0)

    # ════════════════════════════════════════════════════════════════════════ #
    #  WINDOW
    # ════════════════════════════════════════════════════════════════════════ #

    def showEvent(self, event):
        super().showEvent(event)
        self._enable_dwm_shadow()

    def _enable_dwm_shadow(self):
        """Restore Windows drop-shadow on a frameless window via DWM."""
        try:
            import ctypes
            hwnd = int(self.winId())
            # DWMWA_NCRENDERING_POLICY = 2, DWMNCRP_ENABLED = 2
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 2, ctypes.byref(ctypes.c_int(2)), ctypes.sizeof(ctypes.c_int)
            )
            margins = (ctypes.c_int * 4)(1, 1, 1, 1)
            ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, margins)
        except Exception:
            pass

    def closeEvent(self, event):
        event.ignore()
        self.hide()

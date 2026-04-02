"""
Veaja main window — matches DesignWorkFlow web prototype exactly.

Sidebar: 240px, always contrasts content (dark in light mode, light in dark mode).
Pages: Dashboard | Voice Setting | View History | Tutorial | Ask a Question | Data Privacy
"""

import os
from enum import Enum, auto

from gui.icon_utils import svg_pixmap, svg_icon

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QStackedLayout,
    QLabel, QPushButton, QTextEdit, QSlider, QComboBox, QLineEdit,
    QFrame, QScrollArea, QCheckBox, QSizePolicy, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import (
    QPalette, QColor, QPixmap, QFont,
    QPainter, QPainterPath, QTextCursor, QTextCharFormat, QBrush
)
from PyQt6.QtCore import QRectF

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
STYLES = os.path.join(os.path.dirname(__file__), "..", "styles")


# ── Sidebar QSS — LIGHT mode (sidebar is dark) ────────────────────────────────
_SIDEBAR_LIGHT_QSS = """
QWidget {
    background-color: #1a1a1a;
    color: #ffffff;
    font-family: -apple-system, 'Segoe UI', Arial, sans-serif;
}
QLabel  { background: transparent; color: #ffffff; font-size: 13px; }
QFrame  { background: #333333; max-height: 1px; border: none; }
QPushButton {
    background: transparent;
    border: none;
    color: #dddddd;
    font-size: 14px;
    text-align: left;
    padding: 2px 4px;
    border-radius: 4px;
}
QPushButton:hover { color: #ffffff; background: rgba(255,255,255,0.08); }
QPushButton#dashBtn {
    background: #ffffff;
    color: #1a1a1a;
    border: 1px solid #cccccc;
    border-radius: 5px;
    font-size: 14px;
    font-weight: 500;
    text-align: center;
    padding: 9px 0;
}
QPushButton#dashBtn:hover   { background: #f0f0f0; }
QPushButton#dashBtn:!checked {
    background: transparent;
    color: #aaaaaa;
    border: none;
    font-weight: 400;
}
QPushButton#themeBtn {
    background: transparent;
    border: none;
    color: #aaaaaa;
    font-size: 17px;
    text-align: center;
    padding: 0;
    border-radius: 4px;
}
QPushButton#themeBtn:hover { background: rgba(255,255,255,0.1); color: #ffffff; }
QLabel#helpLabel { color: #888888; font-size: 12px; }
QLabel#editIcon  { color: #aaaaaa; font-size: 13px; background: transparent; }
"""

# ── Sidebar QSS — DARK mode (sidebar is light) ────────────────────────────────
_SIDEBAR_DARK_QSS = """
QWidget {
    background-color: #f0f0f0;
    color: #1a1a1a;
    font-family: -apple-system, 'Segoe UI', Arial, sans-serif;
}
QLabel  { background: transparent; color: #1a1a1a; font-size: 13px; }
QFrame  { background: #cccccc; max-height: 1px; border: none; }
QPushButton {
    background: transparent;
    border: none;
    color: #333333;
    font-size: 14px;
    text-align: left;
    padding: 2px 4px;
    border-radius: 4px;
}
QPushButton:hover { color: #1a1a1a; background: rgba(0,0,0,0.07); }
QPushButton#dashBtn {
    background: #1a1a1a;
    color: #ffffff;
    border: 1px solid #555555;
    border-radius: 5px;
    font-size: 14px;
    font-weight: 500;
    text-align: center;
    padding: 9px 0;
}
QPushButton#dashBtn:hover   { background: #333333; }
QPushButton#dashBtn:!checked {
    background: transparent;
    color: #888888;
    border: none;
    font-weight: 400;
}
QPushButton#themeBtn {
    background: transparent;
    border: none;
    color: #666666;
    font-size: 17px;
    text-align: center;
    padding: 0;
    border-radius: 4px;
}
QPushButton#themeBtn:hover { background: rgba(0,0,0,0.07); color: #1a1a1a; }
QLabel#helpLabel { color: #666666; font-size: 12px; }
QLabel#editIcon  { color: #888888; font-size: 13px; background: transparent; }
"""


# ── Read state ─────────────────────────────────────────────────────────────────
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


def _make_square_pixmap(path: str, size: int) -> QPixmap | None:
    """Scale image to fill a square of the given size."""
    raw = QPixmap(path)
    if raw.isNull():
        return None
    return raw.scaled(size, size,
                      Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                      Qt.TransformationMode.SmoothTransformation)


# ══════════════════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):

    # ── Signals ────────────────────────────────────────────────────────────────
    read_requested    = pyqtSignal(str)
    pause_requested   = pyqtSignal()
    resume_requested  = pyqtSignal()
    stop_requested    = pyqtSignal()
    quit_requested    = pyqtSignal()
    theme_changed     = pyqtSignal(bool)   # True = dark
    terms_requested   = pyqtSignal()
    profile_requested = pyqtSignal()
    mode_changed      = pyqtSignal(bool)   # True = online
    tour_requested    = pyqtSignal()

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

        # SVG icon labels/buttons — set during _build_sidebar, recolored in theme
        self._edit_icon_lbl: QLabel | None    = None
        self._tutorial_btn: QPushButton | None = None
        self._ask_btn: QPushButton | None      = None
        self._privacy_btn: QPushButton | None  = None

        self.setWindowTitle("Veaja")
        self.setMinimumSize(780, 580)
        self.resize(900, 660)
        self._center()
        self._build_ui()
        self._apply_theme()

    # ════════════════════════════════════════════════════════════════════════ #
    #  UI CONSTRUCTION
    # ════════════════════════════════════════════════════════════════════════ #

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._sidebar_widget = self._build_sidebar()
        root.addWidget(self._sidebar_widget)

        # Content stack (pages 0-5)
        self._content_stack = QStackedWidget()
        self._content_stack.setObjectName("contentStack")
        self._content_stack.addWidget(self._build_dashboard_page())  # 0
        self._content_stack.addWidget(self._build_settings_page())   # 1
        self._content_stack.addWidget(self._build_history_page())    # 2
        self._content_stack.addWidget(self._build_ask_page())        # 3
        self._content_stack.addWidget(self._build_privacy_page())    # 4
        self._content_stack.addWidget(self._build_tutorial_page())   # 5
        root.addWidget(self._content_stack, 1)

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
        self._profile_frame.setFixedSize(82, 82)
        pf_lay = QVBoxLayout(self._profile_frame)
        pf_lay.setContentsMargins(0, 0, 0, 0)

        self._header_logo = QLabel()
        self._header_logo.setFixedSize(76, 76)
        self._header_logo.setScaledContents(True)
        self._header_logo.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._header_logo.mousePressEvent = lambda _: self.profile_requested.emit()
        pf_lay.addWidget(self._header_logo, 0, Qt.AlignmentFlag.AlignCenter)
        self._reload_header_logo()

        photo_row = QHBoxLayout()
        photo_row.addStretch()
        photo_row.addWidget(self._profile_frame)
        photo_row.addStretch()
        profile_sec.addLayout(photo_row)

        # Name + edit icon
        name_row = QHBoxLayout()
        name_row.setSpacing(6)
        name_row.addStretch()
        self._title_label = QLabel("Veaja")
        self._title_label.setObjectName("profileName")
        self._title_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
        self._title_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self._title_label.mousePressEvent = lambda _: self.profile_requested.emit()
        name_row.addWidget(self._title_label)
        edit_ic = QLabel()
        edit_ic.setObjectName("editIcon")
        edit_ic.setFixedSize(14, 14)
        edit_ic.setScaledContents(True)
        edit_ic.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_ic.mousePressEvent = lambda _: self.profile_requested.emit()
        self._edit_icon_lbl = edit_ic
        name_row.addWidget(edit_ic)
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

        outer.addStretch()

        # ── Help section ──────────────────────────────────────────────────
        help_lbl = QLabel("Help")
        help_lbl.setObjectName("helpLabel")
        outer.addWidget(help_lbl)
        outer.addSpacing(12)

        help_col = QVBoxLayout()
        help_col.setSpacing(12)
        self._tutorial_btn = self._nav_link("  Tutorial",       5)
        self._ask_btn      = self._nav_link("  Ask a Question", 3)
        self._privacy_btn  = self._nav_link("  Data Privacy",   4)
        help_col.addWidget(self._tutorial_btn)
        help_col.addWidget(self._ask_btn)
        help_col.addWidget(self._privacy_btn)
        outer.addLayout(help_col)

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

    def navigate_if_needed(self, page_idx: int, tab: int | None = None):
        """Used by TourOverlay for live-teach navigation."""
        self._navigate(page_idx)
        if tab is not None and page_idx == 0:
            self._switch_tab(tab)

    # ── Dashboard page ─────────────────────────────────────────────────────────

    def _build_dashboard_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("contentPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(0)

        title = QLabel("Veaja Feature")
        title.setObjectName("pageTitle")
        lay.addWidget(title)
        lay.addSpacing(4)

        # Tab bar
        tab_bar = QWidget()
        tab_bar.setObjectName("tabBar")
        tb = QHBoxLayout(tab_bar)
        tb.setContentsMargins(0, 0, 0, 0)
        tb.setSpacing(0)

        self._tab_overlay_btn = QPushButton("Overlay")
        self._tab_overlay_btn.setObjectName("tabBtn")
        self._tab_overlay_btn.setCheckable(True)
        self._tab_overlay_btn.setChecked(True)
        self._tab_overlay_btn.setFixedHeight(36)
        self._tab_overlay_btn.clicked.connect(lambda: self._switch_tab(0))

        self._tab_text_btn = QPushButton("Text label")
        self._tab_text_btn.setObjectName("tabBtn")
        self._tab_text_btn.setCheckable(True)
        self._tab_text_btn.setChecked(False)
        self._tab_text_btn.setFixedHeight(36)
        self._tab_text_btn.clicked.connect(lambda: self._switch_tab(1))

        tb.addWidget(self._tab_overlay_btn)
        tb.addWidget(self._tab_text_btn)
        tb.addStretch()
        lay.addWidget(tab_bar)

        # Tab content stack
        self._tab_stack = QStackedWidget()
        self._tab_stack.addWidget(self._build_overlay_tab())  # 0
        self._tab_stack.addWidget(self._build_text_tab())     # 1
        lay.addWidget(self._tab_stack, 1)
        return page

    def _switch_tab(self, idx: int):
        self._tab_stack.setCurrentIndex(idx)
        self._tab_overlay_btn.setChecked(idx == 0)
        self._tab_text_btn.setChecked(idx == 1)

    def _build_overlay_tab(self) -> QWidget:
        frame = QWidget()
        frame.setObjectName("tabPage")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 18, 0, 0)
        lay.setSpacing(12)

        # ── Bordered card ─────────────────────────────────────────────────
        overlay_box = QWidget()
        overlay_box.setObjectName("overlayBox")
        ob_lay = QVBoxLayout(overlay_box)
        ob_lay.setContentsMargins(0, 0, 0, 0)
        ob_lay.setSpacing(0)

        # Stack: text layer (bottom) + floating pill layer (top)
        stack_host = QWidget()
        stack_host.setObjectName("overlayStack")
        stack_lay = QStackedLayout(stack_host)
        stack_lay.setStackingMode(QStackedLayout.StackingMode.StackAll)
        stack_lay.setContentsMargins(0, 0, 0, 0)

        # ── Layer 0 — scrollable text preview ────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent;")

        text_inner = QWidget()
        text_inner.setStyleSheet("background: transparent;")
        ti_lay = QVBoxLayout(text_inner)
        ti_lay.setContentsMargins(22, 22, 22, 22)
        ti_lay.setSpacing(0)

        self._overlay_text_view = QLabel(
            "Select text in any window and press  Ctrl+R  to read aloud,\n"
            "or press  Ctrl+C  and the overlay pill will appear automatically.\n\n"
            "The floating pill tracks each word in real-time so you can\n"
            "follow along without switching windows."
        )
        self._overlay_text_view.setObjectName("bodyText")
        self._overlay_text_view.setWordWrap(True)
        self._overlay_text_view.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        ti_lay.addWidget(self._overlay_text_view)
        ti_lay.addStretch()
        scroll.setWidget(text_inner)
        stack_lay.addWidget(scroll)

        # ── Layer 1 — floating pill overlay (transparent container) ───────
        pill_float = QWidget()
        pill_float.setStyleSheet("background: transparent;")
        pill_float.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        pf_lay = QVBoxLayout(pill_float)
        pf_lay.setContentsMargins(18, 0, 0, 18)
        pf_lay.setSpacing(0)
        pf_lay.addStretch()

        pill_row = QHBoxLayout()
        pill_row.setSpacing(0)

        pill = QWidget()
        pill.setObjectName("pillWidget")
        pill_lay = QHBoxLayout(pill)
        pill_lay.setContentsMargins(7, 6, 14, 6)
        pill_lay.setSpacing(9)

        self._pill_logo = QLabel()
        self._pill_logo.setObjectName("pillLogo")
        self._pill_logo.setFixedSize(26, 26)
        self._pill_logo.setScaledContents(True)
        self._reload_pill_logo()
        pill_lay.addWidget(self._pill_logo)

        tap_lbl = QLabel("Tap to read")
        tap_lbl.setStyleSheet("font-size: 12px; background: transparent;")
        pill_lay.addWidget(tap_lbl)

        refresh_lbl = QLabel("↻")
        refresh_lbl.setObjectName("refreshIcon")
        pill_lay.addWidget(refresh_lbl)

        pill_row.addWidget(pill)
        pill_row.addStretch()
        pf_lay.addLayout(pill_row)
        stack_lay.addWidget(pill_float)
        stack_lay.setCurrentIndex(1)

        ob_lay.addWidget(stack_host, 1)
        lay.addWidget(overlay_box, 1)

        # ── Hint bar (outside card) ───────────────────────────────────────
        hint = QLabel(
            "On window:  select text  and  Press  Ctrl+R  to read\n"
            "or  Ctrl+C  to pop up overlay"
        )
        hint.setObjectName("hintBar")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(hint)
        return frame

    def _build_text_tab(self) -> QWidget:
        frame = QWidget()
        frame.setObjectName("tabPage")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 18, 0, 0)
        lay.setSpacing(0)

        # ── Text input box ────────────────────────────────────────────────
        text_box = QWidget()
        text_box.setObjectName("textLabelBox")
        tb_lay = QVBoxLayout(text_box)
        tb_lay.setContentsMargins(0, 0, 0, 0)
        tb_lay.setSpacing(0)

        self._text_edit = QTextEdit()
        self._text_edit.setObjectName("textEdit")
        self._text_edit.setPlaceholderText("Paste or type text here to read aloud…")
        self._text_edit.textChanged.connect(self._on_text_changed)
        tb_lay.addWidget(self._text_edit, 1)

        # ── Footer: counter | Clear — Stop — Read ─────────────────────────
        footer = QWidget()
        footer.setObjectName("textFooter")
        ft_lay = QHBoxLayout(footer)
        ft_lay.setContentsMargins(18, 10, 18, 10)
        ft_lay.setSpacing(10)

        # Word / character counter (left)
        self._text_counter = QLabel("0 words · 0 chars")
        self._text_counter.setObjectName("settingsLabel")
        self._text_counter.setStyleSheet("font-size: 12px;")
        ft_lay.addWidget(self._text_counter)

        ft_lay.addStretch()

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("btnOutline")
        clear_btn.setFixedSize(60, 30)
        clear_btn.setToolTip("Clear text")
        clear_btn.clicked.connect(self._text_edit.clear)
        ft_lay.addWidget(clear_btn)

        # Stop button (visible, enabled only while speaking/paused)
        self._stop_btn = QPushButton("■  Stop")
        self._stop_btn.setObjectName("stopBtn")
        self._stop_btn.setFixedSize(72, 30)
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        ft_lay.addWidget(self._stop_btn)

        # Read / Pause / Resume button
        self._read_btn = QPushButton("Read")
        self._read_btn.setObjectName("btnOutline")
        self._read_btn.setFixedSize(80, 30)
        self._read_btn.clicked.connect(self._on_read_clicked)
        ft_lay.addWidget(self._read_btn)

        tb_lay.addWidget(footer)
        lay.addWidget(text_box, 1)
        return frame

    def _on_text_changed(self):
        text = self._text_edit.toPlainText()
        words = len(text.split()) if text.strip() else 0
        chars = len(text)
        self._text_counter.setText(f"{words} word{'s' if words != 1 else ''} · {chars} char{'s' if chars != 1 else ''}")

    # ── Voice Setting page ─────────────────────────────────────────────────────

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("contentPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Top action: Save
        top = QWidget()
        top.setObjectName("pageTopAction")
        t_lay = QHBoxLayout(top)
        t_lay.setContentsMargins(32, 20, 32, 16)
        t_lay.addStretch()
        save_btn = QPushButton("Save")
        save_btn.setObjectName("btnOutline")
        save_btn.setFixedSize(64, 28)
        save_btn.clicked.connect(lambda: None)
        t_lay.addWidget(save_btn)
        lay.addWidget(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("settingsScroll")

        sc = QWidget()
        sc_lay = QVBoxLayout(sc)
        sc_lay.setContentsMargins(32, 0, 32, 32)
        sc_lay.setSpacing(20)

        # ── Shape ─────────────────────────────────────────────────────────
        shape_lbl = QLabel("Shape")
        shape_lbl.setObjectName("settingsLabel")
        sc_lay.addWidget(shape_lbl)

        shape_box = QWidget()
        shape_box.setObjectName("shapeBox")
        sb_lay = QVBoxLayout(shape_box)
        sb_lay.setContentsMargins(16, 16, 16, 8)
        sb_lay.setSpacing(14)

        # Circle row
        circle_row = self._shape_row("Circle", is_circle=True, checked=True)
        self._shape_circle = circle_row[0]
        sb_lay.addWidget(circle_row[1])

        # Rectangle row
        rect_row = self._shape_row("Rectangle", is_circle=False, checked=False)
        self._shape_rect = rect_row[0]
        sb_lay.addWidget(rect_row[1])

        # Mutually exclusive
        self._shape_circle.toggled.connect(
            lambda c: self._shape_rect.setChecked(not c) if c else None
        )
        self._shape_rect.toggled.connect(
            lambda c: self._shape_circle.setChecked(not c) if c else None
        )
        sc_lay.addWidget(shape_box)

        # ── Mode + Language ───────────────────────────────────────────────
        ml_row = QHBoxLayout()
        ml_row.setSpacing(48)

        mode_col = QVBoxLayout()
        mode_col.setSpacing(8)
        mode_lbl = QLabel("Mode")
        mode_lbl.setObjectName("settingsLabel")
        mode_col.addWidget(mode_lbl)
        self._online_btn = QCheckBox("Online Mode")
        self._online_btn.setObjectName("settingsCheck")
        self._online_btn.setChecked(True)
        self._online_btn.toggled.connect(self._on_mode_checkbox)
        mode_col.addWidget(self._online_btn)
        self._offline_btn = QCheckBox("Offline Mode")
        self._offline_btn.setObjectName("settingsCheck")
        self._offline_btn.toggled.connect(
            lambda c: (self._online_btn.blockSignals(True),
                       self._online_btn.setChecked(not c),
                       self._online_btn.blockSignals(False)) if c else None
        )
        mode_col.addWidget(self._offline_btn)
        ml_row.addLayout(mode_col)

        lang_col = QVBoxLayout()
        lang_col.setSpacing(8)
        lang_lbl = QLabel("Language")
        lang_lbl.setObjectName("settingsLabel")
        lang_col.addWidget(lang_lbl)
        lang_inline = QHBoxLayout()
        lang_inline.setSpacing(10)
        self._lang_btn = QPushButton("English")
        self._lang_btn.setObjectName("btnOutline")
        self._lang_btn.setFixedHeight(28)
        lang_inline.addWidget(self._lang_btn)
        lang_inline.addWidget(self._inline_edit_icon())
        lang_inline.addStretch()
        lang_col.addLayout(lang_inline)
        ml_row.addLayout(lang_col)
        ml_row.addStretch()
        sc_lay.addLayout(ml_row)

        # ── Sound + Speed ─────────────────────────────────────────────────
        ss_row = QHBoxLayout()
        ss_row.setSpacing(48)

        sound_col = QVBoxLayout()
        sound_col.setSpacing(8)
        sound_lbl = QLabel("Sound")
        sound_lbl.setObjectName("settingsLabel")
        sound_col.addWidget(sound_lbl)
        sound_inline = QHBoxLayout()
        sound_inline.setSpacing(10)
        self._sound_input = QLineEdit("Alice")
        self._sound_input.setObjectName("settingsInput")
        self._sound_input.setFixedWidth(140)
        sound_inline.addWidget(self._sound_input)
        sound_inline.addWidget(self._inline_edit_icon())
        sound_inline.addStretch()
        sound_col.addLayout(sound_inline)
        ss_row.addLayout(sound_col)

        speed_col = QVBoxLayout()
        speed_col.setSpacing(8)
        speed_lbl = QLabel("Speed")
        speed_lbl.setObjectName("settingsLabel")
        speed_col.addWidget(speed_lbl)
        spd_inline = QHBoxLayout()
        spd_inline.setSpacing(8)
        spd_inline.addWidget(QLabel("🐢"))
        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(50, 400)
        self._speed_slider.setValue(175)
        self._speed_slider.setObjectName("speedSlider")
        self._speed_slider.valueChanged.connect(self._on_speed_changed)
        spd_inline.addWidget(self._speed_slider, 1)
        spd_inline.addWidget(QLabel("🐇"))
        speed_col.addLayout(spd_inline)
        ss_row.addLayout(speed_col)
        ss_row.addStretch()
        sc_lay.addLayout(ss_row)

        # Hidden combo (kept for AppController / TourOverlay compat)
        self._voice_combo = QComboBox()
        self._voice_combo.setVisible(False)
        self._voice_combo.currentIndexChanged.connect(self._on_voice_changed)
        sc_lay.addWidget(self._voice_combo)

        # Hidden volume slider (kept for compat)
        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(100)
        self._vol_slider.setVisible(False)
        self._vol_slider.valueChanged.connect(self._on_volume_changed)
        sc_lay.addWidget(self._vol_slider)

        sc_lay.addStretch()
        scroll.setWidget(sc)
        lay.addWidget(scroll, 1)
        return page

    def _shape_row(self, label: str, is_circle: bool,
                   checked: bool) -> tuple[QCheckBox, QWidget]:
        """Returns (checkbox, row_widget) for a shape option with previews."""
        row = QWidget()
        row_lay = QVBoxLayout(row)
        row_lay.setContentsMargins(0, 0, 0, 0)
        row_lay.setSpacing(10)

        chk = QCheckBox(label)
        chk.setObjectName("settingsCheck")
        chk.setChecked(checked)
        row_lay.addWidget(chk)

        previews_row = QHBoxLayout()
        previews_row.setSpacing(12)
        previews_row.addWidget(self._mini_preview(is_circle, dark=True))
        previews_row.addWidget(self._mini_preview(is_circle, dark=False))
        previews_row.addStretch()
        row_lay.addLayout(previews_row)
        return chk, row

    def _mini_preview(self, is_circle: bool, dark: bool) -> QWidget:
        """Small shape preview card (dark or light background)."""
        card = QWidget()
        card.setFixedSize(150, 90)
        card.setObjectName("miniPreviewDark" if dark else "miniPreviewLight")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(10, 10, 10, 8)
        card_lay.setSpacing(6)

        pill = QWidget()
        pill.setObjectName("miniPillDark" if dark else "miniPillLight")
        pill.setFixedHeight(22)
        p_lay = QHBoxLayout(pill)
        p_lay.setContentsMargins(4, 2, 8, 2)
        p_lay.setSpacing(4)
        dot = QWidget()
        dot.setFixedSize(12, 12)
        dot.setObjectName("miniDotLight" if dark else "miniDotDark")
        p_lay.addWidget(dot)
        tap = QLabel("Tap to read")
        tap.setObjectName("miniTextLight" if dark else "miniTextDark")
        tap.setFont(QFont("Segoe UI", 7))
        p_lay.addWidget(tap)
        ref = QLabel("↻")
        ref.setObjectName("miniTextLight" if dark else "miniTextDark")
        ref.setFont(QFont("Segoe UI", 7))
        p_lay.addWidget(ref)
        card_lay.addWidget(pill)

        speech = QLabel("Hi, I'm Veaja. What would you like me to read for you today?")
        speech.setObjectName("miniSpeechLight" if dark else "miniSpeechDark")
        speech.setWordWrap(True)
        speech.setFont(QFont("Segoe UI", 7))
        card_lay.addWidget(speech, 1)
        return card

    def _inline_edit_icon(self) -> QLabel:
        lbl = QLabel("✎")
        lbl.setObjectName("inlineEdit")
        return lbl

    def _on_mode_checkbox(self, checked: bool):
        self._offline_btn.blockSignals(True)
        self._offline_btn.setChecked(not checked)
        self._offline_btn.blockSignals(False)
        self.mode_changed.emit(checked)

    # ── History page ───────────────────────────────────────────────────────────

    def _build_history_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("contentPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        hdr = QWidget()
        hdr.setObjectName("pageHeader")
        h_lay = QHBoxLayout(hdr)
        h_lay.setContentsMargins(32, 28, 32, 20)
        title = QLabel("History recall")
        title.setObjectName("pageTitle")
        h_lay.addWidget(title)
        h_lay.addStretch()
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("btnOutline")
        clear_btn.setFixedSize(56, 28)
        clear_btn.clicked.connect(self._clear_history)
        h_lay.addWidget(clear_btn)
        lay.addWidget(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._history_cards_widget = QWidget()
        self._history_cards_layout = QVBoxLayout(self._history_cards_widget)
        self._history_cards_layout.setContentsMargins(32, 0, 32, 32)
        self._history_cards_layout.setSpacing(14)
        self._history_cards_layout.addStretch()

        scroll.setWidget(self._history_cards_widget)
        lay.addWidget(scroll, 1)

        # Hidden QListWidget kept for TourOverlay compat (spotlighting)
        self._history_list = QListWidget()
        self._history_list.setVisible(False)
        self._history_list.itemDoubleClicked.connect(self._on_history_item)
        # Also create prev/old lists for compat
        self._history_prev_list = QListWidget()
        self._history_prev_list.setVisible(False)
        self._history_old_list  = QListWidget()
        self._history_old_list.setVisible(False)
        lay.addWidget(self._history_list)
        lay.addWidget(self._history_prev_list)
        lay.addWidget(self._history_old_list)
        return page

    def _make_history_card(self, section_label: str, short: str,
                           full_text: str) -> QWidget:
        card = QWidget()
        card.setObjectName("historyCard")

        outer = QHBoxLayout(card)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(0)

        inner = QVBoxLayout()
        inner.setSpacing(10)

        # Header row: label + progress bar + dot
        hdr = QHBoxLayout()
        hdr.setSpacing(12)
        lbl = QLabel(section_label)
        lbl.setObjectName("historyCardLabel")
        lbl.setFixedWidth(62)
        hdr.addWidget(lbl)

        prog = QWidget()
        prog.setObjectName("historyProgress")
        prog.setFixedHeight(6)
        prog_lay = QHBoxLayout(prog)
        prog_lay.setContentsMargins(0, 0, 0, 0)
        prog_lay.setSpacing(4)
        fill = QWidget()
        fill.setObjectName("progFill")
        fill.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        rest = QWidget()
        rest.setObjectName("progRest")
        rest.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        prog_lay.addWidget(fill, 2)
        prog_lay.addWidget(rest, 1)
        hdr.addWidget(prog, 1)

        dot = QLabel("•")
        dot.setObjectName("historyDot")
        hdr.addWidget(dot)
        inner.addLayout(hdr)

        # Body text
        body = QLabel(short)
        body.setObjectName("historyText")
        body.setWordWrap(True)
        inner.addWidget(body)

        outer.addLayout(inner, 1)

        # Delete button (right side)
        del_btn = QPushButton("🗑")
        del_btn.setObjectName("historyDel")
        del_btn.setFixedSize(28, 28)
        del_btn.setFlat(True)
        del_btn.setToolTip("Delete")
        del_btn.clicked.connect(lambda: self._delete_history_entry(full_text, card))
        outer.addWidget(del_btn, 0, Qt.AlignmentFlag.AlignTop)
        return card

    def _delete_history_entry(self, full_text: str, card: QWidget):
        if full_text in self._history:
            idx = self._history.index(full_text)
            self._history.pop(idx)
            self._history_shorts.pop(idx)
        card.setParent(None)
        card.deleteLater()
        self._rebuild_history_lists()

    # ── Ask a Question page ────────────────────────────────────────────────────

    def _build_ask_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("contentPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        hdr = QWidget()
        hdr.setObjectName("pageHeader")
        h_lay = QHBoxLayout(hdr)
        h_lay.setContentsMargins(32, 28, 32, 20)
        title = QLabel("General")
        title.setObjectName("pageTitle")
        h_lay.addWidget(title)
        h_lay.addStretch()
        email_btn = QPushButton("Email")
        email_btn.setObjectName("btnOutline")
        email_btn.setFixedSize(60, 28)
        h_lay.addWidget(email_btn)
        lay.addWidget(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        sc = QWidget()
        sc_lay = QVBoxLayout(sc)
        sc_lay.setContentsMargins(32, 0, 32, 32)
        sc_lay.setSpacing(14)
        for q, a in [
            ("Q1. How to use overlay feature?",
             "Select text in any PDF, Word doc, or browser.\n"
             "Press Ctrl+R to read immediately, or Ctrl+C to show the overlay pill.\n"
             "The pill highlights each word in yellow as Veaja reads aloud."),
            ("Q2. Do you collect data from us?",
             "No. Veaja does not collect personal data or analytics.\n"
             "In Online mode, text is sent to Microsoft's servers for TTS only.\n"
             "In Offline mode, all processing happens entirely on your device."),
            ("Q3. Can I use this app on mobile phone or tablet?",
             "Currently Veaja is a desktop app for Windows, macOS, and Linux.\n"
             "Mobile support (Android and iOS) is planned for a future release."),
        ]:
            sc_lay.addWidget(self._info_card(q, a))
        sc_lay.addStretch()
        scroll.setWidget(sc)
        lay.addWidget(scroll, 1)
        return page

    # ── Data Privacy page ──────────────────────────────────────────────────────

    def _build_privacy_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("contentPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(0)

        title = QLabel("Term of use")
        title.setObjectName("pageTitle")
        lay.addWidget(title)
        lay.addSpacing(20)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        sc = QWidget()
        sc_lay = QVBoxLayout(sc)
        sc_lay.setContentsMargins(0, 0, 0, 0)
        sc_lay.setSpacing(14)
        for t, body in [
            ("T1. Offline usage:",
             "All text-to-speech processing is performed entirely on your device.\n"
             "No data is transmitted to external servers.\n"
             "Audio files are stored locally at ~/.veaja/audio/ and cleared each session.\n"
             "You are responsible for the content you choose to read."),
            ("T2. Online usage:",
             "Text is sent to Microsoft Azure Cognitive Services for neural TTS synthesis.\n"
             "Veaja does not store, log, or share this text.\n"
             "Microsoft's privacy policy applies to data sent via their API.\n"
             "No account or API key is required — Veaja uses Edge browser's built-in TTS."),
        ]:
            sc_lay.addWidget(self._info_card(t, body))
        sc_lay.addStretch()
        scroll.setWidget(sc)
        lay.addWidget(scroll, 1)
        return page

    # ── Tutorial page (static + launch interactive button) ────────────────────

    def _build_tutorial_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("contentPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(0)

        title = QLabel("Tutorial")
        title.setObjectName("pageTitle")
        lay.addWidget(title)
        lay.addSpacing(20)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        sc = QWidget()
        sc_lay = QVBoxLayout(sc)
        sc_lay.setContentsMargins(0, 0, 0, 0)
        sc_lay.setSpacing(14)

        for t, body in [
            ("Getting Started",
             "Select any text on your screen and press Ctrl+R to have Veaja read it aloud.\n"
             "Use Ctrl+C to pop up the overlay pill anywhere on your screen."),
            ("Using Text Label",
             "Navigate to Dashboard → Text label tab.\n"
             "Type or paste your text into the input area, then click Read to start playback."),
            ("Customising Your Experience",
             "Visit Voice Setting to choose the overlay shape, select a voice, adjust speed,\n"
             "change language, and switch between Online and Offline mode."),
        ]:
            sc_lay.addWidget(self._info_card(t, body))

        # Interactive tour launch button
        sc_lay.addSpacing(8)
        tour_btn = QPushButton("▶  Start Interactive Tutorial")
        tour_btn.setObjectName("tourLaunchBtn")
        tour_btn.setFixedHeight(38)
        tour_btn.clicked.connect(self.tour_requested)
        sc_lay.addWidget(tour_btn)
        sc_lay.addStretch()
        scroll.setWidget(sc)
        lay.addWidget(scroll, 1)
        return page

    # ── Shared card widget ─────────────────────────────────────────────────────

    def _info_card(self, title: str, body: str) -> QWidget:
        card = QWidget()
        card.setObjectName("infoCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(9)
        t = QLabel(title)
        t.setObjectName("cardTitle")
        t.setWordWrap(True)
        lay.addWidget(t)
        b = QLabel(body)
        b.setObjectName("cardBody")
        b.setWordWrap(True)
        lay.addWidget(b)
        return card

    # ════════════════════════════════════════════════════════════════════════ #
    #  PUBLIC API (AppController-compatible)
    # ════════════════════════════════════════════════════════════════════════ #

    def populate_voices(self, voices: list[dict]):
        self._voice_combo.blockSignals(True)
        self._voice_combo.clear()
        for v in voices:
            self._voice_combo.addItem(v["name"], v["id"])
            # Sync first voice name to sound input
        if voices:
            self._sound_input.setText(voices[0]["name"])
        self._voice_combo.blockSignals(False)

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
            self._stop_btn.setEnabled(False)
        elif state == ReadState.PROCESSING:
            btn.setText("⏳…")
            btn.setProperty("btnState", "processing")
            btn.setEnabled(False)
            self._stop_btn.setEnabled(True)
        elif state == ReadState.SPEAKING:
            btn.setText("⏸")
            btn.setProperty("btnState", "active")
            btn.setEnabled(True)
            self._stop_btn.setEnabled(True)
        elif state == ReadState.PAUSED:
            btn.setText("▶")
            btn.setProperty("btnState", "paused")
            btn.setEnabled(True)
            self._stop_btn.setEnabled(True)
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
        self._title_label.setText(name)
        self.setWindowTitle(name)
        self._reload_header_logo(profile.get("logo_path"))
        color = profile.get("highlight_color", "#FFD60A")
        if color:
            self._highlight_color = color

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
            self._sound_input.setText(self._voice_combo.itemText(index))

    def _on_speed_changed(self, value: int):
        if self._tts:
            self._tts.set_rate(value)

    def _on_volume_changed(self, value: int):
        if self._tts:
            self._tts.set_volume(value / 100.0)

    def _on_history_item(self, item: QListWidgetItem):
        text = item.data(Qt.ItemDataRole.UserRole)
        if text:
            self._text_edit.setPlainText(text)
            self._navigate(0)
            self._switch_tab(1)

    # ── History management ─────────────────────────────────────────────────────

    def _add_history(self, text: str):
        if text in self._history:
            return
        short = text[:80] + ("…" if len(text) > 80 else "")
        self._history.insert(0, text)
        self._history_shorts.insert(0, short)
        self._history        = self._history[:20]
        self._history_shorts = self._history_shorts[:20]
        self._rebuild_history_lists()

    def _rebuild_history_lists(self):
        # Clear hidden compat lists
        self._history_list.clear()
        self._history_prev_list.clear()
        self._history_old_list.clear()

        # Clear card widgets (except the stretch at end)
        while self._history_cards_layout.count() > 1:
            item = self._history_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        section_labels = (
            ["Recent"]   * 7  +
            ["Previous"] * 7  +
            ["Old"]      * 6
        )
        for i, (full, short) in enumerate(
            zip(self._history, self._history_shorts)
        ):
            sec = section_labels[i] if i < len(section_labels) else "Old"
            # Card widget
            card = self._make_history_card(sec, short, full)
            self._history_cards_layout.insertWidget(
                self._history_cards_layout.count() - 1, card
            )
            # Hidden list item for TourOverlay compat
            li = QListWidgetItem(short)
            li.setData(Qt.ItemDataRole.UserRole, full)
            if i < 7:
                self._history_list.addItem(li)
            elif i < 14:
                self._history_prev_list.addItem(li)
            else:
                self._history_old_list.addItem(li)

    def _clear_history(self):
        self._history.clear()
        self._history_shorts.clear()
        self._rebuild_history_lists()

    # ════════════════════════════════════════════════════════════════════════ #
    #  THEME
    # ════════════════════════════════════════════════════════════════════════ #

    def _toggle_theme(self):
        self._dark = not self._dark
        self._reload_header_logo()
        self._reload_pill_logo()
        self._apply_theme()
        self.theme_changed.emit(self._dark)

    def _apply_theme(self):
        # Content area QSS
        qss_file = "dark.qss" if self._dark else "light.qss"
        path = os.path.join(STYLES, qss_file)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        # Sidebar (inverted)
        self._apply_sidebar_theme()

    def _apply_sidebar_theme(self):
        if self._sidebar_widget is None:
            return
        qss = _SIDEBAR_DARK_QSS if self._dark else _SIDEBAR_LIGHT_QSS
        self._sidebar_widget.setStyleSheet(qss)

        # Icon color: light icons on dark sidebar (light mode),
        #             dark icons on light sidebar (dark mode)
        icon_color = "#444444" if self._dark else "#dddddd"

        # Theme toggle button icon
        theme_svg = "dark_theme_icon.svg" if self._dark else "light_theme_icon.svg"
        theme_px = svg_pixmap(os.path.join(ASSETS, theme_svg), icon_color, 18)
        if theme_px:
            self._theme_btn.setIcon(svg_icon(os.path.join(ASSETS, theme_svg), icon_color, 18))
            self._theme_btn.setIconSize(theme_px.size())
        else:
            self._theme_btn.setText("☀" if self._dark else "☾")

        # Edit icon next to profile name
        if self._edit_icon_lbl is not None:
            edit_px = svg_pixmap(os.path.join(ASSETS, "edit_icon.svg"), icon_color, 14)
            if edit_px:
                self._edit_icon_lbl.setPixmap(edit_px)

        # Tutorial nav button icon
        if self._tutorial_btn is not None:
            tut_icon = svg_icon(os.path.join(ASSETS, "tutorial_icon.svg"), icon_color, 16)
            self._tutorial_btn.setIcon(tut_icon)

        # Ask a Question nav button icon
        if self._ask_btn is not None:
            ask_icon = svg_icon(os.path.join(ASSETS, "Ask_a_question_icon.svg"), icon_color, 16)
            self._ask_btn.setIcon(ask_icon)

        # Data Privacy nav button icon
        if self._privacy_btn is not None:
            priv_icon = svg_icon(os.path.join(ASSETS, "data_privacy_icon.svg"), icon_color, 16)
            self._privacy_btn.setIcon(priv_icon)

        # Profile glow border
        glow = "#f5a623" if self._dark else "#7c6fff"
        bg   = "#000000"
        if self._profile_frame:
            self._profile_frame.setStyleSheet(
                f"QWidget {{ background: {bg}; border-radius: 10px;"
                f" border: 3px solid {glow}; }}"
            )
        # Profile name color follows sidebar text
        name_color = "#1a1a1a" if self._dark else "#ffffff"
        self._title_label.setStyleSheet(
            f"color: {name_color}; font-size: 15px;"
            f" font-weight: 500; background: transparent;"
        )

    def _reload_header_logo(self, logo_path: str | None = None):
        if logo_path is not None:
            self._logo_path = logo_path if (logo_path and os.path.exists(logo_path)) else None
        if self._logo_path and os.path.exists(self._logo_path):
            px = _make_square_pixmap(self._logo_path, 76)
        else:
            name = "logo_light.png" if self._dark else "logo_dark.png"
            path = os.path.join(ASSETS, name)
            px = _make_square_pixmap(path, 76) if os.path.exists(path) else None
        if px and hasattr(self, "_header_logo"):
            self._header_logo.setPixmap(px)

    def _reload_pill_logo(self):
        if not hasattr(self, "_pill_logo"):
            return
        name = "logo_light.png" if self._dark else "logo_dark.png"
        path = os.path.join(ASSETS, name)
        px = _make_square_pixmap(path, 26) if os.path.exists(path) else None
        if px:
            self._pill_logo.setPixmap(px)

    # ════════════════════════════════════════════════════════════════════════ #
    #  WINDOW
    # ════════════════════════════════════════════════════════════════════════ #

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def _center(self):
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width()  - self.width())  // 2,
            (screen.height() - self.height()) // 2,
        )

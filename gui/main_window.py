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
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QPoint
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
QPushButton:hover   { color: #ffffff; background: rgba(255,255,255,0.08); }
/* Nav links: 50% opacity on active page, 100% otherwise */
QPushButton:checked { color: rgba(221,221,221,0.50); background: transparent; }
/* Dashboard — filled when active */
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
/* Dashboard — border-only when NOT active */
QPushButton#dashBtn:!checked {
    background: transparent;
    color: #aaaaaa;
    border: 1px solid rgba(255,255,255,0.25);
    font-weight: 400;
}
/* Override the general :checked dimming for dashBtn — keep it opaque when active */
QPushButton#dashBtn:checked { background: #ffffff; color: #1a1a1a; }
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
QLabel#profileName { color: #ffffff; font-size: 15px; font-weight: 600; background: transparent; }
QLabel#helpLabel   { color: #cccccc; font-size: 13px; font-weight: 600; background: transparent; }
QLabel#editIcon    { color: #aaaaaa; font-size: 13px; background: transparent; }
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
QPushButton:hover   { color: #1a1a1a; background: rgba(0,0,0,0.07); }
/* Nav links: 50% opacity on active page, 100% otherwise */
QPushButton:checked { color: rgba(51,51,51,0.50); background: transparent; }
/* Dashboard — filled when active */
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
/* Dashboard — border-only when NOT active */
QPushButton#dashBtn:!checked {
    background: transparent;
    color: #888888;
    border: 1px solid rgba(0,0,0,0.20);
    font-weight: 400;
}
/* Override the general :checked dimming for dashBtn — keep it opaque when active */
QPushButton#dashBtn:checked { background: #1a1a1a; color: #ffffff; }
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
QLabel#profileName { color: #1a1a1a; font-size: 15px; font-weight: 600; background: transparent; }
QLabel#helpLabel   { color: #555555; font-size: 13px; font-weight: 600; background: transparent; }
QLabel#editIcon    { color: #888888; font-size: 13px; background: transparent; }
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
    """Scale image to fill a logical square of `size` px, HiDPI-aware.
    SVG files are rendered via svg_pixmap_raw for crisp vector output."""
    if path.lower().endswith(".svg"):
        from gui.icon_utils import svg_pixmap_raw
        return svg_pixmap_raw(path, size)
    raw = QPixmap(path)
    if raw.isNull():
        return None
    # Render at physical resolution so Retina screens stay sharp
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        dpr = app.primaryScreen().devicePixelRatio() if app and app.primaryScreen() else 1.0
    except Exception:
        dpr = 1.0
    phys = int(size * dpr)
    px = raw.scaled(phys, phys,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation)
    px.setDevicePixelRatio(dpr)
    return px


# ══════════════════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):

    # ── Signals ────────────────────────────────────────────────────────────────
    read_requested        = pyqtSignal(str)
    pause_requested       = pyqtSignal()
    resume_requested      = pyqtSignal()
    stop_requested        = pyqtSignal()
    quit_requested        = pyqtSignal()
    theme_changed         = pyqtSignal(bool)   # True = dark
    terms_requested       = pyqtSignal()
    profile_requested     = pyqtSignal()
    profile_save_requested = pyqtSignal(dict)  # emitted when user saves profile page
    mode_changed          = pyqtSignal(bool)   # True = online
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
        self._content_stack.addWidget(self._build_profile_page())    # 6
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
            "Select text in any window and press  Ctrl+R  to read aloud, or press  Ctrl+C  and the overlay pill will appear automatically. The floating pill tracks each word in real-time so you can follow along without switching windows — no need to swap between apps or lose your place.\n\n"
            "Veaja is a real text-to-speech tool built for everyday use. It works across PDFs, emails, web pages, documents, and apps that have no built-in read-aloud feature — just select text and it reads, no copy-paste required. You get a choice of natural-sounding voices across multiple accents and languages, with speed control so you can slow down to absorb detail or speed up to skim. Every session is saved to your history so you can replay anything you've heard — useful for studying, reviewing notes, or catching up on long content hands-free. Veaja runs quietly in your system tray, ready the moment you need it, without cluttering your screen or interrupting your workflow.\n\n"
            "How Veaja works under the hood: when you select text and trigger a read, Veaja captures the selected content through your system clipboard or accessibility layer and passes it directly to a TTS engine. The engine processes the raw text, applies language detection to pick the right voice model, and streams synthesized audio to your output device in real-time. Word-level timestamps returned by the engine drive the highlight on the floating pill — each word lights up in sync with what is being spoken. The overlay itself is a transparent, always-on-top window that stays anchored to your screen corner and never interferes with clicks or focus in the window beneath it.\n\n"
            "The history system records every reading session — the original text, the voice used, the speed setting, and a timestamp — so you can revisit any session from the history page and replay it exactly as it was. Language detection runs automatically before synthesis so Veaja picks the correct pronunciation rules without you having to change settings manually. Speed adjustment is applied at the synthesis stage, not by resampling audio after the fact, which means faster or slower playback keeps the voice sounding natural rather than robotic or distorted."
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

        # ── Layer 1 — floating draggable pill (SVG icon, absolute position) ──
        _PILL_W, _PILL_H = 300, 98          # display size (SVG native: 219×72)

        pill_float = QWidget()
        pill_float.setObjectName("pillFloat")
        pill_float.setStyleSheet("background: transparent;")

        pill = QLabel(pill_float)
        pill.setObjectName("dashboardPill")
        pill.setFixedSize(_PILL_W, _PILL_H)
        pill.setCursor(Qt.CursorShape.OpenHandCursor)
        pill.setStyleSheet("background: transparent;")

        self._dashboard_pill_lbl  = pill
        self._pill_float          = pill_float
        self._pill_drag_start:  QPoint | None = None
        self._pill_drag_origin: QPoint | None = None

        def _pill_press(ev):
            if ev.button() == Qt.MouseButton.LeftButton:
                pill.setCursor(Qt.CursorShape.ClosedHandCursor)
                self._pill_drag_start  = ev.globalPosition().toPoint()
                self._pill_drag_origin = pill.pos()
            ev.accept()

        def _pill_move(ev):
            if self._pill_drag_start is None:
                return
            delta   = ev.globalPosition().toPoint() - self._pill_drag_start
            new_pos = self._pill_drag_origin + delta
            max_x   = pill_float.width()  - pill.width()
            max_y   = pill_float.height() - pill.height()
            pill.move(max(0, min(new_pos.x(), max_x)),
                      max(0, min(new_pos.y(), max_y)))
            ev.accept()

        def _pill_release(ev):
            pill.setCursor(Qt.CursorShape.OpenHandCursor)
            self._pill_drag_start  = None
            self._pill_drag_origin = None
            ev.accept()

        pill.mousePressEvent   = _pill_press
        pill.mouseMoveEvent    = _pill_move
        pill.mouseReleaseEvent = _pill_release

        # Render initial SVG (shape not known yet — default circle)
        QTimer.singleShot(0, self._update_dashboard_pill_icon)

        # Initial position: bottom-left of pill_float
        def _init_pill_pos():
            y = max(0, pill_float.height() - _PILL_H - 18)
            pill.move(18, y)
        QTimer.singleShot(0, _init_pill_pos)

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
        clear_btn.setFixedSize(80, 30)
        clear_btn.setToolTip("Clear text")
        clear_btn.clicked.connect(self._text_edit.clear)
        ft_lay.addWidget(clear_btn)

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

    # ── Profile page (replaces popup dialog) ───────────────────────────────────

    def _build_profile_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("contentPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Top bar: Save button
        top = QWidget()
        top.setObjectName("pageTopAction")
        t_lay = QHBoxLayout(top)
        t_lay.setContentsMargins(32, 20, 32, 16)
        t_lay.addStretch()
        self._profile_save_btn = QPushButton("Save")
        self._profile_save_btn.setObjectName("btnOutline")
        self._profile_save_btn.setFixedSize(90, 32)
        self._profile_save_btn.clicked.connect(self._on_profile_page_save)
        t_lay.addWidget(self._profile_save_btn)
        lay.addWidget(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        body = QWidget()
        body.setObjectName("contentPage")
        b_lay = QVBoxLayout(body)
        b_lay.setContentsMargins(40, 10, 40, 40)
        b_lay.setSpacing(0)
        b_lay.addStretch()

        # Large profile photo with glow border
        photo_row = QHBoxLayout()
        photo_row.addStretch()
        self._profile_photo_frame = QWidget()
        self._profile_photo_frame.setObjectName("profilePhotoFrame")
        self._profile_photo_frame.setFixedSize(220, 220)
        self._profile_photo_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        self._profile_photo_frame.mousePressEvent = lambda _: self._on_profile_choose_photo()
        ppf_lay = QVBoxLayout(self._profile_photo_frame)
        ppf_lay.setContentsMargins(4, 4, 4, 4)
        self._profile_photo_lbl = QLabel()
        self._profile_photo_lbl.setFixedSize(212, 212)
        self._profile_photo_lbl.setScaledContents(True)
        self._profile_photo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ppf_lay.addWidget(self._profile_photo_lbl, 0, Qt.AlignmentFlag.AlignCenter)
        photo_row.addWidget(self._profile_photo_frame)
        photo_row.addStretch()
        b_lay.addLayout(photo_row)
        b_lay.addSpacing(18)

        # Name row: pencil icon (left) + name input — matching role model layout
        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        name_row.addStretch()
        pencil_lbl = QLabel("✎")
        pencil_lbl.setObjectName("profilePageEdit")
        pencil_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        pencil_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        pencil_lbl.mousePressEvent = lambda _: self._on_profile_choose_photo()
        name_row.addWidget(pencil_lbl)
        self._profile_name_edit = QLineEdit()
        self._profile_name_edit.setObjectName("profileNameEdit")
        self._profile_name_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._profile_name_edit.setFixedWidth(240)
        self._profile_name_edit.setFont(QFont("-apple-system", 20, QFont.Weight.Bold))
        self._profile_name_edit.setFrame(False)
        self._profile_name_edit.textChanged.connect(self._on_profile_name_preview)
        name_row.addWidget(self._profile_name_edit)
        name_row.addStretch()
        b_lay.addLayout(name_row)
        b_lay.addSpacing(20)

        # "Change profile" label
        chg_row = QHBoxLayout()
        chg_row.addStretch()
        chg_lbl = QLabel("Change profile")
        chg_lbl.setObjectName("settingsLabel")
        chg_row.addWidget(chg_lbl)
        chg_row.addStretch()
        b_lay.addLayout(chg_row)
        b_lay.addSpacing(14)

        # Buttons: upload photo | set default
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()
        upload_btn = QPushButton("upload photo")
        upload_btn.setObjectName("btnOutline")
        upload_btn.setFixedHeight(32)
        upload_btn.clicked.connect(self._on_profile_choose_photo)
        btn_row.addWidget(upload_btn)
        default_btn = QPushButton("set default")
        default_btn.setObjectName("btnOutline")
        default_btn.setFixedHeight(32)
        default_btn.clicked.connect(self._on_profile_reset_photo)
        btn_row.addWidget(default_btn)
        btn_row.addStretch()
        b_lay.addLayout(btn_row)

        b_lay.addStretch()
        scroll.setWidget(body)
        lay.addWidget(scroll, 1)
        return page

    def _open_profile_page(self):
        """Navigate to the inline profile page, seeding it with current profile."""
        from PyQt6.QtWidgets import QFileDialog  # noqa: F401 (kept for pick)
        self._pending_profile = dict(self._pending_profile) if self._pending_profile else {}
        # Snapshot current saved state so "set default" can revert to it
        self._saved_name = self._title_label.text()
        self._saved_logo = self._logo_path
        # Populate fields from live state
        current_name = self._title_label.text()
        self._profile_name_edit.setText(current_name)
        self._reload_profile_page_photo()
        self._apply_profile_page_glow()
        for btn, _ in self._nav_btns:
            btn.setChecked(False)
        # Hide the sidebar edit icon while on profile page
        if self._edit_icon_lbl is not None:
            self._edit_icon_lbl.setVisible(False)
        self._content_stack.setCurrentIndex(6)

    def _apply_profile_page_glow(self):
        """Apply theme-aware blur glow to the large profile photo frame and name input."""
        if not self._profile_photo_frame:
            return
        # Dark mode → warm golden glow + border  |  Light mode → soft purple glow only
        if self._dark:
            glow_color = QColor("#f5a623")
            glow_hex   = "#f5a623"
            bg         = "#111111"
            border     = f"border: 2px solid {glow_hex};"
        else:
            glow_color = QColor("#7c6fff")
            glow_hex   = "#7c6fff"
            bg         = "#ffffff"
            border     = "border: none;"
        self._profile_photo_frame.setStyleSheet(
            f"#profilePhotoFrame {{ background: {bg}; border-radius: 12px; {border} }}"
        )
        shadow = QGraphicsDropShadowEffect(self._profile_photo_frame)
        shadow.setBlurRadius(65)
        shadow.setOffset(0, 0)
        shadow.setColor(glow_color)
        self._profile_photo_frame.setGraphicsEffect(shadow)
        # Name input: transparent background matching content page, underline only
        if hasattr(self, "_profile_name_edit"):
            txt   = "#ffffff" if self._dark else "#1a1a1a"
            bg_in = "transparent"
            uline = "#555555" if self._dark else "#aaaaaa"
            self._profile_name_edit.setStyleSheet(
                f"QLineEdit#profileNameEdit {{"
                f" background: {bg_in}; color: {txt};"
                f" border: none; border-bottom: 2px solid {uline};"
                f" font-size: 20px; font-weight: 700; padding-bottom: 2px; }}"
            )

    def _reload_profile_page_photo(self):
        if not hasattr(self, "_profile_photo_lbl"):
            return
        logo_path = self._pending_profile.get("logo_path") or self._logo_path
        if logo_path and os.path.exists(logo_path):
            px = _make_square_pixmap(logo_path, 212)
        else:
            src = self._default_logo_path()
            px = _make_square_pixmap(src, 212) if src else None
        if px:
            self._profile_photo_lbl.setPixmap(px)

    def _on_profile_choose_photo(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Avatar Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if path:
            self._pending_profile["logo_path"] = path
            self._reload_profile_page_photo()
            self._reload_header_logo(path)   # live preview in sidebar

    def _on_profile_reset_photo(self):
        """Reset to factory defaults: name 'Veaja', built-in logo, no custom photo."""
        default_name = "Veaja"
        self._pending_profile["logo_path"] = None
        self._pending_profile["app_name"]  = default_name
        # Must explicitly clear stored path — _reload_header_logo(None) skips updating it
        self._logo_path = None
        # Restore profile page fields
        self._profile_name_edit.setText(default_name)
        self._reload_profile_page_photo()
        # Restore sidebar live preview to factory default
        self._title_label.setText(default_name)
        self._reload_header_logo()   # no arg → picks up self._logo_path = None → default img

    def _on_profile_name_preview(self, text: str):
        """Live preview: update sidebar name label as user types."""
        name = text.strip()
        if any(c.isalnum() for c in name):
            self._title_label.setText(name)

    def _on_profile_page_save(self):
        name = self._profile_name_edit.text().strip()
        if not any(c.isalnum() for c in name):
            name = "Veaja"
        self._pending_profile["app_name"] = name
        # Commit sidebar immediately so it persists after navigating away
        self._title_label.setText(name)
        self.setWindowTitle(name)
        self._reload_header_logo(self._pending_profile.get("logo_path"))
        self.profile_save_requested.emit(dict(self._pending_profile))
        self._navigate(0)   # back to dashboard

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
        t_lay.setContentsMargins(32, 14, 32, 10)
        t_lay.addStretch()
        save_btn = QPushButton("Save")
        save_btn.setObjectName("btnOutline")
        save_btn.setFixedSize(90, 32)
        save_btn.clicked.connect(lambda: None)
        t_lay.addWidget(save_btn)
        lay.addWidget(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("settingsScroll")

        sc = QWidget()
        sc_lay = QVBoxLayout(sc)
        sc_lay.setContentsMargins(32, 0, 32, 24)
        sc_lay.setSpacing(14)

        # ── Shape ─────────────────────────────────────────────────────────
        shape_lbl = QLabel("Set overlay shape")
        shape_lbl.setObjectName("shapeSectionLabel")
        sc_lay.addWidget(shape_lbl)

        shape_box = QWidget()
        shape_box.setObjectName("shapeBox")
        sb_lay = QVBoxLayout(shape_box)
        sb_lay.setContentsMargins(16, 8, 16, 40)
        sb_lay.setSpacing(0)

        # Edit icon top-right — floated, doesn't affect vertical rhythm
        edit_row = QHBoxLayout()
        edit_row.setContentsMargins(0, 0, 0, 0)
        edit_row.addStretch()
        shape_edit_ic = self._inline_edit_icon()
        shape_edit_ic.setObjectName("shapeEditIcon")
        shape_edit_ic.setFixedSize(16, 16)
        edit_row.addWidget(shape_edit_ic)
        sb_lay.addLayout(edit_row)

        # Circle row — negative spacing pulls it up tight under edit icon
        circle_row = self._shape_row("Circle", is_circle=True, checked=True)
        self._shape_circle = circle_row[0]
        sb_lay.addWidget(circle_row[1])

        sb_lay.addSpacing(20)   # gap between Circle and Rectangle rows

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

        # Keep dashboard pill SVG in sync with shape setting
        self._shape_circle.toggled.connect(lambda _: self._update_dashboard_pill_icon())
        QTimer.singleShot(0, self._update_dashboard_pill_icon)   # apply on first load

        sc_lay.addWidget(shape_box)

        # ── Mode + Language ───────────────────────────────────────────────
        ml_row = QHBoxLayout()
        ml_row.setSpacing(0)

        # Mode label + checkboxes (stacked label, then horizontal checkboxes)
        mode_block = QVBoxLayout()
        mode_block.setSpacing(10)
        mode_lbl = QLabel("Mode")
        mode_lbl.setObjectName("settingsLabel")
        mode_block.addWidget(mode_lbl)
        chk_row = QHBoxLayout()
        chk_row.setSpacing(40)
        self._online_btn = QCheckBox("Online Mode")
        self._online_btn.setObjectName("settingsCheck")
        self._online_btn.setChecked(True)
        self._online_btn.toggled.connect(self._on_mode_checkbox)
        chk_row.addWidget(self._online_btn)
        self._offline_btn = QCheckBox("Offline Mode")
        self._offline_btn.setObjectName("settingsCheck")
        self._offline_btn.toggled.connect(
            lambda c: (self._online_btn.blockSignals(True),
                       self._online_btn.setChecked(not c),
                       self._online_btn.blockSignals(False)) if c else None
        )
        chk_row.addWidget(self._offline_btn)
        chk_row.addStretch()
        mode_block.addLayout(chk_row)
        ml_row.addLayout(mode_block, 1)

        # Language — right-aligned, same row
        lang_block = QVBoxLayout()
        lang_block.setSpacing(10)
        lang_lbl = QLabel("Language")
        lang_lbl.setObjectName("settingsLabel")
        lang_block.addWidget(lang_lbl)
        lang_inline = QHBoxLayout()
        lang_inline.setSpacing(10)
        self._lang_combo = QComboBox()
        self._lang_combo.setObjectName("settingsCombo")
        self._lang_combo.setFixedWidth(160)
        self._lang_combo.addItem("English")
        lang_inline.addWidget(self._lang_combo)
        lang_inline.addWidget(self._inline_edit_icon())
        lang_block.addLayout(lang_inline)
        ml_row.addLayout(lang_block, 1)
        sc_lay.addLayout(ml_row)

        # ── Sound + Speed ─────────────────────────────────────────────────
        ss_row = QHBoxLayout()
        ss_row.setSpacing(0)

        sound_block = QVBoxLayout()
        sound_block.setSpacing(10)
        sound_lbl = QLabel("Sound")
        sound_lbl.setObjectName("settingsLabel")
        sound_block.addWidget(sound_lbl)
        sound_inline = QHBoxLayout()
        sound_inline.setSpacing(10)
        self._sound_input = QComboBox()
        self._sound_input.setObjectName("settingsCombo")
        self._sound_input.setFixedWidth(200)
        self._sound_input.currentIndexChanged.connect(self._on_sound_combo_changed)
        sound_inline.addWidget(self._sound_input)
        sound_inline.addWidget(self._inline_edit_icon())
        sound_inline.addStretch()
        sound_block.addLayout(sound_inline)
        ss_row.addLayout(sound_block, 1)

        speed_block = QVBoxLayout()
        speed_block.setSpacing(10)
        speed_lbl = QLabel("Speed")
        speed_lbl.setObjectName("settingsLabel")
        speed_block.addWidget(speed_lbl)
        spd_inline = QHBoxLayout()
        spd_inline.setSpacing(10)
        spd_inline.addWidget(QLabel("🐢"))
        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(50, 400)
        self._speed_slider.setValue(175)
        self._speed_slider.setObjectName("speedSlider")
        self._speed_slider.valueChanged.connect(self._on_speed_changed)
        spd_inline.addWidget(self._speed_slider, 1)
        spd_inline.addWidget(QLabel("🐇"))
        speed_block.addLayout(spd_inline)
        ss_row.addLayout(speed_block, 1)
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
        row_lay.setSpacing(14)

        chk = QCheckBox(label)
        chk.setObjectName("settingsCheck")
        chk.setChecked(checked)
        row_lay.addWidget(chk)

        previews_row = QHBoxLayout()
        previews_row.setSpacing(14)
        previews_row.addWidget(self._mini_preview(is_circle, dark=True))
        previews_row.addWidget(self._mini_preview(is_circle, dark=False))
        previews_row.addStretch()
        row_lay.addLayout(previews_row)
        return chk, row

    def _mini_preview(self, is_circle: bool, dark: bool) -> QWidget:
        """Shape preview card using SVG pill icon + description text."""
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtGui import QPainter

        # SVG native: 219×72 — display at inner width preserving aspect ratio
        _inner_w = 236
        _pill_h  = int(_inner_w * 72 / 219)   # ≈ 78px

        card = QWidget()
        card.setFixedSize(260, _pill_h + 80)
        card.setObjectName("miniPreviewDark" if dark else "miniPreviewLight")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(12, 10, 12, 10)
        card_lay.setSpacing(8)

        if is_circle:
            svg_name = "overlay_circle_dark_icon.svg" if dark else "overlay_circle_light_icon.svg"
        else:
            svg_name = "overlay_retangle_dark_icon.svg" if dark else "overlay_retangle_light_icon.svg"

        svg_path = os.path.join(ASSETS, svg_name)
        pill_lbl = QLabel()
        pill_lbl.setFixedSize(_inner_w, _pill_h)
        pill_lbl.setObjectName("miniPillSvg")
        if os.path.exists(svg_path):
            # Render SVG → QPixmap so embedded base64 images are resolved
            app_inst = QApplication.instance()
            dpr = app_inst.primaryScreen().devicePixelRatio() if app_inst else 1.0
            phys_w = int(_inner_w * dpr)
            phys_h = int(_pill_h  * dpr)
            px = QPixmap(phys_w, phys_h)
            px.fill(Qt.GlobalColor.transparent)
            renderer = QSvgRenderer(svg_path)
            painter  = QPainter(px)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            renderer.render(painter)
            painter.end()
            px.setDevicePixelRatio(dpr)
            pill_lbl.setPixmap(px)
        card_lay.addWidget(pill_lbl)

        speech = QLabel(
            "Hi, my name is Veaja. what do you want me to read for you. I'm here to "
            "assist you brother. And don't mind me if my voice isn't sweat enough. "
            "Haa just kidding, cuz I'm a friendly ai assistance. No matter"
        )
        speech.setObjectName("miniSpeechLight" if dark else "miniSpeechDark")
        speech.setWordWrap(True)
        speech.setFont(QFont("-apple-system", 8))
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
        clear_btn.setFixedSize(72, 28)
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

        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 14, 14, 16)
        lay.setSpacing(8)

        # Header row: [label] [stretch] [delete icon button]
        hdr = QHBoxLayout()
        hdr.setSpacing(0)

        lbl = QLabel(section_label)
        lbl.setObjectName("historyCardLabel")
        hdr.addWidget(lbl)
        hdr.addStretch()

        del_btn = QPushButton()
        del_btn.setObjectName("historyDel")
        del_btn.setFixedSize(26, 26)
        del_btn.setFlat(True)
        del_btn.setToolTip("Delete")
        icon_color = "#888888"
        del_icon = svg_icon(os.path.join(ASSETS, "delete_icon.svg"), icon_color, 18)
        if not del_icon.isNull():
            del_btn.setIcon(del_icon)
            del_btn.setIconSize(QSize(18, 18))
        else:
            del_btn.setText("✕")
        del_btn.clicked.connect(lambda: self._delete_history_entry(full_text, card))
        hdr.addWidget(del_btn)

        lay.addLayout(hdr)

        # Body text
        body = QLabel(short)
        body.setObjectName("historyText")
        body.setWordWrap(True)
        lay.addWidget(body)
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
        email_btn.setFixedSize(90, 32)
        email_btn.clicked.connect(self._open_contact_email)
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
            ("Q1. How do I start using Veaja?",
             "Install and launch Veaja — it will sit quietly in your system tray.\n"
             "Select any text in any window, then press Ctrl+R to read it aloud immediately.\n"
             "Alternatively, press Ctrl+C and the overlay pill will appear on your screen so you can follow along word by word.\n"
             "No setup, no account, and no copy-paste is needed. Just select and go."),
            ("Q2. What is the overlay pill and how does it work?",
             "The overlay pill is a small floating widget that appears on top of your screen when Veaja is reading.\n"
             "It shows the Veaja logo, a 'Tap to read' label, and a restart button.\n"
             "As Veaja speaks, it highlights each word in real-time so you can follow along without switching windows.\n"
             "The pill stays on top of all other apps and never blocks your clicks or keyboard input underneath it.\n"
             "You can drag it anywhere on your screen to keep it out of the way."),
            ("Q3. What is the difference between Online and Offline mode?",
             "Offline mode: all processing is done locally on your device using a built-in TTS engine. No internet needed. Completely private.\n"
             "Online mode: your text is sent to Microsoft Azure Cognitive Services, which returns higher-quality, more natural-sounding speech.\n"
             "In Online mode, no account or API key is required — Veaja uses the Edge browser's built-in neural TTS service.\n"
             "Choose Offline if privacy is your priority. Choose Online for the best voice quality."),
            ("Q4. Does Veaja store or record what I read?",
             "Veaja saves a session history so you can replay past readings from the View History page.\n"
             "This history is stored only on your local device — it is never uploaded to any server.\n"
             "In Offline mode, no data ever leaves your machine.\n"
             "In Online mode, the text is sent to Microsoft's TTS service but Veaja itself does not log, store, or share it.\n"
             "You can clear your history at any time from the history page."),
            ("Q5. Which languages and voices are supported?",
             "Currently Veaja supports English only.\n"
             "Multiple voices and accents are available in English — you can choose your preferred voice from Voice Settings.\n"
             "Support for additional languages such as Arabic, French, Spanish, German, and Japanese is planned for a future release.\n"
             "Stay tuned for updates."),
            ("Q6. Can I adjust reading speed?",
             "Yes. Go to Voice Settings and use the speed control to slow down or speed up playback.\n"
             "Speed adjustment is applied at the synthesis stage — not by resampling audio after the fact.\n"
             "This means slow or fast speeds still sound natural, not robotic or distorted.\n"
             "Slower speeds are great for absorbing detail. Faster speeds are useful for skimming long documents."),
            ("Q7. Why is Veaja not reading my selected text?",
             "Make sure the text is actually selectable — some protected PDFs or images do not expose their text.\n"
             "If Ctrl+R does not work, check that Veaja is running in the system tray (look for the tray icon).\n"
             "On macOS, Veaja may need Accessibility permission — go to System Settings → Privacy & Security → Accessibility and enable Veaja.\n"
             "On Windows, some admin-protected applications may block text capture. Try copying the text manually and using the Text Label tab instead."),
            ("Q8. Can I use this app on a mobile phone or tablet?",
             "Currently Veaja is a desktop application available for Windows, macOS, and Linux.\n"
             "Mobile support for Android and iOS is planned for a future release.\n"
             "For now, you can use Veaja on any laptop or desktop computer."),
        ]:
            sc_lay.addWidget(self._info_card(q, a))
        sc_lay.addStretch()
        scroll.setWidget(sc)
        lay.addWidget(scroll, 1)
        return page

    def _open_contact_email(self):
        """Open the user's default mail client addressed to Veaja support."""
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        subject = "Veaja – Question / Feedback"
        body    = "Hi Veaja team,\n\n"
        mailto  = (
            f"mailto:veaja.app.official@gmail.com"
            f"?subject={subject.replace(' ', '%20').replace('/', '%2F').replace('–', '%E2%80%93')}"
            f"&body={body.replace(' ', '%20').replace('\n', '%0A')}"
        )
        QDesktopServices.openUrl(QUrl(mailto))

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
            ("T1. Acceptance of terms",
             "By installing or using Veaja, you agree to these terms of use.\n"
             "If you do not agree, please uninstall the application and discontinue use.\n"
             "These terms may be updated over time. Continued use after an update means you accept the revised terms."),
            ("T2. Offline usage",
             "In Offline mode, all text-to-speech processing is performed entirely on your device.\n"
             "No data is transmitted to any external server.\n"
             "Audio files generated during a session are stored temporarily at ~/.veaja/audio/ and cleared when the session ends.\n"
             "You are solely responsible for the content you choose to read aloud using Veaja."),
            ("T3. Online usage",
             "In Online mode, the text you select is sent to Microsoft Azure Cognitive Services for neural TTS synthesis.\n"
             "Veaja does not store, log, retain, or share this text in any form.\n"
             "Microsoft's own privacy policy governs how they handle data sent through their API.\n"
             "No account, subscription, or API key is required — Veaja relies on the Edge browser's built-in TTS service."),
            ("T4. Acceptable use",
             "You may use Veaja for personal, educational, or professional reading of text you have the right to access.\n"
             "You must not use Veaja to read, reproduce, or distribute copyrighted content without authorisation.\n"
             "You must not use Veaja to process content that is illegal, harmful, abusive, or violates the rights of others.\n"
             "Veaja is a reading aid — it is your responsibility to ensure the content you read complies with applicable laws."),
            ("T5. Data and privacy",
             "Veaja does not create user accounts and does not collect personal information.\n"
             "Session history is stored locally on your device only and is never uploaded.\n"
             "Your voice settings, language preferences, and profile name are saved locally in a configuration file on your machine.\n"
             "You can delete this data at any time by clearing the app's configuration folder."),
            ("T6. Third-party services",
             "Online mode uses Microsoft Azure Cognitive Services (TTS). Use of this service is subject to Microsoft's terms and privacy policy.\n"
             "Veaja does not endorse or take responsibility for the accuracy, availability, or practices of any third-party service.\n"
             "If Microsoft's TTS service is unavailable, Veaja will fall back to Offline mode automatically when possible."),
            ("T7. Limitation of liability",
             "Veaja is provided 'as is' without warranty of any kind, express or implied.\n"
             "The developers are not liable for any loss of data, interruption of service, or damages arising from use of this application.\n"
             "Veaja is a tool — you are responsible for how you use the output it produces."),
            ("T8. Changes and termination",
             "The developers reserve the right to update, modify, or discontinue Veaja at any time without notice.\n"
             "Features available in the current version may change in future releases.\n"
             "You may stop using Veaja at any time by uninstalling it. Local data can be removed manually from your device."),
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
        self._reload_header_logo(profile.get("logo_path"))
        color = profile.get("highlight_color", "#FFD60A")
        if color:
            self._highlight_color = color
        # Restore saved dark/light preference (None = already at system default)
        saved_dark = profile.get("dark_mode")
        if saved_dark is not None and isinstance(saved_dark, bool):
            if saved_dark != self._dark:
                self._toggle_theme()

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
        self._update_dashboard_pill_icon()
        self._apply_theme()
        self.theme_changed.emit(self._dark)
        # If edit profile page is open, refresh its glow colour and photo
        if self._content_stack.currentIndex() == 6:
            self._apply_profile_page_glow()
            # Only swap to default logo if no custom photo is set
            if not self._pending_profile.get("logo_path") and not self._logo_path:
                self._reload_profile_page_photo()

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
            # Use logical size (18×18), not physical pixel size, to stay inside the button
            self._theme_btn.setIconSize(QSize(18, 18))
        else:
            self._theme_btn.setText("☀" if self._dark else "☾")

        # Edit icon next to profile name
        if self._edit_icon_lbl is not None:
            edit_px = svg_pixmap(os.path.join(ASSETS, "edit_icon.svg"), icon_color, 16)
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

        # Profile frame — no glow border, just match sidebar background
        bg = "#f0f0f0" if self._dark else "#1a1a1a"
        if self._profile_frame:
            self._profile_frame.setStyleSheet(
                f"#profileFrame {{ background: {bg}; border-radius: 10px; border: none; }}"
            )
        # Profile name colour is handled by QLabel#profileName rule in sidebar QSS

    def _default_logo_path(self) -> str | None:
        """Return the best available default logo path — PNG preferred over SVG."""
        stem = "logo_light" if self._dark else "logo_dark"
        for ext in (".png", ".svg"):
            p = os.path.join(ASSETS, stem + ext)
            if os.path.exists(p):
                return p
        return None

    def _reload_header_logo(self, logo_path: str | None = None):
        if logo_path is not None:
            self._logo_path = logo_path if (logo_path and os.path.exists(logo_path)) else None
        src = self._logo_path if (self._logo_path and os.path.exists(self._logo_path)) \
              else self._default_logo_path()
        px = _make_square_pixmap(src, 76) if src else None
        if px and hasattr(self, "_header_logo"):
            self._header_logo.setPixmap(px)

    def _update_dashboard_pill_icon(self):
        """Re-render the dashboard pill using the correct overlay SVG (shape + theme)."""
        if not hasattr(self, "_dashboard_pill_lbl"):
            return
        from PyQt6.QtSvg import QSvgRenderer

        is_circle = (not hasattr(self, "_shape_circle")) or self._shape_circle.isChecked()
        if is_circle:
            svg_name = "overlay_circle_dark_icon.svg" if self._dark else "overlay_circle_light_icon.svg"
        else:
            svg_name = "overlay_retangle_dark_icon.svg" if self._dark else "overlay_retangle_light_icon.svg"

        svg_path = os.path.join(ASSETS, svg_name)
        if not os.path.exists(svg_path):
            return

        pill = self._dashboard_pill_lbl
        w, h = pill.width(), pill.height()
        app  = QApplication.instance()
        dpr  = app.primaryScreen().devicePixelRatio() if app else 1.0
        px   = QPixmap(int(w * dpr), int(h * dpr))
        px.fill(Qt.GlobalColor.transparent)
        renderer = QSvgRenderer(svg_path)
        painter  = QPainter(px)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter)
        painter.end()
        px.setDevicePixelRatio(dpr)
        pill.setPixmap(px)

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

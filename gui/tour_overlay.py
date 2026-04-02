"""
Veaja interactive live-teach tutorial.

Spawned by AppController when the user clicks Tutorial in the sidebar.
Covers the MainWindow with a semi-transparent spotlight overlay and
navigates to the relevant page before spotlighting each widget.

Steps that have navigate_to/tab will call main_window.navigate_if_needed()
so the user sees the feature being demonstrated in context (live-teach).
"""

from PyQt6.QtWidgets import QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, QRect, QRectF, QPoint, QEvent
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QFont


# ── Tour step definitions ──────────────────────────────────────────────────────
# navigate_to: content-stack page index to switch to before showing spotlight
#   0 = Dashboard, 1 = Setting, 2 = View History, 3 = Ask, 4 = Privacy
# tab: dashboard tab index (0 = Overlay, 1 = Text label) — used when navigate_to == 0

STEPS = [
    {
        "widget_attr": None,
        "title": "Welcome to Veaja!",
        "body": (
            "This live tutorial walks you through every feature.\n\n"
            "Use  Next  and  Back  to navigate, or  Skip  to close.\n\n"
            "Each step jumps to the relevant page so you can see\n"
            "the feature in context — live!"
        ),
        "navigate_to": None,
    },

    # ── Reading workflow ───────────────────────────────────────────────────────
    {
        "widget_attr": None,
        "title": "Reading in PDF / Word / Browser",
        "body": (
            "Veaja reads text from any application:\n\n"
            "1. Select text in your PDF / Word / browser\n"
            "2. Press  Ctrl+R  — Veaja reads it immediately\n"
            "   (or  Ctrl+C  — the overlay pill appears automatically)\n"
            "3. The floating pill tracks each word in yellow so you\n"
            "   can follow along without switching windows."
        ),
        "navigate_to": 0,
        "tab": 0,
    },

    # ── Overlay tab ────────────────────────────────────────────────────────────
    {
        "widget_attr": "_overlay_text_view",
        "title": "Overlay Tab — Live Preview",
        "body": (
            "The Overlay tab shows the text currently loaded\n"
            "from your clipboard or selection.\n\n"
            "When Veaja reads, words are highlighted in yellow\n"
            "in the floating pill overlay above all windows."
        ),
        "navigate_to": 0,
        "tab": 0,
    },

    # ── Text label tab ─────────────────────────────────────────────────────────
    {
        "widget_attr": "_text_edit",
        "title": "Text Label Tab — Type or Paste",
        "body": (
            "Type or paste text here, then click Read.\n\n"
            "While reading, each word is highlighted in yellow from\n"
            "left to right — a visual progress bar for your eyes.\n\n"
            "Tip: paste long articles here for the best experience."
        ),
        "navigate_to": 0,
        "tab": 1,
    },
    {
        "widget_attr": "_read_btn",
        "title": "Read Button",
        "body": (
            "Click Read to start speaking.\n\n"
            "• Click again while speaking → Pause\n"
            "• Click once more → Resume\n"
            "• Button turns red while speaking, orange while paused."
        ),
        "navigate_to": 0,
        "tab": 1,
    },

    # ── Settings page ──────────────────────────────────────────────────────────
    {
        "widget_attr": "_online_btn",
        "title": "Online / Offline Mode",
        "body": (
            "Online  — Microsoft neural voices.\n"
            "High-quality, human-like. Requires internet.\n\n"
            "Offline — Windows system voices.\n"
            "Works without internet. More robotic.\n\n"
            "Switch here in Settings."
        ),
        "navigate_to": 1,
    },
    {
        "widget_attr": "_voice_combo",
        "title": "Voice Selector",
        "body": (
            "Choose your preferred voice.\n\n"
            "Online voices include regional accents:\n"
            "US, UK, and Australian English."
        ),
        "navigate_to": 1,
    },
    {
        "widget_attr": "_speed_slider",
        "title": "Reading Speed",
        "body": (
            "Drag to speed up or slow down.\n\n"
            "Range: 50 (slow) → 400 (fast).\n"
            "Default 175 is a natural reading pace."
        ),
        "navigate_to": 1,
    },

    # ── History page ───────────────────────────────────────────────────────────
    {
        "widget_attr": "_history_list",
        "title": "Reading History",
        "body": (
            "Your last 20 texts are saved here.\n\n"
            "History is split into Recent, Previous, and Old sections.\n\n"
            "Double-click any item to load it back into the text box."
        ),
        "navigate_to": 2,
    },

    # ── Profile ────────────────────────────────────────────────────────────────
    {
        "widget_attr": "_header_logo",
        "title": "Your Profile",
        "body": (
            "Click the avatar or app name in the sidebar to open profile.\n\n"
            "• Set a custom display name\n"
            "• Set a profile picture (shown in the overlay pill)\n"
            "• Choose your word-highlight colour"
        ),
        "navigate_to": None,
    },

    # ── Ask a Question ─────────────────────────────────────────────────────────
    {
        "widget_attr": None,
        "title": "Ask a Question",
        "body": (
            "Find answers to common questions in the\n"
            "Ask a Question section.\n\n"
            "Topics include: overlay usage, data privacy,\n"
            "and platform availability.\n\n"
            "Use the Email button to contact support."
        ),
        "navigate_to": 3,
    },

    # ── Dark / light mode ──────────────────────────────────────────────────────
    {
        "widget_attr": "_theme_btn",
        "title": "Dark / Light Mode",
        "body": (
            "Toggle between dark and light themes using the\n"
            "☀ / ☾ button at the top of the sidebar.\n\n"
            "The floating overlay and tray icon both\n"
            "follow this setting automatically."
        ),
        "navigate_to": None,
    },

    # ── Word highlighting ──────────────────────────────────────────────────────
    {
        "widget_attr": None,
        "title": "Word Highlighting — Two Modes",
        "body": (
            "Veaja highlights words in two places simultaneously:\n\n"
            "1.  Dashboard Text tab  — yellow progress bar left-to-right.\n"
            "    Best when you paste text directly into Veaja.\n\n"
            "2.  Overlay pill  — karaoke display shows the current word\n"
            "    in yellow. Use this when reading PDFs or browser pages\n"
            "    so you never need to switch windows.\n\n"
            "Customise the highlight colour in your Profile."
        ),
        "navigate_to": None,
    },

    # ── Wrap-up ────────────────────────────────────────────────────────────────
    {
        "widget_attr": None,
        "title": "You're all set!",
        "body": (
            "Quick recap for reading third-party documents:\n\n"
            "1. Open your PDF / Word / browser\n"
            "2. Select the text you want\n"
            "3. Press  Ctrl+R  (no switching, no copy-paste)\n"
            "4. Watch the overlay pill — it tracks every word in yellow\n\n"
            "Enjoy Veaja!"
        ),
        "navigate_to": None,
    },
]


# ── Bubble widget ──────────────────────────────────────────────────────────────

class _Bubble(QWidget):
    """Floating rounded card with title, body, and Prev / Next / Skip."""

    def __init__(self, on_prev, on_next, on_skip, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setMinimumWidth(300)
        self.setMaximumWidth(340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        self._step_label = QLabel()
        self._step_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        f = QFont()
        f.setPointSize(9)
        self._step_label.setFont(f)
        layout.addWidget(self._step_label)

        self._title = QLabel()
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setWeight(QFont.Weight.Bold)
        self._title.setFont(title_font)
        self._title.setWordWrap(True)
        layout.addWidget(self._title)

        self._body = QLabel()
        body_font = QFont()
        body_font.setPointSize(10)
        self._body.setFont(body_font)
        self._body.setWordWrap(True)
        layout.addWidget(self._body)

        layout.addSpacing(8)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._prev_btn = QPushButton("← Back")
        self._prev_btn.setFixedHeight(32)
        self._prev_btn.clicked.connect(on_prev)

        self._next_btn = QPushButton("Next →")
        self._next_btn.setFixedHeight(32)
        self._next_btn.clicked.connect(on_next)

        self._skip_btn = QPushButton("Skip")
        self._skip_btn.setFixedHeight(32)
        self._skip_btn.clicked.connect(on_skip)

        btn_row.addWidget(self._prev_btn)
        btn_row.addWidget(self._next_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._skip_btn)
        layout.addLayout(btn_row)

    def update_content(self, step_idx: int, total: int, title: str, body: str):
        self._step_label.setText(f"{step_idx + 1} / {total}")
        self._title.setText(title)
        self._body.setText(body)
        self._prev_btn.setEnabled(step_idx > 0)
        self._next_btn.setText("Done" if step_idx == total - 1 else "Next →")
        self.adjustSize()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        is_dark = self.palette().color(self.backgroundRole()).lightness() < 128
        if is_dark:
            bg     = QColor(30, 30, 32, 250)
            text   = QColor(245, 245, 247)
            border = QColor(70, 70, 75, 200)
        else:
            bg     = QColor(255, 255, 255, 250)
            text   = QColor(28, 28, 30)
            border = QColor(210, 210, 215, 200)

        self._title.setStyleSheet(f"color: {text.name()};")
        self._body.setStyleSheet(f"color: {text.name()};")
        self._step_label.setStyleSheet(f"color: {text.name()};")

        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(border, 1.0))
        painter.drawRoundedRect(rect, 14, 14)
        painter.setPen(Qt.PenStyle.NoPen)


# ── Main overlay ───────────────────────────────────────────────────────────────

class TourOverlay(QWidget):
    """
    Full-window semi-transparent overlay with spotlight + bubble.
    Live-teaches by navigating to the relevant page before spotlighting.
    """

    def __init__(self, main_window: QWidget):
        super().__init__(main_window)
        self._main  = main_window
        self._step  = 0
        self._steps = STEPS

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.resize(main_window.size())

        self._bubble = _Bubble(
            on_prev=self._prev,
            on_next=self._next,
            on_skip=self.close,
            parent=self,
        )

        self._style_buttons()
        self._main.installEventFilter(self)
        self._go_to(0)

    # ── Navigation ─────────────────────────────────────────────────────────────

    def _prev(self):
        if self._step > 0:
            self._go_to(self._step - 1)

    def _next(self):
        if self._step < len(self._steps) - 1:
            self._go_to(self._step + 1)
        else:
            self.close()

    def _go_to(self, idx: int):
        self._step = idx
        step = self._steps[idx]

        # Live-teach: navigate to the relevant page first
        navigate_to = step.get("navigate_to")
        if navigate_to is not None and hasattr(self._main, "navigate_if_needed"):
            tab = step.get("tab")
            self._main.navigate_if_needed(navigate_to, tab=tab)

        self._bubble.update_content(idx, len(self._steps), step["title"], step["body"])
        self._position_bubble(step.get("widget_attr"))
        self.update()

    # ── Spotlight ──────────────────────────────────────────────────────────────

    def _target_rect(self, widget_attr: str | None) -> QRect | None:
        if not widget_attr:
            return None
        target: QWidget | None = getattr(self._main, widget_attr, None)
        if target is None or not target.isVisible():
            return None
        global_pos = target.mapToGlobal(QPoint(0, 0))
        local_pos  = self.mapFromGlobal(global_pos)
        return QRect(local_pos, target.size()).adjusted(-10, -8, 10, 8)

    # ── Bubble positioning ─────────────────────────────────────────────────────

    def _position_bubble(self, widget_attr: str | None):
        self._bubble.adjustSize()
        bw = self._bubble.width()
        bh = self._bubble.height()
        ow = self.width()
        oh = self.height()

        spot = self._target_rect(widget_attr)

        if spot is None:
            x = (ow - bw) // 2
            y = (oh - bh) // 2
        else:
            gap = 16
            x = spot.left()
            y = spot.bottom() + gap
            if y + bh > oh - 20:
                y = spot.top() - bh - gap
            if y < 20:
                y = spot.bottom() + gap
            x = max(12, min(x, ow - bw - 12))
            y = max(12, min(y, oh - bh - 12))

        self._bubble.move(x, y)

    # ── Painting ───────────────────────────────────────────────────────────────

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        step = self._steps[self._step]
        spot = self._target_rect(step.get("widget_attr"))
        dim  = QColor(0, 0, 0, 160)

        painter.fillRect(self.rect(), dim)

        if spot is not None:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            path = QPainterPath()
            path.addRoundedRect(QRectF(spot), 10, 10)
            painter.fillPath(path, QBrush(Qt.GlobalColor.transparent))

            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor(10, 132, 255, 200), 2.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(spot), 10, 10)

    # ── Event handling ─────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if not self._bubble.geometry().contains(event.position().toPoint()):
            event.accept()
        else:
            super().mousePressEvent(event)

    def eventFilter(self, obj, event):
        if obj is self._main and event.type() == QEvent.Type.Resize:
            self.resize(self._main.size())
            self._position_bubble(self._steps[self._step].get("widget_attr"))
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        self._main.removeEventFilter(self)
        super().closeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.resize(self._main.size())
        self.raise_()

    # ── Button styling ─────────────────────────────────────────────────────────

    def _style_buttons(self):
        base = "QPushButton { border-radius: 8px; font-size: 12px; padding: 0 12px; }"
        self._bubble._next_btn.setStyleSheet(
            f"{base}"
            "QPushButton { background: #0A84FF; color: #fff; border: none; }"
            "QPushButton:hover { background: #339AF0; }"
        )
        self._bubble._prev_btn.setStyleSheet(
            f"{base}"
            "QPushButton { background: transparent; color: #0A84FF;"
            " border: 1px solid #0A84FF; }"
            "QPushButton:hover { background: rgba(10,132,255,0.12); }"
            "QPushButton:disabled { color: #555; border-color: #555; }"
        )
        self._bubble._skip_btn.setStyleSheet(
            f"{base}"
            "QPushButton { background: transparent; color: #888; border: none; }"
            "QPushButton:hover { color: #ccc; }"
        )

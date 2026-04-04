"""
Veaja interactive live-teach tutorial.

Spawned by AppController when the user clicks Tutorial in the sidebar.
Covers the MainWindow with a semi-transparent spotlight overlay and
navigates to the relevant page before spotlighting each widget.

Steps that have navigate_to/tab will call main_window.navigate_if_needed()
so the user sees the feature being demonstrated in context (live-teach).
"""

import html as _html
import re   as _re

from PyQt6.QtWidgets import QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore    import Qt, QRect, QRectF, QPoint, QEvent
from PyQt6.QtGui     import QPainter, QColor, QPen, QBrush, QPainterPath, QFont


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
            "Use Next and Back to navigate, or Skip to close.\n\n"
            "Each step jumps to the relevant page so you can see "
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
            "1. Select text in your PDF, Word, or browser\n"
            "2. Press Ctrl+R — Veaja reads it immediately\n"
            "   (or Ctrl+C — the overlay pill appears automatically)\n"
            "3. The floating pill tracks each word in yellow so you "
            "can follow along without switching windows."
        ),
        "navigate_to": 0,
        "tab": 0,
    },

    # ── Overlay tab ────────────────────────────────────────────────────────────
    {
        "widget_attr": "_overlay_text_view",
        "title": "Overlay Tab — Live Preview",
        "body": (
            "The Overlay tab shows the text currently loaded "
            "from your clipboard or selection.\n\n"
            "When Veaja reads, words are highlighted in yellow "
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
            "While reading, each word is highlighted in yellow "
            "from left to right — a visual progress bar for your eyes.\n\n"
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
            "Online — Microsoft neural voices.\n"
            "High-quality, human-like. Requires internet.\n\n"
            "Offline — Windows system voices.\n"
            "Works without internet. More robotic.\n\n"
            "Switch here in Settings."
        ),
        "navigate_to": 1,
    },
    {
        "widget_attr": "_sound_input",
        "title": "Voice Selector",
        "body": (
            "Choose your preferred voice.\n\n"
            "Online voices include regional accents: "
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
            "Find answers to common questions in the Ask a Question section.\n\n"
            "Topics include: overlay usage, data privacy, "
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
            "Toggle between dark and light themes using the "
            "☀ / ☾ button at the top of the sidebar.\n\n"
            "The floating overlay and tray icon both "
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
            "1. Dashboard Text tab — yellow progress bar left-to-right. "
            "Best when you paste text directly into Veaja.\n\n"
            "2. Overlay pill — karaoke display shows the current word "
            "in yellow. Use this when reading PDFs or browser pages "
            "so you never need to switch windows.\n\n"
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
            "1. Open your PDF, Word, or browser\n"
            "2. Select the text you want\n"
            "3. Press Ctrl+R — no switching, no copy-paste\n"
            "4. Watch the overlay pill — it tracks every word in yellow\n\n"
            "Enjoy Veaja!"
        ),
        "navigate_to": None,
    },
]


# ── Bubble widget ──────────────────────────────────────────────────────────────

class _Bubble(QWidget):
    """Floating rounded card — polished design with progress bar."""

    _W = 400   # fixed card width

    def __init__(self, on_prev, on_next, on_skip, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setFixedWidth(self._W)

        self._total   = 1
        self._current = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 32)   # extra bottom for progress bar
        layout.setSpacing(0)

        # ── Step counter ──────────────────────────────────────────────
        self._step_label = QLabel()
        self._step_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        sf = QFont()
        sf.setPointSize(9)
        self._step_label.setFont(sf)
        layout.addWidget(self._step_label)
        layout.addSpacing(10)

        # ── Title ─────────────────────────────────────────────────────
        self._title = QLabel()
        tf = QFont()
        tf.setPointSize(14)
        tf.setWeight(QFont.Weight.Bold)
        self._title.setFont(tf)
        self._title.setWordWrap(True)
        layout.addWidget(self._title)
        layout.addSpacing(10)

        # ── Body ──────────────────────────────────────────────────────
        self._body = QLabel()
        bf = QFont()
        bf.setPointSize(11)
        self._body.setFont(bf)
        self._body.setWordWrap(True)
        self._body.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self._body)
        layout.addSpacing(22)

        # ── Buttons ───────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.setContentsMargins(0, 0, 0, 0)

        self._prev_btn = QPushButton("← Back")
        self._prev_btn.setFixedHeight(36)
        self._prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._prev_btn.clicked.connect(on_prev)

        self._next_btn = QPushButton("Next →")
        self._next_btn.setFixedHeight(36)
        self._next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._next_btn.clicked.connect(on_next)

        self._skip_btn = QPushButton("Skip")
        self._skip_btn.setFixedHeight(36)
        self._skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._skip_btn.clicked.connect(on_skip)

        btn_row.addWidget(self._prev_btn)
        btn_row.addWidget(self._next_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._skip_btn)
        layout.addLayout(btn_row)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt_body(text: str) -> str:
        """Convert plain body text to styled HTML."""
        escaped = _html.escape(text)
        # Highlight keyboard shortcuts like Ctrl+R
        escaped = _re.sub(
            r'(Ctrl\+\w+)',
            r'<span style="background:rgba(128,128,128,0.18);'
            r'border-radius:3px;padding:0 4px;font-family:monospace;'
            r'font-size:10px;">\1</span>',
            escaped,
        )
        escaped = escaped.replace('\n\n', '<br><br>')
        escaped = escaped.replace('\n',   '<br>')
        return f'<span style="line-height:1.6;">{escaped}</span>'

    # ── Public API ────────────────────────────────────────────────────────────

    def update_content(self, step_idx: int, total: int, title: str, body: str):
        self._total   = total
        self._current = step_idx
        self._step_label.setText(f"{step_idx + 1} / {total}")
        self._title.setText(title)
        self._body.setText(self._fmt_body(body))
        self._prev_btn.setEnabled(step_idx > 0)
        is_last = step_idx == total - 1
        self._next_btn.setText("Done" if is_last else "Next →")
        self.adjustSize()
        self.update()   # repaint progress bar

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        try:
            is_dark = self.parent()._main._dark
        except AttributeError:
            is_dark = self.palette().color(self.backgroundRole()).lightness() < 128
        if is_dark:
            bg      = QColor(26, 26, 28, 64)
            text_c  = QColor(229, 57, 53)
            sub_c   = QColor(220, 80, 70)
            border  = QColor(58, 58, 63, 80)
            trk_c   = QColor(58, 58, 63)
            fill_c  = QColor(10, 132, 255)
        else:
            bg      = QColor(255, 255, 255, 64)
            text_c  = QColor(229, 57, 53)
            sub_c   = QColor(220, 80, 70)
            border  = QColor(210, 210, 215, 80)
            trk_c   = QColor(218, 218, 223)
            fill_c  = QColor(10, 132, 255)

        self._title.setStyleSheet(
            f"color: {text_c.name()}; background: transparent;")
        self._body.setStyleSheet(
            f"color: {sub_c.name()}; background: transparent;")
        self._step_label.setStyleSheet(
            f"color: {sub_c.name()}; background: transparent;")

        # Card background
        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(border, 1.0))
        painter.drawRoundedRect(rect, 16, 16)

        # Progress bar — thin line at the very bottom of the card
        if self._total > 1:
            bar_h  = 3
            margin = 28
            bar_y  = self.height() - 14
            track_w = self.width() - margin * 2
            fill_w  = int(track_w * (self._current + 1) / self._total)

            painter.setPen(Qt.PenStyle.NoPen)

            # track
            painter.setBrush(QBrush(trk_c))
            painter.drawRoundedRect(
                QRectF(margin, bar_y, track_w, bar_h), bar_h / 2, bar_h / 2)

            # fill
            if fill_w > 0:
                painter.setBrush(QBrush(fill_c))
                painter.drawRoundedRect(
                    QRectF(margin, bar_y, fill_w, bar_h), bar_h / 2, bar_h / 2)

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

        navigate_to = step.get("navigate_to")
        if navigate_to is not None and hasattr(self._main, "navigate_if_needed"):
            tab = step.get("tab")
            self._main.navigate_if_needed(navigate_to, tab=tab)

        # Scroll the settings scroll area so the target widget is fully visible
        widget_attr = step.get("widget_attr")
        if widget_attr:
            target = getattr(self._main, widget_attr, None)
            if target and hasattr(self._main, "_settings_scroll"):
                self._main._settings_scroll.ensureWidgetVisible(target, 40, 60)

        self._bubble.update_content(
            idx, len(self._steps), step["title"], step["body"])
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

        try:
            is_dark = self._main._dark
        except AttributeError:
            is_dark = False

        # Dim the background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 150))

        if spot is not None:
            path = QPainterPath()
            path.addRoundedRect(QRectF(spot), 10, 10)

            # Clear the dim overlay inside the spotlight
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillPath(path, QBrush(Qt.GlobalColor.transparent))

            # Fill spotlight with a clean themed background
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver)
            spot_bg = QColor(26, 26, 28, 230) if is_dark else QColor(248, 248, 248, 230)
            painter.setBrush(QBrush(spot_bg))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(spot), 10, 10)

            # Blue spotlight border
            painter.setPen(QPen(QColor(10, 132, 255, 220), 2.0))
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
        base = (
            "QPushButton {"
            "  border-radius: 8px;"
            "  font-size: 13px;"
            "  padding: 0 16px;"
            "  font-weight: 500;"
            "}"
        )
        self._bubble._next_btn.setStyleSheet(
            base +
            "QPushButton { background: #0A84FF; color: #fff; border: none; }"
            "QPushButton:hover { background: #2A9AFF; }"
        )
        self._bubble._prev_btn.setStyleSheet(
            base +
            "QPushButton { background: transparent; color: #0A84FF;"
            "  border: 1.5px solid #0A84FF; }"
            "QPushButton:hover { background: rgba(10,132,255,0.10); }"
            "QPushButton:disabled { color: #aaa; border-color: #aaa; }"
        )
        self._bubble._skip_btn.setStyleSheet(
            base +
            "QPushButton { background: transparent; color: #999; border: none; }"
            "QPushButton:hover { color: #555; }"
        )

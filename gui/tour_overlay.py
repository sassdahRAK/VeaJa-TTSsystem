"""
Veaja interactive product tour.

Spawned by AppController when the user clicks the ? button.
Covers the MainWindow with a semi-transparent overlay and spotlights
each UI element one step at a time.

Usage:
    tour = TourOverlay(main_window)
    tour.show()
"""

from PyQt6.QtWidgets import QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, QRect, QRectF, QPoint, QEvent
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QFont


# ── Tour step definitions ──────────────────────────────────────────────────────

STEPS = [
    {
        "widget_attr": None,
        "title": "Welcome to Veaja!",
        "body": (
            "This quick tour walks you through every feature.\n\n"
            "Use  Next  and  Back  to navigate, or  Skip  to close."
        ),
    },

    # ── Reading from PDFs, Word, browsers ─────────────────────────────────────
    {
        "widget_attr": None,
        "title": "Reading in PDF / Word / Browser",
        "body": (
            "Veaja cannot highlight text inside other apps — that is a\n"
            "system limitation on Windows.\n\n"
            "Here is the workflow:\n"
            "1. Select text in your PDF / Word / browser\n"
            "2. Press  Ctrl+R  — Veaja copies and reads it immediately\n"
            "   (or use  Ctrl+C  and the overlay appears automatically)\n"
            "3. Watch the floating pill — it shows the current\n"
            "   word in yellow (karaoke mode) so you can follow along\n"
            "   without switching windows"
        ),
    },
    {
        "widget_attr": None,
        "title": "Overlay Karaoke — Live Word Tracker",
        "body": (
            "While Veaja speaks, the floating pill shows the current\n"
            "word highlighted in yellow inside the pill itself.\n\n"
            "You can keep your PDF or Word doc in focus — just glance\n"
            "at the pill to see where the reading is up to.\n\n"
            "Click  ⟳  on the pill to restart from the beginning."
        ),
    },

    # ── Dashboard features ─────────────────────────────────────────────────────
    {
        "widget_attr": "_text_edit",
        "title": "Text Input (Dashboard)",
        "body": (
            "Type or paste text here, then click Read.\n\n"
            "While reading, each word is highlighted in yellow from\n"
            "left to right — a progress bar for your eyes.\n\n"
            "Tip: paste long articles here for the best\n"
            "highlighting experience."
        ),
    },
    {
        "widget_attr": "_read_btn",
        "title": "Read Button",
        "body": (
            "Click Read to start speaking.\n\n"
            "• Click again → Pause  (button turns orange)\n"
            "• Click once more → Resume\n"
            "• Button is red while speaking."
        ),
    },
    {
        "widget_attr": "_stop_btn",
        "title": "Stop Button",
        "body": (
            "Immediately stops reading and clears the highlight.\n\n"
            "Tip: while paused, Stop discards your position."
        ),
    },
    {
        "widget_attr": "_online_btn",
        "title": "Online / Offline Mode",
        "body": (
            "Online  — Microsoft neural voices.\n"
            "High-quality, human-like. Requires internet.\n\n"
            "Offline — Windows system voices.\n"
            "Works without internet. More robotic."
        ),
    },
    {
        "widget_attr": "_voice_combo",
        "title": "Voice Selector",
        "body": (
            "Choose your preferred voice.\n\n"
            "Online voices include regional accents:\n"
            "US, UK, and Australian English."
        ),
    },
    {
        "widget_attr": "_speed_slider",
        "title": "Reading Speed",
        "body": (
            "Drag to speed up or slow down.\n\n"
            "Range: 50 (slow) → 400 (fast).\n"
            "Default 175 is a natural reading pace."
        ),
    },
    {
        "widget_attr": "_vol_slider",
        "title": "Volume",
        "body": "Adjust the TTS playback volume from 0 % to 100 %.",
    },
    {
        "widget_attr": "_history_list",
        "title": "Reading History",
        "body": (
            "Your last 20 texts are saved here.\n\n"
            "Double-click any item to load it back into the text box."
        ),
    },
    {
        "widget_attr": "_history_list",
        "title": "Reading History",
        "body": (
            "Your last 20 texts are saved here.\n\n"
            "Double-click any item to reload it — great for re-reading\n"
            "a passage from a PDF you had open earlier."
        ),
    },
    {
        "widget_attr": "_header_logo",
        "title": "Your Profile",
        "body": (
            "Click the avatar or the app name to open your profile.\n\n"
            "• Set a custom display name\n"
            "• Set a profile picture (shown in the overlay pill)\n"
            "• Choose your word-highlight colour"
        ),
    },
    {
        "widget_attr": "_theme_btn",
        "title": "Dark / Light Mode",
        "body": (
            "Toggle between dark and light themes.\n\n"
            "The floating overlay and tray icon both\n"
            "follow this setting automatically."
        ),
    },
    {
        "widget_attr": None,
        "title": "Word Highlighting — Two Modes",
        "body": (
            "Veaja highlights words in two places simultaneously:\n\n"
            "1.  Dashboard text box  — yellow progress bar left-to-right.\n"
            "    Best when you paste text directly into Veaja.\n\n"
            "2.  Overlay pill  — karaoke display shows the current word\n"
            "    in the pill itself, in yellow.\n"
            "    Use this when reading a PDF, Word, or browser page\n"
            "    so you never need to switch windows.\n\n"
            "Customise the colour in Profile → Highlight colour."
        ),
    },
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
    },
]


# ── Bubble widget ─────────────────────────────────────────────────────────────

class _Bubble(QWidget):
    """Floating rounded-rect card with title, body, and Prev/Next/Skip."""

    def __init__(self, on_prev, on_next, on_skip, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setMinimumWidth(300)
        self.setMaximumWidth(340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        # Step indicator
        self._step_label = QLabel()
        self._step_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        f = QFont()
        f.setPointSize(9)
        self._step_label.setFont(f)
        layout.addWidget(self._step_label)

        # Title
        self._title = QLabel()
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setWeight(QFont.Weight.Bold)
        self._title.setFont(title_font)
        self._title.setWordWrap(True)
        layout.addWidget(self._title)

        # Body
        self._body = QLabel()
        body_font = QFont()
        body_font.setPointSize(10)
        self._body.setFont(body_font)
        self._body.setWordWrap(True)
        layout.addWidget(self._body)

        layout.addSpacing(8)

        # Button row
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

        # Detect dark mode: low lightness → dark background
        is_dark = self.palette().color(self.backgroundRole()).lightness() < 128
        if is_dark:
            bg     = QColor(30, 30, 32, 250)
            text   = QColor(245, 245, 247)
            border = QColor(70, 70, 75, 200)
        else:
            bg     = QColor(255, 255, 255, 250)
            text   = QColor(28, 28, 30)
            border = QColor(210, 210, 215, 200)

        # Set text colours dynamically
        self._title.setStyleSheet(f"color: {text.name()};")
        self._body.setStyleSheet(f"color: {text.name()}; opacity: 0.85;")
        self._step_label.setStyleSheet(f"color: {text.name()}; opacity: 0.5;")

        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(border, 1.0))
        painter.drawRoundedRect(rect, 14, 14)

        # Drop shadow hint via border
        painter.setPen(Qt.PenStyle.NoPen)


# ── Main overlay ──────────────────────────────────────────────────────────────

class TourOverlay(QWidget):
    """
    Full-window semi-transparent overlay.
    Draws a spotlight (clear hole) over the current target widget,
    and shows a _Bubble near that spotlight.
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

    # ── Navigation ────────────────────────────────────────────────────────────

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
        self._bubble.update_content(idx, len(self._steps), step["title"], step["body"])
        self._position_bubble(step.get("widget_attr"))
        self.update()   # repaint overlay (spotlight position)

    # ── Spotlight target ──────────────────────────────────────────────────────

    def _target_rect(self, widget_attr: str | None) -> QRect | None:
        """Return the rect of the target widget in overlay-local coordinates."""
        if not widget_attr:
            return None
        target: QWidget | None = getattr(self._main, widget_attr, None)
        if target is None:
            return None
        # Map target's global top-left into this overlay's coordinate space
        global_pos = target.mapToGlobal(QPoint(0, 0))
        local_pos  = self.mapFromGlobal(global_pos)
        return QRect(local_pos, target.size()).adjusted(-10, -8, 10, 8)

    # ── Bubble positioning ────────────────────────────────────────────────────

    def _position_bubble(self, widget_attr: str | None):
        self._bubble.adjustSize()
        bw = self._bubble.width()
        bh = self._bubble.height()
        ow = self.width()
        oh = self.height()

        spot = self._target_rect(widget_attr)

        if spot is None:
            # Centre the bubble
            x = (ow - bw) // 2
            y = (oh - bh) // 2
        else:
            # Prefer below the spotlight; fall back to above
            gap = 16
            x = spot.left()
            y = spot.bottom() + gap
            if y + bh > oh - 20:
                y = spot.top() - bh - gap
            if y < 20:
                y = spot.bottom() + gap
            # Clamp horizontally
            x = max(12, min(x, ow - bw - 12))
            y = max(12, min(y, oh - bh - 12))

        self._bubble.move(x, y)

    # ── Painting — overlay + spotlight ───────────────────────────────────────

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        step = self._steps[self._step]
        spot = self._target_rect(step.get("widget_attr"))

        # Dim background
        dim = QColor(0, 0, 0, 160)

        if spot is None:
            painter.fillRect(self.rect(), dim)
        else:
            # Fill everything with dim colour
            painter.fillRect(self.rect(), dim)

            # Cut out the spotlight using CompositionMode_Clear
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_Clear
            )
            path = QPainterPath()
            path.addRoundedRect(QRectF(spot), 10, 10)
            painter.fillPath(path, QBrush(Qt.GlobalColor.transparent))

            # Draw accent border around spotlight
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver
            )
            accent = QColor(10, 132, 255, 200)   # blue accent
            painter.setPen(QPen(accent, 2.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(spot), 10, 10)

    # ── Intercept clicks outside the bubble to prevent accidental interaction ─

    def mousePressEvent(self, event):
        # Allow clicks through to the bubble; block everything else.
        if not self._bubble.geometry().contains(event.position().toPoint()):
            event.accept()   # swallow the click
        else:
            super().mousePressEvent(event)

    # ── Track parent resize via event filter ─────────────────────────────────

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

    # ── Button styling ────────────────────────────────────────────────────────

    def _style_buttons(self):
        base = (
            "QPushButton { border-radius: 8px; font-size: 12px; padding: 0 12px; }"
        )
        next_style = (
            f"{base}"
            "QPushButton { background: #0A84FF; color: #fff; border: none; }"
            "QPushButton:hover { background: #339AF0; }"
        )
        prev_style = (
            f"{base}"
            "QPushButton { background: transparent; color: #0A84FF; "
            "border: 1px solid #0A84FF; }"
            "QPushButton:hover { background: rgba(10,132,255,0.12); }"
            "QPushButton:disabled { color: #555; border-color: #555; }"
        )
        skip_style = (
            f"{base}"
            "QPushButton { background: transparent; color: #888; border: none; }"
            "QPushButton:hover { color: #ccc; }"
        )
        self._bubble._next_btn.setStyleSheet(next_style)
        self._bubble._prev_btn.setStyleSheet(prev_style)
        self._bubble._skip_btn.setStyleSheet(skip_style)

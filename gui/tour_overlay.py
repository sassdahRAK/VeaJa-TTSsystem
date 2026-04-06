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

from PyQt6.QtWidgets import QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QApplication
from PyQt6.QtCore    import Qt, QRect, QRectF, QPoint, QSize, QEvent, QTimer, pyqtSignal
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
        "get_started": True,   # shows the interactive drag trainer
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
        "widget_attr": "_content_stack",
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
        "widget_attr": "_content_stack",
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


# ── Drag trainer ───────────────────────────────────────────────────────────────

class _DragTrainer(QWidget):
    """
    Full-screen interactive drag exercise.

    When a real OverlayWidget is supplied the trainer shows it on screen and
    polls its position every 50 ms to detect hold → drag → release.

    Phases:
      countdown  — 3 … 2 … 1 big number, 1 s per tick
      hold       — real overlay visible, "Hold on the overlay icon"
      drag       — user is dragging, "Move it anywhere!"
      done       — green "Done ✓" for 1.5 s then emits finished
    """

    finished = pyqtSignal()

    # Fallback fake-pill dimensions (used only when no real overlay is given)
    _PILL_W = 140
    _PILL_H = 50

    def __init__(self, is_dark: bool,
                 overlay_widget: QWidget | None = None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._is_dark        = is_dark
        self._overlay_widget = overlay_widget

        self._phase = "countdown"
        self._count = 3

        # Real-overlay tracking
        self._poll_start_pos    = QPoint(0, 0)
        self._overlay_was_visible = False

        # Fake-pill tracking (fallback when overlay_widget is None)
        self._pill_pos    = QPoint(0, 0)
        self._drag_active = False
        self._drag_offset = QPoint(0, 0)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setMouseTracking(True)

        self._cd_timer = QTimer(self)
        self._cd_timer.timeout.connect(self._tick)

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_overlay)

    # ── Public start ──────────────────────────────────────────────────────────

    def start(self):
        """Reset state and begin the countdown."""
        self._phase = "countdown"
        self._count = 3
        self._poll_timer.stop()
        if self._overlay_widget is None:
            self._reset_pill_pos()
        self._cd_timer.start(1000)
        self.show()
        self.raise_()
        self.update()

    # ── Countdown ─────────────────────────────────────────────────────────────

    def _tick(self):
        self._count -= 1
        if self._count <= 0:
            self._cd_timer.stop()
            self._phase = "hold"
            if self._overlay_widget is not None:
                self._show_real_overlay()
            else:
                self._reset_pill_pos()
        self.update()

    # ── Real overlay management ───────────────────────────────────────────────

    def _show_real_overlay(self):
        ow = self._overlay_widget
        self._overlay_was_visible = ow.isVisible()

        # Position the pill somewhere visible if it wasn't already shown
        if not self._overlay_was_visible:
            screen = QApplication.primaryScreen()
            if screen:
                sg = screen.availableGeometry()
                # Top-centre of screen — above the dimmed main window instructions
                cx = sg.center().x()
                cy = sg.top() + 130
                try:
                    ow.show_near(cx, cy)
                except Exception:
                    try:
                        ow.show_overlay()
                    except Exception:
                        pass
            else:
                try:
                    ow.show_overlay()
                except Exception:
                    pass

        # Record starting position for movement detection
        self._poll_start_pos = ow.pos()
        # Poll every 50 ms to detect drag & release
        self._poll_timer.start(50)

    def _poll_overlay(self):
        """Check if the real overlay widget has been dragged and released."""
        ow = self._overlay_widget
        if not ow:
            return

        cur   = ow.pos()
        delta = cur - self._poll_start_pos
        moved = abs(delta.x()) > 15 or abs(delta.y()) > 15

        mouse_down = bool(QApplication.mouseButtons() & Qt.MouseButton.LeftButton)

        if moved and mouse_down and self._phase == "hold":
            # User has started dragging
            self._phase = "drag"
            self.update()
        elif moved and not mouse_down and self._phase in ("hold", "drag"):
            # User dragged and released
            self._poll_timer.stop()
            self._phase = "done"
            self.update()
            QTimer.singleShot(1500, self._finish)

    # ── Fake pill helpers (fallback only) ─────────────────────────────────────

    def _reset_pill_pos(self):
        self._pill_pos = QPoint(
            self.width()  // 2 - self._PILL_W // 2,
            self.height() // 2 - self._PILL_H // 2,
        )

    def _pill_rect(self) -> QRect:
        return QRect(self._pill_pos, QSize(self._PILL_W, self._PILL_H))

    # ── Mouse events (fake-pill fallback only) ────────────────────────────────

    def mousePressEvent(self, event):
        if self._overlay_widget is not None:
            event.accept()
            return
        if self._phase == "hold":
            if self._pill_rect().contains(event.position().toPoint()):
                self._drag_active = True
                self._drag_offset = event.position().toPoint() - self._pill_pos
                self._phase = "drag"
                self.update()
        event.accept()

    def mouseMoveEvent(self, event):
        if self._overlay_widget is not None:
            event.accept()
            return
        if self._phase == "drag" and self._drag_active:
            new_pos = event.position().toPoint() - self._drag_offset
            new_pos.setX(max(0, min(new_pos.x(), self.width()  - self._PILL_W)))
            new_pos.setY(max(0, min(new_pos.y(), self.height() - self._PILL_H)))
            self._pill_pos = new_pos
            self.update()
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._overlay_widget is not None:
            event.accept()
            return
        if self._phase == "drag":
            self._drag_active = False
            self._phase = "done"
            self.update()
            QTimer.singleShot(1500, self._finish)
        event.accept()

    # ── Finish ────────────────────────────────────────────────────────────────

    def _finish(self):
        self._cd_timer.stop()
        self._poll_timer.stop()
        # Hide the real overlay only if we showed it — leave it if it was
        # already visible before the trainer started.
        if self._overlay_widget is not None and not self._overlay_was_visible:
            try:
                self._overlay_widget.hide_overlay()
            except Exception:
                pass
        self.hide()
        self.finished.emit()

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Dim over the whole trainer area
        painter.fillRect(self.rect(), QColor(0, 0, 0, 210))

        if self._phase == "countdown":
            self._paint_countdown(painter)
        elif self._phase in ("hold", "drag"):
            if self._overlay_widget is not None:
                self._paint_real_instruction(painter)
            else:
                self._paint_fake_drag(painter)
        elif self._phase == "done":
            self._paint_done(painter)

        painter.end()

    # ── Countdown paint ───────────────────────────────────────────────────────

    def _paint_countdown(self, painter: QPainter):
        font = QFont()
        font.setPointSize(96)
        font.setWeight(QFont.Weight.Black)
        painter.setFont(font)
        painter.setPen(QColor(10, 132, 255))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, str(self._count))

        sf = QFont()
        sf.setPointSize(15)
        painter.setFont(sf)
        painter.setPen(QColor(200, 200, 200, 180))
        sub = QRect(0, self.height() // 2 + 70, self.width(), 36)
        painter.drawText(sub, Qt.AlignmentFlag.AlignCenter, "Get ready…")

    # ── Real overlay instruction paint ────────────────────────────────────────

    def _paint_real_instruction(self, painter: QPainter):
        if self._phase == "hold":
            headline = "Hold on the overlay icon"
            hint     = "The floating Veaja pill is now visible — click and hold it, then drag it"
        else:
            headline = "Move it anywhere on screen!"
            hint     = "Release the mouse when you are done"

        hf = QFont()
        hf.setPointSize(22)
        hf.setWeight(QFont.Weight.Bold)
        painter.setFont(hf)
        painter.setPen(QColor(255, 255, 255, 235))
        h_rect = QRect(0, self.height() // 3, self.width(), 50)
        painter.drawText(h_rect, Qt.AlignmentFlag.AlignCenter, headline)

        sf = QFont()
        sf.setPointSize(12)
        painter.setFont(sf)
        painter.setPen(QColor(180, 180, 180, 200))
        s_rect = QRect(40, self.height() // 3 + 58, self.width() - 80, 40)
        painter.drawText(
            s_rect,
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop,
            hint,
        )

        # Small arrow pointing upward toward where the pill is placed
        if self._phase == "hold":
            cx = self.width() // 2
            tip_y = self.height() // 3 - 20
            painter.setPen(QPen(QColor(10, 132, 255, 160), 2))
            painter.drawLine(cx, tip_y, cx, tip_y - 40)
            # Arrowhead
            painter.drawLine(cx, tip_y - 40, cx - 10, tip_y - 25)
            painter.drawLine(cx, tip_y - 40, cx + 10, tip_y - 25)

    # ── Fake pill drag paint (fallback) ───────────────────────────────────────

    def _paint_fake_drag(self, painter: QPainter):
        if self._phase == "hold":
            headline = "Hold on the overlay icon"
            hint     = "Click and hold the pill below, then drag it"
        else:
            headline = "Move it anywhere on screen!"
            hint     = "Release the mouse when you are done"

        hf = QFont()
        hf.setPointSize(20)
        hf.setWeight(QFont.Weight.Bold)
        painter.setFont(hf)
        painter.setPen(QColor(255, 255, 255, 230))
        h_rect = QRect(0, self.height() // 5, self.width(), 44)
        painter.drawText(h_rect, Qt.AlignmentFlag.AlignCenter, headline)

        sf = QFont()
        sf.setPointSize(12)
        painter.setFont(sf)
        painter.setPen(QColor(180, 180, 180, 200))
        s_rect = QRect(0, self.height() // 5 + 50, self.width(), 30)
        painter.drawText(s_rect, Qt.AlignmentFlag.AlignCenter, hint)

        # Draggable fake pill
        pr = self._pill_rect()
        pill_bg = QColor(28, 28, 32, 240) if self._is_dark else QColor(245, 245, 250, 240)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 60)))
        painter.drawRoundedRect(QRectF(pr).adjusted(3, 4, 3, 4), 25, 25)

        painter.setPen(QPen(QColor(10, 132, 255), 2.5))
        painter.setBrush(QBrush(pill_bg))
        painter.drawRoundedRect(QRectF(pr), 25, 25)

        lf = QFont()
        lf.setPointSize(13)
        lf.setWeight(QFont.Weight.DemiBold)
        painter.setFont(lf)
        painter.setPen(QColor(10, 132, 255))
        painter.drawText(pr, Qt.AlignmentFlag.AlignCenter, "⬤  Veaja")

        if self._phase == "hold":
            painter.setPen(QPen(QColor(10, 132, 255, 90), 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(pr).adjusted(-10, -10, 10, 10), 33, 33)

    # ── Done paint ────────────────────────────────────────────────────────────

    def _paint_done(self, painter: QPainter):
        font = QFont()
        font.setPointSize(60)
        font.setWeight(QFont.Weight.Black)
        painter.setFont(font)
        painter.setPen(QColor(52, 199, 89))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Done ✓")

        sf = QFont()
        sf.setPointSize(13)
        painter.setFont(sf)
        painter.setPen(QColor(200, 200, 200, 200))
        sub = QRect(0, self.height() // 2 + 60, self.width(), 36)
        painter.drawText(sub, Qt.AlignmentFlag.AlignCenter,
                         "Great! Now you know how to drag the overlay pill.")


# ── Bubble widget ──────────────────────────────────────────────────────────────

class _Bubble(QWidget):
    """Floating rounded card — polished design with progress bar."""

    _W = 400   # fixed card width

    def __init__(self, on_prev, on_next, on_skip, on_get_started, parent=None):
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

        # "Get Started" — only visible on steps with "get_started": True
        self._gs_btn = QPushButton("▶  Get Started")
        self._gs_btn.setFixedHeight(36)
        self._gs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._gs_btn.clicked.connect(on_get_started)
        self._gs_btn.hide()

        self._next_btn = QPushButton("Next →")
        self._next_btn.setFixedHeight(36)
        self._next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._next_btn.clicked.connect(on_next)

        self._skip_btn = QPushButton("Skip")
        self._skip_btn.setFixedHeight(36)
        self._skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._skip_btn.clicked.connect(on_skip)

        btn_row.addWidget(self._prev_btn)
        btn_row.addWidget(self._gs_btn)    # between ← Back and Next →
        btn_row.addWidget(self._next_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._skip_btn)
        layout.addLayout(btn_row)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt_body(text: str) -> str:
        """Convert plain body text to styled HTML."""
        escaped = _html.escape(text)
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

    def update_content(self, step_idx: int, total: int, title: str, body: str,
                       show_get_started: bool = False):
        self._total   = total
        self._current = step_idx
        self._step_label.setText(f"{step_idx + 1} / {total}")
        self._title.setText(title)
        self._body.setText(self._fmt_body(body))
        self._prev_btn.setEnabled(step_idx > 0)
        is_last = step_idx == total - 1
        self._next_btn.setText("Done" if is_last else "Next →")
        self._gs_btn.setVisible(show_get_started)
        self.adjustSize()
        self.update()

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        try:
            is_dark = self.parent()._main._dark
        except AttributeError:
            is_dark = self.palette().color(self.backgroundRole()).lightness() < 128
        if is_dark:
            bg      = QColor(26, 26, 28, 191)
            text_c  = QColor(229, 57, 53)
            sub_c   = QColor(220, 80, 70)
            border  = QColor(58, 58, 63, 80)
            trk_c   = QColor(58, 58, 63)
            fill_c  = QColor(10, 132, 255)
        else:
            bg      = QColor(255, 255, 255, 191)
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

        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(border, 1.0))
        painter.drawRoundedRect(rect, 16, 16)

        if self._total > 1:
            bar_h   = 3
            margin  = 28
            bar_y   = self.height() - 14
            track_w = self.width() - margin * 2
            fill_w  = int(track_w * (self._current + 1) / self._total)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(trk_c))
            painter.drawRoundedRect(
                QRectF(margin, bar_y, track_w, bar_h), bar_h / 2, bar_h / 2)
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

    def __init__(self, main_window: QWidget, overlay_widget: QWidget | None = None):
        super().__init__(main_window)
        self._main           = main_window
        self._overlay_widget = overlay_widget   # real OverlayWidget (may be None)
        self._step           = 0
        self._steps          = STEPS
        self._trainer: _DragTrainer | None = None

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.resize(main_window.size())

        self._bubble = _Bubble(
            on_prev=self._prev,
            on_next=self._next,
            on_skip=self.close,
            on_get_started=self._on_get_started,
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

        widget_attr = step.get("widget_attr")
        if widget_attr:
            target = getattr(self._main, widget_attr, None)
            if target and hasattr(self._main, "_settings_scroll"):
                self._main._settings_scroll.ensureWidgetVisible(target, 40, 60)

        show_gs = bool(step.get("get_started", False))
        self._bubble.update_content(
            idx, len(self._steps), step["title"], step["body"],
            show_get_started=show_gs,
        )
        self._position_bubble(step.get("widget_attr"))
        self.update()

    # ── Interactive drag trainer ───────────────────────────────────────────────

    def _on_get_started(self):
        """User clicked 'Get Started' — launch the drag mini-tutorial."""
        is_dark = getattr(self._main, "_dark", False)
        if self._trainer is None:
            self._trainer = _DragTrainer(
                is_dark=is_dark,
                overlay_widget=self._overlay_widget,
                parent=self,
            )
            self._trainer.finished.connect(self._on_trainer_finished)
        self._trainer.setGeometry(self.rect())
        self._trainer.start()

    def _on_trainer_finished(self):
        """Drag exercise completed — return to the same step."""
        if self._trainer:
            self._trainer.hide()
        self._go_to(self._step)

    # ── Spotlight ──────────────────────────────────────────────────────────────

    def _target_rect(self, widget_attr: str | None) -> QRect | None:
        if not widget_attr:
            return None
        target: QWidget | None = getattr(self._main, widget_attr, None)
        if target is None or not target.isVisibleTo(self._main):
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

        painter.fillRect(self.rect(), QColor(0, 0, 0, 150))

        if spot is not None:
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver)
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
            if self._trainer and self._trainer.isVisible():
                self._trainer.setGeometry(self.rect())
            self._position_bubble(self._steps[self._step].get("widget_attr"))
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        self._main.removeEventFilter(self)
        if self._trainer:
            self._trainer.hide()
            self._trainer = None
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
        self._bubble._gs_btn.setStyleSheet(
            base +
            "QPushButton { background: #34C759; color: #fff; border: none; }"
            "QPushButton:hover { background: #2EB350; }"
        )

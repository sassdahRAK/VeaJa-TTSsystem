"""
Veaja interactive live-teach tutorial.

Spawned by AppController when the user clicks Tutorial in the sidebar.
Covers the MainWindow with a semi-transparent spotlight overlay and
navigates to the relevant page before spotlighting each widget.
"""

import html as _html
import re   as _re

from PyQt6.QtWidgets import (
    QWidget, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout,
    QApplication, QMenu,
)
from PyQt6.QtCore  import Qt, QRect, QRectF, QPoint, QEvent, QTimer, pyqtSignal
from PyQt6.QtGui   import QPainter, QColor, QPen, QBrush, QFont


# ── Tour step definitions ──────────────────────────────────────────────────────

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
        "get_started": True,
    },
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

# ── Training phase content ──────────────────────────────────────────────────────

_TRAIN_CONTENT = {
    "countdown":       ("{n}",                              "Get ready to practise with the Veaja overlay pill…"),
    "hold":            ("Hold on the overlay icon",         "The Veaja pill is now visible on your screen.\nClick and hold it, then drag it anywhere."),
    "drag":            ("Move it anywhere!",                "Release the mouse when you are done."),
    "drag_done":       ("Great  ✓",                         "Preparing next step…"),
    "ctrl_r":          ("Select text  →  press Ctrl + R",  "Go to any window, select some text, then press Ctrl+R.\n(Veaja will demo it for you in a moment…)"),
    "ctrl_r_reading":  ("Select text  →  press Ctrl + R",  "Veaja is reading — watch the overlay pill highlight each word!"),
    "move":            ("Hold the overlay and move it",     "Drag the Veaja pill to a new spot anywhere on your screen."),
    "moving":          ("Keep going!",                      "Release when you are happy with the new position."),
    "right_click":     ("Right-click on the overlay icon",  "Right-click the Veaja pill to see quick options:\nHide overlay   •   Go to settings"),
    "done":            ("Done  ✓",                          "You know how to use the Veaja overlay.\nReturning to the tutorial…"),
}

_STEP_BADGES = {
    "countdown":      "Preparing…",
    "hold":           "Step 1 / 4  —  Drag the pill",
    "drag":           "Step 1 / 4  —  Drag the pill",
    "drag_done":      "Step 1 / 4  ✓",
    "ctrl_r":         "Step 2 / 4  —  Ctrl + R",
    "ctrl_r_reading": "Step 2 / 4  —  Ctrl + R",
    "move":           "Step 3 / 4  —  Move the pill",
    "moving":         "Step 3 / 4  —  Move the pill",
    "right_click":    "Step 4 / 4  —  Right-click",
    "done":           "All done!",
}

_DEMO_TEXT = (
    "Hello! This is Veaja reading your selected text aloud. "
    "Just select any text in any window and press Ctrl R — "
    "Veaja will read it instantly."
)


# ── Standalone training card ───────────────────────────────────────────────────

class _DragTrainer(QWidget):
    """
    Always-on-top floating instruction card for the interactive training.

    KEY DESIGN: parented to None (standalone top-level window) so it stays
    visible even when the main window hides — which happens automatically
    when the Veaja overlay pill appears on screen.

    After training finishes it calls on_done() to restore the main window.
    """

    def __init__(self, main_window: QWidget,
                 overlay_widget: QWidget | None = None,
                 speak_callback=None,
                 on_done=None):
        super().__init__(None)           # ← no parent; standalone window
        self._main    = main_window
        self._ow      = overlay_widget
        self._speak   = speak_callback
        self._on_done = on_done

        self._phase      = "countdown"
        self._count      = 3
        self._poll_start = QPoint(0, 0)
        self._ow_was_vis = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._build_ui()

        self._cd_timer   = QTimer(self)
        self._cd_timer.timeout.connect(self._tick)
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_fn)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 20, 26, 22)
        lay.setSpacing(0)

        # Step badge
        self._badge = QLabel()
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = QFont(); f.setPointSize(9)
        self._badge.setFont(f)
        lay.addWidget(self._badge)
        lay.addSpacing(10)

        # Title
        self._lbl_title = QLabel()
        self._lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_title.setWordWrap(True)
        f = QFont(); f.setPointSize(16); f.setWeight(QFont.Weight.Bold)
        self._lbl_title.setFont(f)
        lay.addWidget(self._lbl_title)
        lay.addSpacing(10)

        # Body
        self._lbl_body = QLabel()
        self._lbl_body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_body.setWordWrap(True)
        f = QFont(); f.setPointSize(11)
        self._lbl_body.setFont(f)
        lay.addWidget(self._lbl_body)
        lay.addSpacing(18)

        # Exit button
        self._exit_btn = QPushButton("Exit training")
        self._exit_btn.setFixedHeight(32)
        self._exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._exit_btn.clicked.connect(self._exit)
        lay.addWidget(self._exit_btn)

        self.setFixedWidth(390)

    def _apply_theme(self):
        is_dark  = getattr(self._main, "_dark", True)
        text_c   = "#e5e5e8" if is_dark else "#111115"
        sub_c    = "#8888a0" if is_dark else "#55555e"
        badge_c  = "#6060b0" if is_dark else "#7070b8"
        exit_fg  = "#777"
        exit_bdr = "#555" if is_dark else "#bbb"

        self._lbl_title.setStyleSheet(f"color:{text_c}; background:transparent;")
        self._lbl_body.setStyleSheet(f"color:{sub_c}; background:transparent;")
        self._badge.setStyleSheet(f"color:{badge_c}; background:transparent;")
        self._exit_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; color:{exit_fg};"
            f"  border:1px solid {exit_bdr}; border-radius:6px; font-size:12px; }}"
            f"QPushButton:hover {{ color:#aaa; border-color:#999; }}"
        )

    def _refresh(self):
        """Update all labels for the current phase."""
        self._apply_theme()
        title, body = _TRAIN_CONTENT.get(self._phase, ("", ""))
        if self._phase == "countdown":
            title = title.format(n=self._count)
        self._badge.setText(_STEP_BADGES.get(self._phase, ""))
        self._lbl_title.setText(title)
        self._lbl_body.setText(body)
        self.adjustSize()

    # ── Entry point ───────────────────────────────────────────────────────────

    def show_and_start(self):
        """Make the overlay pill visible then begin the countdown."""
        ow = self._ow
        if ow:
            self._ow_was_vis = ow.isVisible()
            if not ow.isVisible():
                screen = QApplication.primaryScreen()
                if screen:
                    sg = screen.availableGeometry()
                    try:
                        ow.show_near(sg.center().x(), sg.top() + 120)
                    except Exception:
                        try:
                            ow.show_overlay()
                        except Exception:
                            pass
            self._poll_start = ow.pos()

        # Position this card at bottom-centre of screen
        screen = QApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            self.adjustSize()
            self.move(
                sg.center().x() - self.width() // 2,
                sg.bottom() - self.height() - 70,
            )

        self._phase = "countdown"
        self._count = 3
        self._refresh()
        self.show()
        self.raise_()
        self._cd_timer.start(1000)

    # ── Countdown ─────────────────────────────────────────────────────────────

    def _tick(self):
        self._count -= 1
        if self._count <= 0:
            self._cd_timer.stop()
            self._go("hold")
        else:
            self._refresh()

    # ── Phase machine ─────────────────────────────────────────────────────────

    def _go(self, phase: str):
        self._phase = phase
        self._cd_timer.stop()
        self._poll_timer.stop()
        self._refresh()

        if phase == "hold":
            if self._ow:
                self._poll_start = self._ow.pos()
                self._poll_timer.start(50)

        elif phase == "drag_done":
            QTimer.singleShot(
                1500,
                lambda: self._go("ctrl_r") if self._phase == "drag_done" else None,
            )

        elif phase == "ctrl_r":
            QTimer.singleShot(2000, self._auto_read)
            QTimer.singleShot(
                10000,
                lambda: self._go("move")
                if self._phase in ("ctrl_r", "ctrl_r_reading") else None,
            )

        elif phase == "move":
            if self._ow:
                self._poll_start = self._ow.pos()
                self._poll_timer.start(50)
            else:
                QTimer.singleShot(
                    5000,
                    lambda: self._go("right_click") if self._phase == "move" else None,
                )

        elif phase == "right_click":
            if self._ow:
                self._ow.installEventFilter(self)
            else:
                QTimer.singleShot(
                    4000,
                    lambda: self._go("done") if self._phase == "right_click" else None,
                )

        elif phase == "done":
            QTimer.singleShot(
                2000,
                lambda: self._finish() if self._phase == "done" else None,
            )

    # ── Poll ──────────────────────────────────────────────────────────────────

    def _poll_fn(self):
        ow = self._ow
        if not ow:
            return
        delta      = ow.pos() - self._poll_start
        moved      = abs(delta.x()) > 15 or abs(delta.y()) > 15
        mouse_down = bool(QApplication.mouseButtons() & Qt.MouseButton.LeftButton)

        if self._phase in ("hold", "drag"):
            if moved and mouse_down:
                self._phase = "drag"
                self._refresh()
            elif moved and not mouse_down:
                self._poll_timer.stop()
                self._go("drag_done")

        elif self._phase in ("move", "moving"):
            if moved and mouse_down:
                self._phase = "moving"
                self._refresh()
            elif moved and not mouse_down:
                self._poll_timer.stop()
                self._go("right_click")

    # ── Auto-read demo ────────────────────────────────────────────────────────

    def _auto_read(self):
        if self._phase != "ctrl_r":
            return
        self._phase = "ctrl_r_reading"
        self._refresh()
        if self._speak:
            try:
                self._speak(_DEMO_TEXT)
            except Exception:
                pass

    # ── Right-click interception ──────────────────────────────────────────────

    def eventFilter(self, obj, event):
        if (obj is self._ow
                and self._phase == "right_click"
                and event.type() == QEvent.Type.MouseButtonPress
                and event.button() == Qt.MouseButton.RightButton):
            self._ow.removeEventFilter(self)
            pos = event.globalPosition().toPoint()
            QTimer.singleShot(0, lambda: self._show_menu(pos))
            return True
        return super().eventFilter(obj, event)

    def _show_menu(self, pos):
        menu = QMenu()
        menu.setStyleSheet(
            "QMenu { background:#1e1e22; border:1px solid #3a3a42;"
            "  border-radius:8px; color:#e0e0e0; font-size:13px; padding:4px; }"
            "QMenu::item { padding:8px 22px; border-radius:6px; }"
            "QMenu::item:selected { background:#0A84FF; color:#fff; }"
        )
        menu.addAction("🔲   Hide overlay")
        menu.addAction("⚙   Go to settings")
        menu.exec(pos)
        if self._phase == "right_click":
            self._go("done")

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def _exit(self):
        self._finish()

    def _finish(self):
        self._cd_timer.stop()
        self._poll_timer.stop()
        ow = self._ow
        if ow:
            try:
                ow.removeEventFilter(self)
            except Exception:
                pass
            if not self._ow_was_vis:
                try:
                    ow.hide_overlay()
                except Exception:
                    pass
        self.close()
        if self._on_done:
            self._on_done()

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        is_dark = getattr(self._main, "_dark", True)
        bg = QColor(20, 20, 24, 246) if is_dark else QColor(248, 248, 252, 246)
        bd = QColor(55, 55, 65, 200) if is_dark else QColor(195, 195, 205, 200)
        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(bd, 1.0))
        painter.drawRoundedRect(
            QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 14, 14)
        painter.end()


# ── Tutorial bubble ────────────────────────────────────────────────────────────

class _Bubble(QWidget):
    """Floating rounded card shown inside TourOverlay."""

    _W = 400

    def __init__(self, on_prev, on_next, on_skip, on_get_started, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setFixedWidth(self._W)

        self._total   = 1
        self._current = 0

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 22, 28, 32)
        lay.setSpacing(0)

        self._step_label = QLabel()
        self._step_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        f = QFont(); f.setPointSize(9)
        self._step_label.setFont(f)
        lay.addWidget(self._step_label)
        lay.addSpacing(10)

        self._title = QLabel()
        f = QFont(); f.setPointSize(14); f.setWeight(QFont.Weight.Bold)
        self._title.setFont(f)
        self._title.setWordWrap(True)
        lay.addWidget(self._title)
        lay.addSpacing(10)

        self._body = QLabel()
        f = QFont(); f.setPointSize(11)
        self._body.setFont(f)
        self._body.setWordWrap(True)
        self._body.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(self._body)
        lay.addSpacing(22)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.setContentsMargins(0, 0, 0, 0)

        self._prev_btn = QPushButton("← Back")
        self._prev_btn.setFixedHeight(36)
        self._prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._prev_btn.clicked.connect(on_prev)

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
        btn_row.addWidget(self._gs_btn)
        btn_row.addWidget(self._next_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._skip_btn)
        lay.addLayout(btn_row)

    @staticmethod
    def _fmt(text: str) -> str:
        escaped = _html.escape(text)
        escaped = _re.sub(
            r'(Ctrl\+\w+)',
            r'<span style="background:rgba(128,128,128,0.18);'
            r'border-radius:3px;padding:0 4px;font-family:monospace;'
            r'font-size:10px;">\1</span>',
            escaped,
        )
        escaped = escaped.replace('\n\n', '<br><br>').replace('\n', '<br>')
        return f'<span style="line-height:1.6;">{escaped}</span>'

    def update_content(self, step_idx: int, total: int, title: str, body: str,
                       show_get_started: bool = False):
        self._total   = total
        self._current = step_idx
        self._step_label.setText(f"{step_idx + 1} / {total}")
        self._title.setText(title)
        self._body.setText(self._fmt(body))
        self._prev_btn.setEnabled(step_idx > 0)
        self._next_btn.setText("Done" if step_idx == total - 1 else "Next →")
        self._gs_btn.setVisible(show_get_started)
        self.adjustSize()
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        try:
            is_dark = self.parent()._main._dark
        except AttributeError:
            is_dark = self.palette().color(self.backgroundRole()).lightness() < 128

        if is_dark:
            bg     = QColor(26, 26, 28, 191)
            text_c = QColor(229, 57, 53)
            sub_c  = QColor(220, 80, 70)
            border = QColor(58, 58, 63, 80)
            trk_c  = QColor(58, 58, 63)
            fill_c = QColor(10, 132, 255)
        else:
            bg     = QColor(255, 255, 255, 191)
            text_c = QColor(229, 57, 53)
            sub_c  = QColor(220, 80, 70)
            border = QColor(210, 210, 215, 80)
            trk_c  = QColor(218, 218, 223)
            fill_c = QColor(10, 132, 255)

        self._title.setStyleSheet(f"color:{text_c.name()}; background:transparent;")
        self._body.setStyleSheet(f"color:{sub_c.name()}; background:transparent;")
        self._step_label.setStyleSheet(f"color:{sub_c.name()}; background:transparent;")

        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(border, 1.0))
        painter.drawRoundedRect(
            QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 16, 16)

        if self._total > 1:
            bar_h   = 3;  margin  = 28
            bar_y   = self.height() - 14
            track_w = self.width() - margin * 2
            fill_w  = int(track_w * (self._current + 1) / self._total)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(trk_c))
            painter.drawRoundedRect(QRectF(margin, bar_y, track_w, bar_h), 1.5, 1.5)
            if fill_w > 0:
                painter.setBrush(QBrush(fill_c))
                painter.drawRoundedRect(QRectF(margin, bar_y, fill_w, bar_h), 1.5, 1.5)

        painter.setPen(Qt.PenStyle.NoPen)


# ── Main tutorial overlay ──────────────────────────────────────────────────────

class TourOverlay(QWidget):
    """
    Full-window semi-transparent overlay drawn as a child of MainWindow.

    When 'Get Started' is clicked on the Reading step the training is
    handed to a standalone _DragTrainer window (always-on-top, no parent)
    that stays visible even after MainWindow hides due to the overlay rule.
    On completion the trainer calls back to restore MainWindow + TourOverlay.
    """

    def __init__(self, main_window: QWidget,
                 overlay_widget: QWidget | None = None,
                 speak_callback=None):
        super().__init__(main_window)
        self._main           = main_window
        self._overlay_widget = overlay_widget
        self._speak_callback = speak_callback
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

        nav = step.get("navigate_to")
        if nav is not None and hasattr(self._main, "navigate_if_needed"):
            self._main.navigate_if_needed(nav, tab=step.get("tab"))

        wa = step.get("widget_attr")
        if wa:
            t = getattr(self._main, wa, None)
            if t and hasattr(self._main, "_settings_scroll"):
                self._main._settings_scroll.ensureWidgetVisible(t, 40, 60)

        self._bubble.update_content(
            idx, len(self._steps), step["title"], step["body"],
            show_get_started=bool(step.get("get_started", False)),
        )
        self._position_bubble(step.get("widget_attr"))
        self.update()

    # ── Get Started ────────────────────────────────────────────────────────────

    def _on_get_started(self):
        """
        Launch the standalone training card alongside the overlay pill.
        Both windows float on top of any app.
        When training finishes, on_done() restores the main window.
        """
        step = self._step   # capture for closure

        def on_done():
            # Bring the main window (and this TourOverlay) back
            self._main.show()
            self._main.activateWindow()
            self._main.raise_()
            self.show()
            self.raise_()
            self._go_to(step)

        self._trainer = _DragTrainer(
            main_window=self._main,
            overlay_widget=self._overlay_widget,
            speak_callback=self._speak_callback,
            on_done=on_done,
        )
        self._trainer.show_and_start()

    # ── Spotlight ──────────────────────────────────────────────────────────────

    def _target_rect(self, widget_attr: str | None) -> QRect | None:
        if not widget_attr:
            return None
        target: QWidget | None = getattr(self._main, widget_attr, None)
        if target is None or not target.isVisibleTo(self._main):
            return None
        gp = target.mapToGlobal(QPoint(0, 0))
        lp = self.mapFromGlobal(gp)
        return QRect(lp, target.size()).adjusted(-10, -8, 10, 8)

    def _position_bubble(self, widget_attr: str | None):
        self._bubble.adjustSize()
        bw, bh = self._bubble.width(), self._bubble.height()
        ow, oh = self.width(), self.height()
        spot = self._target_rect(widget_attr)

        if spot is None:
            x = (ow - bw) // 2
            y = (oh - bh) // 2
        else:
            gap = 16
            x   = spot.left()
            y   = spot.bottom() + gap
            if y + bh > oh - 20:
                y = spot.top() - bh - gap
            if y < 20:
                y = spot.bottom() + gap
            x = max(12, min(x, ow - bw - 12))
            y = max(12, min(y, oh - bh - 12))

        self._bubble.move(x, y)

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 150))

        spot = self._target_rect(self._steps[self._step].get("widget_attr"))
        if spot is not None:
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor(10, 132, 255, 220), 2.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(spot), 10, 10)

    # ── Events ────────────────────────────────────────────────────────────────

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
        if self._trainer:
            self._trainer.close()
            self._trainer = None
        super().closeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.resize(self._main.size())
        self.raise_()

    # ── Button styling ─────────────────────────────────────────────────────────

    def _style_buttons(self):
        base = (
            "QPushButton { border-radius:8px; font-size:13px;"
            "  padding:0 16px; font-weight:500; }"
        )
        self._bubble._next_btn.setStyleSheet(
            base +
            "QPushButton { background:#0A84FF; color:#fff; border:none; }"
            "QPushButton:hover { background:#2A9AFF; }"
        )
        self._bubble._prev_btn.setStyleSheet(
            base +
            "QPushButton { background:transparent; color:#0A84FF;"
            "  border:1.5px solid #0A84FF; }"
            "QPushButton:hover { background:rgba(10,132,255,0.10); }"
            "QPushButton:disabled { color:#aaa; border-color:#aaa; }"
        )
        self._bubble._skip_btn.setStyleSheet(
            base +
            "QPushButton { background:transparent; color:#999; border:none; }"
            "QPushButton:hover { color:#555; }"
        )
        self._bubble._gs_btn.setStyleSheet(
            base +
            "QPushButton { background:#34C759; color:#fff; border:none; }"
            "QPushButton:hover { background:#2EB350; }"
        )

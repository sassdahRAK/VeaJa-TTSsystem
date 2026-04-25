"""
gui/tour_overlay.py — Veaja Interactive Tutorial Overlay
=========================================================

Provides a live, step-by-step guided tour of Veaja's features.
Launched by AppController when the user clicks "Tutorial" in the sidebar.

Architecture
------------
  TourOverlay
    ├── Draws a semi-transparent dim over the MainWindow
    ├── Spotlights a target widget with a blue border
    ├── Shows a floating _Bubble card with navigation buttons
    └── On "Get Started" → spawns _DragTrainer (standalone window)

  _DragTrainer
    ├── Parented to None  →  survives when MainWindow hides
    ├── WindowStaysOnTopHint  →  floats above all other apps
    ├── Guides user through 4 interactive steps with the real overlay pill
    └── Calls on_done() when finished to restore the main window

Key design rule
---------------
  When the Veaja overlay pill appears, MainWindow hides automatically
  (enforced by WindowManager — cannot be broken).  _DragTrainer is
  therefore a *standalone* top-level window so it stays visible even
  while the main window is hidden.
"""

from __future__ import annotations

import html as _html
import re   as _re

from PyQt6.QtWidgets import (
    QWidget, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout,
    QApplication, QMenu,
)
from PyQt6.QtCore  import Qt, QRect, QRectF, QPoint, QEvent, QTimer
from PyQt6.QtGui   import QPainter, QColor, QPen, QBrush, QFont


# ── Tutorial step definitions ─────────────────────────────────────────────────
#
# Each dict describes one slide in the tour.
#
# Keys:
#   widget_attr  — attribute name on MainWindow to spotlight (None = centre card)
#   title        — bold heading shown in the bubble
#   body         — descriptive body text (supports \n for line breaks)
#   navigate_to  — sidebar page index to switch to before showing (None = stay)
#   tab          — optional tab index within the page
#   get_started  — True adds a "▶ Get Started" button for interactive training

STEPS: list[dict] = [
    {
        "widget_attr": None,
        "title": "Welcome to Veaja!",
        "body": "Tap Next to walk through each feature live.\nUse Back or Skip any time.",
        "navigate_to": None,
    },
    {
        "widget_attr": None,
        "title": "Reading in PDF / Word / Browser",
        "body": "Select text in any app, then press Ctrl+R.\nThe overlay pill highlights each word as it's spoken.",
        "navigate_to": 0,
        "tab": 0,
        "get_started": True,   # ← triggers interactive training
    },
    {
        "widget_attr": "_overlay_text_view",
        "title": "Overlay Tab — Live Preview",
        "body": "Shows text from your clipboard.\nWords glow yellow in the floating pill while reading.",
        "navigate_to": 0,
        "tab": 0,
    },
    {
        "widget_attr": "_text_edit",
        "title": "Read Label Tab — Type or Paste",
        "body": "Type or paste text, then click Read.\nEach word highlights as it's spoken.",
        "navigate_to": 0,
        "tab": 1,
    },
    {
        "widget_attr": "_read_btn",
        "title": "Read Button",
        "body": "Click to start. Click again to pause, once more to resume.\nRed = speaking · Orange = paused.",
        "navigate_to": 0,
        "tab": 1,
    },
    {
        "widget_attr": "_online_btn",
        "title": "Online / Offline Mode",
        "body": "Online = natural neural voices (needs internet).\nOffline = system voices, no internet needed.",
        "navigate_to": 1,
    },
    {
        "widget_attr": "_sound_input",
        "title": "Voice Selector",
        "body": "Pick your preferred voice.\nOnline mode includes US, UK, and Australian accents.",
        "navigate_to": 1,
    },
    {
        "widget_attr": "_speed_slider",
        "title": "Reading Speed",
        "body": "Drag the slider to adjust pace.\nDefault 175 is a natural reading speed.",
        "navigate_to": 1,
    },
    {
        "widget_attr": "_content_stack",
        "title": "Reading History",
        "body": "Your last 20 texts are saved here.\nDouble-click any item to reload it.",
        "navigate_to": 2,
    },
    {
        "widget_attr": "_header_logo",
        "title": "Your Profile",
        "body": "Click the avatar in the sidebar to edit your profile.\nSet a name, photo, and word-highlight colour.",
        "navigate_to": None,
    },
    {
        "widget_attr": "_content_stack",
        "title": "Ask a Question",
        "body": "Browse common questions or tap Email to reach support.",
        "navigate_to": 3,
    },
    {
        "widget_attr": "_theme_btn",
        "title": "Dark / Light Mode",
        "body": "Use the ☀/☾ button in the sidebar to switch themes.\nThe overlay and tray icon update automatically.",
        "navigate_to": None,
    },
    {
        "widget_attr": None,
        "title": "You're all set!",
        "body": "Select text anywhere → press Ctrl+R → Veaja reads it.\nEnjoy!",
        "navigate_to": None,
    },
]


# ── Training phase content ────────────────────────────────────────────────────
#
# Maps phase name → (title, body) shown inside the _DragTrainer card.
# "{n}" in the countdown title is replaced with the live count value.

_TRAIN_CONTENT: dict[str, tuple[str, str]] = {
    "countdown":      (
        "{n}",
        "Get ready to practise with the Veaja overlay pill…",
    ),
    "hold":           (
        "Hold on the overlay icon",
        "The Veaja pill is now visible on your screen.\n"
        "Click and hold it, then drag it anywhere.",
    ),
    "drag":           (
        "Move it anywhere!",
        "Release the mouse when you are done.",
    ),
    "drag_done":      (
        "Great  ✓",
        "Preparing next step…",
    ),
    "ctrl_r":         (
        "Select text  →  press Ctrl + R",
        "Go to any window, select some text, then press Ctrl+R.\n\n"
        "Haven't tried yet? A demo will play in 8 seconds…",
    ),
    "ctrl_r_reading": (
        "Select text  →  press Ctrl + R",
        "Veaja is reading — watch the overlay pill highlight each word!",
    ),
    "move":           (
        "Hold the overlay and move it",
        "Drag the Veaja pill to a new spot anywhere on your screen.",
    ),
    "moving":         (
        "Keep going!",
        "Release when you are happy with the new position.",
    ),
    "right_click":    (
        "Right-click on the overlay icon",
        "Right-click the Veaja pill to see quick options:\n"
        "Hide overlay   •   Go to settings",
    ),
    "done":           (
        "Done  ✓",
        "You know how to use the Veaja overlay.\n"
        "Returning to the tutorial…",
    ),
}

# Step badge text shown at the top of the training card (e.g. "Step 1 / 4")
_STEP_BADGES: dict[str, str] = {
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

# Demo sentence spoken automatically during the Ctrl+R training phase.
# Played when the user does not press Ctrl+R within the waiting window,
# or when _auto_read() is triggered by the timeout.
_DEMO_TEXT = (
    "Hello! This is Veaja reading your selected text aloud. "
    "Just select any text in any window and press Ctrl R — "
    "Veaja will read it instantly."
)

# How long (ms) to wait for the user to try Ctrl+R before auto-demoing.
# 8 seconds gives them enough time to read the instructions and attempt it.
_CTRL_R_WAIT_MS  = 8_000
# Safety fallback — advance past the step even if TTS hangs
_CTRL_R_TOTAL_MS = 18_000


# ─────────────────────────────────────────────────────────────────────────────
# _DragTrainer — standalone interactive training card
# ─────────────────────────────────────────────────────────────────────────────

class _DragTrainer(QWidget):
    """
    Floating, always-on-top instruction card for the interactive training.

    Why standalone (parent=None)?
    ------------------------------
    Veaja's WindowManager hides MainWindow whenever the overlay pill appears
    on screen (this rule cannot be broken).  If _DragTrainer were a child of
    MainWindow or TourOverlay it would also disappear.  By having no parent
    and setting WindowStaysOnTopHint it remains visible above *any* full-screen
    application while the user interacts with the real overlay pill.

    Training phases (state machine)
    --------------------------------
      countdown → hold → drag → drag_done
               → ctrl_r → ctrl_r_reading
               → move → moving
               → right_click → done → (calls on_done)

    Drag detection
    --------------
    A 50 ms polling timer reads QApplication.mouseButtons() and the overlay
    pill's position.  This works without modifying OverlayWidget at all.

    Right-click interception
    ------------------------
    An event filter is installed on the overlay widget.  When a right-click
    is detected the filter shows a demo context menu, then advances to "done".
    """

    def __init__(
        self,
        main_window:    QWidget,
        overlay_widget: QWidget | None = None,
        speak_callback                 = None,
        on_done                        = None,
    ):
        """
        Parameters
        ----------
        main_window:    Reference to MainWindow — used for theme detection and
                        to restore the window after training finishes.
        overlay_widget: The real Veaja overlay pill (OverlayWidget instance).
        speak_callback: Callable(text: str) that triggers TTS playback.
        on_done:        Called with no arguments when training completes.
                        Typically shows the main window and advances the tour.
        """
        super().__init__(None)   # None parent → standalone top-level window

        self._main    = main_window
        self._ow      = overlay_widget      # overlay pill reference
        self._speak   = speak_callback
        self._on_done = on_done

        # Phase state machine
        self._phase      = "countdown"
        self._count      = 3                # countdown starting value
        self._poll_start = QPoint(0, 0)     # overlay position at phase start
        self._ow_was_vis = False            # whether pill was visible before training

        # Window flags — no frame, always on top, Tool hides from taskbar
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        # Transparent background so we can draw our own rounded card
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Don't steal keyboard focus when shown
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._build_ui()

        # Countdown timer — fires every 1 s during "countdown" phase
        self._cd_timer = QTimer(self)
        self._cd_timer.timeout.connect(self._tick)

        # Polling timer — fires every 50 ms to detect overlay drag movement
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_fn)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Build the card layout: step badge → title → body → exit button."""
        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 20, 26, 22)
        lay.setSpacing(0)

        # Step badge (e.g. "Step 1 / 4  —  Drag the pill")
        self._badge = QLabel()
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_font = QFont()
        badge_font.setPointSize(9)
        self._badge.setFont(badge_font)
        lay.addWidget(self._badge)
        lay.addSpacing(10)

        # Large title (e.g. "Move it anywhere!")
        self._lbl_title = QLabel()
        self._lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_title.setWordWrap(True)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setWeight(QFont.Weight.Bold)
        self._lbl_title.setFont(title_font)
        lay.addWidget(self._lbl_title)
        lay.addSpacing(10)

        # Instructional body text
        self._lbl_body = QLabel()
        self._lbl_body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_body.setWordWrap(True)
        body_font = QFont()
        body_font.setPointSize(11)
        self._lbl_body.setFont(body_font)
        lay.addWidget(self._lbl_body)
        lay.addSpacing(18)

        # Exit button — lets user bail out at any point
        self._exit_btn = QPushButton("Exit training")
        self._exit_btn.setFixedHeight(32)
        self._exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._exit_btn.clicked.connect(self._exit)
        lay.addWidget(self._exit_btn)

        self.setFixedWidth(390)

    def _apply_theme(self) -> None:
        """Apply dark / light colour scheme to all labels and the exit button."""
        is_dark = getattr(self._main, "_dark", True)

        text_colour  = "#e5e5e8" if is_dark else "#111115"
        sub_colour   = "#8888a0" if is_dark else "#55555e"
        badge_colour = "#6060b0" if is_dark else "#7070b8"
        exit_fg      = "#777777"
        exit_border  = "#555555" if is_dark else "#bbbbbb"

        self._lbl_title.setStyleSheet(
            f"color:{text_colour}; background:transparent;"
        )
        self._lbl_body.setStyleSheet(
            f"color:{sub_colour}; background:transparent;"
        )
        self._badge.setStyleSheet(
            f"color:{badge_colour}; background:transparent;"
        )
        self._exit_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background:transparent; color:{exit_fg};"
            f"  border:1px solid {exit_border}; border-radius:6px;"
            f"  font-size:12px;"
            f"}}"
            f"QPushButton:hover {{ color:#aaaaaa; border-color:#999999; }}"
        )

    def _refresh(self) -> None:
        """Reapply theme and update all labels for the current phase."""
        self._apply_theme()

        title, body = _TRAIN_CONTENT.get(self._phase, ("", ""))

        # Substitute the live countdown value into the title placeholder
        if self._phase == "countdown":
            title = title.format(n=self._count)

        self._badge.setText(_STEP_BADGES.get(self._phase, ""))
        self._lbl_title.setText(title)
        self._lbl_body.setText(body)
        self.adjustSize()

    # ── Entry point ───────────────────────────────────────────────────────────

    def show_and_start(self) -> None:
        """
        Show the real overlay pill, position this card on screen, then start
        the 3-second countdown.

        Called by TourOverlay when the user clicks "▶ Get Started".
        """
        ow = self._ow

        if ow:
            # Remember whether the pill was already visible so we can restore
            # its state correctly when training finishes
            self._ow_was_vis = ow.isVisible()

            if not ow.isVisible():
                # Place the pill near the top-centre of the primary screen
                screen = QApplication.primaryScreen()
                if screen:
                    sg = screen.availableGeometry()
                    try:
                        ow.show_near(sg.center().x(), sg.top() + 120)
                    except Exception:
                        # Fallback if show_near is not available
                        try:
                            ow.show_overlay()
                        except Exception:
                            pass

            # Record the pill's starting position for drag detection
            self._poll_start = ow.pos()

        # Place the training card at the bottom-centre of the screen
        screen = QApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            self.adjustSize()
            self.move(
                sg.center().x() - self.width() // 2,
                sg.bottom() - self.height() - 70,
            )

        # Reset state and begin countdown
        self._phase = "countdown"
        self._count = 3
        self._refresh()
        self.show()
        self.raise_()
        self._cd_timer.start(1000)   # fires every 1 second

    # ── Countdown ─────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        """Decrement the countdown by 1 each second; advance to "hold" at 0."""
        self._count -= 1
        if self._count <= 0:
            self._cd_timer.stop()
            self._go("hold")
        else:
            self._refresh()

    # ── Phase state machine ───────────────────────────────────────────────────

    def _go(self, phase: str) -> None:
        """
        Transition to a new training phase.

        Stops any running timers, updates the UI, then sets up whatever
        listener or timer the new phase needs (polling, event filter, etc.).
        """
        self._phase = phase
        self._cd_timer.stop()
        self._poll_timer.stop()
        self._refresh()

        if phase == "hold":
            # Start polling for the first drag gesture on the overlay pill
            if self._ow:
                self._poll_start = self._ow.pos()
                self._poll_timer.start(50)   # 50 ms resolution

        elif phase == "drag_done":
            # Brief pause before moving to the Ctrl+R instruction
            QTimer.singleShot(
                1500,
                lambda: self._go("ctrl_r") if self._phase == "drag_done" else None,
            )

        elif phase == "ctrl_r":
            # Give the user _CTRL_R_WAIT_MS to try pressing Ctrl+R themselves.
            # If they don't, _auto_read() plays the demo sentence so they can
            # still see word-highlighting even if they skipped the real gesture.
            # The safety fallback at _CTRL_R_TOTAL_MS advances the tour even if
            # TTS is slow or offline, so training never gets stuck here.
            QTimer.singleShot(_CTRL_R_WAIT_MS, self._auto_read)
            QTimer.singleShot(
                _CTRL_R_TOTAL_MS,
                lambda: self._go("move")
                if self._phase in ("ctrl_r", "ctrl_r_reading") else None,
            )

        elif phase == "move":
            if self._ow:
                # Reset poll baseline so we detect movement from the new position
                self._poll_start = self._ow.pos()
                self._poll_timer.start(50)
            else:
                # No overlay available — skip after 5 s
                QTimer.singleShot(
                    5000,
                    lambda: self._go("right_click") if self._phase == "move" else None,
                )

        elif phase == "right_click":
            if self._ow:
                # Install our event filter to intercept the right-click
                self._ow.installEventFilter(self)
            else:
                # No overlay — advance automatically after 4 s
                QTimer.singleShot(
                    4000,
                    lambda: self._go("done") if self._phase == "right_click" else None,
                )

        elif phase == "done":
            # Show "Done ✓" briefly before calling the completion callback
            QTimer.singleShot(
                2000,
                lambda: self._finish() if self._phase == "done" else None,
            )

    # ── Drag detection (50 ms poll) ───────────────────────────────────────────

    def _poll_fn(self) -> None:
        """
        Poll the overlay pill's position and mouse button state every 50 ms.

        Phase transitions:
          hold / drag  : pill moved + mouse held   → "drag"
                         pill moved + mouse released → "drag_done"
          move / moving: same pattern              → "right_click"
        """
        ow = self._ow
        if not ow:
            return

        delta      = ow.pos() - self._poll_start
        moved      = abs(delta.x()) > 15 or abs(delta.y()) > 15
        mouse_down = bool(QApplication.mouseButtons() & Qt.MouseButton.LeftButton)

        if self._phase in ("hold", "drag"):
            if moved and mouse_down:
                # User is actively dragging — update title to "Move it anywhere!"
                self._phase = "drag"
                self._refresh()
            elif moved and not mouse_down:
                # Drag completed — advance to confirmation phase
                self._poll_timer.stop()
                self._go("drag_done")

        elif self._phase in ("move", "moving"):
            if moved and mouse_down:
                self._phase = "moving"
                self._refresh()
            elif moved and not mouse_down:
                self._poll_timer.stop()
                self._go("right_click")

    # ── Ctrl+R demo read ──────────────────────────────────────────────────────

    def _auto_read(self) -> None:
        """
        Automatically speak the demo sentence to show word highlighting.
        Only runs if still in the "ctrl_r" phase (guard against double-advance).
        """
        if self._phase != "ctrl_r":
            return

        self._phase = "ctrl_r_reading"
        self._refresh()

        if self._speak:
            try:
                self._speak(_DEMO_TEXT)
            except Exception:
                pass   # Never crash the tutorial on a TTS error

    # ── Right-click interception ──────────────────────────────────────────────

    def eventFilter(self, obj, event) -> bool:
        """
        Intercept right-clicks on the overlay pill during the "right_click" phase.

        Returns True (consuming the event) so the pill's own context menu does
        not open before we show our tutorial menu.
        """
        if (
            obj is self._ow
            and self._phase == "right_click"
            and event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.RightButton
        ):
            self._ow.removeEventFilter(self)   # one-shot interception
            pos = event.globalPosition().toPoint()
            # Defer via singleShot so we're safely outside the event filter
            QTimer.singleShot(0, lambda: self._show_menu(pos))
            return True   # consume — suppress pill's own handler

        return super().eventFilter(obj, event)

    def _show_menu(self, pos: QPoint) -> None:
        """
        Show the demo right-click context menu.
        QMenu.exec() is blocking; phase advances after it returns regardless
        of which option (if any) the user chooses.
        """
        menu = QMenu()
        menu.setStyleSheet(
            "QMenu {"
            "  background:#1e1e22; border:1px solid #3a3a42;"
            "  border-radius:8px; color:#e0e0e0; font-size:13px; padding:4px;"
            "}"
            "QMenu::item { padding:8px 22px; border-radius:6px; }"
            "QMenu::item:selected { background:#0A84FF; color:#ffffff; }"
        )
        menu.addAction("🔲   Hide overlay")
        menu.addAction("⚙   Go to settings")
        menu.exec(pos)   # blocking — returns when user clicks or dismisses

        # Advance to "done" regardless of which option was selected
        if self._phase == "right_click":
            self._go("done")

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def _exit(self) -> None:
        """Exit button handler — abort training and restore the main window."""
        self._finish()

    def _finish(self) -> None:
        """
        Clean up timers and event filters, optionally hide the overlay pill
        if it was not visible before training started, then close this window
        and call on_done() to restore the main window and continue the tour.
        """
        self._cd_timer.stop()
        self._poll_timer.stop()

        ow = self._ow
        if ow:
            # Always remove our event filter — safe to call even if not installed
            try:
                ow.removeEventFilter(self)
            except Exception:
                pass
            # Restore pill visibility to its pre-training state
            if not self._ow_was_vis:
                try:
                    ow.hide_overlay()
                except Exception:
                    pass

        self.close()

        # Restore the main window and continue the tour
        if self._on_done:
            self._on_done()

    # ── Custom paint — rounded card background ────────────────────────────────

    def paintEvent(self, _event) -> None:
        """Draw the frosted-glass rounded card background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        is_dark = getattr(self._main, "_dark", True)
        bg_colour     = QColor(20,  20,  24,  246) if is_dark else QColor(248, 248, 252, 246)
        border_colour = QColor(55,  55,  65,  200) if is_dark else QColor(195, 195, 205, 200)

        painter.setBrush(QBrush(bg_colour))
        painter.setPen(QPen(border_colour, 1.0))
        painter.drawRoundedRect(
            QRectF(0.5, 0.5, self.width() - 1, self.height() - 1),
            14, 14,
        )
        painter.end()


# ─────────────────────────────────────────────────────────────────────────────
# _Bubble — tutorial navigation card
# ─────────────────────────────────────────────────────────────────────────────

class _Bubble(QWidget):
    """
    Rounded floating card shown inside TourOverlay.

    Contains:
      • Step counter  (e.g. "3 / 13")
      • Title         (bold, accent colour)
      • Body          (descriptive text with rich-text Ctrl+X badges)
      • Navigation    ← Back  |  ▶ Get Started  |  Next →  |  Skip
      • Progress bar  (thin stripe at the bottom of the card)

    The "▶ Get Started" button is hidden on most steps and only revealed
    on steps that have ``get_started: True`` in the STEPS list.
    """

    _CARD_WIDTH = 400   # fixed pixel width of the bubble card

    def __init__(self, on_prev, on_next, on_skip, on_get_started, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Widget)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setFixedWidth(self._CARD_WIDTH)

        self._total   = 1   # total number of steps (for progress bar)
        self._current = 0   # current step index

        self._build_ui(on_prev, on_next, on_skip, on_get_started)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self, on_prev, on_next, on_skip, on_get_started) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 22, 28, 32)
        lay.setSpacing(0)

        # Step counter — top right corner
        self._step_label = QLabel()
        self._step_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        counter_font = QFont()
        counter_font.setPointSize(9)
        self._step_label.setFont(counter_font)
        lay.addWidget(self._step_label)
        lay.addSpacing(10)

        # Step title
        self._title = QLabel()
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setWeight(QFont.Weight.Bold)
        self._title.setFont(title_font)
        self._title.setWordWrap(True)
        lay.addWidget(self._title)
        lay.addSpacing(10)

        # Step body — rich text so we can render keyboard badge spans
        self._body = QLabel()
        body_font = QFont()
        body_font.setPointSize(11)
        self._body.setFont(body_font)
        self._body.setWordWrap(True)
        self._body.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(self._body)
        lay.addSpacing(22)

        # Navigation button row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.setContentsMargins(0, 0, 0, 0)

        self._prev_btn = QPushButton("← Back")
        self._prev_btn.setFixedHeight(36)
        self._prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._prev_btn.clicked.connect(on_prev)

        # "Get Started" — hidden by default; visible on training step only
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

    # ── Content ───────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt(text: str) -> str:
        """
        Convert plain body text to HTML for display in a QLabel.

        Transformations applied:
          • HTML-escape special characters
          • Wrap "Ctrl+X" patterns in a monospace keyboard-badge <span>
          • Convert \\n\\n → <br><br> and \\n → <br>
          • Wrap in a <span> with line-height for breathing room
        """
        escaped = _html.escape(text)

        # Render keyboard shortcuts as inline code badges
        escaped = _re.sub(
            r"(Ctrl\+\w+)",
            r'<span style="background:rgba(128,128,128,0.18);'
            r"border-radius:3px;padding:0 4px;"
            r'font-family:monospace;font-size:10px;">\1</span>',
            escaped,
        )

        escaped = escaped.replace("\n\n", "<br><br>").replace("\n", "<br>")
        return f'<span style="line-height:1.6;">{escaped}</span>'

    def update_content(
        self,
        step_idx:         int,
        total:            int,
        title:            str,
        body:             str,
        show_get_started: bool = False,
    ) -> None:
        """
        Populate the bubble with the content for the given step.

        Parameters
        ----------
        step_idx:         Zero-based index of the current step.
        total:            Total number of steps (used for progress bar).
        title:            Step heading text.
        body:             Step body text (supports \\n line breaks).
        show_get_started: Whether to show the green "▶ Get Started" button.
        """
        self._total   = total
        self._current = step_idx

        self._step_label.setText(f"{step_idx + 1} / {total}")
        self._title.setText(title)
        self._body.setText(self._fmt(body))

        # Disable Back on the first step; change Next to "Done" on the last
        self._prev_btn.setEnabled(step_idx > 0)
        self._next_btn.setText("Done" if step_idx == total - 1 else "Next →")

        # Show or hide the interactive training button
        self._gs_btn.setVisible(show_get_started)

        self.adjustSize()
        self.update()   # trigger repaint for progress bar

    # ── Custom paint — card + progress bar ───────────────────────────────────

    def paintEvent(self, _event) -> None:
        """Draw the frosted card background and the thin progress bar at the bottom."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Detect theme from the parent TourOverlay → MainWindow
        try:
            is_dark = self.parent()._main._dark
        except AttributeError:
            is_dark = (
                self.palette().color(self.backgroundRole()).lightness() < 128
            )

        if is_dark:
            bg     = QColor(26, 26, 28, 191)
            text_c = QColor(255, 255, 255)
            sub_c  = QColor(200, 200, 205)
            border = QColor(58, 58, 63, 80)
            trk_c  = QColor(58, 58, 63)
            fill_c = QColor(10, 132, 255)
        else:
            bg     = QColor(255, 255, 255, 191)
            text_c = QColor(20, 20, 25)
            sub_c  = QColor(60, 60, 70)
            border = QColor(210, 210, 215, 80)
            trk_c  = QColor(218, 218, 223)
            fill_c = QColor(10, 132, 255)

        # Apply colours to text labels (done here so they react to theme changes)
        self._title.setStyleSheet(
            f"color:{text_c.name()}; background:transparent;"
        )
        self._body.setStyleSheet(
            f"color:{sub_c.name()}; background:transparent;"
        )
        self._step_label.setStyleSheet(
            f"color:{sub_c.name()}; background:transparent;"
        )

        # Draw the rounded card background
        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(border, 1.0))
        painter.drawRoundedRect(
            QRectF(0.5, 0.5, self.width() - 1, self.height() - 1),
            16, 16,
        )

        # Draw the thin progress bar at the very bottom of the card
        if self._total > 1:
            bar_height = 3
            margin     = 28
            bar_y      = self.height() - 14
            track_w    = self.width() - margin * 2
            fill_w     = int(track_w * (self._current + 1) / self._total)

            painter.setPen(Qt.PenStyle.NoPen)

            # Grey track (full width)
            painter.setBrush(QBrush(trk_c))
            painter.drawRoundedRect(
                QRectF(margin, bar_y, track_w, bar_height), 1.5, 1.5
            )

            # Blue fill (proportional to progress)
            if fill_w > 0:
                painter.setBrush(QBrush(fill_c))
                painter.drawRoundedRect(
                    QRectF(margin, bar_y, fill_w, bar_height), 1.5, 1.5
                )

        painter.setPen(Qt.PenStyle.NoPen)


# ─────────────────────────────────────────────────────────────────────────────
# TourOverlay — main tutorial overlay widget
# ─────────────────────────────────────────────────────────────────────────────

class TourOverlay(QWidget):
    """
    Full-window semi-transparent overlay drawn as a child of MainWindow.

    Responsibilities
    ----------------
    • Dim the main window with a translucent black overlay
    • Draw a blue spotlight border around the current step's target widget
    • Show and position the _Bubble navigation card
    • Navigate MainWindow to the correct page/tab for each step
    • Launch _DragTrainer when the user clicks "▶ Get Started"

    Interaction with _DragTrainer
    ------------------------------
    When "Get Started" is clicked, a standalone _DragTrainer window is
    created and shown.  Both the overlay pill and the trainer card float
    above all apps independently.  When training finishes, the on_done()
    callback restores this overlay and the main window.
    """

    def __init__(
        self,
        main_window:    QWidget,
        overlay_widget: QWidget | None = None,
        speak_callback                 = None,
    ):
        """
        Parameters
        ----------
        main_window:    The MainWindow instance (parent widget).
        overlay_widget: The real Veaja overlay pill, passed to _DragTrainer.
        speak_callback: TTS callable passed to _DragTrainer for the demo read.
        """
        super().__init__(main_window)

        self._main           = main_window
        self._overlay_widget = overlay_widget
        self._speak_callback = speak_callback
        self._step           = 0
        self._steps          = STEPS
        self._trainer: _DragTrainer | None = None   # keeps trainer alive (no GC)

        # Transparent background — we draw the dim manually in paintEvent
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.resize(main_window.size())

        # Build the navigation bubble
        self._bubble = _Bubble(
            on_prev=self._prev,
            on_next=self._next,
            on_skip=self.close,
            on_get_started=self._on_get_started,
            parent=self,
        )

        self._style_buttons()

        # Track MainWindow resize so we stay full-window
        self._main.installEventFilter(self)

        # Show the first step immediately
        self._go_to(0)

    # ── Step navigation ───────────────────────────────────────────────────────

    def _prev(self) -> None:
        """Navigate to the previous step."""
        if self._step > 0:
            self._go_to(self._step - 1)

    def _next(self) -> None:
        """Navigate to the next step, or close the tour on the last step."""
        if self._step < len(self._steps) - 1:
            self._go_to(self._step + 1)
        else:
            self.close()

    def _go_to(self, idx: int) -> None:
        """
        Jump to step ``idx``.

        Side effects:
          • Navigates MainWindow to the correct page / tab
          • Scrolls the target widget into view (Settings page)
          • Updates the bubble content and spotlight
        """
        self._step = idx
        step = self._steps[idx]

        # Switch the main window to the relevant page
        nav = step.get("navigate_to")
        if nav is not None and hasattr(self._main, "navigate_if_needed"):
            self._main.navigate_if_needed(nav, tab=step.get("tab"))

        # Scroll the target widget into view if it lives in a scroll area
        widget_attr = step.get("widget_attr")
        if widget_attr:
            target = getattr(self._main, widget_attr, None)
            if target and hasattr(self._main, "_settings_scroll"):
                self._main._settings_scroll.ensureWidgetVisible(target, 40, 60)

        # Populate the bubble card
        self._bubble.update_content(
            idx,
            len(self._steps),
            step["title"],
            step["body"],
            show_get_started=bool(step.get("get_started", False)),
        )

        self._position_bubble(widget_attr)
        self.update()   # repaint spotlight

    # ── "Get Started" — launch interactive training ───────────────────────────

    def _on_get_started(self) -> None:
        """
        Spawn the standalone _DragTrainer window alongside the overlay pill.

        Both windows float above all full-screen apps because:
          • Overlay pill  — OverlayWidget uses WindowStaysOnTopHint
          • _DragTrainer  — standalone window (no parent) + WindowStaysOnTopHint

        The on_done closure is captured with the current step index so the
        tour resumes at exactly the right place after training finishes.
        """
        step = self._step   # capture for closure — avoids capturing self._step

        def on_done() -> None:
            """Called by _DragTrainer after training completes or is exited."""
            # Restore the main window (hidden by the WindowManager overlay rule)
            self._main.show()
            self._main.activateWindow()
            self._main.raise_()
            # Restore and re-position this overlay
            self.show()
            self.raise_()
            self._go_to(step)

        # Store reference in self so Python's GC doesn't destroy the window
        self._trainer = _DragTrainer(
            main_window=self._main,
            overlay_widget=self._overlay_widget,
            speak_callback=self._speak_callback,
            on_done=on_done,
        )
        self._trainer.show_and_start()

    # ── Spotlight geometry ────────────────────────────────────────────────────

    def _target_rect(self, widget_attr: str | None) -> QRect | None:
        """
        Return the spotlight rectangle for the given widget attribute name,
        in local (overlay) coordinates, with 10/8 px padding.

        Returns None if the attribute is absent, invisible, or not specified.
        """
        if not widget_attr:
            return None

        target: QWidget | None = getattr(self._main, widget_attr, None)
        if target is None or not target.isVisibleTo(self._main):
            return None

        # Map widget's top-left corner from global → overlay-local coordinates
        global_pos = target.mapToGlobal(QPoint(0, 0))
        local_pos  = self.mapFromGlobal(global_pos)
        return QRect(local_pos, target.size()).adjusted(-10, -8, 10, 8)

    def _position_bubble(self, widget_attr: str | None) -> None:
        """
        Place the bubble card relative to the spotlight rect.

        Placement priority:
          1. Below the spotlight (with 16 px gap)
          2. Above the spotlight if it would overflow the bottom
          3. Centred horizontally, clamped to the overlay bounds
          4. Screen-centred if there is no spotlight (widget_attr is None)
        """
        self._bubble.adjustSize()
        bw, bh = self._bubble.width(), self._bubble.height()
        ow, oh = self.width(), self.height()
        spot   = self._target_rect(widget_attr)

        if spot is None:
            # No target — centre the card on the overlay
            x = (ow - bw) // 2
            y = (oh - bh) // 2
        else:
            gap = 16
            x   = spot.left()
            y   = spot.bottom() + gap

            # Flip above if it would bleed off the bottom edge
            if y + bh > oh - 20:
                y = spot.top() - bh - gap

            # Last resort: force below if above also doesn't fit
            if y < 20:
                y = spot.bottom() + gap

            # Clamp horizontally and vertically within the overlay
            x = max(12, min(x, ow - bw - 12))
            y = max(12, min(y, oh - bh - 12))

        self._bubble.move(x, y)

    # ── Paint — dim + spotlight border ───────────────────────────────────────

    def paintEvent(self, _event) -> None:
        """
        Draw the semi-transparent black dim over the entire window.
        If the current step has a target widget, draw a blue border around it
        (no hole-punching — avoids black-on-dark-mode artefacts).
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Dim the entire main window
        painter.fillRect(self.rect(), QColor(0, 0, 0, 150))

        # Blue spotlight border around the current target widget
        spot = self._target_rect(self._steps[self._step].get("widget_attr"))
        if spot is not None:
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver
            )
            painter.setPen(QPen(QColor(10, 132, 255, 220), 2.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(spot), 10, 10)

    # ── Events ────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        """Block clicks on the dim area; pass through clicks on the bubble."""
        if not self._bubble.geometry().contains(event.position().toPoint()):
            event.accept()   # swallow — prevent user clicking behind the overlay
        else:
            super().mousePressEvent(event)

    def eventFilter(self, obj, event) -> bool:
        """Resize the overlay to match the main window whenever it resizes."""
        if obj is self._main and event.type() == QEvent.Type.Resize:
            self.resize(self._main.size())
            self._position_bubble(self._steps[self._step].get("widget_attr"))
        return super().eventFilter(obj, event)

    def closeEvent(self, event) -> None:
        """Clean up: remove the resize event filter and close any open trainer."""
        self._main.removeEventFilter(self)
        if self._trainer:
            self._trainer.close()
            self._trainer = None
        super().closeEvent(event)

    def showEvent(self, event) -> None:
        """Ensure the overlay fills the main window and stays on top."""
        super().showEvent(event)
        self.resize(self._main.size())
        self.raise_()

    # ── Button styles ─────────────────────────────────────────────────────────

    def _style_buttons(self) -> None:
        """Apply shared and per-button stylesheets to the bubble's buttons."""
        base = (
            "QPushButton {"
            "  border-radius:8px; font-size:13px;"
            "  padding:0 16px; font-weight:500;"
            "}"
        )

        # Primary action — solid blue "Next →" / "Done"
        self._bubble._next_btn.setStyleSheet(
            base
            + "QPushButton { background:#0A84FF; color:#ffffff; border:none; }"
            + "QPushButton:hover { background:#2A9AFF; }"
        )

        # Secondary action — outlined blue "← Back"
        self._bubble._prev_btn.setStyleSheet(
            base
            + "QPushButton {"
            "  background:transparent; color:#0A84FF;"
            "  border:1.5px solid #0A84FF;"
            "}"
            + "QPushButton:hover { background:rgba(10,132,255,0.10); }"
            + "QPushButton:disabled { color:#aaaaaa; border-color:#aaaaaa; }"
        )

        # Tertiary action — ghost "Skip"
        self._bubble._skip_btn.setStyleSheet(
            base
            + "QPushButton { background:transparent; color:#999999; border:none; }"
            + "QPushButton:hover { color:#555555; }"
        )

        # Interactive training — solid green "▶ Get Started"
        self._bubble._gs_btn.setStyleSheet(
            base
            + "QPushButton { background:#34C759; color:#ffffff; border:none; }"
            + "QPushButton:hover { background:#2EB350; }"
        )

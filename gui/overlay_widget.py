"""
Veaja floating overlay widget.

Behaviour:
  • Appears as a small circle (80 px) showing the Veaja logo.
  • On mouse-enter (hover / "drag on"):  text label slides in → pill shape.
  • On mouse-leave:                       text label slides out → circle.
  • Single click anywhere:               read text via TTS.
  • Drag (hold + move):                  reposition on screen.
  • Right-click:                         context menu (hide, settings).
"""

import os
import ctypes
import platform
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QSizePolicy, QApplication, QMenu, QPushButton
)
from PyQt6.QtCore import (
    Qt, QPoint, QRectF, QVariantAnimation,
    QEasingCurve, pyqtSignal, QTimer
)
from PyQt6.QtGui import (
    QPainter, QPainterPath, QColor, QPen, QBrush,
    QFont, QCursor, QPalette, QAction, QPixmap
)


# ══════════════════════════════════════════════════════════════════════════════
# macOS: force overlay above ALL other app windows
# ══════════════════════════════════════════════════════════════════════════════

def _mac_float_above_all(widget: QWidget):
    """
    Push the overlay above every other app window on macOS, regardless of
    which app is currently active.

    Key changes vs. previous version:
      • Level 101 (NSPopUpMenuWindowLevel) — same tier as dropdown menus,
        reliably above all normal app windows even when they are active.
        Level 25 (NSStatusWindowLevel) was NOT high enough; active apps
        could still cover the overlay.
      • orderFrontRegardless — called immediately (no timer delay) so the
        window is front BEFORE the calling app finishes becoming active.
    """
    if platform.system() != "Darwin":
        return
    try:
        objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
        objc.objc_msgSend.restype = ctypes.c_void_p

        ns_view = ctypes.c_void_p(int(widget.winId()))

        # step 0: get NSWindow from NSView
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        sel_window = ctypes.c_void_p(objc.sel_registerName(b"window"))
        ns_window = ctypes.c_void_p(objc.objc_msgSend(ns_view, sel_window))
        if not ns_window.value:
            return  # native window not ready yet — showEvent will retry

        # step 1: setLevel: 101 (NSPopUpMenuWindowLevel)
        # This is the critical fix — 25 (NSStatusWindowLevel) loses to
        # active app windows. 101 stays above them reliably.
        sel_setLevel = ctypes.c_void_p(objc.sel_registerName(b"setLevel:"))
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long]
        objc.objc_msgSend(ns_window, sel_setLevel, 101)

        # step 2: setCollectionBehavior
        # CanJoinAllSpaces    = 1   — visible on every desktop Space
        # FullScreenAuxiliary = 256 — floats above full-screen apps too
        sel_setCB = ctypes.c_void_p(
            objc.sel_registerName(b"setCollectionBehavior:")
        )
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
        objc.objc_msgSend(ns_window, sel_setCB, 1 | 256)

        # step 3: orderFrontRegardless — move to front NOW, even if
        # Veaja is not the active application.
        sel_front = ctypes.c_void_p(
            objc.sel_registerName(b"orderFrontRegardless")
        )
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        objc.objc_msgSend(ns_window, sel_front)

    except Exception as exc:
        print(f"[Veaja] Mac window-level warning: {exc}")


ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")

# Geometry constants
LOGO_SIZE   = 72
PADDING     = 8
CIRCLE_SIZE = LOGO_SIZE + PADDING * 2           # 88 px — collapsed width/height
TEXT_WIDTH  = 240                               # extra width when expanded
PILL_HEIGHT = CIRCLE_SIZE                       # height stays constant
PILL_WIDTH  = CIRCLE_SIZE + TEXT_WIDTH + PADDING  # expanded width
ANIM_MS     = 220                               # animation duration ms
DRAG_PX     = 6                                 # drag-detection threshold

# How often (ms) to re-assert the window level while the overlay is visible.
# This catches edge cases where macOS re-orders windows after focus changes.
_KEEP_FRONT_INTERVAL_MS = 500


def _is_dark_mode() -> bool:
    app = QApplication.instance()
    if app is None:
        return False
    return app.palette().color(QPalette.ColorRole.Window).lightness() < 128


# ══════════════════════════════════════════════════════════════════════════════
# Circular logo widget
# ══════════════════════════════════════════════════════════════════════════════

class _LogoCircle(QWidget):
    """Renders the Veaja logo (or user avatar) clipped to a circle."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(LOGO_SIZE, LOGO_SIZE)
        self._pixmap: QPixmap | None = None
        self._custom_path: str | None = None   # user avatar path when set
        self._load_png()
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    # ── Load helpers ──────────────────────────────────────────────────────────

    def _load_png(self, dark: bool | None = None):
        """Load bundled Veaja logo (dark/light variant)."""
        if dark is None:
            dark = _is_dark_mode()
        name = "logo_light.png" if dark else "logo_dark.png"
        path = os.path.join(ASSETS, name)
        self._set_pixmap_from_path(path)

    def _set_pixmap_from_path(self, path: str):
        if os.path.exists(path):
            raw = QPixmap(path)
            self._pixmap = raw.scaled(
                LOGO_SIZE, LOGO_SIZE,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            self._pixmap = None
        self.update()

    # ── Public API ────────────────────────────────────────────────────────────

    def load_custom(self, path: str):
        """Switch to user's custom avatar image."""
        self._custom_path = path
        self._set_pixmap_from_path(path)

    def reset_to_default(self, dark: bool | None = None):
        """Switch back to bundled Veaja logo."""
        self._custom_path = None
        self._load_png(dark)

    def reload_for_theme(self, dark: bool):
        if self._custom_path:
            pass   # custom avatar doesn't change with theme
        else:
            self._load_png(dark)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Circular clip
        clip = QPainterPath()
        clip.addEllipse(QRectF(0, 0, LOGO_SIZE, LOGO_SIZE))
        painter.setClipPath(clip)

        if self._pixmap and not self._pixmap.isNull():
            # Centre the pixmap inside the circle
            x = (LOGO_SIZE - self._pixmap.width())  // 2
            y = (LOGO_SIZE - self._pixmap.height()) // 2
            painter.drawPixmap(x, y, self._pixmap)
        else:
            # Fallback: red circle with "V"
            painter.setClipping(False)
            accent = QColor(229, 57, 53)
            painter.setBrush(QBrush(accent))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(0, 0, LOGO_SIZE, LOGO_SIZE)
            font = QFont("Arial", 28, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(QRectF(0, 0, LOGO_SIZE, LOGO_SIZE),
                             Qt.AlignmentFlag.AlignCenter, "V")
            return

        # Thin ring border — use parent's stored _dark if available
        painter.setClipping(False)
        try:
            dark = self.parent()._dark
        except AttributeError:
            dark = _is_dark_mode()
        border_color = QColor(100, 100, 100, 180) if dark else QColor(200, 200, 200, 200)
        painter.setPen(QPen(border_color, 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(1, 1, LOGO_SIZE - 2, LOGO_SIZE - 2)


# ══════════════════════════════════════════════════════════════════════════════
# Main overlay widget
# ══════════════════════════════════════════════════════════════════════════════

class OverlayWidget(QWidget):
    """
    Signals
    -------
    read_requested(str)   – user clicked to read text
    hide_requested()      – user chose to hide from context menu
    settings_requested()  – user chose settings from context menu
    """

    read_requested     = pyqtSignal(str)
    stop_requested     = pyqtSignal()        # emitted when user clicks to stop
    hide_requested     = pyqtSignal()
    settings_requested = pyqtSignal()
    overlay_shown      = pyqtSignal()
    overlay_hidden     = pyqtSignal()
    reset_requested    = pyqtSignal()        # emitted when user clicks ⟳ reset

    def __init__(self, parent=None):
        super().__init__(parent)

        # State
        self._text: str = ""
        self._speaking: bool = False
        self._processing: bool = False
        self._paused: bool = False
        self._press_pos: QPoint | None = None
        self._dragging: bool = False
        self._expanded: bool = False
        self._dot_count: int = 0
        # Dark mode stored explicitly — don't rely on per-paint detection
        # because Qt may misread Windows 11 dark mode from QPalette.
        self._dark: bool = _is_dark_mode()

        self._setup_window()
        self._build_ui()
        self._build_animations()
        self._build_keep_front_timer()
        self._build_dot_timer()
        self._position_default()

    # ------------------------------------------------------------------ #
    # Window setup
    # ------------------------------------------------------------------ #

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedHeight(PILL_HEIGHT)
        self.setFixedWidth(CIRCLE_SIZE)

    # ------------------------------------------------------------------ #
    # UI layout
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(PADDING, PADDING, PADDING, PADDING)
        outer.setSpacing(0)

        # Logo circle
        self._logo = _LogoCircle()
        outer.addWidget(self._logo)

        # Text panel (hidden until hover) — must be transparent so the
        # pill's painted background shows through in both dark and light mode.
        self._text_panel = QWidget()
        self._text_panel.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._text_panel.setStyleSheet("background: transparent;")
        self._text_panel.setFixedHeight(LOGO_SIZE)
        self._text_panel.setMaximumWidth(0)
        self._text_panel.setMinimumWidth(0)
        self._text_panel.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )

        tp_layout = QVBoxLayout(self._text_panel)
        tp_layout.setContentsMargins(12, 6, 10, 6)
        tp_layout.setSpacing(2)

        # Title row: label + spacer + reset button
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(4)

        self._title_label = QLabel("Veaja is ready")
        self._title_label.setObjectName("overlayTitle")
        font_title = QFont()
        font_title.setPointSize(10)
        font_title.setWeight(QFont.Weight.Medium)
        self._title_label.setFont(font_title)

        self._reset_btn = QPushButton("⟳")
        self._reset_btn.setObjectName("overlayResetBtn")
        self._reset_btn.setToolTip("Restart reading from beginning")
        self._reset_btn.setFixedSize(22, 22)
        self._reset_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._reset_btn.clicked.connect(self.reset_requested)
        self._reset_btn.setStyleSheet("background: transparent; border: none; font-size: 13px;")

        title_row.addWidget(self._title_label)
        title_row.addStretch()
        title_row.addWidget(self._reset_btn)

        self._body_label = QLabel("Select text to read…")
        self._body_label.setObjectName("overlayBody")
        self._body_label.setWordWrap(True)
        self._body_label.setTextFormat(Qt.TextFormat.RichText)   # needed for karaoke HTML
        font_body = QFont()
        font_body.setPointSize(9)
        self._body_label.setFont(font_body)

        tp_layout.addLayout(title_row)
        tp_layout.addWidget(self._body_label)
        tp_layout.addStretch()

        outer.addWidget(self._text_panel)
        self._update_label_colors()

    # ------------------------------------------------------------------ #
    # Animations
    # ------------------------------------------------------------------ #

    def _build_animations(self):
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(ANIM_MS)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim_value)

    def _on_anim_value(self, value: int):
        self._text_panel.setMaximumWidth(value)
        self._text_panel.setMinimumWidth(value)
        new_w = CIRCLE_SIZE + value + (PADDING if value > 0 else 0)
        self.setFixedWidth(new_w)
        self.update()

    def _expand(self):
        if self._expanded:
            return
        self._expanded = True
        self._anim.stop()
        self._anim.setStartValue(self._text_panel.maximumWidth())
        self._anim.setEndValue(TEXT_WIDTH)
        self._anim.start()

    def _collapse(self):
        if not self._expanded:
            return
        self._expanded = False
        self._anim.stop()
        self._anim.setStartValue(self._text_panel.maximumWidth())
        self._anim.setEndValue(0)
        self._anim.start()

    # ------------------------------------------------------------------ #
    # Keep-on-top timer
    # ------------------------------------------------------------------ #

    def _update_label_colors(self, dark: bool | None = None, speaking: bool = False,
                             paused: bool = False):
        """
        Explicitly set label text colours — overlay doesn't inherit from QSS.
          speaking=True → title turns RED
          paused=True   → title turns ORANGE
          otherwise     → normal colours for dark/light mode
        """
        if dark is None:
            dark = self._dark   # use stored flag, not live detection

        if speaking:
            title_color = "#FF453A" if dark else "#FF3B30"   # red
        elif paused:
            title_color = "#FF9F0A" if dark else "#FF9500"   # orange
        else:
            title_color = "#F5F5F7" if dark else "#1C1C1E"   # normal

        body_color = "#AEAEB2" if dark else "#6C6C70"

        self._title_label.setStyleSheet(
            f"color: {title_color}; background: transparent;"
        )
        self._body_label.setStyleSheet(
            f"color: {body_color}; background: transparent;"
        )
        self._reset_btn.setStyleSheet(
            f"color: {body_color}; background: transparent; border: none; font-size: 13px;"
        )

    def _build_dot_timer(self):
        """Animates '.' → '..' → '...' while processing."""
        self._dot_timer = QTimer(self)
        self._dot_timer.setInterval(450)
        self._dot_timer.timeout.connect(self._tick_dots)

    def _tick_dots(self):
        self._dot_count = (self._dot_count + 1) % 4
        dots = "." * self._dot_count
        self._title_label.setText(f"Processing{dots}")

    def _build_keep_front_timer(self):
        """
        Periodically re-assert the window level while the overlay is visible.

        macOS can re-order windows when another app becomes active.
        Calling _mac_float_above_all every 500 ms guarantees the overlay
        snaps back to the front within half a second even in edge cases.
        The timer only runs while the overlay is shown.
        """
        self._front_timer = QTimer(self)
        self._front_timer.setInterval(_KEEP_FRONT_INTERVAL_MS)
        self._front_timer.timeout.connect(lambda: _mac_float_above_all(self))

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def set_text(self, text: str, auto_show: bool = True):
        """Called by AppController when new selected text is ready."""
        self._text = text
        display = text if len(text) <= 120 else text[:117] + "…"
        self._body_label.setText(display)
        self._title_label.setText("Tap to read" if text else "Veaja is ready")
        if auto_show:
            self.show_overlay()

    def show_overlay(self):
        self.show()
        self.raise_()
        # Call immediately — do NOT delay. The 30 ms delay in the old code
        # meant the overlay was pushed to the front AFTER the other app had
        # already claimed focus, so it was immediately covered again.
        _mac_float_above_all(self)
        # One extra call after 80 ms as a safety net for the first show.
        QTimer.singleShot(80, lambda: _mac_float_above_all(self))

    def hide_overlay(self):
        self._collapse()
        QTimer.singleShot(ANIM_MS + 50, self._do_hide)

    def _do_hide(self):
        # Stop the keep-front timer so it doesn't run while hidden.
        self._front_timer.stop()
        self.hide()
        self.overlay_hidden.emit()

    # ------------------------------------------------------------------ #
    # showEvent — set Mac floating level once the native window exists
    # ------------------------------------------------------------------ #

    def showEvent(self, event):
        super().showEvent(event)
        # Defer by one event-loop tick so the NSWindow is fully initialised.
        QTimer.singleShot(0, self._on_shown)

    def _on_shown(self):
        _mac_float_above_all(self)
        # Start the keep-front timer every time the overlay becomes visible.
        if not self._front_timer.isActive():
            self._front_timer.start()
        self.overlay_shown.emit()

    def set_processing(self, processing: bool):
        """Show animated 'Processing…' dots while synthesis is running."""
        self._processing = processing
        if processing:
            self._dot_count = 0
            self._dot_timer.start()
            self._title_label.setText("Processing")
            self._update_label_colors()   # normal colour while processing
            self._expand()
        else:
            self._dot_timer.stop()
        self.update()

    def set_speaking(self, speaking: bool):
        self._speaking = speaking
        self._processing = False
        self._paused = False
        self._dot_timer.stop()
        if speaking:
            self._title_label.setText("Speaking…  ■ click to stop")
            self._update_label_colors(speaking=True)   # title → RED
            self._expand()
        else:
            # Reset body label to plain preview text
            display = self._text if len(self._text) <= 120 else self._text[:117] + "…"
            self._body_label.setText(display)
            self._title_label.setText("Tap to read" if self._text else "Veaja is ready")
            self._update_label_colors()                # restore normal
        self.update()

    def set_current_word(self, char_start: int, char_end: int):
        """
        Karaoke-style highlight in the overlay body label.
        Called every ~40 ms while speaking so the current word glows yellow.
        Works in ALL contexts — even when reading a PDF or Word document —
        because it only updates the pill's own label, not the third-party app.
        """
        if not self._speaking or not self._text:
            return

        import html as _html

        text = self._text
        char_start = max(0, min(char_start, len(text)))
        char_end   = max(char_start, min(char_end, len(text)))

        # Show a context window: ~35 chars before + current word + ~80 chars after
        ctx_before = 35
        ctx_after  = 80

        before = text[:char_start]
        word   = text[char_start:char_end]
        after  = text[char_end:]

        if len(before) > ctx_before:
            before = "\u2026" + before[-ctx_before:]
        if len(after) > ctx_after:
            after = after[:ctx_after] + "\u2026"

        body_color = "#AEAEB2" if self._dark else "#6C6C70"
        word_color = "#FFD60A"   # yellow — always visible on both themes

        html_text = (
            f"<span style='color:{body_color}'>{_html.escape(before)}</span>"
            f"<span style='color:{word_color};font-weight:bold'>"
            f"{_html.escape(word)}</span>"
            f"<span style='color:{body_color}'>{_html.escape(after)}</span>"
        )
        self._body_label.setText(html_text)

    def set_paused(self, paused: bool):
        """Show paused state — click overlay to resume."""
        self._paused = paused
        self._speaking = False
        self._processing = False
        self._dot_timer.stop()
        if paused:
            self._title_label.setText("Paused  ▶ click to resume")
            self._update_label_colors(paused=True)     # title → ORANGE
            self._expand()
        else:
            self._title_label.setText("Tap to read" if self._text else "Veaja is ready")
            self._update_label_colors()                # restore normal
        self.update()

    def apply_profile(self, profile: dict):
        """
        Called by AppController when user saves their profile.
        Swaps the overlay logo to their custom avatar, or resets to default.
        """
        logo_path = profile.get("logo_path")
        if logo_path and os.path.exists(logo_path):
            self._logo.load_custom(logo_path)
        else:
            self._logo.reset_to_default()

    def show_near(self, screen_x: int, screen_y: int):
        """
        Show the overlay pill near the given screen coordinates.
        Places the overlay to the LEFT of the cursor, centered vertically —
        approximating the left edge of the selected text block at mid-height.
        Clamps to screen bounds so it never goes off-screen.
        """
        screen = QApplication.primaryScreen().availableGeometry()
        # Place to the left of the cursor, vertically centred on it
        x = screen_x - self.width() - 20
        y = screen_y - self.height() // 2
        # If not enough room on the left, fall back to the right
        if x < screen.left() + 10:
            x = screen_x + 20
        # Clamp to screen bounds
        x = min(x, screen.right()  - self.width()  - 10)
        y = max(y, screen.top()    + 10)
        y = min(y, screen.bottom() - self.height() - 10)
        self.move(x, y)
        self.show_overlay()

    def update_theme(self, dark: bool):
        """Called by AppController when user toggles the theme."""
        self._dark = dark
        self._logo.reload_for_theme(dark)
        self._update_label_colors(dark,
                                  speaking=self._speaking,
                                  paused=self._paused)
        self.update()

    # ------------------------------------------------------------------ #
    # Background painting  (pill / circle shape)
    # ------------------------------------------------------------------ #

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Use stored _dark flag — never call _is_dark_mode() here because
        # Qt may misread the Windows 11 dark mode palette, causing every
        # repaint to flip the pill colour incorrectly.
        bg     = QColor(38, 38, 40, 245) if self._dark else QColor(255, 255, 255, 240)
        border = QColor(70, 70, 75, 200) if self._dark else QColor(210, 210, 215, 200)

        rect   = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        radius = PILL_HEIGHT / 2

        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(border, 1.0))
        painter.drawRoundedRect(rect, radius, radius)

    # ------------------------------------------------------------------ #
    # Mouse events — drag + click
    # ------------------------------------------------------------------ #

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self._dragging = False
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self._press_pos is None:
            return
        if event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._press_pos
            if not self._dragging and delta.manhattanLength() > DRAG_PX:
                self._dragging = True
            if self._dragging:
                new_top_left = (event.globalPosition().toPoint()
                                - QPoint(self.width() // 2, self.height() // 2))
                self.move(new_top_left)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self._dragging:
                if self._speaking or self._processing:
                    self.stop_requested.emit()   # pause (AppController decides)
                elif self._paused:
                    self.stop_requested.emit()   # resume (AppController decides)
                elif self._text:
                    self.read_requested.emit(self._text)
            self._press_pos = None
            self._dragging = False

    # ------------------------------------------------------------------ #
    # Hover — expand / collapse text panel
    # ------------------------------------------------------------------ #

    def enterEvent(self, event):
        super().enterEvent(event)
        if self._text:
            self._expand()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._collapse()

    # ------------------------------------------------------------------ #
    # Context menu
    # ------------------------------------------------------------------ #

    def _show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet(self._menu_style())

        act_hide = QAction("Hide Veaja", self)
        act_hide.triggered.connect(self.hide_requested)

        act_settings = QAction("Settings…", self)
        act_settings.triggered.connect(self.settings_requested)

        menu.addAction(act_hide)
        menu.addSeparator()
        menu.addAction(act_settings)
        menu.exec(pos)

    def _menu_style(self) -> str:
        dark = _is_dark_mode()
        if dark:
            return (
                "QMenu { background:#2C2C2E; color:#F5F5F5; border:1px solid #444; "
                "border-radius:8px; padding:4px; }"
                "QMenu::item:selected { background:#3A3A3C; border-radius:4px; }"
            )
        return (
            "QMenu { background:#FFFFFF; color:#1C1C1E; border:1px solid #DDD; "
            "border-radius:8px; padding:4px; }"
            "QMenu::item:selected { background:#F0F0F0; border-radius:4px; }"
        )

    # ------------------------------------------------------------------ #
    # Default screen position (bottom-right)
    # ------------------------------------------------------------------ #

    def _position_default(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.right()  - self.width()  - 24
        y = screen.bottom() - self.height() - 24
        self.move(x, y)

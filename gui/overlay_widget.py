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
    QSizePolicy, QApplication, QMenu
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
    """Renders the Veaja PNG logo clipped to a circle. PNG is used instead
    of SVG for faster load time and lower CPU cost during paint."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(LOGO_SIZE, LOGO_SIZE)
        self._pixmap: QPixmap | None = None
        self._load_png()
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def _load_png(self, dark: bool | None = None):
        """
        logo_dark.png  = dark artwork on WHITE background → use in LIGHT mode
        logo_light.png = light artwork on DARK background → use in DARK mode
        """
        if dark is None:
            dark = _is_dark_mode()
        name = "logo_light.png" if dark else "logo_dark.png"
        path = os.path.join(ASSETS, name)
        if os.path.exists(path):
            # Load once and scale to exact widget size — cached by Qt
            raw = QPixmap(path)
            self._pixmap = raw.scaled(
                LOGO_SIZE, LOGO_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            self._pixmap = None
        self.update()

    def reload_for_theme(self, dark: bool):
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

        # Thin ring border
        painter.setClipping(False)
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
    hide_requested     = pyqtSignal()
    settings_requested = pyqtSignal()
    overlay_shown      = pyqtSignal()
    overlay_hidden     = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # State
        self._text: str = ""
        self._speaking: bool = False
        self._press_pos: QPoint | None = None
        self._dragging: bool = False
        self._expanded: bool = False

        self._setup_window()
        self._build_ui()
        self._build_animations()
        self._build_keep_front_timer()
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

        # Text panel (hidden until hover)
        self._text_panel = QWidget()
        self._text_panel.setFixedHeight(LOGO_SIZE)
        self._text_panel.setMaximumWidth(0)
        self._text_panel.setMinimumWidth(0)
        self._text_panel.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )

        tp_layout = QVBoxLayout(self._text_panel)
        tp_layout.setContentsMargins(12, 6, 10, 6)
        tp_layout.setSpacing(2)

        self._title_label = QLabel("Veaja is ready")
        self._title_label.setObjectName("overlayTitle")
        font_title = QFont()
        font_title.setPointSize(10)
        font_title.setWeight(QFont.Weight.Medium)
        self._title_label.setFont(font_title)

        self._body_label = QLabel("Select text to read…")
        self._body_label.setObjectName("overlayBody")
        self._body_label.setWordWrap(True)
        font_body = QFont()
        font_body.setPointSize(9)
        self._body_label.setFont(font_body)

        tp_layout.addWidget(self._title_label)
        tp_layout.addWidget(self._body_label)
        tp_layout.addStretch()

        outer.addWidget(self._text_panel)

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

    def set_text(self, text: str):
        """Called by AppController when new selected text is ready."""
        self._text = text
        display = text if len(text) <= 120 else text[:117] + "…"
        self._body_label.setText(display)
        self._title_label.setText("Tap to read" if text else "Veaja is ready")
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

    def set_speaking(self, speaking: bool):
        self._speaking = speaking
        self._title_label.setText("Speaking…" if speaking else "Tap to read")
        self.update()

    def update_theme(self, dark: bool):
        """Called by AppController when user toggles the theme."""
        self._logo.reload_for_theme(dark)
        self.update()

    # ------------------------------------------------------------------ #
    # Background painting  (pill / circle shape)
    # ------------------------------------------------------------------ #

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        dark = _is_dark_mode()
        bg    = QColor(28, 28, 30, 235) if dark else QColor(255, 255, 255, 240)
        border = QColor(70, 70, 75, 200) if dark else QColor(210, 210, 215, 200)

        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
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
            if not self._dragging and self._text:
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

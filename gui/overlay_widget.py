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
import sys
import ctypes
import platform
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QSizePolicy, QApplication, QMenu
)
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtCore import (
    Qt, QPoint, QRect, QRectF, QVariantAnimation,
    QEasingCurve, pyqtSignal, QPropertyAnimation, QTimer
)
from PyQt6.QtGui import (
    QPainter, QPainterPath, QColor, QPen, QBrush,
    QFont, QCursor, QPalette, QAction
)


def _mac_float_above_all(widget: QWidget):
    """
    On Mac: set the NSWindow level to NSFloatingWindowLevel (3) and
    enable CanJoinAllSpaces so the overlay appears above every app window
    on every Space.  No-op on Windows/Linux.
    """
    if platform.system() != "Darwin":
        return
    try:
        objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
        objc.objc_msgSend.restype = ctypes.c_void_p

        ns_view = ctypes.c_void_p(int(widget.winId()))

        # [nsView window]
        sel_window = ctypes.c_void_p(objc.sel_registerName(b"window"))
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        ns_window = ctypes.c_void_p(objc.objc_msgSend(ns_view, sel_window))

        # [nsWindow setLevel: NSFloatingWindowLevel]   (= 3)
        sel_setLevel = ctypes.c_void_p(objc.sel_registerName(b"setLevel:"))
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long]
        objc.objc_msgSend(ns_window, sel_setLevel, 3)

        # [nsWindow setCollectionBehavior: CanJoinAllSpaces | Stationary]
        # NSWindowCollectionBehaviorCanJoinAllSpaces = 1
        # NSWindowCollectionBehaviorStationary       = 16
        sel_setCB = ctypes.c_void_p(
            objc.sel_registerName(b"setCollectionBehavior:")
        )
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
        objc.objc_msgSend(ns_window, sel_setCB, 1 | 16)

    except Exception as exc:
        # Non-fatal — overlay still works, just might not float above every app
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


def _is_dark_mode() -> bool:
    app = QApplication.instance()
    if app is None:
        return False
    return app.palette().color(QPalette.ColorRole.Window).lightness() < 128


# ══════════════════════════════════════════════════════════════════════════════
# Circular logo widget
# ══════════════════════════════════════════════════════════════════════════════

class _LogoCircle(QWidget):
    """Renders the Veaja SVG clipped to a circle."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(LOGO_SIZE, LOGO_SIZE)
        self._renderer = None
        self._load_svg()
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def _load_svg(self):
        try:
            from PyQt6.QtSvg import QSvgRenderer
            dark = _is_dark_mode()
            path = os.path.join(ASSETS, "logo_dark.svg" if dark else "logo_light.svg")
            if os.path.exists(path):
                self._renderer = QSvgRenderer(path, self)
        except Exception:
            self._renderer = None

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Circular clip
        clip = QPainterPath()
        clip.addEllipse(QRectF(0, 0, LOGO_SIZE, LOGO_SIZE))
        painter.setClipPath(clip)

        # Background circle fill
        dark = _is_dark_mode()
        bg = QColor(30, 30, 30) if dark else QColor(245, 245, 245)
        painter.fillRect(0, 0, LOGO_SIZE, LOGO_SIZE, bg)

        # Render SVG
        if self._renderer and self._renderer.isValid():
            self._renderer.render(painter, QRectF(0, 0, LOGO_SIZE, LOGO_SIZE))
        else:
            # Fallback: draw "V" letter
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

        # Ring border
        painter.setClipping(False)
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

    read_requested    = pyqtSignal(str)
    hide_requested    = pyqtSignal()
    settings_requested = pyqtSignal()

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

        # ── Logo circle ──────────────────────────────────────────────────
        self._logo = _LogoCircle()
        outer.addWidget(self._logo)

        # ── Text panel (hidden until hover) ─────────────────────────────
        self._text_panel = QWidget()
        self._text_panel.setFixedHeight(LOGO_SIZE)
        self._text_panel.setMaximumWidth(0)   # starts collapsed
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
        # Resize the outer widget smoothly
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
    # Public API
    # ------------------------------------------------------------------ #

    def set_text(self, text: str):
        """Called by AppController when new selected text is ready."""
        self._text = text
        # Truncate for display
        display = text if len(text) <= 120 else text[:117] + "…"
        self._body_label.setText(display)
        self._title_label.setText("Tap to read" if text else "Veaja is ready")
        self.show_overlay()

    def show_overlay(self):
        self.show()
        self.raise_()

    def hide_overlay(self):
        self._collapse()
        QTimer.singleShot(ANIM_MS + 50, self.hide)

    def set_speaking(self, speaking: bool):
        self._speaking = speaking
        self._title_label.setText("Speaking…" if speaking else "Tap to read")
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
        radius = PILL_HEIGHT / 2  # perfect pill / circle

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

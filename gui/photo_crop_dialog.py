"""
PhotoCropDialog — Facebook-style profile photo editor.

Features:
  • Drag  — pan the image inside the circular crop area
  • Scroll / Zoom slider — zoom in / out (0.5× – 4×)
  • Rotation slider + ↺ / ↻ buttons — fine rotation and 90° snaps
  • result_pixmap() — returns the final square-cropped QPixmap
"""

import math

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QWidget, QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, QPointF, QRectF, QSize
from PyQt6.QtGui import (
    QPainter, QPainterPath, QColor, QPen, QBrush,
    QPixmap, QTransform, QFont, QCursor, QLinearGradient
)


# ── Canvas ────────────────────────────────────────────────────────────────────

class _CropCanvas(QWidget):
    """
    Interactive 300×300 circular canvas.
    Drag   → pan    |   Scroll   → zoom    |   Sliders/buttons set zoom & angle.
    """
    CANVAS = 300

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.CANVAS, self.CANVAS)
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))

        # Scale source so its shortest side fills the canvas at zoom=1
        scale = self.CANVAS / min(pixmap.width(), pixmap.height())
        self._src = pixmap.scaled(
            int(pixmap.width()  * scale),
            int(pixmap.height() * scale),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self._zoom:   float  = 1.0
        self._angle:  float  = 0.0
        self._offset: QPointF = QPointF(0.0, 0.0)

        self._drag_start:  QPointF | None = None
        self._off_at_drag: QPointF | None = None

    # ── Public setters ────────────────────────────────────────────────────────

    def set_zoom(self, value: float):
        self._zoom = max(0.5, min(4.0, value))
        self.update()

    def set_angle(self, degrees: float):
        self._angle = degrees % 360
        self.update()

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # ── Checkerboard background (shows transparency) ──────────────────
        tile = 14
        cols = math.ceil(self.CANVAS / tile)
        for row in range(cols):
            for col in range(cols):
                c = QColor(60, 60, 60) if (row + col) % 2 == 0 else QColor(45, 45, 45)
                painter.fillRect(col * tile, row * tile, tile, tile, c)

        # ── Circular clip ─────────────────────────────────────────────────
        clip = QPainterPath()
        clip.addEllipse(QRectF(0, 0, self.CANVAS, self.CANVAS))
        painter.setClipPath(clip)

        # ── Image transform: center → rotate → zoom → pan ────────────────
        cx = cy = self.CANVAS / 2.0
        t = QTransform()
        t.translate(cx + self._offset.x(), cy + self._offset.y())
        t.rotate(self._angle)
        t.scale(self._zoom, self._zoom)
        t.translate(-self._src.width() / 2.0, -self._src.height() / 2.0)
        painter.setTransform(t)
        painter.drawPixmap(0, 0, self._src)

        # ── Ring overlay ──────────────────────────────────────────────────
        painter.resetTransform()
        painter.setClipping(False)
        pen = QPen(QColor(255, 255, 255, 60), 2.0)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(1, 1, self.CANVAS - 2, self.CANVAS - 2)

        # ── Rule-of-thirds grid (subtle) ──────────────────────────────────
        grid_pen = QPen(QColor(255, 255, 255, 28), 0.8)
        painter.setPen(grid_pen)
        for i in (1, 2):
            x = int(self.CANVAS * i / 3)
            y = int(self.CANVAS * i / 3)
            painter.drawLine(x, 0, x, self.CANVAS)
            painter.drawLine(0, y, self.CANVAS, y)

    # ── Mouse ─────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start  = event.position()
            self._off_at_drag = QPointF(self._offset)
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))

    def mouseMoveEvent(self, event):
        if self._drag_start and (event.buttons() & Qt.MouseButton.LeftButton):
            delta = event.position() - self._drag_start
            self._offset = QPointF(
                self._off_at_drag.x() + delta.x(),
                self._off_at_drag.y() + delta.y(),
            )
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = None
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))

    def wheelEvent(self, event):
        factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        self.set_zoom(self._zoom * factor)

    # ── Export ────────────────────────────────────────────────────────────────

    def result_pixmap(self, size: int = 512) -> QPixmap:
        """
        Render the current view into a square QPixmap at `size`×`size`.
        Content is what was visible inside the circular crop area,
        scaled to fill the square — ready to save / display.
        """
        app = QApplication.instance()
        dpr = app.primaryScreen().devicePixelRatio() if (app and app.primaryScreen()) else 1.0
        phys = int(size * dpr)
        px = QPixmap(phys, phys)
        px.fill(Qt.GlobalColor.transparent)

        scale = phys / self.CANVAS
        painter = QPainter(px)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        cx = cy = phys / 2.0
        t = QTransform()
        t.translate(cx + self._offset.x() * scale, cy + self._offset.y() * scale)
        t.rotate(self._angle)
        t.scale(self._zoom * scale, self._zoom * scale)
        t.translate(-self._src.width() / 2.0, -self._src.height() / 2.0)
        painter.setTransform(t)
        painter.drawPixmap(0, 0, self._src)
        painter.end()
        px.setDevicePixelRatio(dpr)
        return px


# ── Dialog ────────────────────────────────────────────────────────────────────

class PhotoCropDialog(QDialog):
    """Modal dialog returned with result_pixmap() on accept."""

    def __init__(self, pixmap: QPixmap, dark: bool = True, parent=None):
        super().__init__(parent)
        self._dark = dark
        self.setWindowTitle("Edit Profile Photo")
        self.setModal(True)
        self.setFixedSize(380, 560)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build_ui(pixmap)
        self._apply_style()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self, pixmap: QPixmap):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        card = QWidget()
        card.setObjectName("cropCard")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(24, 20, 24, 24)
        card_lay.setSpacing(0)
        root.addWidget(card)

        # ── Title bar ─────────────────────────────────────────────────────
        title_row = QHBoxLayout()
        title_lbl = QLabel("Edit Profile Photo")
        title_lbl.setObjectName("cropTitle")
        close_btn = QPushButton("✕")
        close_btn.setObjectName("cropClose")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        title_row.addWidget(close_btn)
        card_lay.addLayout(title_row)
        card_lay.addSpacing(16)

        # ── Canvas ────────────────────────────────────────────────────────
        self._canvas = _CropCanvas(pixmap)
        canvas_row = QHBoxLayout()
        canvas_row.addStretch()
        canvas_row.addWidget(self._canvas)
        canvas_row.addStretch()
        card_lay.addLayout(canvas_row)
        card_lay.addSpacing(6)

        # Hint label
        hint = QLabel("Drag to reposition  ·  Scroll to zoom")
        hint.setObjectName("cropHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_lay.addWidget(hint)
        card_lay.addSpacing(20)

        # ── Zoom ──────────────────────────────────────────────────────────
        card_lay.addWidget(self._section_label("Zoom"))
        card_lay.addSpacing(6)
        zoom_row = QHBoxLayout()
        zoom_row.setSpacing(8)
        z_out = self._icon_btn("－", "zoomBtn")
        self._zoom_slider = self._make_slider(50, 400, 100)
        z_in  = self._icon_btn("＋", "zoomBtn")
        self._zoom_val = QLabel("1.0×")
        self._zoom_val.setObjectName("cropValue")
        self._zoom_val.setFixedWidth(38)
        self._zoom_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        zoom_row.addWidget(z_out)
        zoom_row.addWidget(self._zoom_slider, 1)
        zoom_row.addWidget(z_in)
        zoom_row.addWidget(self._zoom_val)
        card_lay.addLayout(zoom_row)
        card_lay.addSpacing(18)

        z_out.clicked.connect(lambda: self._nudge_zoom(-10))
        z_in.clicked.connect(lambda:  self._nudge_zoom(+10))
        self._zoom_slider.valueChanged.connect(self._on_zoom_changed)

        # ── Rotation ──────────────────────────────────────────────────────
        card_lay.addWidget(self._section_label("Rotation"))
        card_lay.addSpacing(6)
        rot_row = QHBoxLayout()
        rot_row.setSpacing(8)
        r_ccw = self._icon_btn("↺", "rotBtn")
        self._rot_slider = self._make_slider(-180, 180, 0)
        r_cw  = self._icon_btn("↻", "rotBtn")
        self._rot_val = QLabel("0°")
        self._rot_val.setObjectName("cropValue")
        self._rot_val.setFixedWidth(38)
        self._rot_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        rot_row.addWidget(r_ccw)
        rot_row.addWidget(self._rot_slider, 1)
        rot_row.addWidget(r_cw)
        rot_row.addWidget(self._rot_val)
        card_lay.addLayout(rot_row)
        card_lay.addSpacing(6)

        r_ccw.clicked.connect(lambda: self._snap_rotate(-90))
        r_cw.clicked.connect(lambda:  self._snap_rotate(+90))
        self._rot_slider.valueChanged.connect(self._on_rot_changed)

        # Reset rotation button
        reset_row = QHBoxLayout()
        reset_row.addStretch()
        reset_btn = QPushButton("Reset rotation")
        reset_btn.setObjectName("resetRotBtn")
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.clicked.connect(lambda: self._rot_slider.setValue(0))
        reset_row.addWidget(reset_btn)
        reset_row.addStretch()
        card_lay.addLayout(reset_row)
        card_lay.addSpacing(24)

        # ── Action buttons ────────────────────────────────────────────────
        act_row = QHBoxLayout()
        act_row.setSpacing(12)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cropCancel")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)

        apply_btn = QPushButton("Apply")
        apply_btn.setObjectName("cropApply")
        apply_btn.setFixedHeight(40)
        apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_btn.clicked.connect(self.accept)

        act_row.addWidget(cancel_btn, 1)
        act_row.addWidget(apply_btn, 1)
        card_lay.addLayout(act_row)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text.upper())
        lbl.setObjectName("cropSection")
        return lbl

    def _icon_btn(self, text: str, obj: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName(obj)
        btn.setFixedSize(30, 30)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def _make_slider(self, lo: int, hi: int, val: int) -> QSlider:
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(lo, hi)
        s.setValue(val)
        return s

    def _nudge_zoom(self, delta: int):
        self._zoom_slider.setValue(self._zoom_slider.value() + delta)

    def _snap_rotate(self, delta: int):
        current = self._rot_slider.value()
        snapped = round(current / 90) * 90 + delta
        snapped = max(-180, min(180, snapped))
        self._rot_slider.setValue(snapped)

    def _on_zoom_changed(self, val: int):
        zoom = val / 100.0
        self._canvas.set_zoom(zoom)
        self._zoom_val.setText(f"{zoom:.1f}×")

    def _on_rot_changed(self, val: int):
        self._canvas.set_angle(float(val))
        self._rot_val.setText(f"{val}°")

    # ── Style ─────────────────────────────────────────────────────────────────

    def _apply_style(self):
        if self._dark:
            bg       = "#1e1e20"
            card_bg  = "#2a2a2d"
            border   = "rgba(255,255,255,0.10)"
            title_c  = "#f0f0f0"
            hint_c   = "rgba(200,200,200,0.5)"
            sec_c    = "rgba(180,180,180,0.55)"
            val_c    = "#cccccc"
            close_c  = "rgba(255,255,255,0.35)"
            close_h  = "rgba(255,255,255,0.15)"
            slider_g = "#555"
            slider_h = "#888"
            icon_btn_bg   = "rgba(255,255,255,0.07)"
            icon_btn_h    = "rgba(255,255,255,0.14)"
            icon_btn_c    = "#cccccc"
            reset_c       = "rgba(180,180,180,0.5)"
            reset_h       = "rgba(180,180,180,0.8)"
            cancel_bg     = "rgba(255,255,255,0.07)"
            cancel_c      = "#cccccc"
            cancel_h      = "rgba(255,255,255,0.12)"
            apply_bg      = "#e05a2b"
            apply_h       = "#c94d22"
            apply_c       = "#ffffff"
        else:
            bg       = "#f0f0f2"
            card_bg  = "#ffffff"
            border   = "rgba(0,0,0,0.10)"
            title_c  = "#1a1a1a"
            hint_c   = "rgba(80,80,80,0.6)"
            sec_c    = "rgba(80,80,80,0.6)"
            val_c    = "#333333"
            close_c  = "rgba(0,0,0,0.4)"
            close_h  = "rgba(0,0,0,0.08)"
            slider_g = "#bbb"
            slider_h = "#888"
            icon_btn_bg   = "rgba(0,0,0,0.06)"
            icon_btn_h    = "rgba(0,0,0,0.12)"
            icon_btn_c    = "#444444"
            reset_c       = "rgba(80,80,80,0.5)"
            reset_h       = "rgba(80,80,80,0.8)"
            cancel_bg     = "rgba(0,0,0,0.06)"
            cancel_c      = "#444444"
            cancel_h      = "rgba(0,0,0,0.10)"
            apply_bg      = "#e05a2b"
            apply_h       = "#c94d22"
            apply_c       = "#ffffff"

        self.setStyleSheet(f"""
QWidget#cropCard {{
    background: {card_bg};
    border: 1px solid {border};
    border-radius: 18px;
}}
QLabel#cropTitle {{
    font-size: 15px;
    font-weight: 700;
    color: {title_c};
}}
QPushButton#cropClose {{
    background: transparent;
    color: {close_c};
    border: none;
    font-size: 14px;
    border-radius: 14px;
}}
QPushButton#cropClose:hover {{ background: {close_h}; color: {title_c}; }}
QLabel#cropHint {{
    font-size: 11px;
    color: {hint_c};
}}
QLabel#cropSection {{
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.8px;
    color: {sec_c};
}}
QLabel#cropValue {{
    font-size: 11px;
    color: {val_c};
}}
QPushButton#zoomBtn, QPushButton#rotBtn {{
    background: {icon_btn_bg};
    color: {icon_btn_c};
    border: none;
    border-radius: 8px;
    font-size: 15px;
    font-weight: 600;
}}
QPushButton#zoomBtn:hover, QPushButton#rotBtn:hover {{
    background: {icon_btn_h};
}}
QPushButton#resetRotBtn {{
    background: transparent;
    color: {reset_c};
    border: none;
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 6px;
}}
QPushButton#resetRotBtn:hover {{ color: {reset_h}; }}
QSlider::groove:horizontal {{
    height: 4px;
    background: {slider_g};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 16px;
    height: 16px;
    margin: -6px 0;
    background: #e05a2b;
    border-radius: 8px;
}}
QSlider::sub-page:horizontal {{
    background: #e05a2b;
    border-radius: 2px;
}}
QSlider::groove:horizontal:hover {{ background: {slider_h}; }}
QPushButton#cropCancel {{
    background: {cancel_bg};
    color: {cancel_c};
    border: 1px solid {border};
    border-radius: 10px;
    font-size: 13px;
    font-weight: 500;
}}
QPushButton#cropCancel:hover {{ background: {cancel_h}; }}
QPushButton#cropApply {{
    background: {apply_bg};
    color: {apply_c};
    border: none;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton#cropApply:hover {{ background: {apply_h}; }}
""")

    # ── Result ────────────────────────────────────────────────────────────────

    def result_pixmap(self, size: int = 512) -> QPixmap:
        """Return the edited image as a square QPixmap."""
        return self._canvas.result_pixmap(size)

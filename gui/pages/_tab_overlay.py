"""gui/pages/_tab_overlay.py — Overlay tab for the Dashboard."""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QStackedLayout
)
from gui._window_shared import scaled  # noqa: F401
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPixmap, QPainter

from gui._window_shared import ASSETS


class OverlayTabMixin:
    """Overlay tab builder and pill icon logic."""

    def _build_overlay_tab(self) -> QWidget:
        frame = QWidget()
        frame.setObjectName("tabPage")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 18, 0, 0)
        lay.setSpacing(12)

        overlay_box = QWidget()
        overlay_box.setObjectName("overlayBox")
        ob_lay = QVBoxLayout(overlay_box)
        ob_lay.setContentsMargins(0, 0, 0, 0)
        ob_lay.setSpacing(0)

        stack_host = QWidget()
        stack_host.setObjectName("overlayStack")
        stack_lay = QStackedLayout(stack_host)
        stack_lay.setStackingMode(QStackedLayout.StackingMode.StackAll)
        stack_lay.setContentsMargins(0, 0, 0, 0)

        # Layer 0 — scrollable text preview
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent;")

        text_inner = QWidget()
        text_inner.setStyleSheet("background: transparent;")
        from PyQt6.QtWidgets import QVBoxLayout as _VL
        ti_lay = _VL(text_inner)
        ti_lay.setContentsMargins(22, 22, 22, 22)
        ti_lay.setSpacing(0)

        self._overlay_text_view = QLabel(
            "Select text in any window and press  Ctrl+R  to read aloud, or press  Ctrl+C  "
            "and the overlay pill will appear automatically. The floating pill tracks each word "
            "in real-time so you can follow along without switching windows.\n\n"
            "Veaja is a real text-to-speech tool built for everyday use. It works across PDFs, "
            "emails, web pages, documents, and apps that have no built-in read-aloud feature — "
            "just select text and it reads, no copy-paste required.\n\n"
            "The history system records every reading session — the original text, the voice used, "
            "the speed setting, and a timestamp — so you can revisit any session from the history "
            "page and replay it exactly as it was."
        )
        self._overlay_text_view.setObjectName("bodyText")
        self._overlay_text_view.setWordWrap(True)
        self._overlay_text_view.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        ti_lay.addWidget(self._overlay_text_view)
        ti_lay.addStretch()
        scroll.setWidget(text_inner)
        stack_lay.addWidget(scroll)

        # Layer 1 — floating draggable pill
        _PILL_W, _PILL_H = 300, 98
        pill_float = QWidget()
        pill_float.setObjectName("pillFloat")
        pill_float.setStyleSheet("background: transparent;")

        pill = QLabel(pill_float)
        pill.setObjectName("dashboardPill")
        pill.setFixedSize(_PILL_W, _PILL_H)
        pill.setCursor(Qt.CursorShape.OpenHandCursor)
        pill.setStyleSheet("background: transparent;")

        self._dashboard_pill_lbl  = pill
        self._pill_float          = pill_float
        self._pill_drag_start:  QPoint | None = None
        self._pill_drag_origin: QPoint | None = None

        def _pill_press(ev):
            if ev.button() == Qt.MouseButton.LeftButton:
                pill.setCursor(Qt.CursorShape.ClosedHandCursor)
                self._pill_drag_start  = ev.globalPosition().toPoint()
                self._pill_drag_origin = pill.pos()
            ev.accept()

        def _pill_move(ev):
            if self._pill_drag_start is None:
                return
            delta   = ev.globalPosition().toPoint() - self._pill_drag_start
            new_pos = self._pill_drag_origin + delta
            max_x   = pill_float.width()  - pill.width()
            max_y   = pill_float.height() - pill.height()
            pill.move(max(0, min(new_pos.x(), max_x)),
                      max(0, min(new_pos.y(), max_y)))
            ev.accept()

        def _pill_release(ev):
            pill.setCursor(Qt.CursorShape.OpenHandCursor)
            self._pill_drag_start  = None
            self._pill_drag_origin = None
            ev.accept()

        pill.mousePressEvent   = _pill_press
        pill.mouseMoveEvent    = _pill_move
        pill.mouseReleaseEvent = _pill_release

        QTimer.singleShot(0, self._update_dashboard_pill_icon)

        def _init_pill_pos():
            y = max(0, pill_float.height() - _PILL_H - 18)
            pill.move(18, y)
        QTimer.singleShot(0, _init_pill_pos)

        stack_lay.addWidget(pill_float)
        stack_lay.setCurrentIndex(1)
        ob_lay.addWidget(stack_host, 1)
        lay.addWidget(overlay_box, 1)

        hint = QLabel(
            "On window:  select text  and  Press  Ctrl+R  to read\n"
            "or  Ctrl+C  to pop up overlay"
        )
        hint.setObjectName("hintBar")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(hint)
        return frame

    def _update_dashboard_pill_icon(self):
        if not hasattr(self, "_dashboard_pill_lbl"):
            return
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtWidgets import QApplication

        is_circle = (not hasattr(self, "_shape_circle")) or self._shape_circle.isChecked()
        svg_name = (
            "overlay_circle_dark_icon.svg" if (is_circle and self._dark) else
            "overlay_circle_light_icon.svg" if is_circle else
            "overlay_retangle_dark_icon.svg" if self._dark else
            "overlay_retangle_light_icon.svg"
        )
        svg_path = os.path.join(ASSETS, svg_name)
        if not os.path.exists(svg_path):
            return

        pill = self._dashboard_pill_lbl
        w, h = pill.width(), pill.height()
        app  = QApplication.instance()
        dpr  = app.primaryScreen().devicePixelRatio() if app else 1.0
        px   = QPixmap(int(w * dpr), int(h * dpr))
        px.fill(Qt.GlobalColor.transparent)
        renderer = QSvgRenderer(svg_path)
        painter  = QPainter(px)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter)
        painter.end()
        px.setDevicePixelRatio(dpr)
        pill.setPixmap(px)

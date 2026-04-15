"""gui/pages/_flow_layout.py — Reusable flow/wrap layout + draggable tab bar."""

from PyQt6.QtWidgets import QLayout, QWidget, QPushButton
from PyQt6.QtCore import Qt, QRect, QSize, QPoint


# ── Flow layout ───────────────────────────────────────────────────────────────

class FlowLayout(QLayout):
    """Left-to-right wrapping layout — wraps children to the next row when full."""

    def __init__(self, parent=None, h_spacing: int = 6, v_spacing: int = 6):
        super().__init__(parent)
        self._h = h_spacing
        self._v = v_spacing
        self._items: list = []

    def addItem(self, item):
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        s = QSize()
        for item in self._items:
            s = s.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return s + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        m = self.contentsMargins()
        x = rect.x() + m.left()
        y = rect.y() + m.top()
        row_h = 0
        right = rect.right() - m.right()

        for item in self._items:
            w = item.sizeHint()
            next_x = x + w.width()
            if next_x > right and row_h > 0:
                x = rect.x() + m.left()
                y += row_h + self._v
                row_h = 0
                next_x = x + w.width()
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), w))
            x = next_x + self._h
            row_h = max(row_h, w.height())

        return y + row_h - rect.y() + m.bottom()


# Keep old private name working for any existing references
_FlowLayout = FlowLayout


# ── Draggable tab bar ─────────────────────────────────────────────────────────

# Canonical tab definitions — imported by dashboard_mixin and _DraggableTabBar
TAB_DEFS = [
    ("Overlay",     0),
    ("Text label",  1),
    ("Summary",     2),
    ("Translate",   3),
    ("Code",        4),
    ("Generate",    5),
]
DEFAULT_TAB_ORDER = [0, 1, 2, 3, 4, 5]


class DraggableTabBar(QWidget):
    """
    Horizontal tab bar whose buttons can be reordered by dragging.

    • Click  → switch to that tab (calls mixin._switch_tab with canonical idx)
    • Drag   → reorder; a vertical indicator line shows the drop position
    • Order  → persisted via mixin.get_tab_order() / apply_tab_order()
    """

    _DRAG_THRESHOLD = 6

    def __init__(self, mixin, parent=None):
        super().__init__(parent)
        self._mixin   = mixin
        self._order   = list(DEFAULT_TAB_ORDER)
        self._active  = 0

        self._drag_btn_idx:   int | None   = None
        self._drag_press_pos: QPoint | None = None
        self._dragging  = False
        self._drop_pos: int | None = None

        self.setObjectName("tabBar")
        self.setFixedHeight(36)

        from PyQt6.QtWidgets import QHBoxLayout
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._buttons: list[QPushButton] = []
        self._rebuild_buttons()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_active(self, canonical_idx: int):
        self._active = canonical_idx
        self._refresh_checked()

    def apply_order(self, order: list):
        if (isinstance(order, list)
                and len(order) == len(DEFAULT_TAB_ORDER)
                and sorted(order) == sorted(DEFAULT_TAB_ORDER)):
            self._order = list(order)
        self._rebuild_buttons()
        if not getattr(self, "_order_applied_once", False):
            self._order_applied_once = True
            if self._order:
                first = self._order[0]
                self._active = first
                self._mixin._tab_stack.setCurrentIndex(first)
                self._refresh_checked()

    def current_order(self) -> list:
        return list(self._order)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _rebuild_buttons(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        self._buttons.clear()

        for pos, canonical in enumerate(self._order):
            label = TAB_DEFS[canonical][0] if canonical < len(TAB_DEFS) else str(canonical)
            btn = QPushButton(label)
            btn.setObjectName("tabBtn")
            btn.setCheckable(True)
            btn.setFixedHeight(36)
            btn.setCursor(Qt.CursorShape.OpenHandCursor)

            btn.mousePressEvent   = lambda ev, i=pos: self._btn_press(ev, i)
            btn.mouseMoveEvent    = lambda ev, i=pos: self._btn_move(ev, i)
            btn.mouseReleaseEvent = lambda ev, i=pos, c=canonical: self._btn_release(ev, i, c)

            self._layout.addWidget(btn)
            self._buttons.append(btn)

        self._layout.addStretch()
        self._refresh_checked()

    def _refresh_checked(self):
        for pos, canonical in enumerate(self._order):
            if pos < len(self._buttons):
                self._buttons[pos].setChecked(canonical == self._active)

    # ── Drag handling ─────────────────────────────────────────────────────────

    def _btn_press(self, ev, pos: int):
        if ev.button() == Qt.MouseButton.LeftButton:
            self._drag_btn_idx   = pos
            self._drag_press_pos = ev.globalPosition().toPoint()
            self._dragging       = False
        ev.accept()

    def _btn_move(self, ev, pos: int):
        if not (ev.buttons() & Qt.MouseButton.LeftButton):
            return
        if self._drag_press_pos is None:
            return
        delta = (ev.globalPosition().toPoint() - self._drag_press_pos).manhattanLength()
        if not self._dragging and delta > self._DRAG_THRESHOLD:
            self._dragging = True
            self._buttons[pos].setCursor(Qt.CursorShape.ClosedHandCursor)
        if self._dragging:
            local_x = self.mapFromGlobal(ev.globalPosition().toPoint()).x()
            self._drop_pos = self._x_to_insert_pos(local_x)
            self.update()
        ev.accept()

    def _btn_release(self, ev, pos: int, canonical: int):
        if ev.button() == Qt.MouseButton.LeftButton:
            was_dragging = self._dragging
            if was_dragging and self._drop_pos is not None:
                self._do_reorder(self._drag_btn_idx, self._drop_pos)
            self._dragging       = False
            self._drop_pos       = None
            self._drag_btn_idx   = None
            self._drag_press_pos = None
            if pos < len(self._buttons):
                self._buttons[pos].setCursor(Qt.CursorShape.OpenHandCursor)
            self.update()
            if not was_dragging:
                self._mixin._switch_tab(canonical)
        ev.accept()

    def _x_to_insert_pos(self, x: int) -> int:
        for i, btn in enumerate(self._buttons):
            if x < btn.x() + btn.width() // 2:
                return i
        return len(self._buttons)

    def _do_reorder(self, from_pos: int, to_pos: int):
        if from_pos is None:
            return
        to_pos = max(0, min(to_pos, len(self._order)))
        if from_pos == to_pos or from_pos + 1 == to_pos:
            return
        item = self._order.pop(from_pos)
        if to_pos > from_pos:
            to_pos -= 1
        self._order.insert(to_pos, item)
        self._rebuild_buttons()
        self._mixin._on_tab_order_changed()

    # ── Drop indicator ────────────────────────────────────────────────────────

    def paintEvent(self, ev):
        super().paintEvent(ev)
        if not self._dragging or self._drop_pos is None:
            return
        from PyQt6.QtGui import QPainter, QColor, QPen
        painter = QPainter(self)
        is_dark = getattr(self._mixin, "_dark", False)
        pen = QPen(QColor("#ffffff" if is_dark else "#1a1a1a"), 2)
        painter.setPen(pen)
        x = self._insert_x(self._drop_pos)
        painter.drawLine(x, 4, x, self.height() - 4)
        painter.end()

    def _insert_x(self, pos: int) -> int:
        if not self._buttons:
            return 0
        if pos == 0:
            return self._buttons[0].x()
        if pos >= len(self._buttons):
            b = self._buttons[-1]
            return b.x() + b.width()
        return self._buttons[pos].x()

    def _is_dark(self) -> bool:
        return getattr(self._mixin, "_dark", False)


# Keep old private name working
_DraggableTabBar = DraggableTabBar

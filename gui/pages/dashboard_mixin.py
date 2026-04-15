"""
gui/pages/dashboard_mixin.py — Dashboard Page (assembler)
==========================================================

Assembles the Dashboard page from focused sub-modules:

  _tab_overlay.py   — Overlay tab
  _tab_text.py      — Text label tab
  _tab_summary.py   — Summary tab
  _tab_translate.py — Translate tab
  _tab_code.py      — Code analysis tab
  _tab_generate.py  — Generate tab
  _flow_layout.py   — FlowLayout + DraggableTabBar
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QStackedWidget
from PyQt6.QtCore import Qt, QTimer

from gui.pages._flow_layout import DraggableTabBar as _DraggableTabBar  # noqa: F401
from gui.pages._tab_overlay import OverlayTabMixin
from gui.pages._tab_text import TextTabMixin
from gui.pages._tab_summary import SummaryTabMixin
from gui.pages._tab_translate import TranslateTabMixin
from gui.pages._tab_code import CodeTabMixin
from gui.pages._tab_generate import GenerateTabMixin


class DashboardMixin(
    OverlayTabMixin,
    TextTabMixin,
    SummaryTabMixin,
    TranslateTabMixin,
    CodeTabMixin,
    GenerateTabMixin,
):
    """Mixin providing the full Dashboard page for MainWindow."""

    def _build_dashboard_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("contentPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(0)

        title = QLabel("Veaja Feature")
        title.setObjectName("pageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(title)
        lay.addSpacing(4)

        self._dashboard_title  = title
        self._title_fade_armed = False

        self._tab_bar_widget = _DraggableTabBar(self)
        lay.addWidget(self._tab_bar_widget)

        self._tab_stack = QStackedWidget()
        self._tab_stack.addWidget(self._build_overlay_tab())    # 0
        self._tab_stack.addWidget(self._build_text_tab())       # 1
        self._tab_stack.addWidget(self._build_summary_tab())    # 2
        self._tab_stack.addWidget(self._build_translate_tab())  # 3
        self._tab_stack.addWidget(self._build_code_tab())       # 4
        self._tab_stack.addWidget(self._build_generate_tab())   # 5
        lay.addWidget(self._tab_stack, 1)
        return page

    def _switch_tab(self, canonical_idx: int):
        self._tab_stack.setCurrentIndex(canonical_idx)
        self._tab_bar_widget.set_active(canonical_idx)

    def apply_tab_order(self, order: list):
        self._tab_bar_widget.apply_order(order)

    def get_tab_order(self) -> list:
        return self._tab_bar_widget.current_order()

    def _on_tab_order_changed(self):
        self.settings_save_requested.emit({"tab_order": self.get_tab_order()})

    def _fade_dashboard_title(self):
        if not hasattr(self, "_dashboard_title"):
            return
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
        lbl = self._dashboard_title
        lbl.setStyleSheet("")
        effect = QGraphicsOpacityEffect(lbl)
        effect.setOpacity(1.0)
        lbl.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", lbl)
        anim.setDuration(600)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InQuad)
        anim.finished.connect(lambda: lbl.setVisible(False))
        self._dashboard_title_anim = anim
        anim.start()

    def _restart_dashboard_title_fade(self):
        if not hasattr(self, "_dashboard_title"):
            return
        if hasattr(self, "_dashboard_title_anim"):
            self._dashboard_title_anim.stop()
        if hasattr(self, "_dashboard_title_timer") and self._dashboard_title_timer:
            self._dashboard_title_timer.stop()
        lbl = self._dashboard_title
        lbl.setVisible(True)
        lbl.setGraphicsEffect(None)
        self._dashboard_title_timer = QTimer(self)
        self._dashboard_title_timer.setSingleShot(True)
        self._dashboard_title_timer.timeout.connect(self._fade_dashboard_title)
        self._dashboard_title_timer.start(1000)

"""
gui/pages/dashboard_mixin.py — Dashboard Page (assembler)
==========================================================
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget, QPushButton
)
from PyQt6.QtCore import Qt, QTimer

from gui.pages._flow_layout import DraggableTabBar as _DraggableTabBar  # noqa: F401
from gui.pages._tab_overlay import OverlayTabMixin
from gui.pages._tab_text import TextTabMixin
from gui.pages._tab_summary import SummaryTabMixin
from gui.pages._tab_translate import TranslateTabMixin
from gui.pages._tab_code import CodeTabMixin
from gui.pages._tab_generate import GenerateTabMixin

# Canonical indices that require at least one API key
_GATED_TABS = {2, 3, 4, 5}  # Summary, Translate, Code, Generate


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
        self._tab_stack.addWidget(self._build_overlay_tab())                        # 0
        self._tab_stack.addWidget(self._build_text_tab())                           # 1
        self._tab_stack.addWidget(self._wrap_with_gate(self._build_summary_tab(),  2))  # 2
        self._tab_stack.addWidget(self._wrap_with_gate(self._build_translate_tab(),3))  # 3
        self._tab_stack.addWidget(self._wrap_with_gate(self._build_code_tab(),     4))  # 4
        self._tab_stack.addWidget(self._wrap_with_gate(self._build_generate_tab(), 5))  # 5
        lay.addWidget(self._tab_stack, 1)
        # Refresh lock icons after stack is built
        QTimer.singleShot(0, lambda: self._tab_bar_widget.refresh_lock_state())
        return page

    # ── Gate wrapper ──────────────────────────────────────────────────────────

    def _wrap_with_gate(self, content: QWidget, canonical_idx: int) -> QWidget:
        """
        Wraps a tab widget in a QStackedWidget:
          index 0 — gate screen (shown when no API key is set)
          index 1 — real content
        """
        wrapper = QStackedWidget()
        wrapper.setObjectName("tabPage")

        # Gate screen
        gate = QWidget()
        gate.setObjectName("tabPage")
        g_outer = QVBoxLayout(gate)
        g_outer.setContentsMargins(0, 0, 0, 0)
        g_outer.setSpacing(0)
        g_outer.addStretch(1)

        # Center block — stretches full width, all items centered
        center = QWidget()
        center.setObjectName("tabPage")
        g_lay = QVBoxLayout(center)
        g_lay.setContentsMargins(60, 0, 60, 0)
        g_lay.setSpacing(14)

        icon_lbl = QLabel("🔑")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 44px; background: transparent;")
        g_lay.addWidget(icon_lbl)

        msg = QLabel("This feature requires an API key.")
        msg.setObjectName("pageTitle")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setWordWrap(True)
        msg.setSizePolicy(msg.sizePolicy().horizontalPolicy(),
                          msg.sizePolicy().verticalPolicy())
        g_lay.addWidget(msg)

        sub = QLabel(
            "Paste your API key in My API Key to unlock\n"
            "Summary, Translate, Code and Generate."
        )
        sub.setObjectName("settingsLabel")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)
        g_lay.addWidget(sub)

        g_lay.addSpacing(10)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.addStretch()

        go_btn = QPushButton("Go to My API Key →")
        go_btn.setObjectName("btnPrimary")
        go_btn.setFixedHeight(40)
        go_btn.setMinimumWidth(180)
        go_btn.clicked.connect(lambda: self._navigate(8))
        btn_row.addWidget(go_btn)

        link_btn = QPushButton("Get a free API key ↗")
        link_btn.setObjectName("btnOutline")
        link_btn.setFixedHeight(40)
        link_btn.setMinimumWidth(180)
        link_btn.clicked.connect(self._open_api_key_guide)
        btn_row.addWidget(link_btn)
        btn_row.addStretch()

        g_lay.addLayout(btn_row)

        g_outer.addWidget(center, 0, Qt.AlignmentFlag.AlignHCenter)
        g_outer.addStretch(1)

        wrapper.addWidget(gate)    # 0 — gate
        wrapper.addWidget(content) # 1 — content

        # Store reference so _switch_tab can flip it
        if not hasattr(self, "_tab_gates"):
            self._tab_gates: dict[int, QStackedWidget] = {}
        self._tab_gates[canonical_idx] = wrapper

        return wrapper

    def _has_any_api_key(self) -> bool:
        """Return True if the user has saved at least one non-empty API key."""
        if not hasattr(self, "_api_key_inputs"):
            # Fall back to profile cache
            profile = getattr(self, "_api_pw_hash_cache", None)
            # Check profile dict stored on apply_profile
            cached = getattr(self, "_last_profile_cache", {})
            api_keys = [
                "api_key_openai", "api_key_gemini", "api_key_claude",
                "api_key_aistudio", "api_key_mistral", "api_key_cohere",
                "api_key_copilot", "api_key_deepl", "api_key_libretranslate",
                "api_key_stability", "api_key_elevenlabs",
            ]
            return any(cached.get(k, "").strip() for k in api_keys)
        return any(f.text().strip() for f in self._api_key_inputs.values())

    def _open_api_key_guide(self):
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl("https://platform.openai.com/api-keys"))

    def _switch_tab(self, canonical_idx: int):
        self._tab_stack.setCurrentIndex(canonical_idx)
        self._tab_bar_widget.set_active(canonical_idx)
        # Show gate or content for gated tabs
        if canonical_idx in _GATED_TABS and hasattr(self, "_tab_gates"):
            gate_stack = self._tab_gates.get(canonical_idx)
            if gate_stack:
                gate_stack.setCurrentIndex(1 if self._has_any_api_key() else 0)

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

    def _refresh_tab_gates(self):
        """Re-evaluate all gated tabs — call after API keys are saved."""
        if not hasattr(self, "_tab_gates") or not hasattr(self, "_tab_bar_widget"):
            return
        has_key = self._has_any_api_key()
        for gate_stack in self._tab_gates.values():
            gate_stack.setCurrentIndex(1 if has_key else 0)
        # Update lock icons on tab buttons
        self._tab_bar_widget.refresh_lock_state()
        # Update profession lock icons in Summary tab
        if hasattr(self, "_sum_prof_btns"):
            self.refresh_profession_locks()

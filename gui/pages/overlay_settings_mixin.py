"""
gui/pages/overlay_settings_mixin.py — Overlay Setting Page
===========================================================
Provides the Overlay Setting page (shape + animation controls).
Extracted from settings_mixin so Voice Setting stays focused on audio.
"""

import os

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer

from gui._window_shared import ASSETS, scaled
from gui.icon_utils import svg_icon


class OverlaySettingsMixin:
    """Mixin providing the Overlay Setting page for MainWindow."""

    def _build_overlay_settings_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("contentPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Top action bar: Reset + Save ──────────────────────────────────
        top = QWidget()
        top.setObjectName("pageTopAction")
        t_lay = QHBoxLayout(top)
        t_lay.setContentsMargins(scaled(32), scaled(14), scaled(32), scaled(10))
        t_lay.addStretch()

        self._overlay_reset_btn = QPushButton()
        self._overlay_reset_btn.setObjectName("btnOutline")
        self._overlay_reset_btn.setFixedSize(scaled(36), scaled(32))
        self._overlay_reset_btn.setToolTip("Reset overlay settings to defaults")
        self._overlay_reset_btn.clicked.connect(self._reset_overlay_settings)
        t_lay.addWidget(self._overlay_reset_btn)
        t_lay.addSpacing(scaled(8))

        save_btn = QPushButton("Save")
        save_btn.setObjectName("btnOutline")
        save_btn.setFixedSize(scaled(90), scaled(32))
        save_btn.clicked.connect(self._save_overlay_settings)
        t_lay.addWidget(save_btn)
        lay.addWidget(top)

        # ── Scrollable content ────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("settingsScroll")

        sc = QWidget()
        sc_lay = QVBoxLayout(sc)
        sc_lay.setContentsMargins(scaled(32), 0, scaled(32), scaled(24))
        sc_lay.setSpacing(scaled(14))

        # ── Shape ─────────────────────────────────────────────────────────
        shape_lbl = QLabel("Set overlay shape")
        shape_lbl.setObjectName("shapeSectionLabel")
        sc_lay.addWidget(shape_lbl)

        shape_box = QWidget()
        shape_box.setObjectName("shapeBox")
        sb_lay = QVBoxLayout(shape_box)
        sb_lay.setContentsMargins(scaled(16), scaled(8), scaled(16), scaled(40))
        sb_lay.setSpacing(0)

        edit_row = QHBoxLayout()
        edit_row.setContentsMargins(0, 0, 0, 0)
        edit_row.addStretch()
        shape_edit_ic = self._inline_edit_icon()
        shape_edit_ic.setObjectName("shapeEditIcon")
        shape_edit_ic.setFixedSize(scaled(16), scaled(16))
        edit_row.addWidget(shape_edit_ic)
        sb_lay.addLayout(edit_row)

        circle_row = self._shape_row("Circle", is_circle=True, checked=True)
        self._shape_circle = circle_row[0]
        sb_lay.addWidget(circle_row[1])

        sb_lay.addSpacing(scaled(20))

        rect_row = self._shape_row("Rectangle", is_circle=False, checked=False)
        self._shape_rect = rect_row[0]
        sb_lay.addWidget(rect_row[1])

        self._shape_circle.toggled.connect(
            lambda c: self._shape_rect.setChecked(not c) if c else None
        )
        self._shape_rect.toggled.connect(
            lambda c: self._shape_circle.setChecked(not c) if c else None
        )
        self._shape_circle.toggled.connect(lambda _: self._update_dashboard_pill_icon())
        QTimer.singleShot(0, self._update_dashboard_pill_icon)
        self._shape_circle.toggled.connect(
            lambda c: self.shape_changed.emit("circle" if c else "rectangle")
        )

        sc_lay.addWidget(shape_box)

        # ── Animation Overlay ─────────────────────────────────────────────
        anim_lbl = QLabel("Animation Overlay")
        anim_lbl.setObjectName("shapeSectionLabel")
        sc_lay.addWidget(anim_lbl)

        anim_box = QWidget()
        anim_box.setObjectName("shapeBox")
        ab_lay = QVBoxLayout(anim_box)
        ab_lay.setContentsMargins(scaled(16), scaled(12), scaled(16), scaled(16))
        ab_lay.setSpacing(scaled(10))

        self._anim_spin_chk = QCheckBox("Logo spin while reading")
        self._anim_spin_chk.setObjectName("settingsCheck")
        self._anim_spin_chk.setToolTip("Rotates the Veaja logo while speech is playing")
        self._anim_spin_chk.toggled.connect(lambda c: self.anim_spin_changed.emit(c))
        ab_lay.addWidget(self._anim_spin_chk)

        sc_lay.addWidget(anim_box)
        sc_lay.addStretch()
        scroll.setWidget(sc)
        lay.addWidget(scroll, 1)
        return page

    def _save_overlay_settings(self):
        settings = {
            "overlay_shape":     "circle" if self._shape_circle.isChecked() else "rectangle",
            "overlay_anim_spin": self._anim_spin_chk.isChecked(),
        }
        self.settings_save_requested.emit(settings)
        self._navigate(0)

    def _reset_overlay_settings(self):
        self._shape_rect.blockSignals(True)
        self._shape_circle.blockSignals(True)
        self._shape_rect.setChecked(True)
        self._shape_circle.setChecked(False)
        self._shape_rect.blockSignals(False)
        self._shape_circle.blockSignals(False)
        self.shape_changed.emit("rectangle")
        self._update_dashboard_pill_icon()
        self._anim_spin_chk.setChecked(True)

    def _update_overlay_reset_icon(self):
        if not hasattr(self, "_overlay_reset_btn"):
            return
        icon_color = "#c7c7cc" if self._dark else "#3a3a3c"
        icon_path = os.path.join(ASSETS, "restart_icon.svg")
        self._overlay_reset_btn.setIcon(svg_icon(icon_path, icon_color, 16))
        self._overlay_reset_btn.setIconSize(QSize(16, 16))

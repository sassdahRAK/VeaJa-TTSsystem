import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QLineEdit, QGraphicsDropShadowEffect, QCheckBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor, QPixmap, QPainter, QIcon
from PyQt6.QtSvg import QSvgRenderer

from gui._window_shared import ASSETS, _make_square_pixmap  # noqa: F401


def _make_icon_pixmap(svg_str: str, size: int = 16) -> QPixmap:
    """Render an inline SVG string into a QPixmap."""
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    dpr = app.primaryScreen().devicePixelRatio() if (app and app.primaryScreen()) else 1.0
    phys = int(size * dpr)
    px = QPixmap(phys, phys)
    px.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(svg_str.encode())
    p = QPainter(px)
    renderer.render(p)
    p.end()
    px.setDevicePixelRatio(dpr)
    return px


class ProfileMixin:
    """Mixin providing Profile page methods for MainWindow."""

    # ── Profile page (replaces popup dialog) ───────────────────────────────────

    def _build_profile_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("contentPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Top bar: Save button
        top = QWidget()
        top.setObjectName("pageTopAction")
        t_lay = QHBoxLayout(top)
        t_lay.setContentsMargins(32, 20, 32, 16)
        t_lay.addStretch()
        self._profile_save_btn = QPushButton("Save")
        self._profile_save_btn.setObjectName("btnOutline")
        self._profile_save_btn.setFixedSize(90, 32)
        self._profile_save_btn.clicked.connect(self._on_profile_page_save)
        t_lay.addWidget(self._profile_save_btn)
        lay.addWidget(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        body = QWidget()
        body.setObjectName("contentPage")
        b_lay = QVBoxLayout(body)
        b_lay.setContentsMargins(40, 10, 40, 40)
        b_lay.setSpacing(0)
        b_lay.addStretch()

        # Large profile photo with glow border
        photo_row = QHBoxLayout()
        photo_row.addStretch()
        self._profile_photo_frame = QWidget()
        self._profile_photo_frame.setObjectName("profilePhotoFrame")
        self._profile_photo_frame.setFixedSize(220, 220)
        self._profile_photo_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        self._profile_photo_frame.mousePressEvent = lambda _: self._on_profile_choose_photo()
        ppf_lay = QVBoxLayout(self._profile_photo_frame)
        ppf_lay.setContentsMargins(4, 4, 4, 4)
        self._profile_photo_lbl = QLabel()
        self._profile_photo_lbl.setFixedSize(212, 212)
        self._profile_photo_lbl.setScaledContents(True)
        self._profile_photo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ppf_lay.addWidget(self._profile_photo_lbl, 0, Qt.AlignmentFlag.AlignCenter)
        photo_row.addWidget(self._profile_photo_frame)
        photo_row.addStretch()
        b_lay.addLayout(photo_row)
        b_lay.addSpacing(10)

        # Name row: name input + SVG pencil icon (right)
        name_row = QHBoxLayout()
        name_row.setSpacing(6)
        name_row.addStretch()
        self._profile_name_edit = QLineEdit()
        self._profile_name_edit.setObjectName("profileNameEdit")
        self._profile_name_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._profile_name_edit.setFixedWidth(220)
        self._profile_name_edit.setFont(QFont("Segoe UI", 19, QFont.Weight.DemiBold))
        self._profile_name_edit.setFrame(False)
        self._profile_name_edit.textChanged.connect(self._on_profile_name_preview)
        name_row.addWidget(self._profile_name_edit)
        # SVG pencil icon — right of the name, clicks focus the name field
        _pencil_svg = (
            '<svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M11.5 1.5a1.5 1.5 0 0 1 2.12 2.12l-8.5 8.5-2.83.71.71-2.83z"'
            ' stroke="#888" stroke-width="1.2" fill="none"'
            ' stroke-linecap="round" stroke-linejoin="round"/>'
            '</svg>'
        )
        from PyQt6.QtSvg import QSvgRenderer as _Svg
        _rend = _Svg(_pencil_svg.encode())
        _px = QPixmap(13, 13)
        _px.fill(Qt.GlobalColor.transparent)
        _p = QPainter(_px)
        _rend.render(_p)
        _p.end()
        pencil_lbl = QLabel()
        pencil_lbl.setPixmap(_px)
        pencil_lbl.setFixedSize(13, 13)
        pencil_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        pencil_lbl.mousePressEvent = lambda _: self._profile_name_edit.setFocus()
        name_row.addWidget(pencil_lbl)
        name_row.addStretch()
        b_lay.addLayout(name_row)
        b_lay.addSpacing(14)

        # Section divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("profileDivider")
        divider.setStyleSheet("QFrame#profileDivider { border: none; border-top: 1px solid rgba(128,128,128,0.25); margin: 0 100px; }")
        b_lay.addWidget(divider)
        b_lay.addSpacing(18)

        # Section heading: small camera icon + "Profile Photo"
        _cam_svg = (
            '<svg viewBox="0 0 20 18" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M7 2l-1.5 2H3a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6'
            'a2 2 0 0 0-2-2h-2.5L13 2H7z" stroke="#888" stroke-width="1.4"'
            ' fill="none" stroke-linejoin="round"/>'
            '<circle cx="10" cy="10" r="3" stroke="#888" stroke-width="1.4" fill="none"/>'
            '</svg>'
        )
        heading_row = QHBoxLayout()
        heading_row.setSpacing(7)
        heading_row.addStretch()
        cam_lbl = QLabel()
        cam_lbl.setPixmap(_make_icon_pixmap(_cam_svg, 16))
        cam_lbl.setFixedSize(16, 16)
        heading_row.addWidget(cam_lbl)
        heading_lbl = QLabel("Profile Photo")
        heading_lbl.setObjectName("profileSectionHeading")
        heading_lbl.setStyleSheet(
            "QLabel#profileSectionHeading { font-size: 11px; font-weight: 600;"
            " letter-spacing: 0.8px; text-transform: uppercase;"
            " color: rgba(180,180,180,0.75); }"
        )
        heading_row.addWidget(heading_lbl)
        heading_row.addStretch()
        b_lay.addLayout(heading_row)
        b_lay.addSpacing(14)

        # Hint text
        hint_row = QHBoxLayout()
        hint_row.addStretch()
        hint_lbl = QLabel("Click the photo above to browse, or use the options below.")
        hint_lbl.setObjectName("profileHint")
        hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_lbl.setWordWrap(True)
        hint_lbl.setStyleSheet(
            "QLabel#profileHint { font-size: 11px; color: rgba(140,140,140,0.8); }"
        )
        hint_row.addWidget(hint_lbl)
        hint_row.addStretch()
        b_lay.addLayout(hint_row)
        b_lay.addSpacing(16)

        # SVG icons for buttons
        _upload_svg = (
            '<svg viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">'
            '<polyline points="9,12 9,3" stroke="#aaa" stroke-width="1.6"'
            ' stroke-linecap="round"/>'
            '<polyline points="5,7 9,3 13,7" stroke="#aaa" stroke-width="1.6"'
            ' fill="none" stroke-linejoin="round" stroke-linecap="round"/>'
            '<path d="M3 13v1a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2v-1"'
            ' stroke="#aaa" stroke-width="1.6" fill="none" stroke-linecap="round"/>'
            '</svg>'
        )
        _reset_svg = (
            '<svg viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M14 9 A5 5 0 1 1 11.5 4.2" stroke="#aaa" stroke-width="1.6"'
            ' fill="none" stroke-linecap="round"/>'
            '<polyline points="11,2 12.8,4.4 10,5.2" stroke="#aaa" stroke-width="1.6"'
            ' fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
            '</svg>'
        )

        # Buttons: Upload Photo | Set Default
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()

        self._upload_btn = QPushButton("  Upload Photo")
        self._upload_btn.setObjectName("profileActionBtn")
        self._upload_btn.setFixedSize(148, 38)
        self._upload_btn.setIconSize(QSize(16, 16))
        self._upload_btn.setIcon(self._profile_btn_icon(_upload_svg))
        self._upload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._upload_btn.clicked.connect(self._on_profile_choose_photo)
        btn_row.addWidget(self._upload_btn)

        self._default_btn = QPushButton("  Set Default")
        self._default_btn.setObjectName("profileActionBtn")
        self._default_btn.setFixedSize(132, 38)
        self._default_btn.setIconSize(QSize(16, 16))
        self._default_btn.setIcon(self._profile_btn_icon(_reset_svg))
        self._default_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._default_btn.clicked.connect(self._on_profile_reset_photo)
        btn_row.addWidget(self._default_btn)

        btn_row.addStretch()
        b_lay.addLayout(btn_row)
        self._apply_profile_btn_style()
        b_lay.addSpacing(16)

        # "Set to overlay profile" checkbox — only visible when custom photo is set
        cb_row = QHBoxLayout()
        cb_row.addStretch()
        self._overlay_cb = QCheckBox("Set as overlay profile")
        self._overlay_cb.setObjectName("overlayProfileCb")
        self._overlay_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self._overlay_cb.setVisible(False)   # hidden until a custom photo is uploaded
        self._overlay_cb.toggled.connect(self._on_overlay_cb_toggled)
        cb_row.addWidget(self._overlay_cb)
        cb_row.addStretch()
        b_lay.addLayout(cb_row)
        self._apply_overlay_cb_style()

        b_lay.addStretch()
        scroll.setWidget(body)
        lay.addWidget(scroll, 1)
        return page

    def _open_profile_page(self):
        """Navigate to the inline profile page, seeding it with current profile."""
        from PyQt6.QtWidgets import QFileDialog  # noqa: F401 (kept for pick)
        self._pending_profile = dict(self._pending_profile) if self._pending_profile else {}
        # Snapshot current saved state so "set default" can revert to it
        self._saved_name = self._title_label.text()
        self._saved_logo = self._logo_path
        # Populate fields from live state
        current_name = self._title_label.text()
        self._profile_name_edit.setText(current_name)
        self._reload_profile_page_photo()
        self._apply_profile_page_glow()
        # Restore checkbox state from saved profile
        if hasattr(self, "_overlay_cb"):
            has_custom = bool(self._pending_profile.get("logo_path") or self._logo_path)
            use_overlay = bool(self._pending_profile.get("overlay_use_profile_photo", False))
            self._overlay_cb.blockSignals(True)
            self._overlay_cb.setChecked(use_overlay)
            self._overlay_cb.setVisible(has_custom)
            self._overlay_cb.blockSignals(False)
        for btn, _ in self._nav_btns:
            btn.setChecked(False)
        # Hide the sidebar edit icon while on profile page
        if self._edit_icon_lbl is not None:
            self._edit_icon_lbl.setVisible(False)
        self._content_stack.setCurrentIndex(6)

    def _profile_btn_icon(self, svg_str: str):
        """Return a QIcon from an inline SVG string."""
        return QIcon(_make_icon_pixmap(svg_str, 16))

    def _apply_profile_btn_style(self):
        """Apply theme-aware styling to the profile action buttons."""
        if not hasattr(self, "_upload_btn"):
            return
        if self._dark:
            style = (
                "QPushButton#profileActionBtn {"
                " background: rgba(255,255,255,0.06);"
                " color: #e0e0e0;"
                " border: 1px solid rgba(255,255,255,0.15);"
                " border-radius: 10px;"
                " font-size: 13px; font-weight: 500;"
                " padding-left: 4px; }"
                "QPushButton#profileActionBtn:hover {"
                " background: rgba(255,255,255,0.12);"
                " border-color: rgba(255,255,255,0.3); }"
                "QPushButton#profileActionBtn:pressed {"
                " background: rgba(255,255,255,0.04); }"
            )
        else:
            style = (
                "QPushButton#profileActionBtn {"
                " background: rgba(0,0,0,0.04);"
                " color: #2c2c2c;"
                " border: 1px solid rgba(0,0,0,0.15);"
                " border-radius: 10px;"
                " font-size: 13px; font-weight: 500;"
                " padding-left: 4px; }"
                "QPushButton#profileActionBtn:hover {"
                " background: rgba(0,0,0,0.09);"
                " border-color: rgba(0,0,0,0.25); }"
                "QPushButton#profileActionBtn:pressed {"
                " background: rgba(0,0,0,0.02); }"
            )
        for btn in (self._upload_btn, self._default_btn):
            btn.setStyleSheet(style)

    def _apply_overlay_cb_style(self):
        """Theme-aware style for the overlay checkbox."""
        if not hasattr(self, "_overlay_cb"):
            return
        import os as _os
        check_icon = _os.path.join(ASSETS, "check_light.svg").replace("\\", "/")
        if self._dark:
            txt   = "rgba(200,200,200,0.85)"
            box   = "rgba(255,255,255,0.15)"
            chk   = "#e05a2b"
            hover = "rgba(255,255,255,0.22)"
        else:
            txt   = "rgba(60,60,60,0.85)"
            box   = "rgba(0,0,0,0.18)"
            chk   = "#e05a2b"
            hover = "rgba(0,0,0,0.25)"
        self._overlay_cb.setStyleSheet(f"""
QCheckBox#overlayProfileCb {{
    color: {txt};
    font-size: 12px;
    spacing: 8px;
}}
QCheckBox#overlayProfileCb::indicator {{
    width: 16px; height: 16px;
    border: 1.5px solid {box};
    border-radius: 4px;
    background: transparent;
}}
QCheckBox#overlayProfileCb::indicator:hover {{
    border-color: {hover};
}}
QCheckBox#overlayProfileCb::indicator:checked {{
    background: {chk};
    border-color: {chk};
    image: url({check_icon});
}}
""")

    def _on_overlay_cb_toggled(self, checked: bool):
        """Immediately preview the overlay logo change while on the profile page."""
        self._pending_profile["overlay_use_profile_photo"] = checked
        logo_path = self._pending_profile.get("logo_path") or self._logo_path
        # Push live preview to the overlay widget via the profile_save_requested signal
        self.profile_save_requested.emit(dict(self._pending_profile))

    def _apply_profile_page_glow(self):
        """Apply theme-aware glow to the large profile photo frame and name input."""
        if not self._profile_photo_frame:
            return
        if self._dark:
            # Orange glow, no border, frame bg matches logo PNG black background exactly
            glow_color = QColor("#f5a623")
            bg         = "#000000"   # exact match to logo_dark.png background
        else:
            glow_color = QColor("#7c6fff")   # soft purple on light bg
            bg         = "#ffffff"
        self._profile_photo_frame.setStyleSheet(
            f"#profilePhotoFrame {{ background: {bg}; border-radius: 12px; border: none; }}"
        )
        shadow = QGraphicsDropShadowEffect(self._profile_photo_frame)
        shadow.setBlurRadius(60)
        shadow.setOffset(0, 0)
        shadow.setColor(glow_color)
        self._profile_photo_frame.setGraphicsEffect(shadow)

        # Name input — must be transparent so it blends with the page background
        if hasattr(self, "_profile_name_edit"):
            txt = "#ffffff" if self._dark else "#1a1a1a"
            self._profile_name_edit.setStyleSheet(
                f"QLineEdit#profileNameEdit {{"
                f"  background: transparent;"
                f"  color: {txt};"
                f"  border: none;"
                f"  font-size: 19px; font-weight: 600;"
                f"}}"
            )

    def _reload_profile_page_photo(self):
        if not hasattr(self, "_profile_photo_lbl"):
            return
        logo_path = self._pending_profile.get("logo_path") or self._logo_path
        if logo_path and os.path.exists(logo_path):
            px = _make_square_pixmap(logo_path, 212)
        else:
            src = self._default_logo_path()
            px = _make_square_pixmap(src, 212) if src else None
        if px:
            self._profile_photo_lbl.setPixmap(px)

    def _on_profile_choose_photo(self):
        from PyQt6.QtWidgets import QFileDialog
        from gui.photo_crop_dialog import PhotoCropDialog
        import tempfile, os as _os

        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Avatar Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not path:
            return

        raw = QPixmap(path)
        if raw.isNull():
            return

        # Open the editor dialog
        dlg = PhotoCropDialog(raw, dark=self._dark, parent=self)
        if dlg.exec() != PhotoCropDialog.DialogCode.Accepted:
            return

        # Save the edited result as a temp PNG and use it as the avatar path
        edited = dlg.result_pixmap(512)
        tmp_dir = tempfile.gettempdir()
        save_path = _os.path.join(tmp_dir, "veaja_avatar_edited.png")
        edited.save(save_path, "PNG")

        self._pending_profile["logo_path"] = save_path
        self._reload_profile_page_photo()
        self._reload_header_logo(save_path)   # live preview in sidebar
        # Show checkbox now that a custom photo exists
        if hasattr(self, "_overlay_cb"):
            self._overlay_cb.setVisible(True)

    def _on_profile_reset_photo(self):
        """Reset to factory defaults: name 'Veaja', built-in logo, no custom photo."""
        default_name = "Veaja"
        self._pending_profile["logo_path"] = None
        self._pending_profile["app_name"]  = default_name
        self._pending_profile["overlay_use_profile_photo"] = False
        # Must explicitly clear stored path — _reload_header_logo(None) skips updating it
        self._logo_path = None
        # Restore profile page fields
        self._profile_name_edit.setText(default_name)
        self._reload_profile_page_photo()
        # Restore sidebar live preview to factory default
        self._title_label.setText(default_name)
        self._reload_header_logo()   # no arg → picks up self._logo_path = None → default img
        # Hide and uncheck the overlay checkbox — no custom photo to use
        if hasattr(self, "_overlay_cb"):
            self._overlay_cb.blockSignals(True)
            self._overlay_cb.setChecked(False)
            self._overlay_cb.setVisible(False)
            self._overlay_cb.blockSignals(False)
        # Reset overlay logo to default immediately
        self.profile_save_requested.emit(dict(self._pending_profile))

    def _on_profile_name_preview(self, text: str):
        """Live preview: update sidebar name label as user types."""
        name = text.strip()
        if any(c.isalnum() for c in name):
            self._title_label.setText(name)

    def _on_profile_page_save(self):
        name = self._profile_name_edit.text().strip()
        if not any(c.isalnum() for c in name):
            name = "Veaja"
        self._pending_profile["app_name"] = name
        # Commit sidebar immediately so it persists after navigating away
        self._title_label.setText(name)
        self.setWindowTitle(name)
        self._reload_header_logo(self._pending_profile.get("logo_path"))
        self.profile_save_requested.emit(dict(self._pending_profile))
        self._navigate(0)   # back to dashboard

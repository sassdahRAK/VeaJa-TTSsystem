import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QLineEdit, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from gui._window_shared import ASSETS, _make_square_pixmap  # noqa: F401


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
        b_lay.addSpacing(18)

        # Name row: pencil icon (left) + name input — matching role model layout
        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        name_row.addStretch()
        pencil_lbl = QLabel("✎")
        pencil_lbl.setObjectName("profilePageEdit")
        pencil_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        pencil_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        pencil_lbl.mousePressEvent = lambda _: self._on_profile_choose_photo()
        name_row.addWidget(pencil_lbl)
        self._profile_name_edit = QLineEdit()
        self._profile_name_edit.setObjectName("profileNameEdit")
        self._profile_name_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._profile_name_edit.setFixedWidth(240)
        self._profile_name_edit.setFont(QFont("-apple-system", 20, QFont.Weight.Bold))
        self._profile_name_edit.setFrame(False)
        self._profile_name_edit.textChanged.connect(self._on_profile_name_preview)
        name_row.addWidget(self._profile_name_edit)
        name_row.addStretch()
        b_lay.addLayout(name_row)
        b_lay.addSpacing(20)

        # "Change profile" label
        chg_row = QHBoxLayout()
        chg_row.addStretch()
        chg_lbl = QLabel("Change profile")
        chg_lbl.setObjectName("settingsLabel")
        chg_row.addWidget(chg_lbl)
        chg_row.addStretch()
        b_lay.addLayout(chg_row)
        b_lay.addSpacing(14)

        # Buttons: upload photo | set default
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()
        upload_btn = QPushButton("upload photo")
        upload_btn.setObjectName("btnOutline")
        upload_btn.setFixedHeight(32)
        upload_btn.clicked.connect(self._on_profile_choose_photo)
        btn_row.addWidget(upload_btn)
        default_btn = QPushButton("set default")
        default_btn.setObjectName("btnOutline")
        default_btn.setFixedHeight(32)
        default_btn.clicked.connect(self._on_profile_reset_photo)
        btn_row.addWidget(default_btn)
        btn_row.addStretch()
        b_lay.addLayout(btn_row)

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
        for btn, _ in self._nav_btns:
            btn.setChecked(False)
        # Hide the sidebar edit icon while on profile page
        if self._edit_icon_lbl is not None:
            self._edit_icon_lbl.setVisible(False)
        self._content_stack.setCurrentIndex(6)

    def _apply_profile_page_glow(self):
        """Apply theme-aware blur glow to the large profile photo frame and name input."""
        if not self._profile_photo_frame:
            return
        # Dark mode → warm golden glow + border  |  Light mode → soft purple glow only
        if self._dark:
            glow_color = QColor("#f5a623")
            glow_hex   = "#f5a623"
            bg         = "#111111"
            border     = f"border: 2px solid {glow_hex};"
        else:
            glow_color = QColor("#7c6fff")
            glow_hex   = "#7c6fff"
            bg         = "#ffffff"
            border     = "border: none;"
        self._profile_photo_frame.setStyleSheet(
            f"#profilePhotoFrame {{ background: {bg}; border-radius: 12px; {border} }}"
        )
        shadow = QGraphicsDropShadowEffect(self._profile_photo_frame)
        shadow.setBlurRadius(65)
        shadow.setOffset(0, 0)
        shadow.setColor(glow_color)
        self._profile_photo_frame.setGraphicsEffect(shadow)
        # Name input: transparent background matching content page, underline only
        if hasattr(self, "_profile_name_edit"):
            txt   = "#ffffff" if self._dark else "#1a1a1a"
            bg_in = "transparent"
            uline = "#555555" if self._dark else "#aaaaaa"
            self._profile_name_edit.setStyleSheet(
                f"QLineEdit#profileNameEdit {{"
                f" background: {bg_in}; color: {txt};"
                f" border: none; border-bottom: 2px solid {uline};"
                f" font-size: 20px; font-weight: 700; padding-bottom: 2px; }}"
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
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Avatar Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if path:
            self._pending_profile["logo_path"] = path
            self._reload_profile_page_photo()
            self._reload_header_logo(path)   # live preview in sidebar

    def _on_profile_reset_photo(self):
        """Reset to factory defaults: name 'Veaja', built-in logo, no custom photo."""
        default_name = "Veaja"
        self._pending_profile["logo_path"] = None
        self._pending_profile["app_name"]  = default_name
        # Must explicitly clear stored path — _reload_header_logo(None) skips updating it
        self._logo_path = None
        # Restore profile page fields
        self._profile_name_edit.setText(default_name)
        self._reload_profile_page_photo()
        # Restore sidebar live preview to factory default
        self._title_label.setText(default_name)
        self._reload_header_logo()   # no arg → picks up self._logo_path = None → default img

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

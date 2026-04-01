"""
Profile editor dialog.
Allows the user to rename "Veaja" and set a custom avatar image.
Changes are only committed when the user clicks Save.
"""

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFileDialog, QFrame
)
# from PyQt6.QtCore import Qt, QSize
from PyQt6.QtCore import Qt, QSize, QRectF
from PyQt6.QtGui import QFont, QPixmap, QPainter, QPainterPath
# from PyQt6.QtGui import QFont, QPixmap, QPainter, QPainterPath, QRectF
from PyQt6.QtGui import QFont, QPixmap, QPainter, QPainterPath
from PyQt6.QtCore import Qt, QRectF

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")


def _load_avatar_pixmap(logo_path: str | None, size: int = 72) -> QPixmap:
    """Load avatar image clipped to a circle."""
    if logo_path and os.path.exists(logo_path):
        raw = QPixmap(logo_path)
    else:
        # Fall back to bundled logo
        fallback = os.path.join(ASSETS, "logo_dark.png")
        raw = QPixmap(fallback) if os.path.exists(fallback) else QPixmap()

    if raw.isNull():
        return raw

    # Scale and clip to circle
    raw = raw.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                     Qt.TransformationMode.SmoothTransformation)
    result = QPixmap(size, size)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addEllipse(QRectF(0, 0, size, size))
    painter.setClipPath(path)
    x = (raw.width()  - size) // 2
    y = (raw.height() - size) // 2
    painter.drawPixmap(-x, -y, raw)
    painter.end()
    return result


class ProfileDialog(QDialog):
    def __init__(self, profile: dict, parent=None):
        super().__init__(parent)
        self._profile = dict(profile)   # working copy
        self.setWindowTitle("Edit Profile")
        self.setMinimumWidth(380)
        self.setModal(True)
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.setContentsMargins(24, 24, 24, 20)

        # Title
        title = QLabel("👤  Edit Profile")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        lay.addWidget(title)

        lay.addWidget(self._divider())

        # ── Avatar ────────────────────────────────────────────────────────────
        avatar_row = QHBoxLayout()

        self._avatar_label = QLabel()
        self._avatar_label.setFixedSize(72, 72)
        self._avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._refresh_avatar()
        avatar_row.addWidget(self._avatar_label)

        avatar_col = QVBoxLayout()
        avatar_col.setSpacing(6)
        change_btn = QPushButton("Choose image…")
        change_btn.setFixedHeight(32)
        change_btn.clicked.connect(self._pick_avatar)
        avatar_col.addWidget(change_btn)

        reset_avatar_btn = QPushButton("Reset to default")
        reset_avatar_btn.setFixedHeight(32)
        reset_avatar_btn.clicked.connect(self._reset_avatar)
        avatar_col.addWidget(reset_avatar_btn)
        avatar_col.addStretch()

        avatar_row.addSpacing(12)
        avatar_row.addLayout(avatar_col)
        avatar_row.addStretch()
        lay.addLayout(avatar_row)

        lay.addWidget(self._divider())

        # ── App name ──────────────────────────────────────────────────────────
        lay.addWidget(QLabel("Display name"))
        self._name_edit = QLineEdit(self._profile.get("app_name", "Veaja"))
        self._name_edit.setPlaceholderText("e.g. My Reader")
        self._name_edit.setMaxLength(64)
        self._name_edit.setFixedHeight(36)
        lay.addWidget(self._name_edit)

        reset_name_btn = QPushButton("Reset name to 'Veaja'")
        reset_name_btn.setFixedHeight(28)
        reset_name_btn.clicked.connect(lambda: self._name_edit.setText("Veaja"))
        lay.addWidget(reset_name_btn)

        lay.addWidget(self._divider())

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(38)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save")
        save_btn.setFixedHeight(38)
        save_btn.setMinimumWidth(100)
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._on_save)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _pick_avatar(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Avatar Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if path:
            self._profile["logo_path"] = path
            self._refresh_avatar()

    def _reset_avatar(self):
        self._profile["logo_path"] = None
        self._refresh_avatar()

    def _on_save(self):
        name = self._name_edit.text().strip()
        self._profile["app_name"] = name if name else "Veaja"
        self.accept()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _refresh_avatar(self):
        px = _load_avatar_pixmap(self._profile.get("logo_path"), size=72)
        if not px.isNull():
            self._avatar_label.setPixmap(px)

    def get_profile(self) -> dict:
        """Return the edited profile dict (call after dialog.exec() == Accepted)."""
        return dict(self._profile)

    @staticmethod
    def _divider() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #3A3A3C;")
        return line

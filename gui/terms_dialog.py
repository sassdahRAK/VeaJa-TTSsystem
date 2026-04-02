"""
Privacy & Terms dialog.
Shown automatically on first launch, and on demand via the 🔒 header button.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class TermsDialog(QDialog):
    def __init__(self, online_mode: bool, parent=None):
        super().__init__(parent)
        self._online = online_mode
        self.setWindowTitle("Privacy & Data Notice")
        self.setMinimumWidth(460)
        self.setModal(True)
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.setContentsMargins(24, 24, 24, 20)

        # Title
        title = QLabel("🔒  Privacy & Data Notice")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        lay.addWidget(title)

        lay.addWidget(self._divider())

        # Mode-specific notice
        if self._online:
            mode_text = (
                "<b>Online mode (Microsoft Edge TTS) is active.</b><br><br>"
                "When you read text, it is sent to <b>Microsoft's servers</b> for "
                "speech synthesis. This is the same service used by Microsoft Edge's "
                "Read Aloud feature. Sensitive, private, or confidential text should "
                "<b>not</b> be read in this mode.<br><br>"
                "Microsoft's privacy policy governs how they handle that data."
            )
            mode_color = "#FF9500"
            mode_icon  = "⚠️"
        else:
            mode_text = (
                "<b>Offline mode (system voices) is active.</b><br><br>"
                "All text-to-speech processing happens <b>entirely on your device</b>. "
                "No text is sent to any server. Your data never leaves your computer."
            )
            mode_color = "#30D158"
            mode_icon  = "✅"

        mode_label = QLabel(f"{mode_icon}  {mode_text}")
        mode_label.setWordWrap(True)
        mode_label.setTextFormat(Qt.TextFormat.RichText)
        mode_label.setStyleSheet(
            f"background: transparent; border-left: 3px solid {mode_color}; "
            f"padding-left: 10px;"
        )
        lay.addWidget(mode_label)

        lay.addWidget(self._divider())

        # General policy
        general = QLabel(
            "📱  <b>About Veaja</b><br><br>"
            "Veaja is a lightweight, serverless desktop tool. It does <b>not</b> "
            "collect, transmit, or store any personal data on third-party servers.<br><br>"
            "• No account required &nbsp;•&nbsp; No analytics &nbsp;•&nbsp; "
            "No telemetry<br>"
            "• Audio history files are stored <b>locally only</b> at "
            "<code>~/.veaja/audio/</code><br>"
            "• You are responsible for the content you choose to read aloud."
        )
        general.setWordWrap(True)
        general.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(general)

        lay.addWidget(self._divider())

        # Don't show again
        self._dont_show_cb = QCheckBox("Don't show this again")
        lay.addWidget(self._dont_show_cb)

        # OK button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("I Understand")
        ok_btn.setFixedHeight(38)
        ok_btn.setMinimumWidth(120)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        lay.addLayout(btn_row)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def dont_show_again(self) -> bool:
        return self._dont_show_cb.isChecked()

    @staticmethod
    def _divider() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #3A3A3C;")
        return line

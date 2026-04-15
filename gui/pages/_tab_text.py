"""gui/pages/_tab_text.py — Text label tab for the Dashboard."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit
)
from PyQt6.QtCore import Qt


class TextTabMixin:
    """Text label tab builder and read/counter logic."""

    def _build_text_tab(self) -> QWidget:
        frame = QWidget()
        frame.setObjectName("tabPage")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 18, 0, 0)
        lay.setSpacing(0)

        text_box = QWidget()
        text_box.setObjectName("textLabelBox")
        tb_lay = QVBoxLayout(text_box)
        tb_lay.setContentsMargins(0, 0, 0, 0)
        tb_lay.setSpacing(0)

        self._text_edit = QTextEdit()
        self._text_edit.setObjectName("textEdit")
        self._text_edit.setPlaceholderText("Paste or type text here to read aloud…")
        self._text_edit.textChanged.connect(self._on_text_changed)
        tb_lay.addWidget(self._text_edit, 1)

        footer = QWidget()
        footer.setObjectName("textFooter")
        ft_lay = QHBoxLayout(footer)
        ft_lay.setContentsMargins(18, 10, 18, 10)
        ft_lay.setSpacing(10)

        self._text_counter = QLabel("0 words · 0 chars")
        self._text_counter.setObjectName("settingsLabel")
        self._text_counter.setStyleSheet("font-size: 12px;")
        ft_lay.addWidget(self._text_counter)
        ft_lay.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("btnOutline")
        clear_btn.setFixedSize(80, 30)
        clear_btn.clicked.connect(self._text_edit.clear)
        ft_lay.addWidget(clear_btn)

        self._read_btn = QPushButton("Read")
        self._read_btn.setObjectName("btnOutline")
        self._read_btn.setFixedSize(80, 30)
        self._read_btn.clicked.connect(self._on_read_clicked)
        ft_lay.addWidget(self._read_btn)

        tb_lay.addWidget(footer)
        lay.addWidget(text_box, 1)
        return frame

    def _on_text_changed(self):
        text  = self._text_edit.toPlainText()
        words = len(text.split()) if text.strip() else 0
        chars = len(text)
        self._text_counter.setText(
            f"{words} word{'s' if words != 1 else ''} · {chars} char{'s' if chars != 1 else ''}"
        )

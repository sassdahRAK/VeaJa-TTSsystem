"""gui/pages/_tab_translate.py — Translate tab for the Dashboard."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QApplication
)
from PyQt6.QtCore import Qt


class TranslateTabMixin:
    """Translate tab builder and translation logic."""

    def _build_translate_tab(self) -> QWidget:
        frame = QWidget()
        frame.setObjectName("tabPage")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 18, 0, 0)
        lay.setSpacing(12)

        # Language selector row
        lang_row = QHBoxLayout()
        lang_row.setContentsMargins(0, 0, 0, 0)
        lang_row.setSpacing(10)

        from_lbl = QLabel("From")
        from_lbl.setObjectName("featureLabel")
        from_lbl.setFixedWidth(36)
        lang_row.addWidget(from_lbl)

        self._translate_from_combo = QComboBox()
        self._translate_from_combo.setObjectName("translateCombo")
        self._translate_from_combo.setFixedHeight(30)
        for lang in ["Auto detect", "English", "Thai", "French", "Spanish",
                     "German", "Japanese", "Chinese", "Korean", "Arabic"]:
            self._translate_from_combo.addItem(lang)
        lang_row.addWidget(self._translate_from_combo)

        arrow = QLabel("→")
        arrow.setObjectName("featureLabel")
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lang_row.addWidget(arrow)

        to_lbl = QLabel("To")
        to_lbl.setObjectName("featureLabel")
        to_lbl.setFixedWidth(20)
        lang_row.addWidget(to_lbl)

        self._translate_to_combo = QComboBox()
        self._translate_to_combo.setObjectName("translateCombo")
        self._translate_to_combo.setFixedHeight(30)
        for lang in ["English", "Thai", "French", "Spanish",
                     "German", "Japanese", "Chinese", "Korean", "Arabic"]:
            self._translate_to_combo.addItem(lang)
        lang_row.addWidget(self._translate_to_combo)
        lang_row.addStretch()

        translate_btn = QPushButton("Translate")
        translate_btn.setObjectName("btnPrimary")
        translate_btn.setFixedSize(100, 30)
        translate_btn.clicked.connect(self._run_translate)
        lang_row.addWidget(translate_btn)
        lay.addLayout(lang_row)

        # Two-panel layout
        panels = QHBoxLayout()
        panels.setContentsMargins(0, 0, 0, 0)
        panels.setSpacing(14)

        # Input panel
        in_box = QWidget()
        in_box.setObjectName("featureBox")
        in_lay = QVBoxLayout(in_box)
        in_lay.setContentsMargins(0, 0, 0, 0)
        in_lay.setSpacing(0)

        in_hdr = QHBoxLayout()
        in_hdr.setContentsMargins(0, 0, 0, 6)
        in_lbl = QLabel("Source text")
        in_lbl.setObjectName("featureLabel")
        in_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        in_hdr.addWidget(in_lbl)
        in_hdr.addStretch()
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("btnOutline")
        clear_btn.setFixedSize(80, 28)
        clear_btn.clicked.connect(self._clear_translate)
        in_hdr.addWidget(clear_btn)
        in_lay.addLayout(in_hdr)

        self._translate_input = QTextEdit()
        self._translate_input.setObjectName("featureEdit")
        self._translate_input.setPlaceholderText("Paste or type text to translate…")
        in_lay.addWidget(self._translate_input, 1)

        self._translate_counter = QLabel("0 chars")
        self._translate_counter.setObjectName("settingsLabel")
        self._translate_counter.setStyleSheet("font-size: 11px;")
        self._translate_counter.setAlignment(Qt.AlignmentFlag.AlignRight)
        in_lay.addWidget(self._translate_counter)
        self._translate_input.textChanged.connect(self._on_translate_input_changed)

        read_orig_btn = QPushButton("▶  Read original")
        read_orig_btn.setObjectName("btnOutline")
        read_orig_btn.setFixedHeight(30)
        read_orig_btn.clicked.connect(self._read_original)
        in_lay.addSpacing(6)
        in_lay.addWidget(read_orig_btn)
        panels.addWidget(in_box, 1)

        # Output panel
        out_box = QWidget()
        out_box.setObjectName("featureBox")
        out_lay = QVBoxLayout(out_box)
        out_lay.setContentsMargins(0, 0, 0, 0)
        out_lay.setSpacing(0)

        out_hdr = QHBoxLayout()
        out_hdr.setContentsMargins(0, 0, 0, 6)
        out_lbl = QLabel("Translation")
        out_lbl.setObjectName("featureLabel")
        out_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        out_hdr.addWidget(out_lbl)
        out_hdr.addStretch()
        copy_btn = QPushButton("Copy")
        copy_btn.setObjectName("btnOutline")
        copy_btn.setFixedSize(80, 28)
        copy_btn.clicked.connect(self._copy_translation)
        out_hdr.addWidget(copy_btn)
        out_lay.addLayout(out_hdr)

        self._translate_output = QTextEdit()
        self._translate_output.setObjectName("featureEditReadOnly")
        self._translate_output.setReadOnly(True)
        self._translate_output.setPlaceholderText("Translation will appear here…")
        out_lay.addWidget(self._translate_output, 1)

        note = QLabel("Translation requires an internet connection and API key.")
        note.setObjectName("settingsLabel")
        note.setStyleSheet("font-size: 11px;")
        note.setAlignment(Qt.AlignmentFlag.AlignRight)
        out_lay.addWidget(note)

        read_trans_btn = QPushButton("▶  Read translation")
        read_trans_btn.setObjectName("btnPrimary")
        read_trans_btn.setFixedHeight(30)
        read_trans_btn.clicked.connect(self._read_translation)
        out_lay.addSpacing(6)
        out_lay.addWidget(read_trans_btn)
        panels.addWidget(out_box, 1)

        lay.addLayout(panels, 1)
        return frame

    def _on_translate_input_changed(self):
        chars = len(self._translate_input.toPlainText())
        self._translate_counter.setText(f"{chars} char{'s' if chars != 1 else ''}")

    def _clear_translate(self):
        self._translate_input.clear()
        self._translate_output.clear()

    def _copy_translation(self):
        text = self._translate_output.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def _read_original(self):
        text = self._translate_input.toPlainText().strip()
        if text:
            self.read_requested.emit(text)

    def _read_translation(self):
        text = self._translate_output.toPlainText().strip()
        if text:
            self.read_requested.emit(text)

    def _run_translate(self):
        text = self._translate_input.toPlainText().strip()
        if not text:
            return
        from_lang = self._translate_from_combo.currentText()
        to_lang   = self._translate_to_combo.currentText()
        self._translate_output.setPlainText(
            f"[Translation from {from_lang} → {to_lang}]\n\n"
            "Connect a translation API (e.g. Google Translate, DeepL, or LibreTranslate) "
            "to enable live translation. The input text has been received and is ready to send."
        )

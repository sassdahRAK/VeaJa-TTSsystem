"""gui/pages/_tab_translate.py — Translate tab for the Dashboard."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QApplication
)
from gui._window_shared import scaled  # noqa: F401
from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal
from gui.pages._ai_caller import call_ai, get_api_keys, best_provider


# ── Background workers ────────────────────────────────────────────────────────

class _TrSignals(QObject):
    finished = pyqtSignal(str)

class _TrThread(QThread):
    def __init__(self, prompt, system, mixin, signals):
        super().__init__()
        self._prompt  = prompt
        self._system  = system
        self._mixin   = mixin
        self._signals = signals

    def run(self):
        result = call_ai("ask", self._prompt, self._mixin, self._system)
        self._signals.finished.emit(result)


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
        lang_row.setSpacing(8)

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

        # Swap button with SVG icon — horizontal swap arrows, theme-aware
        swap_btn = QPushButton()
        swap_btn.setObjectName("btnOutline")
        swap_btn.setFixedSize(32, 30)
        swap_btn.setToolTip("Swap languages")
        swap_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._tr_swap_btn = swap_btn   # keep ref so theme changes can re-render the icon
        self._tr_swap_svg = (
            '<path d="M4 8h13M4 8l3-3M4 8l3 3" stroke="currentColor" stroke-width="1.7" '
            'stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
            '<path d="M20 16H7m13 0l-3-3m3 3l-3 3" stroke="currentColor" stroke-width="1.7" '
            'stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
        )
        swap_btn.setIcon(self._tr_svg_icon(self._tr_swap_svg))
        from PyQt6.QtCore import QSize
        swap_btn.setIconSize(QSize(16, 16))
        swap_btn.clicked.connect(self._swap_translate_langs)
        lang_row.addWidget(swap_btn)

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

        # Translate button — right next to the "To" combo, no stretch before it
        translate_btn = QPushButton("Translate")
        translate_btn.setObjectName("btnPrimary")
        translate_btn.setFixedHeight(30)
        translate_btn.setMinimumWidth(100)
        translate_btn.clicked.connect(self._run_translate)
        lang_row.addWidget(translate_btn)
        self._translate_btn = translate_btn

        lang_row.addStretch()
        lay.addLayout(lang_row)
        lay.addSpacing(10)  # breathing room between selector and panels

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
        copy_btn.setFixedHeight(28)
        copy_btn.setMinimumWidth(70)
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

        # ── Follow-up Q&A panel ───────────────────────────────────────────
        self._tr_followup_box = QWidget()
        self._tr_followup_box.setObjectName("featureBox")
        self._tr_followup_box.setVisible(False)
        fq_lay = QVBoxLayout(self._tr_followup_box)
        fq_lay.setContentsMargins(0, 8, 0, 0)
        fq_lay.setSpacing(6)

        fq_hdr = QHBoxLayout()
        fq_hdr.setContentsMargins(0, 0, 0, 0)
        fq_icon = QLabel("💬")
        fq_icon.setStyleSheet("font-size: 14px; background: transparent;")
        fq_hdr.addWidget(fq_icon)
        fq_title = QLabel("Ask about a word or concept in the translation:")
        fq_title.setObjectName("featureLabel")
        fq_title.setStyleSheet("color: #e53935;")
        fq_hdr.addWidget(fq_title)
        fq_hdr.addStretch()
        fq_lay.addLayout(fq_hdr)

        fq_hint = QLabel(
            "e.g.  What does 'API' mean?  ·  Explain 'machine learning' in simple terms  ·  What is the context of this word?"
        )
        fq_hint.setObjectName("settingsLabel")
        fq_hint.setStyleSheet("font-size: 10px; font-style: italic;")
        fq_hint.setWordWrap(True)
        fq_lay.addWidget(fq_hint)

        fq_input_row = QHBoxLayout()
        fq_input_row.setSpacing(8)
        self._tr_followup_input = QTextEdit()
        self._tr_followup_input.setObjectName("featureEdit")
        self._tr_followup_input.setPlaceholderText(
            "Ask anything about the translated text… e.g. What is API? What does this term mean?"
        )
        self._tr_followup_input.setFixedHeight(56)
        fq_input_row.addWidget(self._tr_followup_input, 1)

        ask_btn = QPushButton("Ask")
        ask_btn.setObjectName("btnPrimary")
        ask_btn.setFixedSize(70, 56)
        ask_btn.clicked.connect(self._run_tr_followup)
        fq_input_row.addWidget(ask_btn)
        fq_lay.addLayout(fq_input_row)

        self._tr_followup_answer = QTextEdit()
        self._tr_followup_answer.setObjectName("featureEditReadOnly")
        self._tr_followup_answer.setReadOnly(True)
        self._tr_followup_answer.setPlaceholderText("Answer will appear here…")
        self._tr_followup_answer.setMinimumHeight(80)
        self._tr_followup_answer.setVisible(False)
        fq_lay.addWidget(self._tr_followup_answer)

        lay.addWidget(self._tr_followup_box)
        return frame

    def _tr_svg_icon(self, svg_body: str, size: int = 16):
        """Render an SVG path to a QIcon, theme-aware."""
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtGui import QPixmap, QPainter, QIcon, QColor
        from PyQt6.QtWidgets import QApplication
        is_dark = getattr(self, "_dark", True)
        color = "#ffffff" if is_dark else "#1a1a1a"
        # Replace currentColor with the actual color value
        svg_colored = svg_body.replace("currentColor", color)
        svg = (
            f'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">'
            f'{svg_colored}'
            f'</svg>'
        ).encode()
        app = QApplication.instance()
        dpr = app.primaryScreen().devicePixelRatio() if app and app.primaryScreen() else 1.0
        phys = int(size * dpr)
        px = QPixmap(phys, phys)
        px.fill(QColor(0, 0, 0, 0))
        renderer = QSvgRenderer(svg)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(p)
        p.end()
        px.setDevicePixelRatio(dpr)
        return QIcon(px)

    def refresh_translate_icons(self):
        """Re-render theme-sensitive icons on the translate tab (called on theme toggle)."""
        if hasattr(self, "_tr_swap_btn") and hasattr(self, "_tr_swap_svg"):
            from PyQt6.QtCore import QSize
            self._tr_swap_btn.setIcon(self._tr_svg_icon(self._tr_swap_svg))
            self._tr_swap_btn.setIconSize(QSize(16, 16))

    def _swap_translate_langs(self):
        """Swap From and To language selections, and swap the text content."""
        from_idx = self._translate_from_combo.currentIndex()
        to_idx   = self._translate_to_combo.currentIndex()
        from_txt = self._translate_from_combo.currentText()
        to_txt   = self._translate_to_combo.currentText()

        # Skip swap if From is "Auto detect"
        if from_txt == "Auto detect":
            return

        # Find matching index in each combo
        new_from = self._translate_to_combo.findText(from_txt)
        new_to   = self._translate_from_combo.findText(to_txt)

        if new_from >= 0:
            self._translate_from_combo.setCurrentIndex(new_from)
        if new_to >= 0:
            self._translate_to_combo.setCurrentIndex(new_to)

        # Also swap the text content between panels
        src = self._translate_input.toPlainText()
        out = self._translate_output.toPlainText()
        if out.strip() and not out.startswith("[Translation"):
            self._translate_input.setPlainText(out)
            self._translate_output.setPlainText(src)

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

        keys = get_api_keys(self)
        provider_result = best_provider("ask", keys)

        if not provider_result:
            self._translate_output.setPlainText(
                f"[Translation from {from_lang} → {to_lang}]\n\n"
                "No AI API key found.\n\n"
                "Go to  My API Key  in the sidebar to add an OpenAI, Gemini, or Claude key.\n"
                "Translation will work immediately once a key is saved."
            )
            if hasattr(self, "_tr_followup_box"):
                self._tr_followup_box.setVisible(False)
            return

        # Disable button while translating
        if hasattr(self, "_translate_btn"):
            self._translate_btn.setEnabled(False)
            self._translate_btn.setText("Translating…")
        self._translate_output.setPlainText("Translating…")

        src = "the source language" if from_lang == "Auto detect" else from_lang
        system = (
            "You are a professional translator. "
            "Translate the given text accurately, preserving tone, style, and meaning. "
            "Output only the translated text — no explanations, no notes, no labels."
        )
        prompt = f"Translate the following text from {src} to {to_lang}:\n\n{text}"

        signals = _TrSignals()
        signals.finished.connect(self._on_translate_finished)
        self._tr_thread = _TrThread(prompt, system, self, signals)
        self._tr_thread.start()

    def _on_translate_finished(self, result: str):
        if hasattr(self, "_translate_btn"):
            self._translate_btn.setEnabled(True)
            self._translate_btn.setText("Translate")
        self._translate_output.setPlainText(result)
        if hasattr(self, "_tr_followup_box"):
            self._tr_followup_box.setVisible(True)
            self._tr_followup_answer.setVisible(False)

    def _run_tr_followup(self):
        """Answer a follow-up question about the translated text using AI."""
        question = self._tr_followup_input.toPlainText().strip()
        src_text  = self._translate_input.toPlainText().strip()
        tr_text   = self._translate_output.toPlainText().strip()
        if not question:
            return

        # Try local dictionary first for quick common lookups
        local = self._tr_local_explain(question, src_text)
        if local:
            self._tr_followup_answer.setPlainText(local)
            self._tr_followup_answer.setVisible(True)
            return

        keys = get_api_keys(self)
        provider_result = best_provider("ask", keys)

        if not provider_result:
            self._tr_followup_answer.setPlainText(
                f"[Q: {question}]\n\n"
                "Connect an AI API key (OpenAI, Gemini, or Claude) in My API Key "
                "to get a real explanation of this term or concept."
            )
            self._tr_followup_answer.setVisible(True)
            return

        self._tr_followup_answer.setPlainText("Thinking…")
        self._tr_followup_answer.setVisible(True)

        system = (
            "You are a helpful language assistant. "
            "Answer questions about translations, word meanings, grammar, and cultural context. "
            "Be concise and clear."
        )
        context_snippet = src_text[:300] + ("…" if len(src_text) > 300 else "")
        tr_snippet      = tr_text[:300]  + ("…" if len(tr_text)  > 300 else "")
        prompt = (
            f"Original text: \"{context_snippet}\"\n"
            f"Translation: \"{tr_snippet}\"\n\n"
            f"Question: {question}"
        )

        signals = _TrSignals()
        signals.finished.connect(lambda r: (
            self._tr_followup_answer.setPlainText(r),
            self._tr_followup_answer.setVisible(True),
        ))
        self._tr_followup_thread = _TrThread(prompt, system, self, signals)
        self._tr_followup_thread.start()

    def _tr_local_explain(self, question: str, context: str) -> str:
        """
        Simple local dictionary for common technical / academic terms.
        Returns an explanation if the question matches a known term.
        """
        q = question.lower().strip().rstrip("?").strip()
        # Strip "what is", "what does", "explain", "define" prefixes
        for prefix in ("what is ", "what does ", "what are ", "explain ", "define ",
                       "what is an ", "what is a ", "tell me about "):
            if q.startswith(prefix):
                q = q[len(prefix):].strip()
                break

        _DICT = {
            "api": (
                "API (Application Programming Interface) is a set of rules and protocols "
                "that allows different software applications to communicate with each other. "
                "Think of it as a waiter in a restaurant — you (the app) tell the waiter (API) "
                "what you want, and the waiter brings it from the kitchen (the server)."
            ),
            "machine learning": (
                "Machine Learning (ML) is a branch of AI where computers learn from data "
                "without being explicitly programmed. Instead of following fixed rules, "
                "the system finds patterns in examples and improves over time."
            ),
            "algorithm": (
                "An algorithm is a step-by-step set of instructions to solve a problem or "
                "complete a task. Like a recipe — it tells the computer exactly what to do "
                "and in what order."
            ),
            "database": (
                "A database is an organised collection of structured data stored electronically. "
                "It allows data to be easily accessed, managed, and updated. "
                "Examples: MySQL, PostgreSQL, MongoDB."
            ),
            "cloud": (
                "Cloud computing means storing and accessing data and programs over the internet "
                "instead of on your local computer. Examples: AWS, Google Cloud, Azure."
            ),
            "encryption": (
                "Encryption is the process of converting readable data into an unreadable format "
                "to protect it from unauthorised access. Only someone with the correct key can "
                "decrypt and read the original data."
            ),
            "protocol": (
                "A protocol is a set of rules that defines how data is transmitted between devices. "
                "Examples: HTTP (web), SMTP (email), TCP/IP (internet communication)."
            ),
            "framework": (
                "A framework is a pre-built structure of code that developers use as a foundation "
                "to build applications. It provides common tools and patterns so you don't start "
                "from scratch. Examples: React, Django, Flutter."
            ),
            "sdk": (
                "SDK (Software Development Kit) is a collection of tools, libraries, and documentation "
                "that developers use to build applications for a specific platform or service."
            ),
            "ui": (
                "UI (User Interface) is everything the user sees and interacts with on screen — "
                "buttons, menus, text fields, icons. Good UI makes software easy and pleasant to use."
            ),
            "ux": (
                "UX (User Experience) is the overall feeling a user has when using a product. "
                "It covers usability, accessibility, and how satisfying the interaction is."
            ),
        }

        # Try exact match first, then partial
        if q in _DICT:
            return f"📖 {q.upper()}\n\n{_DICT[q]}"
        for key, val in _DICT.items():
            if key in q or q in key:
                return f"📖 {key.upper()}\n\n{val}"
        return ""

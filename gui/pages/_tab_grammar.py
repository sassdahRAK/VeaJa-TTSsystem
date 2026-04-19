"""gui/pages/_tab_grammar.py — Grammar tab for the Dashboard."""

import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QScrollArea, QFrame, QStackedWidget
)
from gui._window_shared import scaled  # noqa: F401
from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal
from gui.pages._ai_caller import call_ai, get_api_keys, best_provider


# ── Background worker ─────────────────────────────────────────────────────────

class _GramSignals(QObject):
    finished = pyqtSignal(str)

class _GramThread(QThread):
    def __init__(self, prompt, system, mixin, signals):
        super().__init__()
        self._prompt  = prompt
        self._system  = system
        self._mixin   = mixin
        self._signals = signals

    def run(self):
        result = call_ai("grammar", self._prompt, self._mixin, self._system)
        self._signals.finished.emit(result)


class GrammarTabMixin:
    """Grammar tab — check, correct and explain grammar issues."""

    def _build_grammar_tab(self) -> QWidget:
        frame = QWidget()
        frame.setObjectName("tabPage")
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Sticky sub-tab bar ────────────────────────────────────────────
        sub_bar = QWidget()
        sub_bar.setObjectName("subTabBar")
        sub_bar.setAutoFillBackground(True)
        sb_lay = QHBoxLayout(sub_bar)
        sb_lay.setContentsMargins(0, 8, 0, 0)
        sb_lay.setSpacing(0)

        self._gram_check_btn = QPushButton("Check")
        self._gram_check_btn.setObjectName("subTabBtn")
        self._gram_check_btn.setCheckable(True)
        self._gram_check_btn.setChecked(True)
        self._gram_check_btn.setFixedHeight(30)
        self._gram_check_btn.clicked.connect(lambda: self._gram_switch(0))

        self._gram_rewrite_btn = QPushButton("Rewrite")
        self._gram_rewrite_btn.setObjectName("subTabBtn")
        self._gram_rewrite_btn.setCheckable(True)
        self._gram_rewrite_btn.setChecked(False)
        self._gram_rewrite_btn.setFixedHeight(30)
        self._gram_rewrite_btn.clicked.connect(lambda: self._gram_switch(1))

        self._gram_explain_btn = QPushButton("Explain")
        self._gram_explain_btn.setObjectName("subTabBtn")
        self._gram_explain_btn.setCheckable(True)
        self._gram_explain_btn.setChecked(False)
        self._gram_explain_btn.setFixedHeight(30)
        self._gram_explain_btn.clicked.connect(lambda: self._gram_switch(2))

        sb_lay.addWidget(self._gram_check_btn)
        sb_lay.addWidget(self._gram_rewrite_btn)
        sb_lay.addWidget(self._gram_explain_btn)
        sb_lay.addStretch()
        outer.addWidget(sub_bar)

        # ── Scrollable content ────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("settingsScroll")
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        inner = QWidget()
        inner.setObjectName("tabPage")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(0, 10, 0, 18)
        lay.setSpacing(10)

        # Input
        in_hdr = QHBoxLayout()
        in_hdr.setContentsMargins(0, 0, 0, 4)
        in_lbl = QLabel("Text to check")
        in_lbl.setObjectName("featureLabel")
        in_hdr.addWidget(in_lbl)
        in_hdr.addStretch()
        clear_gram_btn = QPushButton("Clear")
        clear_gram_btn.setObjectName("btnOutline")
        clear_gram_btn.setFixedSize(70, 26)
        clear_gram_btn.clicked.connect(self._gram_clear)
        in_hdr.addWidget(clear_gram_btn)
        lay.addLayout(in_hdr)

        self._gram_input = QTextEdit()
        self._gram_input.setObjectName("featureEdit")
        self._gram_input.setPlaceholderText("Paste or type text to check grammar…")
        self._gram_input.setFixedHeight(130)
        lay.addWidget(self._gram_input)

        # Action row
        act_row = QHBoxLayout()
        act_row.setContentsMargins(0, 0, 0, 0)
        act_row.setSpacing(10)
        act_row.addStretch()
        self._gram_run_btn = QPushButton("Check Grammar")
        self._gram_run_btn.setObjectName("btnPrimary")
        self._gram_run_btn.setFixedHeight(32)
        self._gram_run_btn.clicked.connect(self._gram_run)
        act_row.addWidget(self._gram_run_btn)
        lay.addLayout(act_row)

        # Output stack
        self._gram_stack = QStackedWidget()

        # ── Check output ──────────────────────────────────────────────────
        check_box = QWidget()
        check_box.setObjectName("featureBox")
        ch_lay = QVBoxLayout(check_box)
        ch_lay.setContentsMargins(0, 0, 0, 0)
        ch_lay.setSpacing(6)
        ch_lay.addWidget(QLabel("Issues found", objectName="featureLabel"))
        self._gram_issues_out = QTextEdit()
        self._gram_issues_out.setObjectName("featureEditReadOnly")
        self._gram_issues_out.setReadOnly(True)
        self._gram_issues_out.setMinimumHeight(140)
        self._gram_issues_out.setPlaceholderText("Grammar issues will appear here…")
        ch_lay.addWidget(self._gram_issues_out)
        self._gram_stack.addWidget(check_box)

        # ── Rewrite output ────────────────────────────────────────────────
        rewrite_box = QWidget()
        rewrite_box.setObjectName("featureBox")
        rw_lay = QVBoxLayout(rewrite_box)
        rw_lay.setContentsMargins(0, 0, 0, 0)
        rw_lay.setSpacing(6)
        rw_hdr = QHBoxLayout()
        rw_hdr.addWidget(QLabel("Corrected text", objectName="featureLabel"))
        rw_hdr.addStretch()
        copy_rw_btn = QPushButton("Copy")
        copy_rw_btn.setObjectName("btnOutline")
        copy_rw_btn.setFixedSize(70, 26)
        copy_rw_btn.clicked.connect(self._gram_copy_rewrite)
        rw_hdr.addWidget(copy_rw_btn)
        rw_lay.addLayout(rw_hdr)
        self._gram_rewrite_out = QTextEdit()
        self._gram_rewrite_out.setObjectName("featureEditReadOnly")
        self._gram_rewrite_out.setReadOnly(True)
        self._gram_rewrite_out.setMinimumHeight(140)
        self._gram_rewrite_out.setPlaceholderText("Corrected version will appear here…")
        rw_lay.addWidget(self._gram_rewrite_out)
        self._gram_stack.addWidget(rewrite_box)

        # ── Explain output ────────────────────────────────────────────────
        explain_box = QWidget()
        explain_box.setObjectName("featureBox")
        ex_lay = QVBoxLayout(explain_box)
        ex_lay.setContentsMargins(0, 0, 0, 0)
        ex_lay.setSpacing(6)
        ex_lay.addWidget(QLabel("Grammar explanation", objectName="featureLabel"))
        self._gram_explain_out = QTextEdit()
        self._gram_explain_out.setObjectName("featureEditReadOnly")
        self._gram_explain_out.setReadOnly(True)
        self._gram_explain_out.setMinimumHeight(140)
        self._gram_explain_out.setPlaceholderText("Explanation will appear here…")
        ex_lay.addWidget(self._gram_explain_out)
        self._gram_stack.addWidget(explain_box)

        lay.addWidget(self._gram_stack)
        lay.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)
        return frame

    # ── Grammar logic ─────────────────────────────────────────────────────────

    def _gram_switch(self, idx: int):
        self._gram_check_btn.setChecked(idx == 0)
        self._gram_rewrite_btn.setChecked(idx == 1)
        self._gram_explain_btn.setChecked(idx == 2)
        self._gram_stack.setCurrentIndex(idx)
        labels = ["Check Grammar", "Rewrite", "Explain"]
        self._gram_run_btn.setText(labels[idx])

    def _gram_clear(self):
        self._gram_input.clear()
        self._gram_issues_out.clear()
        self._gram_rewrite_out.clear()
        self._gram_explain_out.clear()

    def _gram_copy_rewrite(self):
        from PyQt6.QtWidgets import QApplication
        text = self._gram_rewrite_out.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def _gram_run(self):
        text = self._gram_input.toPlainText().strip()
        if not text:
            return
        mode = self._gram_stack.currentIndex()

        keys = get_api_keys(self)
        provider_result = best_provider("grammar", keys)

        if provider_result:
            provider, _ = provider_result
            self._gram_run_btn.setEnabled(False)
            self._gram_run_btn.setText("Thinking…")

            systems = {
                0: (
                    "You are a professional grammar checker. "
                    "List every grammar, spelling, punctuation, and style issue found. "
                    "For each issue: show the original text, the problem, and the fix. "
                    "Use this format:\n• Issue: [original] → Fix: [corrected] — Reason: [why]"
                ),
                1: (
                    "You are a professional editor. "
                    "Rewrite the given text to fix all grammar, spelling, and style issues. "
                    "Preserve the original meaning and tone. "
                    "Return only the corrected text, no explanations."
                ),
                2: (
                    "You are an English grammar teacher. "
                    "Explain the grammar rules relevant to the given text. "
                    "Cover tense, subject-verb agreement, punctuation, and style. "
                    "Be educational and clear."
                ),
            }
            system = systems[mode]
            prompts = {
                0: f"Check this text for grammar issues:\n\n{text}",
                1: f"Rewrite this text with all grammar issues fixed:\n\n{text}",
                2: f"Explain the grammar rules in this text:\n\n{text}",
            }
            prompt = prompts[mode]

            signals = _GramSignals()
            signals.finished.connect(lambda r: self._gram_on_finished(r, mode))
            self._gram_thread = _GramThread(prompt, system, self, signals)
            self._gram_thread.start()
        else:
            # Fallback: basic local check
            if mode == 0:
                issues = self._basic_grammar_check(text)
                self._gram_issues_out.setPlainText(
                    issues if issues else
                    "✓ No obvious issues found.\n\n"
                    "Add an OpenAI, Claude, or Gemini key in My API Key for deep AI analysis."
                )
            elif mode == 1:
                self._gram_rewrite_out.setPlainText(
                    f"[Rewritten version]\n\n{text}\n\n"
                    "— Add an AI API key in My API Key for real grammar correction."
                )
            else:
                self._gram_explain_out.setPlainText(
                    "— Add an AI API key in My API Key for grammar explanations."
                )

    def _gram_on_finished(self, result: str, mode: int):
        self._gram_run_btn.setEnabled(True)
        labels = ["Check Grammar", "Rewrite", "Explain"]
        self._gram_run_btn.setText(labels[mode])
        if mode == 0:
            self._gram_issues_out.setPlainText(result)
        elif mode == 1:
            self._gram_rewrite_out.setPlainText(result)
        else:
            self._gram_explain_out.setPlainText(result)

    def _basic_grammar_check(self, text: str) -> str:
        """Simple rule-based checks — no external deps."""
        issues = []
        sentences = [s.strip() for s in re.split(r'[.!?]', text) if s.strip()]

        for i, s in enumerate(sentences, 1):
            # Double spaces
            if "  " in s:
                issues.append(f"Line {i}: Double space detected.")
            # Starts with lowercase (after first)
            if i > 1 and s and s[0].islower():
                issues.append(f"Line {i}: Sentence may not start with lowercase — '{s[:30]}…'")
            # Common mistakes
            for wrong, right in [
                ("i ", "I "), ("dont", "don't"), ("cant", "can't"),
                ("wont", "won't"), ("its a", "it's a"), ("your welcome", "you're welcome"),
                ("alot", "a lot"), ("definately", "definitely"), ("recieve", "receive"),
            ]:
                if wrong in s.lower():
                    issues.append(f"Line {i}: Consider '{right}' instead of '{wrong}'.")

        return "\n".join(issues) if issues else ""

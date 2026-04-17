"""gui/pages/_tab_ask.py — Ask tab for the Dashboard."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QScrollArea, QFrame
)
from gui._window_shared import scaled  # noqa: F401
from PyQt6.QtCore import Qt, QTimer


class AskTabMixin:
    """Ask tab — conversational Q&A with context."""

    def _build_ask_tab(self) -> QWidget:
        frame = QWidget()
        frame.setObjectName("tabPage")
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(0, 18, 0, 0)
        outer.setSpacing(0)

        # ── Chat history area ─────────────────────────────────────────────
        self._ask_scroll = QScrollArea()
        self._ask_scroll.setWidgetResizable(True)
        self._ask_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._ask_scroll.setObjectName("settingsScroll")
        self._ask_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._ask_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._ask_chat_widget = QWidget()
        self._ask_chat_widget.setObjectName("tabPage")
        self._ask_chat_lay = QVBoxLayout(self._ask_chat_widget)
        self._ask_chat_lay.setContentsMargins(0, 0, 0, 8)
        self._ask_chat_lay.setSpacing(10)
        self._ask_chat_lay.addStretch()

        self._ask_scroll.setWidget(self._ask_chat_widget)
        outer.addWidget(self._ask_scroll, 1)

        # ── Input bar ─────────────────────────────────────────────────────
        input_bar = QWidget()
        input_bar.setObjectName("textFooter")
        ib_lay = QHBoxLayout(input_bar)
        ib_lay.setContentsMargins(0, 8, 0, 0)
        ib_lay.setSpacing(8)

        self._ask_input = QTextEdit()
        self._ask_input.setObjectName("featureEdit")
        self._ask_input.setPlaceholderText("Ask anything… e.g. What does this code do? Explain this concept.")
        self._ask_input.setFixedHeight(64)
        ib_lay.addWidget(self._ask_input, 1)

        btn_col = QVBoxLayout()
        btn_col.setSpacing(4)

        send_btn = QPushButton("Ask")
        send_btn.setObjectName("btnPrimary")
        send_btn.setFixedSize(70, 30)
        send_btn.clicked.connect(self._ask_send)
        btn_col.addWidget(send_btn)

        clear_ask_btn = QPushButton("Clear")
        clear_ask_btn.setObjectName("btnOutline")
        clear_ask_btn.setFixedSize(70, 28)
        clear_ask_btn.clicked.connect(self._ask_clear)
        btn_col.addWidget(clear_ask_btn)

        ib_lay.addLayout(btn_col)
        outer.addWidget(input_bar)
        return frame

    # ── Ask logic ─────────────────────────────────────────────────────────────

    def _ask_send(self):
        question = self._ask_input.toPlainText().strip()
        if not question:
            return
        self._ask_input.clear()
        self._ask_add_bubble(question, is_user=True)
        # Placeholder answer — replace with real API call when key is connected
        QTimer.singleShot(300, lambda: self._ask_add_bubble(
            f"[Answer to: {question[:60]}{'…' if len(question)>60 else ''}]\n\n"
            "Connect an AI API key (OpenAI, Gemini, or Claude) in My API Key "
            "to get a real answer.",
            is_user=False
        ))

    def _ask_add_bubble(self, text: str, is_user: bool):
        bubble = QWidget()
        bubble.setObjectName("askBubbleUser" if is_user else "askBubbleAI")
        b_lay = QHBoxLayout(bubble)
        b_lay.setContentsMargins(0, 0, 0, 0)
        b_lay.setSpacing(0)

        lbl = QLabel(text)
        lbl.setObjectName("askBubbleUserText" if is_user else "askBubbleAIText")
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        if is_user:
            b_lay.addStretch()
            b_lay.addWidget(lbl)
        else:
            b_lay.addWidget(lbl)
            b_lay.addStretch()

        # Insert before the stretch at the end
        self._ask_chat_lay.insertWidget(self._ask_chat_lay.count() - 1, bubble)
        # Scroll to bottom
        QTimer.singleShot(50, lambda: self._ask_scroll.verticalScrollBar().setValue(
            self._ask_scroll.verticalScrollBar().maximum()
        ))

    def _ask_clear(self):
        while self._ask_chat_lay.count() > 1:
            item = self._ask_chat_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

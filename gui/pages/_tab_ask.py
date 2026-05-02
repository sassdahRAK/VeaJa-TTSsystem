"""gui/pages/_tab_ask.py — Ask tab for the Dashboard."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QThread, QObject, pyqtSignal
from gui.pages._flow_layout import FlowLayout as _FlowLayout
from gui.pages._ai_caller import call_ai

# ── Background AI worker ──────────────────────────────────────────────────────

class _AskSignals(QObject):
    finished = pyqtSignal(str)

class _AskThread(QThread):
    def __init__(self, task, prompt, mixin, system, signals):
        super().__init__()
        self._task = task
        self._prompt = prompt
        self._system = system
        self._mixin = mixin
        self._signals = signals

    def run(self):
        result = call_ai(self._task, self._prompt, self._mixin, self._system)
        self._signals.finished.emit(result)


# ── Topic categories ──────────────────────────────────────────────────────────
# (label, emoji, placeholder question hint)
_TOPICS = [
    ("General",            "💬", "Ask anything…"),
    ("Zodiac & Astrology",  "♈", "What does my zodiac sign say about me?"),
    ("Business",           "💼", "How do I write a business plan?"),
    ("Stock & Finance",    "📈", "What is a P/E ratio?"),
    ("War & History",      "⚔️",  "What caused World War I?"),
    ("Tech Skills",        "🛠️",  "How do I learn Python fast?"),
    ("IT & Software",      "💻", "What is the difference between TCP and UDP?"),
    ("Science",            "🔬", "How does CRISPR work?"),
    ("Political Science",  "🏛️",  "What is democracy?"),
    ("Books & Literature", "📚", "Recommend a book on stoicism."),
    ("Visual Art",         "🎨", "What is the golden ratio in art?"),
    ("Music & Artists",    "🎵", "Who invented jazz?"),
    ("Health & Medicine",  "🏥", "What are the symptoms of diabetes?"),
    ("Exercise & Fitness", "🏋️",  "What is the best workout for beginners?"),
    ("Talent & Skills",    "🌟", "How do I improve my public speaking?"),
    ("Meditation",         "🧘", "How do I start meditating?"),
    ("Deep Emotional",     "💙", "How do I deal with grief?"),
    ("Anime & Manga",      "🎌", "What is the best anime for beginners?"),
    ("Movies & TV",        "🎬", "What makes a great screenplay?"),
    ("Social & Culture",   "🌍", "What is cultural appropriation?"),
    ("Ethics & Philosophy","⚖️",  "What is utilitarianism?"),
    ("Food & Cooking",     "🍜", "How do I make a roux?"),
    ("Temple & Religion",  "🛕", "What are the five pillars of Islam?"),
    ("Historical Events",  "📜", "What was the Renaissance?"),
    ("Blockchain",         "⛓️",  "How does a blockchain work?"),
    ("Crypto & Web3",      "₿",  "What is DeFi?"),
    ("AI & Machine Learning","🤖","What is a neural network?"),
    ("Space & Astronomy",  "🚀", "How far is the nearest star?"),
    ("Environment",        "🌱", "What causes climate change?"),
    ("Law & Legal",        "⚖️",  "What is habeas corpus?"),
    ("Psychology",         "🧠", "What is cognitive dissonance?"),
    ("Language & Linguistics","🗣️","How many languages are there?"),
    ("Travel & Geography", "✈️",  "What is the smallest country?"),
    ("Sports",             "⚽", "How does the offside rule work?"),
    ("Gaming",             "🎮", "What is a roguelike game?"),
    ("Fashion & Style",    "👗", "What is the capsule wardrobe?"),
    ("Architecture",       "🏛️",  "What is Bauhaus design?"),
    ("Mathematics",        "∑",  "What is Euler's identity?"),
    ("Chemistry",          "⚗️",  "What is a covalent bond?"),
    ("Biology",            "🧬", "What is mitosis?"),
    ("Physics",            "⚛️",  "What is quantum entanglement?"),
]


class AskTabMixin:
    """Ask tab — conversational Q&A with topic categories."""

    def _build_ask_tab(self) -> QWidget:
        frame = QWidget()
        frame.setObjectName("tabPage")
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(0, 10, 0, 0)
        outer.setSpacing(0)

        # ── Sticky topic bar ──────────────────────────────────────────────
        topic_bar = QWidget()
        topic_bar.setObjectName("subTabBar")
        topic_bar.setAutoFillBackground(True)
        tb_outer = QVBoxLayout(topic_bar)
        tb_outer.setContentsMargins(0, 0, 0, 6)
        tb_outer.setSpacing(4)

        topic_hdr = QLabel("Topic:")
        topic_hdr.setObjectName("featureLabel")
        topic_hdr.setStyleSheet("font-size: 10px;")
        tb_outer.addWidget(topic_hdr)

        # Scrollable topic pills
        topic_scroll = QScrollArea()
        topic_scroll.setWidgetResizable(True)
        topic_scroll.setFrameShape(QFrame.Shape.NoFrame)
        topic_scroll.setFixedHeight(130)
        topic_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        topic_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        topic_scroll.setStyleSheet("background: transparent; border: none;")

        topic_inner = QWidget()
        topic_inner.setStyleSheet("background: transparent;")
        topic_flow = _FlowLayout(topic_inner, h_spacing=5, v_spacing=5)
        topic_flow.setContentsMargins(0, 0, 0, 0)

        self._ask_topic = "General"
        self._ask_topic_btns: list[QPushButton] = []

        for label, emoji, _ in _TOPICS:
            btn = QPushButton(f"{emoji} {label}")
            btn.setObjectName("profBtn")
            btn.setCheckable(True)
            btn.setChecked(label == "General")
            btn.setFixedHeight(26)
            btn.setMinimumWidth(btn.fontMetrics().horizontalAdvance(f"{emoji} {label}") + 22)
            btn.setStyleSheet(
                "QPushButton#profBtn { font-size: 10px; padding: 2px 8px; }"
                "QPushButton#profBtn:checked { border: 2px solid #e53935; font-weight: 600; }"
            )
            btn.clicked.connect(lambda _=False, l=label, e=emoji: self._ask_set_topic(l, e))
            topic_flow.addWidget(btn)
            self._ask_topic_btns.append(btn)

        topic_scroll.setWidget(topic_inner)
        tb_outer.addWidget(topic_scroll)
        outer.addWidget(topic_bar)

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
        self._ask_input.setPlaceholderText("Ask anything…")
        self._ask_input.setFixedHeight(60)
        ib_lay.addWidget(self._ask_input, 1)

        btn_col = QVBoxLayout()
        btn_col.setSpacing(4)

        send_btn = QPushButton("Ask")
        send_btn.setObjectName("btnPrimary")
        send_btn.setFixedSize(70, 28)
        send_btn.clicked.connect(self._ask_send)
        btn_col.addWidget(send_btn)

        clear_ask_btn = QPushButton("Clear")
        clear_ask_btn.setObjectName("btnOutline")
        clear_ask_btn.setFixedSize(70, 26)
        clear_ask_btn.clicked.connect(self._ask_clear)
        btn_col.addWidget(clear_ask_btn)

        ib_lay.addLayout(btn_col)
        outer.addWidget(input_bar)
        return frame

    # ── Topic selection ───────────────────────────────────────────────────────

    def _ask_set_topic(self, label: str, emoji: str):
        self._ask_topic = label
        for btn in self._ask_topic_btns:
            btn_label = btn.text().split(" ", 1)[-1] if " " in btn.text() else btn.text()
            btn.setChecked(btn_label == label)
        # Update placeholder with a hint for this topic
        hint = next((h for l, e, h in _TOPICS if l == label), "Ask anything…")
        self._ask_input.setPlaceholderText(hint)

    # ── Ask logic ─────────────────────────────────────────────────────────────

    def _ask_send(self):
        question = self._ask_input.toPlainText().strip()
        if not question:
            return
        topic = getattr(self, "_ask_topic", "General")
        self._ask_input.clear()
        self._ask_add_bubble(f"[{topic}]  {question}", is_user=True)

        # Show typing indicator
        self._ask_add_bubble("…", is_user=False, bubble_id="typing")

        system = (
            f"You are a knowledgeable assistant specialising in {topic}. "
            "Give clear, accurate, well-structured answers. "
            "Use bullet points or numbered lists when helpful. "
            "Be concise but thorough."
        )
        prompt = f"[Topic: {topic}]\n\n{question}"

        signals = _AskSignals()
        signals.finished.connect(lambda r: self._ask_on_response(r))
        self._ask_thread = _AskThread("ask", prompt, self, system, signals)
        self._ask_thread.start()

    def _ask_on_response(self, response: str):
        # Remove typing indicator
        self._ask_remove_bubble("typing")
        self._ask_add_bubble(response, is_user=False)

    def _ask_add_bubble(self, text: str, is_user: bool, bubble_id: str = ""):
        bubble = QWidget()
        bubble.setObjectName("askBubbleUser" if is_user else "askBubbleAI")
        if bubble_id:
            bubble.setProperty("bubble_id", bubble_id)
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

        self._ask_chat_lay.insertWidget(self._ask_chat_lay.count() - 1, bubble)
        QTimer.singleShot(50, lambda: self._ask_scroll.verticalScrollBar().setValue(
            self._ask_scroll.verticalScrollBar().maximum()
        ))

    def _ask_remove_bubble(self, bubble_id: str):
        for i in range(self._ask_chat_lay.count()):
            item = self._ask_chat_lay.itemAt(i)
            if item and item.widget():
                w = item.widget()
                if w.property("bubble_id") == bubble_id:
                    self._ask_chat_lay.takeAt(i)
                    w.deleteLater()
                    break

    def _ask_clear(self):
        while self._ask_chat_lay.count() > 1:
            item = self._ask_chat_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

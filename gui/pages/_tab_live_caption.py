"""gui/pages/_tab_live_caption.py — Live Caption tab for the Dashboard."""

import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QFrame
)
from gui._window_shared import scaled  # noqa: F401
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject


class _CaptionSignals(QObject):
    text_ready = pyqtSignal(str)


class LiveCaptionTabMixin:
    """Live Caption tab — real-time speech-to-text captions."""

    def _build_live_caption_tab(self) -> QWidget:
        frame = QWidget()
        frame.setObjectName("tabPage")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 18, 0, 0)
        lay.setSpacing(12)

        # ── Controls row ──────────────────────────────────────────────────
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(10)

        lang_lbl = QLabel("Language:")
        lang_lbl.setObjectName("featureLabel")
        ctrl_row.addWidget(lang_lbl)

        self._caption_lang = QComboBox()
        self._caption_lang.setObjectName("translateCombo")
        self._caption_lang.setFixedHeight(30)
        for lang in ["English", "Thai", "French", "Spanish", "German",
                     "Japanese", "Chinese", "Korean", "Arabic"]:
            self._caption_lang.addItem(lang)
        ctrl_row.addWidget(self._caption_lang)
        ctrl_row.addStretch()

        self._caption_start_btn = QPushButton("▶  Start")
        self._caption_start_btn.setObjectName("btnPrimary")
        self._caption_start_btn.setFixedSize(90, 32)
        self._caption_start_btn.clicked.connect(self._caption_toggle)
        ctrl_row.addWidget(self._caption_start_btn)

        clear_cap_btn = QPushButton("Clear")
        clear_cap_btn.setObjectName("btnOutline")
        clear_cap_btn.setFixedSize(70, 32)
        clear_cap_btn.clicked.connect(self._caption_clear)
        ctrl_row.addWidget(clear_cap_btn)

        lay.addLayout(ctrl_row)

        # ── Status bar ────────────────────────────────────────────────────
        self._caption_status = QLabel("Press Start to begin live captioning")
        self._caption_status.setObjectName("settingsLabel")
        self._caption_status.setStyleSheet("font-size: 11px;")
        lay.addWidget(self._caption_status)

        # ── Caption display ───────────────────────────────────────────────
        self._caption_out = QTextEdit()
        self._caption_out.setObjectName("featureEditReadOnly")
        self._caption_out.setReadOnly(True)
        self._caption_out.setPlaceholderText(
            "Live captions will appear here as you speak…\n\n"
            "Requires a microphone and either:\n"
            "  • OpenAI Whisper API key, or\n"
            "  • Google Speech-to-Text API key\n\n"
            "Connect an API key in My API Key to enable."
        )
        lay.addWidget(self._caption_out, 1)

        # ── Live word indicator ───────────────────────────────────────────
        self._caption_live_lbl = QLabel("")
        self._caption_live_lbl.setObjectName("settingsLabel")
        self._caption_live_lbl.setStyleSheet("font-size: 12px; font-style: italic;")
        lay.addWidget(self._caption_live_lbl)

        # Internal state
        self._caption_running = False
        self._caption_signals = _CaptionSignals()
        self._caption_signals.text_ready.connect(self._caption_on_text)

        return frame

    # ── Caption logic ─────────────────────────────────────────────────────────

    def _caption_toggle(self):
        if self._caption_running:
            self._caption_stop()
        else:
            self._caption_start()

    def _caption_start(self):
        self._caption_running = True
        self._caption_start_btn.setText("■  Stop")
        self._caption_start_btn.setObjectName("stopBtn")
        self._caption_start_btn.style().unpolish(self._caption_start_btn)
        self._caption_start_btn.style().polish(self._caption_start_btn)
        self._caption_status.setText("🎙 Listening…")
        self._caption_live_lbl.setText("●  Live")

        # Try to use SpeechRecognition if available
        threading.Thread(target=self._caption_listen_loop, daemon=True).start()

    def _caption_stop(self):
        self._caption_running = False
        self._caption_start_btn.setText("▶  Start")
        self._caption_start_btn.setObjectName("btnPrimary")
        self._caption_start_btn.style().unpolish(self._caption_start_btn)
        self._caption_start_btn.style().polish(self._caption_start_btn)
        self._caption_status.setText("Stopped.")
        self._caption_live_lbl.setText("")

    def _caption_listen_loop(self):
        """Background thread — uses SpeechRecognition if installed."""
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.5)
                while self._caption_running:
                    try:
                        audio = r.listen(source, timeout=3, phrase_time_limit=10)
                        lang_map = {
                            "English": "en-US", "Thai": "th-TH", "French": "fr-FR",
                            "Spanish": "es-ES", "German": "de-DE", "Japanese": "ja-JP",
                            "Chinese": "zh-CN", "Korean": "ko-KR", "Arabic": "ar-SA",
                        }
                        lang = lang_map.get(self._caption_lang.currentText(), "en-US")
                        text = r.recognize_google(audio, language=lang)
                        self._caption_signals.text_ready.emit(text)
                    except Exception:
                        pass
        except ImportError:
            self._caption_signals.text_ready.emit(
                "[SpeechRecognition not installed]\n"
                "Run: pip install SpeechRecognition pyaudio\n"
                "Or connect an OpenAI Whisper API key for cloud captioning."
            )
            self._caption_stop()

    def _caption_on_text(self, text: str):
        existing = self._caption_out.toPlainText()
        sep = "\n" if existing.strip() else ""
        self._caption_out.setPlainText(existing + sep + text)
        # Scroll to bottom
        sb = self._caption_out.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _caption_clear(self):
        self._caption_out.clear()
        self._caption_live_lbl.setText("")

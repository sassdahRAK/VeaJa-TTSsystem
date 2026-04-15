"""
gui/pages/api_keys_mixin.py — My API Key Page
==============================================
Lets users store their own API keys for third-party AI providers.
Keys are saved to the user profile (profile.json) and used by
Summary and Translate features when available.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QLineEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


# Supported providers: (display_name, profile_key, placeholder, docs_url)
_PROVIDERS = [
    ("OpenAI  (GPT-4o, GPT-4, GPT-3.5)",
     "api_key_openai",
     "sk-…",
     "https://platform.openai.com/api-keys"),

    ("Google Gemini  (Gemini 1.5 Pro / Flash)",
     "api_key_gemini",
     "AIza…",
     "https://aistudio.google.com/app/apikey"),

    ("Anthropic Claude  (Claude 3.5 Sonnet / Haiku)",
     "api_key_claude",
     "sk-ant-…",
     "https://console.anthropic.com/settings/keys"),

    ("Google AI Studio  (Gemini via AI Studio)",
     "api_key_aistudio",
     "AIza…",
     "https://aistudio.google.com/app/apikey"),

    ("DeepL  (Translation)",
     "api_key_deepl",
     "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:fx",
     "https://www.deepl.com/account/summary"),

    ("LibreTranslate  (Self-hosted / Public)",
     "api_key_libretranslate",
     "optional — leave blank for public endpoint",
     "https://libretranslate.com"),
]


class ApiKeysMixin:
    """Mixin providing the My API Key page for MainWindow."""

    def _build_api_keys_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("contentPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Top action bar ────────────────────────────────────────────────
        top = QWidget()
        top.setObjectName("pageTopAction")
        t_lay = QHBoxLayout(top)
        t_lay.setContentsMargins(32, 14, 32, 10)

        title = QLabel("My API Keys")
        title.setObjectName("pageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        t_lay.addWidget(title)
        t_lay.addStretch()

        save_btn = QPushButton("Save")
        save_btn.setObjectName("btnOutline")
        save_btn.setFixedSize(90, 32)
        save_btn.clicked.connect(self._save_api_keys)
        t_lay.addWidget(save_btn)
        lay.addWidget(top)

        # ── Subtitle ──────────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("settingsScroll")

        sc = QWidget()
        sc_lay = QVBoxLayout(sc)
        sc_lay.setContentsMargins(32, 8, 32, 32)
        sc_lay.setSpacing(20)

        sub = QLabel(
            "Add your own API keys to unlock AI-powered Summary and Translation. "
            "Keys are stored locally on your device and never sent anywhere except "
            "the provider you choose."
        )
        sub.setObjectName("settingsLabel")
        sub.setWordWrap(True)
        sc_lay.addWidget(sub)

        # ── Provider cards ────────────────────────────────────────────────
        self._api_key_inputs: dict[str, QLineEdit] = {}

        for display_name, profile_key, placeholder, docs_url in _PROVIDERS:
            card = self._build_api_card(display_name, profile_key, placeholder, docs_url)
            sc_lay.addWidget(card)

        sc_lay.addStretch()
        scroll.setWidget(sc)
        lay.addWidget(scroll, 1)
        return page

    def _build_api_card(self, name: str, key: str, placeholder: str, url: str) -> QWidget:
        card = QWidget()
        card.setObjectName("infoCard")
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(18, 14, 18, 14)
        c_lay.setSpacing(8)

        # Provider name row
        name_row = QHBoxLayout()
        name_lbl = QLabel(name)
        name_lbl.setObjectName("cardTitle")
        name_row.addWidget(name_lbl)
        name_row.addStretch()

        # "Get key" link button
        link_btn = QPushButton("Get key ↗")
        link_btn.setObjectName("btnOutline")
        link_btn.setFixedSize(80, 26)
        link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        link_btn.clicked.connect(lambda _=False, u=url: self._open_url(u))
        name_row.addWidget(link_btn)
        c_lay.addLayout(name_row)

        # Key input row
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        field = QLineEdit()
        field.setObjectName("settingsInput")
        field.setPlaceholderText(placeholder)
        field.setEchoMode(QLineEdit.EchoMode.Password)
        field.setFixedHeight(32)
        self._api_key_inputs[key] = field
        input_row.addWidget(field, 1)

        # Show/hide toggle
        toggle_btn = QPushButton("Show")
        toggle_btn.setObjectName("btnOutline")
        toggle_btn.setFixedSize(56, 32)
        toggle_btn.setCheckable(True)
        toggle_btn.toggled.connect(
            lambda checked, f=field, b=toggle_btn: (
                f.setEchoMode(
                    QLineEdit.EchoMode.Normal if checked
                    else QLineEdit.EchoMode.Password
                ),
                b.setText("Hide" if checked else "Show")
            )
        )
        input_row.addWidget(toggle_btn)

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("btnOutline")
        clear_btn.setFixedSize(56, 32)
        clear_btn.clicked.connect(lambda _=False, f=field: f.clear())
        input_row.addWidget(clear_btn)

        c_lay.addLayout(input_row)
        return card

    def _save_api_keys(self):
        """Collect all key fields and persist via settings_save_requested."""
        data = {k: field.text().strip() for k, field in self._api_key_inputs.items()}
        self.settings_save_requested.emit(data)

    def _open_url(self, url: str):
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(url))

    def apply_api_keys(self, profile: dict):
        """Populate key fields from the loaded profile."""
        if not hasattr(self, "_api_key_inputs"):
            return
        for key, field in self._api_key_inputs.items():
            field.setText(profile.get(key, ""))

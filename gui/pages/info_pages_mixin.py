from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame
)


class InfoPagesMixin:
    """Mixin providing Ask, Privacy, and Tutorial page methods for MainWindow."""

    # ── Shared card widget ─────────────────────────────────────────────────────

    def _info_card(self, title: str, body: str) -> QWidget:
        card = QWidget()
        card.setObjectName("infoCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(9)
        t = QLabel(title)
        t.setObjectName("cardTitle")
        t.setWordWrap(True)
        lay.addWidget(t)
        b = QLabel(body)
        b.setObjectName("cardBody")
        b.setWordWrap(True)
        lay.addWidget(b)
        return card

    # ── Ask a Question page ────────────────────────────────────────────────────

    def _build_ask_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("contentPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        hdr = QWidget()
        hdr.setObjectName("pageHeader")
        h_lay = QHBoxLayout(hdr)
        h_lay.setContentsMargins(32, 28, 32, 20)
        title = QLabel("General")
        title.setObjectName("pageTitle")
        h_lay.addWidget(title)
        h_lay.addStretch()
        email_btn = QPushButton("Email")
        email_btn.setObjectName("btnOutline")
        email_btn.setFixedSize(90, 32)
        email_btn.clicked.connect(self._open_contact_email)
        h_lay.addWidget(email_btn)
        lay.addWidget(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        sc = QWidget()
        sc_lay = QVBoxLayout(sc)
        sc_lay.setContentsMargins(32, 0, 32, 32)
        sc_lay.setSpacing(14)
        for q, a in [
            ("Q1. How do I start using Veaja?",
             "Install and launch Veaja — it will sit quietly in your system tray.\n"
             "Select any text in any window, then press Ctrl+R to read it aloud immediately.\n"
             "Alternatively, press Ctrl+C and the overlay pill will appear on your screen so you can follow along word by word.\n"
             "No setup, no account, and no copy-paste is needed. Just select and go."),
            ("Q2. What is the overlay pill and how does it work?",
             "The overlay pill is a small floating widget that appears on top of your screen when Veaja is reading.\n"
             "It shows the Veaja logo, a 'Tap to read' label, and a restart button.\n"
             "As Veaja speaks, it highlights each word in real-time so you can follow along without switching windows.\n"
             "The pill stays on top of all other apps and never blocks your clicks or keyboard input underneath it.\n"
             "You can drag it anywhere on your screen to keep it out of the way."),
            ("Q3. What is the difference between Online and Offline mode?",
             "Offline mode: all processing is done locally on your device using a built-in TTS engine. No internet needed. Completely private.\n"
             "Online mode: your text is sent to Microsoft Azure Cognitive Services, which returns higher-quality, more natural-sounding speech.\n"
             "In Online mode, no account or API key is required — Veaja uses the Edge browser's built-in neural TTS service.\n"
             "Choose Offline if privacy is your priority. Choose Online for the best voice quality."),
            ("Q4. Does Veaja store or record what I read?",
             "Veaja saves a session history so you can replay past readings from the View History page.\n"
             "This history is stored only on your local device — it is never uploaded to any server.\n"
             "In Offline mode, no data ever leaves your machine.\n"
             "In Online mode, the text is sent to Microsoft's TTS service but Veaja itself does not log, store, or share it.\n"
             "You can clear your history at any time from the history page."),
            ("Q5. Which languages and voices are supported?",
             "Currently Veaja supports English only.\n"
             "Multiple voices and accents are available in English — you can choose your preferred voice from Voice Settings.\n"
             "Support for additional languages such as Arabic, French, Spanish, German, and Japanese is planned for a future release.\n"
             "Stay tuned for updates."),
            ("Q6. Can I adjust reading speed?",
             "Yes. Go to Voice Settings and use the speed control to slow down or speed up playback.\n"
             "Speed adjustment is applied at the synthesis stage — not by resampling audio after the fact.\n"
             "This means slow or fast speeds still sound natural, not robotic or distorted.\n"
             "Slower speeds are great for absorbing detail. Faster speeds are useful for skimming long documents."),
            ("Q7. Why is Veaja not reading my selected text?",
             "Make sure the text is actually selectable — some protected PDFs or images do not expose their text.\n"
             "If Ctrl+R does not work, check that Veaja is running in the system tray (look for the tray icon).\n"
             "On macOS, Veaja may need Accessibility permission — go to System Settings → Privacy & Security → Accessibility and enable Veaja.\n"
             "On Windows, some admin-protected applications may block text capture. Try copying the text manually and using the Text Label tab instead."),
            ("Q8. How many features does Veaja currently have?",
             "Veaja currently has 7 core features:\n\n"
             "1. Overlay Read (Ctrl+R or Ctrl+C)\n"
             "   Select any text on your screen and press Ctrl+R to read it immediately. Press Ctrl+C to pop up the floating overlay pill. The pill appears on top of all windows and highlights each word in real-time as Veaja speaks — so you can follow along without switching apps or losing your place.\n\n"
             "2. Text Label tab\n"
             "   Paste or type any text directly into the Text Label tab on the Dashboard and press Read. This is useful when you cannot select text from an app — for example, image-based PDFs or locked documents. You can stop, resume, or clear the text at any time.\n\n"
             "3. Voice Settings\n"
             "   Go to Voice Setting from the sidebar to customise how Veaja sounds and behaves. You can: choose your preferred voice and accent, set reading speed (slower to absorb detail, faster to skim), set volume, switch between Online mode (Azure Neural TTS — higher quality) and Offline mode (fully local, no internet needed), and pick your overlay shape — Circle (pill) or Rectangle.\n\n"
             "4. Overlay Shape Selection\n"
             "   Inside Voice Setting, under 'Set overlay shape', choose whether the floating reading pill appears as a rounded circle/pill shape or a rectangle. Both shapes are previewed in dark and light theme so you can see exactly what it will look like before you decide.\n\n"
             "5. Session History\n"
             "   Every reading session is automatically saved to the View History page. You can replay any past session exactly as it was — same text, same voice, same speed. This is great for studying, reviewing notes, or catching up on content you listened to earlier. You can also delete individual entries or clear the full history.\n\n"
             "6. Edit Profile\n"
             "   Click the pencil icon next to your name in the sidebar to open the Profile page. Here you can set your display name and upload a custom profile photo that appears in the sidebar. Your changes are saved locally and persist between sessions. You can also reset to the default Veaja logo at any time.\n\n"
             "7. Interactive Tutorial\n"
             "   Go to Tutorial from the sidebar to take a guided step-by-step walkthrough of Veaja. The tutorial walks you through: how to trigger a read with Ctrl+R and Ctrl+C, how the overlay pill works, how to use the Text Label tab, how to visit Voice Setting, and how to check your history. Each step highlights the relevant part of the app so you know exactly where to look and what to do."),
            ("Q9. Can I use this app on a mobile phone or tablet?",
             "Currently Veaja is a desktop application available for Windows, macOS, and Linux.\n"
             "Mobile support for Android and iOS is planned for a future release.\n"
             "For now, you can use Veaja on any laptop or desktop computer."),
        ]:
            sc_lay.addWidget(self._info_card(q, a))

        # ── Contact banner ────────────────────────────────────────────────
        sc_lay.addSpacing(8)
        banner = QWidget()
        banner.setObjectName("contactBanner")
        b_lay = QVBoxLayout(banner)
        b_lay.setContentsMargins(20, 16, 20, 16)
        b_lay.setSpacing(6)

        b_title = QLabel("Still need help?")
        b_title.setObjectName("cardTitle")
        b_lay.addWidget(b_title)

        b_body = QLabel(
            "If you ran into a bug, need help debugging an issue, want to request a feature, "
            "or just have feedback for us — we'd love to hear from you.\n"
            "Tap the  Email  button above to open a Gmail compose window addressed directly "
            "to our support inbox. Describe what happened, what you expected, and your "
            "operating system if relevant. We read every message."
        )
        b_body.setObjectName("cardBody")
        b_body.setWordWrap(True)
        b_lay.addWidget(b_body)

        contact_btn = QPushButton("Contact us via Email")
        contact_btn.setObjectName("btnOutline")
        contact_btn.setFixedHeight(34)
        contact_btn.clicked.connect(self._open_contact_email)
        b_lay.addSpacing(4)
        b_lay.addWidget(contact_btn)

        sc_lay.addWidget(banner)
        sc_lay.addStretch()
        scroll.setWidget(sc)
        lay.addWidget(scroll, 1)
        return page

    def _open_contact_email(self):
        """Open Gmail compose in the browser — bypasses system mail client so messages
        actually arrive at veaja.app.official@gmail.com regardless of local mail setup."""
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        import urllib.parse
        subject = "Veaja – Question / Feedback"
        body    = "Hi Veaja team,\n\n"
        params  = urllib.parse.urlencode({
            "view": "cm",
            "to":   "veaja.app.official@gmail.com",
            "su":   subject,
            "body": body,
        })
        QDesktopServices.openUrl(QUrl(f"https://mail.google.com/mail/?{params}"))

    # ── Data Privacy page ──────────────────────────────────────────────────────

    def _build_privacy_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("contentPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(0)

        title = QLabel("Term of use")
        title.setObjectName("pageTitle")
        lay.addWidget(title)
        lay.addSpacing(20)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        sc = QWidget()
        sc_lay = QVBoxLayout(sc)
        sc_lay.setContentsMargins(0, 0, 0, 0)
        sc_lay.setSpacing(14)
        for t, body in [
            ("T1. Acceptance of terms",
             "By installing or using Veaja, you agree to these terms of use.\n"
             "If you do not agree, please uninstall the application and discontinue use.\n"
             "These terms may be updated over time. Continued use after an update means you accept the revised terms."),
            ("T2. Offline usage",
             "In Offline mode, all text-to-speech processing is performed entirely on your device.\n"
             "No data is transmitted to any external server.\n"
             "Audio files generated during a session are stored temporarily at ~/.veaja/audio/ and cleared when the session ends.\n"
             "You are solely responsible for the content you choose to read aloud using Veaja."),
            ("T3. Online usage",
             "In Online mode, the text you select is sent to Microsoft Azure Cognitive Services for neural TTS synthesis.\n"
             "Veaja does not store, log, retain, or share this text in any form.\n"
             "Microsoft's own privacy policy governs how they handle data sent through their API.\n"
             "No account, subscription, or API key is required — Veaja relies on the Edge browser's built-in TTS service."),
            ("T4. Acceptable use",
             "You may use Veaja for personal, educational, or professional reading of text you have the right to access.\n"
             "You must not use Veaja to read, reproduce, or distribute copyrighted content without authorisation.\n"
             "You must not use Veaja to process content that is illegal, harmful, abusive, or violates the rights of others.\n"
             "Veaja is a reading aid — it is your responsibility to ensure the content you read complies with applicable laws."),
            ("T5. Data and privacy",
             "Veaja does not create user accounts and does not collect personal information.\n"
             "Session history is stored locally on your device only and is never uploaded.\n"
             "Your voice settings, language preferences, and profile name are saved locally in a configuration file on your machine.\n"
             "You can delete this data at any time by clearing the app's configuration folder."),
            ("T6. Third-party services",
             "Online mode uses Microsoft Azure Cognitive Services (TTS). Use of this service is subject to Microsoft's terms and privacy policy.\n"
             "Veaja does not endorse or take responsibility for the accuracy, availability, or practices of any third-party service.\n"
             "If Microsoft's TTS service is unavailable, Veaja will fall back to Offline mode automatically when possible."),
            ("T7. Limitation of liability",
             "Veaja is provided 'as is' without warranty of any kind, express or implied.\n"
             "The developers are not liable for any loss of data, interruption of service, or damages arising from use of this application.\n"
             "Veaja is a tool — you are responsible for how you use the output it produces."),
            ("T8. Changes and termination",
             "The developers reserve the right to update, modify, or discontinue Veaja at any time without notice.\n"
             "Features available in the current version may change in future releases.\n"
             "You may stop using Veaja at any time by uninstalling it. Local data can be removed manually from your device."),
        ]:
            sc_lay.addWidget(self._info_card(t, body))
        sc_lay.addStretch()
        scroll.setWidget(sc)
        lay.addWidget(scroll, 1)
        return page

    # ── Tutorial page (static + launch interactive button) ────────────────────

    def _build_tutorial_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("contentPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(0)

        title = QLabel("Tutorial")
        title.setObjectName("pageTitle")
        lay.addWidget(title)
        lay.addSpacing(20)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        sc = QWidget()
        sc_lay = QVBoxLayout(sc)
        sc_lay.setContentsMargins(0, 0, 0, 0)
        sc_lay.setSpacing(14)

        for t, body in [
            ("Getting Started",
             "Select any text on your screen and press Ctrl+R to have Veaja read it aloud.\n"
             "Use Ctrl+C to pop up the overlay pill anywhere on your screen."),
            ("Using Text Label",
             "Navigate to Dashboard → Text label tab.\n"
             "Type or paste your text into the input area, then click Read to start playback."),
            ("Customising Your Experience",
             "Visit Voice Setting to choose the overlay shape, select a voice, adjust speed,\n"
             "change language, and switch between Online and Offline mode."),
        ]:
            sc_lay.addWidget(self._info_card(t, body))

        # Interactive tour launch button
        sc_lay.addSpacing(8)
        tour_btn = QPushButton("▶  Start Interactive Tutorial")
        tour_btn.setObjectName("tourLaunchBtn")
        tour_btn.setFixedHeight(38)
        tour_btn.clicked.connect(self.tour_requested)
        sc_lay.addWidget(tour_btn)
        sc_lay.addStretch()
        scroll.setWidget(sc)
        lay.addWidget(scroll, 1)
        return page

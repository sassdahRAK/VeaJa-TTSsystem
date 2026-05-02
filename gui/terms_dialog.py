"""
Privacy & Terms dialog.
Shown automatically on first launch, and on demand via the header button.
"""

import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QWidget, QScrollArea, QFrame,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

_ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")


class TermsDialog(QDialog):
    def __init__(self, online_mode: bool, dark: bool = True, parent=None):
        super().__init__(parent)
        self._online = online_mode
        self._dark   = dark
        self.setWindowTitle("Privacy & Data Notice — Veaja")
        self.setModal(False)   # non-modal — overlay must stay interactive
        self.setFixedWidth(520)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint   # stay visible but don't block
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)  # don't steal focus
        self._build_ui()
        self._apply_style()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self._card = QWidget()
        self._card.setObjectName("termsCard")
        card_lay = QVBoxLayout(self._card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)
        root.addWidget(self._card)

        # ── Title bar ─────────────────────────────────────────────────────
        title_bar = QWidget()
        title_bar.setObjectName("termsTitleBar")
        title_bar.setFixedHeight(56)
        tb_lay = QHBoxLayout(title_bar)
        tb_lay.setContentsMargins(24, 0, 16, 0)

        lock_lbl = QLabel()
        lock_lbl.setObjectName("termsLockIcon")
        lock_lbl.setFixedSize(22, 22)
        lock_lbl.setPixmap(self._svg_pixmap(
            # Browser-style lock: body + shackle
            '<rect x="5" y="11" width="14" height="10" rx="2" stroke="currentColor" stroke-width="1.7" fill="none"/>'
            '<path d="M8 11V7a4 4 0 0 1 8 0v4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" fill="none"/>'
            '<circle cx="12" cy="16" r="1.2" fill="currentColor"/>',
            size=18,
            color="#f5f5f7" if self._dark else "#1a1a1a",
        ))
        title_lbl = QLabel("Privacy & Data Notice")
        title_lbl.setObjectName("termsTitleText")

        close_btn = QPushButton("✕")
        close_btn.setObjectName("termsClose")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)

        tb_lay.addWidget(lock_lbl)
        tb_lay.addSpacing(8)
        tb_lay.addWidget(title_lbl)
        tb_lay.addStretch()
        tb_lay.addWidget(close_btn)
        card_lay.addWidget(title_bar)

        accent_line = QFrame()
        accent_line.setObjectName("termsAccentLine")
        accent_line.setFixedHeight(2)
        card_lay.addWidget(accent_line)

        # ── Scrollable body ───────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setObjectName("termsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFixedHeight(440)

        body = QWidget()
        body.setObjectName("termsBody")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(24, 20, 24, 8)
        body_lay.setSpacing(18)

        # ── TTS mode notice ───────────────────────────────────────────────
        if self._online:
            accent    = "#e05a2b"
            badge_bg  = "rgba(224, 90, 43, 0.10)"
            mode_icon = "⚠"
            badge_lbl = "ONLINE MODE"
            mode_title = "Microsoft Edge TTS is active"
            mode_body  = (
                "Text you read is sent to <b>Microsoft's servers</b> for speech synthesis — "
                "the same service that powers Edge's Read Aloud feature.<br><br>"
                "Avoid reading sensitive or confidential content in this mode.<br>"
                "<span style='opacity:0.65;'>Microsoft's privacy policy governs how that data is handled.</span>"
            )
        else:
            accent    = "#30a46c"
            badge_bg  = "rgba(48, 164, 108, 0.10)"
            mode_icon = "✓"
            badge_lbl = "OFFLINE MODE"
            mode_title = "All TTS processing is on-device"
            mode_body  = (
                "Text-to-speech runs <b>entirely on your device</b>. "
                "No text is sent to any server — your data never leaves your computer."
            )

        notice_wrapper = QWidget()
        notice_wrapper.setObjectName("termsNoticeWrapper")
        nw_lay = QHBoxLayout(notice_wrapper)
        nw_lay.setContentsMargins(0, 0, 0, 0)
        nw_lay.setSpacing(0)

        self._accent_bar = QFrame()
        self._accent_bar.setObjectName("termsAccentBar")
        self._accent_bar.setFixedWidth(4)
        nw_lay.addWidget(self._accent_bar)

        notice_card = QWidget()
        notice_card.setObjectName("termsNoticeCard")
        nc_lay = QVBoxLayout(notice_card)
        nc_lay.setContentsMargins(16, 14, 16, 14)
        nc_lay.setSpacing(6)

        badge_row = QHBoxLayout()
        badge_row.setSpacing(8)
        # SVG icon: warning triangle (online) or checkmark shield (offline)
        if self._online:
            _mode_svg = (
                '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"'
                ' stroke="currentColor" stroke-width="1.6" fill="none"/>'
                '<line x1="12" y1="9" x2="12" y2="13" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>'
                '<circle cx="12" cy="17" r="0.8" fill="currentColor"/>'
            )
            _mode_color = accent
        else:
            _mode_svg = (
                '<path d="M12 2L3 7v5c0 5.25 3.75 10.15 9 11.25C17.25 22.15 21 17.25 21 12V7L12 2z"'
                ' stroke="currentColor" stroke-width="1.6" fill="none"/>'
                '<polyline points="9 12 11 14 15 10" stroke="currentColor" stroke-width="1.6"'
                ' stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
            )
            _mode_color = accent
        icon_lbl2 = QLabel()
        icon_lbl2.setObjectName("termsModeIcon")
        icon_lbl2.setFixedSize(18, 18)
        icon_lbl2.setPixmap(self._svg_pixmap(_mode_svg, size=16, color=_mode_color))
        badge_label_lbl = QLabel(badge_lbl)
        badge_label_lbl.setObjectName("termsBadge")
        badge_row.addWidget(icon_lbl2)
        badge_row.addWidget(badge_label_lbl)
        badge_row.addStretch()
        nc_lay.addLayout(badge_row)

        mode_title_lbl = QLabel(mode_title)
        mode_title_lbl.setObjectName("termsModeTitle")
        nc_lay.addWidget(mode_title_lbl)

        mode_body_lbl = QLabel(mode_body)
        mode_body_lbl.setObjectName("termsModeBody")
        mode_body_lbl.setWordWrap(True)
        mode_body_lbl.setTextFormat(Qt.TextFormat.RichText)
        nc_lay.addWidget(mode_body_lbl)

        nw_lay.addWidget(notice_card, 1)
        body_lay.addWidget(notice_wrapper)

        # ── AI features notice ────────────────────────────────────────────
        ai_wrapper = QWidget()
        ai_wrapper.setObjectName("termsAiWrapper")
        ai_nw_lay = QHBoxLayout(ai_wrapper)
        ai_nw_lay.setContentsMargins(0, 0, 0, 0)
        ai_nw_lay.setSpacing(0)

        self._ai_accent_bar = QFrame()
        self._ai_accent_bar.setObjectName("termsAiAccentBar")
        self._ai_accent_bar.setFixedWidth(4)
        ai_nw_lay.addWidget(self._ai_accent_bar)

        ai_card = QWidget()
        ai_card.setObjectName("termsAiCard")
        ai_lay = QVBoxLayout(ai_card)
        ai_lay.setContentsMargins(16, 14, 16, 14)
        ai_lay.setSpacing(6)

        ai_badge_row = QHBoxLayout()
        ai_badge_row.setSpacing(8)
        # SVG icon: CPU/chip representing AI
        _ai_svg = (
            '<rect x="9" y="9" width="6" height="6" rx="1" stroke="currentColor" stroke-width="1.5" fill="none"/>'
            '<rect x="4" y="4" width="16" height="16" rx="2" stroke="currentColor" stroke-width="1.5" fill="none"/>'
            '<path d="M9 2v2M15 2v2M9 20v2M15 20v2M2 9h2M2 15h2M20 9h2M20 15h2"'
            ' stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>'
        )
        ai_icon_lbl = QLabel()
        ai_icon_lbl.setObjectName("termsModeIcon")
        ai_icon_lbl.setFixedSize(18, 18)
        ai_icon_lbl.setPixmap(self._svg_pixmap(_ai_svg, size=16, color="#6366f1"))
        ai_badge = QLabel("AI FEATURES")
        ai_badge.setObjectName("termsAiBadge")
        ai_badge_row.addWidget(ai_icon_lbl)
        ai_badge_row.addWidget(ai_badge)
        ai_badge_row.addStretch()
        ai_lay.addLayout(ai_badge_row)

        ai_title = QLabel("Dashboard AI features send data to third-party APIs")
        ai_title.setObjectName("termsModeTitle")
        ai_lay.addWidget(ai_title)

        ai_body = QLabel(
            "When you use Summary, Translate, Code, Generate, Ask, or Grammar tabs, "
            "your text is sent to the AI provider whose key you have added "
            "(OpenAI, Google Gemini, or Anthropic Claude).<br><br>"
            "These features are <b>opt-in</b> — they only activate when you add an API key "
            "in <b>My API Key</b>. No key = no data sent.<br><br>"
            "<span style='opacity:0.65;'>Each provider's own privacy policy governs how they handle your data. "
            "Avoid sending sensitive or confidential content through AI features.</span>"
        )
        ai_body.setObjectName("termsModeBody")
        ai_body.setWordWrap(True)
        ai_body.setTextFormat(Qt.TextFormat.RichText)
        ai_lay.addWidget(ai_body)

        ai_nw_lay.addWidget(ai_card, 1)
        body_lay.addWidget(ai_wrapper)

        # ── About Veaja ───────────────────────────────────────────────────
        about_sec = QLabel("About Veaja")
        about_sec.setObjectName("termsSectionHeader")
        body_lay.addWidget(about_sec)

        about_body = QLabel(
            "Veaja is a <b>desktop productivity tool</b> for reading, summarising, "
            "translating, and analysing text. It runs locally on your device and "
            "does <b>not</b> have its own servers — it connects only to the third-party "
            "services you explicitly configure."
        )
        about_body.setObjectName("termsBodyText")
        about_body.setWordWrap(True)
        about_body.setTextFormat(Qt.TextFormat.RichText)
        body_lay.addWidget(about_body)

        bullets = [
            ("No Veaja account required",
             "No sign-up, no login, no cloud sync with Veaja's servers"),
            ("No analytics or telemetry",
             "Veaja never tracks your usage, behaviour, or content"),
            ("Local storage only",
             "Profile, history, and API keys are saved at <code>~/.veaja/</code> on your device"),
            ("API keys stay on your device",
             "Keys are stored locally and sent only to the provider you chose — never to Veaja"),
            ("Your responsibility",
             "You choose what content to read or send to AI — use good judgement with sensitive data"),
        ]
        for title, detail in bullets:
            row = QHBoxLayout()
            row.setSpacing(12)
            row.setContentsMargins(0, 0, 0, 0)

            dot = QLabel("•")
            dot.setObjectName("termsBulletDot")
            dot.setFixedWidth(12)
            dot.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

            text_col = QVBoxLayout()
            text_col.setSpacing(1)
            title_lbl2 = QLabel(f"<b>{title}</b>")
            title_lbl2.setObjectName("termsBulletTitle")
            title_lbl2.setTextFormat(Qt.TextFormat.RichText)
            detail_lbl = QLabel(detail)
            detail_lbl.setObjectName("termsBulletDetail")
            detail_lbl.setWordWrap(True)
            detail_lbl.setTextFormat(Qt.TextFormat.RichText)
            text_col.addWidget(title_lbl2)
            text_col.addWidget(detail_lbl)

            row.addWidget(dot)
            row.addLayout(text_col, 1)
            body_lay.addLayout(row)

        body_lay.addStretch()
        scroll.setWidget(body)
        card_lay.addWidget(scroll)

        # ── Footer ────────────────────────────────────────────────────────
        footer = QWidget()
        footer.setObjectName("termsFooter")
        foot_lay = QVBoxLayout(footer)
        foot_lay.setContentsMargins(24, 14, 24, 20)
        foot_lay.setSpacing(12)

        divider = QFrame()
        divider.setObjectName("termsFooterDivider")
        divider.setFrameShape(QFrame.Shape.HLine)
        foot_lay.addWidget(divider)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._dont_show_cb = QCheckBox("Don't show this again")
        self._dont_show_cb.setObjectName("termsCb")
        self._dont_show_cb.setCursor(Qt.CursorShape.PointingHandCursor)

        ok_btn = QPushButton("I Understand")
        ok_btn.setObjectName("termsOk")
        ok_btn.setFixedHeight(40)
        ok_btn.setMinimumWidth(130)
        ok_btn.setDefault(True)
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.clicked.connect(self.accept)

        btn_row.addWidget(self._dont_show_cb)
        btn_row.addStretch()
        btn_row.addWidget(ok_btn)
        foot_lay.addLayout(btn_row)
        card_lay.addWidget(footer)

        # Store for styling
        self._accent         = accent
        self._badge_bg       = badge_bg
        self._notice_card    = notice_card
        self._notice_wrapper = notice_wrapper
        self._ai_card        = ai_card
        self._ai_wrapper     = ai_wrapper

    # ── SVG icon helper ───────────────────────────────────────────────────────

    def _svg_pixmap(self, svg_body: str, size: int = 16, color: str = "#ffffff"):
        """Render an SVG path string to a QPixmap at the given logical size."""
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtGui import QPixmap, QPainter, QColor
        from PyQt6.QtWidgets import QApplication
        svg = (
            f'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">'
            f'<g color="{color}">{svg_body}</g>'
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
        return px

    # ── Style ─────────────────────────────────────────────────────────────────

    def _apply_style(self):
        dark   = self._dark
        accent = self._accent
        ai_accent = "#6366f1"   # indigo for AI section
        check_icon = os.path.join(_ASSETS, "check_light.svg").replace("\\", "/")

        if dark:
            card_bg      = "#1c1c1e"
            titlebar_bg  = "#232325"
            body_bg      = "#1c1c1e"
            scroll_bg    = "#1c1c1e"
            footer_bg    = "#1c1c1e"
            border       = "rgba(255,255,255,0.08)"
            title_c      = "#f5f5f7"
            body_c       = "#c7c7cc"
            section_c    = "#8e8e93"
            bullet_dot   = accent
            bullet_ttl   = "#e5e5ea"
            bullet_det   = "#8e8e93"
            close_c      = "rgba(255,255,255,0.35)"
            close_h      = "rgba(255,255,255,0.12)"
            divider_c    = "rgba(255,255,255,0.08)"
            notice_bdr   = "rgba(255,255,255,0.06)"
            cb_c         = "#8e8e93"
            cb_h         = "#f5f5f7"
            ok_bg        = "#ffffff"
            ok_h         = "#e5e5e7"
            ok_c         = "#111111"
            ok_border    = "transparent"
            sb_bg        = "rgba(255,255,255,0.05)"
            sb_h         = "rgba(255,255,255,0.15)"
            mode_body_c  = "#aeaeb2"
            mode_title_c = "#f5f5f7"
            badge_c      = accent
        else:
            card_bg      = "#f5f5f7"
            titlebar_bg  = "#ebebed"
            body_bg      = "#f5f5f7"
            scroll_bg    = "#f5f5f7"
            footer_bg    = "#f5f5f7"
            border       = "rgba(0,0,0,0.10)"
            title_c      = "#1a1a1a"
            body_c       = "#3a3a3c"
            section_c    = "#6e6e73"
            bullet_dot   = accent
            bullet_ttl   = "#1a1a1a"
            bullet_det   = "#6e6e73"
            close_c      = "rgba(0,0,0,0.35)"
            close_h      = "rgba(0,0,0,0.07)"
            divider_c    = "rgba(0,0,0,0.08)"
            notice_bdr   = "rgba(0,0,0,0.07)"
            cb_c         = "#6e6e73"
            cb_h         = "#1a1a1a"
            ok_bg        = "#1a1a1a"
            ok_h         = "#2a2a2a"
            ok_c         = "#ffffff"
            ok_border    = "transparent"
            sb_bg        = "rgba(0,0,0,0.05)"
            sb_h         = "rgba(0,0,0,0.15)"
            mode_body_c  = "#4a4a4f"
            mode_title_c = "#1a1a1a"
            badge_c      = accent

        # TTS notice wrapper
        self._notice_wrapper.setStyleSheet(
            f"QWidget#termsNoticeWrapper {{"
            f"background: {self._badge_bg};"
            f"border: 1px solid {notice_bdr};"
            f"border-radius: 10px; }}"
        )
        self._accent_bar.setStyleSheet(
            f"QFrame#termsAccentBar {{"
            f"background: {accent};"
            f"border-top-left-radius: 10px;"
            f"border-bottom-left-radius: 10px;"
            f"border: none; }}"
        )
        glow = QGraphicsDropShadowEffect(self._accent_bar)
        glow.setBlurRadius(20)
        glow.setOffset(0, 0)
        glow.setColor(QColor(accent))
        self._accent_bar.setGraphicsEffect(glow)
        self._notice_card.setStyleSheet(
            "QWidget#termsNoticeCard { background: transparent; border: none; }"
        )

        # AI notice wrapper
        ai_bg = "rgba(99, 102, 241, 0.10)"
        self._ai_wrapper.setStyleSheet(
            f"QWidget#termsAiWrapper {{"
            f"background: {ai_bg};"
            f"border: 1px solid rgba(99,102,241,0.15);"
            f"border-radius: 10px; }}"
        )
        self._ai_accent_bar.setStyleSheet(
            f"QFrame#termsAiAccentBar {{"
            f"background: {ai_accent};"
            f"border-top-left-radius: 10px;"
            f"border-bottom-left-radius: 10px;"
            f"border: none; }}"
        )
        ai_glow = QGraphicsDropShadowEffect(self._ai_accent_bar)
        ai_glow.setBlurRadius(20)
        ai_glow.setOffset(0, 0)
        ai_glow.setColor(QColor(ai_accent))
        self._ai_accent_bar.setGraphicsEffect(ai_glow)
        self._ai_card.setStyleSheet(
            "QWidget#termsAiCard { background: transparent; border: none; }"
        )

        self.setStyleSheet(f"""
QWidget#termsCard {{
    background: {card_bg};
    border: 1px solid {border};
    border-radius: 16px;
}}
QWidget#termsTitleBar {{
    background: {titlebar_bg};
    border-top-left-radius: 16px;
    border-top-right-radius: 16px;
}}
QLabel#termsLockIcon {{
    background: transparent;
}}
QLabel#termsTitleText {{
    font-size: 14px;
    font-weight: 600;
    color: {title_c};
    background: transparent;
}}
QPushButton#termsClose {{
    background: transparent;
    color: {close_c};
    border: none;
    font-size: 13px;
    border-radius: 15px;
}}
QPushButton#termsClose:hover {{
    background: {close_h};
    color: {title_c};
}}
QFrame#termsAccentLine {{
    background: {accent};
    border: none;
    max-height: 2px;
}}
QScrollArea#termsScroll {{
    background: {scroll_bg};
    border: none;
}}
QWidget#termsBody {{
    background: {body_bg};
}}
QScrollBar:vertical {{
    background: {sb_bg};
    width: 6px;
    border-radius: 3px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {sb_h};
    border-radius: 3px;
    min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QLabel#termsModeIcon {{
    font-size: 14px;
    color: {accent};
    background: transparent;
    font-weight: 700;
}}
QLabel#termsBadge {{
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.8px;
    color: {badge_c};
    background: transparent;
}}
QLabel#termsAiBadge {{
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.8px;
    color: {ai_accent};
    background: transparent;
}}
QLabel#termsModeTitle {{
    font-size: 13px;
    font-weight: 600;
    color: {mode_title_c};
    background: transparent;
}}
QLabel#termsModeBody {{
    font-size: 12px;
    color: {mode_body_c};
    background: transparent;
    line-height: 1.5;
}}
QLabel#termsSectionHeader {{
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.9px;
    color: {section_c};
    background: transparent;
    text-transform: uppercase;
}}
QLabel#termsBodyText {{
    font-size: 13px;
    color: {body_c};
    background: transparent;
    line-height: 1.5;
}}
QLabel#termsBulletDot {{
    font-size: 14px;
    font-weight: 700;
    color: {bullet_dot};
    background: transparent;
}}
QLabel#termsBulletTitle {{
    font-size: 13px;
    color: {bullet_ttl};
    background: transparent;
}}
QLabel#termsBulletDetail {{
    font-size: 12px;
    color: {bullet_det};
    background: transparent;
}}
QWidget#termsFooter {{
    background: {footer_bg};
    border-bottom-left-radius: 16px;
    border-bottom-right-radius: 16px;
}}
QFrame#termsFooterDivider {{
    color: {divider_c};
    background: {divider_c};
    max-height: 1px;
    border: none;
}}
QCheckBox#termsCb {{
    font-size: 12px;
    color: {cb_c};
    spacing: 8px;
}}
QCheckBox#termsCb:hover {{ color: {cb_h}; }}
QCheckBox#termsCb::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1.5px solid {section_c};
    background: transparent;
}}
QCheckBox#termsCb::indicator:checked {{
    background: {accent};
    border-color: {accent};
    image: url({check_icon});
}}
QCheckBox#termsCb::indicator:hover {{ border-color: {accent}; }}
QPushButton#termsOk {{
    background: {ok_bg};
    color: {ok_c};
    border: 1px solid {ok_border};
    border-radius: 10px;
    font-size: 13px;
    font-weight: 600;
    padding: 0 20px;
}}
QPushButton#termsOk:hover {{ background: {ok_h}; }}
QPushButton#termsOk:pressed {{ background: {ok_h}; }}
""")

    # ── Public ────────────────────────────────────────────────────────────────

    def dont_show_again(self) -> bool:
        return self._dont_show_cb.isChecked()

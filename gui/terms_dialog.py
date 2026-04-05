"""
Privacy & Terms dialog.
Shown automatically on first launch, and on demand via the header button.
"""

import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QWidget, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

_ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")


class TermsDialog(QDialog):
    def __init__(self, online_mode: bool, dark: bool = True, parent=None):
        super().__init__(parent)
        self._online = online_mode
        self._dark   = dark
        self.setWindowTitle("Privacy & Data Notice - Veaja")
        self.setModal(True)
        self.setFixedWidth(500)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build_ui()
        self._apply_style()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # Outer card
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

        lock_lbl = QLabel("🔒")
        lock_lbl.setObjectName("termsLockIcon")
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

        # Thin accent line under title bar
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
        scroll.setFixedHeight(420)

        body = QWidget()
        body.setObjectName("termsBody")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(24, 20, 24, 8)
        body_lay.setSpacing(16)

        # ── Mode notice card ──────────────────────────────────────────────
        if self._online:
            accent   = "#e05a2b"
            badge_bg = "rgba(224, 90, 43, 0.12)"
            mode_icon = "⚠"
            badge_label = "ONLINE MODE"
            mode_title = "Microsoft Edge TTS is active"
            mode_body = (
                "Text you read is sent to <b>Microsoft's servers</b> for speech synthesis — "
                "the same service powering Edge's Read Aloud feature.<br><br>"
                "Avoid reading sensitive, private, or confidential content in this mode.<br><br>"
                "<span style='opacity:0.7;'>Microsoft's privacy policy governs how that data is handled.</span>"
            )
        else:
            accent   = "#30a46c"
            badge_bg = "rgba(48, 164, 108, 0.12)"
            mode_icon = "✓"
            badge_label = "OFFLINE MODE"
            mode_title = "All processing is on-device"
            mode_body = (
                "Text-to-speech processing happens <b>entirely on your device</b>. "
                "No text is sent to any server — your data never leaves your computer."
            )

        notice_card = QWidget()
        notice_card.setObjectName("termsNoticeCard")
        nc_lay = QVBoxLayout(notice_card)
        nc_lay.setContentsMargins(16, 14, 16, 14)
        nc_lay.setSpacing(8)

        # Badge row
        badge_row = QHBoxLayout()
        badge_row.setSpacing(8)
        icon_lbl = QLabel(mode_icon)
        icon_lbl.setObjectName("termsModeIcon")
        badge_lbl = QLabel(badge_label)
        badge_lbl.setObjectName("termsBadge")
        badge_row.addWidget(icon_lbl)
        badge_row.addWidget(badge_lbl)
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

        body_lay.addWidget(notice_card)

        # ── Section: About Veaja ──────────────────────────────────────────
        about_sec = QLabel("About Veaja")
        about_sec.setObjectName("termsSectionHeader")
        body_lay.addWidget(about_sec)

        about_body = QLabel(
            "Veaja is a <b>lightweight, serverless</b> desktop tool. "
            "It does <b>not</b> collect, transmit, or store any personal data on third-party servers."
        )
        about_body.setObjectName("termsBodyText")
        about_body.setWordWrap(True)
        about_body.setTextFormat(Qt.TextFormat.RichText)
        body_lay.addWidget(about_body)

        # Bullet points
        bullets = [
            ("No account required", "No sign-up, no login, no cloud sync"),
            ("No analytics or telemetry", "We never track usage or behaviour"),
            ("Local audio history only", "Saved at <code>~/.veaja/audio/</code> on your device"),
            ("Your responsibility", "You choose the content you read aloud"),
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

        # Divider
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

        # Store for style use
        self._accent     = accent
        self._badge_bg   = badge_bg
        self._notice_card = notice_card

    # ── Style ─────────────────────────────────────────────────────────────────

    def _apply_style(self):
        dark = self._dark
        accent = self._accent
        check_icon = os.path.join(_ASSETS, "check_light.svg").replace("\\", "/")

        if dark:
            card_bg       = "#1c1c1e"
            titlebar_bg   = "#232325"
            body_bg       = "#1c1c1e"
            scroll_bg     = "#1c1c1e"
            footer_bg     = "#1c1c1e"
            border        = "rgba(255,255,255,0.08)"
            title_c       = "#f5f5f7"
            body_c        = "#c7c7cc"
            section_c     = "#8e8e93"
            bullet_dot_c  = accent
            bullet_ttl_c  = "#e5e5ea"
            bullet_det_c  = "#8e8e93"
            close_c       = "rgba(255,255,255,0.35)"
            close_h       = "rgba(255,255,255,0.12)"
            divider_c     = "rgba(255,255,255,0.08)"
            notice_border = f"rgba(255,255,255,0.06)"
            cb_c          = "#8e8e93"
            cb_h          = "#f5f5f7"
            ok_bg         = accent
            ok_h          = "#c94d22" if accent == "#e05a2b" else "#27946b"
            ok_c          = "#ffffff"
            scrollbar_bg  = "rgba(255,255,255,0.05)"
            scrollbar_h   = "rgba(255,255,255,0.15)"
            mode_body_c   = "#aeaeb2"
            mode_title_c  = "#f5f5f7"
            badge_c       = accent
            lock_c        = "#f5f5f7"
        else:
            card_bg       = "#ffffff"
            titlebar_bg   = "#f7f7f8"
            body_bg       = "#ffffff"
            scroll_bg     = "#ffffff"
            footer_bg     = "#ffffff"
            border        = "rgba(0,0,0,0.08)"
            title_c       = "#1a1a1a"
            body_c        = "#3a3a3c"
            section_c     = "#6e6e73"
            bullet_dot_c  = accent
            bullet_ttl_c  = "#1a1a1a"
            bullet_det_c  = "#6e6e73"
            close_c       = "rgba(0,0,0,0.4)"
            close_h       = "rgba(0,0,0,0.07)"
            divider_c     = "rgba(0,0,0,0.08)"
            notice_border = "rgba(0,0,0,0.06)"
            cb_c          = "#6e6e73"
            cb_h          = "#1a1a1a"
            ok_bg         = accent
            ok_h          = "#c94d22" if accent == "#e05a2b" else "#27946b"
            ok_c          = "#ffffff"
            scrollbar_bg  = "rgba(0,0,0,0.05)"
            scrollbar_h   = "rgba(0,0,0,0.15)"
            mode_body_c   = "#4a4a4f"
            mode_title_c  = "#1a1a1a"
            badge_c       = accent
            lock_c        = "#1a1a1a"

        self._notice_card.setStyleSheet(
            f"QWidget#termsNoticeCard {{ "
            f"background: {self._badge_bg}; "
            f"border: 1px solid {notice_border}; "
            f"border-left: 3px solid {accent}; "
            f"border-radius: 10px; }}"
        )

        self.setStyleSheet(f"""
/* ── Card ── */
QWidget#termsCard {{
    background: {card_bg};
    border: 1px solid {border};
    border-radius: 16px;
}}

/* ── Title bar ── */
QWidget#termsTitleBar {{
    background: {titlebar_bg};
    border-top-left-radius: 16px;
    border-top-right-radius: 16px;
}}
QLabel#termsLockIcon {{
    font-size: 16px;
    color: {lock_c};
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

/* ── Accent line ── */
QFrame#termsAccentLine {{
    background: {accent};
    border: none;
    max-height: 2px;
}}

/* ── Scroll / body ── */
QScrollArea#termsScroll {{
    background: {scroll_bg};
    border: none;
}}
QWidget#termsBody {{
    background: {body_bg};
}}
QScrollBar:vertical {{
    background: {scrollbar_bg};
    width: 6px;
    border-radius: 3px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {scrollbar_h};
    border-radius: 3px;
    min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* ── Mode notice ── */
QLabel#termsModeIcon {{
    font-size: 15px;
    color: {accent};
    background: transparent;
    font-weight: 700;
}}
QLabel#termsBadge {{
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.2px;
    color: {badge_c};
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
    line-height: 1.5;
    color: {mode_body_c};
    background: transparent;
}}

/* ── Section header ── */
QLabel#termsSectionHeader {{
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.9px;
    color: {section_c};
    background: transparent;
    text-transform: uppercase;
}}

/* ── Body text ── */
QLabel#termsBodyText {{
    font-size: 13px;
    color: {body_c};
    background: transparent;
    line-height: 1.5;
}}

/* ── Bullets ── */
QLabel#termsBulletDot {{
    font-size: 14px;
    font-weight: 700;
    color: {bullet_dot_c};
    background: transparent;
}}
QLabel#termsBulletTitle {{
    font-size: 13px;
    color: {bullet_ttl_c};
    background: transparent;
}}
QLabel#termsBulletDetail {{
    font-size: 12px;
    color: {bullet_det_c};
    background: transparent;
}}

/* ── Footer ── */
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

/* ── Checkbox ── */
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
QCheckBox#termsCb::indicator:hover {{
    border-color: {accent};
}}

/* ── OK button ── */
QPushButton#termsOk {{
    background: {ok_bg};
    color: {ok_c};
    border: none;
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

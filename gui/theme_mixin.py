import os
import re

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QPixmap

from gui.icon_utils import svg_pixmap, svg_icon
from gui._window_shared import ASSETS, STYLES, _make_square_pixmap  # noqa: F401
from gui.sidebar_styles import _SIDEBAR_LIGHT_QSS, _SIDEBAR_DARK_QSS  # noqa: F401


def _scale_qss_fonts(qss: str, factor: float) -> str:
    """
    Scale every ``font-size: Xpt`` value in a QSS string by *factor*.

    This is the only reliable way to zoom a Qt app that uses QSS stylesheets:
    ``widget.setFont()`` is silently overridden by QSS rules, so we must
    regenerate the stylesheet with scaled values instead.

    Only ``pt`` units are scaled (px values are left alone so borders/padding
    stay sharp).  Values are rounded to one decimal place.
    """
    if abs(factor - 1.0) < 0.01:
        return qss   # no-op at 100 %

    def _replace(m: re.Match) -> str:
        orig_pt = float(m.group(1))
        new_pt  = round(orig_pt * factor, 1)
        # Keep at least 6 pt so text never disappears
        new_pt  = max(6.0, new_pt)
        return f"font-size: {new_pt}pt"

    return re.sub(r"font-size:\s*([\d.]+)pt", _replace, qss)


class ThemeMixin:
    """Mixin providing theme management methods for MainWindow."""

    # ════════════════════════════════════════════════════════════════════════ #
    #  THEME
    # ════════════════════════════════════════════════════════════════════════ #

    def _toggle_theme(self):
        self._dark = not self._dark
        self._reload_header_logo()
        self._reload_titlebar_icon()
        self._update_dashboard_pill_icon()
        self._apply_theme()
        self.theme_changed.emit(self._dark)
        # If edit profile page is open, refresh its glow colour and photo
        if self._content_stack.currentIndex() == 6:
            self._apply_profile_page_glow()
            self._apply_profile_btn_style()
            self._apply_overlay_cb_style()
            # Only swap to default logo if no custom photo is set
            if not self._pending_profile.get("logo_path") and not self._logo_path:
                self._reload_profile_page_photo()

    def _apply_theme(self):
        # Content area QSS — scale font-size values by current zoom factor
        qss_file = "dark.qss" if self._dark else "light.qss"
        path = os.path.join(STYLES, qss_file)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                raw_qss = f.read()
            zoom = getattr(self.__class__, "_zoom_factor", 1.0)
            self.setStyleSheet(_scale_qss_fonts(raw_qss, zoom))
        # Sidebar (inverted)
        self._apply_sidebar_theme()
        # Custom title bar
        self._apply_titlebar_theme()
        # Settings page reset icon (theme-sensitive SVG)
        self._update_settings_reset_icon()
        self._update_overlay_reset_icon()

    def _apply_sidebar_theme(self):
        if self._sidebar_widget is None:
            return
        qss = _SIDEBAR_DARK_QSS if self._dark else _SIDEBAR_LIGHT_QSS
        self._sidebar_widget.setStyleSheet(qss)

        # Icon color: light icons on dark sidebar (light mode),
        #             dark icons on light sidebar (dark mode)
        icon_color = "#444444" if self._dark else "#dddddd"

        # Theme toggle button icon
        theme_svg = "dark_theme_icon.svg" if self._dark else "light_theme_icon.svg"
        theme_px = svg_pixmap(os.path.join(ASSETS, theme_svg), icon_color, 18)
        if theme_px:
            self._theme_btn.setIcon(svg_icon(os.path.join(ASSETS, theme_svg), icon_color, 18))
            # Use logical size (18×18), not physical pixel size, to stay inside the button
            self._theme_btn.setIconSize(QSize(18, 18))
        else:
            self._theme_btn.setText("☀" if self._dark else "☾")

        # Edit icon next to profile name
        if self._edit_icon_lbl is not None:
            edit_px = svg_pixmap(os.path.join(ASSETS, "edit_icon.svg"), icon_color, 16)
            if edit_px:
                self._edit_icon_lbl.setPixmap(edit_px)

        # Tutorial nav button icon
        if self._tutorial_btn is not None:
            tut_icon = svg_icon(os.path.join(ASSETS, "tutorial_icon.svg"), icon_color, 16)
            self._tutorial_btn.setIcon(tut_icon)

        # Ask a Question nav button icon
        if self._ask_btn is not None:
            ask_icon = svg_icon(os.path.join(ASSETS, "Ask_a_question_icon.svg"), icon_color, 16)
            self._ask_btn.setIcon(ask_icon)

        # Data Privacy nav button icon
        if self._privacy_btn is not None:
            priv_icon = svg_icon(os.path.join(ASSETS, "data_privacy_icon.svg"), icon_color, 16)
            self._privacy_btn.setIcon(priv_icon)

        # Profile frame — plain square, match sidebar background
        bg = "#f0f0f0" if self._dark else "#1a1a1a"
        if self._profile_frame:
            self._profile_frame.setStyleSheet(
                f"#profileFrame {{ background: {bg}; border-radius: 0px; border: none; }}"
            )
        # Profile name colour is handled by QLabel#profileName rule in sidebar QSS

    def _apply_titlebar_theme(self):
        if not hasattr(self, "_title_bar_widget") or self._title_bar_widget is None:
            return

        if self._dark:
            bg      = "#1a1a1c"
            border  = "rgba(255,255,255,0.06)"
            text_c  = "#111111"
            btn_h   = "rgba(255,255,255,0.09)"
            close_h = "#c42b1c"
            close_t = "#ffffff"
        else:
            bg      = "#ececec"
            border  = "rgba(0,0,0,0.10)"
            text_c  = "#ffffff"
            btn_h   = "rgba(0,0,0,0.08)"
            close_h = "#c42b1c"
            close_t = "#ffffff"

        self._title_bar_widget.setStyleSheet(f"""
QWidget#titleBar {{
    background: {bg};
    border-bottom: 1px solid {border};
}}
QLabel#titleBarIcon {{
    background: transparent;
}}
QLabel#titleBarText {{
    font-size: 12px;
    font-weight: 500;
    color: {text_c};
    background: transparent;
    letter-spacing: 0.2px;
}}
QPushButton#titleBarMin, QPushButton#titleBarMax {{
    background: transparent;
    color: {text_c};
    border: none;
    font-size: 11px;
}}
QPushButton#titleBarMin:hover, QPushButton#titleBarMax:hover {{
    background: {btn_h};
}}
QPushButton#titleBarMin:pressed, QPushButton#titleBarMax:pressed {{
    background: {btn_h};
    opacity: 0.7;
}}
QPushButton#titleBarClose {{
    background: transparent;
    color: {text_c};
    border: none;
    font-size: 11px;
}}
QPushButton#titleBarClose:hover {{
    background: {close_h};
    color: {close_t};
}}
QPushButton#titleBarClose:pressed {{
    background: {close_h};
    opacity: 0.85;
}}
""")

    def _default_logo_path(self) -> str | None:
        """Return the best available default logo path — PNG preferred over SVG."""
        stem = "logo_light" if self._dark else "logo_dark"
        for ext in (".png", ".svg"):
            p = os.path.join(ASSETS, stem + ext)
            if os.path.exists(p):
                return p
        return None

    def _reload_header_logo(self, logo_path: str | None = None):
        if logo_path is not None:
            self._logo_path = logo_path if (logo_path and os.path.exists(logo_path)) else None
        src = self._logo_path if (self._logo_path and os.path.exists(self._logo_path)) \
              else self._default_logo_path()
        if not src or not hasattr(self, "_header_logo"):
            return
        logo_w = self._header_logo.width()
        logo_h = self._header_logo.height()
        size = max(logo_w, logo_h) if max(logo_w, logo_h) > 0 else 76
        px = _make_square_pixmap(src, size)
        if px:
            # Plain square — no corner mask, no circle
            self._header_logo.setPixmap(px)

import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QPixmap

from gui.icon_utils import svg_pixmap, svg_icon
from gui._window_shared import ASSETS, STYLES, _make_square_pixmap  # noqa: F401
from gui.sidebar_styles import _SIDEBAR_LIGHT_QSS, _SIDEBAR_DARK_QSS  # noqa: F401


class ThemeMixin:
    """Mixin providing theme management methods for MainWindow."""

    # ════════════════════════════════════════════════════════════════════════ #
    #  THEME
    # ════════════════════════════════════════════════════════════════════════ #

    def _toggle_theme(self):
        self._dark = not self._dark
        self._reload_header_logo()
        self._update_dashboard_pill_icon()
        self._apply_theme()
        self.theme_changed.emit(self._dark)
        # If edit profile page is open, refresh its glow colour and photo
        if self._content_stack.currentIndex() == 6:
            self._apply_profile_page_glow()
            # Only swap to default logo if no custom photo is set
            if not self._pending_profile.get("logo_path") and not self._logo_path:
                self._reload_profile_page_photo()

    def _apply_theme(self):
        # Content area QSS
        qss_file = "dark.qss" if self._dark else "light.qss"
        path = os.path.join(STYLES, qss_file)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        # Sidebar (inverted)
        self._apply_sidebar_theme()

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

        # Profile frame — no glow border, just match sidebar background
        bg = "#f0f0f0" if self._dark else "#1a1a1a"
        if self._profile_frame:
            self._profile_frame.setStyleSheet(
                f"#profileFrame {{ background: {bg}; border-radius: 10px; border: none; }}"
            )
        # Profile name colour is handled by QLabel#profileName rule in sidebar QSS

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
        px = _make_square_pixmap(src, 76) if src else None
        if px and hasattr(self, "_header_logo"):
            self._header_logo.setPixmap(px)

from operator import index
import os

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QCheckBox, QComboBox, QSlider
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer

from gui._window_shared import ASSETS  # noqa: F401
from gui.icon_utils import svg_icon


class SettingsMixin:
    """Mixin providing Voice Setting page methods for MainWindow."""

    # ── Language map — single source of truth ─────────────────────────────────
    _LANG_ITEMS: list[tuple[str, str]] = [
        ("English",    "en"),
        ("French",     "fr"),
        ("Khmer",      "km"),
        ("Chinese",    "zh"),
        ("Japanese",   "ja"),
        ("Korean",     "ko"),
        ("Thai",       "th"),
        ("Hindi",      "hi"),
        ("Arabic",     "ar"),
        ("German",     "de"),
        ("Spanish",    "es"),
        ("Portuguese", "pt"),
        ("Russian",    "ru"),
        ("Vietnamese", "vi"),
        ("Indonesian", "id"),
    ]

    # ── Voice Setting page ─────────────────────────────────────────────────────

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("contentPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Top action: Reset + Save
        top = QWidget()
        top.setObjectName("pageTopAction")
        t_lay = QHBoxLayout(top)
        t_lay.setContentsMargins(32, 14, 32, 10)
        t_lay.addStretch()

        # Reset button — icon only, themed via _update_settings_reset_icon()
        self._reset_btn = QPushButton()
        self._reset_btn.setObjectName("btnOutline")
        self._reset_btn.setFixedSize(36, 32)
        self._reset_btn.setToolTip("Reset to defaults")
        self._reset_btn.clicked.connect(self._reset_settings)
        t_lay.addWidget(self._reset_btn)
        t_lay.addSpacing(8)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("btnOutline")
        save_btn.setFixedSize(90, 32)
        save_btn.clicked.connect(self._save_settings)
        t_lay.addWidget(save_btn)
        lay.addWidget(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("settingsScroll")
        self._settings_scroll = scroll   # kept so TourOverlay can ensureWidgetVisible

        sc = QWidget()
        sc_lay = QVBoxLayout(sc)
        sc_lay.setContentsMargins(32, 0, 32, 24)
        sc_lay.setSpacing(14)

        # ── Mode + Language ───────────────────────────────────────────────
        ml_row = QHBoxLayout()
        ml_row.setSpacing(0)

        # Mode label + checkboxes (stacked label, then horizontal checkboxes)
        mode_block = QVBoxLayout()
        mode_block.setSpacing(10)
        mode_lbl = QLabel("Mode")
        mode_lbl.setObjectName("settingsLabel")
        mode_block.addWidget(mode_lbl)
        chk_row = QHBoxLayout()
        chk_row.setSpacing(40)
        self._online_btn = QCheckBox("Online Mode")
        self._online_btn.setObjectName("settingsCheck")
        self._online_btn.setChecked(True)
        self._online_btn.toggled.connect(self._on_online_checkbox)
        chk_row.addWidget(self._online_btn)
        self._offline_btn = QCheckBox("Offline Mode")
        self._offline_btn.setObjectName("settingsCheck")
        self._offline_btn.toggled.connect(self._on_offline_checkbox)
        chk_row.addWidget(self._offline_btn)
        chk_row.addStretch()
        mode_block.addLayout(chk_row)

        # Connection status label — updated live by NetworkMonitor
        self._conn_status_lbl = QLabel()
        self._conn_status_lbl.setObjectName("connStatusLbl")
        self._conn_status_lbl.setWordWrap(False)
        font = QFont()
        font.setPointSize(9)
        self._conn_status_lbl.setFont(font)
        mode_block.addWidget(self._conn_status_lbl)

        ml_row.addLayout(mode_block, 1)

        # Language — right-aligned, same row
        lang_block = QVBoxLayout()
        lang_block.setSpacing(10)
        lang_lbl = QLabel("Language")
        lang_lbl.setObjectName("settingsLabel")
        lang_block.addWidget(lang_lbl)
        lang_inline = QHBoxLayout()
        lang_inline.setSpacing(10)
        self._lang_combo = QComboBox()
        self._lang_combo.setObjectName("settingsCombo")
        self._lang_combo.setFixedWidth(160)
        for display_name, _ in self._LANG_ITEMS:
            self._lang_combo.addItem(display_name)
        self._lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        lang_inline.addWidget(self._lang_combo)
        lang_inline.addWidget(self._inline_edit_icon())
        lang_block.addLayout(lang_inline)
        ml_row.addLayout(lang_block, 1)
        sc_lay.addLayout(ml_row)

        # ── Sound + Speed ─────────────────────────────────────────────────
        ss_row = QHBoxLayout()
        ss_row.setSpacing(0)

        sound_block = QVBoxLayout()
        sound_block.setSpacing(10)
        sound_lbl = QLabel("Sound")
        sound_lbl.setObjectName("settingsLabel")
        sound_block.addWidget(sound_lbl)
        sound_inline = QHBoxLayout()
        sound_inline.setSpacing(10)
        self._sound_input = QComboBox()
        self._sound_input.setObjectName("settingsCombo")
        self._sound_input.setFixedWidth(200)
        self._sound_input.currentIndexChanged.connect(self._on_sound_combo_changed)
        sound_inline.addWidget(self._sound_input)
        sound_inline.addWidget(self._inline_edit_icon())
        sound_inline.addStretch()
        sound_block.addLayout(sound_inline)
        ss_row.addLayout(sound_block, 1)

        speed_block = QVBoxLayout()
        speed_block.setSpacing(10)
        speed_lbl = QLabel("Speed")
        speed_lbl.setObjectName("settingsLabel")
        speed_block.addWidget(speed_lbl)
        spd_inline = QHBoxLayout()
        spd_inline.setSpacing(10)
        spd_inline.addWidget(QLabel("🐢"))
        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(50, 400)
        self._speed_slider.setValue(175)
        self._speed_slider.setObjectName("speedSlider")
        self._speed_slider.valueChanged.connect(self._on_speed_changed)
        spd_inline.addWidget(self._speed_slider, 1)
        spd_inline.addWidget(QLabel("🐇"))
        speed_block.addLayout(spd_inline)
        ss_row.addLayout(speed_block, 1)
        sc_lay.addLayout(ss_row)

        # Hidden combo (kept for AppController / TourOverlay compat)
        self._voice_combo = QComboBox()
        self._voice_combo.setVisible(False)
        self._voice_combo.currentIndexChanged.connect(self._on_voice_changed)
        sc_lay.addWidget(self._voice_combo)

        # Hidden volume slider (kept for compat)
        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(100)
        self._vol_slider.setVisible(False)
        self._vol_slider.valueChanged.connect(self._on_volume_changed)
        sc_lay.addWidget(self._vol_slider)

        sc_lay.addStretch()
        scroll.setWidget(sc)
        lay.addWidget(scroll, 1)
        return page

    def _shape_row(self, label: str, is_circle: bool,
                   checked: bool) -> tuple[QCheckBox, QWidget]:
        """Returns (checkbox, row_widget) for a shape option with previews."""
        row = QWidget()
        row_lay = QVBoxLayout(row)
        row_lay.setContentsMargins(0, 0, 0, 0)
        row_lay.setSpacing(14)

        chk = QCheckBox(label)
        chk.setObjectName("settingsCheck")
        chk.setChecked(checked)
        row_lay.addWidget(chk)

        previews_row = QHBoxLayout()
        previews_row.setSpacing(14)
        previews_row.addWidget(self._mini_preview(is_circle, dark=True))
        previews_row.addWidget(self._mini_preview(is_circle, dark=False))
        previews_row.addStretch()
        row_lay.addLayout(previews_row)
        return chk, row

    def _mini_preview(self, is_circle: bool, dark: bool) -> QWidget:
        """Shape preview card using SVG pill icon + description text."""
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtGui import QPainter

        # SVG native: 219×72 — display at inner width preserving aspect ratio
        _inner_w = 236
        _pill_h  = int(_inner_w * 72 / 219)   # ≈ 78px

        card = QWidget()
        card.setFixedSize(260, _pill_h + 80)
        card.setObjectName("miniPreviewDark" if dark else "miniPreviewLight")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(12, 10, 12, 10)
        card_lay.setSpacing(8)

        if is_circle:
            svg_name = "overlay_circle_dark_icon.svg" if dark else "overlay_circle_light_icon.svg"
        else:
            svg_name = "overlay_retangle_dark_icon.svg" if dark else "overlay_retangle_light_icon.svg"

        svg_path = os.path.join(ASSETS, svg_name)
        pill_lbl = QLabel()
        pill_lbl.setFixedSize(_inner_w, _pill_h)
        pill_lbl.setObjectName("miniPillSvg")
        if os.path.exists(svg_path):
            # Render SVG → QPixmap so embedded base64 images are resolved
            app_inst = QApplication.instance()
            dpr = app_inst.primaryScreen().devicePixelRatio() if app_inst else 1.0
            phys_w = int(_inner_w * dpr)
            phys_h = int(_pill_h  * dpr)
            px = QPixmap(phys_w, phys_h)
            px.fill(Qt.GlobalColor.transparent)
            renderer = QSvgRenderer(svg_path)
            painter  = QPainter(px)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            renderer.render(painter)
            painter.end()
            px.setDevicePixelRatio(dpr)
            pill_lbl.setPixmap(px)
        card_lay.addWidget(pill_lbl)

        speech = QLabel(
            "Hi, my name is Veaja. what do you want me to read for you. I'm here to "
            "assist you brother. And don't mind me if my voice isn't sweat enough. "
            "Haa just kidding, cuz I'm a friendly ai assistance. No matter"
        )
        speech.setObjectName("miniSpeechLight" if dark else "miniSpeechDark")
        speech.setWordWrap(True)
        speech.setFont(QFont("-apple-system", 8))
        card_lay.addWidget(speech, 1)
        return card

    def _inline_edit_icon(self) -> QLabel:
        _svg = (
            '<svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M11.5 1.5a1.5 1.5 0 0 1 2.12 2.12l-8.5 8.5-2.83.71.71-2.83z"'
            ' stroke="#888" stroke-width="1.2" fill="none"'
            ' stroke-linecap="round" stroke-linejoin="round"/>'
            '</svg>'
        )
        px = QPixmap(13, 13)
        px.fill(Qt.GlobalColor.transparent)
        renderer = QSvgRenderer(_svg.encode())
        p = QPainter(px)
        renderer.render(p)
        p.end()
        lbl = QLabel()
        lbl.setPixmap(px)
        lbl.setFixedSize(13, 13)
        lbl.setObjectName("inlineEdit")
        return lbl

    def _on_online_checkbox(self, checked: bool):
        """Online checkbox toggled — sync the offline checkbox and notify."""
        self._offline_btn.blockSignals(True)
        self._offline_btn.setChecked(not checked)
        self._offline_btn.blockSignals(False)
        self.mode_changed.emit(checked)   # True = online

    def _on_offline_checkbox(self, checked: bool):
        """Offline checkbox toggled — sync the online checkbox and notify."""
        self._online_btn.blockSignals(True)
        self._online_btn.setChecked(not checked)
        self._online_btn.blockSignals(False)
        self.mode_changed.emit(not checked)  # True = online, so offline → emit False

    def _on_lang_changed(self, index: int):
        """Language combo changed — notify AppController."""
        if 0 <= index < len(self._LANG_ITEMS):
            lang_code = self._LANG_ITEMS[index][1]
        else:
            lang_code = "en"
        self.lang_changed.emit(lang_code)

    def update_connection_status(self, is_online: bool):
        """Called by AppController whenever internet connectivity changes.

        - Updates the status label with a coloured message.
        - Locks/unlocks the Online Mode checkbox: when offline the user cannot
          select online mode (prevents crashes from trying to reach the network).
        """
        # Track so _reset_settings can decide the correct default mode
        self._net_is_online = is_online

        if not hasattr(self, "_conn_status_lbl"):
            return

        if is_online:
            self._conn_status_lbl.setText("Your current state is online")
            self._conn_status_lbl.setStyleSheet("color: #1a7fe8; font-style: normal;")
            # Re-enable online mode checkbox so the user can switch back
            self._online_btn.setEnabled(True)
            self._online_btn.setToolTip("")
        else:
            self._conn_status_lbl.setText(
                "You are offline — please check internet connection"
            )
            self._conn_status_lbl.setStyleSheet("color: #d9363e; font-style: normal;")
            # Force switch to offline mode and lock the online checkbox
            self._online_btn.blockSignals(True)
            self._online_btn.setChecked(False)
            self._online_btn.blockSignals(False)
            self._offline_btn.blockSignals(True)
            self._offline_btn.setChecked(True)
            self._offline_btn.blockSignals(False)
            self._online_btn.setEnabled(False)
            self._online_btn.setToolTip(
                "Online Mode is unavailable — no internet connection detected"
            )

    # ── Save ──────────────────────────────────────────────────────────────────

    def _save_settings(self):
        """Collect the current control state, persist via signal, go to dashboard."""
        settings = {
            "speed":       self._speed_slider.value(),
            "voice_index": self._sound_input.currentIndex(),
            "volume":      self._vol_slider.value() / 100.0,
        }
        self.settings_save_requested.emit(settings)
        self._navigate(0)

    # ── Reset ─────────────────────────────────────────────────────────────────

    def _reset_settings(self):
        """Restore every Voice Setting control to its default value."""

        # 1. Speed → 175
        self._speed_slider.setValue(175)

        # 2. Mode → online if internet available, else offline
        is_online = getattr(self, "_net_is_online", True) and \
                    self._tts is not None and self._tts.is_edge_available()
        self._online_btn.blockSignals(True)
        self._offline_btn.blockSignals(True)
        self._online_btn.setChecked(is_online)
        self._offline_btn.setChecked(not is_online)
        self._online_btn.blockSignals(False)
        self._offline_btn.blockSignals(False)
        self.mode_changed.emit(is_online)

        # 3. Language → English (index 0)
        self._lang_combo.setCurrentIndex(0)

        # 4. Voice / Sound → first available voice
        self._sound_input.blockSignals(True)
        self._voice_combo.blockSignals(True)
        self._sound_input.setCurrentIndex(0)
        self._voice_combo.setCurrentIndex(0)
        self._sound_input.blockSignals(False)
        self._voice_combo.blockSignals(False)
        if self._tts and self._sound_input.count() > 0:
            self._tts.set_voice(self._sound_input.itemData(0))

        # 5. Volume → 100 %
        self._vol_slider.setValue(100)

    def _update_settings_reset_icon(self):
        """Refresh the reset button icon to match the current theme."""
        if not hasattr(self, "_reset_btn"):
            return
        icon_color = "#c7c7cc" if self._dark else "#3a3a3c"
        icon_path = os.path.join(ASSETS, "restart_icon.svg")
        self._reset_btn.setIcon(svg_icon(icon_path, icon_color, 16))
        from PyQt6.QtCore import QSize
        self._reset_btn.setIconSize(QSize(16, 16))
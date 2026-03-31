"""
AppController — central mediator that wires all components together.

Lifecycle:
  splash → main_window shown → clipboard/selection monitor active → overlay reacts
"""

import platform
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, Qt

from core.tts_engine import TTSEngine
from core.selection_monitor import SelectionMonitor
from gui.main_window import MainWindow
from gui.overlay_widget import OverlayWidget
from gui.tray_icon import TrayIcon
from services.window_manager import WindowManager


class AppController(QObject):
    def __init__(self, app: QApplication):
        super().__init__()
        self._app = app
        self._tts = TTSEngine()

        # Build components (not shown yet)
        self._main_window   = MainWindow(tts_engine=self._tts)
        self._overlay       = OverlayWidget()
        self._tray          = TrayIcon(dark_mode=self._is_dark_mode())
        self._monitor       = SelectionMonitor()

        # WindowManager — controls overlay ↔ main-window visibility rules
        self._wm = WindowManager(self._main_window, self._overlay, parent=self)

        self._wire_signals()
        self._populate_voices()

        # Mac: keep running when all windows are closed (live in tray)
        if platform.system() == "Darwin":
            app.setQuitOnLastWindowClosed(False)

    # ------------------------------------------------------------------ #
    # Signal wiring
    # ------------------------------------------------------------------ #

    def _wire_signals(self):
        # Selection monitor → overlay + main window
        self._monitor.text_ready.connect(self._on_text_ready)

        # Overlay user actions
        self._overlay.read_requested.connect(self._speak)
        self._overlay.stop_requested.connect(self._stop_speaking)
        self._overlay.hide_requested.connect(self._overlay.hide_overlay)
        self._overlay.settings_requested.connect(self._wm.show_main)

        # Main window user actions
        self._main_window.read_requested.connect(self._speak)
        self._main_window.stop_requested.connect(self._stop_speaking)
        self._main_window.quit_requested.connect(self._quit)
        self._main_window.theme_changed.connect(self._on_theme_changed)

        # Tray → always show main via WindowManager
        self._tray.show_window_requested.connect(self._wm.show_main)
        self._tray.quit_requested.connect(self._quit)

    def _populate_voices(self):
        voices = self._tts.get_voices()
        self._main_window.populate_voices(voices)

    # ------------------------------------------------------------------ #
    # Public accessors (used by main.py)
    # ------------------------------------------------------------------ #

    @property
    def window_manager(self) -> "WindowManager":
        return self._wm

    # ------------------------------------------------------------------ #
    # Entry point (called by main.py after splash closes)
    # ------------------------------------------------------------------ #

    def start(self):
        self._wm.show_main()

    # ------------------------------------------------------------------ #
    # Text ready (from clipboard / selection)
    # ------------------------------------------------------------------ #

    def _on_text_ready(self, text: str):
        # Update both overlay and main window text area
        self._overlay.set_text(text)
        self._main_window.set_text(text)

    # ------------------------------------------------------------------ #
    # TTS
    # ------------------------------------------------------------------ #

    def _speak(self, text: str):
        if not text.strip():
            return
        self._tts.speak(
            text,
            on_preparing=self._on_preparing_speech,
            on_start=self._on_speaking_started,
            on_finish=self._on_speaking_finished,
            on_error=self._on_speaking_error,
        )

    def _stop_speaking(self):
        self._tts.stop()
        self._on_speaking_finished()

    def _on_preparing_speech(self):
        """Synthesis has started — show processing state immediately."""
        self._overlay.set_processing(True)
        self._main_window.set_processing(True)

    def _on_speaking_started(self):
        """First sentence is now playing — switch to speaking state."""
        self._overlay.set_processing(False)
        self._overlay.set_speaking(True)
        self._main_window.set_speaking(True)

    def _on_speaking_finished(self):
        self._overlay.set_processing(False)
        self._overlay.set_speaking(False)
        self._main_window.set_processing(False)
        self._main_window.set_speaking(False)

    def _on_speaking_error(self, msg: str):
        self._on_speaking_finished()
        self._tray.show_notification("Veaja — TTS error", msg)

    # ------------------------------------------------------------------ #
    # Window management
    # ------------------------------------------------------------------ #

    def _show_main_window(self):
        self._main_window.show()
        self._main_window.raise_()
        self._main_window.activateWindow()

    def _on_theme_changed(self, dark: bool):
        self._tray.update_icon(dark)
        self._overlay.update_theme(dark)

    def _show_main_window(self):
        self._wm.show_main()

    # ------------------------------------------------------------------ #
    # Quit
    # ------------------------------------------------------------------ #

    def _quit(self):
        self._monitor.stop()
        self._tts.stop()
        self._tray.hide()
        QApplication.quit()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _is_dark_mode() -> bool:
        from PyQt6.QtGui import QPalette
        app = QApplication.instance()
        if app is None:
            return False
        return app.palette().color(QPalette.ColorRole.Window).lightness() < 128

"""
AppController — central mediator that wires all components together.

Lifecycle:
  splash → main_window shown → clipboard/selection monitor active → overlay reacts
"""

import platform
from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtCore import QObject, QTimer

from core.tts_engine import TTSEngine
from core.selection_monitor import SelectionMonitor
from core.audio_history import AudioHistory
from core.profile import ProfileManager
from core.language import filter_for_tts, language_display_name
from gui.main_window import MainWindow, ReadState
from gui.overlay_widget import OverlayWidget
from gui.tray_icon import TrayIcon
from gui.terms_dialog import TermsDialog
from gui.profile_dialog import ProfileDialog
from services.window_manager import WindowManager


class AppController(QObject):
    def __init__(self, app: QApplication):
        super().__init__()
        self._app   = app
        self._tts   = TTSEngine()
        self._audio = AudioHistory()
        self._profile = ProfileManager(parent=self)

        # Build components (not shown yet)
        self._main_window = MainWindow(tts_engine=self._tts)
        self._overlay     = OverlayWidget()
        self._tray        = TrayIcon(dark_mode=self._is_dark_mode())
        self._monitor     = SelectionMonitor()

        # WindowManager — controls overlay ↔ main-window visibility rules
        self._wm = WindowManager(self._main_window, self._overlay, parent=self)
        self._current_text: str = ""

        self._wire_signals()
        self._populate_voices()
        # Reflect the initial online/offline state in the UI
        self._main_window.set_online_mode(self._tts.is_edge_available())

        # Mac: keep running when all windows are closed (live in tray)
        if platform.system() == "Darwin":
            app.setQuitOnLastWindowClosed(False)

    # ------------------------------------------------------------------ #
    # Signal wiring
    # ------------------------------------------------------------------ #

    def _wire_signals(self):
        # Selection monitor → overlay + main window
        self._monitor.text_ready.connect(self._on_text_ready)
        # Ctrl+R → read clipboard directly
        self._monitor.read_clipboard_hotkey.connect(self._on_read_hotkey)

        # Overlay user actions
        self._overlay.read_requested.connect(self._speak)
        self._overlay.stop_requested.connect(self._on_overlay_stop)
        self._overlay.hide_requested.connect(self._overlay.hide_overlay)
        self._overlay.settings_requested.connect(self._wm.show_main)
        self._overlay.reset_requested.connect(self._on_reset_requested)

        # Main window user actions
        self._main_window.read_requested.connect(self._speak)
        self._main_window.stop_requested.connect(self._stop_speaking)
        self._main_window.pause_requested.connect(self._pause_speaking)
        self._main_window.resume_requested.connect(self._resume_speaking)
        self._main_window.quit_requested.connect(self._quit)
        self._main_window.theme_changed.connect(self._on_theme_changed)
        self._main_window.terms_requested.connect(self._show_terms)
        self._main_window.profile_requested.connect(self._show_profile_dialog)
        self._main_window.mode_changed.connect(self._on_mode_changed)
        self._main_window.tour_requested.connect(self._show_tour)

        # Profile changes → update UI
        self._profile.profile_changed.connect(self._on_profile_changed)

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
        # Load and apply profile to all components
        profile = self._profile.load()
        self._main_window.apply_profile(profile)
        self._overlay.apply_profile(profile)

        # Push the correct dark/light theme to the overlay at startup
        # so it never relies on live QPalette detection alone.
        self._overlay.update_theme(self._is_dark_mode())

        self._wm.show_main()

        # Show terms dialog on first launch
        if not profile.get("terms_accepted", False):
            QTimer.singleShot(600, self._show_terms_on_launch)

    # ------------------------------------------------------------------ #
    # Text ready (from clipboard / selection)
    # ------------------------------------------------------------------ #

    def _on_text_ready(self, text: str):
        from PyQt6.QtGui import QCursor
        # New text always replaces the current session — stop whatever is playing
        # so the Read button (and Ctrl+R) starts fresh instead of pause/resuming.
        if self._tts.is_speaking() or self._tts.is_paused():
            self._tts.stop()
            self._on_speaking_finished()   # reset UI to IDLE immediately
        self._overlay.set_text(text, auto_show=False)
        self._main_window.set_text(text)
        # Position rule: snap near the cursor ONLY on first appearance.
        # If the overlay is already visible, leave it exactly where it is.
        if not self._overlay.isVisible():
            pos = QCursor.pos()
            self._overlay.show_near(pos.x(), pos.y())
        else:
            self._overlay.show_overlay()   # bring to front without moving

    # ------------------------------------------------------------------ #
    # Ctrl+R hotkey — read current clipboard immediately
    # ------------------------------------------------------------------ #

    def _on_read_hotkey(self):
        """
        Ctrl+R behaviour:
          1. SelectionMonitor already simulated Ctrl+C — clipboard has selected text.
          2. If overlay is hidden → pop it up near the mouse cursor (top-left of selection).
          3. Start reading immediately.
        """
        from PyQt6.QtGui import QCursor
        text = QApplication.clipboard().text().strip()
        if not text:
            return
        self._main_window.set_text(text)
        self._overlay.set_text(text, auto_show=False)
        # Position rule: snap near the cursor ONLY on first appearance.
        # If the overlay is already visible, leave it exactly where it is.
        if not self._overlay.isVisible():
            pos = QCursor.pos()
            self._overlay.show_near(pos.x(), pos.y())
        else:
            self._overlay.show_overlay()   # bring to front without moving
        self._speak(text)

    # ------------------------------------------------------------------ #
    # TTS
    # ------------------------------------------------------------------ #

    def _speak(self, text: str):
        if not text.strip():
            return

        # ── Language protection layer ─────────────────────────────────────────
        # Filter text to the current TTS language (English mode by default).
        # Never crashes — filter_for_tts always returns a safe result.
        try:
            filtered, was_filtered, detected_lang = filter_for_tts(text, target_lang="en")
        except Exception:
            filtered, was_filtered, detected_lang = text, False, "en"

        if not filtered.strip():
            # Nothing readable in English — notify and abort gracefully
            lang_name = language_display_name(detected_lang)
            self._tray.show_notification(
                "Veaja — Language not supported",
                f"No English text found in selection. "
                f"(Detected: {lang_name})\n"
                "Switch to Offline mode or select English text."
            )
            return

        if was_filtered:
            # Inform user that only the English portion will be read
            lang_name = language_display_name(detected_lang)
            self._tray.show_notification(
                "Veaja — Mixed language",
                f"Detected: {lang_name}. Reading English portions only."
            )
            # Update text box to show exactly what will be read
            self._main_window.set_text(filtered)
            self._overlay.set_text(filtered, auto_show=False)

        # ── Speak ─────────────────────────────────────────────────────────────
        self._current_text = filtered
        session_path = self._audio.next_session_path()

        def _on_word(start: int, end: int):
            # Dashboard: cumulative yellow progress bar
            self._main_window.highlight_word(start, end)
            # Overlay pill: karaoke display (works even in PDFs / Word)
            self._overlay.set_current_word(start, end)

        try:
            self._tts.speak(
                filtered,
                on_preparing      = self._on_preparing_speech,
                on_start          = self._on_speaking_started,
                on_finish         = self._on_speaking_finished,
                on_error          = self._on_speaking_error,
                on_paused         = self._on_speaking_paused,
                on_resumed        = self._on_speaking_resumed,
                on_word_highlight = _on_word,
                session_path      = session_path,
            )
        except Exception as exc:
            # Catch any unexpected TTS startup failure — never crash the app
            self._on_speaking_finished()
            self._tray.show_notification("Veaja — TTS error", str(exc))

    def _stop_speaking(self):
        self._tts.stop()
        self._on_speaking_finished()

    def _pause_speaking(self):
        if self._tts.supports_pause():
            self._tts.pause()
            # UI update happens via on_paused callback from the worker signal
        else:
            # pyttsx3 has no pause — treat as stop
            self._stop_speaking()

    def _resume_speaking(self):
        self._tts.resume()
        # UI update happens via on_resumed callback

    def _on_overlay_stop(self):
        """Overlay click during active state — pause if speaking, resume if paused."""
        if self._tts.is_paused():
            self._resume_speaking()
        elif self._tts.is_speaking():
            self._pause_speaking()
        else:
            self._stop_speaking()

    def _on_reset_requested(self):
        """⟳ button — stop current reading and restart from the beginning."""
        if not self._current_text:
            return
        self._tts.stop()
        self._on_speaking_finished()
        # Small delay so the stop completes cleanly before re-starting
        QTimer.singleShot(200, lambda: self._speak(self._current_text))

    # ── TTS lifecycle callbacks ───────────────────────────────────────────────

    def _on_preparing_speech(self):
        self._overlay.set_processing(True)
        self._main_window.set_read_state(ReadState.PROCESSING)

    def _on_speaking_started(self):
        self._overlay.set_processing(False)
        self._overlay.set_speaking(True)
        self._main_window.set_read_state(ReadState.SPEAKING)
        self._main_window.mark_reading_started(self._current_text)

    def _on_speaking_paused(self):
        self._overlay.set_speaking(False)
        self._overlay.set_paused(True)
        self._main_window.set_read_state(ReadState.PAUSED)

    def _on_speaking_resumed(self):
        self._overlay.set_paused(False)
        self._overlay.set_speaking(True)
        self._main_window.set_read_state(ReadState.SPEAKING)

    def _on_speaking_finished(self):
        self._overlay.set_processing(False)
        self._overlay.set_speaking(False)
        self._overlay.set_paused(False)
        self._main_window.set_read_state(ReadState.IDLE)
        self._main_window.clear_highlight()
        self._main_window.mark_reading_started("")   # nothing playing now

    def _on_speaking_error(self, msg: str):
        self._on_speaking_finished()
        self._tray.show_notification("Veaja — TTS error", msg)

    # ------------------------------------------------------------------ #
    # Window management
    # ------------------------------------------------------------------ #

    def _on_mode_changed(self, online: bool):
        """User toggled Online/Offline in the dashboard."""
        self._tts.set_forced_offline(not online)
        # Refresh voice list to show the right voices for the new mode
        self._main_window.populate_voices(self._tts.get_voices())

    def _on_theme_changed(self, dark: bool):
        self._tray.update_icon(dark)
        self._overlay.update_theme(dark)

    # ------------------------------------------------------------------ #
    # Terms dialog
    # ------------------------------------------------------------------ #

    def _show_terms_on_launch(self):
        dlg = TermsDialog(
            online_mode=self._tts.is_edge_available(),
            parent=self._main_window,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.dont_show_again():
            profile = self._profile.get()
            profile["terms_accepted"] = True
            self._profile.save(profile)

    def _show_terms(self):
        TermsDialog(
            online_mode=self._tts.is_edge_available(),
            parent=self._main_window,
        ).exec()

    # ------------------------------------------------------------------ #
    # Profile dialog
    # ------------------------------------------------------------------ #

    def _show_profile_dialog(self):
        dlg = ProfileDialog(self._profile.get(), parent=self._main_window)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._profile.save(dlg.get_profile())

    def _show_tour(self):
        from gui.tour_overlay import TourOverlay
        tour = TourOverlay(self._main_window)
        tour.show()

    def _on_profile_changed(self, profile: dict):
        self._main_window.apply_profile(profile)
        self._overlay.apply_profile(profile)        # swap overlay logo ↔ user avatar
        name = profile.get("app_name", "Veaja")
        try:
            self._tray._tray.setToolTip(f"{name} — running")
        except Exception:
            pass

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

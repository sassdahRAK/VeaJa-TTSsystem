"""
services/app_controller.py — Veaja Application Controller
==========================================================

Central mediator that wires every component together and manages the
overall application lifecycle.

Lifecycle
---------
  splash  →  start()  →  main window shown
                       →  clipboard / selection monitor active
                       →  overlay pill reacts to text + hotkeys

Component graph
---------------
  AppController
    ├── TTSEngine           — speaks text via edge-tts (online) or pyttsx3 (offline)
    ├── AudioHistory        — persists the last N spoken texts
    ├── ProfileManager      — loads / saves user preferences to disk
    ├── MainWindow          — PyQt6 UI (dashboard, settings, history, FAQ)
    ├── OverlayWidget       — floating pill overlay (always on top)
    ├── TrayIcon            — system tray icon + notifications
    ├── SelectionMonitor    — global Ctrl+C / Ctrl+R hotkey listener
    ├── WindowManager       — controls overlay ↔ main window visibility rules
    └── NetworkMonitor      — background internet connectivity checker
"""

import platform

from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtCore    import QObject, QTimer

from config.settings        import MAX_INPUT_CHARS
from core.tts_engine        import TTSEngine
from core.selection_monitor import SelectionMonitor
from core.audio_history     import AudioHistory
from core.profile           import ProfileManager
from core.language          import filter_for_tts, language_display_name
from core.network_monitor   import NetworkMonitor
from gui.main_window        import MainWindow, ReadState
from gui.overlay_widget     import OverlayWidget
from gui.tray_icon          import TrayIcon
from gui.terms_dialog       import TermsDialog
from gui.profile_dialog     import ProfileDialog
from services.window_manager import WindowManager


class AppController(QObject):
    """
    Wires all Veaja components together and owns the top-level event routing.

    Instantiated once in main.py after the splash screen closes.
    Call start() to display the main window and activate all monitors.
    """

    def __init__(self, app: QApplication):
        super().__init__()

        self._app     = app
        self._tts     = TTSEngine()
        self._audio   = AudioHistory()
        self._profile = ProfileManager(parent=self)

        # ── Build UI components (not yet visible) ──────────────────────────────
        self._main_window = MainWindow(tts_engine=self._tts)
        self._overlay     = OverlayWidget()
        self._tray        = TrayIcon(dark_mode=self._is_dark_mode())
        self._monitor     = SelectionMonitor()

        # WindowManager enforces the overlay ↔ main-window visibility rule:
        # when the overlay pill is shown, the main window is hidden, and vice versa.
        self._wm = WindowManager(self._main_window, self._overlay, parent=self)

        # Tracks the text most recently sent to TTS for the ⟳ restart feature
        self._current_text: str = ""

        # NetworkMonitor polls internet connectivity every 10 s in a background thread
        self._net_monitor = NetworkMonitor(parent=self, interval_ms=10_000)

        self._wire_signals()
        self._populate_voices()

        # Reflect the correct online / offline state in the UI immediately
        self._main_window.set_online_mode(self._tts.is_edge_available())

        # macOS: keep the process alive when all windows are closed (live in tray)
        if platform.system() == "Darwin":
            app.setQuitOnLastWindowClosed(False)

    # ── Signal wiring ─────────────────────────────────────────────────────────

    def _wire_signals(self) -> None:
        """Connect every Qt signal to its handler."""

        # ── SelectionMonitor ──────────────────────────────────────────────────
        # Ctrl+C with selected text → load text into overlay + main window
        self._monitor.text_ready.connect(self._on_text_ready)
        # Ctrl+R → immediately read whatever is in the clipboard
        self._monitor.read_clipboard_hotkey.connect(self._on_read_hotkey)

        # ── Overlay pill user actions ──────────────────────────────────────────
        self._overlay.read_requested.connect(self._speak)
        self._overlay.stop_requested.connect(self._on_overlay_stop)
        self._overlay.hide_requested.connect(self._overlay.hide_overlay)
        self._overlay.settings_requested.connect(self._wm.show_main)
        self._overlay.reset_requested.connect(self._on_reset_requested)

        # ── Main window user actions ───────────────────────────────────────────
        self._main_window.read_requested.connect(self._speak)
        self._main_window.stop_requested.connect(self._stop_speaking)
        self._main_window.pause_requested.connect(self._pause_speaking)
        self._main_window.resume_requested.connect(self._resume_speaking)
        self._main_window.quit_requested.connect(self._quit)
        self._main_window.theme_changed.connect(self._on_theme_changed)
        self._main_window.shape_changed.connect(self._overlay.set_shape)
        self._main_window.anim_spin_changed.connect(self._overlay.set_anim_spin)
        self._main_window.terms_requested.connect(self._show_terms)
        self._main_window.profile_requested.connect(self._show_profile_dialog)
        self._main_window.mode_changed.connect(self._on_mode_changed)
        self._main_window.settings_save_requested.connect(self._on_settings_save)
        self._main_window.tour_requested.connect(self._show_tour)
        self._main_window.lang_changed.connect(self._on_lang_changed)  # ADD THIS

        # Profile page live save (e.g. overlay-show checkbox toggle)
        self._main_window.profile_save_requested.connect(
            self._on_profile_save_requested
        )

        # ProfileManager emits profile_changed after every save → update UI
        self._profile.profile_changed.connect(self._on_profile_changed)

        # NetworkMonitor → auto-switch TTS mode + update status label
        self._net_monitor.connectivity_changed.connect(
            self._on_connectivity_changed
        )

        # System tray → always show main window via WindowManager
        self._tray.show_window_requested.connect(self._wm.show_main)
        self._tray.quit_requested.connect(self._quit)

    def _populate_voices(self) -> None:
        """Fetch available voices from the TTS engine and push them to the UI."""
        voices = self._tts.get_voices()
        self._main_window.populate_voices(voices)

    # ── Public accessor ───────────────────────────────────────────────────────

    @property
    def window_manager(self) -> WindowManager:
        """Expose the WindowManager for main.py bootstrapping."""
        return self._wm

    # ── Application entry point ───────────────────────────────────────────────

    def start(self) -> None:
        """
        Called by main.py after the splash screen closes.

        Loads the user profile, applies it to all components, shows the main
        window, and (on first launch) presents the Terms dialog.
        """
        profile = self._profile.load()
        self._main_window.apply_profile(profile)
        self._overlay.apply_profile(profile)

        # Push the saved dark/light theme to the overlay so it never relies
        # solely on live QPalette detection at startup
        self._overlay.update_theme(self._is_dark_mode())

        self._wm.show_main()

        # First-launch: show Terms dialog after a short delay so the window
        # is fully painted before the modal appears
        if not profile.get("terms_accepted", False):
            QTimer.singleShot(600, self._show_terms_on_launch)

    # ── Text ready (Ctrl+C / selection monitor) ───────────────────────────────

    def _on_text_ready(self, text: str) -> None:
        """
        Handle new text captured by the selection monitor (Ctrl+C).

        Always stops any in-progress speech so the Read button starts fresh
        rather than toggling into pause/resume mode on new content.
        """
        from PyQt6.QtGui import QCursor

        # Stop current playback so the next action is always a fresh read
        if self._tts.is_speaking() or self._tts.is_paused():
            self._tts.stop()
            self._on_speaking_finished()   # reset UI to IDLE immediately

        self._overlay.set_text(text, auto_show=False)
        self._main_window.set_text(text)

        # Position rule: snap the pill near the cursor only on its first appearance.
        # If the overlay is already visible, leave it where the user put it.
        if not self._overlay.isVisible():
            pos = QCursor.pos()
            self._overlay.show_near(pos.x(), pos.y())
        else:
            self._overlay.show_overlay()   # bring to front without moving

    # ── Ctrl+R hotkey — read clipboard immediately ────────────────────────────

    def _on_read_hotkey(self) -> None:
        """
        Handle the global Ctrl+R hotkey.

        Flow:
          1. SelectionMonitor already simulated Ctrl+C → clipboard holds the
             selected text from whatever app the user is in.
          2. Load that text into the overlay and main window.
          3. Show the overlay pill near the cursor (first appearance only).
          4. Start reading immediately.
        """
        from PyQt6.QtGui import QCursor

        text = QApplication.clipboard().text().strip()
        if not text:
            return

        self._main_window.set_text(text)
        self._overlay.set_text(text, auto_show=False)

        # Same position rule as _on_text_ready
        if not self._overlay.isVisible():
            pos = QCursor.pos()
            self._overlay.show_near(pos.x(), pos.y())
        else:
            self._overlay.show_overlay()

        self._speak(text)

    # ── TTS — speak ───────────────────────────────────────────────────────────

    def _speak(self, text: str) -> None:
        """
        Speak ``text`` through the TTS engine.

        Language protection
        -------------------
        The text is filtered to English before speaking.  If no English content
        is found the user gets a tray notification and speech is aborted.
        If mixed-language content is found, only the English portion is read
        and the text boxes are updated to reflect exactly what will be spoken.

        Word highlighting
        -----------------
        The ``on_word_highlight`` callback fires for every word boundary event
        from the TTS engine, updating both the dashboard progress bar and the
        overlay pill's karaoke display in real time.
        """
        if not text.strip():
            return

        # ── Input length cap (applied before language detection) ───────────────
        if len(text) > MAX_INPUT_CHARS:
            text = text[:MAX_INPUT_CHARS]
            self._tray.show_notification(
                "Veaja — Text truncated",
                f"Input was too long. Reading the first {MAX_INPUT_CHARS:,} characters.",
            )

        # ── Language filter ────────────────────────────────────────────────────
        active_lang = self._tts.get_active_language()   # ADD THIS
        try:
            filtered, was_filtered, detected_lang = filter_for_tts(
                text, target_lang=active_lang            # CHANGE "en" → active_lang
            )
        except Exception:
            filtered, was_filtered, detected_lang = text, False, active_lang

        if not filtered.strip():
            lang_name = language_display_name(detected_lang)
            self._tray.show_notification(
                "Veaja — Language not supported",
                f"No {language_display_name(active_lang)} text found in selection. "
                f"(Detected: {lang_name})\n"
                "Switch language or select matching text.",
            )
            return

        if was_filtered:
            # Inform the user that only the English portion will be read
            lang_name = language_display_name(detected_lang)
            self._tray.show_notification(
                "Veaja — Mixed language",
                f"Detected: {lang_name}. Reading English portions only.",
            )
            # Update text boxes to show exactly what will be spoken
            self._main_window.set_text(filtered)
            self._overlay.set_text(filtered, auto_show=False)

        # ── Kick off TTS ───────────────────────────────────────────────────────
        self._current_text = filtered
        session_path = self._audio.next_session_path()

        def _on_word(start: int, end: int) -> None:
            # Dashboard: advance the cumulative yellow progress highlight
            self._main_window.highlight_word(start, end)
            # Overlay pill: karaoke word-by-word highlight (works in any app)
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
            # Catch unexpected TTS startup failures — the app must never crash
            self._on_speaking_finished()
            self._tray.show_notification("Veaja — TTS error", str(exc))

    # ── TTS control ───────────────────────────────────────────────────────────

    def _stop_speaking(self) -> None:
        """Stop playback and reset all UI state to IDLE."""
        self._tts.stop()
        self._on_speaking_finished()

    def _pause_speaking(self) -> None:
        """
        Pause if the engine supports it; fall back to stop for pyttsx3 (offline).
        UI update is handled by the on_paused callback, not here.
        """
        if self._tts.supports_pause():
            self._tts.pause()
        else:
            # pyttsx3 has no native pause — treat as a full stop
            self._stop_speaking()

    def _resume_speaking(self) -> None:
        """Resume from a paused state. UI update handled by on_resumed callback."""
        self._tts.resume()

    def _on_overlay_stop(self) -> None:
        """
        Handle a tap on the overlay pill while TTS is active.

        • Speaking  → pause
        • Paused    → resume
        • Idle      → stop (safety fallback)
        """
        if self._tts.is_paused():
            self._resume_speaking()
        elif self._tts.is_speaking():
            self._pause_speaking()
        else:
            self._stop_speaking()

    def _on_reset_requested(self) -> None:
        """
        Handle the ⟳ reset button on the overlay pill.

        Stops the current read and restarts from the beginning of the same text
        after a 200 ms delay to allow the TTS engine to clean up gracefully.
        """
        if not self._current_text:
            return
        self._tts.stop()
        self._on_speaking_finished()
        QTimer.singleShot(200, lambda: self._speak(self._current_text))

    # ── TTS lifecycle callbacks ────────────────────────────────────────────────

    def _on_preparing_speech(self) -> None:
        """TTS engine is fetching / synthesising audio (not yet playing)."""
        self._overlay.set_processing(True)
        self._main_window.set_read_state(ReadState.PROCESSING)

    def _on_speaking_started(self) -> None:
        """Audio playback has begun."""
        self._overlay.set_processing(False)
        self._overlay.set_speaking(True)
        self._main_window.set_read_state(ReadState.SPEAKING)
        self._main_window.mark_reading_started(self._current_text)
        # Show the overlay so spin/glow animations are visible even when
        # the user triggered reading from the main window
        if not self._overlay.isVisible():
            self._overlay.show_overlay()

    def _on_speaking_paused(self) -> None:
        """Audio playback has been paused."""
        self._overlay.set_speaking(False)
        self._overlay.set_paused(True)
        self._main_window.set_read_state(ReadState.PAUSED)

    def _on_speaking_resumed(self) -> None:
        """Audio playback has resumed from pause."""
        self._overlay.set_paused(False)
        self._overlay.set_speaking(True)
        self._main_window.set_read_state(ReadState.SPEAKING)

    def _on_speaking_finished(self) -> None:
        """Audio playback has ended (naturally or was stopped)."""
        self._overlay.set_processing(False)
        self._overlay.set_speaking(False)
        self._overlay.set_paused(False)
        self._main_window.set_read_state(ReadState.IDLE)
        self._main_window.clear_highlight()
        self._main_window.mark_reading_started("")   # nothing is playing now
        # If main window is visible, hide the overlay again (it was auto-shown)
        if self._main_window.isVisible() and self._overlay.isVisible():
            self._overlay.hide_overlay()

    def _on_speaking_error(self, msg: str) -> None:
        """TTS raised an error — reset UI and show a tray notification."""
        self._on_speaking_finished()
        self._tray.show_notification("Veaja — TTS error", msg)

    # ── Settings & mode ───────────────────────────────────────────────────────

    def _on_mode_changed(self, online: bool) -> None:
        """
        User toggled the Online / Offline switch in the Settings page.

        Updates the TTS engine mode and refreshes the voice selector so it
        shows only voices relevant to the new mode.

        voice_index clamp
        -----------------
        Online mode has 8 voices; offline mode may have fewer system voices.
        A saved voice_index of 7 would be out of range after switching to
        offline. We clamp it to 0 and persist the correction so the UI and
        the engine always stay in sync.
        """
        self._tts.set_forced_offline(not online)
        voices = self._tts.get_voices()
        self._main_window.populate_voices(voices)

        # Clamp the saved voice_index to the valid range for the new mode
        if voices:
            profile = self._profile.get()
            voice_index = profile.get("voice_index", 0)
            if not isinstance(voice_index, int) or voice_index >= len(voices):
                profile["voice_index"] = 0
                self._profile.save(profile)

    def _on_settings_save(self, settings: dict) -> None:
        """Merge the changed settings into the user profile and persist to disk."""
        profile = self._profile.get()
        profile.update(settings)
        self._profile.save(profile)

    def _on_lang_changed(self, lang: str) -> None:
        """User selected a different language — switch TTS voices to native speakers."""
        self._tts.set_language(lang)
        voices = self._tts.get_voices()
        self._main_window.populate_voices(voices)

    def _on_connectivity_changed(self, is_online: bool) -> None:
        """
        NetworkMonitor detected an internet state change.

        Going offline:
          • Forces TTS to offline mode immediately to prevent edge-tts crashes.
          • Updates the status label in the Settings page.

        Coming back online:
          • Restores online mode if edge-tts is available.
          • Refreshes the voice list so online voices appear again.
        """
        # Update the status label and lock / unlock the online checkbox
        self._main_window.update_connection_status(is_online)

        if not is_online:
            # Auto-switch to offline to avoid network errors on next read
            self._tts.set_forced_offline(True)
            self._main_window.populate_voices(self._tts.get_voices())
        else:
            # Internet is back — restore online mode if the engine supports it
            if self._tts.is_edge_available():
                self._tts.set_forced_offline(False)
                self._main_window.set_online_mode(True)
                self._main_window.populate_voices(self._tts.get_voices())

    def _on_theme_changed(self, dark: bool) -> None:
        """
        User toggled dark / light mode.

        Updates the tray icon, the overlay pill colour scheme, and persists
        the preference so it survives app restarts.
        """
        self._tray.update_icon(dark)
        self._overlay.update_theme(dark)

        profile = self._profile.get()
        profile["dark_mode"] = dark
        self._profile.save(profile)

    # ── Terms of service ──────────────────────────────────────────────────────

    def _show_terms_on_launch(self) -> None:
        """
        Show the Terms dialog on first launch.

        If the user accepts and ticks "Don't show again", the preference is
        persisted so the dialog never appears again.
        """
        dlg = TermsDialog(
            online_mode=self._tts.is_edge_available(),
            dark=self._is_dark_mode(),
            parent=self._main_window,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.dont_show_again():
            profile = self._profile.get()
            profile["terms_accepted"] = True
            self._profile.save(profile)

    def _show_terms(self) -> None:
        """Show the Terms dialog on demand (from the sidebar link)."""
        TermsDialog(
            online_mode=self._tts.is_edge_available(),
            dark=self._is_dark_mode(),
            parent=self._main_window,
        ).exec()

    # ── Profile ───────────────────────────────────────────────────────────────

    def _show_profile_dialog(self) -> None:
        """Open the modal profile editor. Saves on Accepted."""
        dlg = ProfileDialog(self._profile.get(), parent=self._main_window)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._profile.save(dlg.get_profile())

    def _show_tour(self) -> None:
        """
        Launch the interactive tutorial overlay.

        Passes the overlay pill and TTS callback so the tutorial can show the
        real pill during the "Get Started" interactive training phase.
        """
        from gui.tour_overlay import TourOverlay

        tour = TourOverlay(
            self._main_window,
            overlay_widget=self._overlay,
            speak_callback=self._speak,
        )
        tour.show()

    def _on_profile_save_requested(self, profile: dict) -> None:
        """
        Handle a live profile save from the profile page.

        The profile_changed signal fired by ProfileManager will propagate the
        update to the overlay and main window automatically.
        """
        self._profile.save(profile)   # emits profile_changed → _on_profile_changed

    def _on_profile_changed(self, profile: dict) -> None:
        """Apply an updated profile to all components that care about it."""
        self._main_window.apply_profile(profile)
        self._overlay.apply_profile(profile)   # swaps logo ↔ user avatar on pill

        # Update the tray tooltip to reflect a custom app name if set
        name = profile.get("app_name", "Veaja")
        try:
            self._tray._tray.setToolTip(f"{name} — running")
        except Exception:
            pass

    # ── Quit ──────────────────────────────────────────────────────────────────

    def _quit(self) -> None:
        """Gracefully shut down all background components before exiting."""
        self._monitor.stop()   # stop the global hotkey listener thread
        self._tts.stop()       # stop any in-progress TTS playback
        self._tray.hide()      # remove the system tray icon
        QApplication.quit()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _is_dark_mode() -> bool:
        """
        Detect whether the OS is currently in dark mode.

        Windows: reads the registry key AppsUseLightTheme (0 = dark, 1 = light).
        Other:   falls back to QPalette window lightness < 128.
        """
        import platform as _platform

        if _platform.system() == "Windows":
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                )
                try:
                    # CloseKey is in finally so it always runs even if
                    # QueryValueEx raises — prevents a handle leak.
                    val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                    return val == 0   # 0 → dark mode enabled
                finally:
                    winreg.CloseKey(key)
            except Exception:
                pass   # registry key absent or unreadable — fall through

        # Generic fallback via QPalette
        from PyQt6.QtGui import QPalette
        app = QApplication.instance()
        if app is None:
            return False
        return app.palette().color(QPalette.ColorRole.Window).lightness() < 128

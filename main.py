import sys
import keyboard
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer, QMetaObject, Q_ARG
from gui.main_window import MainWindow
from gui.overlay_window import OverlayWindow
import win32gui
import win32con


class WindowManager:
    """
    The ONLY brain that connects MainWindow and OverlayWindow.
    Neither window imports or calls the other directly.
    This class is the mediator.
    """

    def __init__(self, main_window, overlay_window):
        self.main = main_window
        self.overlay = overlay_window

        # Give overlay a reference so it can ask "are we fullscreen?"
        self.overlay.set_manager(self)

        # Track the PREVIOUS state so we only react on CHANGE
        # (not on every single poll tick)
        self._was_fullscreen = False

        # ── Register Ctrl+C ONCE here ──────────────────────────
        # Why here and NOT inside a window class?
        # Because hotkeys are global — they fire even when
        # your app is not focused. Registering inside a window
        # ties the hotkey to that window's lifecycle, which is wrong.
        keyboard.add_hotkey('ctrl+c', self._on_ctrl_c, suppress=False)

        # ── Start polling timer ────────────────────────────────
        # QTimer fires every 500ms and calls _poll_fullscreen.
        # 500ms = fast enough to feel instant, cheap enough to
        # not waste CPU.
        self.timer = QTimer()
        self.timer.timeout.connect(self._poll_fullscreen)
        self.timer.start(500)

        # ── Wire quit and hide signals from main window ────────
        # Both X buttons call quit_app, — calls hide_main
        self.main.request_quit.connect(self.quit_app)
        self.main.request_hide.connect(self.hide_main)

    def is_fullscreen_mode(self):
        """Overlay asks this before deciding to show."""
        return self._was_fullscreen

    # ─────────────────────────────────────────
    #  Fullscreen detection  ← BUG 1 + 3 fix
    # ─────────────────────────────────────────
    def _is_fullscreen(self):
        """
        Ask Windows: is the currently focused app a TRUE fullscreen app?

        Key difference from before:
        - A MAXIMIZED window (VS Code, terminal, browser) fills the screen
          but still has the WS_MAXIMIZE style bit set.
        - A TRUE fullscreen app (game, video player) has NO maximize bit —
          it just sets its window rect to cover the screen directly.

        We check the style bit to tell them apart.
        Also skips our own windows so switching back to VeaJa
        doesn't count as leaving fullscreen.
        """
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return False

            # If the focused window is one of ours → not a foreign fullscreen
            try:
                our_hwnds = [
                    int(self.main.winId()),
                    int(self.overlay.winId())
                ]
                if hwnd in our_hwnds:
                    return False
            except Exception:
                pass

            # ── BUG 1 FIX: skip maximized windows ──────────────
            # GetWindowLong returns the style flags for the window.
            # WS_MAXIMIZE means it's maximized (not truly fullscreen).
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            if style & win32con.WS_MAXIMIZE:
                return False   # maximized ≠ fullscreen

            # Also skip minimized windows
            if style & win32con.WS_MINIMIZE:
                return False

            # Now check if the window rect actually covers the full screen
            rect = win32gui.GetWindowRect(hwnd)
            screen = QApplication.primaryScreen().geometry()

            return (
                rect[0] <= 0 and
                rect[1] <= 0 and
                rect[2] >= screen.width() and
                rect[3] >= screen.height()
            )

        except Exception:
            # If win32 call fails (e.g. on lock screen),
            # assume NOT fullscreen — safer default
            return False

    # ─────────────────────────────────────────
    #  The poll — called every 500ms
    # ─────────────────────────────────────────
    def _poll_fullscreen(self):
        """
        Called automatically every 500ms by QTimer.

        Logic:
          - If it JUST became fullscreen → hide main window
          - If it JUST left fullscreen   → show main window
          - If state hasn't changed      → do nothing

        The _was_fullscreen flag prevents us from calling
        show()/hide() on every single tick (which would
        cause flickering and wasted work).
        """
        currently_fullscreen = self._is_fullscreen()

        if currently_fullscreen and not self._was_fullscreen:
            # TRANSITION: normal → fullscreen
            self._on_fullscreen()

        elif not currently_fullscreen and self._was_fullscreen:
            # TRANSITION: fullscreen → normal (user swapped back to desktop)
            self._on_normal()

        self._was_fullscreen = currently_fullscreen

    # ─────────────────────────────────────────
    #  Ctrl+C handler
    # ─────────────────────────────────────────
    def _on_ctrl_c(self):
        """
        Called when user presses Ctrl+C (e.g. copying text in a fullscreen app).

        Problem: keyboard library fires from a background thread,
        but Qt windows can ONLY be touched from the main thread.

        Solution: QMetaObject.invokeMethod with QueuedConnection
        schedules calls to run safely on the Qt main thread
        on the next event loop tick.

        Never call window methods directly from here — it will crash.

        We hide main AND directly show overlay here.
        The clipboard guard in overlay (is_fullscreen_mode check) is
        correct for passive clipboard events, but Ctrl+C is an explicit
        user action — we bypass the guard by calling show_window() directly
        from the manager instead of relying on the clipboard signal path.
        """
        # Hide main window
        QMetaObject.invokeMethod(
            self.main,
            "hide",
            Qt.ConnectionType.QueuedConnection
        )
        # Directly show overlay — bypasses the clipboard guard
        QMetaObject.invokeMethod(
            self.overlay,
            "show_window",
            Qt.ConnectionType.QueuedConnection
        )
        # Do NOT touch _was_fullscreen here — let _poll_fullscreen own it

    # ─────────────────────────────────────────
    #  State transition handlers
    # ─────────────────────────────────────────
    def _on_fullscreen(self):
        """User switched to a fullscreen app — hide the main window."""
        self._was_fullscreen = True
        self.main.hide()
        # Note: we do NOT hide the overlay — it has
        # WindowStaysOnTopHint so it floats above the fullscreen app

    def _on_normal(self):
        """
        User left fullscreen / swapped back to desktop.

        BUG 3 FIX: use show() only — no raise_() or activateWindow().
        raise_() + activateWindow() was stealing focus and pulling
        main on top of whatever the user was doing.
        main_win has no WindowStaysOnTopHint so it will sit behind
        other windows naturally once shown without forcing focus.
        """
        self._was_fullscreen = False
        self.main.show()
        # Overlay hides when user is back on the normal desktop
        self.overlay.hide_window()

    def hide_main(self):
        """— button on main window: hide main only."""
        self.main.hide()

    def quit_app(self):
        """X button on either window: terminate everything."""
        self.overlay.tray.hide()
        QApplication.quit()


# ─────────────────────────────────────────────
#   Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # QApplication must be created FIRST — before any window
    app = QApplication(sys.argv)

    # Without this, closing the LAST visible window would quit the app.
    # We want the app to keep running even when main window is hidden.
    app.setQuitOnLastWindowClosed(False)

    # Create both windows
    main_win    = MainWindow()
    overlay_win = OverlayWindow()

    # Hand them to the manager — this wires everything together.
    # Neither window knows about the other.
    manager = WindowManager(main_win, overlay_win)

    # ── Always show main on startup — no fullscreen check needed ──
    # The poll will handle hiding it if a true fullscreen app is detected.
    # The old _is_fullscreen() check was wrongly blocking startup because
    # maximized windows (VS Code, terminal) were treated as fullscreen.
    main_win.show()

    # Start the Qt event loop.
    # app.exec() BLOCKS here — your code runs through
    # callbacks/signals/timers from this point on.
    # It only returns when QApplication.quit() is called.
    sys.exit(app.exec())
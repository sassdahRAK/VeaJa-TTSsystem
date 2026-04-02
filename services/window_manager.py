"""
WindowManager — controls the relationship between the overlay and the main window.

Rules
-----
  • Overlay appears  →  main window hides (slides to tray)
  • Overlay hides    →  main window comes back (if it was visible before)
  • Tray click       →  always shows main window (bypasses hide state)
  • Quit             →  cleans up everything
"""

from PyQt6.QtCore import QObject


class WindowManager(QObject):
    def __init__(self, main_window, overlay, parent=None):
        super().__init__(parent)
        self._main   = main_window
        self._overlay = overlay

        # Was the main window visible just before the overlay appeared?
        self._main_was_visible: bool = False

        # Wire overlay lifetime signals
        overlay.overlay_shown.connect(self._on_overlay_shown)
        overlay.overlay_hidden.connect(self._on_overlay_hidden)

    # ------------------------------------------------------------------ #
    # Overlay lifecycle
    # ------------------------------------------------------------------ #

    def _on_overlay_shown(self):
        """Overlay just became visible — hide the main window."""
        self._main_was_visible = self._main.isVisible()
        if self._main_was_visible:
            self._main.hide()

    def _on_overlay_hidden(self):
        """Overlay just disappeared — restore main window if it was showing."""
        if self._main_was_visible:
            self._main.show()
            self._main.raise_()
            self._main_was_visible = False

    # ------------------------------------------------------------------ #
    # Manual show (tray click, settings menu from overlay, etc.)
    # ------------------------------------------------------------------ #

    def show_main(self):
        """Always show main window regardless of overlay state."""
        self._main_was_visible = True   # ensure it stays after overlay hides
        self._main.show()
        self._main.raise_()
        self._main.activateWindow()

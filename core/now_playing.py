"""
core.now_playing
================
macOS Now Playing / Media Remote integration for Veaja.

When Veaja is reading text, it registers with the macOS Now Playing system so:
  • The ▶ media icon appears in the menu bar
  • The media card shows the text title + progress bar
  • Hardware media keys (F7/F8/F9) control playback
  • AirPods double-tap pause/resume works
  • Lock screen shows playback controls

On Windows and Linux this module is a no-op — all public functions return
immediately without doing anything.

Architecture
------------
NowPlayingManager is a singleton (get_instance()) that:
  1. Registers play/pause/stop/toggle remote command handlers once.
  2. Exposes update() / set_paused() / clear() to update the Now Playing info.
  3. Bridges macOS callbacks back to Qt via pyqtSignal (thread-safe).

Usage (from AppController)
--------------------------
    from core.now_playing import get_instance as get_now_playing
    np = get_now_playing()
    np.play_requested.connect(self._resume_speaking)
    np.pause_requested.connect(self._pause_speaking)
    np.stop_requested.connect(self._stop_speaking)

    # When TTS starts:
    np.update("The quick brown fox…", duration_s=12.5)

    # While speaking (call every ~500ms with current position):
    np.update("The quick brown fox…", duration_s=12.5, elapsed_s=3.2)

    # When paused:
    np.set_paused(True)

    # When finished:
    np.clear()
"""

import platform
import sys

# ── Only import PyObjC / MediaPlayer on macOS ─────────────────────────────────
_IS_MAC = platform.system() == "Darwin"
_AVAILABLE = False

if _IS_MAC:
    try:
        from MediaPlayer import (
            MPNowPlayingInfoCenter,
            MPRemoteCommandCenter,
            MPMediaItemPropertyTitle,
            MPMediaItemPropertyArtist,
            MPMediaItemPropertyPlaybackDuration,
            MPNowPlayingInfoPropertyElapsedPlaybackTime,
            MPNowPlayingInfoPropertyPlaybackRate,
            MPNowPlayingPlaybackStatePlaying,
            MPNowPlayingPlaybackStatePaused,
            MPNowPlayingPlaybackStateStopped,
        )
        _AVAILABLE = True
    except Exception as _e:
        print(f"[Veaja] Now Playing unavailable: {_e}", file=sys.stderr)

# ── Qt signal bridge ──────────────────────────────────────────────────────────
from PyQt6.QtCore import QObject, pyqtSignal


class NowPlayingManager(QObject):
    """
    Singleton manager for macOS Now Playing integration.

    Signals (emitted on Qt main thread via QueuedConnection):
      play_requested()    — user pressed play (media key / AirPods)
      pause_requested()   — user pressed pause
      stop_requested()    — user pressed stop
      toggle_requested()  — user pressed play/pause toggle
    """

    play_requested   = pyqtSignal()
    pause_requested  = pyqtSignal()
    stop_requested   = pyqtSignal()
    toggle_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._registered = False
        self._current_title = ""
        self._duration = 0.0
        self._elapsed  = 0.0
        self._paused   = False

        if _AVAILABLE:
            self._register_commands()

    # ── Remote command registration ───────────────────────────────────────────

    def _register_commands(self):
        """Register play/pause/stop/toggle handlers with MPRemoteCommandCenter."""
        try:
            cc = MPRemoteCommandCenter.sharedCommandCenter()

            # Enable the commands we handle
            cc.playCommand().setEnabled_(True)
            cc.pauseCommand().setEnabled_(True)
            cc.stopCommand().setEnabled_(True)
            cc.togglePlayPauseCommand().setEnabled_(True)

            # Disable commands we don't support (prevents ghost buttons)
            cc.nextTrackCommand().setEnabled_(False)
            cc.previousTrackCommand().setEnabled_(False)
            cc.skipForwardCommand().setEnabled_(False)
            cc.skipBackwardCommand().setEnabled_(False)
            cc.seekForwardCommand().setEnabled_(False)
            cc.seekBackwardCommand().setEnabled_(False)

            # Add handlers — these fire on a background thread, so we emit
            # Qt signals (QueuedConnection delivers them on the main thread).
            cc.playCommand().addTargetWithHandler_(self._on_play)
            cc.pauseCommand().addTargetWithHandler_(self._on_pause)
            cc.stopCommand().addTargetWithHandler_(self._on_stop)
            cc.togglePlayPauseCommand().addTargetWithHandler_(self._on_toggle)

            self._registered = True
        except Exception as exc:
            print(f"[Veaja] Now Playing command registration failed: {exc}",
                  file=sys.stderr)

    # ── Remote command handlers (called on macOS background thread) ───────────

    def _on_play(self, event):
        self.play_requested.emit()
        return 0   # MPRemoteCommandHandlerStatusSuccess

    def _on_pause(self, event):
        self.pause_requested.emit()
        return 0

    def _on_stop(self, event):
        self.stop_requested.emit()
        return 0

    def _on_toggle(self, event):
        self.toggle_requested.emit()
        return 0

    # ── Public API ────────────────────────────────────────────────────────────

    def update(self, title: str, duration_s: float = 0.0,
               elapsed_s: float = 0.0) -> None:
        """
        Update the Now Playing info card.

        Call this when TTS starts and periodically while speaking to keep
        the progress bar accurate.

        title      — text being read (truncated to 80 chars for display)
        duration_s — estimated total duration in seconds (0 = unknown)
        elapsed_s  — current playback position in seconds
        """
        if not _AVAILABLE:
            return
        try:
            self._current_title = title
            self._duration = duration_s
            self._elapsed  = elapsed_s
            self._paused   = False
            self._push_info(playing=True)
        except Exception as exc:
            print(f"[Veaja] Now Playing update failed: {exc}", file=sys.stderr)

    def set_paused(self, paused: bool) -> None:
        """Switch the playback state between playing and paused."""
        if not _AVAILABLE:
            return
        try:
            self._paused = paused
            self._push_info(playing=not paused)
        except Exception as exc:
            print(f"[Veaja] Now Playing pause state failed: {exc}",
                  file=sys.stderr)

    def clear(self) -> None:
        """Remove Veaja from the Now Playing widget (playback ended)."""
        if not _AVAILABLE:
            return
        try:
            center = MPNowPlayingInfoCenter.defaultCenter()
            center.setNowPlayingInfo_(None)
            center.setPlaybackState_(MPNowPlayingPlaybackStateStopped)
        except Exception as exc:
            print(f"[Veaja] Now Playing clear failed: {exc}", file=sys.stderr)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _push_info(self, playing: bool) -> None:
        """Push the current state to MPNowPlayingInfoCenter."""
        center = MPNowPlayingInfoCenter.defaultCenter()

        # Truncate title for display — long text looks bad in the media card
        display_title = self._current_title
        if len(display_title) > 80:
            display_title = display_title[:77] + "…"

        info = {
            MPMediaItemPropertyTitle:                   display_title,
            MPMediaItemPropertyArtist:                  "Veaja TTS",
            MPNowPlayingInfoPropertyPlaybackRate:        1.0 if playing else 0.0,
            MPNowPlayingInfoPropertyElapsedPlaybackTime: float(self._elapsed),
        }
        if self._duration > 0:
            info[MPMediaItemPropertyPlaybackDuration] = float(self._duration)

        center.setNowPlayingInfo_(info)
        state = (MPNowPlayingPlaybackStatePlaying if playing
                 else MPNowPlayingPlaybackStatePaused)
        center.setPlaybackState_(state)


# ── Singleton ─────────────────────────────────────────────────────────────────

_instance: NowPlayingManager | None = None


def get_instance() -> NowPlayingManager:
    """Return the singleton NowPlayingManager, creating it on first call."""
    global _instance
    if _instance is None:
        _instance = NowPlayingManager()
    return _instance

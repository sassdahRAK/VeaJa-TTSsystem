"""
platform_adapters.ios
=====================
iOS / iPadOS adapter — for future BeeWare Toga deployment.

Status: STUB — not yet wired into the main app.
        Implement when targeting iOS via BeeWare.
"""

from platform_adapters.base import BasePlatform


class IOSPlatform(BasePlatform):
    @property
    def name(self) -> str:
        return "iOS"

    @property
    def supports_system_tray(self) -> bool:
        return False

    @property
    def supports_global_hotkeys(self) -> bool:
        return False

    @property
    def supports_clipboard_monitor(self) -> bool:
        return False   # iOS 14+ requires explicit user permission

    @property
    def supports_pause_resume(self) -> bool:
        return True   # AVAudioSession supports pause

    def preferred_tts_backends(self) -> list[str]:
        # iOS has AVSpeechSynthesizer (high quality, offline)
        return ["ios_avs", "edge_tts"]

    def get_config_dir(self) -> str:
        try:
            import toga
            return str(toga.App.app.paths.data)
        except Exception:
            from pathlib import Path
            return str(Path.home() / ".veaja")

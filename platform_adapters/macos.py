"""platform_adapters.macos — macOS (Intel x86_64 and Apple Silicon ARM64)."""

from platform_adapters.base import BasePlatform


class MacOSPlatform(BasePlatform):
    @property
    def name(self) -> str:
        import platform
        return f"macOS {platform.mac_ver()[0]} ({platform.machine()})"

    @property
    def supports_system_tray(self) -> bool:
        return True

    @property
    def supports_global_hotkeys(self) -> bool:
        return True   # pynput works on macOS (requires Accessibility permission)

    @property
    def supports_clipboard_monitor(self) -> bool:
        return True

    @property
    def supports_pause_resume(self) -> bool:
        return True

    def get_config_dir(self) -> str:
        from pathlib import Path
        return str(Path.home() / "Library" / "Application Support" / "Veaja")

    def simulate_copy(self) -> None:
        try:
            from pynput.keyboard import Controller, Key
            kb = Controller()
            kb.press(Key.cmd)
            kb.press('c')
            kb.release('c')
            kb.release(Key.cmd)
        except Exception:
            pass

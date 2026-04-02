"""platform_adapters.linux — Linux desktop (x64, ARM64, Raspberry Pi)."""

from platform_adapters.base import BasePlatform


class LinuxPlatform(BasePlatform):
    @property
    def name(self) -> str:
        import platform
        return f"Linux ({platform.machine()})"

    @property
    def supports_system_tray(self) -> bool:
        return True   # via Qt + libappindicator

    @property
    def supports_global_hotkeys(self) -> bool:
        return True   # pynput works on X11; limited on Wayland

    @property
    def supports_clipboard_monitor(self) -> bool:
        return True

    @property
    def supports_pause_resume(self) -> bool:
        return True

    def get_config_dir(self) -> str:
        import os
        from pathlib import Path
        xdg = os.environ.get("XDG_CONFIG_HOME")
        if xdg:
            return str(Path(xdg) / "veaja")
        return str(Path.home() / ".config" / "veaja")

    def simulate_copy(self) -> None:
        try:
            from pynput.keyboard import Controller, Key
            kb = Controller()
            kb.press(Key.ctrl_l)
            kb.press('c')
            kb.release('c')
            kb.release(Key.ctrl_l)
        except Exception:
            pass

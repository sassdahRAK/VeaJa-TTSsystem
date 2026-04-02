"""platform_adapters.windows — Windows desktop (x64 and ARM64)."""

import sys
from platform_adapters.base import BasePlatform


class WindowsPlatform(BasePlatform):
    @property
    def name(self) -> str:
        import platform
        arch = platform.machine()   # AMD64 or ARM64
        return f"Windows ({arch})"

    @property
    def supports_system_tray(self) -> bool:
        return True

    @property
    def supports_global_hotkeys(self) -> bool:
        return True   # pynput works on Windows

    @property
    def supports_clipboard_monitor(self) -> bool:
        return True

    @property
    def supports_pause_resume(self) -> bool:
        return True   # pygame mixer supports pause/resume

    def get_config_dir(self) -> str:
        import os
        from pathlib import Path
        # Prefer %APPDATA%\Veaja on Windows
        appdata = os.environ.get("APPDATA")
        if appdata:
            return str(Path(appdata) / "Veaja")
        return str(Path.home() / ".veaja")

    def show_notification(self, title: str, body: str) -> None:
        # Delegated to Qt tray icon (QSystemTrayIcon.showMessage)
        # — actual call happens in TrayIcon.show_notification()
        pass

    def read_clipboard(self) -> str:
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                return app.clipboard().text()
        except Exception:
            pass
        return ""

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

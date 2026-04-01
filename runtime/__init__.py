"""
runtime — runtime platform detection and adapter factory.

Usage
-----
    from runtime import get_platform
    plat = get_platform()
    plat.open_url("https://example.com")

Supported targets
-----------------
  desktop   Windows (x64 / ARM), macOS (Intel / Apple Silicon), Linux
  mobile    Android, iOS  (future — BeeWare / Kivy backends)
"""

import sys


def get_platform():
    """Return the appropriate platform adapter for the current runtime."""
    from platform_adapters.base import BasePlatform

    system = sys.platform
    if system == "win32":
        from platform_adapters.windows import WindowsPlatform
        return WindowsPlatform()
    elif system == "darwin":
        from platform_adapters.macos import MacOSPlatform
        return MacOSPlatform()
    elif system.startswith("linux"):
        # Detect Android (Kivy / BeeWare runtime sets ANDROID_ARGUMENT)
        import os
        if "ANDROID_ARGUMENT" in os.environ or "ANDROID_ROOT" in os.environ:
            from platform_adapters.android import AndroidPlatform
            return AndroidPlatform()
        from platform_adapters.linux import LinuxPlatform
        return LinuxPlatform()
    else:
        return BasePlatform()

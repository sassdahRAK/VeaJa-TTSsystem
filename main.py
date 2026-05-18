"""
Veaja — cross-platform TTS desktop app.
Entry point and composition root.

WindowManager rules (wired here, in main):
  • Overlay appears  →  main window hides to tray
  • Overlay hides    →  main window comes back
  • Tray click       →  always show main window

Run:
    python3 main.py

macOS first run — grant Accessibility access when prompted:
    System Settings → Privacy & Security → Accessibility → add Terminal / Python
"""

import sys
import os
import platform

# ── Ensure project root is importable ───────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── Qt high-DPI (must be set before QApplication) ───────────────────────────
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")

# ── Linux: force XCB (X11/XWayland) backend ─────────────────────────────────
if platform.system() == "Linux":
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)
from PyQt6.QtGui import QFont, QIcon, QPixmap

# NOTE: SplashScreen is the ONLY import here at module level.
# AppController, TTSEngine, pygame, edge_tts, pynput etc. are all
# imported AFTER the splash is visible — see main() below.
from gui.splash_screen import SplashScreen


# ── Single-instance lock ─────────────────────────────────────────────────────

def _acquire_instance_lock():
    """
    Prevent multiple Veaja instances from running simultaneously.

    Uses a lock file at ~/.veaja/veaja.lock containing the current PID.
    On startup:
      1. If no lock file exists → write our PID and continue.
      2. If a lock file exists → check if that PID is still alive.
         • Alive  → another instance is running → exit immediately.
         • Dead   → stale lock from a crash → overwrite and continue.

    Returns the lock file path so the caller can clean it up on exit.
    """
    from pathlib import Path

    lock_dir  = Path.home() / ".veaja"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / "veaja.lock"

    system = platform.system()

    if system == "Windows":
        # Windows: use a named mutex — most reliable on Windows
        try:
            import ctypes
            mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "VeajaAppMutex")
            last_err = ctypes.windll.kernel32.GetLastError()
            if last_err == 183:  # ERROR_ALREADY_EXISTS
                # Another instance is running — bring it to front via tray
                from PyQt6.QtWidgets import QMessageBox
                msg = QMessageBox()
                msg.setWindowTitle("Veaja")
                msg.setText("Veaja is already running.\nCheck the system tray.")
                msg.setIcon(QMessageBox.Icon.Information)
                msg.exec()
                sys.exit(0)
            # Keep a module-level reference so the mutex is NOT garbage collected.
            # If mutex is a local var it gets released when this function returns,
            # allowing a second instance to open freely.
            _acquire_instance_lock._win_mutex = mutex
        except Exception:
            pass
        return None

    else:
        # Linux / macOS: use fcntl file lock (released automatically on process exit)
        try:
            import fcntl
            lock_file = open(lock_path, "w")
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            lock_file.write(str(os.getpid()))
            lock_file.flush()
            # Keep the file open — lock is held as long as the process lives
            # Store reference so it isn't garbage collected
            _acquire_instance_lock._lock_file = lock_file
            return lock_path
        except BlockingIOError:
            # Lock is held by another process — already running
            from PyQt6.QtWidgets import QApplication as _QApp, QMessageBox
            _tmp_app = _QApp.instance() or _QApp(sys.argv)
            msg = QMessageBox()
            msg.setWindowTitle("Veaja")
            msg.setText("Veaja is already running.\nCheck the system tray.")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
            sys.exit(0)
        except Exception:
            # Can't acquire lock for any other reason — allow startup anyway
            return None


# ── App-level configuration ──────────────────────────────────────────────────

def _configure_app(app: QApplication) -> None:
    app.setApplicationName("Veaja")
    app.setApplicationDisplayName("Veaja")
    app.setOrganizationName("Veaja")
    app.setOrganizationDomain("veaja.app")

    _assets = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    for _name in ("logo_dark.png", "logo_light.png"):
        _p = os.path.join(_assets, _name)
        if os.path.exists(_p):
            app.setWindowIcon(QIcon(QPixmap(_p)))
            break

    system = platform.system()
    if system == "Darwin":
        # Use Qt's default system font on macOS — avoids the "-apple-system"
        # alias warning that Qt 6.x emits when resolving font family names.
        # Setting point size only (no family) lets Qt pick the correct
        # San Francisco / Helvetica Neue system font automatically.
        from PyQt6.QtGui import QFontDatabase
        sys_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
        sys_font.setPointSize(13)
        app.setFont(sys_font)
        app.setQuitOnLastWindowClosed(False)
    elif system == "Windows":
        app.setFont(QFont("Segoe UI", 10))
    else:
        app.setFont(QFont("Ubuntu", 10))


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # ── Single-instance guard — must run before QApplication on Linux/macOS ──
    # On Windows, QApplication must exist first for the messagebox to work,
    # so we create it early and then check.
    if platform.system() == "Windows":
        app = QApplication(sys.argv)
        _configure_app(app)
        _acquire_instance_lock()   # exits here if already running
    else:
        _acquire_instance_lock()   # exits here if already running
        app = QApplication(sys.argv)
        _configure_app(app)

    # ── 1. Splash screen — show immediately before any heavy imports ─────
    # Read saved theme first (lightweight — just opens a JSON file)
    _saved_dark: bool | None = None
    try:
        import json
        from pathlib import Path
        _profile_path = Path.home() / ".veaja" / "profile.json"
        with open(_profile_path, encoding="utf-8") as _f:
            _saved_dark = json.load(_f).get("dark_mode")
        if not isinstance(_saved_dark, bool):
            _saved_dark = None
    except Exception:
        pass

    splash = SplashScreen(saved_dark=_saved_dark)
    splash.show()
    # Force the splash to paint NOW before we do any heavy imports
    app.processEvents()
    app.processEvents()   # second call ensures the window is fully rendered

    # ── 2. Heavy imports — happen while splash is visible ────────────────
    # These are deferred until after the splash shows so the user sees
    # the splash immediately instead of staring at a blank screen.
    # edge_tts: ~390ms, PyQt6 pages: ~200ms, pynput: ~80ms, pygame: ~76ms
    from services.app_controller import AppController
    from services.window_manager  import WindowManager   # noqa: F401

    # ── 3. Check for espeak on Linux ─────────────────────────────────────
    if platform.system() == "Linux":
        import shutil
        if not shutil.which("espeak") and not shutil.which("espeak-ng"):
            from PyQt6.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Veaja — Offline Mode Unavailable")
            msg.setText("Espeak not found")
            msg.setInformativeText(
                "Offline text-to-speech requires espeak.\n\n"
                "Install it with:\n"
                "  sudo apt install espeak espeak-ng\n\n"
                "Online mode (edge-tts) will still work with internet."
            )
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()

    # ── 4. Build all app components ──────────────────────────────────────
    controller = AppController(app)
    wm: WindowManager = controller.window_manager   # noqa: F841

    # ── 5. Wire splash finish → start app ────────────────────────────────
    splash.finished.connect(controller.start)
    splash.start_timer(delay_ms=1800)   # shorter hold — imports already done

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

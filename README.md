<div align="center">

# Veaja

**Cross-platform text-to-speech desktop app — copy text anywhere, hear it spoken.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![PyQt6](https://img.shields.io/badge/UI-PyQt6-green)](https://pypi.org/project/PyQt6/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](./LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](#requirements)

</div>

---

## What is Veaja?

Veaja is a lightweight desktop app that turns selected text into speech. Select text in any app, press **Ctrl+C**, and a floating pill appears near your cursor. Click it — and it reads aloud using high-quality neural voices.

**Key features:**

- Floating pill overlay with real-time word-by-word karaoke highlighting
- Online mode — Microsoft neural voices via `edge-tts` (pause/resume supported)
- Offline mode — system TTS fallback via `pyttsx3` (always available)
- Auto language detection — filters non-English text to protect neural voices
- Audio session history — last 3 readings saved as MP3 in `~/.veaja/audio/`
- Dark / light theme — follows system or user override
- Global hotkeys — `Ctrl+C` to copy, `Ctrl+R` to read clipboard immediately
- System tray — runs in background, out of your way
- User profile — custom avatar, highlight color, voice, speed, volume

---

## Requirements

| Requirement | Version |
|---|---|
| Python | 3.10 or later |
| Operating System | Windows 10/11 · macOS 12+ · Linux (x64/ARM) |
| Internet | Optional — required only for online neural voices |

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/your-username/veaja.git
cd veaja
```

### 2. Create a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
python main.py
```

---

## Command Line Reference

Veaja is launched from the terminal. The following options are supported:

```
Usage: python main.py [OPTIONS]

Options:
  (no flags)           Launch the full desktop app (default)
  --help               Show this help message
  --version            Print app version and exit
  --offline            Force offline TTS mode at startup
  --voice <name>       Set the voice at startup (see voice list below)
  --rate <wpm>         Set speech rate in words per minute (default: 175)
  --volume <0.0-1.0>   Set volume level (default: 1.0)
  --dark               Force dark theme
  --light              Force light theme
  --no-splash          Skip the splash screen (faster startup)
  --reset-profile      Reset user profile to defaults and launch
```

### Examples

```bash
# Launch normally
python main.py

# Launch in offline mode (no internet needed)
python main.py --offline

# Launch with a specific voice and faster speech
python main.py --voice en-US-GuyNeural --rate 220

# Launch in dark mode, skipping the splash screen
python main.py --dark --no-splash

# Reset your profile settings back to defaults
python main.py --reset-profile
```

### Available voices (online mode)

| Voice name | Accent | Gender |
|---|---|---|
| `en-US-AriaNeural` | US English | Female (default) |
| `en-US-JennyNeural` | US English | Female |
| `en-US-GuyNeural` | US English | Male |
| `en-US-DavisNeural` | US English | Male |
| `en-GB-SoniaNeural` | British English | Female |
| `en-GB-RyanNeural` | British English | Male |
| `en-AU-NatashaNeural` | Australian English | Female |
| `en-AU-WilliamNeural` | Australian English | Male |

> Offline mode uses your system's default voice (SAPI5 on Windows, AVSpeechSynth on macOS, espeak-ng on Linux).

---

## Global Hotkeys

| Hotkey | Action |
|---|---|
| `Ctrl+C` | Copy selected text and show the pill overlay |
| `Ctrl+R` | Read clipboard content immediately |
| Click pill | Start reading (or pause if already speaking) |
| Click pill (paused) | Resume |
| Right-click pill | Context menu (Hide · Settings · Reset) |

---

## Folder Structure

```
veaja/
├── main.py                   Entry point
├── requirements.txt          Python dependencies
│
├── config/
│   └── settings.py           App-wide constants and feature flags
│
├── core/                     Platform-independent business logic
│   ├── tts_engine.py         TTS orchestrator (EdgeTTS + pyttsx3)
│   ├── selection_monitor.py  Clipboard watcher + global hotkeys
│   ├── audio_history.py      MP3 session FIFO queue
│   ├── profile.py            User profile (JSON, ~/.veaja/profile.json)
│   ├── network_monitor.py    Background connectivity checker
│   └── language/
│       ├── __init__.py       Public API: filter_for_tts, detect_language
│       └── detector.py       Unicode-range language detection
│
├── gui/                      PyQt6 desktop UI
│   ├── main_window.py        Dashboard (tabs: Read · History · Settings · Profile)
│   ├── overlay_widget.py     Floating pill overlay
│   ├── tray_icon.py          System tray icon + notifications
│   ├── splash_screen.py      Startup splash
│   ├── profile_dialog.py     Profile editor modal
│   ├── terms_dialog.py       Terms & privacy dialog
│   ├── tour_overlay.py       Interactive onboarding tour
│   ├── photo_crop_dialog.py  Avatar crop tool
│   ├── theme_mixin.py        Dark / light theme utilities
│   └── pages/                Dashboard page mixins
│       ├── dashboard_mixin.py
│       ├── history_mixin.py
│       ├── settings_mixin.py
│       ├── profile_mixin.py
│       └── info_pages_mixin.py
│
├── services/
│   ├── app_controller.py     Central mediator — wires all components
│   └── window_manager.py     Overlay ↔ main window visibility rules
│
├── platform_adapters/        OS-specific adapters
│   ├── base.py               Abstract interface
│   ├── windows.py            Windows x64 / ARM64
│   ├── macos.py              macOS Intel / Apple Silicon
│   ├── linux.py              Linux x64 / ARM
│   ├── android.py            Android stub (future)
│   └── ios.py                iOS stub (future)
│
├── styles/
│   ├── dark.qss              Dark theme stylesheet
│   └── light.qss             Light theme stylesheet
│
├── i18n/
│   ├── __init__.py           t(key, lang) translation helper
│   └── en/strings.json       English UI strings
│
└── assets/
    ├── logo_dark.png
    └── logo_light.png
```

---

## User Data

All user data is stored in `~/.veaja/`:

| Path | Contents |
|---|---|
| `~/.veaja/profile.json` | Your saved settings (voice, theme, speed, avatar, etc.) |
| `~/.veaja/audio/` | Last 3 reading sessions as MP3 files |

To reset everything, delete the `~/.veaja/` folder or run:

```bash
python main.py --reset-profile
```

---

## macOS — Accessibility Permission

Veaja uses global hotkeys which require Accessibility access on macOS.

On first run you will be prompted. If not, grant it manually:

```
System Settings → Privacy & Security → Accessibility → add Terminal (or Python)
```

---

## Platform Notes

### Windows
- TTS voices: SAPI5 (offline), edge-tts (online)
- High-DPI scaling is enabled automatically
- Runs from PowerShell, CMD, or Windows Terminal

### macOS
- TTS voices: AVSpeechSynthesizer (offline), edge-tts (online)
- Pill overlay uses `NSPopUpMenuWindowLevel` to float above all apps
- Requires Accessibility permission for global hotkeys

### Linux
- TTS voices: espeak-ng (offline), edge-tts (online)
- Install espeak-ng if not already present: `sudo apt install espeak-ng`
- Tested on Ubuntu 22.04+ and Debian 12

---

## Development

### Running tests

```bash
# (Add your test runner command here as tests are added)
pytest tests/
```

### Linting

```bash
pip install ruff
ruff check .
```

### Code style

- Python 3.10+ type hints where practical
- Docstrings on every class and public method
- `core/` must have zero GUI imports (enforced by convention)
- Signal/slot names follow Qt conventions: `snake_case` signals, `on_<signal>` slots

---

## Contributing

Contributions are welcome. Please open an issue first to discuss what you'd like to change.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "add: your feature"`
4. Push to your fork: `git push origin feature/your-feature`
5. Open a pull request

See [ARCHITECTURE.md](ARCHITECTURE.md) for a full overview of how the codebase is structured before writing code.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Acknowledgements

- [edge-tts](https://github.com/rany2/edge-tts) — Microsoft neural voice synthesis
- [PyQt6](https://riverbankcomputing.com/software/pyqt/) — Desktop UI framework
- [pyttsx3](https://github.com/nateshmbhat/pyttsx3) — Offline TTS fallback
- [pynput](https://github.com/moses-palmer/pynput) — Global hotkey listener
- [pygame](https://pygame.org) — Audio playback and mixing

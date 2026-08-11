<div align="center">

# Veaja

**Select text anywhere. Press Ctrl+C. Hear it spoken.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![PyQt6](https://img.shields.io/badge/UI-PyQt6-green)](https://pypi.org/project/PyQt6/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](./LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](#requirements)

</div>

---

## What is Veaja?

Veaja is a desktop text-to-speech app that lives in your system tray. Select any text in any app, press **Ctrl+C**, and a floating pill appears near your cursor. Click it to hear the text read aloud.

It works in two modes:

- **Online mode** — Microsoft neural voices via `edge-tts`. High quality, natural-sounding. Requires internet.
- **Offline mode** — System voices via `pyttsx3` + `espeak`. Fully local, no internet needed. On Linux, requires `espeak` to be installed.

Both modes support **pause, resume, and stop** — controlled by clicking the overlay pill.

---

## Features

- Floating pill overlay with real-time word-by-word karaoke highlighting
- Online mode — Microsoft neural voices (US, UK, AU, and many other languages)
- Offline mode — system TTS via espeak (Linux), SAPI5 (Windows), AVSpeech (macOS)
- Pause / resume support in both online and offline modes
- Smart restart button — detects new clipboard text vs replaying same audio
- WAV audio cache — offline mode replays same text instantly without re-rendering
- Auto network detection — switches online/offline automatically when WiFi changes
- Collapsible sidebar with hamburger toggle
- Dark / light theme — follows system or user override
- Global hotkeys — `Ctrl+C` to copy, `Ctrl+R` to read clipboard immediately
- System tray — runs in background, out of your way
- Audio session history — last 3 readings saved as MP3 in `~/.veaja/audio/`
- Multi-language support — English, French, Khmer, Chinese, Japanese, Korean, and more
- AI features — Summary, Translate, Code, Grammar, Ask (requires API keys)
- User profile — custom avatar, highlight color, voice, speed, volume
- Non-modal Privacy notice — overlay stays interactive while notice is open

---

## Requirements

| Requirement | Version |
|---|---|
| Python | 3.10 or later |
| OS | Windows 10/11 · macOS 12+ · Linux (Ubuntu 20.04+) |
| Internet | Optional (online mode only) |

**Linux only:** Install `espeak` for offline mode:
```bash
sudo apt install espeak espeak-ng
```

---

## Quick StarVt

```bash
# 1. Clone
git clone https://github.com/sassdahRAK/VeaJa-TTSsystem.git
cd VeaJa-TTSsystem

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python main.py
```

See [INSTALL.md](INSTALL.md) for detailed platform-specific instructions.

---

## How to use

1. **Select text** in any app (browser, PDF, document, etc.)
2. Press **Ctrl+C** — the floating pill appears near your cursor
3. **Click the pill** to start reading
4. Click again to **pause**, click again to **resume**
5. Click the **⟳ restart button** to restart from the beginning
   - If you've copied new text, it reads the new text instead
6. Right-click the pill for more options (Hide, Settings, Quit)

Or press **Ctrl+R** to read the clipboard immediately without the pill appearing first.

---

## Global hotkeys

| Hotkey | Action |
|---|---|
| `Ctrl+C` | Copy selected text and show the pill overlay |
| `Ctrl+R` | Read clipboard content immediately |
| Click pill | Start / pause / resume |
| Click pill (paused) | Resume |
| Click ⟳ | Restart (or read new clipboard text) |
| Right-click pill | Context menu |

---

## Available voices (online mode — English)

| Voice | Accent | Gender |
|---|---|---|
| `en-US-AriaNeural` | US English | Female (default) |
| `en-US-JennyNeural` | US English | Female |
| `en-US-GuyNeural` | US English | Male |
| `en-US-DavisNeural` | US English | Male |
| `en-GB-SoniaNeural` | British English | Female |
| `en-GB-RyanNeural` | British English | Male |
| `en-AU-NatashaNeural` | Australian English | Female |
| `en-AU-WilliamNeural` | Australian English | Male |

Other languages (French, Khmer, Chinese, Japanese, Korean, Thai, Hindi, Arabic, German, Spanish, Portuguese, Russian, Vietnamese, Indonesian) are also available in online mode.

> Offline mode uses your system's default voice: SAPI5 on Windows, AVSpeechSynthesizer on macOS, espeak-ng on Linux. Veaja auto-selects English (US) if available.

---

## Command line options

```bash
python main.py                    # Launch normally
python main.py --offline          # Start in offline mode
python main.py --dark             # Force dark theme
python main.py --no-splash        # Skip splash screen
python main.py --reset-profile    # Reset all settings to defaults
python main.py --voice en-US-GuyNeural --rate 200
```

---

## User data

All user data is stored locally at `~/.veaja/`:

| Path | Contents |
|---|---|
| `~/.veaja/profile.json` | Settings (voice, theme, speed, avatar, etc.) |
| `~/.veaja/audio/` | Last 3 reading sessions as MP3 files |

To reset everything:
```bash
python main.py --reset-profile
# or delete the folder:
rm -rf ~/.veaja
```

---

## Platform notes

### Linux
- Requires `espeak` or `espeak-ng` for offline mode
- Uses XCB (X11/XWayland) backend — native Wayland is not supported
- Tested on Ubuntu 22.04+

### macOS
- Requires Accessibility permission for global hotkeys
- Pill overlay uses `NSPopUpMenuWindowLevel` to float above all apps
- Tested on macOS 13+

### Windows
- No additional setup required
- SAPI5 voices work out of the box
- Tested on Windows 10 and 11

---

## Project structure

```
veaja/
├── main.py                  Entry point
├── requirements.txt         Python dependencies
├── config/settings.py       App constants
├── core/                    Business logic (no UI imports)
│   ├── tts_engine.py        TTS orchestrator (EdgeTTS + pyttsx3)
│   ├── selection_monitor.py Clipboard + hotkey listener
│   ├── audio_history.py     MP3 session history
│   ├── profile.py           User profile (JSON)
│   ├── network_monitor.py   Internet connectivity checker
│   └── language/            Language detection + filtering
├── gui/                     PyQt6 UI
│   ├── main_window.py       Main window with collapsible sidebar
│   ├── overlay_widget.py    Floating pill overlay
│   └── pages/               Dashboard page mixins
├── services/
│   ├── app_controller.py    Central mediator
│   └── window_manager.py    Overlay ↔ window visibility
├── styles/                  Dark/light QSS stylesheets
└── assets/                  Icons and images
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for a full technical overview.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Acknowledgements

- [edge-tts](https://github.com/rany2/edge-tts) — Microsoft neural voice synthesis
- [PyQt6](https://riverbankcomputing.com/software/pyqt/) — Desktop UI framework
- [pyttsx3](https://github.com/nateshmbhat/pyttsx3) — Offline TTS
- [pygame](https://pygame.org) — Audio playback (both online and offline)
- [pynput](https://github.com/moses-palmer/pynput) — Global hotkey listener

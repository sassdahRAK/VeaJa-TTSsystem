# VeaJa — Text-to-Speech Overlay System

VeaJa is a Windows desktop TTS (Text-to-Speech) tool with two windows: a main dashboard for typing and reading text aloud, and a lightweight overlay that floats above any app. including fullscreen games and video players and automatically displays anything you copy with Ctrl+C.

---

## Features

- **Main dashboard**: type or paste text and click the headphone button to have it read aloud
- **Floating overlay**: appears automatically when you copy text anywhere on your system
- **Fullscreen aware**: main window hides when a fullscreen app is detected, overlay stays on top
- **Ctrl+C trigger**: press Ctrl+C in any app to send copied text straight to the overlay
- **Ctrl+P toggle**: show or hide the overlay at any time
- **Speed & volume controls**: adjust TTS playback speed (0.5x–3.0x) and volume (0–100%) **Not complete yet**
- **System tray**: app keeps running in the background when windows are hidden
- **Dark / light theme**: toggle with the ⚙️ button on the main window
- **History log**: every copied text is saved to `History.txt` with a timestamp

---

## Project Structure

VeaJa-TTSsystem/ <br>
│ <br>
├── main.py  <br>
│ <br>
├── gui/ <br>
│ ├── main_window.py # Main dashboard  <br>
│ └── overlay_window.py # Floating overlay <br>
│ <br>
├── core/ <br>
│ └── tts_engine.py # TextToSpeech class <br>
│ <br>
├── styles/ <br>
│ ├── dark.qss # Dark theme stylesheet <br>
│ └── light.qss # Light theme stylesheet <br>
│ <br>
└── History.txt # Auto-created log of all copied text <br>

---

## Requirements

- Windows 10 or 11
- Python 3.10 or higher

### Python packages

Install all dependencies with:

```bash
pip install PyQt6 keyboard pyttsx3 pywin32
```

| Package    | Purpose                                     |
| ---------- | ------------------------------------------- |
| `PyQt6`    | UI framework for both windows               |
| `keyboard` | Global hotkey listener (Ctrl+C, Ctrl+P)     |
| `pyttsx3`  | Offline text-to-speech engine               |
| `pywin32`  | Windows API access for fullscreen detection |

---

## Installation

1. Clone or download this repository:

```bash
git clone https://github.com/sassdahRAK/VeaJa-TTSsystem.git
cd VeaJa-TTSsystem
```

2. Install dependencies:

```bash
pip install PyQt6 keyboard pyttsx3 pywin32
```

3. Run the app:

```bash
py main.py
```

---

## How to Use

### Starting the app

```bash
py main.py
```

The main dashboard opens automatically. The overlay and system tray are always running in the background.

### Main dashboard

| Action               | What happens                         |
| -------------------- | ------------------------------------ |
| Type text in the box | Prepares text for reading            |
| Click 🎧 button      | Reads the typed text aloud           |
| Click ⚙️ button      | Toggles dark / light theme           |
| Click — (title bar)  | Hides main window, app stays in tray |
| Click ✕ (title bar)  | Quits the entire app                 |

### Overlay

| Action                       | What happens                                 |
| ---------------------------- | -------------------------------------------- |
| Press **Ctrl+C** anywhere    | Copies text → overlay appears with that text |
| Press **Ctrl+P**             | Toggles overlay show / hide                  |
| Click **Read** button        | Reads the displayed text aloud               |
| Click **Stop** button        | Stops reading                                |
| Drag the overlay             | Move it anywhere on screen                   |
| Click **—** (overlay header) | Hides overlay to tray                        |
| Click **✕** (overlay header) | Quits the entire app                         |
| Adjust Speed slider          | Changes TTS reading speed                    |
| Adjust Vol slider            | Changes TTS volume                           |

### Fullscreen behavior

When you switch to a fullscreen app (game, video player):

- The main window **automatically hides**
- The overlay **stays visible** on top of the fullscreen app
- Press **Ctrl+C** to copy text and send it to the overlay
- When you leave the fullscreen app, the main window **automatically comes back**

---

## Architecture

VeaJa uses a **mediator pattern** - `WindowManager` in `main.py` is the only class that controls both windows. Neither window imports or calls the other directly.

main.py (WindowManager) <br>
├── owns QTimer- polls fullscreen state every 500ms <br>
├── owns Ctrl+C hotkey registration <br>
├── calls main_window.hide() / show() <br>
├── calls overlay_window.show_window() <br>
└── handles quit for both windows <br>
main_window.py <br>
└── emits signals UP to WindowManager (never hides/quits itself) <br>
overlay_window.py <br>
└── manages itself (show/hide) <br>
└── asks manager "are we in fullscreen?" before showing on clipboard <br>

### Key design decisions

**Why `WindowManager` owns the hotkeys** — hotkeys are global and fire even when the app is not focused. Registering them inside a window class ties them to that window's lifecycle, which causes bugs when the window is hidden.

**Why `QTimer.singleShot` instead of direct calls from hotkey threads** — the `keyboard` library fires callbacks from a background thread. Qt windows can only be safely touched from the main thread. `QTimer.singleShot(0, fn)` posts the call onto the Qt event queue to run on the next main thread tick.

**Why fullscreen detection checks `WS_MAXIMIZE`** — a maximized window (VS Code, browser, terminal) fills the screen but has the `WS_MAXIMIZE` Windows style flag set. A true fullscreen app (game, video player) does not. Checking the flag prevents the main window from hiding every time you maximize a normal app.

---

## Troubleshooting

**App doesn't start / import error**

- Make sure you're running from the `VeaJa-TTSsystem/` folder: `py main.py`
- Check all packages are installed: `pip install PyQt6 keyboard pyttsx3 pywin32`

**Overlay doesn't appear when I press Ctrl+C**

- Make sure the app is running (check system tray for the green icon)
- Ctrl+C must actually copy text. if nothing is selected, the clipboard doesn't change

**Main window hides when I maximize VS Code / browser**

- This should not happen with the current version — it uses `WS_MAXIMIZE` detection
- If it does, run `py main.py` fresh after replacing `main.py` with the latest version

**TTS has no sound**

- Check Windows volume and default audio output device
- pyttsx3 uses the Windows SAPI voice — make sure a voice is installed in Windows Settings → Time & Language → Speech

**`History.txt` keeps growing**

- This is by design — it logs every copied text with a timestamp
- You can delete or clear `History.txt` at any time; the app will recreate it

---

## Team

| Role                   | Responsibility                                   |
| ---------------------- | ------------------------------------------------ |
| UI / Window management | `Vean Sovanvirak` - PyQt6 windows, WindowManager |
| TTS Engine             | `Keo Seavpav` - pyttsx3 integration              |
| Overlay / Save history | `Hong Limhak` - keyboard date-time               |
---


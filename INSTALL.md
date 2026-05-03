# Veaja — Installation Guide

Step-by-step setup for all supported platforms.

---

## Requirements

| Component | Requirement |
|---|---|
| Python | 3.10 or later (tested on 3.13) |
| OS | Windows 10/11 · macOS 12+ · Linux (Ubuntu 20.04+) |
| Internet | Optional — required only for online neural voices |
| Disk space | ~150 MB (app + venv + dependencies) |

---

## Step 1 — Install Python

**Windows:**
Download from [python.org](https://www.python.org/downloads/). Check **"Add Python to PATH"** during install.

**macOS:**
```bash
brew install python@3.11
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install python3 python3-pip python3-venv
```

---

## Step 2 — Clone the repository

```bash
git clone https://github.com/sassdahRAK/VeaJa-TTSsystem.git
cd VeaJa-TTSsystem
```

---

## Step 3 — Create a virtual environment

```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

---

## Step 4 — Install Python dependencies

```bash
pip install -r requirements.txt
```

---

## Step 5 — Platform-specific setup

### Linux — Install espeak (required for offline mode)

Veaja uses `pyttsx3` for offline TTS, which requires `espeak` on Linux.
Without it, offline mode will not produce any audio.

```bash
# Ubuntu / Debian / Linux Mint
sudo apt update
sudo apt install espeak espeak-ng

# Fedora / RHEL
sudo dnf install espeak espeak-ng

# Arch / Manjaro
sudo pacman -S espeak-ng

# openSUSE
sudo zypper install espeak espeak-ng
```

Verify it works:
```bash
espeak "Hello from Veaja"
```

> **Note:** If you skip this step, Veaja will show a warning dialog on startup and online mode will still work normally.

---

### macOS — Grant Accessibility permission

Veaja uses global hotkeys (`Ctrl+C`, `Ctrl+R`) which require Accessibility access.

On first run, macOS will prompt you automatically. If it doesn't:

1. Open **System Settings** → **Privacy & Security** → **Accessibility**
2. Click **+** and add **Terminal** (or your Python IDE)
3. Restart Veaja

---

### Windows — No additional setup

Windows includes SAPI5 voices by default. Everything works after Step 4.

---

## Step 6 — Run Veaja

```bash
# Make sure venv is active first
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows

python main.py
```

---

## Command line options

```
python main.py [OPTIONS]

Options:
  (no flags)           Launch normally (default)
  --offline            Start in offline mode
  --dark               Force dark theme
  --light              Force light theme
  --no-splash          Skip splash screen (faster startup)
  --reset-profile      Reset all settings to defaults
  --voice <name>       Set voice at startup (online mode voice name)
  --rate <wpm>         Set speech rate in words per minute (default: 175)
  --volume <0.0-1.0>   Set volume (default: 1.0)
  --version            Print version and exit
  --help               Show help
```

---

## Troubleshooting

### "Offline mode doesn't work" (Linux)

**Symptom:** Clicking to read does nothing, or you see a TTS error notification.

**Fix:**
```bash
sudo apt install espeak espeak-ng
```
Then restart Veaja.

---

### "Global hotkeys don't work" (macOS)

**Symptom:** Ctrl+C and Ctrl+R don't trigger Veaja.

**Fix:** Grant Accessibility permission:
- System Settings → Privacy & Security → Accessibility → add Terminal

---

### "Online mode doesn't work"

**Symptom:** "EdgeTTS timed out" or no audio in online mode.

**Fix:**
1. Check your internet connection
2. Try switching to offline mode in Voice Settings
3. If behind a corporate proxy, configure system proxy settings

---

### "ModuleNotFoundError"

**Symptom:** `ModuleNotFoundError: No module named 'PyQt6'`

**Fix:** Make sure the virtual environment is activated:
```bash
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

---

### App crashes on rapid clicking

This was a known issue — fixed in the current version. The app now uses debounce guards
and a `pyttsx3` thread lock to prevent crashes from rapid input.

---

## Uninstalling

### Remove the app
```bash
rm -rf VeaJa-TTSsystem
```

### Remove user data (settings, history, audio cache)
```bash
# macOS / Linux
rm -rf ~/.veaja

# Windows
rmdir /s %USERPROFILE%\.veaja
```

---

## Building a standalone executable (optional)

If you want to distribute Veaja without requiring users to install Python:

```bash
pip install pyinstaller

# Linux / macOS
pyinstaller --onefile --windowed main.py

# Windows
pyinstaller --onefile --windowed --icon=assets/veaja.ico main.py
```

The executable will be in the `dist/` folder.

> **Linux note:** Users will still need to install `espeak` separately even with a standalone build.

# Veaja Installation Guide

Complete installation instructions for all platforms.

---

## Quick Install (All Platforms)

### 1. Install Python 3.10+

**Windows:**
- Download from [python.org](https://www.python.org/downloads/)
- Check "Add Python to PATH" during installation

**macOS:**
```bash
brew install python@3.10
```

**Linux:**
```bash
sudo apt install python3 python3-pip python3-venv  # Ubuntu/Debian
sudo dnf install python3 python3-pip               # Fedora
sudo pacman -S python python-pip                   # Arch
```

### 2. Clone Repository

```bash
git clone https://github.com/sassdahRAK/VeaJa-TTSsystem.git
cd VeaJa-TTSsystem
```

### 3. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 5. Platform-Specific Setup

#### **Linux Only: Install Espeak (Required for Offline Mode)**

Veaja uses espeak for offline text-to-speech on Linux. Install it before running:

```bash
# Ubuntu / Debian / Linux Mint
sudo apt update
sudo apt install espeak espeak-ng

# Fedora / RHEL / CentOS
sudo dnf install espeak espeak-ng

# Arch / Manjaro
sudo pacman -S espeak-ng

# openSUSE
sudo zypper install espeak espeak-ng
```

**Verify installation:**
```bash
espeak "Hello, this is a test"
```

If you hear speech, espeak is working correctly!

#### **macOS Only: Grant Accessibility Permission**

Veaja needs Accessibility access for global hotkeys (Ctrl+C, Ctrl+R).

On first run, macOS will prompt you. If not:

1. Open **System Settings** → **Privacy & Security** → **Accessibility**
2. Click the **+** button
3. Add **Terminal** (or **Python** if running from an IDE)
4. Restart Veaja

#### **Windows: No Additional Setup Required**

Windows includes SAPI5 voices by default. Veaja will work immediately after installing Python dependencies.

---

## Running Veaja

```bash
# Activate virtual environment first
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Run the app
python main.py
```

---

## Troubleshooting

### Linux: "Offline mode doesn't work"

**Symptom:** Clicking to read does nothing, or you see "Failed to initialize TTS engine"

**Solution:** Install espeak:
```bash
sudo apt install espeak espeak-ng
```

Then restart Veaja.

### macOS: "Global hotkeys don't work"

**Symptom:** Ctrl+C and Ctrl+R don't trigger Veaja

**Solution:** Grant Accessibility permission:
1. System Settings → Privacy & Security → Accessibility
2. Add Terminal or Python
3. Restart Veaja

### All Platforms: "Online mode doesn't work"

**Symptom:** "EdgeTTS timed out" or "No internet connection"

**Solution:**
1. Check your internet connection
2. Try switching to offline mode in Settings
3. If behind a proxy, configure system proxy settings

### All Platforms: "ModuleNotFoundError"

**Symptom:** `ModuleNotFoundError: No module named 'PyQt6'` (or other module)

**Solution:**
1. Make sure virtual environment is activated:
   ```bash
   source venv/bin/activate  # macOS/Linux
   venv\Scripts\activate     # Windows
   ```
2. Reinstall dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## Uninstallation

### Remove Application

```bash
# Delete the cloned repository
rm -rf VeaJa-TTSsystem
```

### Remove User Data

Veaja stores settings and audio history in `~/.veaja/`:

```bash
# Linux / macOS
rm -rf ~/.veaja

# Windows
rmdir /s %USERPROFILE%\.veaja
```

---

## Building Standalone Executables (Optional)

For distributing Veaja without requiring users to install Python:

### Using PyInstaller

```bash
pip install pyinstaller

# Windows
pyinstaller --onefile --windowed --icon=assets/veaja.ico main.py

# macOS
pyinstaller --onefile --windowed --icon=assets/logo_dark.png main.py

# Linux
pyinstaller --onefile --windowed main.py
```

The executable will be in the `dist/` folder.

**Note:** Linux users will still need to install espeak separately:
```bash
sudo apt install espeak espeak-ng
```

---

## System Requirements

| Component | Requirement |
|---|---|
| **Python** | 3.10 or later |
| **RAM** | 256 MB minimum, 512 MB recommended |
| **Disk Space** | 100 MB for app + dependencies |
| **Internet** | Optional (required only for online neural voices) |
| **Operating System** | Windows 10/11, macOS 12+, Linux (Ubuntu 20.04+, Fedora 35+, Arch) |

### Linux-Specific Requirements

- **X11 or XWayland** (Wayland-only sessions not supported)
- **espeak or espeak-ng** (for offline TTS)
- **ALSA or PulseAudio** (for audio playback)

---

## Getting Help

- **Issues:** [GitHub Issues](https://github.com/sassdahRAK/VeaJa-TTSsystem/issues)
- **Documentation:** [README.md](README.md) · [ARCHITECTURE.md](ARCHITECTURE.md)
- **License:** [MIT License](LICENSE)


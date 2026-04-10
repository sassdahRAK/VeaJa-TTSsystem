# Veaja — Architecture

This document describes how Veaja is structured, why the layers exist, and how to extend it.

---

## Design principles

- **`core/` is pure Python with zero UI dependencies.** It runs on every platform including future mobile targets (Android, iOS via BeeWare).
- **`platform_adapters/` abstracts all OS calls.** `core/` never imports `winreg`, `ctypes`, `AppKit`, or anything platform-specific.
- **`gui/` is the PyQt6 desktop shell.** It can be swapped for a Toga or Kivy shell for mobile without touching business logic.
- **`services/` is the glue layer.** `AppController` wires components together so neither `core/` nor `gui/` know about each other.
- **Languages are added in `core/language/` and `i18n/` only.** No changes needed in the TTS engine.

---

## Layer diagram

```
┌──────────────────────────────────────────────────────────┐
│                        main.py                           │
│              (composition root, Qt app setup)            │
└───────────────────────────┬──────────────────────────────┘
                            │
            ┌───────────────▼───────────────┐
            │          services/            │
            │  AppController · WindowManager│
            │  (mediator — wires everything)│
            └──────┬──────────────┬─────────┘
                   │              │
        ┌──────────▼──┐     ┌─────▼──────────┐
        │    gui/     │     │    core/        │
        │  PyQt6 UI   │     │ business logic  │
        │  (desktop)  │     │ (no GUI imports)│
        └─────────────┘     └────────┬────────┘
                                     │
                        ┌────────────▼────────────┐
                        │   platform_adapters/    │
                        │ (OS-specific: win/mac/  │
                        │  linux/android/ios)     │
                        └─────────────────────────┘
```

---

## Folder structure

```
veaja/
│
├── main.py                        Entry point — QApplication setup, splash, AppController
│
├── config/
│   └── settings.py                App-wide constants and tuneable defaults
│
├── core/                          Platform-independent business logic
│   ├── tts_engine.py              TTS orchestrator (EdgeTTS + pyttsx3 backends)
│   ├── selection_monitor.py       Clipboard / selection watcher + Ctrl+R hotkey
│   ├── audio_history.py           MP3 session FIFO queue  (~/.veaja/audio/)
│   ├── profile.py                 User profile JSON        (~/.veaja/profile.json)
│   ├── network_monitor.py         Background internet connectivity checker
│   └── language/
│       ├── __init__.py            Public API: filter_for_tts(), detect_language()
│       └── detector.py            Unicode-range + langdetect language detection
│
├── gui/                           PyQt6 desktop UI (no business logic here)
│   ├── main_window.py             Dashboard window (tabs: Read · History · Settings · Profile · Info)
│   ├── overlay_widget.py          Floating pill overlay — karaoke, drag, context menu
│   ├── tray_icon.py               System tray icon + desktop notifications
│   ├── splash_screen.py           Startup splash screen
│   ├── profile_dialog.py          Profile editor modal
│   ├── terms_dialog.py            Terms & privacy dialog
│   ├── tour_overlay.py            Interactive onboarding product tour
│   ├── photo_crop_dialog.py       Avatar photo crop tool
│   ├── theme_mixin.py             Dark / light theme QSS helpers
│   ├── icon_utils.py              SVG / icon loading helpers
│   ├── _window_shared.py          Shared window base utilities
│   ├── sidebar_styles.py          Sidebar styling helpers
│   └── pages/                     Dashboard page mixins (keep main_window.py manageable)
│       ├── dashboard_mixin.py     Main read interface — text input, read button, progress
│       ├── history_mixin.py       Audio history playback with seek slider
│       ├── settings_mixin.py      Voice, speed, volume, online/offline toggle
│       ├── profile_mixin.py       Display name, avatar, highlight color editor
│       └── info_pages_mixin.py    FAQ, About, Release notes, Terms link
│
├── services/
│   ├── app_controller.py          Central mediator — wires all component signals and slots
│   └── window_manager.py          Overlay ↔ main window visibility rules
│
├── platform_adapters/             OS-specific abstractions (never imported by core/)
│   ├── base.py                    Abstract interface — all adapters implement this
│   ├── windows.py                 Windows x64 / ARM64
│   ├── macos.py                   macOS Intel / Apple Silicon
│   ├── linux.py                   Linux x64 / ARM (incl. Raspberry Pi)
│   ├── android.py                 Android — BeeWare Toga (STUB, not yet implemented)
│   └── ios.py                     iOS / iPadOS — BeeWare Toga (STUB, not yet implemented)
│
├── styles/
│   ├── dark.qss                   Dark theme Qt stylesheet
│   └── light.qss                  Light theme Qt stylesheet
│
├── i18n/
│   ├── __init__.py                t(key, lang) translation helper
│   └── en/strings.json            English UI strings (35+ keys)
│
└── assets/
    ├── logo_dark.png
    └── logo_light.png
```

---

## Component overview

### `main.py` — Entry point

Sets up `QApplication`, configures platform fonts, loads the saved theme from profile before
any window is created, shows the splash screen, then hands off to `AppController`.

```
QApplication
    └── SplashScreen  (2.5 s)
    └── AppController.start()
            └── loads profile → shows Terms if first run → shows main window
```

---

### `config/settings.py` — Constants

All tuneable defaults live here. Change a value once — it propagates everywhere.

| Constant | Default | Description |
|---|---|---|
| `APP_VERSION` | `"1.0.0"` | Displayed in About page |
| `DEFAULT_VOICE` | `"en-US-AriaNeural"` | Online voice |
| `DEFAULT_RATE` | `175` | Words per minute |
| `DEFAULT_VOLUME` | `1.0` | 0.0 – 1.0 |
| `MAX_AUDIO_SESSIONS` | `3` | FIFO depth for audio history |
| `LANGUAGE_FILTER_ENABLED` | `True` | Filter non-English text |
| `EDGE_TTS_TIMEOUT_S` | `10` | Seconds per sentence attempt |

---

### `core/tts_engine.py` — TTS orchestrator

Manages two backends selected at runtime:

**EdgeTTSWorker (online)**
- Streams synthesis sentence-by-sentence via `edge-tts`
- Tracks word boundaries for real-time karaoke highlighting
- Concatenates per-sentence MP3s into a session file
- Supports pause and resume via `pygame.mixer`

**Pyttsx3Worker (offline)**
- SAPI5 on Windows, AVSpeechSynthesizer on macOS, espeak-ng on Linux
- No pause/resume (system limitation)

Signal lifecycle:
```
preparing_speech  →  started_speaking
                      ├── word_highlight(word, start, end)   [online only]
                      ├── paused_speaking / resumed_speaking
                      └── finished_speaking
error_occurred  (at any stage)
```

---

### `core/selection_monitor.py` — Clipboard watcher

- Polls `QApplication.clipboard()` for changes
- Listens for global `Ctrl+C` / `Cmd+C` via `pynput` (thread-safe bridge to Qt main thread)
- Supports `Ctrl+R` to read clipboard without re-copying
- 250 ms debounce prevents duplicate events

Emits:
- `text_ready(str)` — new text is available
- `read_clipboard_hotkey()` — user pressed Ctrl+R

---

### `core/profile.py` — User preferences

Stored at `~/.veaja/profile.json`:

```json
{
  "version": 1,
  "terms_accepted": false,
  "dark_mode": null,
  "voice_index": 0,
  "speed": 175,
  "volume": 1.0,
  "highlight_color": "#FFD60A",
  "overlay_shape": "rectangle",
  "logo_path": null
}
```

`dark_mode: null` means follow the system. `true` / `false` override it.

---

### `core/network_monitor.py` — Connectivity

Polls internet connectivity every 10 seconds in a background thread.
Emits `connectivity_changed(bool)` → `AppController` auto-switches TTS backend.

---

### `core/language/detector.py` — Language detection

Two-stage detection:
1. Unicode script range analysis (30+ scripts: CJK, Thai, Devanagari, Arabic, Cyrillic, etc.)
2. Optional `langdetect` for short Latin-script texts

`filter_for_tts(text, target_lang="en")` returns `(filtered_text, was_filtered, detected_lang)`.

The `VOICE_CATALOGUE` maps ISO 639-1 codes to language metadata and edge-tts locales.
Currently only `"en"` has `"tts_supported": True`. Other languages are scaffolded for future expansion.

---

### `services/app_controller.py` — Central mediator

`AppController` is the composition root. It:

1. Creates all components (`TTSEngine`, `MainWindow`, `OverlayWidget`, `TrayIcon`, `SelectionMonitor`, `WindowManager`, `NetworkMonitor`)
2. Wires all Qt signals to slots (250+ lines of connections)
3. Routes text-ready events through the language filter before speaking
4. Syncs theme changes across tray icon, overlay, and main window
5. Handles first-launch flow (Terms dialog, profile loading)

Neither `core/` nor `gui/` imports the other — all coupling goes through `AppController`.

---

### `services/window_manager.py` — Visibility rules

```
Overlay appears  →  main window hides to tray
Overlay hides    →  main window returns (if it was open before)
Tray icon click  →  always show main window
```

---

### `gui/overlay_widget.py` — Floating pill

The pill has three visual states:

| State | Size | Contents |
|---|---|---|
| Collapsed | 80 × 80 px circle | Logo only |
| Expanded | auto × 56 px pill | Logo + scrolling text |
| Karaoke | expanded | Words highlighted in real time |

Interaction:
- Single click → read / pause / resume
- Drag (threshold: 6 px) → reposition anywhere on screen
- Right-click → context menu

macOS: Uses `NSPopUpMenuWindowLevel` (101) via Objective-C bridge so the pill stays above all other app windows.

---

### `gui/tour_overlay.py` — Onboarding tour

Step-by-step interactive guide. Masks the UI, highlights elements with arrows, and walks the user through copying text → pill appearing → clicking to hear it. Can be replayed from the sidebar at any time.

---

## Data flow — reading text aloud

```
User copies text (Ctrl+C)
    │
    ▼
SelectionMonitor  ──text_ready(str)──►  AppController
                                              │
                                    language filter
                                    (filter_for_tts)
                                              │
                             ┌────────────────┴──────────────────┐
                             ▼                                   ▼
                    OverlayWidget                        TTSEngine.speak()
                    (show pill + text)                          │
                                              ┌─────────────────┴──────────────────┐
                                              ▼                                    ▼
                                   EdgeTTSWorker (online)            Pyttsx3Worker (offline)
                                              │
                                    word_highlight signal
                                              │
                                    OverlayWidget + MainWindow
                                    (karaoke highlighting)
                                              │
                                    AudioHistory.save(session_mp3)
```

---

## Adding a new TTS language

1. `core/language/detector.py` — set `VOICE_CATALOGUE["xx"]["tts_supported"] = True`
2. `core/tts_engine.py` — add edge-tts voices for that locale to `EDGE_TTS_VOICES`
3. `i18n/xx/strings.json` — add translated UI strings
4. `gui/pages/settings_mixin.py` — expose language selector in Voice Settings
5. `services/app_controller.py` — pass `target_lang` from profile to `filter_for_tts()`

---

## Mobile expansion (Android & iOS)

The mobile shell will import `core/` and `services/` unchanged.
Only `gui/` and `platform_adapters/` need new implementations.

Planned layout:
```
mobile/
├── android/
│   ├── main_toga.py          BeeWare entry point
│   └── ui/                   Toga widgets mirroring gui/pages/
└── ios/
    ├── main_toga.py
    └── ui/
```

---

## Cross-platform TTS backend matrix

| Platform | Online backend | Offline backend |
|---|---|---|
| Windows | edge-tts | pyttsx3 / SAPI5 |
| macOS | edge-tts | pyttsx3 / AVSpeechSynth |
| Linux | edge-tts | pyttsx3 / espeak-ng |
| Android | edge-tts | Android TTS engine |
| iOS | edge-tts | AVSpeechSynthesizer |

---

## Coding conventions

- `core/` must never import anything from `gui/`, `services/`, or `platform_adapters/`
- Platform-specific code belongs in `platform_adapters/`, never scattered in business logic
- All Qt signals use `snake_case` names; slot handlers are named `on_<signal_name>`
- New UI pages are added as mixins in `gui/pages/` and mixed into `MainWindow`
- Constants go in `config/settings.py`, not inlined in code
- User-visible strings go in `i18n/en/strings.json`, accessed via `t("key")`

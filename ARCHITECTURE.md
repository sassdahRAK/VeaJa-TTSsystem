# Veaja — Architecture

This document describes how Veaja is structured, why the layers exist, and how to extend it.

---

## Design principles

- **`core/` is pure Python with zero UI dependencies.** Business logic runs on every platform.
- **`gui/` is the PyQt6 desktop shell.** It can be swapped for another UI toolkit without touching business logic.
- **`services/` is the glue layer.** `AppController` wires components together so neither `core/` nor `gui/` know about each other.
- **`platform_adapters/` abstracts OS calls.** `core/` never imports `winreg`, `ctypes`, `AppKit`, or anything platform-specific.

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
├── main.py                        Entry point — QApplication, splash, espeak check, AppController
├── requirements.txt               Pinned Python dependencies
├── ARCHITECTURE.md                This file
├── README.md                      User-facing documentation
├── INSTALL.md                     Platform-specific installation guide
│
├── config/
│   └── settings.py                App-wide constants and tuneable defaults
│
├── core/                          Platform-independent business logic
│   ├── tts_engine.py              TTS orchestrator (EdgeTTS + Pyttsx3 backends)
│   │                              — WAV audio cache for instant offline replay
│   │                              — pyttsx3 lock prevents concurrent espeak segfaults
│   ├── selection_monitor.py       Clipboard watcher + Ctrl+C / Ctrl+R global hotkeys
│   ├── audio_history.py           MP3 session FIFO queue  (~/.veaja/audio/)
│   ├── profile.py                 User profile JSON        (~/.veaja/profile.json)
│   ├── network_monitor.py         Background internet connectivity checker (10s interval)
│   └── language/
│       ├── __init__.py            Public API: filter_for_tts(), detect_language()
│       └── detector.py            Unicode-range language detection
│
├── gui/                           PyQt6 desktop UI (no business logic here)
│   ├── main_window.py             Main window — sidebar, content stack, hamburger toggle
│   ├── overlay_widget.py          Floating pill overlay — karaoke, drag, pause/resume
│   ├── tray_icon.py               System tray icon + desktop notifications
│   ├── splash_screen.py           Startup splash screen
│   ├── profile_dialog.py          Profile editor modal
│   ├── terms_dialog.py            Privacy & Data Notice (non-modal, overlay stays active)
│   ├── tour_overlay.py            Interactive onboarding product tour
│   ├── photo_crop_dialog.py       Avatar photo crop tool
│   ├── theme_mixin.py             Dark / light theme QSS helpers
│   ├── icon_utils.py              SVG / icon loading helpers
│   ├── _window_shared.py          Shared window base utilities (DPI scaling, pixmap helpers)
│   ├── sidebar_styles.py          Sidebar QSS styling
│   └── pages/                     Dashboard page mixins
│       ├── dashboard_mixin.py     Main read interface — text input, read button, tabs
│       ├── settings_mixin.py      Voice, speed, volume, online/offline toggle, language
│       ├── overlay_settings_mixin.py  Overlay shape, animation settings
│       ├── history_mixin.py       Audio session history playback
│       ├── profile_mixin.py       Display name, avatar, highlight color
│       ├── api_keys_mixin.py      API key management with lock screen
│       ├── analyse_mixin.py       Text analysis page
│       ├── info_pages_mixin.py    FAQ, Tutorial, Data Privacy, Terms
│       ├── _ai_caller.py          AI feature caller (Summary, Translate, Code, Ask, etc.)
│       ├── _tab_ask.py            Ask tab UI
│       ├── _tab_code.py           Code tab UI
│       ├── _tab_generate.py       Generate tab UI
│       ├── _tab_grammar.py        Grammar tab UI
│       ├── _tab_live_caption.py   Live caption tab UI
│       ├── _tab_overlay.py        Overlay tab UI
│       ├── _tab_summary.py        Summary tab UI
│       ├── _tab_text.py           Text tab UI
│       └── _tab_translate.py      Translate tab UI
│
├── services/
│   ├── app_controller.py          Central mediator — all signal/slot wiring, mode logic,
│   │                              debounce guards, watchdog timer, WAV cache cleanup
│   └── window_manager.py          Overlay ↔ main window visibility rules
│
├── platform_adapters/             OS-specific abstractions
│   ├── base.py                    Abstract interface
│   ├── windows.py                 Windows x64 / ARM64
│   ├── macos.py                   macOS Intel / Apple Silicon
│   ├── linux.py                   Linux x64 / ARM
│   ├── android.py                 Android stub (future)
│   └── ios.py                     iOS stub (future)
│
├── styles/
│   ├── dark.qss                   Dark theme Qt stylesheet
│   └── light.qss                  Light theme Qt stylesheet
│
├── i18n/
│   ├── __init__.py                t(key, lang) translation helper
│   └── en/strings.json            English UI strings
│
└── assets/
    ├── logo_dark.png
    ├── logo_light.png
    └── veaja.ico
```

---

## Component overview

### `main.py` — Entry point

Sets up `QApplication`, configures platform fonts, checks for espeak on Linux (shows a
helpful dialog if missing), loads the saved theme from profile before any window is created,
shows the splash screen, then hands off to `AppController`.

```
QApplication
    └── espeak check (Linux only)
    └── SplashScreen (2.5 s)
    └── AppController.start()
            └── loads profile
            └── NetworkMonitor fires first check → sets online/offline mode
            └── shows Terms dialog (non-modal) if first run
            └── shows main window
```

---

### `config/settings.py` — Constants

| Constant | Default | Description |
|---|---|---|
| `APP_VERSION` | `"1.0.0"` | Displayed in About page |
| `DEFAULT_VOICE` | `"en-US-AriaNeural"` | Default online voice |
| `DEFAULT_RATE` | `175` | Words per minute |
| `DEFAULT_VOLUME` | `1.0` | 0.0 – 1.0 |
| `MAX_AUDIO_SESSIONS` | `3` | FIFO depth for audio history |
| `EDGE_TTS_TIMEOUT_S` | `10` | Seconds per sentence attempt |
| `EDGE_TTS_MAX_RETRIES` | `3` | Retry attempts before giving up |
| `MAX_SENTENCE_QUEUE` | `50` | Max sentences per speak() call |
| `MAX_INPUT_CHARS` | `25000` | Input cap before truncation |

---

### `core/tts_engine.py` — TTS orchestrator

Two backends, selected at runtime based on network state and user preference:

**EdgeTTSWorker (online)**
- Streams synthesis sentence-by-sentence via `edge-tts` (Microsoft Azure neural TTS)
- Tracks word boundaries for real-time karaoke highlighting
- Plays audio via `pygame.mixer` — supports pause/resume
- Concatenates per-sentence MP3s into a session file for history

**Pyttsx3Worker (offline)**
- Renders each sentence to a WAV file via `pyttsx3.save_to_file()`
- Plays WAV files via `pygame.mixer` — supports pause/resume
- WAV audio cache: same text replays instantly without re-rendering
- `pyttsx3_lock` prevents concurrent espeak access (segfault prevention on Linux)
- Auto-selects English (US) voice on startup

**TTSEngine (orchestrator)**
- Holds one active worker at a time
- `_stopping` guard prevents overlapping stop/start races
- `_wav_cache` holds rendered WAV paths for instant replay
- `__del__` cleans up cached WAV files on garbage collection

Signal lifecycle:
```
preparing_speech → started_speaking
                    ├── word_highlight(start, end)   [EdgeTTS only]
                    ├── paused_speaking / resumed_speaking
                    └── finished_speaking
error_occurred  (at any stage)
```

---

### `core/network_monitor.py` — Connectivity

Polls internet connectivity every 10 seconds via raw socket probes to:
- `8.8.8.8:53` (Google DNS)
- `1.1.1.1:53` (Cloudflare DNS)
- `9.9.9.9:53` (Quad9 DNS)

Emits `connectivity_changed(bool)` → `AppController._on_connectivity_changed()`.

**Mode switching rule:** Network state always wins.
- WiFi drops → force offline immediately
- WiFi restores → force online immediately (if edge-tts available)
- User can toggle manually while network is stable

---

### `core/profile.py` — User preferences

Stored at `~/.veaja/profile.json`. Key fields:

```json
{
  "version": 3,
  "app_name": "Veaja",
  "dark_mode": null,
  "voice_index": 0,
  "speed": 175,
  "volume": 1.0,
  "highlight_color": "#FFD60A",
  "overlay_shape": "rectangle",
  "overlay_anim_spin": true,
  "user_mode_preference": null,
  "logo_path": null,
  "terms_accepted": false,
  "nav_order": [1, 7, 8, 2],
  "tab_order": [0, 1, 2, 3, 4, 5, 6, 7, 8]
}
```

`dark_mode: null` = follow system. `user_mode_preference: null` = follow network.

---

### `services/app_controller.py` — Central mediator

The composition root. Responsibilities:

1. Creates all components and wires all Qt signals to slots
2. Routes text through language filter before speaking
3. **Debounce guards** — pause/resume are instant; stop is debounced 200ms (same-action only)
4. **Smart restart** — checks clipboard for new text vs same text; clears WAV cache on restart
5. **Network mode sync** — WiFi change always overrides manual selection
6. **Watchdog timer** — force-resets UI if TTS gets stuck in PROCESSING for 30s
7. **WAV cleanup** — clears cached WAV files on app quit

---

### `gui/main_window.py` — Main window

- **Sidebar** — collapsible via hamburger button `☰` in title bar
  - Remembers last width on collapse/restore
  - Contains profile photo, nav links, help section
- **Content stack** — 10 pages (Dashboard, Voice Setting, History, Ask, Privacy, Tutorial, Profile, Overlay Setting, API Keys, Analyse)
- **Splitter** — sidebar width is user-draggable

---

### `gui/overlay_widget.py` — Floating pill

Three visual states:

| State | Appearance |
|---|---|
| Collapsed | Circle/rectangle logo only |
| Expanded (hover) | Logo + text preview + restart button |
| Speaking | Red title "Speaking… ■ click to stop" + karaoke highlight |
| Paused | Orange title "Paused ▶ click to resume" |
| Processing | Animated dots "Processing..." |

Interaction:
- Single click → read / pause / resume (state-aware)
- Drag → reposition anywhere on screen
- Right-click → context menu (Hide, Settings, Quit)
- Restart button → smart restart (new clipboard text or replay same)

macOS: Uses `NSPopUpMenuWindowLevel` (101) to float above all other apps.
Linux: Uses `startSystemMove()` for reliable drag on X11/Wayland.

---

### `gui/terms_dialog.py` — Privacy notice

**Non-modal** — uses `show()` not `exec()`. The overlay stays fully interactive while
the dialog is open. `WA_ShowWithoutActivating` prevents focus steal.

---

## Data flow — reading text aloud

```
User copies text (Ctrl+C)
    │
    ▼
SelectionMonitor ──text_ready(str)──► AppController
                                            │
                                  language filter
                                  (filter_for_tts)
                                            │
                         ┌──────────────────┴──────────────────┐
                         ▼                                     ▼
                OverlayWidget                          TTSEngine.speak()
                (show pill + text)                            │
                                         ┌────────────────────┴──────────────────┐
                                         ▼                                       ▼
                              EdgeTTSWorker (online)              Pyttsx3Worker (offline)
                              edge-tts → MP3 → pygame             pyttsx3 → WAV → pygame
                                         │
                               word_highlight signal
                                         │
                              OverlayWidget + MainWindow
                              (karaoke highlighting)
                                         │
                              AudioHistory.save(session_mp3)
```

---

## Cross-platform TTS backend matrix

| Platform | Online backend | Offline backend | Pause/Resume |
|---|---|---|---|
| Windows | edge-tts + pygame | pyttsx3 / SAPI5 + pygame | ✅ Both |
| macOS | edge-tts + pygame | pyttsx3 / AVSpeechSynth + pygame | ✅ Both |
| Linux | edge-tts + pygame | pyttsx3 / espeak-ng + pygame | ✅ Both |

---

## Coding conventions

- `core/` must never import anything from `gui/`, `services/`, or `platform_adapters/`
- All Qt signals use `snake_case` names; slot handlers are named `_on_<signal_name>`
- New UI pages are added as mixins in `gui/pages/` and mixed into `MainWindow`
- Constants go in `config/settings.py`, not inlined in code
- WAV temp files must always be cleaned up — use `owns_files` flag pattern

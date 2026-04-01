# Veaja — Project Architecture

## Design principles
- **core/** is pure Python with zero UI dependencies — runs on every platform.
- **platform_adapters/** abstracts OS calls so core/ never imports `winreg`, `ctypes`, etc. directly.
- **gui/** is the PyQt6 desktop shell — swappable with a Toga/Kivy shell for mobile.
- New languages are added in **core/language/** and **i18n/** without touching the TTS engine.

---

## Folder structure

```
VeaJa-TTSs/
│
├── main.py                        Entry point (desktop)
│
├── config/
│   └── settings.py                App-wide constants & feature flags
│
├── core/                          Platform-independent business logic
│   ├── audio_history.py           Session MP3 FIFO queue (~/.veaja/audio/)
│   ├── profile.py                 User profile JSON (~/.veaja/profile.json)
│   ├── selection_monitor.py       Clipboard/selection watcher + Ctrl+R hotkey
│   ├── tts_engine.py              TTS orchestrator (EdgeTTS + pyttsx3 backends)
│   └── language/
│       ├── __init__.py            Public API: filter_for_tts, detect_language
│       ├── detector.py            Unicode-range + langdetect language detection
│       └── voices.py              [future] Per-language voice catalogue
│
├── gui/                           PyQt6 desktop UI
│   ├── main_window.py             Dashboard window
│   ├── overlay_widget.py          Floating pill overlay
│   ├── tray_icon.py               System tray icon
│   ├── splash_screen.py           Splash screen
│   ├── profile_dialog.py          Profile editor
│   ├── terms_dialog.py            Terms & privacy
│   └── tour_overlay.py            Interactive product tour
│
├── styles/                        Qt style sheets
│   ├── dark.qss
│   └── light.qss
│
├── services/
│   ├── app_controller.py          Central mediator — wires all components
│   └── window_manager.py          Overlay ↔ main-window visibility rules
│
├── platform_adapters/             OS-specific adapters (never imported by core/)
│   ├── base.py                    Abstract interface
│   ├── windows.py                 Windows x64 / ARM64
│   ├── macos.py                   macOS Intel / Apple Silicon
│   ├── linux.py                   Linux x64 / ARM (incl. Raspberry Pi)
│   ├── android.py                 Android — BeeWare Toga (STUB)
│   └── ios.py                     iOS / iPadOS — BeeWare Toga (STUB)
│
├── i18n/                          Internationalisation strings
│   ├── __init__.py                t(key, lang) helper
│   ├── en/strings.json            English (default)
│   ├── th/strings.json            [add when Thai UI is needed]
│   ├── zh/strings.json            [add when Chinese UI is needed]
│   └── …
│
└── assets/
    ├── logo_dark.png
    ├── logo_light.png
    └── …
```

---

## Language support expansion

To add a new **TTS language** (e.g. Thai):

1. `core/language/detector.py` — `VOICE_CATALOGUE["th"]["tts_supported"] = True`
2. `core/tts_engine.py` — add Thai edge-tts voices to `EDGE_TTS_VOICES` for that locale
3. `i18n/th/strings.json` — add translated UI strings
4. `gui/main_window.py` — expose language selector in Voice Settings
5. `services/app_controller.py` — pass `target_lang` from profile to `filter_for_tts()`

## Mobile / tablet expansion (Android & iOS)

The mobile UI will be a separate app (BeeWare Toga) that **imports core/ and services/**
without change.  Only `gui/` and `platform_adapters/` need new implementations.

Roadmap:
```
mobile/
├── android/
│   ├── main_toga.py       BeeWare entry point
│   └── ui/                Toga widgets mirroring gui/
└── ios/
    ├── main_toga.py
    └── ui/
```

## Cross-platform TTS backend plan

| Platform      | Online backend | Offline backend         |
|---------------|---------------|-------------------------|
| Windows       | edge-tts      | pyttsx3 / SAPI5         |
| macOS         | edge-tts      | pyttsx3 / AVSpeechSynth |
| Linux         | edge-tts      | pyttsx3 / espeak-ng     |
| Android       | edge-tts      | Android TTS engine      |
| iOS           | edge-tts      | AVSpeechSynthesizer     |

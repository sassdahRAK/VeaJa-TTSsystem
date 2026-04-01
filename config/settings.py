"""
config.settings
===============
Centralised app-wide constants and tuneable defaults.

All feature flags and limits live here so they are easy to find
and override without hunting through the codebase.

Cross-platform note
-------------------
Platform-specific paths are resolved at runtime via platform_adapters,
not hardcoded here.
"""

# ── App identity ───────────────────────────────────────────────────────────────
APP_NAME    = "Veaja"
APP_VERSION = "1.0.0"

# ── Language / TTS ────────────────────────────────────────────────────────────
DEFAULT_LANGUAGE      = "en"          # ISO 639-1
DEFAULT_VOICE         = "en-US-AriaNeural"
DEFAULT_RATE          = 175           # words per minute equivalent
DEFAULT_VOLUME        = 1.0           # 0.0 – 1.0
MAX_SENTENCE_LENGTH   = 500           # chars; longer sentences are split
MIN_SENTENCE_MERGE    = 40            # chars; shorter fragments are merged
NON_LATIN_THRESHOLD   = 0.20          # fraction above which text is "not English"

# ── Language protection ────────────────────────────────────────────────────────
LANGUAGE_FILTER_ENABLED    = True     # Always filter for safety
NOTIFY_ON_LANGUAGE_FILTER  = True     # Show tray notification when filtered

# ── Audio history ─────────────────────────────────────────────────────────────
MAX_AUDIO_SESSIONS  = 3               # FIFO queue depth

# ── Overlay ───────────────────────────────────────────────────────────────────
OVERLAY_LOGO_SIZE   = 72              # px
OVERLAY_TEXT_WIDTH  = 240             # px — expanded pill text area
OVERLAY_ANIM_MS     = 220             # slide animation duration
OVERLAY_DRAG_PX     = 6              # drag detection threshold

# ── Highlight ─────────────────────────────────────────────────────────────────
DEFAULT_HIGHLIGHT_COLOR = "#FFD60A"   # yellow

# ── Network ───────────────────────────────────────────────────────────────────
EDGE_TTS_TIMEOUT_S  = 10             # seconds per sentence synthesis attempt

# ── Platform keep-front timer (macOS) ─────────────────────────────────────────
KEEP_FRONT_INTERVAL_MS = 500

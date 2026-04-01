"""
core.language.detector
======================
Language detection and text filtering.  Zero required dependencies.
Optional: pip install langdetect  (improves accuracy for short texts)

Design goals
------------
• Never raises — every public function returns a safe result.
• Works offline with the built-in Unicode-range heuristic.
• Sentence-level + word-level extraction for mixed-language text.
• Easily extended: add a new language by inserting a row in VOICE_CATALOGUE.

Cross-platform
--------------
Pure Python — runs identically on Windows, macOS, Linux, Android (Kivy/
BeeWare), and iOS (Pythonista / BeeWare).
"""

import re
from typing import Optional

# ── Unicode block → ISO 639-1 language code ───────────────────────────────────
# Each tuple: (range_start, range_end_inclusive, iso_code)
_SCRIPT_RANGES: list[tuple[int, int, str]] = [
    # CJK
    (0x4E00, 0x9FFF, "zh"),   # CJK Unified Ideographs
    (0x3400, 0x4DBF, "zh"),   # CJK Extension A
    (0x20000, 0x2A6DF, "zh"), # CJK Extension B
    (0x3040, 0x309F, "ja"),   # Hiragana
    (0x30A0, 0x30FF, "ja"),   # Katakana
    (0x31F0, 0x31FF, "ja"),   # Katakana phonetic extensions
    (0xAC00, 0xD7AF, "ko"),   # Hangul Syllables
    (0x1100, 0x11FF, "ko"),   # Hangul Jamo
    # South / Southeast Asia
    (0x0E00, 0x0E7F, "th"),   # Thai
    (0x0900, 0x097F, "hi"),   # Devanagari (Hindi, Marathi, etc.)
    (0x0980, 0x09FF, "bn"),   # Bengali
    (0x0A00, 0x0A7F, "pa"),   # Gurmukhi (Punjabi)
    (0x0A80, 0x0AFF, "gu"),   # Gujarati
    (0x0B00, 0x0B7F, "or"),   # Odia
    (0x0B80, 0x0BFF, "ta"),   # Tamil
    (0x0C00, 0x0C7F, "te"),   # Telugu
    (0x0C80, 0x0CFF, "kn"),   # Kannada
    (0x0D00, 0x0D7F, "ml"),   # Malayalam
    (0x0D80, 0x0DFF, "si"),   # Sinhala
    (0x1000, 0x109F, "my"),   # Myanmar (Burmese)
    (0x1780, 0x17FF, "km"),   # Khmer
    (0x1C90, 0x1CBF, "ka"),   # Georgian supplement
    # Middle East / Africa
    (0x0600, 0x06FF, "ar"),   # Arabic
    (0x0750, 0x077F, "ar"),   # Arabic Supplement
    (0x0590, 0x05FF, "he"),   # Hebrew
    (0x07C0, 0x07FF, "ha"),   # N'Ko (West African)
    (0x1200, 0x137F, "am"),   # Ethiopic (Amharic)
    # European non-Latin
    (0x0400, 0x04FF, "ru"),   # Cyrillic
    (0x0500, 0x052F, "ru"),   # Cyrillic Supplement
    (0x0370, 0x03FF, "el"),   # Greek
]

# ── Language meta-data for future TTS backend selection ───────────────────────
# "tts_supported" = True  → Veaja can already read this language
# Add entries as new backends are integrated
VOICE_CATALOGUE: dict[str, dict] = {
    "en": {"name": "English",    "tts_supported": True,  "edge_locale": "en-US"},
    "zh": {"name": "Chinese",    "tts_supported": False, "edge_locale": "zh-CN"},
    "ja": {"name": "Japanese",   "tts_supported": False, "edge_locale": "ja-JP"},
    "ko": {"name": "Korean",     "tts_supported": False, "edge_locale": "ko-KR"},
    "th": {"name": "Thai",       "tts_supported": False, "edge_locale": "th-TH"},
    "hi": {"name": "Hindi",      "tts_supported": False, "edge_locale": "hi-IN"},
    "ar": {"name": "Arabic",     "tts_supported": False, "edge_locale": "ar-EG"},
    "fr": {"name": "French",     "tts_supported": False, "edge_locale": "fr-FR"},
    "de": {"name": "German",     "tts_supported": False, "edge_locale": "de-DE"},
    "es": {"name": "Spanish",    "tts_supported": False, "edge_locale": "es-ES"},
    "pt": {"name": "Portuguese", "tts_supported": False, "edge_locale": "pt-BR"},
    "ru": {"name": "Russian",    "tts_supported": False, "edge_locale": "ru-RU"},
    "vi": {"name": "Vietnamese", "tts_supported": False, "edge_locale": "vi-VN"},
    "id": {"name": "Indonesian", "tts_supported": False, "edge_locale": "id-ID"},
}


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _char_script(ch: str) -> Optional[str]:
    """Return the ISO code for ch's script, or None if Latin/neutral."""
    cp = ord(ch)
    for lo, hi, lang in _SCRIPT_RANGES:
        if lo <= cp <= hi:
            return lang
    return None


def _non_latin_ratio(text: str) -> float:
    """Fraction of alphabetic characters that belong to a non-Latin script."""
    alpha = [c for c in text if c.isalpha()]
    if not alpha:
        return 0.0
    non_latin = sum(1 for c in alpha if _char_script(c) is not None)
    return non_latin / len(alpha)


def _dominant_non_latin_lang(text: str) -> Optional[str]:
    """Return the most frequent non-Latin script language found in text."""
    counts: dict[str, int] = {}
    for ch in text:
        lang = _char_script(ch)
        if lang:
            counts[lang] = counts.get(lang, 0) + 1
    return max(counts, key=lambda k: counts[k]) if counts else None


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def detect_language(text: str) -> str:
    """
    Detect the dominant language of *text*.

    Returns an ISO 639-1 code ('en', 'zh', 'th', …) or 'en' as a safe
    default.  Prefers the *langdetect* library when installed; otherwise
    falls back to Unicode-range heuristics.

    Never raises.
    """
    if not text or not text.strip():
        return "en"

    try:
        # Optional high-accuracy path
        from langdetect import detect, LangDetectException  # type: ignore
        try:
            result = detect(text[:2000])  # cap length for performance
            return result
        except LangDetectException:
            pass
    except ImportError:
        pass

    # Heuristic: count non-Latin script characters
    ratio = _non_latin_ratio(text)
    if ratio < 0.15:
        return "en"   # ≥ 85 % Latin → English (or a Latin-script language)

    lang = _dominant_non_latin_lang(text)
    return lang if lang else "en"


def is_english(text: str) -> bool:
    """
    Return True when *text* is predominantly English / Latin-script.
    Accepts accented Latin characters (French, German, Spanish, etc.)
    as English-compatible because edge-tts handles them fine.
    Never raises.
    """
    if not text or not text.strip():
        return True
    try:
        return _non_latin_ratio(text) < 0.20   # allow up to 20 % non-Latin
    except Exception:
        return True


def extract_english(text: str) -> str:
    """
    Extract only English / Latin-script content from *text*.

    Strategy (applied in order):
    1. If text is already English → return unchanged.
    2. Sentence-level: keep sentences where non-Latin ratio < 20 %.
    3. Word-level: keep whitespace tokens where ≥ 80 % of alpha chars are Latin.
    4. Character-level fallback: strip non-ASCII characters.

    Returns "" if nothing English-like is found.
    Never raises.
    """
    if not text or not text.strip():
        return ""

    try:
        if is_english(text):
            return text

        # ── 1. Sentence pass ──────────────────────────────────────────────────
        sentences = re.split(r'(?<=[.!?…])\s+', text.strip())
        english_sentences = [
            s.strip() for s in sentences
            if s.strip() and is_english(s)
        ]
        if english_sentences:
            return " ".join(english_sentences)

        # ── 2. Word pass ──────────────────────────────────────────────────────
        english_tokens: list[str] = []
        for token in text.split():
            alpha = [c for c in token if c.isalpha()]
            if not alpha:
                english_tokens.append(token)   # keep numbers / punctuation
                continue
            latin = [c for c in alpha if _char_script(c) is None]
            if len(latin) / len(alpha) >= 0.80:
                english_tokens.append(token)
        if english_tokens:
            return " ".join(english_tokens).strip()

        # ── 3. Character-level fallback ───────────────────────────────────────
        safe = re.sub(r'[^\x00-\x7F]+', ' ', text)
        return re.sub(r'\s{2,}', ' ', safe).strip()

    except Exception:
        # Absolute last resort: strip everything non-ASCII
        try:
            return re.sub(r'[^\x00-\x7F]+', ' ', text).strip()
        except Exception:
            return ""


def filter_for_tts(
    text: str,
    target_lang: str = "en",
) -> tuple[str, bool, str]:
    """
    Prepare *text* for TTS in *target_lang*.

    Returns
    -------
    filtered_text : str
        Safe text ready for TTS.  Empty string if nothing suitable found.
    was_filtered : bool
        True when non-target content was removed.
    detected_lang : str
        The detected dominant language of the original text.

    Never raises.
    """
    if not text or not text.strip():
        return "", False, "en"

    try:
        detected = detect_language(text)

        if target_lang == "en":
            if is_english(text):
                return text, False, detected

            filtered = extract_english(text)
            return filtered, True, detected

        # ── Future: per-language backends ─────────────────────────────────────
        # elif target_lang == "zh":
        #     from core.language.backends.zh import filter_chinese
        #     return filter_chinese(text), False, detected
        else:
            # Language not yet supported — return English portion as fallback
            filtered = extract_english(text)
            return filtered, True, detected

    except Exception:
        # Crash-proof last resort
        try:
            safe = re.sub(r'[^\x00-\x7F]+', ' ', text).strip()
            return safe, True, "unknown"
        except Exception:
            return "", True, "unknown"


def language_display_name(iso_code: str) -> str:
    """Human-readable name for an ISO 639-1 code. Never raises."""
    try:
        return VOICE_CATALOGUE.get(iso_code, {}).get("name", iso_code.upper())
    except Exception:
        return iso_code

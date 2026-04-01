"""
i18n — internationalisation helpers.

Usage
-----
    from i18n import t
    print(t("app.ready"))        # → "Veaja is ready"
    print(t("app.ready", "th")) # → "Veaja พร้อมแล้ว"  (when th/strings.json exists)

Adding a new language
---------------------
1. Create  i18n/<iso_code>/strings.json
2. Copy en/strings.json as a template
3. Translate each value (keep the keys identical)
4. The language is automatically available via t(key, lang)
"""

import json
import os

_CACHE: dict[str, dict[str, str]] = {}

_HERE = os.path.dirname(__file__)


def _load(lang: str) -> dict[str, str]:
    if lang not in _CACHE:
        path = os.path.join(_HERE, lang, "strings.json")
        try:
            with open(path, encoding="utf-8") as f:
                _CACHE[lang] = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            _CACHE[lang] = {}
    return _CACHE[lang]


def t(key: str, lang: str = "en") -> str:
    """
    Translate *key* into *lang*.
    Falls back to English, then to the bare key if nothing found.
    Never raises.
    """
    try:
        strings = _load(lang)
        if key in strings:
            return strings[key]
        # Fall back to English
        en = _load("en")
        return en.get(key, key)
    except Exception:
        return key

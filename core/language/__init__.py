# """
# core.language — language detection, text filtering, and voice catalogue.

# Public API
# ----------
# from core.language import filter_for_tts, detect_language, is_english
# """

# from core.language.detector import (
#     detect_language, is_english, filter_for_tts, language_display_name
# )

# __all__ = ["detect_language", "is_english", "filter_for_tts", "language_display_name"]
"""
core.language — language detection, text filtering, and voice catalogue.

Public API
----------
from core.language import filter_for_tts, detect_language, is_english, is_french
"""

from core.language.detector import (
    detect_language, is_english, is_french, filter_for_tts, language_display_name
)

__all__ = ["detect_language", "is_english", "is_french", "filter_for_tts", "language_display_name"]
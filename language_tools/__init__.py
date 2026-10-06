"""Language detection and offline subtitle language helpers."""

from .core import LanguageInfo, detect_cues_language, detect_language, translate_cues

__all__ = ["LanguageInfo", "detect_language", "detect_cues_language", "translate_cues"]

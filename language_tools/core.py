from __future__ import annotations

import re
from dataclasses import dataclass

from common.zhconv import convert_chinese_text


@dataclass(frozen=True)
class LanguageInfo:
    code: str
    label: str
    confidence: float


LANGUAGE_LABELS = {
    "zh-Hans": "中文（简体）",
    "zh-Hant": "中文（繁体）",
    "ja": "日语",
    "ko": "韩语",
    "en": "英语/拉丁字母",
    "ru": "俄语/西里尔字母",
    "unknown": "未知语言",
}

SINGLE_SOURCE_MODE_LABELS = {
    "auto_chinese": "检测中文后自动生成简繁双语",
    "none": "缺少第二轨时仅保留原文",
    "s2t": "强制简体 -> 繁体",
    "t2s": "强制繁体 -> 简体",
}

_TRADITIONAL_MARKERS = set("體臺灣與為國後會個們這裏裡來說對時間門開關無從學電腦圖檔壓縮轉換簡繁寫讀顯異錯誤處啟動選擇輸出號軌跡質清晰內封樣式聲音")


def _visible_text(text: str) -> str:
    text = re.sub(r"\{[^}]*\}", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.replace(r"\N", " ").replace(r"\n", " ")


def detect_language(text: str) -> LanguageInfo:
    visible = _visible_text(text)
    if not visible.strip():
        return LanguageInfo("unknown", LANGUAGE_LABELS["unknown"], 0.0)

    total = max(1, len(re.findall(r"[^\W_]", visible, re.UNICODE)))
    hangul = len(re.findall(r"[\uac00-\ud7af]", visible))
    kana = len(re.findall(r"[\u3040-\u30ff]", visible))
    cjk = len(re.findall(r"[\u3400-\u9fff]", visible))
    cyrillic = len(re.findall(r"[\u0400-\u04ff]", visible))
    latin = len(re.findall(r"[A-Za-z]", visible))

    if hangul / total >= 0.12:
        code = "ko"
        score = min(0.99, 0.65 + hangul / total)
    elif kana / total >= 0.03:
        code = "ja"
        score = min(0.99, 0.65 + kana / total)
    elif cjk / total >= 0.12:
        traditional = sum(visible.count(char) for char in _TRADITIONAL_MARKERS)
        code = "zh-Hant" if traditional / max(1, cjk) >= 0.04 else "zh-Hans"
        score = min(0.98, 0.70 + cjk / total * 0.25)
    elif cyrillic / total >= 0.12:
        code = "ru"
        score = min(0.98, 0.65 + cyrillic / total)
    elif latin / total >= 0.35:
        code = "en"
        score = min(0.90, 0.55 + latin / total * 0.35)
    else:
        code = "unknown"
        score = 0.25
    return LanguageInfo(code, LANGUAGE_LABELS[code], round(score, 3))


def detect_cues_language(cues: list[tuple[str, str, str]]) -> LanguageInfo:
    return detect_language("\n".join(cue[2] for cue in cues))


def automatic_chinese_mode(language: LanguageInfo) -> str | None:
    if language.code == "zh-Hans":
        return "s2t"
    if language.code == "zh-Hant":
        return "t2s"
    return None


def single_source_mode_from_label(value: str) -> str:
    value = (value or "").strip()
    if value in SINGLE_SOURCE_MODE_LABELS:
        return value
    for key, label in SINGLE_SOURCE_MODE_LABELS.items():
        if value == label:
            return key
    return "auto_chinese"


def translate_cues(
    cues: list[tuple[str, str, str]],
    mode_key: str,
) -> list[tuple[str, str, str]]:
    """Translate cue text with the bundled OpenCC engine, preserving timing."""
    return [(start, end, convert_chinese_text(text, mode_key)) for start, end, text in cues]

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .text_utils import safe_stem, unique_path


@dataclass(frozen=True)
class ConversionMode:
    key: str
    label: str
    suffix: str
    opencc_config: str | None = None


MODES = [
    ConversionMode("none", "不转换", "same", None),
    ConversionMode("t2s", "繁体 -> 简体", "t2s", "t2s"),
    ConversionMode("s2t", "简体 -> 繁体", "s2t", "s2t"),
    ConversionMode("tw2s", "台湾繁体 -> 简体", "tw2s", "tw2s"),
    ConversionMode("s2tw", "简体 -> 台湾繁体", "s2tw", "s2tw"),
    ConversionMode("hk2s", "香港繁体 -> 简体", "hk2s", "hk2s"),
    ConversionMode("s2hk", "简体 -> 香港繁体", "s2hk", "s2hk"),
]
MODE_BY_KEY = {mode.key: mode for mode in MODES}
LABEL_BY_KEY = {mode.key: mode.label for mode in MODES}
KEY_BY_LABEL = {mode.label: mode.key for mode in MODES}

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".xml",
    ".html",
    ".htm",
    ".xhtml",
    ".srt",
    ".ass",
    ".ssa",
    ".vtt",
    ".skrt",
}

_SIMPLE_T2S = str.maketrans(
    {
        "體": "体",
        "臺": "台",
        "台": "台",
        "灣": "湾",
        "與": "与",
        "為": "为",
        "國": "国",
        "後": "后",
        "會": "会",
        "個": "个",
        "們": "们",
        "這": "这",
        "裏": "里",
        "裡": "里",
        "來": "来",
        "說": "说",
        "對": "对",
        "時": "时",
        "間": "间",
        "門": "门",
        "開": "开",
        "關": "关",
        "無": "无",
        "從": "从",
        "學": "学",
        "電": "电",
        "腦": "脑",
        "圖": "图",
        "檔": "档",
        "壓": "压",
        "縮": "缩",
        "轉": "转",
        "換": "换",
        "簡": "简",
        "繁": "繁",
        "寫": "写",
        "讀": "读",
        "顯": "显",
        "異": "异",
        "錯": "错",
        "誤": "误",
        "處": "处",
        "理": "理",
        "啟": "启",
        "動": "动",
        "選": "选",
        "擇": "择",
        "輸": "输",
        "入": "入",
        "出": "出",
        "號": "号",
        "軌": "轨",
        "跡": "迹",
        "質": "质",
        "清": "清",
        "晰": "晰",
        "內": "内",
        "封": "封",
        "樣": "样",
        "式": "式",
        "顔": "颜",
        "色": "色",
        "顏": "颜",
        "聲": "声",
        "嗎": "吗",
        "嗎": "吗",
        "點": "点",
        "頁": "页",
        "標": "标",
        "題": "题",
        "證": "证",
    }
)

_SIMPLE_S2T = str.maketrans({value: key for key, value in _SIMPLE_T2S.items() if value != key})


def mode_key_from_label(value: str) -> str:
    value = (value or "none").strip()
    if value in MODE_BY_KEY:
        return value
    return KEY_BY_LABEL.get(value, "none")


def mode_label(mode_key: str) -> str:
    return LABEL_BY_KEY.get(mode_key_from_label(mode_key), "不转换")


def mode_suffix(mode_key: str) -> str:
    return MODE_BY_KEY.get(mode_key_from_label(mode_key), MODE_BY_KEY["none"]).suffix


@lru_cache(maxsize=8)
def _opencc_converter(config: str):
    from opencc import OpenCC

    return OpenCC(config)


def convert_chinese_text(text: str, mode_key: str) -> str:
    mode = MODE_BY_KEY.get(mode_key_from_label(mode_key), MODE_BY_KEY["none"])
    if mode.key == "none" or not text:
        return text
    if mode.opencc_config:
        try:
            return _opencc_converter(mode.opencc_config).convert(text)
        except Exception:
            pass
    if mode.key in {"t2s", "tw2s", "hk2s"}:
        return text.translate(_SIMPLE_T2S)
    if mode.key in {"s2t", "s2tw", "s2hk"}:
        return text.translate(_SIMPLE_S2T)
    return text


def read_text_auto(path: str | Path) -> str:
    source = Path(path)
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "big5", "cp950"):
        try:
            return source.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return source.read_text(encoding="utf-8", errors="replace")


def output_suffix(source: Path, output_format: str) -> str:
    fmt = (output_format or "same").strip().casefold().lstrip(".")
    if fmt in {"same", "", "原格式"}:
        return source.suffix or ".txt"
    suffix = "." + fmt
    if suffix in TEXT_EXTENSIONS:
        return suffix
    return source.suffix or ".txt"


def convert_text_file(
    source: str | Path,
    output_dir: str | Path | None,
    mode_key: str,
    output_format: str = "same",
) -> Path:
    source_path = Path(source)
    if source_path.suffix.casefold() not in TEXT_EXTENSIONS:
        raise ValueError(f"不支持的文本格式: {source_path.suffix or source_path.name}")
    out_root = Path(output_dir) if output_dir else source_path.parent / "繁简转换输出"
    out_root.mkdir(parents=True, exist_ok=True)
    suffix = output_suffix(source_path, output_format)
    tag = mode_suffix(mode_key)
    name = safe_stem(source_path.stem)
    output = unique_path(out_root / f"{name}_{tag}{suffix}")
    converted = convert_chinese_text(read_text_auto(source_path), mode_key)
    output.write_text(converted, encoding="utf-8", newline="")
    return output


def convert_text_files(
    sources: list[str | Path],
    output_dir: str | Path | None,
    mode_key: str,
    output_format: str = "same",
    log=None,
) -> list[Path]:
    outputs: list[Path] = []
    for index, source in enumerate(sources, 1):
        source_path = Path(source)
        try:
            if log:
                log(f"[{index}/{len(sources)}] 转换: {source_path.name} -> {mode_label(mode_key)}")
            output = convert_text_file(source_path, output_dir, mode_key, output_format)
            outputs.append(output)
            if log:
                log(f"已输出: {output}")
        except Exception as exc:
            if log:
                log(f"失败: {source_path} - {exc}")
    return outputs

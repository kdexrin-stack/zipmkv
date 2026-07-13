from __future__ import annotations

import re
import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from common.log import Logger, emit
from common.media_tools import find_ffmpeg, find_ffprobe, probe_subtitle_streams, run_hidden
from common.text_utils import safe_stem, unique_path
from common.zhconv import convert_chinese_text


SUBTITLE_EXTENSIONS = {".ass", ".ssa", ".srt", ".vtt", ".skrt"}
VIDEO_EXTENSIONS = {".mkv", ".mp4", ".mov", ".avi", ".wmv", ".flv", ".webm", ".m4v"}

DEFAULT_ASS_FORMAT = [
    "Name",
    "Fontname",
    "Fontsize",
    "PrimaryColour",
    "SecondaryColour",
    "OutlineColour",
    "BackColour",
    "Bold",
    "Italic",
    "Underline",
    "StrikeOut",
    "ScaleX",
    "ScaleY",
    "Spacing",
    "Angle",
    "BorderStyle",
    "Outline",
    "Shadow",
    "Alignment",
    "MarginL",
    "MarginR",
    "MarginV",
    "Encoding",
]

DEFAULT_ASS_STYLE = {
    "Name": "Default",
    "Fontname": "Microsoft YaHei",
    "Fontsize": "48",
    "PrimaryColour": "&H00FFFFFF",
    "SecondaryColour": "&H000000FF",
    "OutlineColour": "&H00000000",
    "BackColour": "&H64000000",
    "Bold": "0",
    "Italic": "0",
    "Underline": "0",
    "StrikeOut": "0",
    "ScaleX": "100",
    "ScaleY": "100",
    "Spacing": "0",
    "Angle": "0",
    "BorderStyle": "1",
    "Outline": "2",
    "Shadow": "0",
    "Alignment": "2",
    "MarginL": "30",
    "MarginR": "30",
    "MarginV": "36",
    "Encoding": "1",
}

SCRIPT_INFO_STYLE_KEYS = [
    "WrapStyle",
    "ScaledBorderAndShadow",
    "YCbCr Matrix",
    "PlayResX",
    "PlayResY",
    "Collisions",
]
SCRIPT_INFO_STYLE_KEY_MAP = {key.casefold(): key for key in SCRIPT_INFO_STYLE_KEYS}
STYLE_USAGE_MARKER = "; zipmkv-style-usage:"


@dataclass
class StyleOptions:
    font_name: str = ""
    font_size: str = ""
    primary_color: str = ""
    outline_color: str = ""
    alignment: str = ""
    margin_l: str = ""
    margin_r: str = ""
    margin_v: str = ""
    outline: str = ""
    shadow: str = ""
    bold: bool | None = None
    italic: bool | None = None
    use_sample: bool = False
    safe_single_language: bool = True
    remux_video: bool = False
    subtitle_stream: int = 0
    all_subtitle_streams: bool = True
    output_format: str = "same"
    text_conversion_mode: str = "none"


def is_subtitle(path: str | Path) -> bool:
    return Path(path).suffix.casefold() in SUBTITLE_EXTENSIONS


def is_video(path: str | Path) -> bool:
    return Path(path).suffix.casefold() in VIDEO_EXTENSIONS


def read_text(path: str | Path) -> str:
    source = Path(path)
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return source.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return source.read_text(encoding="utf-8", errors="replace")


def normalize_ass_color(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if re.fullmatch(r"&H[0-9A-Fa-f]{6,8}", value):
        hex_part = value[2:].upper()
        if len(hex_part) == 6:
            hex_part = "00" + hex_part
        return "&H" + hex_part
    match = re.fullmatch(r"#?([0-9A-Fa-f]{6})", value)
    if not match:
        return value
    rgb = match.group(1)
    rr, gg, bb = rgb[0:2], rgb[2:4], rgb[4:6]
    return f"&H00{bb}{gg}{rr}".upper()


def parse_ass_styles(text: str) -> tuple[list[str], list[dict[str, str]]]:
    in_styles = False
    fields = DEFAULT_ASS_FORMAT[:]
    styles: list[dict[str, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.casefold() == "[v4+ styles]" or line.casefold() == "[v4 styles]":
            in_styles = True
            continue
        if in_styles and line.startswith("[") and line.endswith("]"):
            break
        if not in_styles:
            continue
        if line.lower().startswith("format:"):
            fields = [part.strip() for part in line.split(":", 1)[1].split(",")]
        elif line.lower().startswith("style:"):
            values = [part.strip() for part in line.split(":", 1)[1].split(",", len(fields) - 1)]
            style = dict(zip(fields, values))
            styles.append(style)
    return fields, styles


def parse_script_info_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    in_script_info = False
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.casefold() == "[script info]":
            in_script_info = True
            continue
        if in_script_info and stripped.startswith("[") and stripped.endswith("]"):
            break
        if not in_script_info or ":" not in raw_line or stripped.startswith(";"):
            continue
        key, value = raw_line.split(":", 1)
        canonical = SCRIPT_INFO_STYLE_KEY_MAP.get(key.strip().casefold())
        if canonical and value.strip():
            values[canonical] = value.strip()
    return values


def apply_sample_script_info(text: str, sample_text: str | None) -> str:
    values = parse_script_info_values(sample_text or "")
    if not values:
        return text

    lines = text.splitlines()
    if not any(line.strip().casefold() == "[script info]" for line in lines):
        injected = ["[Script Info]", *[f"{key}: {value}" for key, value in values.items()], ""]
        return "\n".join(injected + lines).rstrip() + "\n"

    output: list[str] = []
    in_script_info = False
    seen: set[str] = set()
    inserted_missing = False

    def append_missing() -> None:
        nonlocal inserted_missing
        if inserted_missing:
            return
        for key, value in values.items():
            if key not in seen:
                output.append(f"{key}: {value}")
                seen.add(key)
        inserted_missing = True

    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.casefold() == "[script info]":
            in_script_info = True
            output.append(raw_line)
            continue
        if in_script_info and stripped.startswith("[") and stripped.endswith("]"):
            append_missing()
            in_script_info = False
            output.append(raw_line)
            continue
        if in_script_info and ":" in raw_line and not stripped.startswith(";"):
            key, _ = raw_line.split(":", 1)
            canonical = SCRIPT_INFO_STYLE_KEY_MAP.get(key.strip().casefold())
            if canonical and canonical in values:
                output.append(f"{canonical}: {values[canonical]}")
                seen.add(canonical)
                continue
        output.append(raw_line)

    if in_script_info:
        append_missing()
    return "\n".join(output).rstrip() + "\n"


def ass_style_usage_counts(text: str) -> dict[str, int]:
    marked: dict[str, int] = {}
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped.startswith(STYLE_USAGE_MARKER):
            continue
        payload = stripped[len(STYLE_USAGE_MARKER):].strip()
        try:
            item = json.loads(payload)
        except json.JSONDecodeError:
            continue
        name = str(item.get("style", ""))
        count = int(item.get("count", 0) or 0)
        if name and count > 0:
            marked[name] = marked.get(name, 0) + count
    if marked:
        return marked

    event_fields: list[str] = []
    in_events = False
    counts: dict[str, int] = {}
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.casefold() == "[events]":
            in_events = True
            continue
        if in_events and stripped.startswith("[") and stripped.endswith("]"):
            break
        if not in_events:
            continue
        if stripped.lower().startswith("format:"):
            event_fields = [part.strip() for part in stripped.split(":", 1)[1].split(",")]
            continue
        if stripped.lower().startswith("dialogue:") and event_fields:
            values = [part.strip() for part in raw_line.split(":", 1)[1].split(",", len(event_fields) - 1)]
            row = dict(zip(event_fields, values))
            name = row.get("Style", "")
            if name:
                counts[name] = counts.get(name, 0) + 1
    return counts


def dominant_sample_style(sample_styles: list[dict[str, str]], sample_text: str | None) -> tuple[dict[str, str] | None, bool]:
    if not sample_styles:
        return None, False
    counts = ass_style_usage_counts(sample_text or "")
    if not counts:
        return None, False

    ranked: list[tuple[int, int, dict[str, str]]] = []
    for index, style in enumerate(sample_styles):
        ranked.append((counts.get(style.get("Name", ""), 0), -index, style))
    ranked.sort(reverse=True, key=lambda item: (item[0], item[1]))
    top_count, _, style = ranked[0]
    if top_count <= 0:
        return None, False

    ordered_counts = sorted((count for count in counts.values() if count > 0), reverse=True)
    second_count = ordered_counts[1] if len(ordered_counts) > 1 else 0
    total = sum(ordered_counts)
    confident = second_count == 0 or top_count >= second_count * 2 or top_count >= total * 0.45
    return style, confident


def style_to_line(fields: list[str], style: dict[str, str]) -> str:
    return "Style: " + ",".join(style.get(field, "") for field in fields)


def manual_style_values(options: StyleOptions) -> dict[str, str]:
    values: dict[str, str] = {}
    mapping = {
        "font_name": "Fontname",
        "font_size": "Fontsize",
        "primary_color": "PrimaryColour",
        "outline_color": "OutlineColour",
        "alignment": "Alignment",
        "margin_l": "MarginL",
        "margin_r": "MarginR",
        "margin_v": "MarginV",
        "outline": "Outline",
        "shadow": "Shadow",
    }
    for attr, field in mapping.items():
        value = getattr(options, attr).strip()
        if value:
            if field.endswith("Colour"):
                value = normalize_ass_color(value)
            values[field] = value
    if options.bold is not None:
        values["Bold"] = "-1" if options.bold else "0"
    if options.italic is not None:
        values["Italic"] = "-1" if options.italic else "0"
    return values


def _sample_values_for_target(
    target_index: int,
    target_style: dict[str, str],
    target_count: int,
    sample_styles: list[dict[str, str]],
    sample_text: str | None,
    safe_single_language: bool,
) -> dict[str, str]:
    if not sample_styles:
        return {}
    by_name = {style.get("Name", "").casefold(): style for style in sample_styles}
    sample = None
    dominant_is_confident = False
    if target_count <= 1 and len(sample_styles) > 1:
        sample, dominant_is_confident = dominant_sample_style(sample_styles, sample_text)
    if sample is None:
        sample = by_name.get(target_style.get("Name", "").casefold())
    if sample is None:
        sample = sample_styles[min(target_index, len(sample_styles) - 1)]

    allowed = {
        "Fontname",
        "Fontsize",
        "PrimaryColour",
        "SecondaryColour",
        "OutlineColour",
        "BackColour",
        "Bold",
        "Italic",
        "Underline",
        "StrikeOut",
        "ScaleX",
        "ScaleY",
        "Spacing",
        "Angle",
        "BorderStyle",
        "Outline",
        "Shadow",
        "Alignment",
        "MarginL",
        "MarginR",
        "MarginV",
        "Encoding",
    }
    values = {field: value for field, value in sample.items() if field in allowed}
    if safe_single_language and len(sample_styles) > 1 and target_count <= 1 and not dominant_is_confident:
        for risky_field in ("Fontsize", "ScaleX", "ScaleY", "MarginV"):
            values.pop(risky_field, None)
    return values


def apply_styles_to_ass(text: str, options: StyleOptions, sample_text: str | None = None) -> str:
    target_fields, target_styles = parse_ass_styles(text)
    if not target_styles:
        text = build_ass_from_dialogues([], DEFAULT_ASS_STYLE, title="Converted")
        target_fields, target_styles = parse_ass_styles(text)

    _, sample_styles = parse_ass_styles(sample_text or "")
    manual_values = manual_style_values(options)
    style_index = -1
    in_styles = False
    lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line
        stripped = raw_line.strip()
        if stripped.casefold() == "[v4+ styles]" or stripped.casefold() == "[v4 styles]":
            in_styles = True
            lines.append(raw_line)
            continue
        if in_styles and stripped.startswith("[") and stripped.endswith("]"):
            in_styles = False
            lines.append(raw_line)
            continue
        if in_styles and stripped.lower().startswith("style:"):
            style_index += 1
            style = target_styles[style_index].copy()
            if options.use_sample:
                style.update(
                    _sample_values_for_target(
                        style_index,
                        target_styles[style_index],
                        len(target_styles),
                        sample_styles,
                        sample_text,
                        options.safe_single_language,
                    )
                )
            style.update(manual_values)
            line = style_to_line(target_fields, style)
        lines.append(line)
    result = "\n".join(lines).rstrip() + "\n"
    if options.use_sample and sample_text:
        result = apply_sample_script_info(result, sample_text)
    return result


def merge_sample_texts(sample_texts: list[str | None]) -> str | None:
    parts = [text for text in sample_texts if text]
    if not parts:
        return None

    merged_styles: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    usage_totals: dict[str, int] = {}
    script_info_values: dict[str, str] = {}
    for sample_index, text in enumerate(parts):
        if not script_info_values:
            script_info_values = parse_script_info_values(text)
        usage_counts = ass_style_usage_counts(text)
        for style_name, count in usage_counts.items():
            usage_totals[style_name] = usage_totals.get(style_name, 0) + count
        fields, styles = parse_ass_styles(text)
        for style_index, style in enumerate(styles):
            name = style.get("Name", f"Style{len(merged_styles)}")
            if name.casefold() in seen:
                continue
            seen.add(name.casefold())
            normalized = {**DEFAULT_ASS_STYLE, **style}
            merged_styles.append(
                (
                    usage_counts.get(name, 0),
                    -(sample_index * 10000 + style_index),
                    style_to_line(DEFAULT_ASS_FORMAT, normalized),
                )
            )

    if not merged_styles:
        return parts[0]

    merged_styles.sort(reverse=True, key=lambda item: (item[0], item[1]))
    script_lines = [
        "[Script Info]",
        "Title: merged samples",
        "ScriptType: v4.00+",
    ]
    for key, value in script_info_values.items():
        script_lines.append(f"{key}: {value}")
    for style_name, count in usage_totals.items():
        if count > 0:
            payload = json.dumps({"style": style_name, "count": count}, ensure_ascii=False)
            script_lines.append(f"{STYLE_USAGE_MARKER} {payload}")

    return "\n".join(
        [
            *script_lines,
            "",
            "[V4+ Styles]",
            "Format: " + ",".join(DEFAULT_ASS_FORMAT),
            *[line for _, _, line in merged_styles],
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
            "",
        ]
    )


def parse_srt_like(text: str) -> list[tuple[str, str, str]]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    cues: list[tuple[str, str, str]] = []
    blocks = re.split(r"\n{2,}", text.strip())
    for block in blocks:
        lines = [line.strip("\ufeff") for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if re.fullmatch(r"\d+", lines[0]):
            lines = lines[1:]
        if not lines or "-->" not in lines[0]:
            continue
        start, end = [part.strip().split()[0] for part in lines[0].split("-->", 1)]
        body = r"\N".join(lines[1:])
        body = re.sub(r"<[^>]+>", "", body)
        cues.append((normalize_time(start), normalize_time(end), body))
    return cues


def normalize_time(value: str) -> str:
    value = value.replace(",", ".")
    parts = value.split(":")
    if len(parts) == 3:
        h, m, s = parts
    elif len(parts) == 2:
        h, m, s = "0", parts[0], parts[1]
    else:
        return "0:00:00.00"
    seconds = float(s)
    return f"{int(h)}:{int(m):02d}:{seconds:05.2f}"


def build_ass_from_dialogues(cues: list[tuple[str, str, str]], style: dict[str, str], title: str) -> str:
    style_line = style_to_line(DEFAULT_ASS_FORMAT, style)
    event_format = "Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    dialogues = [
        f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}"
        for start, end, text in cues
    ]
    return "\n".join(
        [
            "[Script Info]",
            f"Title: {title}",
            "ScriptType: v4.00+",
            "WrapStyle: 0",
            "ScaledBorderAndShadow: yes",
            "PlayResX: 1920",
            "PlayResY: 1080",
            "YCbCr Matrix: TV.709",
            "",
            "[V4+ Styles]",
            "Format: " + ",".join(DEFAULT_ASS_FORMAT),
            style_line,
            "",
            "[Events]",
            "Format: " + event_format,
            *dialogues,
            "",
        ]
    )


def ass_time_to_srt(value: str) -> str:
    match = re.fullmatch(r"(?P<h>\d+):(?P<m>\d{2}):(?P<s>\d{2})(?:\.(?P<cs>\d{1,2}))?", value.strip())
    if not match:
        return "00:00:00,000"
    h = int(match.group("h"))
    m = int(match.group("m"))
    s = int(match.group("s"))
    cs = match.group("cs") or "0"
    ms = int(cs.ljust(2, "0")) * 10
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_ass_dialogues(text: str) -> list[tuple[str, str, str]]:
    event_fields: list[str] = []
    in_events = False
    cues: list[tuple[str, str, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.casefold() == "[events]":
            in_events = True
            continue
        if in_events and line.startswith("[") and line.endswith("]"):
            break
        if not in_events:
            continue
        if line.lower().startswith("format:"):
            event_fields = [part.strip() for part in line.split(":", 1)[1].split(",")]
            continue
        if line.lower().startswith("dialogue:") and event_fields:
            values = [part.strip() for part in line.split(":", 1)[1].split(",", len(event_fields) - 1)]
            row = dict(zip(event_fields, values))
            text_value = re.sub(r"\{[^}]*\}", "", row.get("Text", ""))
            text_value = text_value.replace(r"\N", "\n").replace(r"\n", "\n")
            cues.append((row.get("Start", "0:00:00.00"), row.get("End", "0:00:00.00"), text_value))
    return cues


def convert_ass_dialogue_texts(text: str, mode_key: str) -> str:
    if not mode_key or mode_key == "none":
        return text
    event_fields: list[str] = []
    text_index = -1
    in_events = False
    output: list[str] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.casefold() == "[events]":
            in_events = True
            output.append(raw_line)
            continue
        if in_events and stripped.startswith("[") and stripped.endswith("]"):
            in_events = False
            output.append(raw_line)
            continue
        if in_events and stripped.lower().startswith("format:"):
            event_fields = [part.strip() for part in stripped.split(":", 1)[1].split(",")]
            lowered = [field.casefold() for field in event_fields]
            text_index = lowered.index("text") if "text" in lowered else -1
            output.append(raw_line)
            continue
        if in_events and stripped.lower().startswith("dialogue:") and event_fields and text_index >= 0:
            prefix, payload = raw_line.split(":", 1)
            values = [part.strip() for part in payload.split(",", len(event_fields) - 1)]
            if len(values) > text_index:
                values[text_index] = convert_chinese_text(values[text_index], mode_key)
                output.append(f"{prefix}: " + ",".join(values))
                continue
        output.append(raw_line)
    return "\n".join(output).rstrip() + "\n"


def ass_to_srt(text: str) -> str:
    cues = parse_ass_dialogues(text)
    blocks = []
    for index, (start, end, body) in enumerate(cues, 1):
        blocks.append(f"{index}\n{ass_time_to_srt(start)} --> {ass_time_to_srt(end)}\n{body}")
    return "\n\n".join(blocks).rstrip() + "\n"


def ass_to_vtt(text: str) -> str:
    srt = ass_to_srt(text)
    return "WEBVTT\n\n" + srt.replace(",", ".")


def target_output_suffix(target: Path, output_format: str) -> str:
    fmt = output_format.casefold().strip()
    if fmt in {"same", "", "原格式"}:
        suffix = target.suffix.casefold()
        if suffix in {".ass", ".ssa", ".srt", ".vtt"}:
            return suffix
        return ".ass"
    if not fmt.startswith("."):
        fmt = "." + fmt
    if fmt in {".ass", ".ssa", ".srt", ".vtt"}:
        return fmt
    return ".ass"


def render_output_text(ass_text: str, suffix: str) -> str:
    suffix = suffix.casefold()
    if suffix == ".srt":
        return ass_to_srt(ass_text)
    if suffix == ".vtt":
        return ass_to_vtt(ass_text)
    return ass_text


def subtitle_text_to_ass(path: str | Path, options: StyleOptions) -> str:
    source = Path(path)
    text = read_text(source)
    if source.suffix.casefold() in {".ass", ".ssa"}:
        return apply_styles_to_ass(text, options)
    cues = parse_srt_like(text)
    style = DEFAULT_ASS_STYLE.copy()
    style.update(manual_style_values(options))
    return build_ass_from_dialogues(cues, style, title=source.stem)


def load_sample_text(sample_path: str | Path | None, stream_index: int = 0, log: Logger | None = None) -> str | None:
    if not sample_path:
        return None
    sample = Path(sample_path)
    if is_subtitle(sample):
        text = read_text(sample)
        if sample.suffix.casefold() in {".ass", ".ssa"}:
            return text
        return subtitle_text_to_ass(sample, StyleOptions())
    if is_video(sample):
        temp_dir = Path(tempfile.mkdtemp(prefix="zipmkv_sample_sub_"))
        try:
            extracted = extract_subtitle_from_video(sample, temp_dir, stream_index=stream_index, log=log)
            return read_text(extracted)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    return None


def load_sample_texts(sample_path: str | Path | None, log: Logger | None = None) -> list[str]:
    if not sample_path:
        return []
    sample = Path(sample_path)
    if is_subtitle(sample):
        text = read_text(sample)
        if sample.suffix.casefold() in {".ass", ".ssa"}:
            return [text]
        return [subtitle_text_to_ass(sample, StyleOptions())]
    if is_video(sample):
        temp_dir = Path(tempfile.mkdtemp(prefix="zipmkv_sample_sub_"))
        try:
            extracted = extract_all_subtitles_from_video(sample, temp_dir, log=log)
            return [read_text(path) for path in extracted]
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    return []


def load_sample_style_texts(sample_path: str | Path | None, log: Logger | None = None) -> list[str]:
    if not sample_path:
        return []
    sample = Path(sample_path)
    suffix = sample.suffix.casefold()
    if suffix in {".ass", ".ssa"}:
        return [read_text(sample)]
    if is_subtitle(sample):
        emit(log, f"示例 {sample.name} 是 {suffix}，没有字体/颜色/描边样式；将转换为默认 ASS 样式参与处理。")
        return [subtitle_text_to_ass(sample, StyleOptions())]
    if is_video(sample):
        streams = probe_subtitle_streams(sample)
        if not streams:
            emit(log, f"示例视频没有内封字幕轨道: {sample.name}")
            return []
        temp_dir = Path(tempfile.mkdtemp(prefix="zipmkv_sample_style_"))
        try:
            result: list[str] = []
            for order, stream in enumerate(streams):
                codec = str(stream.get("codec_name", "")).casefold()
                if not any(token in codec for token in ("ass", "ssa", "substation")):
                    emit(log, f"示例视频字幕轨 {order} 是 {stream.get('codec_name', '')}；将转换为默认 ASS 样式参与处理。")
                extracted = extract_subtitle_from_video(sample, temp_dir, stream_index=order, log=log)
                if extracted.suffix.casefold() in {".ass", ".ssa"}:
                    result.append(read_text(extracted))
                else:
                    result.append(subtitle_text_to_ass(extracted, StyleOptions()))
            return result
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    return []


def subtitle_extract_suffix(stream: dict) -> str:
    codec = str(stream.get("codec_name", "")).casefold()
    if any(token in codec for token in ("subrip", "srt", "mov_text", "text")):
        return ".srt"
    if "webvtt" in codec or "vtt" in codec:
        return ".vtt"
    return ".ass"


def extract_subtitle_from_video(
    video_path: str | Path,
    output_dir: str | Path,
    stream_index: int = 0,
    log: Logger | None = None,
) -> Path:
    ffmpeg = find_ffmpeg()
    ffprobe = find_ffprobe()
    if not ffmpeg:
        raise RuntimeError("未找到 ffmpeg，无法读取视频内封字幕。")
    streams = probe_subtitle_streams(video_path, ffprobe)
    if not streams:
        raise RuntimeError("视频中没有检测到内封字幕轨道。")
    if stream_index < 0 or stream_index >= len(streams):
        raise RuntimeError(f"字幕轨道序号超出范围，可用轨道数: {len(streams)}")

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    stream = streams[stream_index]
    suffix = subtitle_extract_suffix(stream)
    output = output_root / f"{safe_stem(Path(video_path).stem)}_subtitle_{stream_index}{suffix}"
    emit(log, f"提取视频字幕轨道 {stream_index}: {Path(video_path).name} -> 临时 {suffix}")
    result = run_hidden([
        str(ffmpeg),
        "-y",
        "-i",
        str(video_path),
        "-map",
        f"0:s:{stream_index}",
        str(output),
    ])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "提取视频字幕失败")
    return output


def extract_all_subtitles_from_video(
    video_path: str | Path,
    output_dir: str | Path,
    log: Logger | None = None,
) -> list[Path]:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("未找到 ffmpeg，无法读取视频内封字幕。")
    streams = probe_subtitle_streams(video_path)
    if not streams:
        raise RuntimeError("视频中没有检测到内封字幕轨道。")
    extracted: list[Path] = []
    for stream_index in range(len(streams)):
        extracted.append(extract_subtitle_from_video(video_path, output_dir, stream_index=stream_index, log=log))
    return extracted


def remux_video_with_subtitles(
    video_path: str | Path,
    subtitle_paths: list[str | Path],
    output_path: str | Path,
    replace_existing_subtitles: bool = False,
    log: Logger | None = None,
) -> Path:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("未找到 ffmpeg，无法重新封装视频。")
    subtitles = [Path(path) for path in subtitle_paths if Path(path).is_file() and is_subtitle(path)]
    if not subtitles:
        raise RuntimeError("没有可封装进视频的字幕文件。")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    command = [
        str(ffmpeg),
        "-y",
        "-i",
        str(video_path),
    ]
    for subtitle in subtitles:
        command.extend(["-i", str(subtitle)])
    command.extend(["-map", "0"])
    if replace_existing_subtitles:
        command.extend(["-map", "-0:s"])
    for input_index in range(1, len(subtitles) + 1):
        command.extend(["-map", f"{input_index}:0"])
    command.extend(["-c", "copy", str(output)])

    emit(
        log,
        f"封装 MKV: {Path(video_path).name} + {len(subtitles)} 个字幕轨"
        + ("（替换原字幕轨）" if replace_existing_subtitles else "（保留原字幕轨并追加）"),
    )
    result = run_hidden(command)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "重新封装视频失败")
    return output


def remux_video_with_subtitle(video_path: str | Path, subtitle_path: str | Path, output_path: str | Path) -> Path:
    return remux_video_with_subtitles(
        video_path,
        [subtitle_path],
        output_path,
        replace_existing_subtitles=True,
    )


def remove_subtitle_tracks_from_video(
    video_path: str | Path,
    output_path: str | Path,
    all_subtitle_streams: bool = True,
    subtitle_stream: int = 0,
    log: Logger | None = None,
) -> Path:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("未找到 ffmpeg，无法删除视频内封字幕轨。")
    video = Path(video_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(ffmpeg),
        "-y",
        "-i",
        str(video),
        "-map",
        "0",
        "-map",
        "-0:s?" if all_subtitle_streams else f"-0:s:{subtitle_stream}?",
        "-c",
        "copy",
        str(output),
    ]
    emit(log, f"删除字幕轨: {video.name} -> {'全部字幕轨' if all_subtitle_streams else f'字幕轨 {subtitle_stream}'}")
    result = run_hidden(command)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "删除视频字幕轨失败")
    return output


def remove_subtitle_tracks_from_videos(
    video_paths: list[str | Path],
    output_dir: str | Path | None,
    all_subtitle_streams: bool = True,
    subtitle_stream: int = 0,
    log: Logger | None = None,
) -> list[Path]:
    videos = [Path(path) for path in video_paths if is_video(path) and Path(path).is_file()]
    if not videos:
        raise RuntimeError("请先选择要删除字幕轨的视频。")
    out_root = Path(output_dir) if output_dir else videos[0].parent / "字幕删除输出"
    out_root.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for video in videos:
        output = unique_path(out_root / f"{safe_stem(video.stem)}_删除字幕.mkv")
        outputs.append(
            remove_subtitle_tracks_from_video(
                video,
                output,
                all_subtitle_streams=all_subtitle_streams,
                subtitle_stream=subtitle_stream,
                log=log,
            )
        )
        emit(log, f"已输出删除字幕视频: {outputs[-1]}")
    return outputs


def mux_subtitles_into_videos(
    subtitle_paths: list[str | Path],
    video_paths: list[str | Path],
    output_dir: str | Path | None,
    replace_existing_subtitles: bool = False,
    log: Logger | None = None,
) -> list[Path]:
    subtitles = [Path(path) for path in subtitle_paths if is_subtitle(path) and Path(path).is_file()]
    videos = [Path(path) for path in video_paths if is_video(path) and Path(path).is_file()]
    if not subtitles:
        raise RuntimeError("没有可封装的视频字幕输出。")
    if not videos:
        raise RuntimeError("请先选择要封装字幕的目标视频。")

    out_root = Path(output_dir) if output_dir else videos[0].parent / "字幕封装输出"
    out_root.mkdir(parents=True, exist_ok=True)
    jobs: list[tuple[Path, list[Path]]] = []
    if len(videos) == 1:
        jobs.append((videos[0], subtitles))
    elif len(subtitles) == 1:
        jobs.extend((video, [subtitles[0]]) for video in videos)
    else:
        limit = min(len(videos), len(subtitles))
        if len(videos) != len(subtitles):
            emit(log, f"视频 {len(videos)} 个、字幕 {len(subtitles)} 个，按自然排序只处理前 {limit} 对。")
        jobs.extend((videos[index], [subtitles[index]]) for index in range(limit))

    outputs: list[Path] = []
    for video, job_subtitles in jobs:
        output = unique_path(out_root / f"{safe_stem(video.stem)}_封装字幕.mkv")
        outputs.append(
            remux_video_with_subtitles(
                video,
                job_subtitles,
                output,
                replace_existing_subtitles=replace_existing_subtitles,
                log=log,
            )
        )
        emit(log, f"已封装视频: {outputs[-1]}")
    return outputs


def modify_subtitle_or_video(
    target_path: str | Path,
    output_dir: str | Path | None,
    options: StyleOptions,
    sample_path: str | Path | None = None,
    log: Logger | None = None,
) -> list[Path]:
    target = Path(target_path)
    out_root = Path(output_dir) if output_dir else target.parent / "字幕样式输出"
    out_root.mkdir(parents=True, exist_ok=True)
    sample_text = None
    if options.use_sample:
        sample_text = merge_sample_texts(load_sample_style_texts(sample_path, log=log))
        if not sample_text:
            raise RuntimeError(
                "未读取到可用示例字幕。请使用单独字幕文件，或带内封字幕轨道的视频；硬字幕视频无法读取字幕。"
            )

    if is_video(target):
        with tempfile.TemporaryDirectory(prefix="zipmkv_extract_") as temp_name:
            temp_dir = Path(temp_name)
            extracted_files = (
                extract_all_subtitles_from_video(target, temp_dir, log=log)
                if options.all_subtitle_streams
                else [extract_subtitle_from_video(target, temp_dir, stream_index=options.subtitle_stream, log=log)]
            )
            return _write_video_subtitle_outputs(target, extracted_files, out_root, options, sample_text, log)

    if is_subtitle(target):
        if target.suffix.casefold() in {".ass", ".ssa"}:
            ass_text = apply_styles_to_ass(read_text(target), options, sample_text=sample_text)
        else:
            ass_text = subtitle_text_to_ass(target, options)
            if options.use_sample and sample_text:
                ass_text = apply_styles_to_ass(ass_text, options, sample_text=sample_text)
        ass_text = convert_ass_dialogue_texts(ass_text, options.text_conversion_mode)
        suffix = target_output_suffix(target, options.output_format)
        output = unique_path(out_root / f"{safe_stem(target.stem)}_modified{suffix}")
        output.write_text(render_output_text(ass_text, suffix), encoding="utf-8")
        emit(log, f"已输出字幕: {output}")
        return [output]

    raise ValueError("请选择字幕文件或视频文件。")


def _write_video_subtitle_outputs(
    target: Path,
    extracted_files: list[Path],
    out_root: Path,
    options: StyleOptions,
    sample_text: str | None,
    log: Logger | None = None,
) -> list[Path]:
    outputs = []
    suffix = target_output_suffix(target, options.output_format)
    multiple_tracks = len(extracted_files) > 1
    for index, extracted in enumerate(extracted_files):
        if extracted.suffix.casefold() in {".ass", ".ssa"}:
            source_ass = read_text(extracted)
        else:
            emit(log, f"读取内封 {extracted.suffix.upper().lstrip('.')} 文本并转换为 ASS: {extracted.name}")
            source_ass = subtitle_text_to_ass(extracted, options)
        ass_text = apply_styles_to_ass(source_ass, options, sample_text=sample_text)
        ass_text = convert_ass_dialogue_texts(ass_text, options.text_conversion_mode)
        track_part = f"_track{index}" if multiple_tracks else ""
        subtitle_output = unique_path(out_root / f"{safe_stem(target.stem)}{track_part}_modified{suffix}")
        subtitle_output.write_text(render_output_text(ass_text, suffix), encoding="utf-8")
        outputs.append(subtitle_output)
        emit(log, f"已输出字幕: {subtitle_output}")
    if options.remux_video:
        video_output = unique_path(out_root / f"{safe_stem(target.stem)}_modified.mkv")
        remux_video_with_subtitles(target, outputs, video_output, replace_existing_subtitles=True, log=log)
        outputs.append(video_output)
        emit(log, f"已重新封装视频: {video_output}")
    return outputs


def modify_many(
    target_paths: list[str | Path],
    output_dir: str | Path | None,
    options: StyleOptions,
    sample_paths: list[str | Path] | None = None,
    log: Logger | None = None,
) -> list[Path]:
    sample_text: str | None = None
    sample_loaded = False

    def get_sample_text() -> str | None:
        nonlocal sample_loaded, sample_text
        if sample_loaded or not options.use_sample:
            return sample_text
        sample_loaded = True
        sample_texts: list[str | None] = []
        for path in (sample_paths or []):
            try:
                emit(log, f"读取示例样式: {Path(path).name}")
                sample_texts.extend(load_sample_style_texts(path, log=log))
            except Exception as exc:
                emit(log, f"跳过示例: {Path(path).name} - {exc}")
        sample_text = merge_sample_texts(sample_texts)
        if not sample_text:
            raise RuntimeError(
                "未读取到可用示例字幕。请使用单独字幕文件，或带内封字幕轨道的视频；硬字幕视频无法读取字幕。"
            )
        return sample_text

    outputs: list[Path] = []
    out_root = Path(output_dir) if output_dir else None

    for target in target_paths:
        target_path = Path(target)
        emit(log, f"处理字幕目标: {target_path.name}")
        try:
            if is_video(target_path):
                output_folder = out_root or target_path.parent / "字幕样式输出"
                output_folder.mkdir(parents=True, exist_ok=True)
                suffix = target_output_suffix(target_path, options.output_format)
                active_sample_text = get_sample_text()
                with tempfile.TemporaryDirectory(prefix="zipmkv_extract_") as temp_name:
                    temp_dir = Path(temp_name)
                    extracted_files = (
                        extract_all_subtitles_from_video(target_path, temp_dir, log=log)
                        if options.all_subtitle_streams
                        else [extract_subtitle_from_video(target_path, temp_dir, stream_index=options.subtitle_stream, log=log)]
                    )
                    outputs.extend(
                        _write_video_subtitle_outputs(
                            target_path,
                            extracted_files,
                            output_folder,
                            options,
                            active_sample_text if options.use_sample else None,
                            log,
                        )
                    )
            elif is_subtitle(target_path):
                output_folder = out_root or target_path.parent / "字幕样式输出"
                output_folder.mkdir(parents=True, exist_ok=True)
                active_sample_text = get_sample_text()
                if target_path.suffix.casefold() in {".ass", ".ssa"}:
                    ass_text = apply_styles_to_ass(
                        read_text(target_path),
                        options,
                        sample_text=active_sample_text if options.use_sample else None,
                    )
                else:
                    ass_text = subtitle_text_to_ass(target_path, options)
                    if options.use_sample and active_sample_text:
                        ass_text = apply_styles_to_ass(ass_text, options, sample_text=active_sample_text)
                ass_text = convert_ass_dialogue_texts(ass_text, options.text_conversion_mode)
                suffix = target_output_suffix(target_path, options.output_format)
                output = unique_path(output_folder / f"{safe_stem(target_path.stem)}_modified{suffix}")
                output.write_text(render_output_text(ass_text, suffix), encoding="utf-8")
                outputs.append(output)
                emit(log, f"已输出字幕: {output}")
            else:
                emit(log, f"跳过不支持的文件: {target_path}")
        except Exception as exc:
            emit(log, f"处理失败: {target_path.name} - {exc}")
    return outputs


def ass_color_to_rgb(value: str, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    value = value.strip()
    match = re.fullmatch(r"&H(?:[0-9A-Fa-f]{2})?([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})", value)
    if not match:
        return fallback
    bb, gg, rr = match.groups()
    return int(rr, 16), int(gg, 16), int(bb, 16)


def first_preview_style(ass_text: str) -> dict[str, str]:
    _, styles = parse_ass_styles(ass_text)
    if not styles:
        return DEFAULT_ASS_STYLE.copy()
    dominant, confident = dominant_sample_style(styles, ass_text)
    if dominant and confident:
        return {**DEFAULT_ASS_STYLE, **dominant}
    for style in styles:
        if style.get("Name", "").casefold() == "default":
            return {**DEFAULT_ASS_STYLE, **style}
    return {**DEFAULT_ASS_STYLE, **styles[0]}


def create_ass_preview_image(
    subtitle_path: str | Path,
    output_path: str | Path,
    sample_text: str = "字幕效果预览\\NSubtitle Preview",
) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    source = Path(subtitle_path)
    output = Path(output_path)
    ass_text = read_text(source) if source.suffix.casefold() in {".ass", ".ssa"} else subtitle_text_to_ass(source, StyleOptions())
    style = first_preview_style(ass_text)

    width, height = 960, 540
    image = Image.new("RGB", (width, height), (24, 27, 31))
    draw = ImageDraw.Draw(image)
    for y in range(height):
        shade = 24 + int(y / height * 32)
        draw.line([(0, y), (width, y)], fill=(shade, shade + 2, shade + 6))

    font_size = int(float(style.get("Fontsize", "48") or 48))
    font_size = max(18, min(font_size, 90))
    font_candidates = [
        style.get("Fontname", ""),
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    font = None
    for candidate in font_candidates:
        if not candidate:
            continue
        try:
            font = ImageFont.truetype(candidate, font_size)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()

    primary = ass_color_to_rgb(style.get("PrimaryColour", ""), (255, 255, 255))
    outline_color = ass_color_to_rgb(style.get("OutlineColour", ""), (0, 0, 0))
    outline = int(float(style.get("Outline", "2") or 2))
    shadow = int(float(style.get("Shadow", "0") or 0))
    margin_v = int(float(style.get("MarginV", "36") or 36))
    alignment = int(float(style.get("Alignment", "2") or 2))

    lines = sample_text.replace(r"\N", "\n").splitlines()
    boxes = [draw.textbbox((0, 0), line, font=font, stroke_width=outline) for line in lines]
    text_width = max((box[2] - box[0] for box in boxes), default=0)
    line_height = max((box[3] - box[1] for box in boxes), default=font_size) + 8
    text_height = line_height * len(lines)
    x = (width - text_width) // 2
    if alignment in {7, 8, 9}:
        y = margin_v
    elif alignment in {4, 5, 6}:
        y = (height - text_height) // 2
    else:
        y = height - margin_v - text_height

    if shadow:
        for offset in range(1, shadow + 1):
            for idx, line in enumerate(lines):
                draw.text((x + offset * 2, y + idx * line_height + offset * 2), line, font=font, fill=(0, 0, 0))
    for idx, line in enumerate(lines):
        draw.text(
            (x, y + idx * line_height),
            line,
            font=font,
            fill=primary,
            stroke_width=max(0, outline),
            stroke_fill=outline_color,
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return output

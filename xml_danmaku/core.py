from __future__ import annotations

import html
import os
import re
from dataclasses import dataclass
from pathlib import Path

from common.log import Logger, emit
from common.zhconv import convert_chinese_text


P_PATTERN = re.compile(r'(<d\s+[^>]*p=")([^",]+)((?:,[^"]*)?)(")')
CONTENT_PATTERN = re.compile(r"(<d\s+[^>]*>)(.*?)(</d>)")


@dataclass
class DanmakuOptions:
    delete_negative: bool = True
    adjust_enabled: bool = False
    offset_seconds: float = 0.0
    strip_ass_tags: bool = False
    output_dir_name: str = "已修改的弹幕"
    text_conversion_mode: str = "none"


@dataclass
class DanmakuStats:
    deleted: int = 0
    adjusted: int = 0
    stripped: int = 0


def ass_color_to_decimal(ass_color: str) -> int | None:
    match = re.fullmatch(r"&H([0-9A-Fa-f]{6})", ass_color)
    if not match:
        return None
    value = match.group(1)
    blue = int(value[0:2], 16)
    green = int(value[2:4], 16)
    red = int(value[4:6], 16)
    return red + (green << 8) + (blue << 16)


def remove_ass_tags(text: str) -> tuple[str, str | None]:
    color_matches = re.findall(r"\{\s*\\c(&H[0-9A-Fa-f]{6})\b[^}]*\}", text)
    last_color = color_matches[-1] if color_matches else None
    cleaned = re.sub(r"\{[^}]*\}", "", text)
    cleaned = re.sub(r"\\hh?", " ", cleaned)
    cleaned = re.sub(r"\\[nN]", " ", cleaned)
    cleaned = re.sub(r"\\[a-zA-Z]+\d*", " ", cleaned)
    cleaned = re.sub(r" +", " ", cleaned).strip()
    return cleaned, last_color


def _replace_color_in_p(line: str, decimal_color: int) -> str:
    def replacer(match: re.Match[str]) -> str:
        fields = match.group(3).lstrip(",").split(",")
        if len(fields) >= 3:
            fields[2] = str(decimal_color)
            return match.group(1) + match.group(2) + "," + ",".join(fields) + match.group(4)
        return match.group(0)

    return P_PATTERN.sub(replacer, line, count=1)


def _adjust_time(line: str, offset_seconds: float) -> tuple[str, bool]:
    match = P_PATTERN.search(line)
    if not match:
        return line, False
    try:
        old_time = float(match.group(2))
    except ValueError:
        return line, False
    new_time = old_time + offset_seconds
    new_time_str = f"{new_time:.6f}".rstrip("0").rstrip(".")
    return (
        P_PATTERN.sub(lambda m: m.group(1) + new_time_str + m.group(3) + m.group(4), line, count=1),
        True,
    )


def process_line(line: str, options: DanmakuOptions, stats: DanmakuStats) -> str | None:
    if options.delete_negative:
        match = P_PATTERN.search(line)
        if match:
            try:
                if float(match.group(2)) < 0:
                    stats.deleted += 1
                    return None
            except ValueError:
                pass

    if options.strip_ass_tags or options.text_conversion_mode != "none":
        content_match = CONTENT_PATTERN.search(line)
        if content_match:
            _prefix, content, _suffix = content_match.group(1, 2, 3)
            decoded = html.unescape(content)
            new_content = decoded
            if options.strip_ass_tags:
                new_content, color_tag = remove_ass_tags(new_content)
                if new_content != decoded:
                    stats.stripped += 1
                    if color_tag:
                        decimal_color = ass_color_to_decimal(color_tag)
                        if decimal_color is not None:
                            line = _replace_color_in_p(line, decimal_color)
            if options.text_conversion_mode != "none":
                new_content = convert_chinese_text(new_content, options.text_conversion_mode)
            if new_content != decoded:
                line = CONTENT_PATTERN.sub(
                    lambda match: match.group(1) + html.escape(new_content) + match.group(3),
                    line,
                    count=1,
                )

    if options.adjust_enabled and options.offset_seconds:
        line, adjusted = _adjust_time(line, options.offset_seconds)
        if adjusted:
            stats.adjusted += 1

    return line


def process_xml_file(path: str | Path, options: DanmakuOptions) -> tuple[Path, DanmakuStats]:
    source = Path(path)
    output_dir = source.parent / options.output_dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / source.name
    stats = DanmakuStats()

    lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        for line in lines:
            processed = process_line(line, options, stats)
            if processed is not None:
                handle.write(processed)
    return output, stats


def process_xml_files(paths: list[str | Path], options: DanmakuOptions, log: Logger | None = None) -> int:
    success = 0
    for path in paths:
        try:
            output, stats = process_xml_file(path, options)
            emit(
                log,
                f"{os.path.basename(path)} -> {output} | 调整 {stats.adjusted}，删除 {stats.deleted}，清理 {stats.stripped}",
            )
            success += 1
        except Exception as exc:
            emit(log, f"失败: {path} - {exc}")
    return success

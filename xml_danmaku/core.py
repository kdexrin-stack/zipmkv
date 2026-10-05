from __future__ import annotations

import html
import os
import re
from dataclasses import dataclass
from pathlib import Path

from common.log import Logger, emit
from common.text_utils import unique_path
from common.zhconv import convert_chinese_text


P_PATTERN = re.compile(r'(<d\s+[^>]*p=")([^",]+)((?:,[^"]*)?)(")')
CONTENT_PATTERN = re.compile(r"(<d\s+[^>]*>)(.*?)(</d>)")


@dataclass
class DanmakuOptions:
    delete_negative: bool = True
    adjust_enabled: bool = False
    offset_seconds: float = 0.0
    strip_ass_tags: bool = False
    output_format: str = "xml"  # "xml", "ass", "srt"
    output_dir_name: str = "已修改的弹幕"
    text_conversion_mode: str = "none"
    scroll_duration: float = 10.0
    static_duration: float = 5.0
    font_name: str = "Microsoft YaHei"
    font_size: int = 34
    screen_width: int = 1920
    screen_height: int = 1080


@dataclass
class DanmakuStats:
    deleted: int = 0
    adjusted: int = 0
    stripped: int = 0
    converted: int = 0


@dataclass
class DanmakuItem:
    time: float
    mode: int
    size: int
    color: int
    text: str


def ass_color_to_decimal(ass_color: str) -> int | None:
    match = re.fullmatch(r"&H([0-9A-Fa-f]{6})", ass_color)
    if not match:
        return None
    value = match.group(1)
    blue = int(value[0:2], 16)
    green = int(value[2:4], 16)
    red = int(value[4:6], 16)
    return red + (green << 8) + (blue << 16)


def decimal_to_ass_color(color_num: int) -> str:
    red = (color_num >> 16) & 0xFF
    green = (color_num >> 8) & 0xFF
    blue = color_num & 0xFF
    return f"&H00{blue:02X}{green:02X}{red:02X}"


def format_ass_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def format_srt_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms >= 1000:
        ms = 999
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


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


def parse_danmaku_items(source: Path, options: DanmakuOptions, stats: DanmakuStats) -> list[DanmakuItem]:
    items: list[DanmakuItem] = []
    danmaku_tag = re.compile(r'<d\s+p="([^"]+)">([^<]*)</d>')
    with source.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            match = danmaku_tag.search(line)
            if not match:
                continue
            p_str, text_raw = match.group(1), match.group(2)
            params = p_str.split(",")
            if len(params) < 4:
                continue
            try:
                t = float(params[0])
                mode = int(params[1])
                size = int(params[2])
                color = int(params[3])
            except ValueError:
                continue
            
            if options.adjust_enabled:
                t += options.offset_seconds
            if options.delete_negative and t < 0:
                stats.deleted += 1
                continue
            text = html.unescape(text_raw)
            if options.strip_ass_tags:
                text, _ = remove_ass_tags(text)
                stats.stripped += 1
            if options.text_conversion_mode != "none":
                text = convert_chinese_text(text, options.text_conversion_mode)
            if not text.strip():
                continue
            items.append(DanmakuItem(time=t, mode=mode, size=size, color=color, text=text))
        
    items.sort(key=lambda x: x.time)
    return items


def convert_items_to_ass(items: list[DanmakuItem], options: DanmakuOptions) -> str:
    w = options.screen_width
    h = options.screen_height
    font_size = options.font_size
    line_h = font_size + 6
    max_tracks = max(10, (h - 150) // line_h)
    
    header = [
        "[Script Info]",
        "; Script generated by zipmkv Danmaku Converter",
        "Title: Danmaku Subtitle",
        "ScriptType: v4.00+",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        f"PlayResX: {w}",
        f"PlayResY: {h}",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: R2L,{options.font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,1.5,0,7,0,0,0,1",
        f"Style: TOP,{options.font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,1.5,0,8,0,0,0,1",
        f"Style: BTM,{options.font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,1.5,0,2,0,0,0,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    
    track_end_time = [0.0] * max_tracks
    track_enter_time = [0.0] * max_tracks
    top_end_time = [0.0] * max_tracks
    btm_end_time = [0.0] * max_tracks
    
    events: list[str] = []
    
    for item in items:
        start_t = max(0.0, item.time)
        color_tag = ""
        if item.color != 16777215 and item.color != 0:
            color_tag = f"{{\\c{decimal_to_ass_color(item.color)}}}"
            
        if item.mode in (1, 2, 3, 6):  # Scroll R2L
            dur = options.scroll_duration
            end_t = start_t + dur
            text_len = len(item.text)
            text_w = text_len * font_size
            enter_t = start_t + dur * (text_w / (w + text_w))
            
            # Find best track
            chosen_row = 0
            found = False
            for r in range(max_tracks):
                if start_t >= track_enter_time[r] and end_t >= track_end_time[r]:
                    chosen_row = r
                    found = True
                    break
            if not found:
                chosen_row = min(range(max_tracks), key=lambda r: track_enter_time[r])
                
            track_enter_time[chosen_row] = enter_t
            track_end_time[chosen_row] = end_t
            y = 20 + chosen_row * line_h
            
            start_str = format_ass_time(start_t)
            end_str = format_ass_time(end_t)
            move_cmd = f"{{\\move({w}, {y}, -{text_w}, {y})}}"
            events.append(f"Dialogue: 0,{start_str},{end_str},R2L,,0,0,0,,{move_cmd}{color_tag}{item.text}")
            
        elif item.mode == 5:  # Top static
            dur = options.static_duration
            end_t = start_t + dur
            chosen_row = 0
            for r in range(max_tracks):
                if start_t >= top_end_time[r]:
                    chosen_row = r
                    break
            top_end_time[chosen_row] = end_t
            y = 20 + chosen_row * line_h
            start_str = format_ass_time(start_t)
            end_str = format_ass_time(end_t)
            pos_cmd = f"{{\\pos({w // 2}, {y})}}"
            events.append(f"Dialogue: 0,{start_str},{end_str},TOP,,0,0,0,,{pos_cmd}{color_tag}{item.text}")
            
        elif item.mode == 4:  # Bottom static
            dur = options.static_duration
            end_t = start_t + dur
            chosen_row = 0
            for r in range(max_tracks):
                if start_t >= btm_end_time[r]:
                    chosen_row = r
                    break
            btm_end_time[chosen_row] = end_t
            y = h - 30 - chosen_row * line_h
            start_str = format_ass_time(start_t)
            end_str = format_ass_time(end_t)
            pos_cmd = f"{{\\pos({w // 2}, {y})}}"
            events.append(f"Dialogue: 0,{start_str},{end_str},BTM,,0,0,0,,{pos_cmd}{color_tag}{item.text}")
            
    return "\n".join(header + events).rstrip() + "\n"


def convert_items_to_srt(items: list[DanmakuItem], options: DanmakuOptions) -> str:
    blocks: list[str] = []
    for idx, item in enumerate(items, 1):
        start_t = max(0.0, item.time)
        dur = options.scroll_duration if item.mode in (1, 2, 3, 6) else options.static_duration
        end_t = start_t + dur
        start_str = format_srt_time(start_t)
        end_str = format_srt_time(end_t)
        blocks.append(f"{idx}\n{start_str} --> {end_str}\n{item.text}")
    return "\n\n".join(blocks).rstrip() + "\n"


def process_xml_file(path: str | Path, options: DanmakuOptions) -> tuple[Path, DanmakuStats]:
    source = Path(path)
    stats = DanmakuStats()
    
    fmt = options.output_format.casefold().lstrip(".")
    if fmt == "ass":
        output_dir = source.parent / "弹幕转字幕输出"
        output_dir.mkdir(parents=True, exist_ok=True)
        output = unique_path(output_dir / f"{source.stem}.ass")
        items = parse_danmaku_items(source, options, stats)
        ass_content = convert_items_to_ass(items, options)
        output.write_text(ass_content, encoding="utf-8")
        stats.converted = len(items)
        return output, stats
        
    if fmt == "srt":
        output_dir = source.parent / "弹幕转字幕输出"
        output_dir.mkdir(parents=True, exist_ok=True)
        output = unique_path(output_dir / f"{source.stem}.srt")
        items = parse_danmaku_items(source, options, stats)
        srt_content = convert_items_to_srt(items, options)
        output.write_text(srt_content, encoding="utf-8")
        stats.converted = len(items)
        return output, stats
        
    output_dir = source.parent / options.output_dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    output = unique_path(output_dir / source.name)

    with source.open("r", encoding="utf-8", errors="replace") as in_f, output.open("w", encoding="utf-8", newline="") as handle:
        for line in in_f:
            processed = process_line(line, options, stats)
            if processed is not None:
                handle.write(processed)
    return output, stats


def process_xml_files(paths: list[str | Path], options: DanmakuOptions, log: Logger | None = None) -> int:
    success = 0
    for path in paths:
        try:
            output, stats = process_xml_file(path, options)
            if options.output_format.casefold() in ("ass", "srt"):
                emit(
                    log,
                    f"{os.path.basename(path)} -> {output} | 转换生成 {stats.converted} 条字幕",
                )
            else:
                emit(
                    log,
                    f"{os.path.basename(path)} -> {output} | 调整 {stats.adjusted}，删除 {stats.deleted}，清理 {stats.stripped}",
                )
            success += 1
        except Exception as exc:
            emit(log, f"失败: {path} - {exc}")
    return success

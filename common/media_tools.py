from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from .paths import app_root, materialize_tool_dir, resource_path, runtime_tool_dir


def _program_file_dirs(app_dir_name: str) -> list[Path]:
    dirs: list[Path] = []
    for env_name in ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(env_name)
        if base:
            dirs.append(Path(base) / app_dir_name)
    if os.name == "nt":
        for drive_letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            root = Path(f"{drive_letter}:\\")
            if root.exists():
                dirs.append(root / "Program Files" / app_dir_name)
                dirs.append(root / "Program Files (x86)" / app_dir_name)
    seen: set[str] = set()
    result: list[Path] = []
    for item in dirs:
        key = str(item).casefold()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def find_executable(names: list[str], app_dirs: list[str]) -> Path | None:
    vendor_dirs = [
        materialize_tool_dir("ffmpeg"),
        resource_path("vendor", "tools", "ffmpeg"),
        resource_path("vendor", "tools"),
    ]
    for directory in vendor_dirs:
        for name in names:
            candidate = directory / name
            if candidate.is_file():
                return candidate
        for pattern in names:
            stem = Path(pattern).stem
            for candidate in directory.glob(f"{stem}*.exe"):
                if candidate.is_file():
                    return candidate

    for name in names:
        found = shutil.which(name)
        if found:
            return Path(found)
    for app_dir in app_dirs:
        for directory in _program_file_dirs(app_dir):
            for name in names:
                candidate = directory / "bin" / name
                if candidate.is_file():
                    return candidate
                candidate = directory / name
                if candidate.is_file():
                    return candidate
    return None


def find_ffmpeg() -> Path | None:
    found = find_executable(["ffmpeg.exe", "ffmpeg"], ["ffmpeg", "FFmpeg"])
    if found:
        return found
    try:
        import imageio_ffmpeg

        bundled = imageio_ffmpeg.get_ffmpeg_exe()
        if bundled:
            return Path(bundled)
    except Exception:
        pass
    return None


def find_ffprobe() -> Path | None:
    return find_executable(["ffprobe.exe", "ffprobe"], ["ffmpeg", "FFmpeg"])


def describe_ffmpeg(path: str | Path | None = None) -> str:
    if path is None:
        materialized = runtime_tool_dir("ffmpeg") / "ffmpeg.exe"
        if materialized.exists():
            ffmpeg = materialized
        elif (resource_path("vendor", "tools", "ffmpeg", "ffmpeg.7z")).exists():
            return "内置 FFmpeg：首次处理视频时自动准备"
        else:
            ffmpeg = find_ffmpeg()
    else:
        ffmpeg = Path(path)
    if not ffmpeg:
        return "未检测到 FFmpeg"
    try:
        relative = ffmpeg.resolve().relative_to((app_root() / "tools").resolve())
        return f"内置 FFmpeg: tools\\{relative}"
    except (OSError, ValueError):
        pass
    if any(part.startswith("_MEI") for part in ffmpeg.parts):
        return "内置 FFmpeg（单文件 EXE 运行时临时目录）"
    return f"FFmpeg: {ffmpeg}"


def run_hidden(args: list[str], timeout: int = 1200) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def ffmpeg_probe_text(video_path: str | Path) -> str:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("未找到 ffmpeg，无法读取视频内封字幕。")
    result = run_hidden([str(ffmpeg), "-hide_banner", "-i", str(video_path)], timeout=120)
    return (result.stderr or "") + "\n" + (result.stdout or "")


def probe_stream_lines(video_path: str | Path) -> list[str]:
    text = ffmpeg_probe_text(video_path)
    return [line.strip() for line in text.splitlines() if "Stream #" in line]


def _probe_with_ffmpeg(video_path: str | Path) -> list[dict]:
    text = ffmpeg_probe_text(video_path)
    streams: list[dict] = []
    pattern = re.compile(
        r"Stream #0:(?P<index>\d+)"
        r"(?:\[[^\]]+\])?"
        r"(?:\((?P<language>[^)]+)\))?"
        r"[^:\r\n]*:\s*Subtitle:\s*(?P<codec>[^\r\n]+)",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        codec = match.group("codec").split(",", 1)[0].strip()
        block = text[match.end(): match.end() + 900]
        next_stream = block.find("Stream #")
        if next_stream >= 0:
            block = block[:next_stream]
        title_match = re.search(r"^\s*title\s*:\s*(?P<title>.+)$", block, re.IGNORECASE | re.MULTILINE)
        streams.append(
            {
                "index": int(match.group("index")),
                "codec_name": codec,
                "tags": {
                    "language": match.group("language") or "",
                    "title": title_match.group("title").strip() if title_match else "",
                },
            }
        )
    return streams


def probe_subtitle_streams(video_path: str | Path, ffprobe_path: str | Path | None = None) -> list[dict]:
    ffprobe = Path(ffprobe_path) if ffprobe_path else find_ffprobe()
    if not ffprobe:
        return _probe_with_ffmpeg(video_path)
    result = run_hidden([
        str(ffprobe),
        "-v",
        "error",
        "-select_streams",
        "s",
        "-show_entries",
        "stream=index,codec_name:stream_tags=language,title",
        "-of",
        "json",
        str(video_path),
    ])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "读取字幕轨道失败")
    payload = json.loads(result.stdout or "{}")
    return payload.get("streams", [])

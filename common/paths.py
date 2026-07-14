from __future__ import annotations

import sys
import shutil
import subprocess
from pathlib import Path


def bundle_root() -> Path:
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled:
        return Path(bundled).resolve()
    return Path(__file__).resolve().parents[1]


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def resource_path(*parts: str) -> Path:
    return bundle_root().joinpath(*parts)


def runtime_tool_dir(tool_name: str | None = None) -> Path:
    root = app_root() / "tools"
    return root / tool_name if tool_name else root


def materialize_tool_dir(tool_name: str) -> Path:
    target = runtime_tool_dir(tool_name)
    expected_name = "ffmpeg.exe" if tool_name == "ffmpeg" else "7z.exe" if tool_name == "7zip" else None
    if target.exists() and (expected_name is None or (target / expected_name).exists()):
        return target

    source = resource_path("vendor", "tools", tool_name)
    if not source.exists():
        return target

    try:
        target.mkdir(parents=True, exist_ok=True)
        packed_ffmpeg = source / "ffmpeg.7z"
        if tool_name == "ffmpeg" and packed_ffmpeg.is_file():
            seven_zip = materialize_tool_dir("7zip") / "7z.exe"
            if not seven_zip.exists():
                return source
            result = subprocess.run(
                [str(seven_zip), "x", "-y", f"-o{target}", str(packed_ffmpeg)],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode == 0 and (target / "ffmpeg.exe").exists():
                return target
            return source
        if source.is_dir():
            for item in source.iterdir():
                destination = target / item.name
                if item.is_file() and (
                    not destination.exists() or destination.stat().st_size != item.stat().st_size
                ):
                    shutil.copy2(item, destination)
        elif source.is_file():
            shutil.copy2(source, target / source.name)
    except OSError:
        return source
    return target


def ensure_runtime_dirs(root: Path | None = None) -> dict[str, Path]:
    base = root or app_root()
    dirs = {
        "root": base,
        "output": base / "output",
        "temp": base / "temp",
        "logs": base / "logs",
        "config": base / "config",
        "tools": base / "tools",
    }
    for path in dirs.values():
        if path != base:
            path.mkdir(parents=True, exist_ok=True)
    return dirs

from __future__ import annotations

import sys
import shutil
import subprocess
import os
import threading
from pathlib import Path


_TOOL_MATERIALIZE_LOCK = threading.RLock()
_APP_ROOT: Path | None = None


def bundle_root() -> Path:
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled:
        return Path(bundled).resolve()
    return Path(__file__).resolve().parents[1]


def app_root() -> Path:
    global _APP_ROOT
    if _APP_ROOT is not None:
        return _APP_ROOT
    candidate = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
    try:
        candidate.mkdir(parents=True, exist_ok=True)
        probe = candidate / ".zipmkv_write_probe"
        probe.write_bytes(b"ok")
        probe.unlink(missing_ok=True)
        _APP_ROOT = candidate
    except OSError:
        local_root = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        _APP_ROOT = Path(local_root) / "zipmkv"
        _APP_ROOT.mkdir(parents=True, exist_ok=True)
    return _APP_ROOT


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

    with _TOOL_MATERIALIZE_LOCK:
        if target.exists() and (expected_name is None or (target / expected_name).exists()):
            return target
        staging = target.parent / f".{tool_name}.staging"
        try:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
            staging.mkdir(parents=True, exist_ok=True)
            packed_ffmpeg = source / "ffmpeg.7z"
            if tool_name == "ffmpeg" and packed_ffmpeg.is_file():
                seven_zip = materialize_tool_dir("7zip") / "7z.exe"
                if not seven_zip.exists():
                    return source
                result = subprocess.run(
                    [str(seven_zip), "x", "-y", f"-o{staging}", str(packed_ffmpeg)],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if result.returncode != 0 or not (staging / "ffmpeg.exe").exists():
                    return source
            elif source.is_dir():
                for item in source.iterdir():
                    if item.name == "ffmpeg.7z":
                        continue
                    destination = staging / item.name
                    if item.is_file():
                        shutil.copy2(item, destination)
            elif source.is_file():
                shutil.copy2(source, staging / source.name)
            else:
                return target

            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
            os.replace(staging, target)
            return target
        except OSError:
            shutil.rmtree(staging, ignore_errors=True)
            return source


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

from __future__ import annotations

import sys
import shutil
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
    if target.exists():
        return target

    source = resource_path("vendor", "tools", tool_name)
    if not source.exists():
        return target

    try:
        target.mkdir(parents=True, exist_ok=True)
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

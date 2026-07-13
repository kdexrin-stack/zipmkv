from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


def natural_sort_key(value: str | Path) -> list[tuple[int, int | str]]:
    text = str(value.name if isinstance(value, Path) else value)
    parts = re.split(r"(\d+)", text)
    key: list[tuple[int, int | str]] = []
    for part in parts:
        if part.isdigit():
            key.append((0, int(part)))
        else:
            key.append((1, part.casefold()))
    return key


def natural_sorted(values: Iterable[str | Path]) -> list:
    return sorted(values, key=natural_sort_key)


def safe_stem(name: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", name).strip()
    return cleaned or "untitled"


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1

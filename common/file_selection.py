from __future__ import annotations

from pathlib import Path

from .archive_tools import is_archive
from .text_utils import natural_sorted


def collect_files_from_inputs(
    files: list[str | Path] | None = None,
    folders: list[str | Path] | None = None,
    extensions: set[str] | None = None,
    include_archives: bool = False,
    recursive: bool = True,
) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()

    def accepts(path: Path) -> bool:
        suffix = path.suffix.casefold()
        return (extensions is not None and suffix in extensions) or (include_archives and is_archive(path))

    def add(path: Path) -> None:
        if not path.is_file() or not accepts(path):
            return
        key = str(path.resolve()).casefold()
        if key not in seen:
            seen.add(key)
            result.append(path)

    for item in files or []:
        add(Path(item))

    for folder in folders or []:
        root = Path(folder)
        if not root.is_dir():
            continue
        iterator = root.rglob("*") if recursive else root.glob("*")
        for path in iterator:
            add(path)

    return natural_sorted(result)

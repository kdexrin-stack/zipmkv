from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .archive_tools import is_archive
from .text_utils import natural_sorted


def _path_key(path: str | Path) -> str:
    try:
        return str(Path(path).resolve()).casefold()
    except OSError:
        return str(path).casefold()


@dataclass(frozen=True)
class InputSnapshot:
    """Immutable input selection passed from Tk to a worker thread."""

    files: tuple[Path, ...]
    folders: tuple[Path, ...]
    excluded: frozenset[str]
    allowed_extensions: frozenset[str] | None
    include_archives: bool

    @property
    def has_inputs(self) -> bool:
        return bool(self.files or self.folders)


def resolve_input_snapshot(
    snapshot: InputSnapshot,
    extensions: set[str] | frozenset[str] | None = None,
    include_archives: bool | None = None,
) -> list[Path]:
    """Resolve a frozen selection. The potentially slow folder scan belongs in workers."""
    active_extensions = extensions if extensions is not None else snapshot.allowed_extensions
    if active_extensions is not None:
        active_extensions = {str(item).casefold() for item in active_extensions}
    active_archives = snapshot.include_archives if include_archives is None else include_archives
    resolved = collect_files_from_inputs(
        files=list(snapshot.files),
        folders=list(snapshot.folders),
        extensions=active_extensions,
        include_archives=active_archives,
    )
    excluded = snapshot.excluded
    return [path for path in resolved if _path_key(path) not in excluded and str(path) not in excluded]


def format_byte_size(size_in_bytes: int) -> str:
    """Format bytes into a human-readable string (KB, MB, GB)."""
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    elif size_in_bytes < 1024 * 1024 * 1024:
        return f"{size_in_bytes / (1024 * 1024):.1f} MB"
    return f"{size_in_bytes / (1024 * 1024 * 1024):.2f} GB"


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
        if extensions is None:
            return True
        suffix = path.suffix.casefold()
        normalized_extensions = {str(item).casefold() for item in extensions}
        return (suffix in normalized_extensions) or (include_archives and is_archive(path))

    def add(path: Path) -> None:
        if not path.is_file() or not accepts(path):
            return
        key = _path_key(path)
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


class InputFileCollection:
    """Unified data model for handling file & folder inputs with exclusions and summaries."""

    def __init__(self, allowed_extensions: set[str] | None = None, include_archives: bool = False):
        self.files: list[str] = []
        self.folders: list[str] = []
        self.excluded: set[str] = set()
        self.display_items: list[tuple[str, str]] = []
        self.allowed_extensions = allowed_extensions
        self.include_archives = include_archives
        self._cached_resolved: list[Path] | None = None
        self._cached_signature: tuple[object, ...] | None = None

    def _invalidate_cache(self) -> None:
        self._cached_resolved = None
        self._cached_signature = None

    def snapshot(self) -> InputSnapshot:
        return InputSnapshot(
            files=tuple(Path(path) for path in self.files if path not in self.excluded),
            folders=tuple(Path(path) for path in self.folders if path not in self.excluded),
            excluded=frozenset(self.excluded | {_path_key(path) for path in self.excluded}),
            allowed_extensions=(
                frozenset(str(item).casefold() for item in self.allowed_extensions)
                if self.allowed_extensions is not None
                else None
            ),
            include_archives=self.include_archives,
        )

    def has_inputs(self) -> bool:
        return bool(
            any(path not in self.excluded for path in self.files)
            or any(path not in self.excluded for path in self.folders)
        )

    def direct_files(self) -> list[Path]:
        """Return only explicitly selected files; never recurse into folders."""
        return [
            Path(path)
            for path in self.files
            if path not in self.excluded and Path(path).is_file()
        ]

    def visible_folders(self) -> list[Path]:
        return [Path(path) for path in self.folders if path not in self.excluded]

    def add_files(self, paths: list[str | Path]) -> None:
        for p in paths:
            sp = str(p)
            if sp not in self.files:
                self.files.append(sp)
                self.excluded.discard(sp)
        self._invalidate_cache()
        self.refresh_display_items()

    def add_folder(self, folder_path: str | Path) -> None:
        sf = str(folder_path)
        if sf not in self.folders:
            self.folders.append(sf)
            self.excluded.discard(sf)
        self._invalidate_cache()
        self.refresh_display_items()

    def remove_indices(self, indices: list[int]) -> None:
        for index in sorted(indices, reverse=True):
            if 0 <= index < len(self.display_items):
                _, raw_key = self.display_items[index]
                self.excluded.add(raw_key)
                if raw_key in self.files:
                    self.files.remove(raw_key)
                if raw_key in self.folders:
                    self.folders.remove(raw_key)
        self._invalidate_cache()
        self.refresh_display_items()

    def clear(self) -> None:
        self.files.clear()
        self.folders.clear()
        self.excluded.clear()
        self.display_items.clear()
        self._invalidate_cache()

    def refresh_display_items(self) -> None:
        items: list[tuple[str, str]] = []
        for folder in self.folders:
            if folder not in self.excluded:
                p = Path(folder)
                items.append((f"📁 [目录] {p.name or folder} ({folder})", folder))
        for file in self.files:
            if file not in self.excluded:
                p = Path(file)
                items.append((f"📄 {p.name}", file))
        self.display_items = items

    def resolve_files(self, extensions: set[str] | None = None, include_archives: bool | None = None) -> list[Path]:
        exts = extensions if extensions is not None else self.allowed_extensions
        incs = include_archives if include_archives is not None else self.include_archives
        signature = (
            tuple(self.files),
            tuple(self.folders),
            tuple(sorted(self.excluded)),
            tuple(sorted(str(item).casefold() for item in exts)) if exts is not None else None,
            incs,
        )
        if self._cached_resolved is not None and self._cached_signature == signature:
            return list(self._cached_resolved)
        all_resolved = collect_files_from_inputs(
            files=self.files,
            folders=self.folders,
            extensions=exts,
            include_archives=incs,
        )
        res = [p for p in all_resolved if str(p) not in self.excluded and str(p.resolve()) not in self.excluded]
        self._cached_resolved = res
        self._cached_signature = signature
        return list(res)

    def get_summary(self, extensions: set[str] | None = None, include_archives: bool | None = None) -> str:
        """Return an instant selection summary; folder contents are counted at execution time."""
        direct_files = self.direct_files()
        folders = self.visible_folders()
        if extensions is not None:
            normalized = {str(item).casefold() for item in extensions}
            direct_files = [path for path in direct_files if path.suffix.casefold() in normalized]
        if include_archives:
            allowed = {str(item).casefold() for item in (extensions or set())}
            direct_files = [
                path for path in direct_files if path.suffix.casefold() in allowed or is_archive(path)
            ]
        if not direct_files and not folders:
            return "尚未选择输入素材"
        total_size = sum(path.stat().st_size for path in direct_files if path.exists())
        parts = []
        if direct_files:
            parts.append(f"{len(direct_files)} 个直接文件 · {format_byte_size(total_size)}")
        if folders:
            parts.append(f"{len(folders)} 个文件夹（执行时递归扫描）")
        return "已选择 " + " + ".join(parts)

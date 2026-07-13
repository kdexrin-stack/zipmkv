from __future__ import annotations

from pathlib import Path

from common.file_selection import collect_files_from_inputs
from common.log import Logger
from common.zhconv import TEXT_EXTENSIONS, convert_text_files


def collect_convertible_files(
    files: list[str | Path] | None = None,
    folders: list[str | Path] | None = None,
    excluded: set[str] | None = None,
) -> list[Path]:
    paths = collect_files_from_inputs(files, folders, extensions=TEXT_EXTENSIONS)
    excluded_keys = excluded or set()
    return [path for path in paths if str(path.resolve()).casefold() not in excluded_keys]


def convert_many(
    files: list[str | Path],
    output_dir: str | Path | None,
    mode_key: str,
    output_format: str = "same",
    log: Logger | None = None,
) -> list[Path]:
    if not files:
        raise ValueError("请选择要转换的文本、字幕或 XML 文件。")
    return convert_text_files(files, output_dir, mode_key, output_format=output_format, log=log)

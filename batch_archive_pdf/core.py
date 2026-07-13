from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from random import choice

from common.archive_tools import ArchiveTool, extract_archive, is_archive
from common.log import Logger, emit
from common.text_utils import natural_sorted, safe_stem, unique_path
from image_archive_pdf.core import collect_image_paths, save_image_paths_to_pdf


def convert_archives_to_pdf(
    archive_paths: list[str | Path],
    output_dir: str | Path | None = None,
    password: str | None = None,
    archive_tool: ArchiveTool | None = None,
    log: Logger | None = None,
    preview_callback=None,
) -> list[Path]:
    archives = [Path(path) for path in archive_paths if Path(path).is_file() and is_archive(path)]
    if not archives:
        raise ValueError("请选择至少一个 zip、rar、7z、epub 等文件。")

    default_output = archives[0].parent / "PDF输出"
    out_root = Path(output_dir) if output_dir else default_output
    out_root.mkdir(parents=True, exist_ok=True)

    generated: list[Path] = []
    for index, archive in enumerate(natural_sorted(archives), 1):
        emit(log, f"[{index}/{len(archives)}] 处理压缩包: {archive.name}")
        temp_dir = Path(tempfile.mkdtemp(prefix="zipmkv_batch_"))
        try:
            extract_archive(archive, temp_dir, password=password, tool=archive_tool, log=log)
            image_paths, temp_dirs = collect_image_paths(temp_dir, password=password, archive_tool=archive_tool, log=log)
            if not image_paths:
                emit(log, f"未找到有效图片: {archive.name}")
                continue

            pdf_path = unique_path(out_root / f"{safe_stem(archive.stem)}.pdf")
            page_count = save_image_paths_to_pdf(image_paths, pdf_path, log=log)
            generated.append(pdf_path)
            emit(log, f"生成 PDF: {pdf_path}，页数 {page_count}")
            if preview_callback and image_paths:
                preview_callback(Path(choice(image_paths)), pdf_path)
            for nested_temp in temp_dirs:
                shutil.rmtree(nested_temp, ignore_errors=True)
        except Exception as exc:
            emit(log, f"处理失败: {archive.name} - {exc}")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return generated

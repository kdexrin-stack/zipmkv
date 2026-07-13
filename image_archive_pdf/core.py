from __future__ import annotations

import html
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from random import choice

from PIL import Image, ImageFile, ImageSequence
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

from common.archive_tools import ArchiveTool, extract_archive, is_archive
from common.log import Logger, emit
from common.text_utils import natural_sorted, safe_stem, unique_path
from common.zhconv import convert_chinese_text


ImageFile.LOAD_TRUNCATED_IMAGES = True

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp"}
PDF_EXTENSIONS = {".pdf"}
TEXT_EXTENSIONS = {".txt"}
HTML_EXTENSIONS = {".html", ".htm", ".xhtml"}
DOCUMENT_EXTENSIONS = IMAGE_EXTENSIONS | PDF_EXTENSIONS | TEXT_EXTENSIONS | HTML_EXTENSIONS
MERGE_INPUT_EXTENSIONS = IMAGE_EXTENSIONS | PDF_EXTENSIONS | TEXT_EXTENSIONS


@dataclass(frozen=True)
class ContentItem:
    kind: str
    path: Path
    title: str


@dataclass(frozen=True)
class EpubChapter:
    chapter_id: str
    title: str
    chapter_name: str
    body: str


def is_image(path: str | Path) -> bool:
    return Path(path).suffix.casefold() in IMAGE_EXTENSIONS


def is_pdf(path: str | Path) -> bool:
    return Path(path).suffix.casefold() in PDF_EXTENSIONS


def is_text(path: str | Path) -> bool:
    return Path(path).suffix.casefold() in TEXT_EXTENSIONS


def is_html(path: str | Path) -> bool:
    return Path(path).suffix.casefold() in HTML_EXTENSIONS


def is_merge_input(path: str | Path) -> bool:
    candidate = Path(path)
    return is_image(candidate) or is_pdf(candidate) or is_text(candidate) or is_archive(candidate)


def read_text_file(path: str | Path) -> str:
    source = Path(path)
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return source.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return source.read_text(encoding="utf-8", errors="replace")


def html_to_text(value: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", value)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|li|h[1-6]|tr|section|article)>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def read_content_text(item: ContentItem, text_conversion_mode: str = "none") -> str:
    if item.kind == "html":
        text = html_to_text(read_text_file(item.path))
    elif item.kind == "pdf":
        text = extract_pdf_text(item.path)
    else:
        text = read_text_file(item.path)
    return convert_chinese_text(text, text_conversion_mode)


def extract_pdf_text(path: str | Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("缺少 pypdf，无法读取或合并 PDF。请重新运行打包脚本安装项目依赖。") from exc

    reader = PdfReader(str(path))
    parts: list[str] = []
    for index, page in enumerate(reader.pages, 1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if text.strip():
            parts.append(f"第 {index} 页\n{text.strip()}")
    return "\n\n".join(parts)


def _append_image_to_pdf(pdf: canvas.Canvas, path: Path, log: Logger | None = None) -> int:
    try:
        with Image.open(path) as img:
            if path.suffix.casefold() == ".gif":
                count = 0
                for frame in ImageSequence.Iterator(img):
                    page = frame.convert("RGB")
                    width, height = page.size
                    pdf.setPageSize((width, height))
                    pdf.drawImage(ImageReader(page), 0, 0, width=width, height=height)
                    pdf.showPage()
                    count += 1
                return count

            page = img.convert("RGB")
            width, height = page.size
            pdf.setPageSize((width, height))
            pdf.drawImage(ImageReader(page), 0, 0, width=width, height=height)
            pdf.showPage()
            return 1
    except Exception as exc:
        emit(log, f"跳过无法读取的图片: {path.name} - {exc}")
        return 0


def collect_image_paths(
    root: str | Path,
    password: str | None = None,
    archive_tool: ArchiveTool | None = None,
    log: Logger | None = None,
) -> tuple[list[Path], list[Path]]:
    root_path = Path(root)
    image_paths: list[Path] = []
    temp_dirs: list[Path] = []

    if root_path.is_file():
        if is_image(root_path):
            return [root_path], []
        if is_archive(root_path):
            temp_dir = Path(tempfile.mkdtemp(prefix="zipmkv_extract_"))
            temp_dirs.append(temp_dir)
            extract_archive(root_path, temp_dir, password=password, tool=archive_tool, log=log)
            nested_paths, nested_temps = collect_image_paths(temp_dir, password=password, archive_tool=archive_tool, log=log)
            temp_dirs.extend(nested_temps)
            return nested_paths, temp_dirs
        return [], []

    for path in natural_sorted(root_path.rglob("*")):
        path = Path(path)
        if not path.is_file():
            continue
        if is_image(path):
            image_paths.append(path)
        elif is_archive(path):
            temp_dir = Path(tempfile.mkdtemp(prefix="zipmkv_nested_"))
            temp_dirs.append(temp_dir)
            try:
                extract_archive(path, temp_dir, password=password, tool=archive_tool, log=log)
                nested_paths, nested_temps = collect_image_paths(temp_dir, password=password, archive_tool=archive_tool, log=log)
                image_paths.extend(nested_paths)
                temp_dirs.extend(nested_temps)
            except Exception as exc:
                emit(log, f"跳过无法解压的压缩包: {path.name} - {exc}")
    return image_paths, temp_dirs


def collect_content_items(
    root: str | Path,
    password: str | None = None,
    archive_tool: ArchiveTool | None = None,
    log: Logger | None = None,
) -> tuple[list[ContentItem], list[Path]]:
    root_path = Path(root)
    items: list[ContentItem] = []
    temp_dirs: list[Path] = []

    def add_file(path: Path, title: str | None = None) -> None:
        suffix = path.suffix.casefold()
        item_title = title or path.stem
        if suffix in IMAGE_EXTENSIONS:
            items.append(ContentItem("image", path, item_title))
        elif suffix in PDF_EXTENSIONS:
            items.append(ContentItem("pdf", path, item_title))
        elif suffix in TEXT_EXTENSIONS:
            items.append(ContentItem("text", path, item_title))
        elif suffix in HTML_EXTENSIONS:
            items.append(ContentItem("html", path, item_title))

    if root_path.is_file():
        if root_path.suffix.casefold() in DOCUMENT_EXTENSIONS:
            add_file(root_path)
            return items, temp_dirs
        if is_archive(root_path):
            temp_dir = Path(tempfile.mkdtemp(prefix="zipmkv_extract_"))
            temp_dirs.append(temp_dir)
            extract_archive(root_path, temp_dir, password=password, tool=archive_tool, log=log)
            nested_items, nested_temps = collect_content_items(
                temp_dir,
                password=password,
                archive_tool=archive_tool,
                log=log,
            )
            temp_dirs.extend(nested_temps)
            return nested_items, temp_dirs
        return items, temp_dirs

    for path in natural_sorted(root_path.rglob("*")):
        path = Path(path)
        if not path.is_file():
            continue
        if path.suffix.casefold() in DOCUMENT_EXTENSIONS:
            add_file(path)
        elif is_archive(path):
            temp_dir = Path(tempfile.mkdtemp(prefix="zipmkv_nested_"))
            temp_dirs.append(temp_dir)
            try:
                extract_archive(path, temp_dir, password=password, tool=archive_tool, log=log)
                nested_items, nested_temps = collect_content_items(
                    temp_dir,
                    password=password,
                    archive_tool=archive_tool,
                    log=log,
                )
                items.extend(nested_items)
                temp_dirs.extend(nested_temps)
            except Exception as exc:
                emit(log, f"跳过无法解压的压缩包: {path.name} - {exc}")
    return items, temp_dirs


def save_image_paths_to_pdf(image_paths: list[str | Path], pdf_path: str | Path, log: Logger | None = None) -> int:
    if not image_paths:
        raise ValueError("没有可写入 PDF 的图片。")

    output = Path(pdf_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(output))
    page_count = 0
    try:
        for image_path in image_paths:
            page_count += _append_image_to_pdf(pdf, Path(image_path), log)
    finally:
        pdf.save()
    if page_count <= 0:
        raise ValueError("没有成功写入 PDF 的图片。")
    return page_count


def _wrap_text_line(text: str, font_name: str, font_size: int, max_width: float) -> list[str]:
    if not text:
        return [""]
    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        if current and pdfmetrics.stringWidth(candidate, font_name, font_size) > max_width:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def save_text_to_pdf(text: str, pdf_path: str | Path, title: str = "文本", log: Logger | None = None) -> int:
    output = Path(pdf_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    except Exception:
        pass
    font_name = "STSong-Light"
    font_size = 11
    width, height = A4
    margin = 54
    line_height = 16
    page_count = 0
    pdf = canvas.Canvas(str(output), pagesize=A4)
    try:
        pdf.setTitle(title)
        y = height - margin

        def new_page() -> None:
            nonlocal y, page_count
            if page_count:
                pdf.showPage()
            page_count += 1
            y = height - margin
            pdf.setFont(font_name, 14)
            pdf.drawString(margin, y, title[:80])
            y -= line_height * 2
            pdf.setFont(font_name, font_size)

        new_page()
        paragraphs = text.replace("\r\n", "\n").replace("\r", "\n").splitlines() or [""]
        for paragraph in paragraphs:
            wrapped = _wrap_text_line(paragraph, font_name, font_size, width - margin * 2) if paragraph else [""]
            for line in wrapped:
                if y < margin:
                    new_page()
                pdf.drawString(margin, y, line)
                y -= line_height
            if y < margin:
                new_page()
            y -= 4
    finally:
        pdf.save()
    if page_count <= 0:
        raise ValueError("没有成功写入文本 PDF。")
    return page_count


def save_content_items_to_pdf(
    items: list[ContentItem],
    pdf_path: str | Path,
    log: Logger | None = None,
    text_conversion_mode: str = "none",
) -> int:
    if not items:
        raise ValueError("没有可写入 PDF 的内容。")
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError as exc:
        raise RuntimeError("缺少 pypdf，无法合并 PDF。请重新运行打包脚本安装项目依赖。") from exc

    output = Path(pdf_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    page_count = 0
    with tempfile.TemporaryDirectory(prefix="zipmkv_merge_pdf_") as temp_name:
        temp_dir = Path(temp_name)
        for index, item in enumerate(items, 1):
            emit(log, f"写入 PDF 内容 {index}/{len(items)}: {item.path.name}")
            source_pdf: Path | None = None
            if item.kind == "pdf":
                source_pdf = item.path
                if text_conversion_mode != "none":
                    emit(log, f"PDF 页面原样合并，不转换页面文字: {item.path.name}")
            elif item.kind == "image":
                source_pdf = temp_dir / f"image_{index}.pdf"
                save_image_paths_to_pdf([item.path], source_pdf, log=log)
            else:
                source_pdf = temp_dir / f"text_{index}.pdf"
                text = read_content_text(item, text_conversion_mode=text_conversion_mode)
                if not text.strip():
                    emit(log, f"跳过无可提取文本的文件: {item.path.name}")
                    continue
                save_text_to_pdf(text, source_pdf, title=item.title, log=log)

            try:
                reader = PdfReader(str(source_pdf))
                if getattr(reader, "is_encrypted", False):
                    emit(log, f"跳过加密 PDF: {item.path.name}")
                    continue
                for page in reader.pages:
                    writer.add_page(page)
                    page_count += 1
            except Exception as exc:
                emit(log, f"跳过无法写入 PDF 的内容: {item.path.name} - {exc}")
        if page_count <= 0:
            raise ValueError("没有成功合并任何 PDF 页面。")
        with output.open("wb") as handle:
            writer.write(handle)
    return page_count


def _media_type(path: Path) -> str:
    suffix = path.suffix.casefold()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }.get(suffix, "application/octet-stream")


def _xhtml_document(title: str, body: str) -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE html>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" lang="zh-CN">\n'
        "<head>\n"
        f"<title>{html.escape(title)}</title>\n"
        '<meta charset="utf-8"/>\n'
        "<style>body{font-family:serif;line-height:1.65;margin:1em;} img{max-width:100%;height:auto;display:block;margin:auto;} pre{white-space:pre-wrap;}</style>\n"
        "</head>\n"
        f"<body>{body}</body>\n"
        "</html>\n"
    )


def _paragraphs_to_xhtml(text: str) -> str:
    paragraphs = [part.strip() for part in re.split(r"\n{2,}", text.replace("\r\n", "\n").replace("\r", "\n"))]
    if not paragraphs:
        return "<p></p>"
    body_parts: list[str] = []
    for paragraph in paragraphs:
        lines = [html.escape(line) for line in paragraph.splitlines()]
        body_parts.append("<p>" + "<br/>".join(lines) + "</p>")
    return "\n".join(body_parts)


def _epub_chapter_for_item(
    item: ContentItem,
    index: int,
    total: int,
    images: list[tuple[str, Path, str]],
    log: Logger | None,
    text_conversion_mode: str = "none",
) -> EpubChapter:
    chapter_id = f"chap{index}"
    chapter_name = f"chapters/{chapter_id}.xhtml"
    item_title = item.title or f"章节 {index}"
    emit(log, f"写入 EPUB 内容 {index}/{total}: {item.path.name}")
    if item.kind == "image":
        image_name = f"images/image_{index}{item.path.suffix.lower() or '.img'}"
        images.append((f"img{index}", item.path, image_name))
        body = (
            f"<h1>{html.escape(item_title)}</h1>"
            f"<p><img src=\"../{image_name}\" alt=\"{html.escape(item_title)}\"/></p>"
        )
    else:
        text = read_content_text(item, text_conversion_mode=text_conversion_mode)
        if item.kind == "pdf" and not text.strip():
            emit(log, f"PDF 没有可提取文本，EPUB 中保留提示章节: {item.path.name}")
            text = "该 PDF 未提取到可复制文本，可能是扫描版图片 PDF。"
        body = f"<h1>{html.escape(item_title)}</h1>\n{_paragraphs_to_xhtml(text)}"
    return EpubChapter(chapter_id, item_title, chapter_name, body)


def save_content_items_to_epub(
    items: list[ContentItem],
    epub_path: str | Path,
    title: str,
    log: Logger | None = None,
    text_conversion_mode: str = "none",
) -> int:
    if not items:
        raise ValueError("没有可写入 EPUB 的内容。")
    output = Path(epub_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    images: list[tuple[str, Path, str]] = []
    chapters = [
        _epub_chapter_for_item(item, index, len(items), images, log, text_conversion_mode=text_conversion_mode)
        for index, item in enumerate(items, 1)
    ]

    manifest_items = [
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '<item id="style" href="style.css" media-type="text/css"/>',
    ]
    spine_items: list[str] = []
    for chapter in chapters:
        manifest_items.append(f'<item id="{chapter.chapter_id}" href="{chapter.chapter_name}" media-type="application/xhtml+xml"/>')
        spine_items.append(f'<itemref idref="{chapter.chapter_id}"/>')
    for image_id, _path, image_name in images:
        manifest_items.append(f'<item id="{image_id}" href="{image_name}" media-type="{_media_type(Path(image_name))}"/>')

    nav_items = "\n".join(
        f'<li><a href="{chapter.chapter_name}">{html.escape(chapter.title)}</a></li>'
        for chapter in chapters
    )
    content_opf = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">\n'
        "<metadata xmlns:dc=\"http://purl.org/dc/elements/1.1/\">\n"
        '<dc:identifier id="bookid">zipmkv-generated-book</dc:identifier>\n'
        f"<dc:title>{html.escape(title)}</dc:title>\n"
        "<dc:language>zh-CN</dc:language>\n"
        "</metadata>\n"
        "<manifest>\n"
        + "\n".join(manifest_items)
        + "\n</manifest>\n"
        "<spine>\n"
        + "\n".join(spine_items)
        + "\n</spine>\n"
        "</package>\n"
    )
    nav = _xhtml_document(title, f"<h1>{html.escape(title)}</h1><nav epub:type=\"toc\" xmlns:epub=\"http://www.idpf.org/2007/ops\"><ol>{nav_items}</ol></nav>")
    style_css = "body{line-height:1.65;} img{max-width:100%;height:auto;}\n"
    container_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
        '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>\n'
        "</container>\n"
    )

    with zipfile.ZipFile(output, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", container_xml)
        zf.writestr("OEBPS/content.opf", content_opf)
        zf.writestr("OEBPS/nav.xhtml", nav)
        zf.writestr("OEBPS/style.css", style_css)
        for chapter in chapters:
            zf.writestr(f"OEBPS/{chapter.chapter_name}", _xhtml_document(chapter.title, chapter.body))
        for _image_id, image_path, image_name in images:
            zf.write(image_path, f"OEBPS/{image_name}")
    return len(chapters)


def _folder_pdf_items(folder: Path) -> list[Path]:
    child_items = [
        path
        for path in natural_sorted(folder.iterdir())
        if path.is_dir() or (path.is_file() and is_archive(path))
    ]
    if child_items:
        return child_items
    return [folder]


def _group_selected_images(image_paths: list[Path]) -> list[tuple[str, list[Path]]]:
    groups: dict[Path, list[Path]] = {}
    for image in natural_sorted(image_paths):
        groups.setdefault(image.parent, []).append(image)
    result: list[tuple[str, list[Path]]] = []
    for parent, images in groups.items():
        name = images[0].stem if len(images) == 1 else f"{parent.name or '选中图片'}_图片"
        result.append((name, images))
    return result


def _default_output_root(file_paths: list[Path], folder_paths: list[Path], output_dir: str | Path | None) -> Path:
    if output_dir:
        return Path(output_dir)
    if file_paths:
        return file_paths[0].parent / "整理输出"
    if folder_paths:
        return folder_paths[0] / "整理输出"
    return Path.cwd() / "整理输出"


def _collect_inputs_as_content(
    file_paths: list[Path],
    folder_paths: list[Path],
    password: str | None,
    archive_tool: ArchiveTool | None,
    log: Logger | None,
) -> tuple[list[ContentItem], list[Path]]:
    items: list[ContentItem] = []
    temp_dirs: list[Path] = []
    sources = natural_sorted(file_paths) + natural_sorted(folder_paths)
    for source in sources:
        emit(log, f"读取输入: {source.name}")
        source_items, source_temps = collect_content_items(
            source,
            password=password,
            archive_tool=archive_tool,
            log=log,
        )
        if not source_items:
            emit(log, f"未找到可合并内容: {source.name}")
        items.extend(source_items)
        temp_dirs.extend(source_temps)
    return items, temp_dirs


def _write_content_output(
    items: list[ContentItem],
    output: Path,
    output_format: str,
    title: str,
    log: Logger | None,
    text_conversion_mode: str = "none",
) -> int:
    if output_format == "epub":
        return save_content_items_to_epub(items, output, title=title, log=log, text_conversion_mode=text_conversion_mode)
    return save_content_items_to_pdf(items, output, log=log, text_conversion_mode=text_conversion_mode)


def convert_mixed_items(
    file_paths: list[str | Path] | None = None,
    folder_paths: list[str | Path] | None = None,
    output_dir: str | Path | None = None,
    password: str | None = None,
    archive_tool: ArchiveTool | None = None,
    output_format: str = "pdf",
    merge_output: bool = True,
    output_name: str = "",
    text_conversion_mode: str = "none",
    log: Logger | None = None,
    preview_callback=None,
) -> list[Path]:
    files = [Path(path) for path in file_paths or [] if Path(path).is_file() and is_merge_input(path)]
    folders = [Path(path) for path in folder_paths or [] if Path(path).is_dir()]
    if not files and not folders:
        raise ValueError("请选择图片、压缩包、EPUB、PDF、TXT，或包含这些内容的文件夹。")

    fmt = output_format.casefold().strip().lstrip(".")
    if fmt not in {"pdf", "epub"}:
        raise ValueError("输出格式只支持 PDF 或 EPUB。")

    out_root = _default_output_root(files, folders, output_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    suffix = f".{fmt}"
    generated: list[Path] = []

    if merge_output:
        items, temp_dirs = _collect_inputs_as_content(files, folders, password, archive_tool, log)
        try:
            if not items:
                raise ValueError("没有可合并的内容。")
            name = safe_stem(output_name.strip() or "合并整理")
            output = unique_path(out_root / f"{name}{suffix}")
            count = _write_content_output(items, output, fmt, name, log, text_conversion_mode=text_conversion_mode)
            generated.append(output)
            emit(log, f"生成 {fmt.upper()}: {output}，内容数 {count}")
            first_image = next((item.path for item in items if item.kind == "image"), None)
            if preview_callback and first_image:
                preview_callback(first_image, output)
        finally:
            for temp_dir in temp_dirs:
                shutil.rmtree(temp_dir, ignore_errors=True)
        return generated

    sources = natural_sorted(files) + natural_sorted(folders)
    for index, source in enumerate(sources, 1):
        emit(log, f"[{index}/{len(sources)}] 处理: {source.name}")
        items, temp_dirs = collect_content_items(source, password=password, archive_tool=archive_tool, log=log)
        try:
            if not items:
                emit(log, f"未找到可输出内容: {source.name}")
                continue
            name = safe_stem(source.stem if source.is_file() else source.name)
            output = unique_path(out_root / f"{name}{suffix}")
            count = _write_content_output(items, output, fmt, name, log, text_conversion_mode=text_conversion_mode)
            generated.append(output)
            emit(log, f"生成 {fmt.upper()}: {output}，内容数 {count}")
            first_image = next((item.path for item in items if item.kind == "image"), None)
            if preview_callback and first_image:
                preview_callback(first_image, output)
        finally:
            for temp_dir in temp_dirs:
                shutil.rmtree(temp_dir, ignore_errors=True)

    return generated


def convert_mixed_items_to_pdf(
    file_paths: list[str | Path] | None = None,
    folder_paths: list[str | Path] | None = None,
    output_dir: str | Path | None = None,
    password: str | None = None,
    archive_tool: ArchiveTool | None = None,
    log: Logger | None = None,
    preview_callback=None,
) -> list[Path]:
    files = [Path(path) for path in file_paths or [] if Path(path).is_file()]
    folders = [Path(path) for path in folder_paths or [] if Path(path).is_dir()]
    archive_files = [path for path in files if is_archive(path)]
    image_files = [path for path in files if is_image(path)]

    jobs: list[tuple[str, Path]] = []
    image_groups = _group_selected_images(image_files)
    for archive in natural_sorted(archive_files):
        jobs.append((safe_stem(archive.stem), archive))
    for folder in natural_sorted(folders):
        folder_items = _folder_pdf_items(folder)
        for item in folder_items:
            name = safe_stem(item.stem if item.is_file() else item.name)
            jobs.append((name, item))
        if folder_items != [folder]:
            loose_images = [
                path for path in natural_sorted(folder.iterdir()) if path.is_file() and is_image(path)
            ]
            if loose_images:
                image_groups.append((f"{safe_stem(folder.name)}_散图", loose_images))

    if not jobs and not image_groups:
        raise ValueError("请选择图片、压缩包、EPUB，或包含图片/压缩包的文件夹。")

    out_root = Path(output_dir) if output_dir else None
    if out_root:
        out_root.mkdir(parents=True, exist_ok=True)

    generated: list[Path] = []
    total_jobs = len(jobs) + len(image_groups)
    current = 0

    for name, item in jobs:
        current += 1
        emit(log, f"[{current}/{total_jobs}] 处理: {item.name}")
        image_paths, temp_dirs = collect_image_paths(item, password=password, archive_tool=archive_tool, log=log)
        if not image_paths:
            for temp_dir in temp_dirs:
                shutil.rmtree(temp_dir, ignore_errors=True)
            emit(log, f"未找到有效图片: {item.name}")
            continue

        target_dir = out_root or (item.parent / "PDF输出")
        target_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = unique_path(target_dir / f"{name}.pdf")
        try:
            page_count = save_image_paths_to_pdf(image_paths, pdf_path, log=log)
            generated.append(pdf_path)
            emit(log, f"生成 PDF: {pdf_path}，页数 {page_count}")
            if preview_callback and image_paths:
                preview_callback(Path(choice(image_paths)), pdf_path)
        finally:
            for temp_dir in temp_dirs:
                shutil.rmtree(temp_dir, ignore_errors=True)

    for name, images in image_groups:
        current += 1
        emit(log, f"[{current}/{total_jobs}] 处理图片: {name}")
        target_dir = out_root or (images[0].parent / "PDF输出")
        target_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = unique_path(target_dir / f"{safe_stem(name)}.pdf")
        page_count = save_image_paths_to_pdf(images, pdf_path, log=log)
        generated.append(pdf_path)
        emit(log, f"生成 PDF: {pdf_path}，页数 {page_count}")
        if preview_callback and images:
            preview_callback(Path(choice(images)), pdf_path)

    return generated


def convert_folder_items_to_pdf(
    main_folder: str | Path,
    output_dir: str | Path | None = None,
    password: str | None = None,
    archive_tool: ArchiveTool | None = None,
    log: Logger | None = None,
    preview_callback=None,
) -> list[Path]:
    folder = Path(main_folder)
    if not folder.is_dir():
        raise ValueError("请选择一个包含图片、子文件夹或压缩包的目录。")
    return convert_mixed_items_to_pdf(
        folder_paths=[folder],
        output_dir=output_dir,
        password=password,
        archive_tool=archive_tool,
        log=log,
        preview_callback=preview_callback,
    )

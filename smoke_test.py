from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image

from batch_archive_pdf.core import convert_archives_to_pdf
from common.archive_tools import find_archive_tools
from common.media_tools import find_ffmpeg, probe_subtitle_streams, run_hidden
from common.paths import ensure_runtime_dirs
from common.zhconv import convert_chinese_text, convert_text_file
from image_archive_pdf.core import convert_folder_items_to_pdf, convert_mixed_items, save_text_to_pdf
from rename_files.core import ManualRenameRule, build_manual_pairs, build_pairs, copy_by_pairs, format_manual_name
from subtitles.core import StyleOptions, modify_subtitle_or_video
from subtitles.core import modify_many
from subtitles.core import mux_subtitles_into_videos, remove_subtitle_tracks_from_videos
from zh_convert.core import convert_many as convert_zh_many
from xml_danmaku.core import DanmakuOptions, process_xml_files


def log(message: str) -> None:
    print(message)


def make_image(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (80, 120), color).save(path)


def assert_file(path: Path) -> None:
    if not path.exists() or path.stat().st_size <= 0:
        raise AssertionError(f"missing output: {path}")


def smoke_image_archive_pdf(base: Path) -> None:
    source = base / "image_archive_source"
    output = base / "image_archive_output"
    make_image(source / "book1" / "001.jpg", (255, 0, 0))
    make_image(source / "book1" / "002.jpg", (0, 255, 0))
    result = convert_folder_items_to_pdf(source, output_dir=output, log=log)
    if len(result) != 1:
        raise AssertionError(f"expected 1 PDF, got {len(result)}")
    assert_file(result[0])


def smoke_mixed_pdf_epub(base: Path) -> None:
    source = base / "mixed_source"
    output = base / "mixed_output"
    source.mkdir(parents=True, exist_ok=True)
    image = source / "001.png"
    make_image(image, (90, 120, 200))
    text = source / "note.txt"
    text.write_text("第一段文本\n\n繁體字與臺灣\n\nSecond paragraph", encoding="utf-8")
    pdf = source / "input.pdf"
    save_text_to_pdf("PDF input text", pdf, title="input")

    merged_pdf = convert_mixed_items(
        [image, text, pdf],
        output_dir=output,
        output_format="pdf",
        merge_output=True,
        output_name="merged",
        log=log,
    )
    if len(merged_pdf) != 1 or merged_pdf[0].suffix.casefold() != ".pdf":
        raise AssertionError("mixed PDF output count mismatch")
    assert_file(merged_pdf[0])
    from pypdf import PdfReader

    if len(PdfReader(str(merged_pdf[0])).pages) < 3:
        raise AssertionError("mixed PDF page count check failed")

    merged_epub = convert_mixed_items(
        [image, text, pdf],
        output_dir=output,
        output_format="epub",
        merge_output=True,
        output_name="merged_book",
        log=log,
    )
    if len(merged_epub) != 1 or merged_epub[0].suffix.casefold() != ".epub":
        raise AssertionError("mixed EPUB output count mismatch")
    assert_file(merged_epub[0])
    with zipfile.ZipFile(merged_epub[0]) as zf:
        names = set(zf.namelist())
        if "mimetype" not in names or "OEBPS/content.opf" not in names:
            raise AssertionError("epub structure check failed")

    converted_epub = convert_mixed_items(
        [text],
        output_dir=output,
        output_format="epub",
        merge_output=True,
        output_name="converted_book",
        text_conversion_mode="t2s",
        log=log,
    )
    with zipfile.ZipFile(converted_epub[0]) as zf:
        content = "\n".join(
            zf.read(name).decode("utf-8", errors="ignore")
            for name in zf.namelist()
            if name.endswith(".xhtml")
        )
        if "繁体字与台湾" not in content:
            raise AssertionError("mixed EPUB text conversion path failed")


def smoke_zh_convert(base: Path) -> None:
    source = base / "zh_convert"
    source.mkdir(parents=True, exist_ok=True)
    traditional = "繁體字與臺灣"
    simplified = "繁体字与台湾"
    if convert_chinese_text(traditional, "t2s") != simplified:
        raise AssertionError("t2s conversion failed")
    txt = source / "繁体.txt"
    txt.write_text(traditional, encoding="utf-8")
    output = convert_text_file(txt, source / "out", "t2s")
    if output.read_text(encoding="utf-8") != simplified:
        raise AssertionError("text file conversion failed")
    outputs = convert_zh_many([txt], source / "out_batch", "s2t", log=log)
    if len(outputs) != 1 or not outputs[0].exists():
        raise AssertionError("batch zh conversion failed")


def smoke_batch_archive_pdf(base: Path) -> None:
    source = base / "batch_source"
    image_dir = source / "zip_images"
    make_image(image_dir / "001.png", (0, 0, 255))
    make_image(image_dir / "002.png", (255, 255, 0))
    archive = source / "images.zip"
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w") as zf:
        for image in sorted(image_dir.glob("*.png")):
            zf.write(image, image.name)
    epub = source / "images.epub"
    with zipfile.ZipFile(epub, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")
        for image in sorted(image_dir.glob("*.png")):
            zf.write(image, f"OPS/images/{image.name}")
    output = base / "batch_output"
    result = convert_archives_to_pdf([archive, epub], output_dir=output, log=log)
    if len(result) != 2:
        raise AssertionError(f"expected 2 PDFs, got {len(result)}")
    for pdf in result:
        assert_file(pdf)


def smoke_rename_files(base: Path) -> None:
    source = base / "rename"
    source.mkdir(parents=True, exist_ok=True)
    a1 = source / "001 new.txt"
    a2 = source / "002 new.txt"
    b1 = source / "a.old"
    b2 = source / "b.old"
    for path in (a1, a2, b1, b2):
        path.write_text(path.name, encoding="utf-8")
    pairs = build_pairs([a1, a2], [b1, b2])
    result = copy_by_pairs(pairs, log=log)
    if result.success != 2:
        raise AssertionError(f"expected 2 copied renames, got {result.success}")
    if not b1.exists() or not b2.exists():
        raise AssertionError("source files should not be modified")
    if not (source / "重命名输出" / "001 new.old").exists() or not (source / "重命名输出" / "002 new.old").exists():
        raise AssertionError("renamed copies not found")

    manual_source = base / "rename_manual"
    manual_source.mkdir(parents=True, exist_ok=True)
    m1 = manual_source / "raw-a.mp4"
    m2 = manual_source / "raw-b.mp4"
    m3 = manual_source / "raw-c.mp4"
    for path in (m1, m2, m3):
        path.write_text(path.name, encoding="utf-8")
    rule = ManualRenameRule(prefix="视频", suffix="视频", number_style="ep01", start=1, step=1)
    if format_manual_name(0, rule) != "视频ep01视频":
        raise AssertionError("manual rename format failed")
    manual_pairs = build_manual_pairs([m1, m2, m3], rule)
    manual_result = copy_by_pairs(manual_pairs, manual_source / "out", log=log)
    if manual_result.success != 3:
        raise AssertionError("manual rename copy failed")
    if not (manual_source / "out" / "视频ep01视频.mp4").exists():
        raise AssertionError("manual renamed output not found")
    custom_rule = ManualRenameRule(number_style="自定义模板", custom_template="EP{num:03d}")
    if format_manual_name(4, custom_rule) != "EP005":
        raise AssertionError("custom rename template failed")


def smoke_xml_danmaku(base: Path) -> None:
    source = base / "xml"
    source.mkdir(parents=True, exist_ok=True)
    xml_path = source / "danmaku.xml"
    xml_path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<i>\n'
        '<d p="-1,1,25,16777215,0,0,0,0">negative</d>\n'
        '<d p="1,1,25,16777215,0,0,0,0">{\\c&H0000FF}繁體字</d>\n'
        "</i>\n",
        encoding="utf-8",
    )
    count = process_xml_files(
        [xml_path],
        DanmakuOptions(delete_negative=True, adjust_enabled=True, offset_seconds=2, strip_ass_tags=True, text_conversion_mode="t2s"),
        log=log,
    )
    if count != 1:
        raise AssertionError("xml process failed")
    output = source / "已修改的弹幕" / "danmaku.xml"
    assert_file(output)
    text = output.read_text(encoding="utf-8")
    if "negative" in text or "{\\c" in text or 'p="3,' not in text or "繁体字" not in text:
        raise AssertionError("xml output content check failed")


def smoke_subtitles(base: Path) -> None:
    source = base / "subtitles"
    source.mkdir(parents=True, exist_ok=True)
    srt = source / "sample.srt"
    srt.write_text(
        "1\n00:00:01,000 --> 00:00:02,500\nhello\n\n"
        "2\n00:00:03,000 --> 00:00:04,000\nworld\n",
        encoding="utf-8",
    )
    sample_ass = source / "style.ass"
    sample_ass.write_text(
        "[Script Info]\nTitle: sample\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\nYCbCr Matrix: TV.601\n\n"
        "[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
        "Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,0,2,30,30,24,1\n"
        "Style: Body,FangSong,72,&H00FFFFFF,&H000000FF,&H00112233,&H64000000,-1,0,0,0,100,100,0,0,1,4,1,2,20,20,18,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:01.00,0:00:02.00,Body,,0,0,0,,sample\n",
        encoding="utf-8",
    )
    result = modify_subtitle_or_video(
        srt,
        source / "out",
        StyleOptions(font_name="Microsoft YaHei", font_size="40", primary_color="#00FF00", use_sample=True, output_format="ass"),
        sample_path=sample_ass,
        log=log,
    )
    if len(result) != 1:
        raise AssertionError("subtitle output count mismatch")
    assert_file(result[0])
    text = result[0].read_text(encoding="utf-8")
    if "Microsoft YaHei" not in text or "&H0000FF00" not in text or "Dialogue:" not in text:
        raise AssertionError("subtitle output content check failed")

    traditional_srt = source / "traditional.srt"
    traditional_srt.write_text(
        "1\n00:00:01,000 --> 00:00:02,000\n繁體字與臺灣\n",
        encoding="utf-8",
    )
    converted_result = modify_many(
        [traditional_srt],
        source / "out_convert",
        StyleOptions(output_format="ass", text_conversion_mode="t2s"),
        log=log,
    )
    converted_text = converted_result[0].read_text(encoding="utf-8")
    if "繁体字与台湾" not in converted_text or "Dialogue:" not in converted_text:
        raise AssertionError("subtitle conversion output check failed")

    batch_result = modify_many(
        [srt],
        source / "out_srt",
        StyleOptions(output_format="srt", font_name="Arial"),
        sample_paths=[sample_ass],
        log=log,
    )
    if batch_result[0].suffix.casefold() != ".srt":
        raise AssertionError("subtitle output format override failed")
    if "-->" not in batch_result[0].read_text(encoding="utf-8"):
        raise AssertionError("srt output content check failed")

    ffmpeg = find_ffmpeg()
    if ffmpeg:
        srt2 = source / "sample2.srt"
        srt2.write_text(
            "1\n00:00:01,000 --> 00:00:02,000\nsecond track\n",
            encoding="utf-8",
        )
        video = source / "video_with_subs.mkv"
        result = run_hidden([
            str(ffmpeg),
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=160x90:d=5",
            "-i",
            str(srt),
            "-i",
            str(srt2),
            "-map",
            "0:v",
            "-map",
            "1:0",
            "-map",
            "2:0",
            "-t",
            "5",
            "-c:v",
            "mpeg4",
            "-c:s",
            "srt",
            str(video),
        ])
        if result.returncode != 0:
            raise AssertionError(result.stderr.strip() or "failed to create mkv smoke file")
        streams = probe_subtitle_streams(video)
        if not streams:
            raise AssertionError("video subtitle stream not detected")
        video_outputs = modify_many(
            [video],
            source / "out_video",
            StyleOptions(output_format="ass", all_subtitle_streams=True, use_sample=True),
            sample_paths=[sample_ass],
            log=log,
        )
        ass_outputs = [path for path in video_outputs if path.suffix.casefold() == ".ass"]
        if len(ass_outputs) < 2:
            raise AssertionError("video subtitle all-track output failed")
        ass_text = ass_outputs[0].read_text(encoding="utf-8")
        if "Style: Default,FangSong,72" not in ass_text or "PlayResX: 1920" not in ass_text or "Dialogue:" not in ass_text:
            raise AssertionError("video internal srt to styled ass failed")

        remux_outputs = modify_many(
            [video],
            source / "out_remux",
            StyleOptions(output_format="ass", all_subtitle_streams=True, use_sample=True, remux_video=True),
            sample_paths=[sample_ass],
            log=log,
        )
        remuxed = next((path for path in remux_outputs if path.suffix.casefold() == ".mkv"), None)
        if not remuxed or len(probe_subtitle_streams(remuxed)) < 2:
            raise AssertionError("video internal subtitle style remux failed")

        added_outputs = mux_subtitles_into_videos(
            [srt],
            [video],
            source / "out_add_mux",
            replace_existing_subtitles=False,
            log=log,
        )
        if len(probe_subtitle_streams(added_outputs[0])) < 3:
            raise AssertionError("video add subtitle mux failed")

        removed_outputs = remove_subtitle_tracks_from_videos(
            [video],
            source / "out_remove_mux",
            all_subtitle_streams=True,
            log=log,
        )
        if probe_subtitle_streams(removed_outputs[0]):
            raise AssertionError("video subtitle delete failed")


def main() -> None:
    runtime = ensure_runtime_dirs()
    base = runtime["temp"] / "smoke_test"
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True, exist_ok=True)

    tests = [
        ("压缩工具发现", lambda _: log(str(find_archive_tools()))),
        ("图片/压缩包批量合成 PDF", smoke_image_archive_pdf),
        ("图片/PDF/TXT 合并输出 PDF/EPUB", smoke_mixed_pdf_epub),
        ("繁简文字转换", smoke_zh_convert),
        ("多压缩包转 PDF", smoke_batch_archive_pdf),
        ("批量文件重命名", smoke_rename_files),
        ("XML 弹幕批量处理", smoke_xml_danmaku),
        ("字幕样式修改", smoke_subtitles),
    ]

    for name, test in tests:
        print(f"\n== {name} ==")
        test(base)
        print(f"PASS: {name}")

    ffmpeg = find_ffmpeg()
    print(f"\nFFmpeg: {ffmpeg or 'not found'}")
    print("\nALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureSpec:
    key: str
    category: str
    title: str
    description: str
    module: str
    frame_class: str = "FeatureFrame"
    nav_title: str | None = None


FEATURES = [
    FeatureSpec(
        key="image_archive_pdf",
        category="文档与文件",
        title="图片/压缩包/PDF/EPUB/TXT 整理",
        description="选择多种素材并合并为 PDF 或 EPUB。",
        module="image_archive_pdf.gui",
        nav_title="文档合并与整理",
    ),
    FeatureSpec(
        key="rename_files",
        category="文档与文件",
        title="批量文件重命名",
        description="B 组文件套用 A 组文件名。",
        module="rename_files.gui",
        nav_title="批量文件重命名",
    ),
    FeatureSpec(
        key="subtitles",
        category="字幕与视频",
        title="字幕样式与视频轨道",
        description="字幕样式修改、示例对齐、音轨无损提取及 MKV 封装。",
        module="subtitles.gui",
        nav_title="字幕样式与视频轨道",
    ),
    FeatureSpec(
        key="xml_danmaku",
        category="字幕与视频",
        title="XML 弹幕处理与转换",
        description="弹幕转 ASS 滚动字幕、负时间清理、时间平移与样式转换。",
        module="xml_danmaku.gui",
        nav_title="XML 弹幕处理与转换",
    ),
    FeatureSpec(
        key="zh_convert",
        category="文字工具",
        title="繁简文字转换",
        description="批量处理文本、字幕、XML 的简体/繁体互转。",
        module="zh_convert.gui",
        nav_title="繁简文字转换",
    ),
    FeatureSpec(
        key="language_tools",
        category="文字工具",
        title="字幕语言识别与简繁双语",
        description="识别单语字幕；中文单轨离线生成简体/繁体双语 ASS。",
        module="language_tools.gui",
        nav_title="字幕语言识别与双语",
    ),
]

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


FEATURES = [
    FeatureSpec(
        key="image_archive_pdf",
        category="文档与文件",
        title="图片/压缩包/PDF/EPUB/TXT 整理",
        description="选择多种素材并合并为 PDF 或 EPUB。",
        module="image_archive_pdf.gui",
    ),
    FeatureSpec(
        key="rename_files",
        category="文档与文件",
        title="批量文件重命名",
        description="B 组文件套用 A 组文件名。",
        module="rename_files.gui",
    ),
    FeatureSpec(
        key="subtitles",
        category="字幕与视频",
        title="字幕样式与视频轨道",
        description="字幕样式修改、示例对齐、轨道检测及 MKV 封装。",
        module="subtitles.gui",
    ),
    FeatureSpec(
        key="xml_danmaku",
        category="字幕与视频",
        title="XML 弹幕批量处理",
        description="删除负时间、平移时间、清理 ASS 样式。",
        module="xml_danmaku.gui",
    ),
    FeatureSpec(
        key="zh_convert",
        category="文字工具",
        title="繁简文字转换",
        description="批量处理文本、字幕、XML 的简体/繁体互转。",
        module="zh_convert.gui",
    ),
]

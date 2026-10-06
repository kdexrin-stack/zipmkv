from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk

from PIL import Image, ImageTk

from common.file_selection import InputFileCollection, resolve_input_snapshot
from common.gui_base import LogFrame, ToolFrame, bind_listbox_delete_menu
from common.media_tools import describe_ffmpeg, probe_stream_lines, probe_subtitle_streams
from common.paths import ensure_runtime_dirs
from common.theme import COLORS
from common.ui_components import SubtitleTimeline
from common.zhconv import MODES, mode_key_from_label, mode_label

from .core import (
    BilingualOptions,
    SUBTITLE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    StyleOptions,
    create_ass_preview_image,
    is_subtitle,
    is_video,
    modify_many,
    mux_subtitles_into_videos,
    remove_subtitle_tracks_from_videos,
    extract_audio_from_videos,
    build_bilingual_from_inputs,
    load_sample_style_texts,
    merge_sample_texts,
    read_subtitle_cues,
)


TARGET_EXTENSIONS = SUBTITLE_EXTENSIONS | VIDEO_EXTENSIONS
VIDEO_ACTION_MODIFY = "修改字幕后封装"
VIDEO_ACTION_ADD = "直接添加字幕"
VIDEO_ACTION_REMOVE = "删除视频字幕轨"
VIDEO_ACTION_EXTRACT_AUDIO = "无损提取音频轨"
VIDEO_ACTION_BILINGUAL = "提取/合成双语字幕"


class FeatureFrame(ToolFrame):
    title = "字幕样式修改"
    description = "修改单独字幕文件，或提取视频内封字幕后修改样式。"

    def __init__(self, master):
        super().__init__(master)
        self.target_collection = InputFileCollection(TARGET_EXTENSIONS)
        self.sample_collection = InputFileCollection(TARGET_EXTENSIONS)
        self.video_source_collection = InputFileCollection(TARGET_EXTENSIONS)
        self.video_sample_collection = InputFileCollection(TARGET_EXTENSIONS)
        self.mux_video_collection = InputFileCollection(VIDEO_EXTENSIONS)
        self.output_var = tk.StringVar()
        self.video_output_var = tk.StringVar()
        self.output_format_var = tk.StringVar(value="same")
        self.text_conversion_var = tk.StringVar(value="不转换")
        self.video_action_var = tk.StringVar(value=VIDEO_ACTION_MODIFY)
        self.video_source_var = tk.StringVar(value="尚未选择字幕来源")
        self.replace_video_subtitles_var = tk.BooleanVar(value=False)
        self.stream_var = tk.IntVar(value=0)
        self.all_tracks_var = tk.BooleanVar(value=True)
        self.style_mode_var = tk.StringVar(value="manual")
        self.safe_var = tk.BooleanVar(value=True)
        self.remux_var = tk.BooleanVar(value=False)
        self.bilingual_package_var = tk.BooleanVar(value=False)
        self.bilingual_keep_unmatched_var = tk.BooleanVar(value=True)
        self.bilingual_flatten_var = tk.BooleanVar(value=True)
        self.bilingual_reference_mode_var = tk.StringVar(value="参考文件优先")
        self.bilingual_scale_var = tk.StringVar(value="0.78")
        self.bilingual_tolerance_var = tk.StringVar(value="1.2")
        self.bilingual_single_mode_var = tk.StringVar(value="检测中文后自动生成简繁双语")
        self.bold_var = tk.BooleanVar(value=False)
        self.italic_var = tk.BooleanVar(value=False)
        self.apply_bold_var = tk.BooleanVar(value=False)
        self.apply_italic_var = tk.BooleanVar(value=False)
        self.font_var = tk.StringVar()
        self.size_var = tk.StringVar()
        self.primary_var = tk.StringVar()
        self.outline_color_var = tk.StringVar()
        self.align_var = tk.StringVar()
        self.margin_l_var = tk.StringVar()
        self.margin_r_var = tk.StringVar()
        self.margin_v_var = tk.StringVar()
        self.outline_var = tk.StringVar()
        self.shadow_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.preview_var = tk.StringVar(value="生成后显示 ASS/SSA 效果示例")
        self.preview_cue_var = tk.StringVar(value="生成字幕后可点击时间轴查看实际事件")
        self.preview_image = None
        self.preview_cues: list[tuple[str, str, str]] = []
        self.manual_widgets: list[tk.Widget] = []
        self.sample_widgets: list[tk.Widget] = []
        self.stream_spins: list[ttk.Spinbox] = []
        self.color_swatches: list[tuple[tk.StringVar, tk.Label]] = []
        self._build()
        self.refresh_color_swatches()
        self.refresh_status()
        self.update_option_states()
        self.update_track_state()

    @property
    def target_files(self) -> list[str]:
        return self.target_collection.files

    @target_files.setter
    def target_files(self, value: list[str]) -> None:
        self.target_collection.files = list(value)
        self.target_collection.refresh_display_items()

    @property
    def target_folders(self) -> list[str]:
        return self.target_collection.folders

    @target_folders.setter
    def target_folders(self, value: list[str]) -> None:
        self.target_collection.folders = list(value)
        self.target_collection.refresh_display_items()

    @property
    def sample_files(self) -> list[str]:
        return self.sample_collection.files

    @sample_files.setter
    def sample_files(self, value: list[str]) -> None:
        self.sample_collection.files = list(value)
        self.sample_collection.refresh_display_items()

    @property
    def sample_folders(self) -> list[str]:
        return self.sample_collection.folders

    @sample_folders.setter
    def sample_folders(self, value: list[str]) -> None:
        self.sample_collection.folders = list(value)
        self.sample_collection.refresh_display_items()

    @property
    def video_source_files(self) -> list[str]:
        return self.video_source_collection.files

    @video_source_files.setter
    def video_source_files(self, value: list[str]) -> None:
        self.video_source_collection.files = list(value)
        self.video_source_collection.refresh_display_items()

    @property
    def video_source_folders(self) -> list[str]:
        return self.video_source_collection.folders

    @video_source_folders.setter
    def video_source_folders(self, value: list[str]) -> None:
        self.video_source_collection.folders = list(value)
        self.video_source_collection.refresh_display_items()

    @property
    def video_sample_files(self) -> list[str]:
        return self.video_sample_collection.files

    @video_sample_files.setter
    def video_sample_files(self, value: list[str]) -> None:
        self.video_sample_collection.files = list(value)
        self.video_sample_collection.refresh_display_items()

    @property
    def video_sample_folders(self) -> list[str]:
        return self.video_sample_collection.folders

    @video_sample_folders.setter
    def video_sample_folders(self, value: list[str]) -> None:
        self.video_sample_collection.folders = list(value)
        self.video_sample_collection.refresh_display_items()

    @property
    def mux_video_files(self) -> list[str]:
        return self.mux_video_collection.files

    @mux_video_files.setter
    def mux_video_files(self, value: list[str]) -> None:
        self.mux_video_collection.files = list(value)
        self.mux_video_collection.refresh_display_items()

    @property
    def mux_video_folders(self) -> list[str]:
        return self.mux_video_collection.folders

    @mux_video_folders.setter
    def mux_video_folders(self, value: list[str]) -> None:
        self.mux_video_collection.folders = list(value)
        self.mux_video_collection.refresh_display_items()

    def _build(self) -> None:
        paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)
        top = ttk.Frame(paned)
        bottom = ttk.Frame(paned)
        paned.add(top, weight=4)
        paned.add(bottom, weight=2)

        def balance_panes(event) -> None:
            if event.height >= 480:
                paned.sashpos(0, int(event.height * 0.56))

        paned.bind("<Configure>", balance_panes)

        self.notebook = ttk.Notebook(top, style="Feature.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.style_tab = ttk.Frame(self.notebook, style="Surface.TFrame")
        self.video_tab = ttk.Frame(self.notebook, style="Surface.TFrame")
        self.notebook.add(self.style_tab, text="字幕样式")
        self.notebook.add(self.video_tab, text="视频轨道与封装")
        self.notebook.bind("<<NotebookTabChanged>>", self._on_workspace_changed)

        self._build_style_tab()
        self._build_video_tab()
        self._build_result_panel(bottom)
        self._on_workspace_changed()

    def _build_style_tab(self) -> None:
        body = self._create_scroll_body(self.style_tab)

        file_frame = ttk.LabelFrame(body, text="Step 1 · 📁 输入目标与示例", style="Card.TLabelframe", padding=6)
        file_frame.pack(fill=tk.X, pady=(2, 4))
        file_frame.columnconfigure(1, weight=1)

        target_buttons = ttk.Frame(file_frame)
        target_buttons.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=2)
        ttk.Label(target_buttons, text="目标字幕/视频").pack(side=tk.LEFT)
        ttk.Button(target_buttons, text="+ 选择文件", command=self.choose_targets).pack(side=tk.LEFT, padx=4)
        ttk.Button(target_buttons, text="📁 文件夹", command=self.choose_target_folder).pack(side=tk.LEFT)
        ttk.Button(target_buttons, text="清空", command=self.clear_targets).pack(side=tk.LEFT, padx=4)
        self.target_list = tk.Listbox(file_frame, height=2, exportselection=False)
        self.target_list.grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=2)
        bind_listbox_delete_menu(self.target_list, self.delete_selected_targets, self.clear_targets)

        sample_buttons = ttk.Frame(file_frame)
        sample_buttons.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=2)
        ttk.Label(sample_buttons, text="示例样式源").pack(side=tk.LEFT)
        ttk.Button(sample_buttons, text="+ 选择示例", command=self.choose_samples).pack(side=tk.LEFT, padx=4)
        ttk.Button(sample_buttons, text="📁 文件夹", command=self.choose_sample_folder).pack(side=tk.LEFT)
        ttk.Button(sample_buttons, text="清空", command=self.clear_samples).pack(side=tk.LEFT, padx=4)
        self.sample_list = tk.Listbox(file_frame, height=2, exportselection=False)
        self.sample_list.grid(row=3, column=0, columnspan=3, sticky=tk.EW, pady=2)
        bind_listbox_delete_menu(self.sample_list, self.delete_selected_samples, self.clear_samples)

        ttk.Label(file_frame, text="输出目录").grid(row=4, column=0, sticky=tk.W, pady=2)
        ttk.Entry(file_frame, textvariable=self.output_var).grid(row=4, column=1, sticky=tk.EW, padx=4)
        ttk.Button(file_frame, text="浏览", command=self.choose_output).grid(row=4, column=2)

        option_frame = ttk.LabelFrame(body, text="Step 2 · ⚙️ 样式来源与转换规则", style="Card.TLabelframe", padding=6)
        option_frame.pack(fill=tk.X, pady=(2, 4))
        ttk.Radiobutton(
            option_frame,
            text="手动参数",
            value="manual",
            variable=self.style_mode_var,
            command=self.update_option_states,
        ).grid(row=0, column=0, sticky=tk.W, padx=(0, 18))
        ttk.Radiobutton(
            option_frame,
            text="示例样式对齐",
            value="sample",
            variable=self.style_mode_var,
            command=self.update_option_states,
        ).grid(row=0, column=1, sticky=tk.W, padx=(0, 18))
        ttk.Radiobutton(
            option_frame,
            text="示例样式 + 手动覆盖",
            value="sample_manual",
            variable=self.style_mode_var,
            command=self.update_option_states,
        ).grid(row=0, column=2, sticky=tk.W)

        safe_check = ttk.Checkbutton(option_frame, text="双语示例对单语目标时保留目标字号/边距", variable=self.safe_var)
        safe_check.grid(row=1, column=0, columnspan=2, sticky=tk.W)
        self.sample_widgets.append(safe_check)

        ttk.Label(option_frame, text="输出格式").grid(row=2, column=0, sticky=tk.W, pady=4)
        ttk.Combobox(
            option_frame,
            textvariable=self.output_format_var,
            values=["same", "ass", "srt", "vtt"],
            width=10,
            state="readonly",
        ).grid(row=2, column=1, sticky=tk.W)
        ttk.Label(option_frame, text="文字繁简").grid(row=2, column=2, sticky=tk.E, padx=(20, 4))
        ttk.Combobox(
            option_frame,
            textvariable=self.text_conversion_var,
            values=[mode.label for mode in MODES],
            width=16,
            state="readonly",
        ).grid(row=2, column=3, sticky=tk.W)

        ttk.Checkbutton(option_frame, text="视频目标处理后重新封装为 MKV", variable=self.remux_var).grid(row=3, column=0, sticky=tk.W)
        all_tracks_check = ttk.Checkbutton(
            option_frame,
            text="视频字幕轨道：全部处理",
            variable=self.all_tracks_var,
            command=self.update_track_state,
        )
        all_tracks_check.grid(row=3, column=1, sticky=tk.W)
        ttk.Label(option_frame, text="单轨序号").grid(row=3, column=2, sticky=tk.E, padx=(20, 4))
        stream_spin = ttk.Spinbox(option_frame, from_=0, to=20, width=5, textvariable=self.stream_var)
        stream_spin.grid(row=3, column=3, sticky=tk.W)
        self.stream_spins.append(stream_spin)

        style_frame = ttk.LabelFrame(body, text="3. 手动参数（留空则不覆盖）", padding=8)
        style_frame.pack(fill=tk.X, pady=6)
        fields = [
            ("字体", self.font_var, False),
            ("字号", self.size_var, False),
            ("主颜色", self.primary_var, True),
            ("描边颜色", self.outline_color_var, True),
            ("对齐 1-9", self.align_var, False),
            ("左边距", self.margin_l_var, False),
            ("右边距", self.margin_r_var, False),
            ("垂直边距", self.margin_v_var, False),
            ("描边", self.outline_var, False),
            ("阴影", self.shadow_var, False),
        ]
        for index, (label, var, is_color) in enumerate(fields):
            row = index // 2
            col = (index % 2) * 2
            label_widget = ttk.Label(style_frame, text=label)
            label_widget.grid(row=row, column=col, sticky=tk.W, pady=3)
            control = ttk.Frame(style_frame)
            control.grid(row=row, column=col + 1, sticky=tk.EW, padx=5)
            entry_widget = ttk.Entry(control, textvariable=var, width=18 if is_color else 22)
            entry_widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.manual_widgets.extend([label_widget, entry_widget])
            if is_color:
                swatch = tk.Label(
                    control,
                    width=3,
                    relief=tk.FLAT,
                    bd=0,
                    highlightthickness=1,
                    highlightbackground=COLORS["border"],
                    bg="#FFFFFF",
                )
                swatch.pack(side=tk.LEFT, padx=(5, 3))
                button = ttk.Button(control, text="拾取", width=5, command=lambda v=var: self.choose_color(v))
                button.pack(side=tk.LEFT)
                var.trace_add("write", lambda *_args, v=var: self.refresh_color_swatches(v))
                self.color_swatches.append((var, swatch))
                self.manual_widgets.extend([swatch, button])
        for row, col, text, var in [
            (5, 0, "覆盖粗体", self.apply_bold_var),
            (5, 1, "粗体开启", self.bold_var),
            (5, 2, "覆盖斜体", self.apply_italic_var),
            (5, 3, "斜体开启", self.italic_var),
        ]:
            widget = ttk.Checkbutton(style_frame, text=text, variable=var)
            widget.grid(row=row, column=col, sticky=tk.W)
            self.manual_widgets.append(widget)

    def _build_video_tab(self) -> None:
        body = self._create_scroll_body(self.video_tab)
        ttk.Label(body, text="单独执行轨道检测、字幕追加、样式修改后封装或字幕轨删除。", style="Muted.TLabel").pack(anchor=tk.W)

        operation_frame = ttk.LabelFrame(body, text="1. 视频操作", padding=8)
        operation_frame.pack(fill=tk.X, pady=8)
        operation_frame.columnconfigure(1, weight=1)
        ttk.Label(operation_frame, text="操作").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Combobox(
            operation_frame,
            textvariable=self.video_action_var,
            values=[
                VIDEO_ACTION_MODIFY,
                VIDEO_ACTION_ADD,
                VIDEO_ACTION_BILINGUAL,
                VIDEO_ACTION_REMOVE,
                VIDEO_ACTION_EXTRACT_AUDIO,
            ],
            state="readonly",
            width=20,
        ).grid(row=0, column=1, sticky=tk.W, padx=6)
        ttk.Checkbutton(
            operation_frame,
            text="封装时替换原字幕轨",
            variable=self.replace_video_subtitles_var,
        ).grid(row=0, column=2, sticky=tk.W)

        source_frame = ttk.LabelFrame(body, text="2. 字幕来源", padding=8)
        source_frame.pack(fill=tk.X, pady=6)
        source_frame.columnconfigure(0, weight=1)
        source_buttons = ttk.Frame(source_frame)
        source_buttons.grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Button(source_buttons, text="选择单/多个字幕或视频", command=self.choose_video_sources).pack(side=tk.LEFT)
        ttk.Button(source_buttons, text="选择文件夹扫描", command=self.choose_video_source_folder).pack(side=tk.LEFT, padx=6)
        ttk.Label(source_buttons, textvariable=self.video_source_var, style="Muted.TLabel").pack(side=tk.LEFT, padx=8)
        self.video_source_list = tk.Listbox(source_frame, height=4, exportselection=False)
        self.video_source_list.grid(row=1, column=0, sticky=tk.EW, pady=4)
        bind_listbox_delete_menu(
            self.video_source_list,
            self.delete_selected_video_sources,
            self.clear_video_sources,
        )

        video_sample_buttons = ttk.Frame(source_frame)
        video_sample_buttons.grid(row=2, column=0, sticky=tk.W, pady=(8, 4))
        ttk.Label(video_sample_buttons, text="示例样式（可选）").pack(side=tk.LEFT)
        ttk.Button(video_sample_buttons, text="选择单/多个", command=self.choose_video_samples).pack(side=tk.LEFT, padx=6)
        ttk.Button(video_sample_buttons, text="选择文件夹", command=self.choose_video_sample_folder).pack(side=tk.LEFT)
        self.video_sample_list = tk.Listbox(source_frame, height=3, exportselection=False)
        self.video_sample_list.grid(row=3, column=0, sticky=tk.EW, pady=4)
        bind_listbox_delete_menu(
            self.video_sample_list,
            self.delete_selected_video_samples,
            self.clear_video_samples,
        )

        mux_frame = ttk.LabelFrame(body, text="3. 目标视频", padding=8)
        mux_frame.pack(fill=tk.X, pady=6)
        mux_frame.columnconfigure(0, weight=1)
        video_buttons = ttk.Frame(mux_frame)
        video_buttons.grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Button(video_buttons, text="选择单/多个视频", command=self.choose_mux_videos).pack(side=tk.LEFT)
        ttk.Button(video_buttons, text="选择文件夹扫描", command=self.choose_mux_video_folder).pack(side=tk.LEFT, padx=6)
        self.mux_video_list = tk.Listbox(mux_frame, height=6, exportselection=False)
        self.mux_video_list.grid(row=1, column=0, sticky=tk.EW, pady=4)
        bind_listbox_delete_menu(self.mux_video_list, self.delete_selected_mux_videos, self.clear_mux_videos)

        track_frame = ttk.LabelFrame(body, text="4. 输出与轨道范围", padding=8)
        track_frame.pack(fill=tk.X, pady=6)
        track_frame.columnconfigure(1, weight=1)
        ttk.Label(track_frame, text="输出目录").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Entry(track_frame, textvariable=self.video_output_var).grid(row=0, column=1, sticky=tk.EW, padx=6)
        ttk.Button(track_frame, text="选择", command=self.choose_video_output).grid(row=0, column=2)
        ttk.Checkbutton(
            track_frame,
            text="全部字幕轨道",
            variable=self.all_tracks_var,
            command=self.update_track_state,
        ).grid(row=1, column=0, sticky=tk.W, pady=4)
        track_controls = ttk.Frame(track_frame)
        track_controls.grid(row=1, column=1, columnspan=2, sticky=tk.W)
        ttk.Label(track_controls, text="单轨序号").pack(side=tk.LEFT, padx=(0, 5))
        stream_spin = ttk.Spinbox(track_controls, from_=0, to=20, width=5, textvariable=self.stream_var)
        stream_spin.pack(side=tk.LEFT)
        self.stream_spins.append(stream_spin)
        ttk.Label(track_controls, text="所有结果输出为新 MKV，源视频保持不变。", style="Muted.TLabel").pack(side=tk.LEFT, padx=20)

        bilingual_frame = ttk.LabelFrame(body, text="5. 双语字幕合成（选择“提取/合成双语字幕”后生效）", padding=8)
        bilingual_frame.pack(fill=tk.X, pady=6)
        bilingual_frame.columnconfigure(1, weight=1)
        ttk.Label(bilingual_frame, text="样式来源").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Combobox(
            bilingual_frame,
            textvariable=self.bilingual_reference_mode_var,
            values=["参考文件优先", "内置清晰白字黑边"],
            state="readonly",
            width=20,
        ).grid(row=0, column=1, sticky=tk.W, padx=6)
        ttk.Label(
            bilingual_frame,
            text="示例区可放双语或单语 ASS/SRT/视频；单语示例只提供样式。",
            style="Muted.TLabel",
        ).grid(row=0, column=2, sticky=tk.W, padx=8)

        ttk.Label(bilingual_frame, text="第二字幕字号比例").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Entry(bilingual_frame, textvariable=self.bilingual_scale_var, width=8).grid(row=1, column=1, sticky=tk.W, padx=6)
        ttk.Label(bilingual_frame, text="建议 0.70-0.85；第二字幕固定在下方且小于第一字幕。", style="Muted.TLabel").grid(
            row=1, column=2, sticky=tk.W, padx=8
        )
        ttk.Label(bilingual_frame, text="时间匹配容差（秒）").grid(row=2, column=0, sticky=tk.W, pady=4)
        ttk.Entry(bilingual_frame, textvariable=self.bilingual_tolerance_var, width=8).grid(row=2, column=1, sticky=tk.W, padx=6)
        ttk.Label(bilingual_frame, text="先按重叠时间匹配，再按最近开始时间匹配。", style="Muted.TLabel").grid(
            row=2, column=2, sticky=tk.W, padx=8
        )
        ttk.Label(bilingual_frame, text="只有单轨时").grid(row=3, column=0, sticky=tk.W, pady=4)
        ttk.Combobox(
            bilingual_frame,
            textvariable=self.bilingual_single_mode_var,
            values=[
                "检测中文后自动生成简繁双语",
                "缺少第二轨时仅保留原文",
                "强制简体 -> 繁体",
                "强制繁体 -> 简体",
            ],
            state="readonly",
            width=24,
        ).grid(row=3, column=1, sticky=tk.W, padx=6)
        ttk.Label(
            bilingual_frame,
            text="仅中文支持内置离线互转；日文/英文等只识别并保留原文。",
            style="Muted.TLabel",
        ).grid(row=3, column=2, sticky=tk.W, padx=8)
        ttk.Checkbutton(
            bilingual_frame,
            text="原字幕中的双行文本合并为单行（避免四行叠加）",
            variable=self.bilingual_flatten_var,
        ).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=3)
        ttk.Checkbutton(
            bilingual_frame,
            text="保留未匹配字幕事件",
            variable=self.bilingual_keep_unmatched_var,
        ).grid(row=4, column=2, sticky=tk.W, padx=8)
        ttk.Checkbutton(
            bilingual_frame,
            text="双语 ASS 同时封装到新 MKV（目标视频为空时使用来源视频）",
            variable=self.bilingual_package_var,
        ).grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=3)

        ttk.Label(body, textvariable=self.status_var, style="Muted.TLabel", wraplength=900).pack(fill=tk.X, pady=8)

    def _build_result_panel(self, bottom: ttk.Frame) -> None:
        action_row = ttk.Frame(bottom, style="Surface.TFrame")
        action_row.pack(fill=tk.X, pady=(6, 8))
        self.primary_action_var = tk.StringVar(value="▶ 开始修改字幕")
        self.primary_action_button = ttk.Button(action_row, textvariable=self.primary_action_var, style="Primary.TButton")
        self.primary_action_button.configure(command=self._run_active_workspace)
        self.primary_action_button.pack(side=tk.LEFT)
        ttk.Button(action_row, text="📂 打开输出目录", style="OpenDir.TButton", command=self.reveal_output_folder).pack(side=tk.LEFT, padx=10)
        self.probe_button = ttk.Button(
            action_row,
            text="检测字幕源/轨道",
            command=lambda: self.probe_all_videos(self.probe_button),
        )
        self.probe_button.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(action_row, text="清空日志", command=self.log_frame.clear).pack(side=tk.RIGHT)

        result_panes = ttk.PanedWindow(bottom, orient=tk.HORIZONTAL)
        result_panes.pack(fill=tk.BOTH, expand=True)
        log_area = ttk.LabelFrame(result_panes, text="日志", padding=6)
        self.log_frame.destroy()
        self.log_frame = LogFrame(log_area)
        self.log_frame.text.configure(height=9)
        self.log_frame.pack(fill=tk.BOTH, expand=True)

        preview_area = ttk.LabelFrame(result_panes, text="效果示例", padding=6)
        preview_area.columnconfigure(0, weight=1)
        preview_area.rowconfigure(0, weight=1)
        self.preview_label = ttk.Label(preview_area, text="暂无预览", anchor=tk.CENTER, width=36)
        self.preview_label.grid(row=0, column=0, sticky=tk.NSEW, pady=(0, 5))
        self.preview_timeline = SubtitleTimeline(preview_area, self._select_preview_cue)
        self.preview_timeline.grid(row=1, column=0, sticky=tk.EW, pady=(0, 5))
        ttk.Label(
            preview_area,
            textvariable=self.preview_cue_var,
            style="Task.TLabel",
            wraplength=360,
            justify=tk.LEFT,
        ).grid(row=2, column=0, sticky=tk.EW, pady=(0, 3))
        ttk.Label(
            preview_area,
            textvariable=self.preview_var,
            wraplength=360,
            style="Muted.TLabel",
        ).grid(row=3, column=0, sticky=tk.EW)
        result_panes.add(log_area, weight=3)
        result_panes.add(preview_area, weight=1)

    def _on_workspace_changed(self, _event=None) -> None:
        if not hasattr(self, "primary_action_var"):
            return
        if self.notebook.index("current") == 0:
            self.primary_action_var.set("▶ 开始修改字幕")
        else:
            self.primary_action_var.set("▶ 执行视频操作")

    def _run_active_workspace(self) -> None:
        if self.notebook.index("current") == 0:
            self.start_style(self.primary_action_button)
        else:
            self.start_video(self.primary_action_button)

    def _create_scroll_body(self, master) -> ttk.Frame:
        outer = ttk.Frame(master)
        outer.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(outer, highlightthickness=0, bg=COLORS["surface"])
        scrollbar = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        body = ttk.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=body, anchor=tk.NW)

        def resize_body(event) -> None:
            canvas.itemconfigure(window_id, width=event.width)

        def update_region(_event=None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_mousewheel(event) -> None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<Configure>", resize_body)
        body.bind("<Configure>", update_region)
        canvas.bind("<Enter>", lambda _event: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))
        return body

    def _entry_color_to_hex(self, value: str) -> str:
        value = value.strip()
        if not value:
            return ""
        raw = value[1:] if value.startswith("#") else value
        if len(raw) == 6 and all(char in "0123456789abcdefABCDEF" for char in raw):
            return "#" + raw.upper()
        if value.upper().startswith("&H"):
            hex_part = value[2:].strip().upper()
            if len(hex_part) == 8:
                hex_part = hex_part[2:]
            if len(hex_part) == 6 and all(char in "0123456789ABCDEF" for char in hex_part):
                bb, gg, rr = hex_part[0:2], hex_part[2:4], hex_part[4:6]
                return f"#{rr}{gg}{bb}"
        return ""

    def refresh_color_swatches(self, changed_var: tk.StringVar | None = None) -> None:
        for var, swatch in self.color_swatches:
            if changed_var is not None and var is not changed_var:
                continue
            color = self._entry_color_to_hex(var.get())
            if color:
                swatch.configure(bg=color, text="")
            else:
                swatch.configure(bg="#FFFFFF", text=" ")

    def choose_color(self, var: tk.StringVar) -> None:
        initial = self._entry_color_to_hex(var.get()) or "#FFFFFF"
        _rgb, color = colorchooser.askcolor(color=initial, title="选择字幕颜色")
        if color:
            var.set(color.upper())
            self.refresh_color_swatches(var)

    def has_manual_overrides(self) -> bool:
        text_vars = [
            self.font_var,
            self.size_var,
            self.primary_var,
            self.outline_color_var,
            self.align_var,
            self.margin_l_var,
            self.margin_r_var,
            self.margin_v_var,
            self.outline_var,
            self.shadow_var,
        ]
        return any(var.get().strip() for var in text_vars) or self.apply_bold_var.get() or self.apply_italic_var.get()

    def update_option_states(self) -> None:
        mode = self.style_mode_var.get()
        manual_state = tk.NORMAL if mode in {"manual", "sample_manual"} else tk.DISABLED
        sample_state = tk.NORMAL if mode in {"sample", "sample_manual"} else tk.DISABLED
        for widget in self.manual_widgets:
            widget.configure(state=manual_state)
        for widget in self.sample_widgets:
            widget.configure(state=sample_state)

    def update_track_state(self) -> None:
        state = tk.DISABLED if self.all_tracks_var.get() else tk.NORMAL
        for stream_spin in self.stream_spins:
            stream_spin.configure(state=state)

    def refresh_status(self) -> None:
        description = describe_ffmpeg()
        if description != "未检测到 FFmpeg":
            self.status_var.set(f"FFmpeg 可用于视频内封字幕。{description}")
        else:
            self.status_var.set("未检测到 FFmpeg；仍可处理单独字幕文件，视频内封字幕需要 FFmpeg。")

    def _current_targets(self) -> list[Path]:
        return self.target_collection.resolve_files()

    def _current_samples(self) -> list[Path]:
        return self.sample_collection.resolve_files()

    def _current_video_sources(self) -> list[Path]:
        return self.video_source_collection.resolve_files()

    def _current_video_samples(self) -> list[Path]:
        return self.video_sample_collection.resolve_files()

    def _current_mux_videos(self) -> list[Path]:
        return self.mux_video_collection.resolve_files()

    def choose_targets(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择目标字幕或视频",
            filetypes=[("字幕/视频", "*.ass *.ssa *.srt *.vtt *.skrt *.mkv *.mp4 *.mov *.avi *.wmv *.flv *.webm *.m4v"), ("所有文件", "*.*")],
        )
        if paths:
            self.target_collection.add_files(list(paths))
            self.refresh_lists()

    def choose_target_folder(self) -> None:
        path = filedialog.askdirectory(title="选择包含目标字幕/视频的文件夹")
        if path:
            self.target_collection.add_folder(path)
            self.refresh_lists()

    def choose_samples(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择示例字幕或视频",
            filetypes=[("字幕/视频", "*.ass *.ssa *.srt *.vtt *.skrt *.mkv *.mp4 *.mov *.avi *.wmv *.flv *.webm *.m4v"), ("所有文件", "*.*")],
        )
        if paths:
            self.sample_collection.add_files(list(paths))
            if self.style_mode_var.get() == "manual":
                self.style_mode_var.set("sample_manual" if self.has_manual_overrides() else "sample")
                self.update_option_states()
            self.refresh_lists()

    def choose_sample_folder(self) -> None:
        path = filedialog.askdirectory(title="选择包含示例字幕/视频的文件夹")
        if path:
            self.sample_collection.add_folder(path)
            if self.style_mode_var.get() == "manual":
                self.style_mode_var.set("sample_manual" if self.has_manual_overrides() else "sample")
                self.update_option_states()
            self.refresh_lists()

    def refresh_lists(self) -> None:
        self.target_list.delete(0, tk.END)
        for text, _ in self.target_collection.display_items:
            self.target_list.insert(tk.END, text)

        self.sample_list.delete(0, tk.END)
        for text, _ in self.sample_collection.display_items:
            self.sample_list.insert(tk.END, text)

        self.video_source_list.delete(0, tk.END)
        for text, _ in self.video_source_collection.display_items:
            self.video_source_list.insert(tk.END, text)
        video_sources = self.video_source_collection.direct_files()
        video_source_folders = self.video_source_collection.visible_folders()
        subtitle_count = sum(1 for path in video_sources if is_subtitle(path))
        video_count = sum(1 for path in video_sources if is_video(path))
        if video_sources or video_source_folders:
            detail = f"直接文件 {len(video_sources)} 个（字幕 {subtitle_count} / 视频 {video_count}）"
            if video_source_folders:
                detail += f" + 文件夹 {len(video_source_folders)} 个（执行时扫描）"
            self.video_source_var.set("已选 " + detail)
        else:
            self.video_source_var.set("尚未选择字幕来源")

        self.video_sample_list.delete(0, tk.END)
        for text, _ in self.video_sample_collection.display_items:
            self.video_sample_list.insert(tk.END, text)

        self.mux_video_list.delete(0, tk.END)
        for text, _ in self.mux_video_collection.display_items:
            self.mux_video_list.insert(tk.END, text)

    def delete_selected_targets(self) -> None:
        self.target_collection.remove_indices(list(self.target_list.curselection()))
        self.refresh_lists()

    def delete_selected_samples(self) -> None:
        self.sample_collection.remove_indices(list(self.sample_list.curselection()))
        self.refresh_lists()

    def delete_selected_video_sources(self) -> None:
        self.video_source_collection.remove_indices(list(self.video_source_list.curselection()))
        self.refresh_lists()

    def delete_selected_video_samples(self) -> None:
        self.video_sample_collection.remove_indices(list(self.video_sample_list.curselection()))
        self.refresh_lists()

    def delete_selected_mux_videos(self) -> None:
        self.mux_video_collection.remove_indices(list(self.mux_video_list.curselection()))
        self.refresh_lists()

    def clear_targets(self) -> None:
        self.target_collection.clear()
        self.refresh_lists()

    def clear_samples(self) -> None:
        self.sample_collection.clear()
        self.refresh_lists()

    def clear_video_sources(self) -> None:
        self.video_source_collection.clear()
        self.refresh_lists()

    def clear_video_samples(self) -> None:
        self.video_sample_collection.clear()
        self.refresh_lists()

    def clear_mux_videos(self) -> None:
        self.mux_video_collection.clear()
        self.refresh_lists()

    def choose_output(self) -> None:
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_var.set(path)

    def choose_video_sources(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择视频页字幕来源",
            filetypes=[("字幕/视频", "*.ass *.ssa *.srt *.vtt *.skrt *.mkv *.mp4 *.mov *.avi *.wmv *.flv *.webm *.m4v"), ("所有文件", "*.*")],
        )
        if paths:
            self.video_source_collection.add_files(list(paths))
            self.refresh_lists()

    def choose_video_source_folder(self) -> None:
        path = filedialog.askdirectory(title="选择包含字幕来源的文件夹")
        if path:
            self.video_source_collection.add_folder(path)
            self.refresh_lists()

    def choose_video_samples(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择视频页示例字幕或视频",
            filetypes=[("字幕/视频", "*.ass *.ssa *.srt *.vtt *.skrt *.mkv *.mp4 *.mov *.avi *.wmv *.flv *.webm *.m4v"), ("所有文件", "*.*")],
        )
        if paths:
            self.video_sample_collection.add_files(list(paths))
            if self.style_mode_var.get() == "manual":
                self.style_mode_var.set("sample_manual" if self.has_manual_overrides() else "sample")
                self.update_option_states()
            self.refresh_lists()

    def choose_video_sample_folder(self) -> None:
        path = filedialog.askdirectory(title="选择包含视频页示例的文件夹")
        if path:
            self.video_sample_collection.add_folder(path)
            if self.style_mode_var.get() == "manual":
                self.style_mode_var.set("sample_manual" if self.has_manual_overrides() else "sample")
                self.update_option_states()
            self.refresh_lists()

    def choose_video_output(self) -> None:
        path = filedialog.askdirectory(title="选择视频操作输出目录")
        if path:
            self.video_output_var.set(path)

    def choose_mux_videos(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择要封装/删除字幕的视频",
            filetypes=[("视频", "*.mkv *.mp4 *.mov *.avi *.wmv *.flv *.webm *.m4v"), ("所有文件", "*.*")],
        )
        if paths:
            self.mux_video_collection.add_files(list(paths))
            self.refresh_lists()

    def choose_mux_video_folder(self) -> None:
        path = filedialog.askdirectory(title="选择包含视频的文件夹")
        if path:
            self.mux_video_collection.add_folder(path)
            self.refresh_lists()

    def _probe_video_group(self, label: str, paths: list[Path]) -> int:
        subtitle_files = [path for path in paths if path.suffix.casefold() in SUBTITLE_EXTENSIONS]
        videos = [path for path in paths if path.suffix.casefold() in VIDEO_EXTENSIONS]
        subtitle_source_count = len(subtitle_files)
        if subtitle_files:
            self.log_frame.write(f"[{label}] 已选择单独字幕文件 {len(subtitle_files)} 个（无需检测内封轨道）。")
            for index, subtitle in enumerate(subtitle_files, 1):
                self.log_frame.write(f"  字幕文件 {index}: {subtitle.name}")
        if not videos:
            if not subtitle_files:
                self.log_frame.write(f"[{label}] 未选择视频或字幕文件。")
            return subtitle_source_count

        total_subtitle_streams = 0
        for index, video in enumerate(videos, 1):
            self.log_frame.write(f"[{label} {index}/{len(videos)}] {video.name}")
            try:
                streams = probe_subtitle_streams(video)
                if streams:
                    for order, stream in enumerate(streams):
                        tags = stream.get("tags", {}) or {}
                        real_index = stream.get("index", "")
                        codec = stream.get("codec_name", "")
                        language = tags.get("language", "")
                        title = tags.get("title", "")
                        self.log_frame.write(
                            f"  字幕轨 {order}，实际流 {real_index}: codec={codec}, language={language}, title={title}"
                        )
                    total_subtitle_streams += len(streams)
                else:
                    self.log_frame.write("  未检测到内封字幕轨道。")
                    self.log_frame.write("  如果文件名包含 SRT/ASS 字样，可能是外挂字幕；请把同目录字幕文件也加入目标。")

                raw_lines = probe_stream_lines(video)
                if raw_lines:
                    self.log_frame.write("  视频内全部流:")
                    for line in raw_lines:
                        self.log_frame.write(f"    {line}")
            except Exception as exc:
                self.log_frame.write(f"  检测失败: {exc}")
        return subtitle_source_count + total_subtitle_streams

    def _probe_workspace_job(self, workspace: str) -> str:
        self.log_frame.write("开始检测当前页面的字幕源和视频内封轨道...")
        if workspace == "video":
            source_count = self._probe_video_group("视频页字幕来源", self._current_video_sources())
            sample_count = self._probe_video_group("视频页示例", self._current_video_samples())
            video_count = self._probe_video_group("视频页目标视频", self._current_mux_videos())
            message = (
                f"视频页检测完成：字幕来源 {source_count}，示例 {sample_count}，"
                f"目标视频字幕轨 {video_count}。"
            )
        else:
            target_count = self._probe_video_group("样式页目标", self._current_targets())
            sample_count = self._probe_video_group("样式页示例", self._current_samples())
            message = f"样式页检测完成：目标 {target_count}，示例 {sample_count}。"
        self.log_frame.write(message)
        return message

    def probe_all_videos(self, button: tk.Widget | None = None) -> None:
        workspace = "style" if self.notebook.index("current") == 0 else "video"
        job = lambda: self._probe_workspace_job(workspace)
        if button is None:
            job()
            return
        self.run_background(button, job)

    def update_preview(self, outputs: list[Path]) -> None:
        subtitle_output = next(
            (path for path in outputs if Path(path).suffix.casefold() in {".ass", ".ssa", ".srt", ".vtt", ".skrt"}),
            None,
        )
        if not subtitle_output:
            self.preview_label.config(image="", text="暂无可预览字幕")
            self.preview_var.set("已生成文件，但没有可预览的字幕文件。")
            self.preview_cue_var.set("没有可显示的字幕事件")
            self.preview_cues = []
            self.preview_timeline.set_cues([])
            self.preview_image = None
            return
        try:
            self.preview_cues = read_subtitle_cues(subtitle_output)
            self.preview_timeline.set_cues(self.preview_cues)
            if self.preview_cues:
                self.preview_cue_var.set(self._format_preview_cue(0))
            else:
                self.preview_cue_var.set("文件已生成，但没有解析到有效字幕事件")
            preview_path = ensure_runtime_dirs()["temp"] / "subtitle_preview.png"
            create_ass_preview_image(subtitle_output, preview_path)
            with Image.open(preview_path) as image:
                image.thumbnail((340, 190))
                self.preview_image = ImageTk.PhotoImage(image.copy())
            self.preview_label.config(image=self.preview_image, text="")
            suffix = Path(subtitle_output).suffix.casefold()
            if suffix in {".srt", ".vtt", ".skrt"}:
                self.preview_var.set(
                    f"文本预览: {Path(subtitle_output).name} · {len(self.preview_cues)} 个事件"
                    "（该格式不保存字体/颜色/描边）"
                )
            else:
                self.preview_var.set(f"样式预览: {Path(subtitle_output).name} · {len(self.preview_cues)} 个事件")
        except Exception as exc:
            self.preview_label.config(image="", text="预览生成失败")
            self.preview_cue_var.set("字幕事件解析失败")
            self.preview_timeline.set_cues([])
            self.preview_var.set(f"{type(exc).__name__}: {exc}")

    def _format_preview_cue(self, index: int) -> str:
        if not self.preview_cues:
            return "没有可显示的字幕事件"
        start, end, text = self.preview_cues[index]
        return f"#{index + 1}  {start} → {end}\n{text}"

    def _select_preview_cue(self, index: int) -> None:
        if not self.preview_cues:
            return
        index = max(0, min(index, len(self.preview_cues) - 1))
        self.preview_timeline.selected = index
        self.preview_timeline.redraw()
        self.preview_cue_var.set(self._format_preview_cue(index))

    def build_options(self, remux_video: bool | None = None) -> StyleOptions:
        mode = self.style_mode_var.get()
        manual_enabled = mode in {"manual", "sample_manual"}
        return StyleOptions(
            font_name=self.font_var.get() if manual_enabled else "",
            font_size=self.size_var.get() if manual_enabled else "",
            primary_color=self.primary_var.get() if manual_enabled else "",
            outline_color=self.outline_color_var.get() if manual_enabled else "",
            alignment=self.align_var.get() if manual_enabled else "",
            margin_l=self.margin_l_var.get() if manual_enabled else "",
            margin_r=self.margin_r_var.get() if manual_enabled else "",
            margin_v=self.margin_v_var.get() if manual_enabled else "",
            outline=self.outline_var.get() if manual_enabled else "",
            shadow=self.shadow_var.get() if manual_enabled else "",
            bold=self.bold_var.get() if manual_enabled and self.apply_bold_var.get() else None,
            italic=self.italic_var.get() if manual_enabled and self.apply_italic_var.get() else None,
            use_sample=mode in {"sample", "sample_manual"},
            safe_single_language=self.safe_var.get(),
            remux_video=self.remux_var.get() if remux_video is None else remux_video,
            subtitle_stream=self.stream_var.get(),
            all_subtitle_streams=self.all_tracks_var.get(),
            output_format=self.output_format_var.get(),
            text_conversion_mode=mode_key_from_label(self.text_conversion_var.get()),
        )

    def build_bilingual_options(self) -> BilingualOptions:
        try:
            scale = min(0.95, max(0.5, float(self.bilingual_scale_var.get().strip())))
        except (TypeError, ValueError):
            scale = 0.78
        try:
            tolerance = min(10.0, max(0.0, float(self.bilingual_tolerance_var.get().strip())))
        except (TypeError, ValueError):
            tolerance = 1.2
        single_mode = {
            "检测中文后自动生成简繁双语": "auto_chinese",
            "缺少第二轨时仅保留原文": "none",
            "强制简体 -> 繁体": "s2t",
            "强制繁体 -> 简体": "t2s",
        }.get(self.bilingual_single_mode_var.get(), "auto_chinese")
        return BilingualOptions(
            style_preset="reference" if self.bilingual_reference_mode_var.get() == "参考文件优先" else "default",
            secondary_scale=scale,
            sync_tolerance=tolerance,
            flatten_separator=" / " if self.bilingual_flatten_var.get() else r"\N",
            keep_unmatched=self.bilingual_keep_unmatched_var.get(),
            single_source_mode=single_mode,
        )

    def _delete_video_tracks_job(
        self,
        videos: list[Path],
        output_dir: str | None,
        all_tracks: bool,
        stream_index: int,
    ) -> str:
        outputs = remove_subtitle_tracks_from_videos(
            videos,
            output_dir,
            all_subtitle_streams=all_tracks,
            subtitle_stream=stream_index,
            log=self.log_frame.write,
        )
        self.log_frame.write("完成输出:")
        for output in outputs:
            self.log_frame.write(str(output))
        return f"删除完成，生成 {len(outputs)} 个 MKV。"

    def _extract_audio_job(
        self,
        videos: list[Path],
        output_dir: str | None,
        stream_index: int,
    ) -> str:
        outputs = extract_audio_from_videos(
            videos,
            output_dir=output_dir,
            audio_stream=stream_index,
            audio_format="mp3",
            log=self.log_frame.write,
        )
        self.log_frame.write("完成输出:")
        for output in outputs:
            self.log_frame.write(str(output))
        return f"音频提取完成，生成 {len(outputs)} 个音频文件。"

    def _add_target_subtitles_job(
        self,
        sources: list[Path],
        videos: list[Path],
        output_dir: str | None,
        replace_existing: bool,
    ) -> str:
        subtitles = [path for path in sources if is_subtitle(path)]
        outputs = mux_subtitles_into_videos(
            subtitles,
            videos,
            output_dir,
            replace_existing_subtitles=replace_existing,
            log=self.log_frame.write,
        )
        self.log_frame.write("完成输出:")
        for output in outputs:
            self.log_frame.write(str(output))
        return f"封装完成，生成 {len(outputs)} 个 MKV。"

    def _modify_targets_job(
        self,
        targets: list[Path],
        samples: list[Path],
        options: StyleOptions,
        output_dir: str | None,
        style_mode: str,
    ) -> list[Path]:
        self.log_frame.write("开始处理字幕样式...")
        if options.output_format.casefold() in {"srt", "vtt"}:
            self.log_frame.write("提示：SRT/VTT 不保存字体、颜色、描边；需要视觉样式请输出 ASS。")
        if style_mode in {"sample", "sample_manual"}:
            self.log_frame.write("示例模式：SRT/VTT 示例只提供文本结构，ASS/SSA 示例可提供完整视觉样式。")
        if style_mode == "sample_manual":
            self.log_frame.write("示例 + 手动覆盖：冲突参数以手动填写为准，留空参数沿用示例。")
        conversion_mode = options.text_conversion_mode
        if conversion_mode != "none":
            self.log_frame.write(f"文字繁简转换：{mode_label(conversion_mode)}。")

        outputs = modify_many(
            targets,
            output_dir,
            options,
            sample_paths=samples,
            log=self.log_frame.write,
        )
        if not outputs:
            raise RuntimeError("没有生成字幕文件。请先检测目标视频是否含有可处理的内封字幕轨。")
        self.log_frame.write(f"字幕处理完成，生成 {len(outputs)} 个文件。")
        self.call_in_ui(lambda: self.update_preview([Path(output) for output in outputs]))
        return [Path(output) for output in outputs]

    def start_style(self, button: tk.Widget) -> None:
        target_snapshot = self.target_collection.snapshot()
        sample_snapshot = self.sample_collection.snapshot()
        if not target_snapshot.has_inputs:
            messagebox.showwarning("未选择目标", "请先在“字幕样式”页选择目标字幕或视频。")
            return
        options = self.build_options()
        output_dir = self.output_var.get().strip() or None
        style_mode = self.style_mode_var.get()

        def job() -> str:
            targets = resolve_input_snapshot(target_snapshot)
            samples = resolve_input_snapshot(sample_snapshot)
            if not targets:
                raise RuntimeError("所选目标中没有找到可处理的字幕或视频文件。")
            outputs = self._modify_targets_job(
                targets,
                samples,
                options,
                output_dir,
                style_mode,
            )
            self.log_frame.write("完成输出:")
            for output in outputs:
                self.log_frame.write(str(output))
            return f"字幕处理完成，生成 {len(outputs)} 个文件。"

        out_target = output_dir or (target_snapshot.files[0].parent if target_snapshot.files else target_snapshot.folders[0])
        self.run_background(button, job, output_dir=out_target)

    def start_video(self, button: tk.Widget) -> None:
        source_snapshot = self.video_source_collection.snapshot()
        sample_snapshot = self.video_sample_collection.snapshot()
        mux_snapshot = self.mux_video_collection.snapshot()
        action = self.video_action_var.get()
        output_dir = self.video_output_var.get().strip() or None
        all_tracks = self.all_tracks_var.get()
        stream_index = self.stream_var.get()
        replace_existing = self.replace_video_subtitles_var.get()

        if action == VIDEO_ACTION_BILINGUAL:
            if not source_snapshot.has_inputs:
                messagebox.showwarning("未选择字幕来源", "请先选择视频内字幕来源或多个外挂字幕文件。")
                return
            bilingual_options = self.build_bilingual_options()
            package_mkv = self.bilingual_package_var.get()
            reference_mode = self.bilingual_reference_mode_var.get()

            def bilingual_job() -> str:
                sources = resolve_input_snapshot(source_snapshot)
                samples = resolve_input_snapshot(sample_snapshot)
                if not sources:
                    raise RuntimeError("字幕来源扫描后为空，请检查视频或外挂字幕文件。")
                reference_text = None
                if reference_mode == "参考文件优先" and samples:
                    reference_parts: list[str] = []
                    for sample in samples:
                        reference_parts.extend(load_sample_style_texts(sample, log=self.log_frame.write))
                    reference_text = merge_sample_texts(reference_parts)
                    if not reference_text:
                        self.log_frame.write("未读取到可用参考样式，将使用内置双语样式。")
                outputs = build_bilingual_from_inputs(
                    sources,
                    output_dir,
                    reference_text=reference_text,
                    options=bilingual_options,
                    log=self.log_frame.write,
                )
                if not package_mkv:
                    self.log_frame.write("双语字幕已生成；未封装视频，原视频保持不变。")
                    return f"双语字幕生成完成，生成 {len(outputs)} 个 ASS。"

                mux_videos = resolve_input_snapshot(mux_snapshot)
                if not mux_videos:
                    mux_videos = [path for path in sources if is_video(path)]
                if not mux_videos:
                    raise RuntimeError("已要求封装 MKV，但没有找到目标视频。请在“目标视频”中选择视频。")
                mux_outputs = mux_subtitles_into_videos(
                    outputs,
                    mux_videos,
                    output_dir,
                    replace_existing_subtitles=replace_existing,
                    log=self.log_frame.write,
                )
                self.log_frame.write("双语字幕封装完成；源视频保持不变。")
                for output in mux_outputs:
                    self.log_frame.write(str(output))
                return f"双语字幕生成并封装完成，生成 {len(mux_outputs)} 个 MKV。"

            default_source = source_snapshot.files[0].parent if source_snapshot.files else source_snapshot.folders[0]
            self.run_background(button, bilingual_job, output_dir=output_dir or default_source)
            return

        if action == VIDEO_ACTION_REMOVE:
            if not mux_snapshot.has_inputs:
                messagebox.showwarning("未选择视频", "请在“视频轨道与封装”页选择要删除字幕轨的视频。")
                return
            self.run_background(
                button,
                lambda: self._delete_video_tracks_job(
                    resolve_input_snapshot(mux_snapshot),
                    output_dir,
                    all_tracks,
                    stream_index,
                ),
                output_dir=output_dir or (mux_snapshot.files[0].parent if mux_snapshot.files else mux_snapshot.folders[0]),
            )
            return

        if action == VIDEO_ACTION_EXTRACT_AUDIO:
            if not mux_snapshot.has_inputs:
                messagebox.showwarning("未选择视频", "请在“视频轨道与封装”页选择要提取音频的视频。")
                return
            self.run_background(
                button,
                lambda: self._extract_audio_job(resolve_input_snapshot(mux_snapshot), output_dir, stream_index),
                output_dir=output_dir or (mux_snapshot.files[0].parent if mux_snapshot.files else mux_snapshot.folders[0]),
            )
            return

        if not mux_snapshot.has_inputs:
            messagebox.showwarning("未选择视频", "请先在“视频轨道与封装”页选择目标视频。")
            return

        if action == VIDEO_ACTION_ADD:
            if not source_snapshot.has_inputs:
                messagebox.showwarning("未选择字幕", "请在当前页的“字幕来源”中选择要添加的单独字幕文件。")
                return
            self.run_background(
                button,
                lambda: self._add_target_subtitles_job(
                    resolve_input_snapshot(source_snapshot),
                    resolve_input_snapshot(mux_snapshot),
                    output_dir,
                    replace_existing,
                ),
                output_dir=output_dir or (mux_snapshot.files[0].parent if mux_snapshot.files else mux_snapshot.folders[0]),
            )
            return

        if action != VIDEO_ACTION_MODIFY:
            messagebox.showwarning("未选择操作", "请选择一个视频操作。")
            return
        if not source_snapshot.has_inputs:
            messagebox.showwarning("未选择字幕来源", "请在当前页选择要修改并封装的字幕或视频。")
            return
        style_mode = self.style_mode_var.get()
        if style_mode in {"sample", "sample_manual"} and not sample_snapshot.has_inputs:
            messagebox.showwarning("未选择示例", "当前样式模式需要示例，请在当前页选择示例字幕或视频。")
            return
        options = self.build_options(remux_video=False)

        def job() -> str:
            sources = resolve_input_snapshot(source_snapshot)
            samples = resolve_input_snapshot(sample_snapshot)
            mux_videos = resolve_input_snapshot(mux_snapshot)
            if not sources or not mux_videos:
                raise RuntimeError("视频操作输入在扫描后为空，请检查文件夹内容。")
            outputs = self._modify_targets_job(
                sources,
                samples,
                options,
                output_dir,
                style_mode,
            )
            subtitle_outputs = [path for path in outputs if is_subtitle(path)]
            if not subtitle_outputs:
                raise RuntimeError("字幕修改完成，但没有可用于封装的字幕输出。")
            mux_outputs = mux_subtitles_into_videos(
                subtitle_outputs,
                mux_videos,
                output_dir,
                replace_existing_subtitles=replace_existing,
                log=self.log_frame.write,
            )
            self.log_frame.write("完成输出:")
            for output in mux_outputs:
                self.log_frame.write(str(output))
            return f"修改并封装完成，生成 {len(mux_outputs)} 个 MKV。"

        self.run_background(
            button,
            job,
            output_dir=output_dir or (mux_snapshot.files[0].parent if mux_snapshot.files else mux_snapshot.folders[0]),
        )

    def start(self, button: tk.Widget) -> None:
        """Compatibility entry point for standalone callers."""
        self.start_style(button)

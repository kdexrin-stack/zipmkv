from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk

from PIL import Image, ImageTk

from common.file_selection import collect_files_from_inputs
from common.gui_base import LogFrame, ToolFrame, bind_listbox_delete_menu
from common.media_tools import describe_ffmpeg, find_ffmpeg, probe_stream_lines, probe_subtitle_streams
from common.paths import ensure_runtime_dirs
from common.theme import COLORS
from common.zhconv import MODES, mode_key_from_label, mode_label

from .core import (
    SUBTITLE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    StyleOptions,
    create_ass_preview_image,
    is_subtitle,
    is_video,
    modify_many,
    mux_subtitles_into_videos,
    remove_subtitle_tracks_from_videos,
)


TARGET_EXTENSIONS = SUBTITLE_EXTENSIONS | VIDEO_EXTENSIONS


class FeatureFrame(ToolFrame):
    title = "字幕样式修改"
    description = "修改单独字幕文件，或提取视频内封字幕后修改样式。"

    def __init__(self, master):
        super().__init__(master)
        self.target_files: list[str] = []
        self.target_folders: list[str] = []
        self.target_excluded: set[str] = set()
        self.target_display_items: list[tuple[str, str]] = []
        self.sample_files: list[str] = []
        self.sample_folders: list[str] = []
        self.sample_excluded: set[str] = set()
        self.sample_display_items: list[tuple[str, str]] = []
        self.mux_video_files: list[str] = []
        self.mux_video_folders: list[str] = []
        self.mux_video_excluded: set[str] = set()
        self.mux_video_display_items: list[tuple[str, str]] = []
        self.output_var = tk.StringVar()
        self.output_format_var = tk.StringVar(value="same")
        self.text_conversion_var = tk.StringVar(value="不转换")
        self.video_action_var = tk.StringVar(value="修改后封装到指定视频")
        self.video_source_var = tk.StringVar(value="尚未选择字幕来源")
        self.replace_video_subtitles_var = tk.BooleanVar(value=False)
        self.stream_var = tk.IntVar(value=0)
        self.all_tracks_var = tk.BooleanVar(value=True)
        self.style_mode_var = tk.StringVar(value="manual")
        self.safe_var = tk.BooleanVar(value=True)
        self.remux_var = tk.BooleanVar(value=False)
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
        self.preview_image = None
        self.manual_widgets: list[tk.Widget] = []
        self.sample_widgets: list[tk.Widget] = []
        self.stream_spins: list[ttk.Spinbox] = []
        self.color_swatches: list[tuple[tk.StringVar, tk.Label]] = []
        self._build()
        self.refresh_color_swatches()
        self.refresh_status()
        self.update_option_states()
        self.update_track_state()

    def _build(self) -> None:
        paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)
        top = ttk.Frame(paned)
        bottom = ttk.Frame(paned)
        paned.add(top, weight=4)
        paned.add(bottom, weight=2)

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
        ttk.Label(body, text="选择目标字幕或视频，可按示例样式对齐，也可使用手动参数覆盖。", style="Muted.TLabel").pack(anchor=tk.W)

        file_frame = ttk.LabelFrame(body, text="1. 输入与输出", padding=8)
        file_frame.pack(fill=tk.X, pady=8)
        file_frame.columnconfigure(1, weight=1)

        target_buttons = ttk.Frame(file_frame)
        target_buttons.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=4)
        ttk.Label(target_buttons, text="目标").pack(side=tk.LEFT)
        ttk.Button(target_buttons, text="选择单/多个", command=self.choose_targets).pack(side=tk.LEFT, padx=5)
        ttk.Button(target_buttons, text="选择文件夹", command=self.choose_target_folder).pack(side=tk.LEFT)
        self.target_list = tk.Listbox(file_frame, height=4, exportselection=False)
        self.target_list.grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=4)
        bind_listbox_delete_menu(self.target_list, self.delete_selected_targets, self.clear_targets)

        sample_buttons = ttk.Frame(file_frame)
        sample_buttons.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=4)
        ttk.Label(sample_buttons, text="示例").pack(side=tk.LEFT)
        ttk.Button(sample_buttons, text="选择单/多个", command=self.choose_samples).pack(side=tk.LEFT, padx=5)
        ttk.Button(sample_buttons, text="选择文件夹", command=self.choose_sample_folder).pack(side=tk.LEFT)
        self.sample_list = tk.Listbox(file_frame, height=4, exportselection=False)
        self.sample_list.grid(row=3, column=0, columnspan=3, sticky=tk.EW, pady=4)
        bind_listbox_delete_menu(self.sample_list, self.delete_selected_samples, self.clear_samples)

        ttk.Label(file_frame, text="输出目录").grid(row=4, column=0, sticky=tk.W, pady=4)
        ttk.Entry(file_frame, textvariable=self.output_var).grid(row=4, column=1, sticky=tk.EW, padx=5)
        ttk.Button(file_frame, text="选择", command=self.choose_output).grid(row=4, column=2)

        option_frame = ttk.LabelFrame(body, text="2. 样式来源与输出", padding=8)
        option_frame.pack(fill=tk.X, pady=6)
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
                swatch = tk.Label(control, width=3, relief=tk.SUNKEN, bg="#FFFFFF")
                swatch.pack(side=tk.LEFT, padx=(5, 3))
                button = ttk.Button(control, text="选择", width=5, command=lambda v=var: self.choose_color(v))
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
        ttk.Label(operation_frame, text="字幕来源").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Label(operation_frame, textvariable=self.video_source_var, style="Muted.TLabel").grid(row=0, column=1, sticky=tk.W, padx=6)
        ttk.Button(operation_frame, text="选择字幕来源", command=lambda: self.notebook.select(self.style_tab)).grid(row=0, column=2)
        ttk.Label(operation_frame, text="操作").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Combobox(
            operation_frame,
            textvariable=self.video_action_var,
            values=["修改后封装到指定视频", "仅添加目标字幕到指定视频", "删除指定视频内封字幕"],
            state="readonly",
            width=28,
        ).grid(row=1, column=1, sticky=tk.W, padx=6)
        ttk.Checkbutton(
            operation_frame,
            text="封装时替换原字幕轨",
            variable=self.replace_video_subtitles_var,
        ).grid(row=1, column=2, sticky=tk.W)

        mux_frame = ttk.LabelFrame(body, text="2. 目标视频", padding=8)
        mux_frame.pack(fill=tk.X, pady=6)
        mux_frame.columnconfigure(0, weight=1)
        video_buttons = ttk.Frame(mux_frame)
        video_buttons.grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Button(video_buttons, text="选择单/多个视频", command=self.choose_mux_videos).pack(side=tk.LEFT)
        ttk.Button(video_buttons, text="选择文件夹扫描", command=self.choose_mux_video_folder).pack(side=tk.LEFT, padx=6)
        self.mux_video_list = tk.Listbox(mux_frame, height=6, exportselection=False)
        self.mux_video_list.grid(row=1, column=0, sticky=tk.EW, pady=4)
        bind_listbox_delete_menu(self.mux_video_list, self.delete_selected_mux_videos, self.clear_mux_videos)

        track_frame = ttk.LabelFrame(body, text="3. 轨道范围", padding=8)
        track_frame.pack(fill=tk.X, pady=6)
        ttk.Checkbutton(
            track_frame,
            text="全部字幕轨道",
            variable=self.all_tracks_var,
            command=self.update_track_state,
        ).pack(side=tk.LEFT)
        ttk.Label(track_frame, text="单轨序号").pack(side=tk.LEFT, padx=(24, 5))
        stream_spin = ttk.Spinbox(track_frame, from_=0, to=20, width=5, textvariable=self.stream_var)
        stream_spin.pack(side=tk.LEFT)
        self.stream_spins.append(stream_spin)
        ttk.Label(track_frame, text="所有结果输出为新 MKV，源视频保持不变。", style="Muted.TLabel").pack(side=tk.LEFT, padx=20)

        ttk.Label(body, textvariable=self.status_var, style="Muted.TLabel", wraplength=900).pack(fill=tk.X, pady=8)

    def _build_result_panel(self, bottom: ttk.Frame) -> None:
        action_row = ttk.Frame(bottom, style="Surface.TFrame")
        action_row.pack(fill=tk.X, pady=(6, 8))
        self.primary_action_var = tk.StringVar(value="开始修改字幕")
        self.primary_action_button = ttk.Button(action_row, textvariable=self.primary_action_var, style="Primary.TButton")
        self.primary_action_button.configure(command=self._run_active_workspace)
        self.primary_action_button.pack(side=tk.LEFT)
        self.probe_button = ttk.Button(
            action_row,
            text="检测字幕源/轨道",
            command=lambda: self.probe_all_videos(self.probe_button),
        )
        self.probe_button.pack(side=tk.LEFT, padx=8)
        ttk.Button(action_row, text="清空日志", command=self.log_frame.clear).pack(side=tk.LEFT)

        result_panes = ttk.PanedWindow(bottom, orient=tk.HORIZONTAL)
        result_panes.pack(fill=tk.BOTH, expand=True)
        log_area = ttk.LabelFrame(result_panes, text="日志", padding=6)
        self.log_frame.destroy()
        self.log_frame = LogFrame(log_area)
        self.log_frame.text.configure(height=9)
        self.log_frame.pack(fill=tk.BOTH, expand=True)

        preview_area = ttk.LabelFrame(result_panes, text="效果示例", padding=6)
        self.preview_label = ttk.Label(preview_area, text="暂无预览", anchor=tk.CENTER, width=36)
        self.preview_label.pack(fill=tk.BOTH, expand=True)
        ttk.Label(preview_area, textvariable=self.preview_var, wraplength=320, style="Muted.TLabel").pack(fill=tk.X)
        result_panes.add(log_area, weight=3)
        result_panes.add(preview_area, weight=1)

    def _on_workspace_changed(self, _event=None) -> None:
        if not hasattr(self, "primary_action_var"):
            return
        if self.notebook.index("current") == 0:
            self.primary_action_var.set("开始修改字幕")
        else:
            self.primary_action_var.set("执行视频操作")

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
        ffmpeg = find_ffmpeg()
        if ffmpeg:
            self.status_var.set(f"已检测到 FFmpeg，可处理视频内封字幕。{describe_ffmpeg(ffmpeg)}")
        else:
            self.status_var.set("未检测到 FFmpeg；仍可处理单独字幕文件，视频内封字幕需要 FFmpeg。")

    def _current_targets(self) -> list[Path]:
        files = collect_files_from_inputs(self.target_files, self.target_folders, extensions=TARGET_EXTENSIONS)
        return [path for path in files if str(path.resolve()).casefold() not in self.target_excluded]

    def _current_samples(self) -> list[Path]:
        files = collect_files_from_inputs(self.sample_files, self.sample_folders, extensions=TARGET_EXTENSIONS)
        return [path for path in files if str(path.resolve()).casefold() not in self.sample_excluded]

    def choose_targets(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择目标字幕或视频",
            filetypes=[
                ("字幕/视频", "*.ass *.ssa *.srt *.vtt *.skrt *.mkv *.mp4 *.mov *.avi *.wmv *.flv *.webm *.m4v"),
                ("所有文件", "*.*"),
            ],
        )
        if paths:
            self.target_files.extend(list(paths))
            self.refresh_lists()

    def choose_target_folder(self) -> None:
        path = filedialog.askdirectory(title="选择包含目标字幕/视频的文件夹")
        if path:
            self.target_folders.append(path)
            self.refresh_lists()

    def choose_samples(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择示例字幕或视频",
            filetypes=[
                ("字幕/视频", "*.ass *.ssa *.srt *.vtt *.skrt *.mkv *.mp4 *.mov *.avi *.wmv *.flv *.webm *.m4v"),
                ("所有文件", "*.*"),
            ],
        )
        if paths:
            self.sample_files.extend(list(paths))
            if self.style_mode_var.get() == "manual":
                self.style_mode_var.set("sample_manual" if self.has_manual_overrides() else "sample")
                self.update_option_states()
            self.refresh_lists()

    def choose_sample_folder(self) -> None:
        path = filedialog.askdirectory(title="选择包含示例字幕/视频的文件夹")
        if path:
            self.sample_folders.append(path)
            if self.style_mode_var.get() == "manual":
                self.style_mode_var.set("sample_manual" if self.has_manual_overrides() else "sample")
                self.update_option_states()
            self.refresh_lists()

    def refresh_lists(self) -> None:
        target_paths = self._current_targets()
        self.target_display_items = []
        self.target_list.delete(0, tk.END)
        for path in target_paths:
            self.target_display_items.append(("file", str(path)))
            self.target_list.insert(tk.END, str(path))
        for folder in self.target_folders:
            self.target_display_items.append(("folder", folder))
            self.target_list.insert(tk.END, f"[文件夹] {folder}")

        subtitle_count = sum(1 for path in target_paths if is_subtitle(path))
        video_count = sum(1 for path in target_paths if is_video(path))
        if target_paths:
            self.video_source_var.set(f"样式页目标 {len(target_paths)} 个（字幕 {subtitle_count} / 视频 {video_count}）")
        else:
            self.video_source_var.set("尚未选择字幕来源")

        sample_paths = self._current_samples()
        self.sample_display_items = []
        self.sample_list.delete(0, tk.END)
        for index, path in enumerate(sample_paths, 1):
            self.sample_display_items.append(("file", str(path)))
            self.sample_list.insert(tk.END, f"{index}. {path.suffix.lower()} | {path}")
        for folder in self.sample_folders:
            self.sample_display_items.append(("folder", folder))
            self.sample_list.insert(tk.END, f"[示例文件夹] {folder}")

        self.mux_video_display_items = []
        self.mux_video_list.delete(0, tk.END)
        for path in self._current_mux_videos():
            self.mux_video_display_items.append(("file", str(path)))
            self.mux_video_list.insert(tk.END, str(path))
        for folder in self.mux_video_folders:
            self.mux_video_display_items.append(("folder", folder))
            self.mux_video_list.insert(tk.END, f"[视频文件夹] {folder}")

    def _delete_selected(
        self,
        listbox: tk.Listbox,
        display_items: list[tuple[str, str]],
        files: list[str],
        folders: list[str],
        excluded: set[str],
    ) -> None:
        for index in sorted(listbox.curselection(), reverse=True):
            if index >= len(display_items):
                continue
            kind, value = display_items[index]
            if kind == "folder":
                folders[:] = [item for item in folders if item != value]
            else:
                files[:] = [item for item in files if item != value]
                excluded.add(str(Path(value).resolve()).casefold())
        self.refresh_lists()

    def delete_selected_targets(self) -> None:
        self._delete_selected(
            self.target_list,
            self.target_display_items,
            self.target_files,
            self.target_folders,
            self.target_excluded,
        )

    def delete_selected_samples(self) -> None:
        self._delete_selected(
            self.sample_list,
            self.sample_display_items,
            self.sample_files,
            self.sample_folders,
            self.sample_excluded,
        )

    def clear_targets(self) -> None:
        self.target_files = []
        self.target_folders = []
        self.target_excluded.clear()
        self.refresh_lists()

    def clear_samples(self) -> None:
        self.sample_files = []
        self.sample_folders = []
        self.sample_excluded.clear()
        self.refresh_lists()

    def choose_output(self) -> None:
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_var.set(path)

    def choose_mux_videos(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择要封装/删除字幕的视频",
            filetypes=[
                ("视频", "*.mkv *.mp4 *.mov *.avi *.wmv *.flv *.webm *.m4v"),
                ("所有文件", "*.*"),
            ],
        )
        if paths:
            self.mux_video_files.extend(list(paths))
            self.refresh_lists()

    def choose_mux_video_folder(self) -> None:
        path = filedialog.askdirectory(title="选择包含视频的文件夹")
        if path:
            self.mux_video_folders.append(path)
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

    def _probe_all_videos_job(self) -> str:
        self.log_frame.write("开始检测字幕源和视频内封轨道...")
        target_count = self._probe_video_group("目标", self._current_targets())
        sample_count = self._probe_video_group("示例", self._current_samples())
        mux_count = self._probe_video_group("封装视频", self._current_mux_videos())
        message = f"检测完成：目标 {target_count}，示例 {sample_count}，封装视频字幕轨 {mux_count}。"
        self.log_frame.write(message)
        return message

    def probe_all_videos(self, button: tk.Widget | None = None) -> None:
        if button is None:
            self._probe_all_videos_job()
            return
        self.run_background(button, self._probe_all_videos_job)

    def update_preview(self, outputs: list[Path]) -> None:
        subtitle_output = next(
            (path for path in outputs if Path(path).suffix.casefold() in {".ass", ".ssa", ".srt", ".vtt", ".skrt"}),
            None,
        )
        if not subtitle_output:
            self.preview_label.config(image="", text="暂无可预览字幕")
            self.preview_var.set("已生成文件，但没有可预览的字幕文件。")
            self.preview_image = None
            return
        try:
            preview_path = ensure_runtime_dirs()["temp"] / "subtitle_preview.png"
            create_ass_preview_image(subtitle_output, preview_path)
            with Image.open(preview_path) as image:
                image.thumbnail((340, 190))
                self.preview_image = ImageTk.PhotoImage(image.copy())
            self.preview_label.config(image=self.preview_image, text="")
            suffix = Path(subtitle_output).suffix.casefold()
            if suffix in {".srt", ".vtt", ".skrt"}:
                self.preview_var.set(f"文本预览: {Path(subtitle_output).name}（该格式不保存字体/颜色/描边）")
            else:
                self.preview_var.set(f"样式预览: {Path(subtitle_output).name}")
        except Exception as exc:
            self.preview_label.config(image="", text="预览生成失败")
            self.preview_var.set(str(exc))

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

    def _current_mux_videos(self) -> list[Path]:
        files = collect_files_from_inputs(self.mux_video_files, self.mux_video_folders, extensions=VIDEO_EXTENSIONS)
        return [path for path in files if str(path.resolve()).casefold() not in self.mux_video_excluded]

    def delete_selected_mux_videos(self) -> None:
        self._delete_selected(
            self.mux_video_list,
            self.mux_video_display_items,
            self.mux_video_files,
            self.mux_video_folders,
            self.mux_video_excluded,
        )

    def clear_mux_videos(self) -> None:
        self.mux_video_files = []
        self.mux_video_folders = []
        self.mux_video_excluded.clear()
        self.refresh_lists()

    def _delete_video_tracks_job(self, videos: list[Path]) -> str:
        outputs = remove_subtitle_tracks_from_videos(
            videos,
            self.output_var.get() or None,
            all_subtitle_streams=self.all_tracks_var.get(),
            subtitle_stream=self.stream_var.get(),
            log=self.log_frame.write,
        )
        self.log_frame.write("完成输出:")
        for output in outputs:
            self.log_frame.write(str(output))
        return f"删除完成，生成 {len(outputs)} 个 MKV。"

    def _add_target_subtitles_job(self, targets: list[Path], videos: list[Path]) -> str:
        subtitles = [path for path in targets if is_subtitle(path)]
        outputs = mux_subtitles_into_videos(
            subtitles,
            videos,
            self.output_var.get() or None,
            replace_existing_subtitles=self.replace_video_subtitles_var.get(),
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
        *,
        remux_video: bool,
    ) -> list[Path]:
        self.log_frame.write("开始处理字幕样式...")
        if self.output_format_var.get().casefold() in {"srt", "vtt"}:
            self.log_frame.write("提示：SRT/VTT 不保存字体、颜色、描边；需要视觉样式请输出 ASS。")
        if self.style_mode_var.get() in {"sample", "sample_manual"}:
            self.log_frame.write("示例模式：SRT/VTT 示例只提供文本结构，ASS/SSA 示例可提供完整视觉样式。")
        if self.style_mode_var.get() == "sample_manual":
            self.log_frame.write("示例 + 手动覆盖：冲突参数以手动填写为准，留空参数沿用示例。")
        conversion_mode = mode_key_from_label(self.text_conversion_var.get())
        if conversion_mode != "none":
            self.log_frame.write(f"文字繁简转换：{mode_label(conversion_mode)}。")

        outputs = modify_many(
            targets,
            self.output_var.get() or None,
            self.build_options(remux_video=remux_video),
            sample_paths=samples,
            log=self.log_frame.write,
        )
        if not outputs:
            raise RuntimeError("没有生成字幕文件。请先检测目标视频是否含有可处理的内封字幕轨。")
        self.log_frame.write(f"字幕处理完成，生成 {len(outputs)} 个文件。")
        self.call_in_ui(lambda: self.update_preview([Path(output) for output in outputs]))
        return [Path(output) for output in outputs]

    def start_style(self, button: tk.Widget) -> None:
        targets = self._current_targets()
        samples = self._current_samples()
        if not targets:
            messagebox.showwarning("未选择目标", "请先在“字幕样式”页选择目标字幕或视频。")
            return

        def job() -> str:
            outputs = self._modify_targets_job(
                targets,
                samples,
                remux_video=self.remux_var.get(),
            )
            self.log_frame.write("完成输出:")
            for output in outputs:
                self.log_frame.write(str(output))
            return f"字幕处理完成，生成 {len(outputs)} 个文件。"

        self.run_background(button, job)

    def start_video(self, button: tk.Widget) -> None:
        targets = self._current_targets()
        samples = self._current_samples()
        mux_videos = self._current_mux_videos()
        target_videos = [path for path in targets if is_video(path)]
        action = self.video_action_var.get()

        if action == "删除指定视频内封字幕":
            videos = mux_videos or target_videos
            if not videos:
                messagebox.showwarning("未选择视频", "请在“视频轨道与封装”页选择要删除字幕轨的视频。")
                return
            self.run_background(button, lambda: self._delete_video_tracks_job(videos))
            return

        if not mux_videos:
            messagebox.showwarning("未选择视频", "请先在“视频轨道与封装”页选择目标视频。")
            return

        if action == "仅添加目标字幕到指定视频":
            if not any(is_subtitle(path) for path in targets):
                messagebox.showwarning("未选择字幕", "请到“字幕样式”页选择要追加的单独字幕文件。")
                return
            self.run_background(button, lambda: self._add_target_subtitles_job(targets, mux_videos))
            return

        if action != "修改后封装到指定视频":
            messagebox.showwarning("未选择操作", "请选择一个视频操作。")
            return
        if not targets:
            messagebox.showwarning("未选择字幕来源", "请到“字幕样式”页选择要修改并封装的字幕或视频。")
            return

        def job() -> str:
            outputs = self._modify_targets_job(targets, samples, remux_video=False)
            subtitle_outputs = [path for path in outputs if is_subtitle(path)]
            if not subtitle_outputs:
                raise RuntimeError("字幕修改完成，但没有可用于封装的字幕输出。")
            mux_outputs = mux_subtitles_into_videos(
                subtitle_outputs,
                mux_videos,
                self.output_var.get() or None,
                replace_existing_subtitles=self.replace_video_subtitles_var.get(),
                log=self.log_frame.write,
            )
            self.log_frame.write("完成输出:")
            for output in mux_outputs:
                self.log_frame.write(str(output))
            return f"修改并封装完成，生成 {len(mux_outputs)} 个 MKV。"

        self.run_background(button, job)

    def start(self, button: tk.Widget) -> None:
        """Compatibility entry point for standalone callers."""
        self.start_style(button)

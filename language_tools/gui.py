from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from common.file_selection import InputFileCollection, resolve_input_snapshot
from common.gui_base import FileListCard, ToolFrame
from subtitles.core import BilingualOptions, SUBTITLE_EXTENSIONS, VIDEO_EXTENSIONS, build_bilingual_from_inputs

from .core import SINGLE_SOURCE_MODE_LABELS, single_source_mode_from_label


INPUT_EXTENSIONS = SUBTITLE_EXTENSIONS | VIDEO_EXTENSIONS
INPUT_FILETYPES = [
    ("字幕与视频", "*.ass *.ssa *.srt *.vtt *.skrt *.mkv *.mp4 *.mov *.avi *.wmv *.flv *.webm *.m4v"),
    ("所有文件", "*.*"),
]


class FeatureFrame(ToolFrame):
    title = "字幕语言识别与简繁双语"
    description = "识别单语字幕；中文单轨可离线生成简体/繁体双语 ASS。"

    def __init__(self, master):
        super().__init__(master)
        self.collection = InputFileCollection(INPUT_EXTENSIONS)
        self.output_var = tk.StringVar()
        self.single_mode_var = tk.StringVar(value=SINGLE_SOURCE_MODE_LABELS["auto_chinese"])
        self.flatten_var = tk.BooleanVar(value=True)
        self._build()

    def _build(self) -> None:
        body = ttk.Frame(self, style="Workspace.TFrame")
        body.pack(fill=tk.BOTH, expand=True)

        self.file_card = FileListCard(
            body,
            title="1. 选择字幕文件、视频或文件夹",
            collection=self.collection,
            filetypes=INPUT_FILETYPES,
            file_dialog_title="选择字幕文件或视频",
            height=7,
        )
        self.file_card.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        options = ttk.LabelFrame(body, text="2. 单轨处理策略", style="Card.TLabelframe", padding=8)
        options.pack(fill=tk.X, pady=(0, 8))
        options.columnconfigure(1, weight=1)
        ttk.Label(options, text="缺少第二字幕时").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Combobox(
            options,
            textvariable=self.single_mode_var,
            values=list(SINGLE_SOURCE_MODE_LABELS.values()),
            state="readonly",
            width=28,
        ).grid(row=0, column=1, sticky=tk.W, padx=8)
        ttk.Label(
            options,
            text="仅简体/繁体互转是内置离线能力，其他语言不会伪造翻译。",
            style="Muted.TLabel",
        ).grid(row=0, column=2, sticky=tk.W, padx=8)
        ttk.Checkbutton(
            options,
            text="原字幕双行合并为单行",
            variable=self.flatten_var,
        ).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=4)
        ttk.Label(
            options,
            text="使用独立上下两种 ASS 样式，避免双语字号和换行互相冲突。",
            style="Muted.TLabel",
        ).grid(row=1, column=2, sticky=tk.W, padx=8)
        ttk.Label(options, text="输出目录").grid(row=2, column=0, sticky=tk.W, pady=4)
        ttk.Entry(options, textvariable=self.output_var).grid(row=2, column=1, sticky=tk.EW, padx=8)
        ttk.Button(options, text="选择", command=self.choose_output).grid(row=2, column=2, sticky=tk.W)

        action_row = ttk.Frame(body, style="Surface.TFrame")
        action_row.pack(fill=tk.X, pady=(0, 8))
        self.start_button = ttk.Button(action_row, text="▶ 开始识别并生成", style="Primary.TButton")
        self.start_button.configure(command=lambda: self.start(self.start_button))
        self.start_button.pack(side=tk.LEFT)
        ttk.Button(action_row, text="📂 打开输出目录", style="OpenDir.TButton", command=self.reveal_output_folder).pack(
            side=tk.LEFT, padx=10
        )
        ttk.Button(action_row, text="清空日志", command=self.log_frame.clear).pack(side=tk.RIGHT)
        self.log_frame.pack(fill=tk.BOTH, expand=True)

    def choose_output(self) -> None:
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_var.set(path)

    def start(self, button: tk.Widget) -> None:
        snapshot = self.collection.snapshot()
        if not snapshot.has_inputs:
            self.log_frame.write("请先选择字幕文件、视频或文件夹。")
            return

        output_dir = self.output_var.get().strip() or None
        mode = single_source_mode_from_label(self.single_mode_var.get())
        separator = " / " if self.flatten_var.get() else r"\N"

        def job() -> str:
            paths = resolve_input_snapshot(snapshot)
            if not paths:
                raise RuntimeError("扫描后没有可处理的字幕或视频文件。")
            outputs = build_bilingual_from_inputs(
                paths,
                output_dir,
                options=BilingualOptions(
                    flatten_separator=separator,
                    single_source_mode=mode,
                ),
                log=self.log_frame.write,
            )
            if not outputs:
                raise RuntimeError("没有生成字幕输出。")
            self.log_frame.write("语言识别与双语字幕处理完成：")
            for output in outputs:
                self.log_frame.write(str(output))
            return f"处理完成，生成 {len(outputs)} 个 ASS 文件"

        out_target = output_dir or (snapshot.files[0].parent if snapshot.files else snapshot.folders[0])
        self.run_background(button, job, output_dir=out_target)

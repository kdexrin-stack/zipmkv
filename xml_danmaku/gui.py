from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from common.file_selection import InputFileCollection, resolve_input_snapshot
from common.gui_base import FileListCard, ToolFrame
from common.zhconv import MODES, mode_key_from_label

from .core import DanmakuOptions, process_xml_files


XML_FILETYPES = [("XML 弹幕文件", "*.xml"), ("所有文件", "*.*")]


class FeatureFrame(ToolFrame):
    title = "XML 弹幕批量处理"
    description = "批量处理 B 站 XML 弹幕：转 ASS 滚动字幕/SRT、删除负时间、整体平移、清理 ASS 样式标签。"

    def __init__(self, master):
        super().__init__(master)
        self.delete_var = tk.BooleanVar(value=True)
        self.strip_var = tk.BooleanVar(value=False)
        self.adjust_var = tk.BooleanVar(value=False)
        self.direction_var = tk.StringVar(value="delay")
        self.hour_var = tk.IntVar(value=0)
        self.minute_var = tk.IntVar(value=0)
        self.second_var = tk.IntVar(value=0)
        self.output_format_var = tk.StringVar(value="XML (清洗/平移)")
        self.scroll_dur_var = tk.DoubleVar(value=10.0)
        self.font_size_var = tk.IntVar(value=34)
        self.text_conversion_var = tk.StringVar(value="不转换")
        self._build()
        self.toggle_format()

    def _build(self) -> None:
        self.collection = InputFileCollection(allowed_extensions={".xml"})
        self.file_card = FileListCard(
            self,
            title="Step 1 · 📁 输入 XML 弹幕",
            collection=self.collection,
            filetypes=XML_FILETYPES,
            file_dialog_title="选择 XML 弹幕文件",
            height=4,
            padding=8,
        )
        self.file_card.pack(fill=tk.BOTH, expand=False, pady=(2, 4))

        option_frame = ttk.LabelFrame(self, text="Step 2 · ⚙️ 处理与转换设置", style="Card.TLabelframe", padding=8)
        option_frame.pack(fill=tk.X, pady=(2, 4))
        
        fmt_row = ttk.Frame(option_frame)
        fmt_row.pack(anchor=tk.W, pady=(0, 4))
        ttk.Label(fmt_row, text="输出格式").pack(side=tk.LEFT)
        fmt_combo = ttk.Combobox(
            fmt_row,
            textvariable=self.output_format_var,
            values=["XML (清洗/平移)", "ASS 滚动字幕", "SRT 字幕"],
            width=18,
            state="readonly",
        )
        fmt_combo.pack(side=tk.LEFT, padx=6)
        
        ttk.Label(fmt_row, text="滚动时长(秒)").pack(side=tk.LEFT, padx=(12, 0))
        self.scroll_spin = ttk.Spinbox(fmt_row, from_=5, to=20, width=5, textvariable=self.scroll_dur_var, state=tk.DISABLED)
        self.scroll_spin.pack(side=tk.LEFT, padx=6)
        ttk.Label(fmt_row, text="字号").pack(side=tk.LEFT, padx=(8, 0))
        self.font_size_spin = ttk.Spinbox(fmt_row, from_=18, to=72, width=5, textvariable=self.font_size_var, state=tk.DISABLED)
        self.font_size_spin.pack(side=tk.LEFT, padx=6)

        self.output_format_var.trace_add("write", lambda *_args: self.toggle_format())

        ttk.Checkbutton(option_frame, text="删除时间戳为负数的无效弹幕", variable=self.delete_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(option_frame, text="清理 ASS 样式标签并保留原颜色", variable=self.strip_var).pack(anchor=tk.W, pady=2)
        ttk.Checkbutton(option_frame, text="启用弹幕时间平移", variable=self.adjust_var, command=self.toggle_adjust).pack(anchor=tk.W, pady=2)
        
        conversion_row = ttk.Frame(option_frame)
        conversion_row.pack(anchor=tk.W, pady=(4, 2))
        ttk.Label(conversion_row, text="文字繁简").pack(side=tk.LEFT)
        ttk.Combobox(
            conversion_row,
            textvariable=self.text_conversion_var,
            values=[mode.label for mode in MODES],
            width=18,
            state="readonly",
        ).pack(side=tk.LEFT, padx=6)

        adjust = ttk.Frame(option_frame)
        adjust.pack(anchor=tk.W, padx=20, pady=4)
        ttk.Label(adjust, text="时").grid(row=0, column=0)
        self.hour_spin = ttk.Spinbox(adjust, from_=0, to=99, width=5, textvariable=self.hour_var, state=tk.DISABLED)
        self.hour_spin.grid(row=0, column=1, padx=3)
        ttk.Label(adjust, text="分").grid(row=0, column=2)
        self.minute_spin = ttk.Spinbox(adjust, from_=0, to=59, width=5, textvariable=self.minute_var, state=tk.DISABLED)
        self.minute_spin.grid(row=0, column=3, padx=3)
        ttk.Label(adjust, text="秒").grid(row=0, column=4)
        self.second_spin = ttk.Spinbox(adjust, from_=0, to=59, width=5, textvariable=self.second_var, state=tk.DISABLED)
        self.second_spin.grid(row=0, column=5, padx=3)
        self.ahead_radio = ttk.Radiobutton(adjust, text="提前", value="ahead", variable=self.direction_var, state=tk.DISABLED)
        self.ahead_radio.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=(4, 0))
        self.delay_radio = ttk.Radiobutton(adjust, text="延后", value="delay", variable=self.direction_var, state=tk.DISABLED)
        self.delay_radio.grid(row=1, column=3, columnspan=2, sticky=tk.W, pady=(4, 0))

        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=(6, 8))
        start_button = ttk.Button(row, text="▶ 开始批量处理", style="Primary.TButton")
        start_button.config(command=lambda: self.start(start_button))
        start_button.pack(side=tk.LEFT)
        ttk.Button(row, text="📂 打开输出目录", style="OpenDir.TButton", command=self.reveal_output_folder).pack(side=tk.LEFT, padx=10)
        ttk.Button(row, text="清空日志", command=self.log_frame.clear).pack(side=tk.RIGHT)

        self.log_frame.pack(fill=tk.BOTH, expand=True)

    def toggle_format(self) -> None:
        is_sub = "字幕" in self.output_format_var.get()
        state = tk.NORMAL if is_sub else tk.DISABLED
        self.scroll_spin.configure(state=state)
        self.font_size_spin.configure(state=state)

    def toggle_adjust(self) -> None:
        state = tk.NORMAL if self.adjust_var.get() else tk.DISABLED
        for w in (self.hour_spin, self.minute_spin, self.second_spin, self.ahead_radio, self.delay_radio):
            w.configure(state=state)

    def calculate_offset(self) -> float:
        total = self.hour_var.get() * 3600 + self.minute_var.get() * 60 + self.second_var.get()
        return -float(total) if self.direction_var.get() == "ahead" else float(total)

    def start(self, button: tk.Widget) -> None:
        snapshot = self.collection.snapshot()
        if not snapshot.has_inputs:
            self.log_frame.write("请先添加需要处理的 XML 弹幕文件。")
            return

        fmt_raw = self.output_format_var.get()
        out_fmt = "ass" if "ASS" in fmt_raw else "srt" if "SRT" in fmt_raw else "xml"

        options = DanmakuOptions(
            delete_negative=self.delete_var.get(),
            adjust_enabled=self.adjust_var.get(),
            offset_seconds=self.calculate_offset(),
            strip_ass_tags=self.strip_var.get(),
            output_format=out_fmt,
            scroll_duration=self.scroll_dur_var.get(),
            font_size=self.font_size_var.get(),
            text_conversion_mode=mode_key_from_label(self.text_conversion_var.get()),
        )

        def job() -> str:
            files = resolve_input_snapshot(snapshot, extensions={".xml"})
            if not files:
                raise RuntimeError("所选输入中没有找到 XML 弹幕文件。")
            processed = process_xml_files(files, options, log=self.log_frame.write)
            self.log_frame.write(f"处理完成，共处理 {processed} 个文件。")
            if files:
                out_dir_name = "弹幕转字幕输出" if out_fmt in ("ass", "srt") else "已修改的弹幕"
                self.last_output_dir = files[0].parent / out_dir_name
            return f"处理完成，共处理 {processed} 个文件"

        out_folder = snapshot.files[0].parent / ("弹幕转字幕输出" if out_fmt in ("ass", "srt") else "已修改的弹幕") if snapshot.files else snapshot.folders[0]
        self.run_background(button, job, output_dir=out_folder)

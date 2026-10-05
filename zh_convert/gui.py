from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk

from common.file_selection import InputFileCollection, resolve_input_snapshot
from common.gui_base import FileListCard, ToolFrame
from common.theme import BASE_FONT_SIZE, COLORS, FONT_FAMILY
from common.zhconv import MODES, TEXT_EXTENSIONS, convert_chinese_text, mode_key_from_label, read_text_auto

from .core import convert_many


ZH_FILETYPES = [
    ("文本与字幕文件", "*.txt *.srt *.ass *.vtt *.xml *.md *.html *.htm *.lrc *.json *.csv"),
    ("所有文件", "*.*"),
]


class FeatureFrame(ToolFrame):
    title = "繁简文字转换"
    description = "批量处理 TXT、字幕、XML、HTML 等文本文件的简体/繁体互转。"

    def __init__(self, master):
        super().__init__(master)
        self.output_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="繁体 -> 简体")
        self.output_format_var = tk.StringVar(value="same")
        self._build()

    def _build(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill=tk.BOTH, expand=False, pady=(2, 4))

        self.collection = InputFileCollection(allowed_extensions=TEXT_EXTENSIONS)
        self.file_card = FileListCard(
            top,
            title="Step 1 · 📁 待转换文本素材",
            collection=self.collection,
            filetypes=ZH_FILETYPES,
            file_dialog_title="选择文本、字幕或 XML 文件",
            height=3,
            padding=8,
            on_changed=self.update_preview,
        )
        self.file_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        self.file_card.listbox.bind("<<ListboxSelect>>", lambda _event: self.update_preview())

        form = ttk.LabelFrame(top, text="Step 2 · ⚙️ 繁简转换规则与输出", style="Card.TLabelframe", padding=8)
        form.pack(side=tk.RIGHT, fill=tk.BOTH)
        ttk.Label(form, text="转换方向").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Combobox(
            form,
            textvariable=self.mode_var,
            values=[mode.label for mode in MODES if mode.key != "none"],
            width=18,
            state="readonly",
        ).grid(row=0, column=1, sticky=tk.W, padx=4)
        self.mode_var.trace_add("write", lambda *_args: self.update_preview())
        
        ttk.Label(form, text="输出格式").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Combobox(
            form,
            textvariable=self.output_format_var,
            values=["same", "txt", "srt", "ass", "vtt", "xml", "md", "html"],
            width=8,
            state="readonly",
        ).grid(row=1, column=1, sticky=tk.W, padx=4)
        ttk.Label(form, text="输出目录").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Entry(form, textvariable=self.output_var, width=24).grid(row=2, column=1, sticky=tk.EW, padx=4)
        ttk.Button(form, text="浏览", command=self.choose_output).grid(row=2, column=2)

        preview = ttk.LabelFrame(self, text="转换效果实时对比预览", style="Card.TLabelframe", padding=6)
        preview.pack(fill=tk.BOTH, expand=True, pady=(2, 4))
        preview.columnconfigure(0, weight=1)
        preview.columnconfigure(1, weight=1)
        ttk.Label(preview, text="原文内容预览", style="Muted.TLabel").grid(row=0, column=0, sticky=tk.W, pady=(0, 1))
        ttk.Label(preview, text="转换后效果预览", style="Muted.TLabel").grid(row=0, column=1, sticky=tk.W, pady=(0, 1))
        self.before_text = self._build_preview_text(preview)
        self.before_text.grid(row=1, column=0, sticky=tk.NSEW, padx=(0, 4))
        self.after_text = self._build_preview_text(preview)
        self.after_text.grid(row=1, column=1, sticky=tk.NSEW, padx=(4, 0))
        preview.rowconfigure(1, weight=1)

        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=(4, 6))
        start_button = ttk.Button(row, text="▶ 开始批量转换", style="Primary.TButton")
        start_button.config(command=lambda: self.start(start_button))
        start_button.pack(side=tk.LEFT)
        ttk.Button(row, text="📂 打开输出目录", style="OpenDir.TButton", command=self.reveal_output_folder).pack(side=tk.LEFT, padx=10)
        ttk.Button(row, text="刷新预览", command=self.update_preview).pack(side=tk.LEFT)
        ttk.Button(row, text="清空日志", command=self.log_frame.clear).pack(side=tk.RIGHT)

        self.log_frame.pack(fill=tk.BOTH, expand=True)

    def _build_preview_text(self, master) -> scrolledtext.ScrolledText:
        widget = scrolledtext.ScrolledText(master, height=4, wrap=tk.WORD)
        widget.configure(
            bg=COLORS["surface"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            selectbackground=COLORS["selection"],
            selectforeground=COLORS["primary_hover"],
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["primary"],
            font=(FONT_FAMILY, BASE_FONT_SIZE),
            padx=8,
            pady=6,
        )
        return widget

    def choose_output(self) -> None:
        target = filedialog.askdirectory(title="选择输出目录")
        if target:
            self.output_var.set(target)

    def update_preview(self) -> None:
        selected_idx = self.file_card.listbox.curselection()
        target_file: Path | None = None
        if selected_idx and selected_idx[0] < len(self.file_card.collection.display_items):
            _, raw_key = self.file_card.collection.display_items[selected_idx[0]]
            candidate = Path(raw_key)
            if candidate.is_file() and candidate.suffix.casefold() in TEXT_EXTENSIONS:
                target_file = candidate
        if target_file is None:
            direct_files = [
                path for path in self.collection.direct_files()
                if path.suffix.casefold() in TEXT_EXTENSIONS
            ]
            target_file = direct_files[0] if direct_files else None
        if target_file is None:
            self._set_preview_content("", "")
            if self.collection.visible_folders():
                self._set_preview_content("文件夹内容将在开始转换时后台扫描。", "")
            return

        try:
            sample = read_text_auto(target_file)
            lines = sample.splitlines()[:12]
            preview_source = "\n".join(lines)
            mode_key = mode_key_from_label(self.mode_var.get())
            preview_converted = convert_chinese_text(preview_source, mode_key)
            self._set_preview_content(preview_source, preview_converted)
        except Exception as exc:
            self._set_preview_content(f"预览读取失败: {exc}", "")

    def _set_preview_content(self, before: str, after: str) -> None:
        self.before_text.delete("1.0", tk.END)
        self.before_text.insert(tk.END, before)
        self.after_text.delete("1.0", tk.END)
        self.after_text.insert(tk.END, after)

    def start(self, button: tk.Widget) -> None:
        snapshot = self.collection.snapshot()
        if not snapshot.has_inputs:
            self.log_frame.write("请先添加需要转换的文本素材。")
            return

        mode_key = mode_key_from_label(self.mode_var.get())
        output_dir = self.output_var.get().strip() or None
        output_format = self.output_format_var.get()

        def job() -> str:
            files = resolve_input_snapshot(snapshot, extensions=TEXT_EXTENSIONS)
            if not files:
                raise RuntimeError("所选输入中没有可转换的文本或字幕文件。")
            generated = convert_many(
                files,
                mode=mode_key,
                output_dir=output_dir,
                output_format=output_format,
                log=self.log_frame.write,
            )
            self.log_frame.write(f"完成，共转换 {len(generated)} 个文本文件。")
            if generated:
                self.last_output_dir = Path(generated[0]).parent
            return f"完成，共转换 {len(generated)} 个文本文件"

        out_target = output_dir or (snapshot.files[0].parent if snapshot.files else snapshot.folders[0])
        self.run_background(button, job, output_dir=out_target)

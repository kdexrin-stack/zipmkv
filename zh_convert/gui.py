from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from common.gui_base import ToolFrame, bind_listbox_delete_menu
from common.theme import BASE_FONT_SIZE, COLORS, FONT_FAMILY
from common.zhconv import MODES, TEXT_EXTENSIONS, convert_chinese_text, mode_key_from_label, read_text_auto

from .core import collect_convertible_files, convert_many


class FeatureFrame(ToolFrame):
    title = "繁简文字转换"
    description = "批量处理 TXT、字幕、XML、HTML 等文本文件的简体/繁体互转。"

    def __init__(self, master):
        super().__init__(master)
        self.files: list[str] = []
        self.folders: list[str] = []
        self.excluded_paths: set[str] = set()
        self.display_items: list[tuple[str, str]] = []
        self.output_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="繁体 -> 简体")
        self.output_format_var = tk.StringVar(value="same")
        self.summary_var = tk.StringVar(value="尚未选择输入")
        self._build()

    def _build(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill=tk.BOTH, expand=False, pady=8)

        input_frame = ttk.LabelFrame(top, text="输入", padding=8)
        input_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        buttons = ttk.Frame(input_frame)
        buttons.pack(anchor=tk.W)
        ttk.Button(buttons, text="选择单/多个", command=self.choose_files).pack(side=tk.LEFT)
        ttk.Button(buttons, text="选择文件夹扫描", command=self.choose_folder).pack(side=tk.LEFT, padx=6)
        self.listbox = tk.Listbox(input_frame, height=8, exportselection=False)
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        bind_listbox_delete_menu(self.listbox, self.delete_selected, self.clear_items)
        self.listbox.bind("<<ListboxSelect>>", lambda _event: self.update_preview())
        ttk.Label(input_frame, textvariable=self.summary_var, style="Muted.TLabel").pack(anchor=tk.W)

        form = ttk.LabelFrame(top, text="转换设置", padding=8)
        form.pack(side=tk.RIGHT, fill=tk.X)
        ttk.Label(form, text="转换方向").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Combobox(
            form,
            textvariable=self.mode_var,
            values=[mode.label for mode in MODES if mode.key != "none"],
            width=20,
            state="readonly",
        ).grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(form, text="输出格式").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Combobox(
            form,
            textvariable=self.output_format_var,
            values=["same", "txt", "srt", "ass", "vtt", "xml", "md", "html"],
            width=10,
            state="readonly",
        ).grid(row=1, column=1, sticky=tk.W, padx=5)
        ttk.Label(form, text="输出目录").grid(row=2, column=0, sticky=tk.W, pady=4)
        ttk.Entry(form, textvariable=self.output_var, width=36).grid(row=2, column=1, sticky=tk.EW, padx=5)
        ttk.Button(form, text="选择", command=self.choose_output).grid(row=2, column=2)
        ttk.Label(
            form,
            text="默认不改源文件，会在原路径新建“繁简转换输出”文件夹。",
            style="Muted.TLabel",
            wraplength=420,
        ).grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(6, 0))

        preview = ttk.LabelFrame(self, text="效果预览", padding=8)
        preview.pack(fill=tk.BOTH, expand=True, pady=6)
        preview.columnconfigure(0, weight=1)
        preview.columnconfigure(1, weight=1)
        ttk.Label(preview, text="原文").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(preview, text="转换后").grid(row=0, column=1, sticky=tk.W)
        self.before_text = self._build_preview_text(preview)
        self.before_text.grid(row=1, column=0, sticky=tk.NSEW, padx=(0, 5))
        self.after_text = self._build_preview_text(preview)
        self.after_text.grid(row=1, column=1, sticky=tk.NSEW, padx=(5, 0))
        preview.rowconfigure(1, weight=1)

        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=8)
        start_button = ttk.Button(row, text="开始转换", style="Primary.TButton")
        start_button.config(command=lambda: self.start(start_button))
        start_button.pack(side=tk.LEFT)
        ttk.Button(row, text="刷新预览", command=self.update_preview).pack(side=tk.LEFT, padx=8)
        ttk.Button(row, text="清空日志", command=self.log_frame.clear).pack(side=tk.LEFT)

        self.log_frame.pack(fill=tk.BOTH, expand=True)

    def _build_preview_text(self, master) -> scrolledtext.ScrolledText:
        widget = scrolledtext.ScrolledText(master, height=8, wrap=tk.WORD)
        widget.configure(
            bg=COLORS["surface"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief=tk.SOLID,
            bd=1,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            font=(FONT_FAMILY, BASE_FONT_SIZE),
        )
        return widget

    def choose_files(self) -> None:
        patterns = " ".join(f"*{suffix}" for suffix in sorted(TEXT_EXTENSIONS))
        paths = filedialog.askopenfilenames(
            title="选择要转换的文本/字幕/XML 文件",
            filetypes=[("可转换文本", patterns), ("所有文件", "*.*")],
        )
        if paths:
            self.files.extend(list(paths))
            self.refresh_list()

    def choose_folder(self) -> None:
        path = filedialog.askdirectory(title="选择包含文本/字幕/XML 的文件夹")
        if path:
            self.folders.append(path)
            self.refresh_list()

    def choose_output(self) -> None:
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_var.set(path)

    def current_files(self) -> list[Path]:
        return collect_convertible_files(self.files, self.folders, self.excluded_paths)

    def refresh_list(self) -> None:
        self.display_items = []
        self.listbox.delete(0, tk.END)
        for path in self.current_files():
            self.display_items.append(("file", str(path)))
            self.listbox.insert(tk.END, str(path))
        for folder in self.folders:
            self.display_items.append(("folder", folder))
            self.listbox.insert(tk.END, f"[文件夹扫描] {folder}")
        file_count = len([item for item in self.display_items if item[0] == "file"])
        folder_count = len([item for item in self.display_items if item[0] == "folder"])
        self.summary_var.set(f"已选择 {file_count} 个文件，{folder_count} 个文件夹。" if file_count or folder_count else "尚未选择输入")
        self.update_preview()

    def delete_selected(self) -> None:
        for index in sorted(self.listbox.curselection(), reverse=True):
            if index >= len(self.display_items):
                continue
            kind, value = self.display_items[index]
            if kind == "folder":
                self.folders = [item for item in self.folders if item != value]
            else:
                self.files = [item for item in self.files if item != value]
                self.excluded_paths.add(str(Path(value).resolve()).casefold())
        self.refresh_list()

    def clear_items(self) -> None:
        self.files = []
        self.folders = []
        self.excluded_paths.clear()
        self.refresh_list()
        self.log_frame.clear()

    def _preview_file(self) -> Path | None:
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.display_items) and self.display_items[index][0] == "file":
                return Path(self.display_items[index][1])
        files = self.current_files()
        return files[0] if files else None

    def _set_text(self, widget: scrolledtext.ScrolledText, value: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, value)
        widget.configure(state=tk.DISABLED)

    def update_preview(self) -> None:
        path = self._preview_file()
        if not path:
            self._set_text(self.before_text, "尚未选择可预览文件")
            self._set_text(self.after_text, "")
            return
        try:
            text = read_text_auto(path)
            sample = text[:3000]
            converted = convert_chinese_text(sample, mode_key_from_label(self.mode_var.get()))
            self._set_text(self.before_text, sample)
            self._set_text(self.after_text, converted)
        except Exception as exc:
            self._set_text(self.before_text, str(path))
            self._set_text(self.after_text, f"预览失败: {exc}")

    def start(self, button: tk.Widget) -> None:
        files = self.current_files()
        if not files:
            messagebox.showwarning("未选择文件", "请先选择要转换的文本、字幕或 XML 文件。")
            return

        mode = mode_key_from_label(self.mode_var.get())

        def job() -> str:
            outputs = convert_many(
                files,
                self.output_var.get() or None,
                mode,
                output_format=self.output_format_var.get(),
                log=self.log_frame.write,
            )
            if not outputs:
                raise RuntimeError("没有生成任何转换结果。")
            self.log_frame.write(f"完成，共生成 {len(outputs)} 个文件。")
            self.call_in_ui(self.update_preview)
            return f"转换完成，生成 {len(outputs)} 个文件。"

        self.run_background(button, job)

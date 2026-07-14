from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from common.file_selection import collect_files_from_inputs
from common.gui_base import ToolFrame, bind_listbox_delete_menu
from common.zhconv import MODES, mode_key_from_label, mode_label

from .core import DanmakuOptions, process_xml_files


class FeatureFrame(ToolFrame):
    title = "XML 弹幕批量处理"
    description = "批量处理 B 站 XML 弹幕：删除负时间、整体平移、清理 ASS 样式标签。"

    def __init__(self, master):
        super().__init__(master)
        self.files: list[str] = []
        self.folders: list[str] = []
        self.excluded_paths: set[str] = set()
        self.display_items: list[tuple[str, str]] = []
        self.delete_var = tk.BooleanVar(value=True)
        self.strip_var = tk.BooleanVar(value=False)
        self.adjust_var = tk.BooleanVar(value=False)
        self.direction_var = tk.StringVar(value="delay")
        self.hour_var = tk.IntVar(value=0)
        self.minute_var = tk.IntVar(value=0)
        self.second_var = tk.IntVar(value=0)
        self.text_conversion_var = tk.StringVar(value="不转换")
        self._build()

    def _build(self) -> None:
        file_frame = ttk.LabelFrame(self, text="文件", padding=6)
        file_frame.pack(fill=tk.BOTH, expand=False, pady=8)
        file_buttons = ttk.Frame(file_frame)
        file_buttons.pack(anchor=tk.W)
        ttk.Button(file_buttons, text="选择单/多个 XML", command=self.choose_files).pack(side=tk.LEFT)
        ttk.Button(file_buttons, text="选择文件夹扫描", command=self.choose_folder).pack(side=tk.LEFT, padx=6)
        self.listbox = tk.Listbox(file_frame, height=6)
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        bind_listbox_delete_menu(self.listbox, self.delete_selected, self.clear_files)

        option_frame = ttk.LabelFrame(self, text="处理选项", padding=8)
        option_frame.pack(fill=tk.X, pady=6)
        ttk.Checkbutton(option_frame, text="删除负数时间弹幕", variable=self.delete_var).pack(anchor=tk.W)
        ttk.Checkbutton(option_frame, text="清理 ASS 样式标签并保留颜色", variable=self.strip_var).pack(anchor=tk.W)
        ttk.Checkbutton(option_frame, text="启用时间平移", variable=self.adjust_var, command=self.toggle_adjust).pack(anchor=tk.W)
        conversion_row = ttk.Frame(option_frame)
        conversion_row.pack(anchor=tk.W, pady=(6, 0))
        ttk.Label(conversion_row, text="文字繁简").pack(side=tk.LEFT)
        ttk.Combobox(
            conversion_row,
            textvariable=self.text_conversion_var,
            values=[mode.label for mode in MODES],
            width=18,
            state="readonly",
        ).pack(side=tk.LEFT, padx=6)

        adjust = ttk.Frame(option_frame)
        adjust.pack(anchor=tk.W, padx=20, pady=5)
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
        self.ahead_radio.grid(row=1, column=1, columnspan=2, sticky=tk.W)
        self.delay_radio = ttk.Radiobutton(adjust, text="延后", value="delay", variable=self.direction_var, state=tk.DISABLED)
        self.delay_radio.grid(row=1, column=3, columnspan=2, sticky=tk.W)

        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=8)
        start_button = ttk.Button(row, text="开始处理", style="Primary.TButton")
        start_button.config(command=lambda: self.start(start_button))
        start_button.pack(side=tk.LEFT)
        ttk.Button(row, text="清空日志", command=self.log_frame.clear).pack(side=tk.LEFT, padx=8)

        self.log_frame.pack(fill=tk.BOTH, expand=True)

    def choose_files(self) -> None:
        paths = filedialog.askopenfilenames(title="选择 XML 文件", filetypes=[("XML 文件", "*.xml"), ("所有文件", "*.*")])
        if paths:
            self.files.extend(list(paths))
            self.refresh_list()

    def choose_folder(self) -> None:
        path = filedialog.askdirectory(title="选择包含 XML 的文件夹")
        if path:
            self.folders.append(path)
            self.refresh_list()

    def refresh_list(self) -> None:
        self.display_items = []
        self.listbox.delete(0, tk.END)
        for path in self.current_files():
            self.display_items.append(("file", str(path)))
            self.listbox.insert(tk.END, str(path))
        for folder in self.folders:
            self.display_items.append(("folder", folder))
            self.listbox.insert(tk.END, f"[文件夹] {folder}")

    def current_files(self):
        files = collect_files_from_inputs(self.files, self.folders, extensions={".xml"})
        return [path for path in files if str(path.resolve()).casefold() not in self.excluded_paths]

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

    def clear_files(self) -> None:
        self.files = []
        self.folders = []
        self.excluded_paths.clear()
        self.refresh_list()

    def toggle_adjust(self) -> None:
        state = tk.NORMAL if self.adjust_var.get() else tk.DISABLED
        for widget in (self.hour_spin, self.minute_spin, self.second_spin, self.ahead_radio, self.delay_radio):
            widget.config(state=state)

    def start(self, button: tk.Widget) -> None:
        targets = self.current_files()
        if not targets:
            messagebox.showwarning("未选择文件", "请先选择 XML 文件。")
            return

        seconds = self.hour_var.get() * 3600 + self.minute_var.get() * 60 + self.second_var.get()
        if self.direction_var.get() == "ahead":
            seconds = -seconds
        options = DanmakuOptions(
            delete_negative=self.delete_var.get(),
            adjust_enabled=self.adjust_var.get(),
            offset_seconds=seconds,
            strip_ass_tags=self.strip_var.get(),
            text_conversion_mode=mode_key_from_label(self.text_conversion_var.get()),
        )

        def job() -> None:
            conversion_mode = mode_key_from_label(self.text_conversion_var.get())
            if conversion_mode != "none":
                self.log_frame.write(f"文字繁简转换：{mode_label(conversion_mode)}。")
            count = process_xml_files(targets, options, self.log_frame.write)
            self.log_frame.write(f"完成，共处理 {count} 个文件。")

        self.run_background(button, job)

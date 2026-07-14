from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from PIL import Image, ImageTk

from common.file_selection import collect_files_from_inputs
from common.gui_base import ArchiveToolSelector, ToolFrame, bind_listbox_delete_menu

from .core import convert_archives_to_pdf


class FeatureFrame(ToolFrame):
    title = "多压缩包转 PDF"
    description = "多选压缩包，按文件名自然排序逐个生成 PDF。"

    def __init__(self, master):
        super().__init__(master)
        self.archive_paths: list[str] = []
        self.folder_paths: list[str] = []
        self.excluded_paths: set[str] = set()
        self.display_items: list[tuple[str, str]] = []
        self.output_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.preview_image = None
        self.preview_var = tk.StringVar(value="尚未生成预览")
        self._build()

    def _build(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill=tk.BOTH, expand=False, pady=8)

        left = ttk.Frame(top)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        file_buttons = ttk.Frame(left)
        file_buttons.pack(anchor=tk.W)
        ttk.Button(file_buttons, text="选择单/多个压缩包", command=self.choose_archives).pack(side=tk.LEFT)
        ttk.Button(file_buttons, text="选择文件夹扫描", command=self.choose_folder).pack(side=tk.LEFT, padx=6)
        self.listbox = tk.Listbox(left, height=8)
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        bind_listbox_delete_menu(self.listbox, self.delete_selected, self.clear_archives)

        form = ttk.Frame(top)
        form.pack(side=tk.RIGHT, fill=tk.X, padx=(10, 0))
        ttk.Label(form, text="输出目录").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Entry(form, textvariable=self.output_var, width=42).grid(row=0, column=1, padx=5)
        ttk.Button(form, text="选择", command=self.choose_output).grid(row=0, column=2)
        ttk.Label(form, text="解压密码（可空）").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Entry(form, textvariable=self.password_var, show="*").grid(row=1, column=1, sticky=tk.EW, padx=5)

        self.tool_selector = ArchiveToolSelector(self)
        self.tool_selector.pack(fill=tk.X, pady=6)

        button_row = ttk.Frame(self)
        button_row.pack(fill=tk.X, pady=8)
        start_button = ttk.Button(button_row, text="开始转换", style="Primary.TButton")
        start_button.config(command=lambda: self.start(start_button))
        start_button.pack(side=tk.LEFT)
        ttk.Button(button_row, text="清空列表", command=self.clear_archives).pack(side=tk.LEFT, padx=8)
        ttk.Button(button_row, text="清空日志", command=self.log_frame.clear).pack(side=tk.LEFT)

        bottom = ttk.Frame(self)
        bottom.pack(fill=tk.BOTH, expand=True)
        self.log_frame.pack(in_=bottom, side=tk.LEFT, fill=tk.BOTH, expand=True)
        preview = ttk.LabelFrame(bottom, text="随机效果示例", padding=8)
        preview.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        self.preview_label = ttk.Label(preview, text="生成后显示", anchor=tk.CENTER, width=28)
        self.preview_label.pack(fill=tk.BOTH, expand=True)
        ttk.Label(preview, textvariable=self.preview_var, wraplength=220, style="Muted.TLabel").pack(fill=tk.X)

    def choose_archives(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择压缩包",
            filetypes=[("压缩包/电子书", "*.zip *.rar *.7z *.cbz *.cbr *.cb7 *.epub *.tar *.gz *.tgz"), ("所有文件", "*.*")],
        )
        if paths:
            self.archive_paths.extend(list(paths))
            self.refresh_list()

    def choose_folder(self) -> None:
        path = filedialog.askdirectory(title="选择包含压缩包的文件夹")
        if path:
            self.folder_paths.append(path)
            self.refresh_list()

    def choose_output(self) -> None:
        path = filedialog.askdirectory(title="选择 PDF 输出目录")
        if path:
            self.output_var.set(path)

    def clear_archives(self) -> None:
        self.archive_paths = []
        self.folder_paths = []
        self.excluded_paths.clear()
        self.refresh_list()

    def current_archives(self):
        files = collect_files_from_inputs(self.archive_paths, self.folder_paths, include_archives=True)
        return [path for path in files if str(path.resolve()).casefold() not in self.excluded_paths]

    def delete_selected(self) -> None:
        for index in sorted(self.listbox.curselection(), reverse=True):
            if index >= len(self.display_items):
                continue
            kind, value = self.display_items[index]
            if kind == "folder":
                self.folder_paths = [item for item in self.folder_paths if item != value]
            else:
                self.archive_paths = [item for item in self.archive_paths if item != value]
                self.excluded_paths.add(str(Path(value).resolve()).casefold())
        self.refresh_list()

    def refresh_list(self) -> None:
        self.display_items = []
        self.listbox.delete(0, tk.END)
        for path in self.current_archives():
            self.display_items.append(("file", str(path)))
            self.listbox.insert(tk.END, str(path))
        for folder in self.folder_paths:
            self.display_items.append(("folder", folder))
            self.listbox.insert(tk.END, f"[文件夹] {folder}")

    def start(self, button: tk.Widget) -> None:
        def show_preview(image_path: Path, pdf_path: Path) -> None:
            def update() -> None:
                try:
                    with Image.open(image_path) as img:
                        img.thumbnail((220, 300))
                        self.preview_image = ImageTk.PhotoImage(img.copy())
                    self.preview_label.config(image=self.preview_image, text="")
                    self.preview_var.set(f"样张: {image_path.name}\nPDF: {pdf_path.name}")
                except Exception as exc:
                    self.preview_var.set(f"预览失败: {exc}")

            self.after(0, update)

        def job() -> None:
            generated = convert_archives_to_pdf(
                self.current_archives(),
                output_dir=self.output_var.get() or None,
                password=self.password_var.get() or None,
                archive_tool=self.tool_selector.selected_tool(),
                log=self.log_frame.write,
                preview_callback=show_preview,
            )
            self.log_frame.write(f"完成，共生成 {len(generated)} 个 PDF。")

        self.run_background(button, job)

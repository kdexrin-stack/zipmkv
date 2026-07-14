from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from PIL import Image, ImageTk

from common.gui_base import ArchiveToolSelector, ToolFrame, bind_listbox_delete_menu
from common.zhconv import MODES, mode_key_from_label, mode_label

from .core import convert_mixed_items


class FeatureFrame(ToolFrame):
    title = "图片/压缩包/PDF/EPUB/TXT 整理"
    description = "选择图片、压缩包、EPUB、PDF、TXT，或选择文件夹扫描，整理合并为 PDF 或 EPUB。"

    def __init__(self, master):
        super().__init__(master)
        self.file_paths: list[str] = []
        self.folder_paths: list[str] = []
        self.excluded_paths: set[str] = set()
        self.display_items: list[tuple[str, str]] = []
        self.output_var = tk.StringVar()
        self.output_name_var = tk.StringVar(value="合并整理")
        self.output_format_var = tk.StringVar(value="pdf")
        self.merge_var = tk.BooleanVar(value=True)
        self.password_var = tk.StringVar()
        self.text_conversion_var = tk.StringVar(value="不转换")
        self.selection_summary_var = tk.StringVar(value="尚未选择输入")
        self.preview_image = None
        self.preview_var = tk.StringVar(value="尚未生成预览")
        self._build()

    def _build(self) -> None:
        ttk.Label(
            self,
            text="不改源文件；默认把所选内容合并成一个大文件。PDF 输入合并为 PDF 时保留原页面；PDF 输出 EPUB 时会提取可复制文本。",
            style="Muted.TLabel",
            wraplength=820,
        ).pack(anchor=tk.W, pady=(4, 0))

        top = ttk.Frame(self)
        top.pack(fill=tk.BOTH, expand=False, pady=8)

        left = ttk.Frame(top)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        buttons = ttk.Frame(left)
        buttons.pack(anchor=tk.W)
        ttk.Button(buttons, text="选择文件", command=self.choose_files).pack(side=tk.LEFT)
        ttk.Button(buttons, text="选择文件夹扫描", command=self.choose_folder).pack(side=tk.LEFT, padx=6)
        self.listbox = tk.Listbox(left, height=9, exportselection=False)
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        bind_listbox_delete_menu(self.listbox, self.delete_selected, self.clear_items)
        ttk.Label(left, textvariable=self.selection_summary_var, style="Muted.TLabel").pack(anchor=tk.W)

        form = ttk.Frame(top)
        form.pack(side=tk.RIGHT, fill=tk.X, padx=(10, 0))
        ttk.Label(form, text="输出目录").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Entry(form, textvariable=self.output_var, width=42).grid(row=0, column=1, padx=5)
        ttk.Button(form, text="选择", command=self.choose_output).grid(row=0, column=2)
        ttk.Label(form, text="输出格式").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Combobox(
            form,
            textvariable=self.output_format_var,
            values=["pdf", "epub"],
            state="readonly",
            width=8,
        ).grid(row=1, column=1, sticky=tk.W, padx=5)
        ttk.Checkbutton(form, text="合并为一个大文件", variable=self.merge_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=4)
        ttk.Label(form, text="合并文件名").grid(row=3, column=0, sticky=tk.W, pady=4)
        ttk.Entry(form, textvariable=self.output_name_var, width=42).grid(row=3, column=1, padx=5)
        ttk.Label(form, text="文字繁简").grid(row=4, column=0, sticky=tk.W, pady=4)
        ttk.Combobox(
            form,
            textvariable=self.text_conversion_var,
            values=[mode.label for mode in MODES],
            state="readonly",
            width=16,
        ).grid(row=4, column=1, sticky=tk.W, padx=5)
        ttk.Label(form, text="解压密码（可空）").grid(row=5, column=0, sticky=tk.W, pady=4)
        ttk.Entry(form, textvariable=self.password_var, show="*").grid(row=5, column=1, sticky=tk.EW, padx=5)

        self.tool_selector = ArchiveToolSelector(self)
        self.tool_selector.pack(fill=tk.X, pady=6)

        button_row = ttk.Frame(self)
        button_row.pack(fill=tk.X, pady=8)
        start_button = ttk.Button(button_row, text="开始整理", style="Primary.TButton")
        start_button.config(command=lambda: self.start(start_button))
        start_button.pack(side=tk.LEFT)
        ttk.Button(button_row, text="清空列表", command=self.clear_items).pack(side=tk.LEFT, padx=8)
        ttk.Button(button_row, text="清空日志", command=self.log_frame.clear).pack(side=tk.LEFT)

        bottom = ttk.Frame(self)
        bottom.pack(fill=tk.BOTH, expand=True)
        self.log_frame.pack(in_=bottom, side=tk.LEFT, fill=tk.BOTH, expand=True)
        preview = ttk.LabelFrame(bottom, text="随机效果示例", padding=8)
        preview.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        self.preview_label = ttk.Label(preview, text="生成后显示", anchor=tk.CENTER, width=28)
        self.preview_label.pack(fill=tk.BOTH, expand=True)
        ttk.Label(preview, textvariable=self.preview_var, wraplength=220, style="Muted.TLabel").pack(fill=tk.X)

    def choose_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择图片、压缩包、EPUB、PDF 或 TXT",
            filetypes=[
                (
                    "可整理文件",
                    "*.jpg *.jpeg *.png *.gif *.bmp *.tif *.tiff *.webp "
                    "*.zip *.rar *.7z *.cbz *.cbr *.cb7 *.epub *.pdf *.txt "
                    "*.tar *.gz *.tgz *.bz2 *.xz",
                ),
                ("所有文件", "*.*"),
            ],
        )
        if paths:
            self.file_paths.extend(list(paths))
            self.refresh_list()

    def choose_folder(self) -> None:
        path = filedialog.askdirectory(title="选择包含图片/压缩包/EPUB/PDF/TXT 的文件夹")
        if path:
            self.folder_paths.append(path)
            self.refresh_list()

    def choose_output(self) -> None:
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_var.set(path)

    def current_files(self) -> list[Path]:
        files: list[Path] = []
        seen: set[str] = set()
        for item in self.file_paths:
            path = Path(item)
            if not path.is_file():
                continue
            key = str(path.resolve()).casefold()
            if key in self.excluded_paths or key in seen:
                continue
            seen.add(key)
            files.append(path)
        return files

    def current_folders(self) -> list[Path]:
        folders: list[Path] = []
        seen: set[str] = set()
        for item in self.folder_paths:
            path = Path(item)
            if not path.is_dir():
                continue
            key = str(path.resolve()).casefold()
            if key in self.excluded_paths or key in seen:
                continue
            seen.add(key)
            folders.append(path)
        return folders

    def refresh_list(self) -> None:
        self.display_items = []
        self.listbox.delete(0, tk.END)
        for path in self.current_files():
            self.display_items.append(("file", str(path)))
            self.listbox.insert(tk.END, str(path))
        for folder in self.current_folders():
            self.display_items.append(("folder", str(folder)))
            self.listbox.insert(tk.END, f"[文件夹扫描] {folder}")
        file_count = len([item for item in self.display_items if item[0] == "file"])
        folder_count = len([item for item in self.display_items if item[0] == "folder"])
        if file_count or folder_count:
            self.selection_summary_var.set(f"已选择 {file_count} 个文件，{folder_count} 个文件夹。")
        else:
            self.selection_summary_var.set("尚未选择输入")

    def clear_items(self) -> None:
        self.file_paths = []
        self.folder_paths = []
        self.excluded_paths.clear()
        self.refresh_list()

    def delete_selected(self) -> None:
        for index in sorted(self.listbox.curselection(), reverse=True):
            if index >= len(self.display_items):
                continue
            kind, value = self.display_items[index]
            if kind == "folder":
                self.folder_paths = [item for item in self.folder_paths if item != value]
            else:
                self.file_paths = [item for item in self.file_paths if item != value]
            self.excluded_paths.add(str(Path(value).resolve()).casefold())
        self.refresh_list()

    def start(self, button: tk.Widget) -> None:
        def show_preview(image_path: Path, pdf_path: Path) -> None:
            def update() -> None:
                try:
                    with Image.open(image_path) as img:
                        img.thumbnail((220, 300))
                        self.preview_image = ImageTk.PhotoImage(img.copy())
                    self.preview_label.config(image=self.preview_image, text="")
                    self.preview_var.set(f"样张: {image_path.name}\n输出: {pdf_path.name}")
                except Exception as exc:
                    self.preview_var.set(f"预览失败: {exc}")

            self.call_in_ui(update)

        def job() -> None:
            conversion_mode = mode_key_from_label(self.text_conversion_var.get())
            if conversion_mode != "none":
                self.log_frame.write(f"文字繁简转换：{mode_label(conversion_mode)}。PDF 原页面合并时保持原样。")
            generated = convert_mixed_items(
                file_paths=self.current_files(),
                folder_paths=self.current_folders(),
                output_dir=self.output_var.get() or None,
                password=self.password_var.get() or None,
                archive_tool=self.tool_selector.selected_tool(),
                output_format=self.output_format_var.get(),
                merge_output=self.merge_var.get(),
                output_name=self.output_name_var.get(),
                text_conversion_mode=conversion_mode,
                log=self.log_frame.write,
                preview_callback=show_preview,
            )
            self.log_frame.write(f"完成，共生成 {len(generated)} 个文件。")

        self.run_background(button, job)

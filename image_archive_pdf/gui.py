from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk

from common.file_selection import resolve_input_snapshot
from common.gui_base import ArchiveToolSelector, FileListCard, ToolFrame
from common.zhconv import MODES, mode_key_from_label, mode_label

from .core import convert_mixed_items


MERGE_FILETYPES = [
    (
        "可整理素材",
        "*.jpg *.jpeg *.png *.gif *.bmp *.tif *.tiff *.webp "
        "*.zip *.rar *.7z *.cbz *.cbr *.cb7 *.epub *.pdf *.txt "
        "*.tar *.gz *.tgz *.bz2 *.xz",
    ),
    ("所有文件", "*.*"),
]


class FeatureFrame(ToolFrame):
    title = "图片/压缩包/PDF/EPUB/TXT 整理"
    description = "选择图片、压缩包、EPUB、PDF、TXT，或选择文件夹扫描，整理合并为 PDF 或 EPUB。"

    def __init__(self, master):
        super().__init__(master)
        self.output_var = tk.StringVar()
        self.output_name_var = tk.StringVar(value="合并整理")
        self.output_format_var = tk.StringVar(value="pdf")
        self.merge_var = tk.BooleanVar(value=True)
        self.password_var = tk.StringVar()
        self.text_conversion_var = tk.StringVar(value="不转换")
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
        top.pack(fill=tk.BOTH, expand=False, pady=(6, 8))

        self.file_card = FileListCard(
            top,
            title="Step 1 · 📁 输入素材列表",
            filetypes=MERGE_FILETYPES,
            file_dialog_title="选择图片、压缩包、EPUB、PDF 或 TXT",
            height=4,
            padding=8,
        )
        self.file_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        form = ttk.LabelFrame(top, text="Step 2 · ⚙️ 整理与输出设置", style="Card.TLabelframe", padding=8)
        form.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(0, 0))
        ttk.Label(form, text="输出目录").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(form, textvariable=self.output_var, width=28).grid(row=0, column=1, columnspan=2, padx=4, sticky=tk.EW)
        ttk.Button(form, text="浏览", command=self.choose_output).grid(row=0, column=3, padx=(2, 0))

        ttk.Label(form, text="输出格式").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Combobox(
            form,
            textvariable=self.output_format_var,
            values=["pdf", "epub"],
            state="readonly",
            width=8,
        ).grid(row=1, column=1, sticky=tk.W, padx=4)
        ttk.Label(form, text="文字繁简").grid(row=1, column=2, sticky=tk.W, padx=(8, 2))
        ttk.Combobox(
            form,
            textvariable=self.text_conversion_var,
            values=[mode.label for mode in MODES],
            state="readonly",
            width=12,
        ).grid(row=1, column=3, sticky=tk.W, padx=2)

        ttk.Checkbutton(form, text="合并大文件", variable=self.merge_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)
        ttk.Label(form, text="合并名称").grid(row=2, column=2, sticky=tk.W, padx=(8, 2))
        ttk.Entry(form, textvariable=self.output_name_var, width=14).grid(row=2, column=3, padx=2, sticky=tk.EW)

        ttk.Label(form, text="解压密码").grid(row=3, column=0, sticky=tk.W, pady=2)
        ttk.Entry(form, textvariable=self.password_var, show="*", width=12).grid(row=3, column=1, sticky=tk.W, padx=4)

        self.tool_selector = ArchiveToolSelector(self)
        self.tool_selector.pack(fill=tk.X, pady=(2, 4))

        button_row = ttk.Frame(self)
        button_row.pack(fill=tk.X, pady=(6, 8))
        start_button = ttk.Button(button_row, text="▶ 开始合并整理", style="Primary.TButton")
        start_button.config(command=lambda: self.start(start_button))
        start_button.pack(side=tk.LEFT)
        ttk.Button(button_row, text="📂 打开输出目录", style="OpenDir.TButton", command=self.reveal_output_folder).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_row, text="清空日志", command=self.log_frame.clear).pack(side=tk.RIGHT)

        bottom = ttk.Frame(self)
        bottom.pack(fill=tk.BOTH, expand=True)
        self.log_frame.pack(in_=bottom, side=tk.LEFT, fill=tk.BOTH, expand=True)
        preview = ttk.LabelFrame(bottom, text="效果示例预览", style="Card.TLabelframe", padding=10)
        preview.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        self.preview_label = ttk.Label(preview, text="生成后显示", anchor=tk.CENTER, width=28)
        self.preview_label.pack(fill=tk.BOTH, expand=True)
        ttk.Label(preview, textvariable=self.preview_var, wraplength=220, style="Muted.TLabel").pack(fill=tk.X, pady=(4, 0))

    def choose_output(self) -> None:
        target = filedialog.askdirectory(title="选择输出目录")
        if target:
            self.output_var.set(target)

    def start(self, button: tk.Widget) -> None:
        snapshot = self.file_card.collection.snapshot()
        if not snapshot.has_inputs:
            self.log_frame.write("请先添加需要整理的素材文件或扫描文件夹。")
            return
        output_dir = self.output_var.get().strip() or None
        output_format = self.output_format_var.get()
        merge_output = self.merge_var.get()
        output_name = self.output_name_var.get()
        password = self.password_var.get() or None
        conversion_mode = mode_key_from_label(self.text_conversion_var.get())

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

        def job() -> str:
            files = resolve_input_snapshot(snapshot)
            folders = list(snapshot.folders)
            if not files and not folders:
                raise RuntimeError("所选输入中没有可整理的文件或文件夹。")
            if conversion_mode != "none":
                self.log_frame.write(f"文字繁简转换：{mode_label(conversion_mode)}。PDF 原页面合并时保持原样。")
            generated = convert_mixed_items(
                file_paths=files,
                folder_paths=folders,
                output_dir=output_dir,
                password=password,
                archive_tool=self.tool_selector.selected_tool(),
                output_format=output_format,
                merge_output=merge_output,
                output_name=output_name,
                text_conversion_mode=conversion_mode,
                log=self.log_frame.write,
                preview_callback=show_preview,
            )
            self.log_frame.write(f"完成，共生成 {len(generated)} 个文件。")
            if generated:
                self.last_output_dir = Path(generated[0]).parent
            return f"完成，共生成 {len(generated)} 个文件"

        out_target = output_dir or (snapshot.files[0].parent if snapshot.files else snapshot.folders[0])
        self.run_background(button, job, output_dir=out_target)

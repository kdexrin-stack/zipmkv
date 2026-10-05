from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk

from common.file_selection import InputFileCollection, resolve_input_snapshot
from common.gui_base import ArchiveToolSelector, FileListCard, ToolFrame

from .core import convert_archives_to_pdf


ARCHIVE_FILETYPES = [
    ("压缩包/电子书", "*.zip *.rar *.7z *.cbz *.cbr *.cb7 *.epub *.tar *.gz *.tgz"),
    ("所有文件", "*.*"),
]


class FeatureFrame(ToolFrame):
    title = "多压缩包转 PDF"
    description = "多选压缩包，按文件名自然排序逐个生成 PDF。"

    def __init__(self, master):
        super().__init__(master)
        self.output_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.preview_image = None
        self.preview_var = tk.StringVar(value="尚未生成预览")
        self._build()

    def _build(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill=tk.BOTH, expand=False, pady=(6, 8))

        self.collection = InputFileCollection(include_archives=True)
        self.file_card = FileListCard(
            top,
            title="Step 1 · 📁 输入压缩包列表",
            collection=self.collection,
            filetypes=ARCHIVE_FILETYPES,
            file_dialog_title="选择压缩包",
            height=4,
            padding=8,
        )
        self.file_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        form = ttk.LabelFrame(top, text="Step 2 · ⚙️ 转换设置", style="Card.TLabelframe", padding=8)
        form.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(0, 0))
        ttk.Label(form, text="输出目录").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(form, textvariable=self.output_var, width=28).grid(row=0, column=1, padx=4, sticky=tk.EW)
        ttk.Button(form, text="浏览", command=self.choose_output).grid(row=0, column=2)
        ttk.Label(form, text="解压密码").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(form, textvariable=self.password_var, show="*", width=20).grid(row=1, column=1, sticky=tk.W, padx=4)

        self.tool_selector = ArchiveToolSelector(self)
        self.tool_selector.pack(fill=tk.X, pady=(2, 4))

        button_row = ttk.Frame(self)
        button_row.pack(fill=tk.X, pady=(6, 8))
        start_button = ttk.Button(button_row, text="▶ 开始批量转换", style="Primary.TButton")
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
        path = filedialog.askdirectory(title="选择 PDF 输出目录")
        if path:
            self.output_var.set(path)

    def start(self, button: tk.Widget) -> None:
        snapshot = self.collection.snapshot()
        if not snapshot.has_inputs:
            self.log_frame.write("请先添加需要转换的压缩包。")
            return
        output_dir = self.output_var.get().strip() or None
        password = self.password_var.get() or None

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

            self.call_in_ui(update)

        def job() -> str:
            archives = resolve_input_snapshot(snapshot, include_archives=True)
            if not archives:
                raise RuntimeError("所选输入中没有可处理的压缩包。")
            generated = convert_archives_to_pdf(
                archives,
                output_dir=output_dir,
                password=password,
                archive_tool=self.tool_selector.selected_tool(),
                log=self.log_frame.write,
                preview_callback=show_preview,
            )
            self.log_frame.write(f"完成，共转换 {len(generated)} 个压缩包。")
            if generated:
                self.last_output_dir = Path(generated[0]).parent
            return f"完成，共转换 {len(generated)} 个压缩包"

        out_target = output_dir or (snapshot.files[0].parent if snapshot.files else snapshot.folders[0])
        self.run_background(button, job, output_dir=out_target)

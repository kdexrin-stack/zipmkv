from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from common.gui_base import ToolFrame, bind_listbox_delete_menu
from common.text_utils import natural_sorted
from common.theme import configure_listbox

from .core import ManualRenameRule, build_manual_pairs, build_pairs, copy_by_pairs, format_manual_name


class FeatureFrame(ToolFrame):
    title = "批量文件重命名"
    description = "用参考文件名配对，或按手动规则生成 ep1、01、视频ep01视频 等新文件名。"

    def __init__(self, master):
        super().__init__(master)
        self.name_files: list[str] = []
        self.name_folders: list[str] = []
        self.name_excluded: set[str] = set()
        self.target_files: list[str] = []
        self.target_folders: list[str] = []
        self.target_excluded: set[str] = set()
        self.a_display_items: list[tuple[str, str]] = []
        self.b_display_items: list[tuple[str, str]] = []
        self.output_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="reference")
        self.prefix_var = tk.StringVar()
        self.suffix_var = tk.StringVar()
        self.number_style_var = tk.StringVar(value="ep01")
        self.start_var = tk.IntVar(value=1)
        self.step_var = tk.IntVar(value=1)
        self.custom_template_var = tk.StringVar(value="视频ep{num:02d}视频")
        self.example_var = tk.StringVar()
        self.a_widgets: list[tk.Widget] = []
        self.manual_widgets: list[tk.Widget] = []
        self._build()
        self._bind_rule_changes()
        self.update_mode_state()
        self.refresh_preview()

    def _build(self) -> None:
        mode_frame = ttk.LabelFrame(self, text="命名方式", padding=8)
        mode_frame.pack(fill=tk.X, pady=(8, 6))
        ttk.Radiobutton(
            mode_frame,
            text="参考 A 组文件名",
            value="reference",
            variable=self.mode_var,
            command=self.update_mode_state,
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            mode_frame,
            text="手动规则生成",
            value="manual",
            variable=self.mode_var,
            command=self.update_mode_state,
        ).pack(side=tk.LEFT, padx=(18, 0))

        panes = ttk.Frame(self)
        panes.pack(fill=tk.BOTH, expand=True, pady=6)

        self.a_list = self._build_file_panel(
            panes,
            "A 组：参考新名字",
            self.choose_a,
            self.choose_a_folder,
        )
        bind_listbox_delete_menu(self.a_list, self.delete_selected_a, self.clear_a)
        self.b_list = self._build_file_panel(
            panes,
            "B 组：将生成重命名副本",
            self.choose_b,
            self.choose_b_folder,
        )
        bind_listbox_delete_menu(self.b_list, self.delete_selected_b, self.clear_b)

        rule_frame = ttk.LabelFrame(self, text="手动规则", padding=8)
        rule_frame.pack(fill=tk.X, pady=6)
        rule_frame.columnconfigure(7, weight=1)
        self._add_rule_label(rule_frame, "固定前缀", 0, 0)
        prefix_entry = ttk.Entry(rule_frame, textvariable=self.prefix_var, width=14)
        prefix_entry.grid(row=0, column=1, sticky=tk.W, padx=(4, 12))
        self.manual_widgets.append(prefix_entry)

        self._add_rule_label(rule_frame, "编号样式", 0, 2)
        style_combo = ttk.Combobox(
            rule_frame,
            textvariable=self.number_style_var,
            values=["1", "01", "001", "ep1", "ep01", "EP01", "E01", "自定义模板"],
            width=12,
            state="readonly",
        )
        style_combo.grid(row=0, column=3, sticky=tk.W, padx=(4, 12))
        style_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_preview())
        self.manual_widgets.append(style_combo)

        self._add_rule_label(rule_frame, "固定后缀", 0, 4)
        suffix_entry = ttk.Entry(rule_frame, textvariable=self.suffix_var, width=14)
        suffix_entry.grid(row=0, column=5, sticky=tk.W, padx=(4, 12))
        self.manual_widgets.append(suffix_entry)

        self._add_rule_label(rule_frame, "起始", 1, 0)
        start_spin = ttk.Spinbox(rule_frame, from_=0, to=9999, width=6, textvariable=self.start_var)
        start_spin.grid(row=1, column=1, sticky=tk.W, padx=(4, 12), pady=(6, 0))
        self.manual_widgets.append(start_spin)

        self._add_rule_label(rule_frame, "步进", 1, 2)
        step_spin = ttk.Spinbox(rule_frame, from_=1, to=999, width=6, textvariable=self.step_var)
        step_spin.grid(row=1, column=3, sticky=tk.W, padx=(4, 12), pady=(6, 0))
        self.manual_widgets.append(step_spin)

        self._add_rule_label(rule_frame, "自定义模板", 1, 4)
        custom_entry = ttk.Entry(rule_frame, textvariable=self.custom_template_var, width=28)
        custom_entry.grid(row=1, column=5, columnspan=3, sticky=tk.EW, padx=(4, 0), pady=(6, 0))
        self.manual_widgets.append(custom_entry)
        ttk.Label(
            rule_frame,
            text="模板支持 {num}、{num:02d}、{num:03d}；也可直接写 视频ep{num:02d}视频。",
            style="Muted.TLabel",
        ).grid(row=2, column=0, columnspan=8, sticky=tk.W, pady=(6, 0))
        ttk.Label(rule_frame, textvariable=self.example_var, style="Muted.TLabel").grid(
            row=3,
            column=0,
            columnspan=8,
            sticky=tk.W,
            pady=(4, 0),
        )

        preview_frame = ttk.LabelFrame(self, text="重命名预览", padding=6)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=6)
        self.preview = tk.Listbox(preview_frame, height=8, exportselection=False)
        configure_listbox(self.preview)
        self.preview.pack(fill=tk.BOTH, expand=True)

        output_row = ttk.Frame(self)
        output_row.pack(fill=tk.X, pady=4)
        ttk.Label(output_row, text="输出目录").pack(side=tk.LEFT)
        ttk.Entry(output_row, textvariable=self.output_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(output_row, text="选择", command=self.choose_output).pack(side=tk.LEFT)

        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=8)
        start_button = ttk.Button(row, text="生成重命名副本", style="Primary.TButton")
        start_button.config(command=lambda: self.start(start_button))
        start_button.pack(side=tk.LEFT)
        ttk.Button(row, text="刷新预览", command=self.refresh_preview).pack(side=tk.LEFT, padx=8)
        ttk.Button(row, text="清空", command=self.clear_all).pack(side=tk.LEFT)

        self.log_frame.pack(fill=tk.BOTH, expand=True)

    def _add_rule_label(self, master, text: str, row: int, column: int) -> None:
        label = ttk.Label(master, text=text)
        label.grid(row=row, column=column, sticky=tk.W, pady=(0 if row == 0 else 6, 0))
        self.manual_widgets.append(label)

    def _build_file_panel(self, master, title: str, file_command, folder_command):
        frame = ttk.LabelFrame(master, text=title, padding=6)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        listbox = tk.Listbox(frame, height=8, exportselection=False)
        listbox.pack(fill=tk.BOTH, expand=True)
        button_row = ttk.Frame(frame)
        button_row.pack(anchor=tk.W, pady=5)
        file_button = ttk.Button(button_row, text="选择文件", command=file_command)
        file_button.pack(side=tk.LEFT)
        folder_button = ttk.Button(button_row, text="选择文件夹扫描", command=folder_command)
        folder_button.pack(side=tk.LEFT, padx=6)
        if not self.a_widgets:
            self.a_widgets.extend([listbox, file_button, folder_button])
        return listbox

    def _bind_rule_changes(self) -> None:
        for var in (
            self.prefix_var,
            self.suffix_var,
            self.number_style_var,
            self.start_var,
            self.step_var,
            self.custom_template_var,
        ):
            var.trace_add("write", lambda *_args: self.refresh_preview())

    def choose_a(self) -> None:
        paths = filedialog.askopenfilenames(title="选择 A 组参考文件")
        if paths:
            self.name_files.extend(list(paths))
            self.refresh_lists()

    def choose_a_folder(self) -> None:
        path = filedialog.askdirectory(title="选择包含 A 组参考文件的文件夹")
        if path:
            self.name_folders.append(path)
            self.refresh_lists()

    def choose_b(self) -> None:
        paths = filedialog.askopenfilenames(title="选择 B 组目标文件")
        if paths:
            self.target_files.extend(list(paths))
            self.refresh_lists()

    def choose_b_folder(self) -> None:
        path = filedialog.askdirectory(title="选择包含 B 组目标文件的文件夹")
        if path:
            self.target_folders.append(path)
            self.refresh_lists()

    def choose_output(self) -> None:
        path = filedialog.askdirectory(title="选择重命名输出目录")
        if path:
            self.output_var.set(path)

    def _collect_files(self, files: list[str], folders: list[str], excluded: set[str]) -> list[Path]:
        result: list[Path] = []
        seen: set[str] = set()

        def add(path: Path) -> None:
            if not path.is_file():
                return
            key = str(path.resolve()).casefold()
            if key in excluded or key in seen:
                return
            seen.add(key)
            result.append(path)

        for item in files:
            add(Path(item))
        for folder in folders:
            root = Path(folder)
            if not root.is_dir():
                continue
            for path in root.rglob("*"):
                add(path)
        return natural_sorted(result)

    def current_name_files(self) -> list[Path]:
        return self._collect_files(self.name_files, self.name_folders, self.name_excluded)

    def current_target_files(self) -> list[Path]:
        return self._collect_files(self.target_files, self.target_folders, self.target_excluded)

    def refresh_lists(self) -> None:
        self.a_display_items = []
        self.a_list.delete(0, tk.END)
        for path in self.current_name_files():
            self.a_display_items.append(("file", str(path)))
            self.a_list.insert(tk.END, str(path))
        for folder in self.name_folders:
            self.a_display_items.append(("folder", folder))
            self.a_list.insert(tk.END, f"[文件夹扫描] {folder}")

        self.b_display_items = []
        self.b_list.delete(0, tk.END)
        for path in self.current_target_files():
            self.b_display_items.append(("file", str(path)))
            self.b_list.insert(tk.END, str(path))
        for folder in self.target_folders:
            self.b_display_items.append(("folder", folder))
            self.b_list.insert(tk.END, f"[文件夹扫描] {folder}")
        self.refresh_preview()

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

    def delete_selected_a(self) -> None:
        self._delete_selected(self.a_list, self.a_display_items, self.name_files, self.name_folders, self.name_excluded)

    def delete_selected_b(self) -> None:
        self._delete_selected(self.b_list, self.b_display_items, self.target_files, self.target_folders, self.target_excluded)

    def clear_a(self) -> None:
        self.name_files = []
        self.name_folders = []
        self.name_excluded.clear()
        self.refresh_lists()

    def clear_b(self) -> None:
        self.target_files = []
        self.target_folders = []
        self.target_excluded.clear()
        self.refresh_lists()

    def clear_all(self) -> None:
        self.clear_a()
        self.clear_b()
        self.log_frame.clear()

    def manual_rule(self) -> ManualRenameRule:
        return ManualRenameRule(
            prefix=self.prefix_var.get(),
            suffix=self.suffix_var.get(),
            number_style=self.number_style_var.get(),
            start=max(0, self.start_var.get()),
            step=max(1, self.step_var.get()),
            custom_template=self.custom_template_var.get(),
        )

    def current_pairs(self):
        targets = self.current_target_files()
        if self.mode_var.get() == "manual":
            return build_manual_pairs(targets, self.manual_rule())
        return build_pairs(self.current_name_files(), targets)

    def refresh_preview(self) -> None:
        if not hasattr(self, "preview"):
            return
        self.preview.delete(0, tk.END)
        if self.mode_var.get() == "manual":
            rule = self.manual_rule()
            examples = [format_manual_name(index, rule) for index in range(3)]
            self.example_var.set("示例：" + "，".join(examples))
        else:
            self.example_var.set("参考模式：B 组保留自己的扩展名，文件名套用 A 组。")
        pairs = self.current_pairs()
        if not pairs and self.mode_var.get() == "manual":
            for index in range(3):
                self.preview.insert(tk.END, f"示例文件{index + 1}.mp4 -> {format_manual_name(index, self.manual_rule())}.mp4")
            return
        for pair in pairs:
            self.preview.insert(tk.END, f"{pair.target_file.name} -> {pair.new_path.name}")

    def update_mode_state(self) -> None:
        reference_state = tk.NORMAL if self.mode_var.get() == "reference" else tk.DISABLED
        manual_state = tk.NORMAL if self.mode_var.get() == "manual" else tk.DISABLED
        for widget in self.a_widgets:
            widget.configure(state=reference_state)
        for widget in self.manual_widgets:
            widget.configure(state=manual_state)
        self.refresh_preview()

    def start(self, button: tk.Widget) -> None:
        targets = self.current_target_files()
        if not targets:
            messagebox.showwarning("未选择文件", "请先选择 B 组目标文件或文件夹。")
            return
        if self.mode_var.get() == "reference":
            names = self.current_name_files()
            if not names:
                messagebox.showwarning("未选择参考", "参考模式需要先选择 A 组参考文件。")
                return
            if len(names) != len(targets):
                ok = messagebox.askyesno(
                    "数量不一致",
                    f"A 组 {len(names)} 个，B 组 {len(targets)} 个。是否按较短一组继续？",
                )
                if not ok:
                    return

        def job() -> None:
            pairs = self.current_pairs()
            if not pairs:
                raise RuntimeError("没有可处理的重命名配对。")
            result = copy_by_pairs(pairs, self.output_var.get() or None, self.log_frame.write)
            self.log_frame.write(f"完成：成功复制 {result.success}，失败 {result.failed}。源文件未改动。")

        self.run_background(button, job)

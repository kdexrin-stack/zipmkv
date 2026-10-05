from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from common.file_selection import InputFileCollection, resolve_input_snapshot
from common.gui_base import ToolFrame, bind_listbox_delete_menu
from common.theme import configure_listbox

from .core import (
    ManualRenameRule,
    RenamePair,
    build_manual_pairs,
    build_pairs,
    copy_by_pairs,
    format_manual_name,
    rename_by_pairs,
)


class FeatureFrame(ToolFrame):
    title = "批量文件重命名"
    description = "用参考文件名配对，或按手动规则生成 ep01、01、前缀+序号+后缀 等新文件名，支持生成安全副本与原地改名。"

    def __init__(self, master):
        super().__init__(master)
        self.a_collection = InputFileCollection()
        self.b_collection = InputFileCollection()
        self.output_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="reference")
        self.action_mode_var = tk.StringVar(value="copy")
        self.prefix_var = tk.StringVar()
        self.suffix_var = tk.StringVar()
        self.number_style_var = tk.StringVar(value="ep01")
        self.start_var = tk.IntVar(value=1)
        self.step_var = tk.IntVar(value=1)
        self.custom_template_var = tk.StringVar(value="视频ep{num:02d}视频")
        self.example_var = tk.StringVar()
        self.preview_info_var = tk.StringVar(value="就绪")
        self.a_count_var = tk.StringVar(value="0 个文件")
        self.b_count_var = tk.StringVar(value="0 个文件")
        self.a_widgets: list[tk.Widget] = []
        self.manual_widgets: list[tk.Widget] = []
        self.copy_output_widgets: list[tk.Widget] = []
        self._preview_debounce_id: str | None = None
        self._build()
        self._bind_rule_changes()
        self.update_mode_state()
        self.update_action_mode_state()
        self.refresh_preview()

    def _build(self) -> None:
        # Step 1: Naming mode
        mode_frame = ttk.LabelFrame(self, text="Step 1 · 🔀 命名模式选择", style="Card.TLabelframe", padding=(12, 8))
        mode_frame.pack(fill=tk.X, pady=(4, 6))
        ttk.Radiobutton(
            mode_frame,
            text="参考 A 组文件名（一对一按自然顺序套用新名称）",
            value="reference",
            variable=self.mode_var,
            command=self.update_mode_state,
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            mode_frame,
            text="按规则自动生成（前缀/编号/后缀/自定义模板）",
            value="manual",
            variable=self.mode_var,
            command=self.update_mode_state,
        ).pack(side=tk.LEFT, padx=(24, 0))

        # Files dual panels
        panes = ttk.Frame(self)
        panes.pack(fill=tk.BOTH, expand=True, pady=(2, 6))

        self.a_list, self.a_badge = self._build_file_panel(
            panes,
            "A 组：参考名称源 (提取文件名)",
            self.choose_a,
            self.choose_a_folder,
            self.a_count_var,
        )
        bind_listbox_delete_menu(self.a_list, self.delete_selected_a, self.clear_a)

        self.b_list, self.b_badge = self._build_file_panel(
            panes,
            "B 组：待处理目标文件 (应用新名称)",
            self.choose_b,
            self.choose_b_folder,
            self.b_count_var,
        )
        bind_listbox_delete_menu(self.b_list, self.delete_selected_b, self.clear_b)

        # Step 2: Rules (Manual mode)
        rule_frame = ttk.LabelFrame(self, text="Step 2 · ⚙️ 编号与命名规则设置", style="Card.TLabelframe", padding=(10, 6))
        rule_frame.pack(fill=tk.X, pady=(2, 4))
        rule_frame.columnconfigure(7, weight=1)

        self._add_rule_label(rule_frame, "固定前缀", 0, 0)
        prefix_entry = ttk.Entry(rule_frame, textvariable=self.prefix_var, width=12)
        prefix_entry.grid(row=0, column=1, sticky=tk.W, padx=(4, 8))
        self.manual_widgets.append(prefix_entry)

        self._add_rule_label(rule_frame, "编号样式", 0, 2)
        style_combo = ttk.Combobox(
            rule_frame,
            textvariable=self.number_style_var,
            values=["1", "01", "001", "ep1", "ep01", "EP01", "E01", "自定义模板"],
            width=10,
            state="readonly",
        )
        style_combo.grid(row=0, column=3, sticky=tk.W, padx=(4, 8))
        style_combo.bind("<<ComboboxSelected>>", lambda _event: self._trigger_preview())
        self.manual_widgets.append(style_combo)

        self._add_rule_label(rule_frame, "固定后缀", 0, 4)
        suffix_entry = ttk.Entry(rule_frame, textvariable=self.suffix_var, width=12)
        suffix_entry.grid(row=0, column=5, sticky=tk.W, padx=(4, 8))
        self.manual_widgets.append(suffix_entry)

        self._add_rule_label(rule_frame, "起始序号", 1, 0)
        start_spin = ttk.Spinbox(rule_frame, from_=0, to=9999, width=5, textvariable=self.start_var)
        start_spin.grid(row=1, column=1, sticky=tk.W, padx=(4, 8), pady=(4, 0))
        self.manual_widgets.append(start_spin)

        self._add_rule_label(rule_frame, "递增步进", 1, 2)
        step_spin = ttk.Spinbox(rule_frame, from_=1, to=999, width=5, textvariable=self.step_var)
        step_spin.grid(row=1, column=3, sticky=tk.W, padx=(4, 8), pady=(4, 0))
        self.manual_widgets.append(step_spin)

        self._add_rule_label(rule_frame, "自定义模板", 1, 4)
        custom_entry = ttk.Entry(rule_frame, textvariable=self.custom_template_var, width=24)
        custom_entry.grid(row=1, column=5, columnspan=3, sticky=tk.EW, padx=(4, 0), pady=(4, 0))
        self.manual_widgets.append(custom_entry)

        ttk.Label(rule_frame, textvariable=self.example_var, style="Eyebrow.TLabel").grid(
            row=2,
            column=0,
            columnspan=8,
            sticky=tk.W,
            pady=(2, 0),
        )

        # Step 3: Action mode & Output dir
        action_frame = ttk.LabelFrame(self, text="Step 3 · 🎯 执行方式与输出", style="Card.TLabelframe", padding=(10, 6))
        action_frame.pack(fill=tk.X, pady=(2, 4))

        act_row = ttk.Frame(action_frame)
        act_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Radiobutton(
            act_row,
            text="生成重命名副本（安全推荐，复制到输出目录，保留源文件）",
            value="copy",
            variable=self.action_mode_var,
            command=self.update_action_mode_state,
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            act_row,
            text="直接原地重命名（直接修改当前文件，无需复制，节省磁盘空间）",
            value="rename",
            variable=self.action_mode_var,
            command=self.update_action_mode_state,
        ).pack(side=tk.LEFT, padx=(20, 0))

        output_row = ttk.Frame(action_frame)
        output_row.pack(fill=tk.X, pady=(2, 0))
        out_lbl = ttk.Label(output_row, text="输出目录")
        out_lbl.pack(side=tk.LEFT)
        out_entry = ttk.Entry(output_row, textvariable=self.output_var)
        out_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        out_btn = ttk.Button(output_row, text="浏览", command=self.choose_output)
        out_btn.pack(side=tk.LEFT)
        self.copy_output_widgets.extend([out_lbl, out_entry, out_btn])

        # Preview listbox
        preview_frame = ttk.LabelFrame(self, text="效果即时预览", style="Card.TLabelframe", padding=6)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(2, 4))
        prev_head = ttk.Frame(preview_frame)
        prev_head.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(prev_head, textvariable=self.preview_info_var, style="Badge.TLabel").pack(side=tk.LEFT)

        self.preview = tk.Listbox(preview_frame, height=3, exportselection=False)
        configure_listbox(self.preview)
        self.preview.pack(fill=tk.BOTH, expand=True)

        # Control row
        row = ttk.Frame(self)
        row.pack(fill=tk.X, pady=(4, 6))
        self.start_button = ttk.Button(row, text="▶ 执行重命名", style="Primary.TButton")
        self.start_button.config(command=lambda: self.start(self.start_button))
        self.start_button.pack(side=tk.LEFT)
        ttk.Button(row, text="📂 打开目标目录", style="OpenDir.TButton", command=self.reveal_output_folder).pack(side=tk.LEFT, padx=10)
        ttk.Button(row, text="刷新预览", command=self.refresh_preview).pack(side=tk.LEFT)
        ttk.Button(row, text="清空列表", command=self.clear_all).pack(side=tk.LEFT, padx=8)
        ttk.Button(row, text="清空日志", command=self.log_frame.clear).pack(side=tk.RIGHT)

        self.log_frame.pack(fill=tk.BOTH, expand=True)

    def _add_rule_label(self, master, text: str, row: int, column: int) -> None:
        label = ttk.Label(master, text=text)
        label.grid(row=row, column=column, sticky=tk.W, pady=(0 if row == 0 else 4, 0))
        self.manual_widgets.append(label)

    def _build_file_panel(self, master, title: str, file_command, folder_command, count_var: tk.StringVar):
        frame = ttk.LabelFrame(master, text=title, style="Card.TLabelframe", padding=6)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
        listbox = tk.Listbox(frame, height=3, exportselection=False)
        listbox.pack(fill=tk.BOTH, expand=True)
        button_row = ttk.Frame(frame)
        button_row.pack(fill=tk.X, pady=3)
        file_button = ttk.Button(button_row, text="+ 选择文件", command=file_command)
        file_button.pack(side=tk.LEFT)
        folder_button = ttk.Button(button_row, text="📁 扫描文件夹", command=folder_command)
        folder_button.pack(side=tk.LEFT, padx=4)
        badge = ttk.Label(button_row, textvariable=count_var, style="SidebarMuted.TLabel")
        badge.pack(side=tk.RIGHT, padx=4)
        if not self.a_widgets:
            self.a_widgets.extend([listbox, file_button, folder_button, badge])
        return listbox, badge

    def _bind_rule_changes(self) -> None:
        for var in (
            self.prefix_var,
            self.suffix_var,
            self.number_style_var,
            self.start_var,
            self.step_var,
            self.custom_template_var,
        ):
            var.trace_add("write", lambda *_args: self._trigger_preview())

    def _trigger_preview(self) -> None:
        if self._preview_debounce_id is not None:
            try:
                self.after_cancel(self._preview_debounce_id)
            except Exception:
                pass
        self._preview_debounce_id = self.after(50, self.refresh_preview)

    def choose_a(self) -> None:
        paths = filedialog.askopenfilenames(title="选择 A 组参考文件")
        if paths:
            self.a_collection.add_files(list(paths))
            self.refresh_lists()

    def choose_a_folder(self) -> None:
        path = filedialog.askdirectory(title="选择包含 A 组参考文件的文件夹")
        if path:
            self.a_collection.add_folder(path)
            self.refresh_lists()

    def choose_b(self) -> None:
        paths = filedialog.askopenfilenames(title="选择 B 组待处理目标文件")
        if paths:
            self.b_collection.add_files(list(paths))
            self.refresh_lists()

    def choose_b_folder(self) -> None:
        path = filedialog.askdirectory(title="选择包含 B 组目标文件的文件夹")
        if path:
            self.b_collection.add_folder(path)
            self.refresh_lists()

    def choose_output(self) -> None:
        path = filedialog.askdirectory(title="选择重命名副本输出目录")
        if path:
            self.output_var.set(path)

    def current_name_files(self) -> list[Path]:
        return self.a_collection.resolve_files()

    def current_target_files(self) -> list[Path]:
        return self.b_collection.resolve_files()

    def refresh_lists(self) -> None:
        self.a_list.delete(0, tk.END)
        for text, _ in self.a_collection.display_items:
            self.a_list.insert(tk.END, text)

        self.b_list.delete(0, tk.END)
        for text, _ in self.b_collection.display_items:
            self.b_list.insert(tk.END, text)

        a_direct = self.a_collection.direct_files()
        b_direct = self.b_collection.direct_files()
        a_folder_count = len(self.a_collection.visible_folders())
        b_folder_count = len(self.b_collection.visible_folders())
        self.a_count_var.set(
            f"直接文件 {len(a_direct)} 个" + (f" + 文件夹 {a_folder_count} 个（执行时扫描）" if a_folder_count else "")
        )
        self.b_count_var.set(
            f"直接文件 {len(b_direct)} 个" + (f" + 文件夹 {b_folder_count} 个（执行时扫描）" if b_folder_count else "")
        )
        self._trigger_preview()

    def delete_selected_a(self) -> None:
        self.a_collection.remove_indices(list(self.a_list.curselection()))
        self.refresh_lists()

    def delete_selected_b(self) -> None:
        self.b_collection.remove_indices(list(self.b_list.curselection()))
        self.refresh_lists()

    def clear_a(self) -> None:
        self.a_collection.clear()
        self.refresh_lists()

    def clear_b(self) -> None:
        self.b_collection.clear()
        self.refresh_lists()

    def clear_all(self) -> None:
        self.clear_a()
        self.clear_b()
        self.log_frame.clear()

    def manual_rule(self) -> ManualRenameRule:
        try:
            start = max(0, int(self.start_var.get()))
        except Exception:
            start = 1
        try:
            step = max(1, int(self.step_var.get()))
        except Exception:
            step = 1
        return ManualRenameRule(
            prefix=self.prefix_var.get(),
            suffix=self.suffix_var.get(),
            number_style=self.number_style_var.get(),
            start=start,
            step=step,
            custom_template=self.custom_template_var.get(),
        )

    def current_pairs(self) -> list[RenamePair]:
        targets = self.current_target_files()
        if not targets:
            return []
        if self.mode_var.get() == "manual":
            return build_manual_pairs(targets, self.manual_rule())
        return build_pairs(self.current_name_files(), targets)

    def refresh_preview(self) -> None:
        self._preview_debounce_id = None
        if not hasattr(self, "preview"):
            return
        self.preview.delete(0, tk.END)
        if self.mode_var.get() == "manual":
            rule = self.manual_rule()
            examples = [format_manual_name(index, rule) for index in range(3)]
            self.example_var.set("示例：" + "，".join(examples))
        else:
            self.example_var.set("参考模式：B 组保留自己的文件后缀，主文件名一一套用 A 组。")

        preview_targets = self.b_collection.direct_files()
        preview_names = self.a_collection.direct_files()
        if self.mode_var.get() == "manual":
            pairs = build_manual_pairs(preview_targets, self.manual_rule())
        else:
            pairs = build_pairs(preview_names, preview_targets)
        if not pairs and self.mode_var.get() == "manual":
            self.preview_info_var.set("演示样例预览 (请在上方添加 B 组目标文件)")
            rule = self.manual_rule()
            for index in range(3):
                self.preview.insert(tk.END, f"示例视频{index + 1}.mp4  ➔  {format_manual_name(index, rule)}.mp4")
            return

        if not pairs:
            self.preview_info_var.set("等待输入：请选择文件或文件夹")
            return

        max_display = 100
        total = len(pairs)
        self.preview_info_var.set(
            f"已生成 {total} 项重命名配对" + (f" (前 {max_display} 项预览)" if total > max_display else "")
        )
        for pair in pairs[:max_display]:
            self.preview.insert(tk.END, f"{pair.target_file.name}  ➔  {pair.new_path.name}")
        if total > max_display:
            self.preview.insert(tk.END, f"... 共 {total} 项配对，已截断显示以保障流畅操作 ...")

    def update_mode_state(self) -> None:
        is_ref = self.mode_var.get() == "reference"
        reference_state = tk.NORMAL if is_ref else tk.DISABLED
        manual_state = tk.NORMAL if not is_ref else tk.DISABLED
        for widget in self.a_widgets:
            widget.configure(state=reference_state)
        for widget in self.manual_widgets:
            widget.configure(state=manual_state)
        self._trigger_preview()

    def update_action_mode_state(self) -> None:
        is_copy = self.action_mode_var.get() == "copy"
        state = tk.NORMAL if is_copy else tk.DISABLED
        for widget in self.copy_output_widgets:
            widget.configure(state=state)
        if is_copy:
            self.start_button.config(text="▶ 生成重命名副本")
        else:
            self.start_button.config(text="⚠️ 原地重命名源文件")

    def start(self, button: tk.Widget) -> None:
        target_snapshot = self.b_collection.snapshot()
        name_snapshot = self.a_collection.snapshot()
        if not target_snapshot.has_inputs:
            messagebox.showwarning("未选择文件", "请先选择 B 组目标文件或文件夹。")
            return

        mode = self.mode_var.get()
        action_mode = self.action_mode_var.get()
        rule = self.manual_rule()
        output_dir = self.output_var.get().strip() or None

        if mode == "reference" and not name_snapshot.has_inputs:
            messagebox.showwarning("未选择参考", "参考模式需要先在 A 组选择参考文件。")
            return
        direct_targets = self.b_collection.direct_files()
        direct_names = self.a_collection.direct_files()
        if mode == "reference" and not target_snapshot.folders and not name_snapshot.folders and len(direct_names) != len(direct_targets):
            ok = messagebox.askyesno(
                "数量不一致",
                f"A 组参考文件 {len(direct_names)} 个，B 组目标文件 {len(direct_targets)} 个。\n是否按较短的一组 ({min(len(direct_names), len(direct_targets))} 个) 继续执行？",
            )
            if not ok:
                return

        if action_mode == "rename":
            confirm = messagebox.askyesno(
                "确认原地直接重命名",
                "⚠️ 注意：即将直接修改 B 组源文件名。\n文件夹输入会在后台递归扫描，冲突文件会跳过并记录日志。\n\n是否确认立即执行？",
            )
            if not confirm:
                return

        def job() -> str:
            targets = resolve_input_snapshot(target_snapshot)
            names = resolve_input_snapshot(name_snapshot)
            if not targets:
                raise RuntimeError("B 组中没有找到可处理的文件。请检查文件夹内容。")
            if mode == "manual":
                active_pairs = build_manual_pairs(targets, rule)
            else:
                if not names:
                    raise RuntimeError("A 组中没有找到可用的参考文件。")
                if len(names) != len(targets):
                    self.log_frame.write(
                        f"提示：A 组 {len(names)} 个、B 组 {len(targets)} 个，按较短一组配对。"
                    )
                active_pairs = build_pairs(names, targets)
            if not active_pairs:
                raise RuntimeError("没有可处理的重命名配对。")
            if action_mode == "rename":
                result = rename_by_pairs(active_pairs, self.log_frame.write)
                self.log_frame.write(
                    f"原地重命名完成：成功 {result.success}，跳过 {result.skipped}，失败 {result.failed}。"
                )
                if active_pairs:
                    self.last_output_dir = active_pairs[0].target_file.parent
                self.call_in_ui(self.refresh_lists)
                return f"原地重命名完成 (成功 {result.success})"
            else:
                result = copy_by_pairs(active_pairs, output_dir, self.log_frame.write)
                self.log_frame.write(
                    f"副本生成完成：成功复制 {result.success}，跳过 {result.skipped}，失败 {result.failed}。源文件未改动。"
                )
                if active_pairs:
                    out_dir = Path(output_dir) if output_dir else (active_pairs[0].target_file.parent / "重命名输出")
                    self.last_output_dir = out_dir
                return f"已生成重命名副本 (成功 {result.success})"

        default_out = Path(output_dir) if output_dir else (
            target_snapshot.files[0].parent if target_snapshot.files else target_snapshot.folders[0]
        )
        self.run_background(button, job, output_dir=default_out)

from __future__ import annotations

import importlib
import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.paths import ensure_runtime_dirs
from common.theme import COLORS, FONT_FAMILY, apply_app_theme, enable_high_dpi_awareness
from common.haruhi_theme import HARUHI_THEME
from common.ui_components import Tooltip, decorate_buttons, icon_button, icon_image
from features import FEATURES, FeatureSpec

APP_VERSION = "1.3.1"

FEATURE_ICONS = {
    "image_archive_pdf": "file-stack", "rename_files": "file-pen-line",
    "subtitles": "captions", "xml_danmaku": "messages-square",
    "zh_convert": "languages", "language_tools": "scan-text",
}


class ZipMkvApp(tk.Tk):
    def __init__(self):
        enable_high_dpi_awareness()
        super().__init__()
        self.title("zipmkv · 媒体与字幕工具箱")
        self.geometry("1240x760")
        self.minsize(1020, 640)
        ensure_runtime_dirs()
        apply_app_theme(self)
        self.configure(bg=COLORS["bg"])
        self._loaded_frames: dict[str, ttk.Frame] = {}
        self.current_frame: ttk.Frame | None = None
        self.current_feature: FeatureSpec | None = None
        self.feature_iids: dict[str, str] = {}
        self.feature_by_iid: dict[str, FeatureSpec] = {}
        self.group_iids = {}
        self.search_var = tk.StringVar()
        self.category_var = tk.StringVar()
        self.haruhi_btn_text = tk.StringVar(value=f"🌸 凉宫春日立绘: {HARUHI_THEME.status_label}")
        self.module_index_var = tk.StringVar()
        self.status_var = tk.StringVar(value="就绪")
        self._build()
        self.load_feature(FEATURES[0])
        self._schedule_startup_probe()

    def _schedule_startup_probe(self) -> None:
        marker_value = os.environ.get("ZIPMKV_STARTUP_PROBE")
        if not marker_value:
            return

        marker = Path(marker_value)

        def complete_probe() -> None:
            try:
                if os.environ.get("ZIPMKV_PROBE_TOOLS"):
                    from common.archive_tools import find_archive_tools
                    from common.media_tools import find_ffmpeg, run_hidden

                    for feature in FEATURES:
                        self.load_feature(feature)
                        self.update_idletasks()
                    if not find_archive_tools():
                        raise RuntimeError("bundled 7-Zip was not found")
                    ffmpeg = find_ffmpeg()
                    if not ffmpeg:
                        raise RuntimeError("bundled FFmpeg was not found")
                    result = run_hidden([str(ffmpeg), "-version"], timeout=30)
                    if result.returncode != 0:
                        raise RuntimeError("bundled FFmpeg did not execute")
                marker.parent.mkdir(parents=True, exist_ok=True)
                marker.write_text("ready\n", encoding="utf-8")
            except Exception as exc:
                marker.parent.mkdir(parents=True, exist_ok=True)
                marker.write_text(f"error: {exc}\n", encoding="utf-8")
            finally:
                self.destroy()

        self.after(500, complete_probe)

    def _build(self) -> None:
        root = ttk.Frame(self, style="App.TFrame")
        root.pack(fill=tk.BOTH, expand=True)

        sidebar = ttk.Frame(root, width=256, padding=(16, 18), style="Sidebar.TFrame")
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 0))
        sidebar.pack_propagate(False)

        # Subtle divider between sidebar and main workspace
        tk.Frame(root, width=1, bg=COLORS["border"]).pack(side=tk.LEFT, fill=tk.Y)

        brand = ttk.Frame(sidebar, style="Sidebar.TFrame")
        brand.pack(fill=tk.X, pady=(0, 18))
        tk.Label(
            brand,
            image=icon_image(self, "archive", 26, "#ffffff"),
            bg=COLORS["primary"],
            fg="#ffffff",
            padx=9,
            pady=9,
            font=(FONT_FAMILY, 14, "bold"),
            bd=0,
        ).pack(side=tk.LEFT, padx=(0, 10))
        brand_text = ttk.Frame(brand, style="Sidebar.TFrame")
        brand_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(brand_text, text="zipmkv", style="AppTitle.TLabel").pack(anchor=tk.W)
        ttk.Label(brand_text, text=f"DESKTOP v{APP_VERSION}", style="SidebarMuted.TLabel").pack(anchor=tk.W)

        search_row = ttk.Frame(sidebar, style="Sidebar.TFrame")
        search_row.pack(fill=tk.X, pady=(0, 14))
        ttk.Label(search_row, image=icon_image(self, "search", 18)).pack(side=tk.LEFT, padx=(0, 5))
        search_entry = ttk.Entry(search_row, textvariable=self.search_var, width=16)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        Tooltip(search_entry, "搜索模块")
        self.search_var.trace_add("write", lambda *_args: self.filter_features())

        groups: dict[str, list[FeatureSpec]] = {}
        for feature in FEATURES:
            groups.setdefault(feature.category, []).append(feature)

        tree_height = len(FEATURES) + len(groups)
        self.feature_tree = ttk.Treeview(
            sidebar,
            show="tree",
            selectmode="browse",
            style="Nav.Treeview",
            height=tree_height,
            takefocus=True,
        )
        self.feature_tree.column("#0", width=218, stretch=True)
        self.feature_tree.pack(fill=tk.BOTH, expand=True)
        for group_index, (category, features) in enumerate(groups.items()):
            group_iid = f"group_{group_index}"
            self.group_iids[category] = group_iid
            self.feature_tree.insert("", tk.END, iid=group_iid, text=category, open=True, tags=("category",))
            for feature in features:
                iid = f"feature_{feature.key}"
                self.feature_tree.insert(
                    group_iid, tk.END, iid=iid, text=f"  {feature.nav_title or feature.title}",
                    image=icon_image(self, FEATURE_ICONS.get(feature.key, "archive"), 18), tags=("feature",),
                )
                self.feature_iids[feature.key] = iid
                self.feature_by_iid[iid] = feature
        self.feature_tree.tag_configure(
            "category",
            foreground=COLORS["sidebar_muted"],
            background=COLORS["sidebar"],
            font=(FONT_FAMILY, 9, "bold"),
        )
        self.feature_tree.bind("<<TreeviewSelect>>", self.on_select)

        sidebar_footer = ttk.Frame(sidebar, style="Sidebar.TFrame")
        sidebar_footer.pack(side=tk.BOTTOM, fill=tk.X, pady=(12, 0))
        ttk.Separator(sidebar_footer).pack(fill=tk.X, pady=(0, 8))
        self.figure_slot = ttk.Frame(sidebar_footer, height=132, style="Sidebar.TFrame")
        self.figure_slot.pack(fill=tk.X)
        self.figure_slot.pack_propagate(False)
        footer_tools = ttk.Frame(sidebar_footer)
        footer_tools.pack(fill=tk.X, pady=(6, 8))
        for name, command, label in (
            ("settings-2", self.cycle_haruhi_opacity, "立绘显示强度"),
            ("image", self.choose_custom_haruhi_image, "自定义侧栏图片"),
            ("folder-open", self.open_runtime_dir, "运行目录"),
            ("code-xml", self.show_extension_help, "扩展模块指南"),
        ):
            icon_button(footer_tools, name, command, label).pack(side=tk.LEFT, padx=2)
        ttk.Label(sidebar_footer, text="离线处理 · 默认保留源文件", style="SidebarMuted.TLabel").pack(anchor=tk.W)

        content_shell = ttk.Frame(root, padding=(16, 12), style="App.TFrame")
        content_shell.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.header = ttk.Frame(content_shell, style="Header.TFrame", padding=(14, 8))
        self.header.pack(fill=tk.X, pady=(0, 8))
        self.feature_icon = tk.Label(self.header, bg=COLORS["primary_soft"], padx=10, pady=10)
        self.feature_icon.pack(side=tk.LEFT, padx=(0, 12))
        header_text = ttk.Frame(self.header, style="Header.TFrame")
        header_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.page_title_var = tk.StringVar()
        self.page_desc_var = tk.StringVar()
        ttk.Label(header_text, textvariable=self.category_var, style="Eyebrow.TLabel").pack(anchor=tk.W)
        ttk.Label(header_text, textvariable=self.page_title_var, style="PageTitle.TLabel").pack(anchor=tk.W, pady=(1, 0))
        ttk.Label(
            header_text,
            textvariable=self.page_desc_var,
            style="Muted.TLabel",
            wraplength=720,
        ).pack(anchor=tk.W, pady=(2, 0))
        
        index_badge = tk.Label(
            self.header,
            textvariable=self.module_index_var,
            bg=COLORS["primary_soft"],
            fg=COLORS["primary"],
            font=(FONT_FAMILY, 9, "bold"),
            padx=10,
            pady=4,
            bd=0,
        )
        index_badge.pack(side=tk.RIGHT, anchor=tk.NE)

        status = ttk.Frame(content_shell, style="Status.TFrame", padding=(12, 6))
        status.pack(side=tk.BOTTOM, fill=tk.X, pady=(6, 0))
        self.status_dot = tk.Frame(status, width=8, height=8, bg=COLORS["success"])
        self.status_dot.pack(side=tk.LEFT, padx=(0, 8))
        self.status_label = ttk.Label(status, textvariable=self.status_var, style="Status.TLabel", wraplength=650)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.task_progress = ttk.Progressbar(status, mode="determinate", maximum=100, length=105)
        self.task_progress.pack(side=tk.RIGHT, padx=(8, 0))

        self.content = ttk.Frame(content_shell, padding=0, style="Workspace.TFrame")
        self.content.pack(fill=tk.BOTH, expand=True)
        self.content.rowconfigure(0, weight=1)
        self.content.columnconfigure(0, weight=1)
        self.content_canvas = tk.Canvas(
            self.content,
            bg=COLORS["surface"],
            highlightthickness=0,
            bd=0,
        )
        self.content_canvas.grid(row=0, column=0, sticky=tk.NSEW)
        self.content_vscroll = ttk.Scrollbar(self.content, orient=tk.VERTICAL, command=self.content_canvas.yview)
        self.content_vscroll.grid(row=0, column=1, sticky=tk.NS)
        self.content_hscroll = ttk.Scrollbar(self.content, orient=tk.HORIZONTAL, command=self.content_canvas.xview)
        self.content_hscroll.grid(row=1, column=0, sticky=tk.EW)
        self.content_canvas.configure(
            yscrollcommand=self.content_vscroll.set,
            xscrollcommand=self.content_hscroll.set,
        )
        self.content_window: int | None = None

        self.haruhi_watermark_label = tk.Label(self.figure_slot, bg=COLORS["sidebar"], bd=0, cursor="hand2")
        self.haruhi_watermark_label.bind("<Button-1>", lambda _e: self.cycle_haruhi_opacity())
        Tooltip(self.haruhi_watermark_label, "切换侧栏图片强度")
        self._haruhi_debounce_id: str | None = None

        # Global shortcuts
        self.bind_all("<Control-Return>", lambda _e: self._trigger_primary_action())
        self.bind_all("<F5>", lambda _e: self._trigger_primary_action())
        self.bind_all("<Control-e>", lambda _e: self._trigger_reveal_output())
        self.bind_all("<Control-E>", lambda _e: self._trigger_reveal_output())
        self.bind_all("<Control-l>", lambda _e: self._trigger_clear_log())
        self.bind_all("<Control-L>", lambda _e: self._trigger_clear_log())

    def _trigger_primary_action(self) -> None:
        if not self.current_frame or getattr(self, "_active_tool", None) is not None:
            return
        for attr in ("primary_action_button", "start_button"):
            btn = getattr(self.current_frame, attr, None)
            if btn and btn.cget("state") != tk.DISABLED:
                btn.invoke()
                return
        for child in self.current_frame.winfo_children():
            if isinstance(child, ttk.Button) and "Primary" in str(child.cget("style")):
                if child.cget("state") != tk.DISABLED:
                    child.invoke()
                    return

    def _trigger_reveal_output(self) -> None:
        if self.current_frame and hasattr(self.current_frame, "reveal_output_folder"):
            self.current_frame.reveal_output_folder()

    def _trigger_clear_log(self) -> None:
        if self.current_frame and hasattr(self.current_frame, "log_frame"):
            self.current_frame.log_frame.clear()

    def cycle_haruhi_opacity(self) -> None:
        HARUHI_THEME.cycle_opacity()
        self.haruhi_btn_text.set(f"🌸 凉宫春日立绘: {HARUHI_THEME.status_label}")
        self._update_haruhi_watermark()

    def choose_custom_haruhi_image(self) -> None:
        path = filedialog.askopenfilename(
            title="选择自定义背景/立绘图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.webp *.bmp"), ("所有文件", "*.*")],
        )
        if path:
            HARUHI_THEME.set_custom_image(Path(path))
            self.haruhi_btn_text.set(f"🌸 凉宫春日立绘: {HARUHI_THEME.status_label}")
            self._update_haruhi_watermark()

    def _update_haruhi_watermark(self) -> None:
        if not hasattr(self, "haruhi_watermark_label"):
            return
        if self._haruhi_debounce_id:
            try:
                self.after_cancel(self._haruhi_debounce_id)
            except Exception:
                pass
        self._haruhi_debounce_id = self.after(80, self._render_haruhi_watermark_now)

    def _render_haruhi_watermark_now(self) -> None:
        self._haruhi_debounce_id = None
        if not HARUHI_THEME.enabled:
            self.haruhi_watermark_label.place_forget()
            return
        target_height = 130
        img = HARUHI_THEME.get_blended_figure(target_height, COLORS["surface"])
        if img:
            self.haruhi_watermark_label.configure(image=img)
            self.haruhi_watermark_label.image = img
            self.haruhi_watermark_label.place(relx=0.5, rely=1.0, anchor="s")
        else:
            self.haruhi_watermark_label.place_forget()

    def on_select(self, event=None) -> None:
        selection = self.feature_tree.selection()
        if not selection:
            return
        feature = self.feature_by_iid.get(selection[0])
        if feature is None:
            if self.current_feature:
                self.after_idle(lambda: self.feature_tree.selection_set(self.feature_iids[self.current_feature.key]))
            return
        self.load_feature(feature)

    def filter_features(self) -> None:
        if not hasattr(self, "feature_tree"):
            return
        query = self.search_var.get().strip().casefold()
        for category, group_iid in self.group_iids.items():
            visible = [feature for feature in FEATURES if feature.category == category and query in
                       f"{feature.title} {feature.nav_title or ''} {feature.description} {feature.key}".casefold()]
            self.feature_tree.move(group_iid, "", tk.END)
            for feature in FEATURES:
                if feature.category == category:
                    iid = self.feature_iids[feature.key]
                    if feature in visible:
                        self.feature_tree.move(iid, group_iid, tk.END)
                    else:
                        self.feature_tree.detach(iid)
            if not visible:
                self.feature_tree.detach(group_iid)

    def set_task_state(self, state: str) -> None:
        self.task_progress.stop()
        self.status_dot.configure(bg=COLORS["error"] if state == "error" else COLORS["primary"] if state == "running" else COLORS["success"])
        if state == "running":
            self.task_progress.configure(mode="indeterminate")
            self.task_progress.start(20)
        else:
            self.task_progress.configure(mode="determinate", value=100 if state == "success" else 0)

    def load_feature(self, feature: FeatureSpec) -> None:
        if self.current_feature == feature and self.current_frame is not None:
            return
        frame = self._loaded_frames.get(feature.key)
        if frame is None:
            try:
                module = importlib.import_module(feature.module)
                frame_class = getattr(module, feature.frame_class)
                frame = frame_class(self.content_canvas)
                decorate_buttons(frame)
                self._loaded_frames[feature.key] = frame
            except Exception as exc:
                messagebox.showerror("加载失败", f"{feature.title} 加载失败:\n{exc}")
                return
        self.current_frame = frame
        self.current_feature = feature
        self.content_canvas.delete("all")
        self.content_canvas.xview_moveto(0)
        self.content_canvas.yview_moveto(0)
        self.content_window = self.content_canvas.create_window((0, 0), window=frame, anchor=tk.NW)
        frame.bind("<Configure>", self._sync_content_scrollregion)
        self.content_canvas.bind("<Configure>", self._resize_content_window)
        self.after_idle(self._layout_content_window)
        feature_index = FEATURES.index(feature) + 1
        self.category_var.set(feature.category.upper())
        self.page_title_var.set(feature.title)
        self.feature_icon.configure(image=icon_image(self, FEATURE_ICONS.get(feature.key, "archive"), 26))
        self.page_desc_var.set(feature.description)
        self.module_index_var.set(f"{feature_index:02d} / {len(FEATURES):02d}")
        self.status_var.set(f"{feature.title} · {'处理中' if getattr(frame, '_busy', False) else '就绪'}")
        iid = self.feature_iids[feature.key]
        self.feature_tree.selection_set(iid)
        self.feature_tree.focus(iid)
        self.feature_tree.see(iid)

    def _sync_content_scrollregion(self, _event=None) -> None:
        self.content_canvas.configure(scrollregion=self.content_canvas.bbox("all"))

    def _resize_content_window(self, _event=None) -> None:
        self._layout_content_window()

    def _layout_content_window(self) -> None:
        if self.current_frame is None or self.content_window is None:
            return
        width = max(self.content_canvas.winfo_width(), 740)
        self.content_canvas.itemconfigure(self.content_window, width=width)
        height = max(self.content_canvas.winfo_height(), self.current_frame.winfo_reqheight())
        self.content_canvas.itemconfigure(self.content_window, height=height)
        self._sync_content_scrollregion()
        self._update_haruhi_watermark()

    def _render_background_watermark(self, width: int, height: int) -> None:
        """Compatibility hook retained for older callers."""
        self._update_haruhi_watermark()

    def open_runtime_dir(self) -> None:
        root = ensure_runtime_dirs()["root"]
        try:
            if sys.platform.startswith("win"):
                import os

                os.startfile(root)
            else:
                messagebox.showinfo("运行目录", str(root))
        except Exception:
            messagebox.showinfo("运行目录", str(root))

    def show_extension_help(self) -> None:
        messagebox.showinfo(
            "扩展方式",
            "新增功能时：\n"
            "1. 在 zipmkv 下新建一个功能文件夹。\n"
            "2. 提供 core.py、gui.py、main.py。\n"
            "3. gui.py 暴露 FeatureFrame 类。\n"
            "4. 在 features.py 的 FEATURES 列表中添加一项并指定 category。\n",
        )


def main() -> None:
    ZipMkvApp().mainloop()


if __name__ == "__main__":
    main()

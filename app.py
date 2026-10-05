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
from features import FEATURES, FeatureSpec

APP_VERSION = "1.2.1"


class ZipMkvApp(tk.Tk):
    def __init__(self):
        enable_high_dpi_awareness()
        super().__init__()
        self.title("zipmkv 工具箱 · SOS团特别版")
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

        sidebar = ttk.Frame(root, width=280, padding=(18, 20), style="Sidebar.TFrame")
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 0))
        sidebar.pack_propagate(False)

        # Subtle divider between sidebar and main workspace
        tk.Frame(root, width=1, bg=COLORS["border"]).pack(side=tk.LEFT, fill=tk.Y)

        brand = ttk.Frame(sidebar, style="Sidebar.TFrame")
        brand.pack(fill=tk.X, pady=(0, 18))
        tk.Label(
            brand,
            text="Z",
            bg=COLORS["primary"],
            fg="#ffffff",
            width=2,
            height=1,
            font=(FONT_FAMILY, 14, "bold"),
            bd=0,
        ).pack(side=tk.LEFT, padx=(0, 10))
        brand_text = ttk.Frame(brand, style="Sidebar.TFrame")
        brand_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(brand_text, text="zipmkv", style="AppTitle.TLabel").pack(anchor=tk.W)
        ttk.Label(brand_text, text=f"DESKTOP v{APP_VERSION}", style="SidebarMuted.TLabel").pack(anchor=tk.W)

        ttk.Label(sidebar, text="功能模块导航", style="SidebarSection.TLabel").pack(anchor=tk.W, pady=(0, 8))

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
        self.feature_tree.column("#0", width=238, stretch=True)
        self.feature_tree.pack(fill=tk.BOTH, expand=True)
        for group_index, (category, features) in enumerate(groups.items()):
            group_iid = f"group_{group_index}"
            self.feature_tree.insert("", tk.END, iid=group_iid, text=f"▾ {category}", open=True, tags=("category",))
            for feature in features:
                iid = f"feature_{feature.key}"
                self.feature_tree.insert(group_iid, tk.END, iid=iid, text=f"  {feature.nav_title or feature.title}", tags=("feature",))
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
        ttk.Button(sidebar_footer, textvariable=self.haruhi_btn_text, command=self.cycle_haruhi_opacity, style="Sidebar.TButton").pack(fill=tk.X, pady=(0, 4))
        ttk.Button(sidebar_footer, text="🖼️ 自定义春日图片", command=self.choose_custom_haruhi_image, style="Sidebar.TButton").pack(fill=tk.X, pady=(0, 4))
        ttk.Button(sidebar_footer, text="打开运行目录", command=self.open_runtime_dir, style="Sidebar.TButton").pack(fill=tk.X)
        ttk.Button(sidebar_footer, text="扩展模块指南", command=self.show_extension_help, style="Sidebar.TButton").pack(fill=tk.X, pady=(4, 0))
        ttk.Label(sidebar_footer, text="SOS团 · 本地私有安全运行", style="SidebarMuted.TLabel").pack(anchor=tk.W, pady=(8, 0))

        content_shell = ttk.Frame(root, padding=(16, 12), style="App.TFrame")
        content_shell.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.header = ttk.Frame(content_shell, style="Header.TFrame", padding=(14, 8))
        self.header.pack(fill=tk.X, pady=(0, 8))
        tk.Frame(self.header, width=4, bg=COLORS["primary"]).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
        header_text = ttk.Frame(self.header, style="Header.TFrame")
        header_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.page_title_var = tk.StringVar()
        self.page_desc_var = tk.StringVar()
        ttk.Label(header_text, textvariable=self.category_var, style="Eyebrow.TLabel").pack(anchor=tk.W)
        ttk.Label(header_text, textvariable=self.page_title_var, style="PageTitle.TLabel").pack(anchor=tk.W, pady=(1, 0))
        ttk.Label(header_text, textvariable=self.page_desc_var, style="Muted.TLabel").pack(anchor=tk.W, pady=(2, 0))
        
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
        tk.Frame(status, width=8, height=8, bg=COLORS["success"]).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(status, textvariable=self.status_var, style="Status.TLabel").pack(side=tk.LEFT)
        ttk.Label(status, text="快捷键: Ctrl+Enter 执行 · Ctrl+E 输出 · Ctrl+L 清空日志", style="Status.TLabel").pack(side=tk.RIGHT)

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

        self.haruhi_watermark_label = tk.Label(self.content, bg=COLORS["surface"], bd=0, cursor="hand2")
        self.haruhi_watermark_label.bind("<Button-1>", lambda _e: self.cycle_haruhi_opacity())
        self.haruhi_watermark_label.bind(
            "<Enter>",
            lambda _e: self.status_var.set(f"🌸 凉宫春日立绘 ({HARUHI_THEME.status_label}) · 点击切换透明度 · 团长正在注视你的工作！"),
        )
        self.haruhi_watermark_label.bind(
            "<Leave>",
            lambda _e: self.status_var.set(f"{self.current_feature.title if self.current_feature else 'zipmkv'} · 就绪"),
        )
        self._haruhi_debounce_id: str | None = None

        # Global shortcuts
        self.bind_all("<Control-Return>", lambda _e: self._trigger_primary_action())
        self.bind_all("<F5>", lambda _e: self._trigger_primary_action())
        self.bind_all("<Control-e>", lambda _e: self._trigger_reveal_output())
        self.bind_all("<Control-E>", lambda _e: self._trigger_reveal_output())
        self.bind_all("<Control-l>", lambda _e: self._trigger_clear_log())
        self.bind_all("<Control-L>", lambda _e: self._trigger_clear_log())

    def _trigger_primary_action(self) -> None:
        if not self.current_frame:
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
        h = self.content.winfo_height()
        if h < 100:
            h = 500
        raw_height = max(180, min(380, int(h * 0.52)))
        target_height = (raw_height // 30) * 30
        img = HARUHI_THEME.get_blended_figure(target_height, COLORS["surface"])
        if img:
            self.haruhi_watermark_label.configure(image=img)
            self.haruhi_watermark_label.image = img
            self.haruhi_watermark_label.place(relx=1.0, rely=1.0, anchor="se", x=-16, y=-16)
            self.haruhi_watermark_label.lift()
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

    def load_feature(self, feature: FeatureSpec) -> None:
        if self.current_feature == feature and self.current_frame is not None:
            return
        frame = self._loaded_frames.get(feature.key)
        if frame is None:
            try:
                module = importlib.import_module(feature.module)
                frame_class = getattr(module, feature.frame_class)
                frame = frame_class(self.content_canvas)
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
        self.page_desc_var.set(feature.description)
        self.module_index_var.set(f"{feature_index:02d} / {len(FEATURES):02d}")
        self.status_var.set(f"{feature.title} · 就绪")
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
        width = max(self.content_canvas.winfo_width(), 900)
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

from __future__ import annotations

import importlib
import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.paths import ensure_runtime_dirs
from common.theme import COLORS, FONT_FAMILY, apply_app_theme, enable_high_dpi_awareness
from features import FEATURES, FeatureSpec

APP_VERSION = "1.1.1"


class ZipMkvApp(tk.Tk):
    def __init__(self):
        enable_high_dpi_awareness()
        super().__init__()
        self.title("zipmkv 工具箱")
        self.geometry("1360x840")
        self.minsize(1080, 680)
        ensure_runtime_dirs()
        apply_app_theme(self)
        self.configure(bg=COLORS["bg"])
        self.current_frame: ttk.Frame | None = None
        self.current_feature: FeatureSpec | None = None
        self.feature_iids: dict[str, str] = {}
        self.feature_by_iid: dict[str, FeatureSpec] = {}
        self.category_var = tk.StringVar()
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

        sidebar = ttk.Frame(root, width=286, padding=(20, 22), style="Sidebar.TFrame")
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 1))
        sidebar.pack_propagate(False)

        brand = ttk.Frame(sidebar, style="Sidebar.TFrame")
        brand.pack(fill=tk.X, pady=(0, 24))
        tk.Label(
            brand,
            text="Z",
            bg=COLORS["surface"],
            fg=COLORS["primary_hover"],
            width=2,
            height=1,
            font=(FONT_FAMILY, 18, "bold"),
            bd=0,
        ).pack(side=tk.LEFT, padx=(0, 11))
        brand_text = ttk.Frame(brand, style="Sidebar.TFrame")
        brand_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(brand_text, text="zipmkv", style="AppTitle.TLabel").pack(anchor=tk.W)
        ttk.Label(brand_text, text=f"DESKTOP  {APP_VERSION}", style="SidebarMuted.TLabel").pack(anchor=tk.W)

        ttk.Label(sidebar, text="工作区", style="SidebarSection.TLabel").pack(anchor=tk.W, pady=(0, 8))

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
            self.feature_tree.insert("", tk.END, iid=group_iid, text=category, open=True, tags=("category",))
            for feature in features:
                iid = f"feature_{feature.key}"
                self.feature_tree.insert(group_iid, tk.END, iid=iid, text=feature.nav_title or feature.title, tags=("feature",))
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
        sidebar_footer.pack(side=tk.BOTTOM, fill=tk.X, pady=(18, 0))
        ttk.Separator(sidebar_footer).pack(fill=tk.X, pady=(0, 14))
        ttk.Button(sidebar_footer, text="打开运行目录", command=self.open_runtime_dir, style="Sidebar.TButton").pack(fill=tk.X)
        ttk.Button(sidebar_footer, text="扩展模块", command=self.show_extension_help, style="Sidebar.TButton").pack(fill=tk.X, pady=(8, 0))
        ttk.Label(sidebar_footer, text="LOCAL · PRIVATE", style="SidebarMuted.TLabel").pack(anchor=tk.W, pady=(15, 0))

        content_shell = ttk.Frame(root, padding=(24, 20), style="App.TFrame")
        content_shell.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.header = ttk.Frame(content_shell, style="Header.TFrame")
        self.header.pack(fill=tk.X, pady=(0, 14))
        tk.Frame(self.header, width=5, bg=COLORS["accent"]).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        header_text = ttk.Frame(self.header, style="Header.TFrame", padding=(0, 9))
        header_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.page_title_var = tk.StringVar()
        self.page_desc_var = tk.StringVar()
        ttk.Label(header_text, textvariable=self.category_var, style="Eyebrow.TLabel").pack(anchor=tk.W)
        ttk.Label(header_text, textvariable=self.page_title_var, style="PageTitle.TLabel").pack(anchor=tk.W, pady=(1, 0))
        ttk.Label(header_text, textvariable=self.page_desc_var, style="Muted.TLabel").pack(anchor=tk.W, pady=(4, 0))
        ttk.Label(self.header, textvariable=self.module_index_var, style="Index.TLabel", padding=(16, 12)).pack(side=tk.RIGHT, anchor=tk.NE)

        status = ttk.Frame(content_shell, style="Status.TFrame", padding=(12, 7))
        status.pack(side=tk.BOTTOM, fill=tk.X, pady=(12, 0))
        tk.Frame(status, width=8, height=8, bg=COLORS["bell"]).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(status, textvariable=self.status_var, style="Status.TLabel").pack(side=tk.LEFT)
        ttk.Label(status, text="本地处理 · 源文件受保护", style="Status.TLabel").pack(side=tk.RIGHT)

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
        if self.current_frame:
            self.current_frame.destroy()
            self.current_frame = None
        try:
            module = importlib.import_module(feature.module)
            frame_class = getattr(module, feature.frame_class)
            frame = frame_class(self.content_canvas)
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
        self.current_frame.update_idletasks()
        height = max(self.content_canvas.winfo_height(), self.current_frame.winfo_reqheight())
        self.content_canvas.itemconfigure(self.content_window, height=height)
        self._sync_content_scrollregion()

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

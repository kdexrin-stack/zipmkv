from __future__ import annotations

import importlib
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


class ZipMkvApp(tk.Tk):
    def __init__(self):
        enable_high_dpi_awareness()
        super().__init__()
        self.title("zipmkv 工具箱")
        self.geometry("1240x780")
        self.minsize(1080, 680)
        ensure_runtime_dirs()
        apply_app_theme(self)
        self.configure(bg=COLORS["bg"])
        self.current_frame: ttk.Frame | None = None
        self.current_feature: FeatureSpec | None = None
        self.feature_iids: dict[str, str] = {}
        self.feature_by_iid: dict[str, FeatureSpec] = {}
        self._build()
        self.load_feature(FEATURES[0])

    def _build(self) -> None:
        root = ttk.Frame(self, style="App.TFrame")
        root.pack(fill=tk.BOTH, expand=True)

        sidebar = ttk.Frame(root, width=270, padding=(18, 18), style="Sidebar.TFrame")
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 1))
        sidebar.pack_propagate(False)

        ttk.Label(sidebar, text="zipmkv", style="AppTitle.TLabel").pack(anchor=tk.W)
        ttk.Label(sidebar, text="本地批处理工具箱", style="SidebarMuted.TLabel").pack(anchor=tk.W, pady=(0, 18))
        ttk.Label(sidebar, text="工作区", style="SidebarSection.TLabel").pack(anchor=tk.W, pady=(0, 6))

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
        self.feature_tree.column("#0", width=228, stretch=True)
        self.feature_tree.pack(fill=tk.X)
        for group_index, (category, features) in enumerate(groups.items()):
            group_iid = f"group_{group_index}"
            self.feature_tree.insert("", tk.END, iid=group_iid, text=category, open=True, tags=("category",))
            for feature in features:
                iid = f"feature_{feature.key}"
                self.feature_tree.insert(group_iid, tk.END, iid=iid, text=feature.title, tags=("feature",))
                self.feature_iids[feature.key] = iid
                self.feature_by_iid[iid] = feature
        self.feature_tree.tag_configure("category", foreground=COLORS["muted"], font=(FONT_FAMILY, 9, "bold"))
        self.feature_tree.bind("<<TreeviewSelect>>", self.on_select)

        ttk.Separator(sidebar).pack(fill=tk.X, pady=16)
        ttk.Button(sidebar, text="打开运行目录", command=self.open_runtime_dir).pack(fill=tk.X)
        ttk.Button(sidebar, text="关于扩展", command=self.show_extension_help).pack(fill=tk.X, pady=6)

        content_shell = ttk.Frame(root, padding=(18, 16), style="App.TFrame")
        content_shell.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.header = ttk.Frame(content_shell, style="Surface.TFrame", padding=(16, 12))
        self.header.pack(fill=tk.X, pady=(0, 12))
        self.page_title_var = tk.StringVar()
        self.page_desc_var = tk.StringVar()
        ttk.Label(self.header, textvariable=self.page_title_var, style="PageTitle.TLabel").pack(anchor=tk.W)
        ttk.Label(self.header, textvariable=self.page_desc_var, style="Surface.TLabel", foreground=COLORS["muted"]).pack(anchor=tk.W, pady=(3, 0))

        self.content = ttk.Frame(content_shell, padding=0, style="App.TFrame")
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

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
        if self.current_frame:
            self.current_frame.destroy()
            self.current_frame = None
        try:
            module = importlib.import_module(feature.module)
            frame_class = getattr(module, feature.frame_class)
            frame = frame_class(self.content)
        except Exception as exc:
            messagebox.showerror("加载失败", f"{feature.title} 加载失败:\n{exc}")
            return
        self.current_frame = frame
        self.current_feature = feature
        frame.pack(fill=tk.BOTH, expand=True)
        self.page_title_var.set(feature.title)
        self.page_desc_var.set(feature.description)
        iid = self.feature_iids[feature.key]
        self.feature_tree.selection_set(iid)
        self.feature_tree.focus(iid)
        self.feature_tree.see(iid)

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

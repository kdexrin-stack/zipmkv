from __future__ import annotations

import ctypes
import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk


COLORS = {
    "bg": "#f6f8fb",
    "surface": "#ffffff",
    "surface_muted": "#f8fafc",
    "border": "#d8e0e8",
    "text": "#1f2933",
    "muted": "#52606d",
    "primary": "#2563eb",
    "primary_hover": "#1d4ed8",
    "selection": "#dbeafe",
    "hover": "#eef4fb",
}

FONT_FAMILY = "Microsoft YaHei"
BASE_FONT_SIZE = 10


def enable_high_dpi_awareness() -> None:
    if not sys.platform.startswith("win"):
        return
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def apply_window_scaling(root: tk.Misc) -> None:
    try:
        dpi = float(root.winfo_fpixels("1i"))
        if dpi > 0:
            root.tk.call("tk", "scaling", dpi / 72.0)
    except Exception:
        pass


def apply_named_fonts() -> None:
    fonts = {
        "TkDefaultFont": (FONT_FAMILY, BASE_FONT_SIZE),
        "TkTextFont": (FONT_FAMILY, BASE_FONT_SIZE),
        "TkMenuFont": (FONT_FAMILY, BASE_FONT_SIZE),
        "TkHeadingFont": (FONT_FAMILY, BASE_FONT_SIZE, "bold"),
        "TkCaptionFont": (FONT_FAMILY, BASE_FONT_SIZE),
        "TkSmallCaptionFont": (FONT_FAMILY, BASE_FONT_SIZE),
        "TkIconFont": (FONT_FAMILY, BASE_FONT_SIZE),
        "TkTooltipFont": (FONT_FAMILY, BASE_FONT_SIZE),
    }
    for name, config in fonts.items():
        try:
            tkfont.nametofont(name).configure(family=config[0], size=config[1], weight=config[2] if len(config) > 2 else "normal")
        except Exception:
            continue


def apply_app_theme(root: tk.Misc | None = None) -> ttk.Style:
    if root is not None:
        apply_window_scaling(root)
        apply_named_fonts()
    style = ttk.Style()
    preferred = ["vista", "xpnative", "clam", "aqua", "default"] if sys.platform.startswith("win") else ["clam", "aqua", "default"]
    available = set(style.theme_names())
    for theme in preferred:
        if theme in available:
            style.theme_use(theme)
            break
    style.configure(".", font=(FONT_FAMILY, BASE_FONT_SIZE), background=COLORS["bg"], foreground=COLORS["text"])
    style.configure("TFrame", background=COLORS["surface"])
    style.configure("App.TFrame", background=COLORS["bg"])
    style.configure("Surface.TFrame", background=COLORS["surface"])
    style.configure("Sidebar.TFrame", background=COLORS["surface_muted"])
    style.configure("TLabel", background=COLORS["surface"], foreground=COLORS["text"])
    style.configure("Surface.TLabel", background=COLORS["surface"], foreground=COLORS["text"])
    style.configure("Sidebar.TLabel", background=COLORS["surface_muted"], foreground=COLORS["text"])
    style.configure("Muted.TLabel", background=COLORS["surface"], foreground=COLORS["muted"])
    style.configure("SidebarMuted.TLabel", background=COLORS["surface_muted"], foreground=COLORS["muted"])
    style.configure(
        "SidebarSection.TLabel",
        background=COLORS["surface_muted"],
        foreground=COLORS["text"],
        font=(FONT_FAMILY, 10, "bold"),
    )
    style.configure("AppTitle.TLabel", background=COLORS["surface_muted"], foreground=COLORS["text"], font=(FONT_FAMILY, 20, "bold"))
    style.configure("PageTitle.TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=(FONT_FAMILY, 15, "bold"))
    style.configure("TButton", padding=(12, 7), borderwidth=1)
    style.configure("Primary.TButton", padding=(14, 8), background=COLORS["primary"], foreground="#ffffff", borderwidth=1)
    style.configure("TEntry", padding=(6, 4), fieldbackground=COLORS["surface"])
    style.configure("TCombobox", padding=(6, 4), fieldbackground=COLORS["surface"])
    style.configure(
        "Nav.Treeview",
        background=COLORS["surface_muted"],
        fieldbackground=COLORS["surface_muted"],
        foreground=COLORS["text"],
        borderwidth=0,
        relief=tk.FLAT,
        rowheight=34,
        font=(FONT_FAMILY, BASE_FONT_SIZE),
    )
    style.map(
        "Nav.Treeview",
        background=[("selected", COLORS["selection"])],
        foreground=[("selected", COLORS["text"])],
    )
    style.configure("Feature.TNotebook", background=COLORS["surface"], borderwidth=0)
    style.configure("Feature.TNotebook.Tab", padding=(16, 9), font=(FONT_FAMILY, BASE_FONT_SIZE, "bold"))
    style.map(
        "Feature.TNotebook.Tab",
        background=[("selected", COLORS["surface"]), ("active", COLORS["hover"])],
        foreground=[("selected", COLORS["primary"])],
    )
    style.configure("TLabelframe", background=COLORS["surface"], bordercolor=COLORS["border"], relief=tk.FLAT)
    style.configure("TLabelframe.Label", background=COLORS["surface"], foreground=COLORS["muted"], font=(FONT_FAMILY, BASE_FONT_SIZE, "bold"))
    style.map(
        "TButton",
        background=[("active", COLORS["hover"])],
        foreground=[("disabled", COLORS["muted"])],
    )
    style.map(
        "Primary.TButton",
        background=[("active", COLORS["primary_hover"]), ("disabled", COLORS["border"])],
        foreground=[("active", "#ffffff"), ("disabled", COLORS["muted"])],
    )
    return style


def configure_listbox(listbox: tk.Listbox) -> None:
    listbox.configure(
        bg=COLORS["surface"],
        fg=COLORS["text"],
        selectbackground=COLORS["selection"],
        selectforeground="#102a43",
        activestyle="none",
        relief=tk.SOLID,
        bd=1,
        highlightthickness=1,
        highlightbackground=COLORS["border"],
        highlightcolor=COLORS["primary"],
        font=(FONT_FAMILY, BASE_FONT_SIZE),
    )

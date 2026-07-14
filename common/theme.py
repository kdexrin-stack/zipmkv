from __future__ import annotations

import ctypes
import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk


COLORS = {
    "bg": "#edf1f5",
    "surface": "#ffffff",
    "surface_muted": "#f6f8fb",
    "surface_strong": "#e7ecf2",
    "border": "#cfd7e2",
    "text": "#18212f",
    "muted": "#617083",
    "primary": "#2f6fed",
    "primary_hover": "#245dcc",
    "primary_soft": "#e8efff",
    "accent": "#ef6a4c",
    "success": "#178c78",
    "selection": "#dce7ff",
    "hover": "#edf3ff",
    "sidebar": "#111827",
    "sidebar_surface": "#182232",
    "sidebar_hover": "#222f43",
    "sidebar_text": "#f6f8fb",
    "sidebar_muted": "#98a6b8",
    "console": "#111923",
    "console_text": "#d9e4ee",
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


def _configure_checkbox_indicator(root: tk.Misc, style: ttk.Style) -> None:
    size = 18
    image_width = 23

    def square(fill: str, border: str) -> tk.PhotoImage:
        image = tk.PhotoImage(master=root, width=image_width, height=size)
        image.put(border, to=(0, 0, size, size))
        image.put(fill, to=(1, 1, size - 1, size - 1))
        return image

    unchecked = square(COLORS["surface"], COLORS["border"])
    checked = square(COLORS["primary"], COLORS["primary"])
    for x, y in ((4, 8), (5, 9), (6, 10), (7, 11), (8, 10), (9, 9), (10, 8), (11, 7), (12, 6), (13, 5)):
        checked.put("#ffffff", to=(x, y, x + 2, y + 2))

    try:
        style.element_create(
            "Zipmkv.Checkbutton.indicator",
            "image",
            unchecked,
            ("selected", checked),
            sticky="",
        )
        style.layout(
            "TCheckbutton",
            [
                (
                    "Checkbutton.padding",
                    {
                        "sticky": "nswe",
                        "children": [
                            ("Zipmkv.Checkbutton.indicator", {"side": "left", "sticky": ""}),
                            (
                                "Checkbutton.focus",
                                {
                                    "side": "left",
                                    "sticky": "w",
                                    "children": [("Checkbutton.label", {"sticky": "nswe"})],
                                },
                            ),
                        ],
                    },
                )
            ],
        )
        root._zipmkv_checkbox_images = (unchecked, checked)
    except tk.TclError:
        pass


def apply_app_theme(root: tk.Misc | None = None) -> ttk.Style:
    if root is not None:
        apply_window_scaling(root)
        apply_named_fonts()
    style = ttk.Style()
    preferred = ["clam", "vista", "xpnative", "aqua", "default"]
    available = set(style.theme_names())
    for theme in preferred:
        if theme in available:
            style.theme_use(theme)
            break
    style.configure(
        ".",
        font=(FONT_FAMILY, BASE_FONT_SIZE),
        background=COLORS["surface"],
        foreground=COLORS["text"],
    )
    style.configure("TFrame", background=COLORS["surface"])
    style.configure("App.TFrame", background=COLORS["bg"])
    style.configure("Workspace.TFrame", background=COLORS["surface"])
    style.configure("Surface.TFrame", background=COLORS["surface"])
    style.configure("Header.TFrame", background=COLORS["surface"])
    style.configure("Status.TFrame", background=COLORS["surface_muted"])
    style.configure("Sidebar.TFrame", background=COLORS["sidebar"])
    style.configure("TLabel", background=COLORS["surface"], foreground=COLORS["text"])
    style.configure("Surface.TLabel", background=COLORS["surface"], foreground=COLORS["text"])
    style.configure("Sidebar.TLabel", background=COLORS["sidebar"], foreground=COLORS["sidebar_text"])
    style.configure("Muted.TLabel", background=COLORS["surface"], foreground=COLORS["muted"])
    style.configure("SidebarMuted.TLabel", background=COLORS["sidebar"], foreground=COLORS["sidebar_muted"])
    style.configure("Status.TLabel", background=COLORS["surface_muted"], foreground=COLORS["muted"], font=(FONT_FAMILY, 9))
    style.configure("Eyebrow.TLabel", background=COLORS["surface"], foreground=COLORS["primary"], font=(FONT_FAMILY, 9, "bold"))
    style.configure("Index.TLabel", background=COLORS["surface"], foreground=COLORS["muted"], font=(FONT_FAMILY, 10, "bold"))
    style.configure(
        "SidebarSection.TLabel",
        background=COLORS["sidebar"],
        foreground=COLORS["sidebar_muted"],
        font=(FONT_FAMILY, 9, "bold"),
    )
    style.configure("AppTitle.TLabel", background=COLORS["sidebar"], foreground=COLORS["sidebar_text"], font=(FONT_FAMILY, 18, "bold"))
    style.configure("PageTitle.TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=(FONT_FAMILY, 17, "bold"))
    style.configure("TButton", padding=(13, 8), borderwidth=1, relief=tk.FLAT, background=COLORS["surface"], bordercolor=COLORS["border"], focuscolor=COLORS["primary_soft"])
    style.configure("Primary.TButton", padding=(16, 9), background=COLORS["primary"], foreground="#ffffff", borderwidth=0, relief=tk.FLAT, focuscolor=COLORS["primary"])
    style.configure("Sidebar.TButton", padding=(12, 8), background=COLORS["sidebar_surface"], foreground=COLORS["sidebar_text"], borderwidth=0, relief=tk.FLAT, focuscolor=COLORS["sidebar_surface"])
    style.configure("TEntry", padding=(8, 6), fieldbackground=COLORS["surface"], bordercolor=COLORS["border"], lightcolor=COLORS["border"], darkcolor=COLORS["border"], insertcolor=COLORS["text"])
    style.configure("TCombobox", padding=(8, 6), fieldbackground=COLORS["surface"], background=COLORS["surface"], bordercolor=COLORS["border"], lightcolor=COLORS["border"], darkcolor=COLORS["border"], arrowcolor=COLORS["muted"])
    style.configure("TSpinbox", padding=(8, 6), fieldbackground=COLORS["surface"], bordercolor=COLORS["border"], arrowcolor=COLORS["muted"])
    style.configure("TCheckbutton", background=COLORS["surface"], foreground=COLORS["text"], padding=(2, 3), focuscolor=COLORS["surface"])
    style.configure("TRadiobutton", background=COLORS["surface"], foreground=COLORS["text"], padding=(2, 3), focuscolor=COLORS["surface"])
    style.configure(
        "Nav.Treeview",
        background=COLORS["sidebar"],
        fieldbackground=COLORS["sidebar"],
        foreground=COLORS["sidebar_text"],
        borderwidth=0,
        relief=tk.FLAT,
        rowheight=38,
        font=(FONT_FAMILY, BASE_FONT_SIZE),
    )
    style.map(
        "Nav.Treeview",
        background=[("selected", COLORS["primary"]), ("!selected", COLORS["sidebar"])],
        foreground=[("selected", "#ffffff"), ("!selected", COLORS["sidebar_text"])],
    )
    style.configure("Feature.TNotebook", background=COLORS["surface"], borderwidth=0, tabmargins=(0, 0, 0, 0))
    style.configure("Feature.TNotebook.Tab", padding=(16, 10), font=(FONT_FAMILY, BASE_FONT_SIZE, "bold"), background=COLORS["surface_muted"], borderwidth=0)
    style.map(
        "Feature.TNotebook.Tab",
        background=[("selected", COLORS["surface"]), ("active", COLORS["hover"])],
        foreground=[("selected", COLORS["primary"])],
    )
    style.configure("TLabelframe", background=COLORS["surface"], bordercolor=COLORS["border"], lightcolor=COLORS["border"], darkcolor=COLORS["border"], borderwidth=1, relief=tk.SOLID)
    style.configure("TLabelframe.Label", background=COLORS["surface"], foreground=COLORS["text"], font=(FONT_FAMILY, BASE_FONT_SIZE, "bold"))
    style.configure("Vertical.TScrollbar", background=COLORS["surface_strong"], troughcolor=COLORS["surface_muted"], borderwidth=0, arrowcolor=COLORS["muted"])
    style.configure("Horizontal.TScrollbar", background=COLORS["surface_strong"], troughcolor=COLORS["surface_muted"], borderwidth=0, arrowcolor=COLORS["muted"])
    style.map(
        "TButton",
        background=[("active", COLORS["hover"]), ("pressed", COLORS["primary_soft"]), ("disabled", COLORS["surface_strong"])],
        bordercolor=[("focus", COLORS["primary"]), ("active", COLORS["primary"])],
        foreground=[("disabled", COLORS["muted"])],
    )
    style.map(
        "Primary.TButton",
        background=[("active", COLORS["primary_hover"]), ("disabled", COLORS["border"])],
        foreground=[("active", "#ffffff"), ("disabled", COLORS["muted"])],
    )
    style.map(
        "Sidebar.TButton",
        background=[("active", COLORS["sidebar_hover"]), ("pressed", COLORS["primary"])],
        foreground=[("active", "#ffffff")],
    )
    style.map(
        "TCombobox",
        bordercolor=[("focus", COLORS["primary"])],
        fieldbackground=[("readonly", COLORS["surface"]), ("disabled", COLORS["surface_muted"])],
        foreground=[("readonly", COLORS["text"]), ("disabled", COLORS["muted"])],
    )
    style.map("TEntry", bordercolor=[("focus", COLORS["primary"])])
    if root is not None:
        _configure_checkbox_indicator(root, style)
    return style


def configure_listbox(listbox: tk.Listbox) -> None:
    listbox.configure(
        bg=COLORS["surface_muted"],
        fg=COLORS["text"],
        selectbackground=COLORS["selection"],
        selectforeground=COLORS["text"],
        activestyle="none",
        relief=tk.FLAT,
        bd=0,
        highlightthickness=1,
        highlightbackground=COLORS["border"],
        highlightcolor=COLORS["primary"],
        font=(FONT_FAMILY, BASE_FONT_SIZE),
        selectborderwidth=0,
    )

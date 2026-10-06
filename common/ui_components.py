from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from .paths import resource_path
from .theme import COLORS, FONT_FAMILY


def icon_image(master: tk.Misc, name: str, size: int = 20, color: str | None = None) -> ImageTk.PhotoImage:
    root = master.winfo_toplevel()
    pixels = max(size, round(size * float(root.winfo_fpixels("1i")) / 96))
    key = (name, pixels, color or COLORS["primary"])
    cache = getattr(root, "_icon_cache", None)
    if cache is None:
        cache = root._icon_cache = {}
    if key not in cache:
        with Image.open(resource_path("assets", "icons", f"{name}.png")) as original:
            alpha = original.getchannel("A").resize((pixels, pixels), Image.Resampling.LANCZOS)
        colored = Image.new("RGBA", (pixels, pixels), key[2])
        colored.putalpha(alpha)
        cache[key] = ImageTk.PhotoImage(colored, master=root)
    return cache[key]


class Tooltip:
    def __init__(self, widget: tk.Misc, text: str):
        self.widget, self.text = widget, text
        self.window = None
        self.after_id = None
        widget.bind("<Enter>", self.schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")
        widget.bind("<Destroy>", self.hide, add="+")

    def schedule(self, _event=None) -> None:
        self.hide()
        self.after_id = self.widget.after(450, self.show)

    def show(self) -> None:
        self.after_id = None
        self.window = tk.Toplevel(self.widget)
        self.window.overrideredirect(True)
        ttk.Label(self.window, text=self.text, padding=(9, 6), style="Tooltip.TLabel").pack()
        self.window.update_idletasks()
        x = min(self.widget.winfo_rootx(), self.widget.winfo_screenwidth() - self.window.winfo_reqwidth() - 12)
        self.window.geometry(f"+{x}+{self.widget.winfo_rooty() + self.widget.winfo_height() + 6}")

    def hide(self, _event=None) -> None:
        if self.after_id is not None:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
        if self.window is not None:
            self.window.destroy()
            self.window = None


def icon_button(master, name: str, command, tooltip: str, text: str = "", primary: bool = False):
    button = ttk.Button(
        master, command=command, text=text, compound=tk.LEFT,
        image=icon_image(master, name, color="#ffffff" if primary else COLORS["primary"]),
        style="Primary.TButton" if primary else "Icon.TButton" if not text else "TButton",
    )
    if not text:
        button.configure(width=3)
    Tooltip(button, tooltip)
    return button


def decorate_buttons(parent: tk.Misc) -> None:
    """Unify existing toolbars without changing their commands or module APIs."""
    for widget in parent.winfo_children():
        if isinstance(widget, ttk.Button) and not getattr(widget, "_icon_decorated", False):
            text = str(widget.cget("text"))
            if widget.cget("textvariable"):
                text = str(widget.getvar(widget.cget("textvariable")))
            plain = re.sub(r"^[^\w\u3400-\u9fff]+", "", text).strip()
            name = None
            compact = False
            if str(widget.cget("style")) == "Primary.TButton":
                name = "play"
            elif "打开" in plain and "目录" in plain:
                name, compact = "folder-open", True
            elif plain in {"浏览", "选择", "选择输出目录"} or "文件夹" in plain:
                name = "folder-open"
                compact = plain in {"浏览", "选择", "选择输出目录"}
            elif "清空日志" in plain:
                name, compact = "eraser", True
            elif "清空" in plain or "删除所选" in plain:
                name, compact = "trash-2", True
            elif "刷新" in plain:
                name, compact = "refresh-cw", True
            elif "检测" in plain:
                name = "scan-text"
            elif "选择" in plain and ("文件" in plain or "示例" in plain or "字幕" in plain or "视频" in plain):
                name = "file-plus"
            if name:
                widget.configure(
                    image=icon_image(widget, name, color="#ffffff" if str(widget.cget("style")) == "Primary.TButton" else COLORS["primary"]),
                    compound=tk.LEFT,
                )
                if not widget.cget("textvariable"):
                    widget.configure(text="" if compact else plain)
                if compact:
                    widget.configure(style="Icon.TButton", width=3)
                Tooltip(widget, plain)
                widget._icon_decorated = True
        decorate_buttons(widget)


class SubtitleTimeline(tk.Canvas):
    """Small inspectable timeline of actual cues, not a decorative waveform."""
    def __init__(self, master, on_select):
        super().__init__(master, height=55, bg=COLORS["primary_soft"], highlightthickness=0)
        self.cues = []
        self.selected = 0
        self.on_select = on_select
        self.bind("<Configure>", lambda _event: self.redraw())
        self.bind("<Button-1>", self.select_at)

    @staticmethod
    def seconds(value: str) -> float:
        hours, minutes, seconds = value.replace(",", ".").split(":")
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)

    def set_cues(self, cues, selected=0) -> None:
        self.cues, self.selected = list(cues), selected
        self.redraw()

    def redraw(self) -> None:
        self.delete("all")
        width = max(1, self.winfo_width() - 16)
        if not self.cues:
            return
        duration = max(self.seconds(cue[1]) for cue in self.cues) or 1
        stride = max(1, len(self.cues) // 350)
        for index in range(0, len(self.cues), stride):
            start, end, _ = self.cues[index]
            x1, x2 = 8 + width * self.seconds(start) / duration, 8 + width * self.seconds(end) / duration
            self.create_rectangle(x1, 12, max(x1 + 2, x2), 29, fill=COLORS["primary_soft_border"], outline="")
        start, end, _ = self.cues[self.selected]
        x = 8 + width * self.seconds(start) / duration
        self.create_rectangle(x, 10, max(x + 3, 8 + width * self.seconds(end) / duration), 31, fill=COLORS["primary"], outline="")
        self.create_text(8, 42, anchor=tk.W, text=start, fill=COLORS["muted"], font=(FONT_FAMILY, 8))
        self.create_text(width + 8, 42, anchor=tk.E, text=f"{duration:.1f}s", fill=COLORS["muted"], font=(FONT_FAMILY, 8))

    def select_at(self, event) -> None:
        if self.cues:
            duration = max(self.seconds(cue[1]) for cue in self.cues)
            instant = (event.x - 8) / max(1, self.winfo_width() - 16) * duration
            index = min(range(len(self.cues)), key=lambda i: abs(self.seconds(self.cues[i][0]) - instant))
            self.on_select(index)

from __future__ import annotations

import tkinter as tk

from .gui import FeatureFrame


def main() -> None:
    root = tk.Tk()
    root.title("繁简文字转换")
    root.geometry("960x720")
    frame = FeatureFrame(root)
    frame.pack(fill=tk.BOTH, expand=True)
    root.mainloop()


if __name__ == "__main__":
    main()

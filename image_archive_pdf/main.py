from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.theme import apply_app_theme
from image_archive_pdf.gui import FeatureFrame


def main() -> None:
    root = tk.Tk()
    root.title("图片/压缩包/PDF/EPUB/TXT 整理")
    root.geometry("820x620")
    apply_app_theme()
    FeatureFrame(root).pack(fill=tk.BOTH, expand=True)
    root.mainloop()


if __name__ == "__main__":
    main()

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.theme import apply_app_theme
from batch_archive_pdf.gui import FeatureFrame


def main() -> None:
    root = tk.Tk()
    root.title("多压缩包转 PDF")
    root.geometry("840x620")
    apply_app_theme()
    FeatureFrame(root).pack(fill=tk.BOTH, expand=True)
    root.mainloop()


if __name__ == "__main__":
    main()

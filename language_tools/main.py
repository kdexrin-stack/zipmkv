from __future__ import annotations

import tkinter as tk
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.theme import apply_app_theme
try:
    from .gui import FeatureFrame
except ImportError:  # Allows `python language_tools/main.py` as well as `python -m ...`.
    from language_tools.gui import FeatureFrame


def main() -> None:
    root = tk.Tk()
    root.title("字幕语言识别与简繁双语")
    root.geometry("960x720")
    apply_app_theme()
    frame = FeatureFrame(root)
    frame.pack(fill=tk.BOTH, expand=True)
    root.mainloop()


if __name__ == "__main__":
    main()

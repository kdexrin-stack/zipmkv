from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk

from .paths import resource_path


class HaruhiThemeManager:
    """Manages Haruhi Suzumiya (凉宫春日 / SOS 团) anime character illustration with transparency."""

    OPACITY_LEVELS = [0.35, 0.55, 0.20, 0.0]
    OPACITY_LABELS = {
        0.35: "35% (清爽适中)",
        0.55: "55% (二次元鲜明)",
        0.20: "20% (轻柔微影)",
        0.0: "已关闭",
    }

    def __init__(self):
        self.opacity_index: int = 0  # Default 0.35 (35%)
        self.assets_dir = resource_path("assets", "haruhi")
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.figure_path = self.assets_dir / "haruhi_feathered.png"
        self.custom_image_path: Path | None = None
        self._cached_image: ImageTk.PhotoImage | None = None
        self._cached_key: tuple[int, float, str] | None = None

    @property
    def opacity(self) -> float:
        return self.OPACITY_LEVELS[self.opacity_index]

    @property
    def enabled(self) -> bool:
        return self.opacity > 0.0

    @property
    def status_label(self) -> str:
        return self.OPACITY_LABELS.get(self.opacity, f"{int(self.opacity * 100)}%")

    def cycle_opacity(self) -> float:
        """Cycle through opacity levels: 35% -> 55% -> 20% -> 0% (off) -> 35%."""
        self.opacity_index = (self.opacity_index + 1) % len(self.OPACITY_LEVELS)
        self._cached_image = None
        return self.opacity

    def set_custom_image(self, path: Path | None) -> None:
        self.custom_image_path = path
        self._cached_image = None

    def get_blended_figure(self, target_height: int, bg_hex: str = "#ffffff") -> ImageTk.PhotoImage | None:
        """Render character figure with soft transparency pre-blended against background color."""
        if not self.enabled or target_height < 100:
            return None

        cache_key = (target_height, self.opacity, bg_hex)
        if self._cached_image and self._cached_key == cache_key:
            return self._cached_image

        source_path = self.custom_image_path or self.figure_path
        if not source_path.exists():
            return None

        try:
            with Image.open(source_path) as src:
                src = src.convert("RGBA")
                target_w = max(40, int(src.width * (target_height / src.height)))
                resized = src.resize((target_w, target_height), Image.Resampling.LANCZOS)

                # Parse background color hex to RGB tuple
                hex_clean = bg_hex.lstrip("#")
                bg_rgb = tuple(int(hex_clean[i:i + 2], 16) for i in (0, 2, 4))

                # Scale alpha by opacity using pure Pillow point transform
                r, g, b, a = resized.split()
                current_op = self.opacity
                a_scaled = a.point(lambda p: int(p * current_op))
                blended_rgba = Image.merge("RGBA", (r, g, b, a_scaled))

                # Pre-composite onto solid background for crisp Tkinter rendering
                bg = Image.new("RGBA", (target_w, target_height), bg_rgb + (255,))
                composite = Image.alpha_composite(bg, blended_rgba)

                self._cached_image = ImageTk.PhotoImage(composite)
                self._cached_key = cache_key
                return self._cached_image
        except Exception:
            return None


HARUHI_THEME = HaruhiThemeManager()

from __future__ import annotations

import math
from pathlib import Path
import tkinter as tk
from PIL import Image, ImageDraw, ImageFont, ImageTk

from .paths import resource_path


class HaruhiThemeManager:
    """Manages Haruhi Suzumiya (SOS 团) anime background watermark and themes."""

    def __init__(self):
        self.enabled: bool = True
        self.custom_image_path: Path | None = None
        self.cached_image: ImageTk.PhotoImage | None = None
        self._cached_size: tuple[int, int] = (0, 0)
        self.assets_dir = resource_path("assets", "haruhi")
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.default_bg_path = self.assets_dir / "haruhi_watermark.png"
        self._ensure_default_art()

    def _ensure_default_art(self) -> None:
        """Generate a clean, high-resolution aesthetic Haruhi Suzumiya / SOS Brigade watermark if not present."""
        if self.default_bg_path.exists():
            return
        width, height = 700, 560
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw Haruhi Ribbon & Armband themed geometric motif (SOS 团长标志 & 黄色发带)
        # Background soft decorative circles
        draw.ellipse([340, 100, 680, 440], fill=(255, 235, 230, 26))
        draw.ellipse([380, 140, 640, 400], fill=(255, 243, 205, 32))

        # Iconic Red Armband "団長" (Brigade Chief)
        draw.rounded_rectangle([420, 220, 620, 310], radius=16, fill=(225, 45, 57, 48), outline=(225, 45, 57, 75), width=2)
        draw.rounded_rectangle([428, 228, 612, 302], radius=12, fill=(240, 60, 70, 30))

        # Yellow Hair Ribbon Accents (Haruhi's signature yellow ribbon)
        ribbon_color = (245, 158, 11, 60)
        ribbon_outline = (217, 119, 6, 80)
        draw.polygon([(400, 200), (430, 170), (450, 210), (420, 240)], fill=ribbon_color, outline=ribbon_outline)
        draw.polygon([(640, 200), (610, 170), (590, 210), (620, 240)], fill=ribbon_color, outline=ribbon_outline)

        # Try to use standard system fonts or default font for clean typography
        try:
            font_large = ImageFont.truetype("msyh.ttc", 38)
            font_sub = ImageFont.truetype("msyh.ttc", 18)
            font_small = ImageFont.truetype("msyh.ttc", 13)
        except Exception:
            font_large = ImageFont.load_default()
            font_sub = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Text: 団長 / SOS团
        draw.text((520, 265), "団 長", fill=(255, 255, 255, 85), font=font_large, anchor="mm")
        draw.text((520, 340), "涼宮ハルヒの憂鬱 · SOS 団", fill=(30, 41, 59, 60), font=font_sub, anchor="mm")
        draw.text((520, 370), "世界を大いに盛り上げるための涼宮ハルヒの団", fill=(100, 116, 139, 45), font=font_small, anchor="mm")
        draw.text((520, 392), "Spreading Excitement with Haruhi Suzumiya", fill=(148, 163, 184, 40), font=font_small, anchor="mm")

        img.save(self.default_bg_path, "PNG")

    def toggle(self) -> bool:
        self.enabled = not self.enabled
        self.cached_image = None
        return self.enabled

    def get_watermark_image(self, width: int, height: int) -> ImageTk.PhotoImage | None:
        if not self.enabled or width < 200 or height < 200:
            return None
        if self.cached_image and self._cached_size == (width, height):
            return self.cached_image

        target_path = self.custom_image_path or self.default_bg_path
        if not target_path.exists():
            self._ensure_default_art()
            target_path = self.default_bg_path

        try:
            with Image.open(target_path) as base_img:
                base_img = base_img.convert("RGBA")
                max_w = int(width * 0.65)
                max_h = int(height * 0.65)
                ratio = min(max_w / base_img.width, max_h / base_img.height, 1.0)
                new_w = max(100, int(base_img.width * ratio))
                new_h = max(80, int(base_img.height * ratio))
                resized = base_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                canvas_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                paste_x = max(0, width - new_w - 20)
                paste_y = max(0, height - new_h - 15)
                canvas_img.paste(resized, (paste_x, paste_y), resized)

                self.cached_image = ImageTk.PhotoImage(canvas_img)
                self._cached_size = (width, height)
                return self.cached_image
        except Exception:
            return None


HARUHI_THEME = HaruhiThemeManager()

"""Rasterize the pinned Lucide icon font. Only small PNG assets ship in the EXE."""
from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.468.0"
NAMES = (
    "archive", "file-stack", "file-pen-line", "captions", "messages-square",
    "languages", "scan-text", "folder-open", "file-plus", "trash-2", "eraser",
    "refresh-cw", "play", "search", "settings-2", "image", "code-xml", "shield-check",
    "chevron-left", "chevron-right", "maximize-2", "check", "circle-alert",
)


def main() -> None:
    base = f"https://unpkg.com/lucide-static@{VERSION}/font"
    with urlopen(f"{base}/lucide.css", timeout=30) as response:
        css = response.read().decode("utf-8")
    with urlopen(f"{base}/lucide.ttf", timeout=30) as response:
        font_data = response.read()
    output = ROOT / "assets" / "icons"
    output.mkdir(parents=True, exist_ok=True)
    glyphs = dict(re.findall(r'\.icon-([\w-]+):before\s*\{\s*content:\s*"\\([\da-f]+)"', css))
    font = ImageFont.truetype(BytesIO(font_data), 72)
    for name in NAMES:
        if name not in glyphs:
            raise ValueError(f"Missing upstream icon: {name}")
        image = Image.new("RGBA", (96, 96))
        draw = ImageDraw.Draw(image)
        glyph = chr(int(glyphs[name], 16))
        left, top, right, bottom = draw.textbbox((0, 0), glyph, font=font)
        draw.text(((96 - right + left) / 2 - left, (96 - bottom + top) / 2 - top), glyph, font=font, fill="white")
        image.save(output / f"{name}.png", optimize=True)
    with urlopen(f"https://unpkg.com/lucide-static@{VERSION}/LICENSE", timeout=30) as response:
        (output / "LICENSE.txt").write_bytes(response.read())
    print(f"Generated {len(NAMES)} Lucide PNGs")


if __name__ == "__main__":
    main()

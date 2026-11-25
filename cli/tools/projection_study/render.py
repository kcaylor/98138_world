"""Preview images for the study (approximate colors, not the kit's cited ones)."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

COL = {
    "land": (242, 243, 242),
    "shelf": (66, 192, 251),
    "mid": (0, 143, 155),
    "deep": (25, 50, 90),
    "off": (27, 42, 52),
    "base": (5, 19, 29),
    "margin": (32, 50, 80),
    "rim": (228, 205, 158),
}


def _ocean(z: float):
    if np.isnan(z) or z > -1000:
        return COL["shelf"]
    return COL["mid"] if z > -4000 else COL["deep"]


def render(path: Path, on, land, depth, px: int = 7, rim=None, grid: bool = True,
           square_margin: bool = False) -> None:
    """Round studs for land and ocean; margin studs drawn round or square, optionally a rim."""
    H, W = on.shape
    img = Image.new("RGB", (W * px, H * px), COL["base"])
    d = ImageDraw.Draw(img)
    m = 0.6
    for r in range(H):
        for c in range(W):
            box = [c * px + m, r * px + m, (c + 1) * px - m - 1, (r + 1) * px - m - 1]
            if rim is not None and rim[r, c]:
                d.rectangle(box, fill=COL["rim"]) if square_margin else d.ellipse(box, fill=COL["rim"])
            elif not on[r, c]:
                if square_margin:
                    d.rectangle(box, fill=COL["margin"])
                else:
                    d.ellipse(box, fill=COL["off"])
            else:
                d.ellipse(box, fill=COL["land"] if land[r, c] else _ocean(depth[r, c]))
    if grid:
        for c in range(0, W + 1, 16):
            d.line([(c * px, 0), (c * px, H * px)], fill=(90, 90, 90), width=1)
        for r in range(0, H + 1, 16):
            d.line([(0, r * px), (W * px, r * px)], fill=(90, 90, 90), width=1)
    img.save(path)


def _font(size: int):
    for name in ("/System/Library/Fonts/Supplemental/Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def contact_sheet(path: Path, tiles: List[Tuple[Path, str, str, Tuple[int, int]]], cols: int = 3,
                  scale: float = 3.0) -> Tuple[int, int]:
    """tiles: (image path, title, subtitle, (W, H) in studs)."""
    font, small = _font(22), _font(17)
    cw, ch = int(160 * scale) + 30, int(96 * scale) + 80
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cw + 20, rows * ch + 20), (250, 250, 248))
    sd = ImageDraw.Draw(sheet)
    for i, (img_path, title, sub, (W, H)) in enumerate(tiles):
        im = Image.open(img_path).resize((int(W * scale), int(H * scale)), Image.LANCZOS)
        x0, y0 = 20 + (i % cols) * cw, 20 + (i // cols) * ch
        sheet.paste(im, (x0, y0 + 56))
        sd.text((x0, y0), title, fill=(20, 20, 20), font=font)
        sd.text((x0, y0 + 28), sub, fill=(90, 90, 90), font=small)
    sheet.save(path)
    return sheet.size

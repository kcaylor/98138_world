"""Preview PNG of a layout: one square of cited RGB per stud (FR-024; not a build sheet).

Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import numpy as np
from PIL import Image

from ..kit.part_colors import load_part_colors


def color_rgb() -> Dict[Tuple[str, str], Tuple[int, int, int]]:
    """(part, key) -> cited RGB from the part-color table (kit colors equal kit_colors.json)."""
    t = load_part_colors()
    return {(p, c.key): tuple(c.rgb) for p, rows in t.parts.items() for c in rows}


def write_preview(layout, path, scale: int = 8) -> Path:
    rgb = color_rgb()
    img = np.zeros((layout.height, layout.width, 3), dtype=np.uint8)
    for pos in layout.positions:
        key = (pos.lego_part_id, pos.color_id)
        if key not in rgb:
            raise ValueError(f"no cited RGB for {pos.color_id} on part {pos.lego_part_id}")
        img[pos.y, pos.x] = rgb[key]
    if scale > 1:
        img = np.repeat(np.repeat(img, scale, axis=0), scale, axis=1)
    path = Path(path)
    Image.fromarray(img, "RGB").save(path, format="PNG")
    return path

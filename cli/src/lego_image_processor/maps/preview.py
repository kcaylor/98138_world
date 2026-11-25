"""Preview PNG of a layout: one stud of cited RGB per position (FR-024; not a build sheet).

The default style draws each stud as a round 1×1 piece on a black background, as the map looks
built; ``style="square"`` fills each cell edge to edge.

Feature 016 (FR-012; research R13): a template's margin studs are 1×1 square tiles (part type
``square_tile``), so the round style draws them as full squares in their margin or ring color;
land and ocean studs are rounds, as on the kit. Margin studs in LEGO Black are drawn in the
preview's background color (pure black by default), so a Black margin blends into the background;
other margin colors and the outline ring keep their cited colors (owner, 2026-11-24). Only the
drawing changes: layouts, parts lists, exports, sheets and cells.json keep LEGO Black's cited color.
Kit layouts have no square tiles, so their previews are unchanged (SC-001).

Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import numpy as np
from PIL import Image

from ..kit.part_colors import load_part_colors
from ..layout.position import MARGIN_PART_TYPE

STYLES = ("round", "square")
DEFAULT_STYLE = "round"
DEFAULT_BACKGROUND = (0, 0, 0)
# Stud diameter as a share of the 8 mm pitch, leaving a visible gap between round pieces.
STUD_DIAMETER = 0.9
_SUPERSAMPLE = 8
# Feature 016: margin studs in this color (not the ring) are drawn in the background color.
BACKGROUND_MARGIN_COLOR = "lego_black"


def color_rgb() -> Dict[Tuple[str, str], Tuple[int, int, int]]:
    """(part, key) -> cited RGB from the part-color table (kit colors equal kit_colors.json)."""
    t = load_part_colors()
    return {(p, c.key): tuple(c.rgb) for p, rows in t.parts.items() for c in rows}


def stud_coverage(scale: int, diameter: float = STUD_DIAMETER) -> np.ndarray:
    """Anti-aliased coverage (0..1) of one round stud in a ``scale`` × ``scale`` cell."""
    n = scale * _SUPERSAMPLE
    c = (np.arange(n) + 0.5) / n - 0.5
    inside = (c[None, :] ** 2 + c[:, None] ** 2) <= (diameter / 2) ** 2
    return inside.reshape(scale, _SUPERSAMPLE, scale, _SUPERSAMPLE).mean(axis=(1, 3))


def _ring_color(layout):
    """The layout's outline-ring color (``metadata.map.margin.ring``), or None."""
    meta = getattr(layout, "map_metadata", None) or {}
    return (meta.get("margin") or {}).get("ring")


def write_preview(layout, path, scale: int = 8, style: str = DEFAULT_STYLE,
                  background: Tuple[int, int, int] = DEFAULT_BACKGROUND) -> Path:
    if style not in STYLES:
        raise ValueError(f"unknown preview style {style!r} (expected one of {', '.join(STYLES)})")
    rgb = color_rgb()
    img = np.zeros((layout.height, layout.width, 3), dtype=np.uint8)
    square = np.zeros((layout.height, layout.width), dtype=bool)
    # Black margin studs take the background; a Black ring (margin in another color) keeps its color.
    blend = None if _ring_color(layout) == BACKGROUND_MARGIN_COLOR else BACKGROUND_MARGIN_COLOR
    for pos in layout.positions:
        key = (pos.lego_part_id, pos.color_id)
        if key not in rgb:
            raise ValueError(f"no cited RGB for {pos.color_id} on part {pos.lego_part_id}")
        is_square = pos.part_type == MARGIN_PART_TYPE
        img[pos.y, pos.x] = background if is_square and pos.color_id == blend else rgb[key]
        square[pos.y, pos.x] = is_square
    if scale > 1:
        img = np.repeat(np.repeat(img, scale, axis=0), scale, axis=1)
    if style == "round":
        a = np.tile(stud_coverage(scale), (layout.height, layout.width))
        if square.any():  # feature 016: a template's margin tiles fill their cells
            a = np.where(np.repeat(np.repeat(square, scale, axis=0), scale, axis=1), 1.0, a)
        a = a[..., None]
        bg = np.asarray(background, dtype=np.float64)
        img = np.rint(img * a + bg * (1.0 - a)).astype(np.uint8)
    path = Path(path)
    Image.fromarray(img, "RGB").save(path, format="PNG")
    return path

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

Feature 017 (FR-024; research R15; contracts/in-margin-plaque.md "Preview"): the in-margin plaque
(``metadata.plaque``) is drawn as one filled rectangle in its tile's cited Black over its studs. In
the round style it spans the studs minus the gap a round stud leaves (``STUD_DIAMETER``), half of it
on each side, anti-aliased; in the square style it fills the studs' cells. A layout may lack exactly
the plaque's studs and no other position (``ValueError`` otherwise); previews without a plaque are
unchanged.

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


def _check_positions(layout) -> None:
    """A layout may lack exactly its plaque's studs (feature 017) and no other position."""
    covered = getattr(layout, "plaque_positions", frozenset())
    off = [(x, y) for (x, y) in covered if not (0 <= x < layout.width and 0 <= y < layout.height)]
    if off:
        raise ValueError(f"the plaque (metadata.plaque) covers studs off the {layout.width} x {layout.height} board")
    present = set()
    for pos in layout.positions:
        if (pos.x, pos.y) in covered:
            raise ValueError(f"a piece at column {pos.x}, row {pos.y} is under the plaque (metadata.plaque)")
        present.add((pos.x, pos.y))
    for y in range(layout.height):
        for x in range(layout.width):
            if (x, y) not in present and (x, y) not in covered:
                raise ValueError(f"the layout has no piece at column {x}, row {y}; a layout may lack only the "
                                 f"studs of its plaque (metadata.plaque)")


def plaque_rgb(record) -> Tuple[int, int, int]:
    """The cited RGB of the plaque tile a ``metadata.plaque`` record names (plaque_parts.json)."""
    from ..kit.plaque_parts import load_plaque_parts

    try:
        part = load_plaque_parts().get(str(record.get("part_id")))
    except KeyError:
        part = None
    if part is None or part.color.key != record.get("color"):
        raise ValueError(f"no cited RGB for {record.get('color')} on plaque part {record.get('part_id')}")
    return tuple(part.color.rgb)


def _edge_coverage(n: int, start: float, stop: float) -> np.ndarray:
    """Share of each of ``n`` pixels inside [start, stop) (pixel i spans [i, i + 1))."""
    i = np.arange(n, dtype=np.float64)
    return np.clip(np.minimum(i + 1.0, stop) - np.maximum(i, start), 0.0, 1.0)


def _draw_plaque(img: np.ndarray, record, scale: int, style: str) -> np.ndarray:
    """``img`` (as drawn, H*scale x W*scale x 3) with the plaque's filled rectangle over its studs."""
    s = record["studs"]
    inset = (1.0 - STUD_DIAMETER) / 2.0 * scale if style == "round" else 0.0
    ys = _edge_coverage(img.shape[0], s["row"] * scale + inset, (s["row"] + s["height"]) * scale - inset)
    xs = _edge_coverage(img.shape[1], s["col"] * scale + inset, (s["col"] + s["width"]) * scale - inset)
    a = (ys[:, None] * xs[None, :])[..., None]
    color = np.asarray(plaque_rgb(record), dtype=np.float64)
    return np.rint(color * a + img.astype(np.float64) * (1.0 - a)).astype(np.uint8)


def write_preview(layout, path, scale: int = 8, style: str = DEFAULT_STYLE,
                  background: Tuple[int, int, int] = DEFAULT_BACKGROUND) -> Path:
    if style not in STYLES:
        raise ValueError(f"unknown preview style {style!r} (expected one of {', '.join(STYLES)})")
    _check_positions(layout)
    plaque = getattr(layout, "plaque", None)  # feature 017
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
    for (x, y) in getattr(layout, "plaque_positions", frozenset()):  # under the plaque: background
        img[y, x] = background
        square[y, x] = True
    if scale > 1:
        img = np.repeat(np.repeat(img, scale, axis=0), scale, axis=1)
    if style == "round":
        a = np.tile(stud_coverage(scale), (layout.height, layout.width))
        if square.any():  # feature 016: a template's margin tiles fill their cells
            a = np.where(np.repeat(np.repeat(square, scale, axis=0), scale, axis=1), 1.0, a)
        a = a[..., None]
        bg = np.asarray(background, dtype=np.float64)
        img = np.rint(img * a + bg * (1.0 - a)).astype(np.uint8)
    if plaque is not None:
        img = _draw_plaque(img, plaque, scale, style)
    path = Path(path)
    Image.fromarray(img, "RGB").save(path, format="PNG")
    return path

"""Legend entries: one numbered lot per part and color, from the 005 parts list (006 FR-003, FR-005).

Numbers follow the parts list's lot order. Names and IDs come only from 005's resolver
(``Lot.ids``); an unverified lot shows the layout's color name and code and "no cited IDs". Its
swatch uses the feature-001 palette RGB for display only (not a cited table), else mid grey.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Optional, Tuple

from ..palette.loader import LegoPalette
from ..parts import Lot, PartsList
from .model import BLACK, GREY, RGB, WHITE, latin1_safe

# One label per parts-list part type (parts.partslist.PART_TYPE); the web prebuild maps the parts
# its variants use through it, so a new part type needs its label here (016 research R16).
PART_LABEL = {"plate": "plate 1x1 round", "tile": "tile 1x1 round", "square_tile": "tile 1x1 square"}
NO_IDS = "no cited IDs"


@dataclass(frozen=True)
class LegendEntry:
    number: int
    lot: Lot
    rgb: RGB
    text_color: RGB
    label_lines: Tuple[str, ...]

    @property
    def verified(self) -> bool:
        return self.lot.verified

    @property
    def name(self) -> str:
        return self.lot.display_name

    @property
    def part_label(self) -> str:
        return PART_LABEL[self.lot.part_type]


def _linear(c: int) -> float:
    s = c / 255
    return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb: RGB) -> float:
    r, g, b = (_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def text_color(rgb: RGB) -> RGB:
    """Black or white, whichever has the higher WCAG contrast ratio against ``rgb``."""
    lum = relative_luminance(rgb)
    on_black = (lum + 0.05) / 0.05
    on_white = 1.05 / (lum + 0.05)
    return BLACK if on_black >= on_white else WHITE


@lru_cache(maxsize=None)
def _palette() -> LegoPalette:
    return LegoPalette.load_default()


def display_rgb(lot: Lot) -> RGB:
    if lot.ids is not None:
        return tuple(lot.ids.rgb)
    pal = _palette()
    color: Optional[object] = None
    try:
        color = pal.get_by_id(int(str(lot.layout_color_code).split(",")[0]))
    except ValueError:
        color = None
    if color is None or color.name.lower() != lot.layout_color_name.lower():
        color = pal.get_by_name(lot.layout_color_name) or color
    return tuple(color.rgb) if color is not None else GREY


def label_lines(lot: Lot) -> Tuple[str, ...]:
    """Two text lines for a legend row (Latin-1)."""
    part = PART_LABEL[lot.part_type]
    if lot.ids is None:
        first = f"{lot.layout_color_name} (code {lot.layout_color_code}) · {part} · {NO_IDS}"
        second = f"color key {lot.color_key}; {lot.reason}"
    else:
        r = lot.ids
        first = f"{r.lego_name} ({r.lego_id}) · {part} · element {r.element_id}"
        second = (f"BrickLink {r.bricklink_item_no} / {r.bricklink_color_name} ({r.bricklink_color_id})"
                  f" · Rebrickable {r.rebrickable_part_num} / {r.rebrickable_color_name} "
                  f"({r.rebrickable_color_id})")
    return (latin1_safe(first), latin1_safe(second))


def build_legend(parts_list: PartsList) -> Tuple[LegendEntry, ...]:
    out = []
    for i, lot in enumerate(parts_list.lots, start=1):
        rgb = display_rgb(lot)
        out.append(LegendEntry(number=i, lot=lot, rgb=rgb, text_color=text_color(rgb),
                               label_lines=label_lines(lot)))
    return tuple(out)


def lot_numbers(legend: Tuple[LegendEntry, ...]) -> Dict[Tuple[str, str], int]:
    """(part_id, color_key) -> lot number."""
    return {(e.lot.part_id, e.lot.color_key): e.number for e in legend}

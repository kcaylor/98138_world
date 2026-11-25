"""Price lots: one map part in one cited color, and the lot sets a fetch covers (feature 011, R5).

A lot is identified by (part ID, LEGO color ID) and is built only from the cited tables
(``part_colors.json``, ``part_numbers.json``), never typed in. The default lot set is every color
the bundled recipes declare (land colors on plate 6141, ocean colors and the shadow color on tile
98138, and the margin colors on the 1x1 square tile 3070b that a non-kit template uses, feature
016); arrangements move whole frames and never change colors, so it covers A, B and C. BrickLink
files the square tile as item 3070 (``part_numbers.json``), so its lots are fetched by that number.
Feature 017: the in-margin plaque's tile (tile 6x6, part 10202, Black) is lot ``10202:26``, cited in
``plaque_parts.json`` (its BrickLink item there); ``recipe_lots`` adds it only for a recipe that
names a corner (``[margin].plaque``; no bundled one does), and ``all_cited_lots`` keeps to the
``part_colors.json`` parts, so ``--all-colors`` is unchanged.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Sequence, Tuple

from ..kit.part_colors import PartColor, load_part_colors
from ..kit.part_numbers import load_part_numbers

PART_ORDER = {"6141": 0, "98138": 1, "3070b": 2, "10202": 3}
PART_TYPE = {"6141": "plate", "98138": "tile", "3070b": "square_tile", "10202": "plaque_tile"}
PART_NAMES = "6141, 98138, 3070b or 10202"
# A part ID may end in one lowercase letter (3070b, feature 016); parse_lot still checks PART_ORDER.
_LOT_RE = re.compile(r"^(\d+[a-z]?):(\d+)$")


@dataclass(frozen=True)
class LotRef:
    part_id: str
    lego_color_id: int
    color_key: str
    lego_color_name: str
    bricklink_item_type: str
    bricklink_item_no: str
    bricklink_color_id: int
    bricklink_color_name: str

    @property
    def key(self) -> Tuple[str, int]:
        return (self.part_id, self.lego_color_id)

    @property
    def sort_key(self) -> Tuple[int, int]:
        return (PART_ORDER[self.part_id], self.lego_color_id)

    @property
    def part_type(self) -> str:
        return PART_TYPE[self.part_id]

    @property
    def label(self) -> str:
        """``tile 98138 Earth Blue (LEGO 140)``."""
        return f"{self.part_type} {self.part_id} {self.lego_color_name} (LEGO {self.lego_color_id})"

    @property
    def spec(self) -> str:
        """``98138:140``, the ``--lot`` form."""
        return f"{self.part_id}:{self.lego_color_id}"


def _plaque_tile(part_id: str):
    """The in-margin plaque's tile in plaque_parts.json (a ``PlaquePart``) when ``part_id`` is it,
    else None (feature 017)."""
    if PART_TYPE.get(part_id) != "plaque_tile":
        return None
    from ..kit.plaque_parts import load_plaque_parts

    try:
        part = load_plaque_parts().get(part_id)
    except KeyError:
        return None
    return part if part.kind == "tile" else None


def _rows(part_id: str) -> Tuple[PartColor, ...]:
    """The cited colors of a map part: part_colors.json, or plaque_parts.json for the plaque tile;
    ``KeyError`` for any other part."""
    tile = _plaque_tile(part_id)
    if tile is not None:
        return (tile.color,)
    return load_part_colors().for_part(part_id)


def _from_row(part_id: str, row: PartColor) -> LotRef:
    tile = _plaque_tile(part_id)
    numbers = tile.numbers if tile is not None else load_part_numbers().get(part_id)
    if row.bricklink.name not in numbers.bricklink_colors:
        raise ValueError(f"{part_id} {row.key}: BrickLink color {row.bricklink.name!r} is not on "
                         f"BrickLink's catalog page for item {numbers.bricklink_item_no}")
    return LotRef(part_id=part_id, lego_color_id=row.lego.id, color_key=row.key,
                  lego_color_name=row.lego.name, bricklink_item_type=numbers.bricklink_item_type,
                  bricklink_item_no=numbers.bricklink_item_no, bricklink_color_id=row.bricklink.id,
                  bricklink_color_name=row.bricklink.name)


def lot_ref(part_id: str, color_key: str) -> LotRef:
    """The cited lot for ``part_id`` (6141, 98138, 3070b or the plaque tile 10202) in ``color_key``;
    ``ValueError`` if none."""
    try:
        rows = _rows(str(part_id))
    except KeyError:
        raise ValueError(f"part {part_id!r} is not a map part ({PART_NAMES})")
    row = next((r for r in rows if r.key == color_key), None)
    if row is None:
        raise ValueError(f"no cited color {color_key!r} for part {part_id}")
    return _from_row(str(part_id), row)


def lot_ref_by_lego_id(part_id: str, lego_color_id: int) -> Optional[LotRef]:
    """The cited lot with this LEGO color ID, or None."""
    try:
        rows = _rows(str(part_id))
    except KeyError:
        return None
    row = next((r for r in rows if r.lego.id == int(lego_color_id)), None)
    return None if row is None else _from_row(str(part_id), row)


def sort_lots(lots: Iterable[LotRef]) -> Tuple[LotRef, ...]:
    unique: Dict[Tuple[str, int], LotRef] = {}
    for lot in lots:
        unique.setdefault(lot.key, lot)
    return tuple(sorted(unique.values(), key=lambda l: l.sort_key))


def recipe_lots(recipes: Optional[Sequence] = None) -> Tuple[LotRef, ...]:
    """Every lot the recipes declare (default: all bundled recipes), sorted and unique.

    Each recipe also adds its margin colors on the square tile (its ``[margin]`` table, else the
    default Black with no ring; feature 016, data-model.md PriceLot.recipe_lots), so a fetch covers
    the recipe's builds on a non-kit template as well; and (feature 017) the in-margin plaque's
    tile when its ``[margin]`` names a corner."""
    from ..maps.margin import MARGIN_PART_ID, MarginTreatment, plaque_tile

    if recipes is None:
        recipes = bundled_recipe_objects()
    out = []
    for r in recipes:
        out += [lot_ref(r.land.part_id, k) for k in r.land.colors]
        out += [lot_ref(r.ocean.part_id, k) for k in r.ocean.colors]
        if r.shadow.enabled:
            out.append(lot_ref(r.ocean.part_id, r.shadow.color))
        margin = getattr(r, "margin", None) or MarginTreatment()
        out += [lot_ref(MARGIN_PART_ID, k) for k in (margin.color, margin.ring) if k]
        if margin.plaque is not None:
            tile = plaque_tile()
            out.append(lot_ref(tile.part_id, tile.color.key))
    return sort_lots(out)


def bundled_recipe_objects():
    from ..maps.recipe import bundled_recipes, load_recipe
    return [load_recipe(p) for p in bundled_recipes().values()]


def all_cited_lots() -> Tuple[LotRef, ...]:
    """Every cited color of the map parts in part_colors.json (6141, 98138 and, since feature 016,
    3070b); the plaque tile (feature 017, plaque_parts.json) is not among them."""
    table = load_part_colors()
    return sort_lots(_from_row(part_id, row) for part_id in PART_ORDER if part_id in table.parts
                     for row in table.for_part(part_id))


def parse_lot(text: str) -> LotRef:
    """``PART:LEGO_COLOR_ID`` (for example ``98138:140`` or ``3070b:26``) to a cited lot;
    ``ValueError`` if not cited."""
    s = str(text).strip()
    m = _LOT_RE.match(s)
    if not m:
        raise ValueError(f"lot {s!r} is not PART:LEGO_COLOR_ID (for example 98138:140)")
    part_id, lego_id = m.group(1), int(m.group(2))
    if part_id not in PART_ORDER:
        raise ValueError(f"lot {s!r}: part {part_id} is not a map part ({PART_NAMES})")
    lot = lot_ref_by_lego_id(part_id, lego_id)
    if lot is None:
        raise ValueError(f"lot {s!r}: no cited color with LEGO ID {lego_id} for part {part_id}")
    return lot


def named_lots(texts: Iterable[str]) -> Tuple[LotRef, ...]:
    return sort_lots(parse_lot(t) for t in texts)

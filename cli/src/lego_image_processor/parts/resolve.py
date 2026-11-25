"""Resolve a layout color to cited catalog IDs (feature 005 FR-005).

A lot is verified only when the cited part-color table has a row for the layout's part whose LEGO
color ID equals the layout's ``lego_color_code``. Colors match by LEGO ID, not by name or key, so a
palette's "Dark Red" (154) resolves to the cited "New Dark Red" (154). Marketplace part numbers
come from ``part_numbers.json``. Nothing is guessed: any other case is unverified, with a reason.
The in-margin plaque's tile (feature 017; ``resolve_plaque_tile``) is cited in ``plaque_parts.json``
instead, which gives the same ``PartNumbers`` and ``PartColor`` objects, so its lot resolves to the
same ``ResolvedColor``.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Union

from ..kit.part_colors import PartColor, PartColorTable, load_part_colors
from ..kit.part_numbers import PartNumberTable, PartNumbers, load_part_numbers
from ..kit.plaque_parts import PlaquePartTable, load_plaque_parts

REASON_NO_COLOR = "no cited color for part"
REASON_CODE_MISMATCH = "color code mismatch"  # missing, invalid, or inconsistent LEGO color ID
REASON_NOT_ON_PART_PAGE = "color not listed on BrickLink's catalog page for the part"


@dataclass(frozen=True)
class ResolvedColor:
    """Cited IDs for one part in one color."""

    part: PartNumbers
    color: PartColor

    @property
    def part_id(self) -> str:
        return self.part.part_id

    @property
    def lego_name(self) -> str:
        return self.color.lego.name

    @property
    def lego_id(self) -> int:
        return self.color.lego.id

    @property
    def element_id(self) -> str:
        return self.color.element_id

    @property
    def bricklink_item_type(self) -> str:
        return self.part.bricklink_item_type

    @property
    def bricklink_item_no(self) -> str:
        return self.part.bricklink_item_no

    @property
    def bricklink_color_name(self) -> str:
        return self.color.bricklink.name

    @property
    def bricklink_color_id(self) -> int:
        return self.color.bricklink.id

    @property
    def rebrickable_part_num(self) -> str:
        return self.part.rebrickable_part_num

    @property
    def rebrickable_color_name(self) -> str:
        return self.color.rebrickable.name

    @property
    def rebrickable_color_id(self) -> int:
        return self.color.rebrickable.id

    @property
    def rgb(self) -> Tuple[int, int, int]:
        return tuple(self.color.rgb)

    @property
    def citation_ids(self) -> Tuple[str, ...]:
        ids = [c.id for c in self.color.citations.values()]
        ids += [p.id for p in self.part.citations.values()]
        return tuple(dict.fromkeys(ids))


@dataclass(frozen=True)
class Unresolved:
    reason: str


def resolve_color(part_id: str, color_key: str, lego_color_code: Union[str, int, None],
                  part_colors: Optional[PartColorTable] = None,
                  part_numbers: Optional[PartNumberTable] = None) -> Union[ResolvedColor, Unresolved]:
    """Cited IDs for ``part_id`` in ``color_key``, or why there are none."""
    part_colors = part_colors or load_part_colors()
    part_numbers = part_numbers or load_part_numbers()
    try:
        part_colors.for_part(str(part_id))
        numbers = part_numbers.get(str(part_id))
    except KeyError:
        return Unresolved(REASON_NO_COLOR)
    try:
        code = int(str(lego_color_code).strip())
    except (TypeError, ValueError):
        return Unresolved(REASON_CODE_MISMATCH)
    row = part_colors.by_lego_id(str(part_id), code)
    if row is None:
        return Unresolved(REASON_NO_COLOR)
    if row.bricklink.name not in numbers.bricklink_colors:
        return Unresolved(REASON_NOT_ON_PART_PAGE)
    return ResolvedColor(part=numbers, color=row)


def resolve_plaque_tile(part_id: str, color_key: str,
                        plaque_parts: Optional[PlaquePartTable] = None) -> Union[ResolvedColor, Unresolved]:
    """Cited IDs for the in-margin plaque's tile (feature 017) from ``plaque_parts.json``: the part
    must be a tile there and ``color_key`` its cited color (Black); otherwise unverified."""
    table = plaque_parts or load_plaque_parts()
    try:
        part = table.get(str(part_id))
    except KeyError:
        return Unresolved(REASON_NO_COLOR)
    if part.kind != "tile" or part.color.key != color_key:
        return Unresolved(REASON_NO_COLOR)
    if part.color.bricklink.name not in part.numbers.bricklink_colors:
        return Unresolved(REASON_NOT_ON_PART_PAGE)
    return ResolvedColor(part=part.numbers, color=part.color)

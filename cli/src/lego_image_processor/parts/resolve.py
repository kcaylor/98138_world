"""Resolve a layout color to cited catalog IDs (feature 005 FR-005).

A lot is verified only when the cited part-color table has a row for the layout's part and color
key and the layout's ``lego_color_code`` equals that row's LEGO color ID. Marketplace part numbers
come from ``part_numbers.json``. Nothing is guessed: any other case is unverified, with a reason.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Union

from ..kit.part_colors import PartColor, PartColorTable, load_part_colors
from ..kit.part_numbers import PartNumberTable, PartNumbers, load_part_numbers

REASON_NO_COLOR = "no cited color for part"
REASON_CODE_MISMATCH = "color code mismatch"
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
        row = part_colors.get(str(part_id), color_key)
        numbers = part_numbers.get(str(part_id))
    except KeyError:
        return Unresolved(REASON_NO_COLOR)
    if row is None:
        return Unresolved(REASON_NO_COLOR)
    try:
        code = int(str(lego_color_code).strip())
    except (TypeError, ValueError):
        return Unresolved(REASON_CODE_MISMATCH)
    if code != row.lego.id:
        return Unresolved(REASON_CODE_MISMATCH)
    if row.bricklink.name not in numbers.bricklink_colors:
        return Unresolved(REASON_NOT_ON_PART_PAGE)
    return ResolvedColor(part=numbers, color=row)

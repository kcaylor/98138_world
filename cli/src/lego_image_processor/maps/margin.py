"""The margin of a non-kit template (feature 016; data-model.md MarginTreatment; research R12).

Studs off the globe are built from the 1x1 square tile, part 3070b (``MARGIN_PART_ID``), in one
margin color (default Black, ``DEFAULT_MARGIN_COLOR``) with an optional outline ring: the margin
studs that touch an on-globe stud along an edge (``ring_cells``). The treatment comes from the
recipe's ``[margin]`` table, overridden per field by ``--margin-color`` and ``--ring-color``
(``none`` turns a recipe ring off; ``resolve_margin``). Both colors must be cited colors of part
3070b and must differ; an error names the option or key path, lists the available 3070b color
keys and points to ``kit part-colors --part 3070b``. The kit template has no margin, so the
treatment is ignored there. Margin labels are not part of this feature (feature 017, map stickers).
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple

import numpy as np

from ..kit.part_colors import load_part_colors

MARGIN_PART_ID = "3070b"
DEFAULT_MARGIN_COLOR = "lego_black"
NO_RING = "none"


class MarginError(ValueError):
    """A margin or ring color breaks a rule; ``where`` is the option or recipe key path."""

    def __init__(self, where: str, rule: str):
        self.where, self.rule = where, rule
        super().__init__(f"{where}: {rule}")


@dataclass(frozen=True)
class MarginTreatment:
    """data-model.md MarginTreatment: ``color`` (a 3070b color key) and ``ring`` (a 3070b color
    key, or None for no ring; never equal to ``color``)."""

    color: str = DEFAULT_MARGIN_COLOR
    ring: Optional[str] = None

    def provenance(self, cells: Mapping[str, int]) -> Dict[str, Any]:
        """``metadata.map.margin`` and the report's ``margin``: ``cells`` per role (margin, ring)."""
        return {"part_id": MARGIN_PART_ID, "color": self.color, "ring": self.ring,
                "cells": {k: int(v) for k, v in cells.items()}}


def margin_colors() -> Tuple[str, ...]:
    """The cited colors of the square tile (part_colors.json order)."""
    return tuple(c.key for c in load_part_colors().for_part(MARGIN_PART_ID))


def _available() -> str:
    """The tail of every margin color error: the available 3070b color keys and where to see them."""
    return f"available: {', '.join(margin_colors())}; see `kit part-colors --part {MARGIN_PART_ID}`"


def color_rule(key: Any) -> Optional[str]:
    """None when ``key`` is a cited 3070b color; otherwise the rule text for the error."""
    if isinstance(key, str) and load_part_colors().get(MARGIN_PART_ID, key) is not None:
        return None
    shown = repr(key) if isinstance(key, str) else "a color key string"
    return f"{shown} is not a color of the 1x1 square tile (part {MARGIN_PART_ID}); {_available()}"


def ring_rule(ring: str, color: str) -> str:
    """The rule text when the ring and margin colors are the same (spec Edge Cases, research R12)."""
    return (f"the ring color {ring!r} must differ from the margin color {color!r} (1x1 square tile, "
            f"part {MARGIN_PART_ID}); {_available()}")


def check_color(key: Any, where: str) -> str:
    rule = color_rule(key)
    if rule is not None:
        raise MarginError(where, rule)
    return key


def resolve_margin(base: Optional[MarginTreatment], margin_color: Optional[str] = None,
                   ring_color: Optional[str] = None) -> MarginTreatment:
    """The treatment to build with: ``base`` (the recipe's ``[margin]``, or the default Black with
    no ring) overridden per field by the options. Raises ``MarginError`` naming the option
    (``--margin-color``, ``--ring-color``) or the key path (``margin.color``, ``margin.ring``)."""
    base = base or MarginTreatment()
    if margin_color is not None:
        color, color_where = margin_color, "--margin-color"
    else:
        color, color_where = base.color, "margin.color"
    if ring_color is not None:
        ring = None if ring_color.strip().lower() == NO_RING else ring_color
        ring_where = "--ring-color"
    else:
        ring, ring_where = base.ring, "margin.ring"
    check_color(color, color_where)
    if ring is not None:
        check_color(ring, ring_where)
        if ring == color:
            # name the option that made them equal (an option wins over the recipe)
            where = ring_where if ring_where.startswith("--") or not color_where.startswith("--") else color_where
            raise MarginError(where, ring_rule(ring, color))
    return MarginTreatment(color=color, ring=ring)


def ring_cells(template) -> np.ndarray:
    """Margin studs with an on-globe 4-neighbour (no wrap at the board edges); none on the kit."""
    on = np.asarray(template.on_globe, dtype=bool)
    pad = np.pad(on, 1, constant_values=False)
    nb = pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]
    return ~on & nb


def margin_labels(template, treatment: MarginTreatment) -> np.ndarray:
    """Color key of every margin stud (None on the globe): the ring color on the ring, the margin
    color elsewhere."""
    margin = ~np.asarray(template.on_globe, dtype=bool)
    out = np.full(margin.shape, None, dtype=object)
    out[margin] = treatment.color
    if treatment.ring is not None:
        out[ring_cells(template)] = treatment.ring
    return out


def margin_cells(template, treatment: MarginTreatment) -> Dict[str, int]:
    """Studs per role: ``margin`` (in the margin color) and ``ring`` (in the ring color)."""
    total = int((~np.asarray(template.on_globe, dtype=bool)).sum())
    ring = int(ring_cells(template).sum()) if treatment.ring is not None else 0
    return {"margin": total - ring, "ring": ring}

"""The margin of a non-kit template (feature 016; data-model.md MarginTreatment; research R12).

Studs off the globe are built from the 1x1 square tile, part 3070b (``MARGIN_PART_ID``), in one
margin color (default Black, ``DEFAULT_MARGIN_COLOR``) with an optional outline ring: the margin
studs that touch an on-globe stud along an edge (``ring_cells``). The treatment comes from the
recipe's ``[margin]`` table, overridden per field by ``--margin-color`` and ``--ring-color``
(``none`` turns a recipe ring off; ``resolve_margin``). Both colors must be cited colors of part
3070b and must differ; an error names the option or key path, lists the available 3070b color
keys and points to ``kit part-colors --part 3070b``. The kit template has no margin, so the
treatment is ignored there. Margin labels are not part of this feature (feature 017, map stickers).

Feature 017 (FR-021, FR-022; research R15; contracts/in-margin-plaque.md; data-model.md
InMarginPlaque): the treatment may also place the small plaque's tile (``load_plaque_parts()
.plaques["small"].tile``: tile 6x6, part 10202, Black) in one margin corner, chosen by the recipe's
``[margin].plaque`` or ``--plaque`` (``none`` turns a recipe's plaque off). It sits one stud in
from both board edges of its corner (``plaque_studs``); ``place_plaque`` checks, in order, that the
template is not the kit, that all its studs are margin studs inside the corner's clear block (the
template's ``counts.corners``), that they lie in one 16 x 16 module and that no outline-ring stud
is within one stud of the tile. Its studs carry no 1x1 piece, so ``margin_cells`` leaves them out.
The tile is Black whatever the margin and ring colors are. On the kit a plaque chosen with
``--plaque`` is an error and one from the recipe is ignored (decision E2).
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Mapping, Optional, Tuple

import numpy as np

from ..kit.part_colors import load_part_colors
from ..templates.board import CORNERS, MODULE

MARGIN_PART_ID = "3070b"
DEFAULT_MARGIN_COLOR = "lego_black"
NO_RING = "none"
PLAQUE_CORNERS = CORNERS  # top-left, top-right, bottom-left, bottom-right (feature 017)
NO_PLAQUE = "none"
PLAQUE_SIZE = "small"  # the in-margin plaque is the small plaque's tile (plaque_parts.json)
PLAQUE_OFFSET = 1  # studs in from both board edges of the corner


class MarginError(ValueError):
    """A margin or ring color breaks a rule; ``where`` is the option or recipe key path."""

    def __init__(self, where: str, rule: str):
        self.where, self.rule = where, rule
        super().__init__(f"{where}: {rule}")


class PlaqueError(MarginError):
    """The in-margin plaque cannot be placed (feature 017); ``where`` is ``--plaque`` or
    ``margin.plaque``."""


@dataclass(frozen=True)
class MarginTreatment:
    """data-model.md MarginTreatment: ``color`` (a 3070b color key) and ``ring`` (a 3070b color
    key, or None for no ring; never equal to ``color``). Feature 017: ``plaque`` is the corner of the
    in-margin plaque (None for none) and ``plaque_source`` where it came from (``option`` or
    ``recipe``; None without a plaque)."""

    color: str = DEFAULT_MARGIN_COLOR
    ring: Optional[str] = None
    plaque: Optional[str] = None
    plaque_source: Optional[str] = None

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


def corner_rule() -> str:
    """The rule text of an unknown plaque corner (feature 017)."""
    return f"must be one of {', '.join(PLAQUE_CORNERS)}"


def resolve_margin(base: Optional[MarginTreatment], margin_color: Optional[str] = None,
                   ring_color: Optional[str] = None, plaque: Optional[str] = None) -> MarginTreatment:
    """The treatment to build with: ``base`` (the recipe's ``[margin]``, or the default Black with
    no ring) overridden per field by the options. Raises ``MarginError`` naming the option
    (``--margin-color``, ``--ring-color``) or the key path (``margin.color``, ``margin.ring``).
    ``plaque`` (feature 017, ``--plaque``): a corner wins over the recipe's (source ``option``),
    ``none`` turns the recipe's off, None keeps it (source ``recipe``)."""
    base = base or MarginTreatment()
    corner, corner_source = base.plaque, base.plaque_source
    if plaque is not None:
        if plaque == NO_PLAQUE:
            corner, corner_source = None, None
        elif plaque in PLAQUE_CORNERS:
            corner, corner_source = plaque, "option"
        else:
            raise MarginError("--plaque", f"{plaque!r} {corner_rule()} (or {NO_PLAQUE})")
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
    return MarginTreatment(color=color, ring=ring, plaque=corner, plaque_source=corner_source)


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
    """Studs per role: ``margin`` (in the margin color) and ``ring`` (in the ring color). The
    studs under an in-margin plaque (feature 017) carry no square tile and are left out; the plaque
    never covers the ring."""
    total = int((~np.asarray(template.on_globe, dtype=bool)).sum())
    ring = int(ring_cells(template).sum()) if treatment.ring is not None else 0
    plaque = plaque_for(template, treatment)
    covered = 0 if plaque is None else plaque.cells
    return {"margin": total - ring - covered, "ring": ring}


# --- feature 017: the in-margin plaque -------------------------------------------------------

@dataclass(frozen=True)
class InMarginPlaque:
    """data-model.md InMarginPlaque: the small plaque's tile in a margin corner. ``row``/``col``
    are the top-left stud (0-based board coordinates, rows north to south), ``height``/``width``
    its size in studs; ``part_id`` and ``color`` come from plaque_parts.json."""

    corner: str
    source: str
    part_id: str
    color: str
    row: int
    col: int
    height: int
    width: int

    @property
    def studs(self) -> Dict[str, int]:
        return {"row": self.row, "col": self.col, "height": self.height, "width": self.width}

    @property
    def cells(self) -> int:
        return self.height * self.width

    def mask(self, shape) -> np.ndarray:
        """Board-shaped boolean mask of the covered studs."""
        m = np.zeros(shape, dtype=bool)
        m[self.row:self.row + self.height, self.col:self.col + self.width] = True
        return m

    def positions(self) -> FrozenSet[Tuple[int, int]]:
        """The covered studs as layout positions ``(x, y)``."""
        return frozenset((x, y) for y in range(self.row, self.row + self.height)
                         for x in range(self.col, self.col + self.width))

    def layout_record(self) -> Dict[str, Any]:
        """``metadata.plaque`` of the layout (contracts/in-margin-plaque.md "Layout JSON")."""
        return {"part_id": self.part_id, "color": self.color, "corner": self.corner,
                "studs": self.studs, "cells": self.cells}

    def report_record(self) -> Dict[str, Any]:
        """The suitability report's ``margin.plaque``."""
        return {"corner": self.corner, "source": self.source, "studs": self.studs, "part_id": self.part_id}


def plaque_tile():
    """The in-margin plaque's tile: the small plaque's tile in plaque_parts.json (a ``PlaquePart``)."""
    from ..kit.plaque_parts import load_plaque_parts

    return load_plaque_parts().plaques[PLAQUE_SIZE].tile


def _tile_label(tile) -> str:
    w, h = tile.studs
    return f"tile {w}x{h} (part {tile.part_id})"


def plaque_label(part_id: Any) -> str:
    """``tile 6x6 (part 10202)`` for the plaque tile (plaque_parts.json), else ``part <id>``."""
    tile = plaque_tile()
    return _tile_label(tile) if str(part_id) == tile.part_id else f"part {part_id}"


def plaque_studs(template, corner: str) -> Dict[str, int]:
    """The tile's studs in ``corner``: ``PLAQUE_OFFSET`` studs in from both board edges
    (contracts/in-margin-plaque.md "Placement")."""
    if corner not in PLAQUE_CORNERS:
        raise ValueError(f"unknown corner {corner!r}; {corner_rule()}")
    w, h = plaque_tile().studs
    vertical, horizontal = corner.split("-")
    row = PLAQUE_OFFSET if vertical == "top" else template.height - PLAQUE_OFFSET - h
    col = PLAQUE_OFFSET if horizontal == "left" else template.width - PLAQUE_OFFSET - w
    return {"row": row, "col": col, "height": h, "width": w}


def _span(studs: Mapping[str, int]) -> str:
    r, c, h, w = studs["row"], studs["col"], studs["height"], studs["width"]
    return f"rows {r}-{r + h - 1}, columns {c}-{c + w - 1}"


def plaque_text(record: Mapping[str, Any]) -> str:
    """``tile 6x6 (part 10202), Black, bottom-left, rows 73-78, columns 1-6``: a plaque record
    (the layout's ``metadata.plaque`` or the report's ``margin.plaque``) as the CLI prints it; the
    tile's label and color name come from plaque_parts.json (contracts/cli.md)."""
    tile = plaque_tile()
    part = str(record.get("part_id"))
    color = record.get("color", tile.color.key)  # the report's record has no color: the tile is Black
    label = plaque_label(part)
    name = tile.color.lego.name if part == tile.part_id and color == tile.color.key else str(color)
    return f"{label}, {name}, {record.get('corner')}, {_span(record['studs'])}"


def plaque_misfit(template, corner: str, studs: Mapping[str, int], *, block: Optional[Mapping[str, int]] = None,
                  margin: Optional[np.ndarray] = None, ring: Optional[np.ndarray] = None) -> Optional[str]:
    """None when the tile at ``studs`` fits ``corner``; else why not. In order: all studs are
    margin studs inside the corner's clear block (``block``, default the template's
    ``counts.corners``), they lie in one 16 x 16 module, and no outline-ring stud is within one stud
    (Chebyshev distance 1). ``block``, ``margin`` and ``ring`` default to the template's."""
    block = template.counts["corners"][corner] if block is None else block
    margin = np.asarray(template.margin, dtype=bool) if margin is None else np.asarray(margin, dtype=bool)
    ring = ring_cells(template) if ring is None else np.asarray(ring, dtype=bool)
    r, c, h, w = studs["row"], studs["col"], studs["height"], studs["width"]
    H, W = margin.shape
    inside = (0 <= r and r + h <= H and 0 <= c and c + w <= W
              and block["row"] <= r and r + h <= block["row"] + block["height"]
              and block["col"] <= c and c + w <= block["col"] + block["width"])
    if not inside or not margin[r:r + h, c:c + w].all():
        return f"{_span(studs)} are not all margin studs inside the corner's clear block"
    if (r // MODULE, c // MODULE) != ((r + h - 1) // MODULE, (c + w - 1) // MODULE):
        return f"{_span(studs)} are not inside one {MODULE} x {MODULE} module"
    if ring[max(r - 1, 0):r + h + 1, max(c - 1, 0):c + w + 1].any():
        return f"a stud of the outline ring is within one stud of {_span(studs)}"
    return None


def _templates_with_a_margin() -> str:
    from ..templates import TemplateError, confirmed_templates

    try:
        ids = [t.id for t in confirmed_templates() if not t.is_kit and int(t.counts["margin"]) > 0]
    except TemplateError:
        ids = []
    return ", ".join(ids) if ids else "none confirmed yet"


def place_plaque(template, corner: str, source: str = "option") -> InMarginPlaque:
    """The plaque in ``corner`` of ``template``, or ``PlaqueError`` (``where`` is ``--plaque`` for
    ``source`` ``option``, ``margin.plaque`` for ``recipe``) naming the corner, the space the tile
    needs and the corner's clear block."""
    where = "--plaque" if source == "option" else "margin.plaque"
    tile = plaque_tile()
    if template.is_kit:
        raise PlaqueError(where, f"the kit template has no margin, so the plaque {_tile_label(tile)} cannot go "
                                 f"in its {corner} corner; templates with a margin: "
                                 f"{_templates_with_a_margin()} (choose one with --template)")
    if corner not in PLAQUE_CORNERS:
        raise PlaqueError(where, f"{corner!r} {corner_rule()}")
    studs = plaque_studs(template, corner)
    why = plaque_misfit(template, corner, studs)
    if why is not None:
        block = template.counts["corners"][corner]
        w, h = tile.studs
        raise PlaqueError(where, f"the plaque {_tile_label(tile)} does not fit the {corner} corner of template "
                                 f"{template.id}: {why}; it needs {w} x {h} studs plus one stud from the outline "
                                 f"ring, and the corner's clear block is {block['height']} x {block['width']} "
                                 f"studs")
    return InMarginPlaque(corner=corner, source=source, part_id=tile.part_id, color=tile.color.key, **studs)


def plaque_for(template, treatment: Optional[MarginTreatment]) -> Optional[InMarginPlaque]:
    """The plaque ``treatment`` places on ``template``, or None. On the kit a corner from the
    recipe is ignored (016's margin note covers it) and one from ``--plaque`` is an error."""
    if treatment is None or treatment.plaque is None:
        return None
    source = treatment.plaque_source or "recipe"
    if template.is_kit and source != "option":
        return None
    return place_plaque(template, treatment.plaque, source)

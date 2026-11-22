"""The kit's three frame arrangements A, B and C (feature 007).

LEGO 31203 building instructions, pp. 7-8 ("1 world - 3 combinations"): frame 1 America (kit
columns 0-31), frame 2 Europe & Africa (32-95), frame 3 Asia & Australia (96-127), hung as
A = 1·2·3 (default), B = 3·1·2 or C = 2·3·1. Each arrangement is a cyclic column shift by whole
frames: display column = (kit column + column_shift) mod 128. Kit columns are those of A, in which
the kit mask, the official design and the projection are defined; layout positions use display
columns. The data is ``data/kit_31203_arrangements.json``.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "kit_31203_arrangements.json"
ARRANGEMENT_IDS = ("A", "B", "C")
DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
SAME_PIECES_NOTE = "Every arrangement uses the same pieces; only the frames' order changes."


class ArrangementError(ValueError):
    """An unknown arrangement, or a layout that cannot be arranged."""


@dataclass(frozen=True)
class Frame:
    number: int
    name: str
    columns: Tuple[int, int]
    section_columns: str

    @property
    def width(self) -> int:
        return self.columns[1] - self.columns[0] + 1

    @property
    def label(self) -> str:
        return f"{self.number} {self.name}"


@dataclass(frozen=True)
class Arrangement:
    id: str
    name: str
    centre: str
    frame_order: Tuple[int, ...]
    column_shift: int
    width: int = 128

    def to_display(self, x: int) -> int:
        return (x + self.column_shift) % self.width

    def to_kit(self, x: int) -> int:
        return (x - self.column_shift) % self.width

    def roll(self, a: np.ndarray) -> np.ndarray:
        """A kit-coordinate array (rows x 128) as hung (display coordinates)."""
        return np.roll(a, self.column_shift, axis=1)

    def unroll(self, a: np.ndarray) -> np.ndarray:
        """A display-coordinate array back in kit coordinates."""
        return np.roll(a, -self.column_shift, axis=1)

    def frame_spans(self) -> List[Tuple[Frame, int, int]]:
        """(frame, first display column, last display column), left to right as hung."""
        by_number = {f.number: f for f in frames()}
        out, x = [], 0
        for n in self.frame_order:
            f = by_number[n]
            out.append((f, x, x + f.width - 1))
            x += f.width
        return out

    def boundaries(self) -> Tuple[int, ...]:
        """Display columns where a frame starts, other than column 0."""
        return tuple(s for _, s, _ in self.frame_spans() if s > 0)

    def frame_at(self, x: int) -> Frame:
        """The physical frame at display column ``x``."""
        for f, s, e in self.frame_spans():
            if s <= x <= e:
                return f
        raise ArrangementError(f"column {x} is outside 0-{self.width - 1}")

    def describe(self) -> str:
        order = "·".join(str(n) for n in self.frame_order)
        return f"{self.id} ({self.name}, frames {order}, {self.centre} in the centre)"

    def record(self) -> Dict[str, Any]:
        """The ``metadata.arrangement`` block of a layout."""
        src = load_arrangements().source
        return {"id": self.id, "name": self.name, "centre": self.centre,
                "frame_order": list(self.frame_order), "column_shift": self.column_shift,
                "source": {k: src[k] for k in ("title", "url", "sha256", "pages", "citation")}}


@dataclass(frozen=True)
class ArrangementData:
    frames: Tuple[Frame, ...]
    arrangements: Tuple[Arrangement, ...]
    source: Dict[str, Any]
    disclaimer: str


@lru_cache(maxsize=None)
def load_arrangements(path: Optional[str] = None) -> ArrangementData:
    raw = json.loads(Path(path or DATA_PATH).read_text(encoding="utf-8"))
    width = int(raw["width"])
    fr = tuple(Frame(number=int(f["number"]), name=f["name"], columns=tuple(f["columns"]),
                     section_columns=f["section_columns"]) for f in raw["frames"])
    x = 0
    for f in fr:  # frames tile the grid in kit order
        if f.columns[0] != x or f.width % 16:
            raise ArrangementError(f"{DATA_PATH.name}: frame {f.number} does not continue at column {x}")
        x = f.columns[1] + 1
    if x != width:
        raise ArrangementError(f"{DATA_PATH.name}: frames cover {x} of {width} columns")
    widths = {f.number: f.width for f in fr}
    out = []
    for a in raw["arrangements"]:
        order = tuple(int(n) for n in a["frame_order"])
        if sorted(order) != sorted(widths):
            raise ArrangementError(f"{DATA_PATH.name}: arrangement {a['id']} frame order {order}")
        start_of_1 = sum(widths[n] for n in order[:order.index(1)])
        shift = int(a["column_shift"])
        if shift % width != start_of_1 % width:
            raise ArrangementError(f"{DATA_PATH.name}: arrangement {a['id']} column_shift {shift} does not "
                                   f"match its frame order (frame 1 starts at display column {start_of_1})")
        out.append(Arrangement(id=a["id"], name=a["name"], centre=a["centre"], frame_order=order,
                               column_shift=shift, width=width))
    if tuple(a.id for a in out) != ARRANGEMENT_IDS:
        raise ArrangementError(f"{DATA_PATH.name}: arrangements must be {', '.join(ARRANGEMENT_IDS)}")
    disclaimer = raw["source"].get("disclaimer")
    if disclaimer != DISCLAIMER:
        raise ArrangementError(f"{DATA_PATH.name}: missing disclaimer")
    return ArrangementData(frames=fr, arrangements=tuple(out), source=dict(raw["source"]),
                           disclaimer=disclaimer)


def frames() -> Tuple[Frame, ...]:
    return load_arrangements().frames


def valid_values() -> List[str]:
    arr = load_arrangements().arrangements
    return [a.id for a in arr] + [a.name for a in arr]


def parse_arrangement(value: Optional[str]) -> Arrangement:
    """``A``/``B``/``C`` or a name (``europe-africa``, ``americas``, ``asia-australia``), any case;
    None is A."""
    arr = load_arrangements().arrangements
    if value is None:
        return arr[0]
    v = str(value).strip().lower()
    for a in arr:
        if v in (a.id.lower(), a.name):
            return a
    raise ArrangementError(f"unknown arrangement {value!r}; use one of {', '.join(valid_values())}")


def arrangement_of(grid) -> Arrangement:
    """The arrangement a layout records (``metadata.arrangement``); none recorded means A."""
    rec = getattr(grid, "arrangement", None)
    if not rec:
        return parse_arrangement(None)
    aid = rec.get("id") if isinstance(rec, dict) else None
    try:
        a = parse_arrangement(aid) if aid in ARRANGEMENT_IDS else None
    except ArrangementError:
        a = None
    if a is None:
        raise ArrangementError(f"layout records an unknown arrangement {aid!r}; expected one of "
                               f"{', '.join(ARRANGEMENT_IDS)}")
    return a


def arrange_grid(grid, target: Arrangement):
    """``grid`` re-hung as ``target``: every position moves by whole frames (x shifts by the
    difference of the two column shifts, mod 128); colors, parts and other metadata are kept.
    Positions are written in row-major order of the new columns."""
    from .grid import PositionPlacementGrid
    from .position import PositionPlacement

    current = arrangement_of(grid)
    if grid.width != target.width:
        raise ArrangementError(f"layout width is {grid.width}; arrangements need the {target.width}-column kit grid")
    delta = target.column_shift - current.column_shift
    moved = []
    for p in grid.positions:
        if not (0 <= p.x < grid.width and 0 <= p.y < grid.height):
            raise ArrangementError(f"position ({p.x}, {p.y}) is outside the {grid.width} x {grid.height} grid")
        d = p.to_dict()
        d["x"] = (p.x + delta) % grid.width
        moved.append(PositionPlacement.from_dict(d))
    moved.sort(key=lambda p: (p.y, p.x))
    return PositionPlacementGrid(width=grid.width, height=grid.height, positions=moved,
                                 source_image=grid.source_image, generated_at=grid.generated_at,
                                 schema_version=grid.schema_version, map_metadata=grid.map_metadata,
                                 arrangement=target.record())

"""How the kit's frames are hung: combinations A-E (features 007 and 010).

LEGO 31203 building instructions, pp. 7-8 ("1 world - 3 combinations"): frame 1 America (kit
columns 0-31, strips A-B), frame 2 Europe & Africa (32-95, strips C-F), frame 3 Asia & Australia
(96-127, strips G-H), hung as A = 1·2·3 (default), B = 3·1·2 or C = 2·3·1. Feature 010 adds two
combinations that are not among the instructions' three: D = 2b·3·1·2a (``pacific``, the date line
centred) and E = 2b·3·1·2a (``asia-pacific``, 146° E centred), frame 2 split between two of its
strips. They are possible because a joint inside a frame uses the same 15 connector pegs as a joint
between frames (pp. 134-139) and the border is built round the finished board (p. 140).

Every arrangement is a cyclic rotation of the 8 strips (16 columns each): display column =
(kit column + column_shift) mod 128. Kit columns are those of A, in which the kit mask, the official
design and the projection are defined; layout positions use display columns. The data is
``data/kit_31203_arrangements.json`` (format 2).
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
ARRANGEMENT_IDS = ("A", "B", "C", "D", "E")
INSTRUCTION_IDS = ("A", "B", "C")  # the building instructions' combinations (pp. 7-8, 139)
FORMAT_VERSION = "2"
STRIP_LETTERS = "ABCDEFGH"
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

    @property
    def strips(self) -> str:
        """The kit strips (section column letters) of this frame, e.g. ``"CDEF"``."""
        return STRIP_LETTERS[self.columns[0] // 16:(self.columns[1] + 1) // 16]


@dataclass(frozen=True)
class Group:
    """A frame, or a part of a split frame (``2a``/``2b``), as hung: display columns start-end."""

    label: str
    frame: Frame
    strips: str
    start: int
    end: int

    @property
    def strip_range(self) -> str:
        return self.strips if len(self.strips) == 1 else f"{self.strips[0]}-{self.strips[-1]}"


@dataclass(frozen=True)
class Joint:
    """The joint between neighbouring strips ``left`` and ``right`` (kit letters) at display column
    ``x``: ``kept`` inside a group (pegged with its frame), ``make`` between groups."""

    left: str
    right: str
    x: int
    kind: str

    @property
    def text(self) -> str:
        return f"{self.left}|{self.right}"


@dataclass(frozen=True)
class AssemblyFacts:
    """Peg counts for hanging the board (pp. 134-139); ``pegs_supplied`` is the kit inventory's
    quantity of the connector peg (kit_31203_inventory.json, p. 159)."""

    pegs_per_joint: int
    pegs_per_base_joint: int
    bases_per_strip: int
    peg_design_id: str
    joint_pages: str
    border_pages: str
    pegs_supplied: int
    n_strips: int = 8

    @property
    def strip_joints(self) -> int:
        return self.n_strips - 1

    @property
    def base_joints(self) -> int:
        return self.n_strips * (self.bases_per_strip - 1)

    @property
    def pegs_used(self) -> int:
        return self.strip_joints * self.pegs_per_joint + self.base_joints * self.pegs_per_base_joint


@dataclass(frozen=True)
class Arrangement:
    id: str
    name: str
    centre: str
    frame_order: Tuple[int, ...]
    column_shift: int
    width: int = 128
    strips: str = STRIP_LETTERS
    groups: Tuple[str, ...] = ()
    in_instructions: bool = True

    @property
    def is_split(self) -> bool:
        """True when a frame is hung in two parts (D, E)."""
        return len(self.frame_order) != len(set(self.frame_order))

    @property
    def order_text(self) -> str:
        """``1·2·3`` or ``2b·3·1·2a``."""
        return "·".join(self.groups or tuple(str(n) for n in self.frame_order))

    @property
    def source(self) -> Dict[str, Any]:
        """The citation for this combination: pp. 7-8 (A-C), the joints pages 134-140 (D, E)."""
        data = load_arrangements()
        return data.source if self.in_instructions else data.joints_source

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

    def group_spans(self) -> List[Group]:
        """The frames or frame parts left to right as hung, with their display columns."""
        return list(_group_spans(self.strips, self.groups, self.width))

    def frame_spans(self) -> List[Tuple[Frame, int, int]]:
        """(frame, first display column, last display column) of each group, left to right as
        hung; a split frame appears twice."""
        return [(g.frame, g.start, g.end) for g in self.group_spans()]

    def boundaries(self) -> Tuple[int, ...]:
        """Display columns where a frame or frame part starts, other than column 0."""
        return tuple(g.start for g in self.group_spans() if g.start > 0)

    def group_at(self, x: int) -> Group:
        for g in self.group_spans():
            if g.start <= x <= g.end:
                return g
        raise ArrangementError(f"column {x} is outside 0-{self.width - 1}")

    def frame_at(self, x: int) -> Frame:
        """The physical frame at display column ``x``."""
        return self.group_at(x).frame

    def joints(self) -> List[Joint]:
        """The 7 strip joints as hung, left to right."""
        out = []
        for i in range(len(self.strips) - 1):
            a, b = self.group_at(16 * i), self.group_at(16 * (i + 1))
            out.append(Joint(self.strips[i], self.strips[i + 1], 16 * (i + 1),
                             "kept" if a == b else "make"))
        return out

    def unpeg(self) -> List[Tuple[str, str]]:
        """Joints inside the kit's frames (as built, p. 137) that this combination takes apart."""
        kept = {(j.left, j.right) for j in self.joints() if j.kind == "kept"}
        return [pair for pair in _frame_joints() if pair not in kept]

    def describe(self) -> str:
        text = f"{self.id} ({self.name}, frames {self.order_text}, {self.centre} in the centre"
        return text + (")" if self.in_instructions else "; not in the building instructions)")

    def record(self) -> Dict[str, Any]:
        """The ``metadata.arrangement`` block of a layout (A-C exactly as in feature 007)."""
        src = self.source
        out: Dict[str, Any] = {"id": self.id, "name": self.name, "centre": self.centre,
                               "frame_order": list(self.frame_order), "column_shift": self.column_shift}
        if not self.in_instructions:
            out.update(strips=self.strips, groups=list(self.groups), in_instructions=False)
        out["source"] = {k: src[k] for k in ("title", "url", "sha256", "pages", "citation")}
        return out


@dataclass(frozen=True)
class ArrangementData:
    frames: Tuple[Frame, ...]
    arrangements: Tuple[Arrangement, ...]
    source: Dict[str, Any]
    disclaimer: str
    joints_source: Dict[str, Any]
    assembly: AssemblyFacts


def _frame_of_strip(letter: str) -> Frame:
    x = 16 * STRIP_LETTERS.index(letter)
    for f in frames():
        if f.columns[0] <= x <= f.columns[1]:
            return f
    raise ArrangementError(f"strip {letter} is in no frame")


def _frame_joints() -> List[Tuple[str, str]]:
    """Strip joints inside the kit's frames: A|B, C|D, D|E, E|F, G|H."""
    return [(f.strips[i], f.strips[i + 1]) for f in frames() for i in range(len(f.strips) - 1)]


def _runs(strips: str, fr: Tuple[Frame, ...]) -> List[Tuple[int, str]]:
    """(frame number, strips) of each run of strips of one frame, left to right; split parts
    labelled later."""
    of = {letter: f.number for f in fr for letter in f.strips}
    runs: List[Tuple[int, str]] = []
    for letter in strips:
        if runs and runs[-1][0] == of[letter]:
            runs[-1] = (runs[-1][0], runs[-1][1] + letter)
        else:
            runs.append((of[letter], letter))
    return runs


def _labels(runs: List[Tuple[int, str]]) -> Tuple[str, ...]:
    """``"2"`` for a whole frame; ``"2a"`` (lower kit columns) and ``"2b"`` for a split one."""
    out = []
    for n, strip in runs:
        parts = sorted(s for m, s in runs if m == n)
        out.append(str(n) if len(parts) == 1 else f"{n}{'ab'[parts.index(strip)]}")
    return tuple(out)


@lru_cache(maxsize=None)
def _group_spans(strips: str, groups: Tuple[str, ...], width: int) -> List[Group]:
    runs = _runs(strips, frames())
    by_number = {f.number: f for f in frames()}
    out, x = [], 0
    for (n, letters), label in zip(runs, groups or _labels(runs)):
        out.append(Group(label, by_number[n], letters, x, x + 16 * len(letters) - 1))
        x += 16 * len(letters)
    return out


def _assembly_facts(raw: Dict[str, Any], n_strips: int) -> AssemblyFacts:
    from ..kit.inventory import load_kit_inventory

    design = str(raw["peg_design_id"])
    supplied = sum(e.quantity for e in load_kit_inventory().elements if e.design_id == design)
    if not supplied:
        raise ArrangementError(f"{DATA_PATH.name}: connector peg {design} is not in the kit inventory")
    return AssemblyFacts(pegs_per_joint=int(raw["pegs_per_joint"]),
                         pegs_per_base_joint=int(raw["pegs_per_base_joint"]),
                         bases_per_strip=int(raw["bases_per_strip"]), peg_design_id=design,
                         joint_pages=str(raw["joint_pages"]), border_pages=str(raw["border_pages"]),
                         pegs_supplied=supplied, n_strips=n_strips)


@lru_cache(maxsize=None)
def load_arrangements(path: Optional[str] = None) -> ArrangementData:
    raw = json.loads(Path(path or DATA_PATH).read_text(encoding="utf-8"))
    name = DATA_PATH.name
    if str(raw.get("format_version")) != FORMAT_VERSION:
        raise ArrangementError(f"{name}: format_version must be {FORMAT_VERSION}")
    width = int(raw["width"])
    fr = tuple(Frame(number=int(f["number"]), name=f["name"], columns=tuple(f["columns"]),
                     section_columns=f["section_columns"]) for f in raw["frames"])
    x = 0
    for f in fr:  # frames tile the grid in kit order, in whole 16-column strips
        if f.columns[0] != x or f.width % 16:
            raise ArrangementError(f"{name}: frame {f.number} does not continue at column {x}")
        x = f.columns[1] + 1
    if x != width or width != 16 * len(STRIP_LETTERS):
        raise ArrangementError(f"{name}: frames cover {x} of {width} columns")
    widths = {f.number: f.width for f in fr}
    rotations = {STRIP_LETTERS[i:] + STRIP_LETTERS[:i] for i in range(len(STRIP_LETTERS))}
    out = []
    for a in raw["arrangements"]:
        aid = a["id"]
        order = tuple(int(n) for n in a["frame_order"])
        strips = str(a["strips"])
        if strips not in rotations:
            raise ArrangementError(f"{name}: arrangement {aid} strips {strips!r} is not a rotation of "
                                   f"{STRIP_LETTERS}")
        shift = int(a["column_shift"])
        start_of_a = 16 * strips.index("A")
        if shift % width != start_of_a % width:
            raise ArrangementError(f"{name}: arrangement {aid} column_shift {shift} does not match its "
                                   f"strips (strip A starts at display column {start_of_a})")
        runs = _runs(strips, fr)
        if order != tuple(n for n, _ in runs) or sorted(set(order)) != sorted(widths):
            raise ArrangementError(f"{name}: arrangement {aid} frame order {order} does not match its "
                                   f"strips {strips}")
        groups = tuple(str(g) for g in a["groups"])
        if groups != _labels(runs):
            raise ArrangementError(f"{name}: arrangement {aid} groups {list(groups)} do not match its "
                                   f"strips (expected {list(_labels(runs))})")
        official = a["in_instructions"]
        if official is not (aid in INSTRUCTION_IDS):
            raise ArrangementError(f"{name}: arrangement {aid} in_instructions must be "
                                   f"{str(aid in INSTRUCTION_IDS).lower()}")
        out.append(Arrangement(id=aid, name=a["name"], centre=a["centre"], frame_order=order,
                               column_shift=shift, width=width, strips=strips, groups=groups,
                               in_instructions=official))
    if tuple(a.id for a in out) != ARRANGEMENT_IDS:
        raise ArrangementError(f"{name}: arrangements must be {', '.join(ARRANGEMENT_IDS)}")
    disclaimer = raw["source"].get("disclaimer")
    if disclaimer != DISCLAIMER or raw["joints_source"].get("disclaimer") != DISCLAIMER:
        raise ArrangementError(f"{name}: missing disclaimer")
    return ArrangementData(frames=fr, arrangements=tuple(out), source=dict(raw["source"]),
                           disclaimer=disclaimer, joints_source=dict(raw["joints_source"]),
                           assembly=_assembly_facts(raw["assembly"], len(STRIP_LETTERS)))


def frames() -> Tuple[Frame, ...]:
    return load_arrangements().frames


def valid_values() -> List[str]:
    arr = load_arrangements().arrangements
    return [a.id for a in arr] + [a.name for a in arr]


def parse_arrangement(value: Optional[str]) -> Arrangement:
    """``A``-``E`` or a name (``europe-africa``, ``americas``, ``asia-australia``, ``pacific``,
    ``asia-pacific``), any case; None is A."""
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
    """``grid`` re-hung as ``target``: every position moves by whole strips (x shifts by the
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


# --- assembly steps (feature 010; shared by the build sheets and the web prebuild) -------------

def _and(items: List[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _citation_ascii(src: Dict[str, Any]) -> str:
    return src["citation"].replace("–", "-")


def assembly_note(a: Arrangement) -> str:
    """Whether the combination is in the building instructions and, for D and E, why it is
    possible (with the citation)."""
    if a.in_instructions:
        return (f"Combination {a.id} is one of the three combinations in the building instructions "
                f"({_citation_ascii(load_arrangements().source)} and 139).")
    facts = load_arrangements().assembly
    return (f"Combination {a.id} is not one of the three combinations in the building instructions. "
            f"It is possible because a joint inside a frame uses the same {facts.pegs_per_joint} "
            "connector pegs as a joint between frames and the white border is built round the "
            "finished board, so the 8 strips can be hung in any rotation with one kit's parts "
            f"({_citation_ascii(a.source)}).")


def assembly_steps(a: Arrangement) -> List[str]:
    """Numbered-step texts (without numbers) for hanging the board as ``a``, after the example of
    the building instructions' p. 139. ASCII and Latin-1 only, so the PDF can print them."""
    facts = load_arrangements().assembly
    fr = frames()
    built = ", ".join(f"frame {f.number} {f.name} = strips {f.strips[0]}-{f.strips[-1]}" for f in fr)
    steps = [f"Build the 40 section bases and peg them into 8 strips of five, then the strips into "
             f"the three frames, as in the building instructions (pp. 134-138): {built}."]
    split = a.unpeg()
    if split:
        spans = a.group_spans()
        parts = sorted((g for g in spans if sum(h.frame == g.frame for h in spans) > 1),
                       key=lambda g: g.label)
        left, right = split[0]
        n = parts[0].frame.number
        steps.append(f"Unpeg frame {n} between strips {left} and {right}: take out that joint's "
                     f"{facts.pegs_per_joint} connector pegs and keep them for the joints below. "
                     f"Frame {n} is now " + " and ".join(f"part {g.label} (strips {g.strip_range})"
                                                         for g in parts) + ".")
    what = "groups" if a.is_split else "frames"
    steps.append(f"Lay the {what} face up, left to right: {' · '.join(a.groups)} "
                 f"(strips {' '.join(a.strips)}).")
    joins = [j.text for j in a.joints() if j.kind == "make"]
    steps.append(f"Peg the {what} together at {_and(joins)}, {facts.pegs_per_joint} connector pegs "
                 "per joint, as for the frame joints on p. 139.")
    steps.append(f"Build the white border round the whole board as in pp. {facts.border_pages}; it is "
                 "the same for every combination.")
    steps.append(f"Connector pegs (part {facts.peg_design_id}): {facts.strip_joints} strip joints x "
                 f"{facts.pegs_per_joint} + {facts.n_strips} strips x {facts.bases_per_strip - 1} base "
                 f"joints x {facts.pegs_per_base_joint} = {facts.pegs_used} of the "
                 f"{facts.pegs_supplied} in the kit, the same for every combination; no extra parts.")
    return steps

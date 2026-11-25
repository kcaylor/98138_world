"""Black tiles and plates for the map sticker plaques, with cited IDs (feature 017; ``plaque_parts.json``).

A plaque is a Black tile on a Black plate of the same size; the printed sticker goes on the tile.
Small: tile 6x6 (10202) on plate 6x6 (3958); large: smooth tile 8x16 (4974) on plate 8x16 (92438),
studs given as width x height as the sticker is read. None of the four parts is in kit 31203. The
values come from pinned snapshots (``tools/partcolors plaque-parts``); nothing here is typed in by
hand. The loader returns the same ``PartNumbers`` and ``PartColor`` objects as the map parts, and
re-checks rules 3 and 5-9 of the file's contract (specs/017-map-stickers/contracts/plaque-parts-file.md).
``part_colors.json`` and ``part_numbers.json`` are not changed by this file.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .colors import CATALOGS, CITATION_FIELDS, DATA_DIR, CatalogColor
from .inventory import load_kit_inventory
from .part_colors import PartColor
from .part_numbers import PartNumbers, PinnedPage
from .source import DISCLAIMER, Citation

PLAQUE_PARTS_PATH = DATA_DIR / "plaque_parts.json"
SIZES = ("small", "large")
KINDS = ("tile", "plate")
COLOR_KEY = "lego_black"
BLACK_BRICKLINK = CatalogColor(name="Black", id=11)  # BrickLink color guide (contract rule 6)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class PlaquePart:
    """One Black part of a plaque: the tile that carries the sticker, or the plate under it."""

    part_id: str
    kind: str
    studs: Tuple[int, int]
    name: str
    numbers: PartNumbers
    color: PartColor


@dataclass(frozen=True)
class Plaque:
    """A plaque size: ``tile`` on ``plate``, both ``studs`` (width x height as the sticker is read)."""

    size: str
    tile: PlaquePart
    plate: PlaquePart
    studs: Tuple[int, int]

    @property
    def parts(self) -> Tuple[PlaquePart, PlaquePart]:
        return (self.tile, self.plate)


@dataclass(frozen=True)
class PlaquePartTable:
    source: Dict[str, Any]
    snapshots: Tuple[PinnedPage, ...]
    parts: Dict[str, PlaquePart]
    plaques: Dict[str, Plaque]

    def __hash__(self) -> int:
        return id(self)

    def get(self, part_id: str) -> PlaquePart:
        if part_id not in self.parts:
            raise KeyError(f"part {part_id} is not in plaque_parts.json (known: {sorted(self.parts)})")
        return self.parts[part_id]


def _fail(rule: str) -> ValueError:
    return ValueError(f"plaque_parts.json: {rule}")


def _str(v: Any) -> bool:
    return isinstance(v, str) and bool(v)


def _int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _studs(v: Any, where: str) -> Tuple[int, int]:
    if not (isinstance(v, list) and len(v) == 2 and all(_int(n) and n > 0 for n in v)):
        raise _fail(f"{where}: studs must be two positive integers [width, height]")
    return (v[0], v[1])


def _snapshots(source: Dict[str, Any]) -> Dict[str, PinnedPage]:
    out: List[PinnedPage] = []
    for i, s in enumerate(source.get("snapshots") or []):
        if not isinstance(s, dict) or not all(_str(s.get(k)) for k in ("id", "title", "url", "accessed")):
            raise _fail(f"source.snapshots[{i}]: id, title, url and accessed are required")
        if not isinstance(s.get("sha256"), str) or not _SHA256_RE.match(s["sha256"]):
            raise _fail(f"rule 8: source.snapshots[{i}] {s['id']}: sha256 must be 64 lowercase hex characters")
        if not _DATE_RE.match(s["accessed"]):
            raise _fail(f"rule 8: source.snapshots[{i}] {s['id']}: accessed must be YYYY-MM-DD")
        out.append(PinnedPage(s["id"], s["title"], s["url"], s["sha256"], s["accessed"]))
    by_id = {p.id: p for p in out}
    if not out or len(by_id) != len(out):
        raise _fail("source.snapshots must be a non-empty list with unique ids")
    return by_id


def _citation(by_id: Dict[str, PinnedPage], cid: Any, where: str) -> PinnedPage:
    if cid not in by_id:
        raise _fail(f"rule 8: {where}: citation {cid!r} does not resolve to source.snapshots")
    return by_id[cid]


def _kit_ids() -> Tuple[set, set]:
    inv = load_kit_inventory()
    parts = {p for e in inv.elements for p in e.part_ids} | {e.design_id for e in inv.elements if e.design_id}
    return parts, {e.element_id for e in inv.elements}


def _part(part_id: str, row: Any, by_id: Dict[str, PinnedPage], kit_parts: set,
          kit_elements: set) -> PlaquePart:
    where = f"parts.{part_id}"
    if not isinstance(row, dict):
        raise _fail(f"{where} must be an object")
    kind = row.get("kind")
    if kind not in KINDS:
        raise _fail(f"{where}: kind must be one of {KINDS}")
    studs = _studs(row.get("studs"), where)
    if not _str(row.get("name")):
        raise _fail(f"{where}: name is required")
    designs = row.get("lego_design_ids")
    if not (isinstance(designs, list) and designs and all(_str(d) and d.isdigit() for d in designs)):
        raise _fail(f"{where}: lego_design_ids must be a non-empty list of design IDs")
    bl, rb, col = row.get("bricklink") or {}, row.get("rebrickable") or {}, row.get("color") or {}
    if bl.get("item_type") != "P" or not _str(bl.get("item_no")):
        raise _fail(f"{where}: bricklink item_type 'P' and item_no are required")
    alternates = bl.get("alternates")
    if not (isinstance(alternates, list) and all(_str(a) for a in alternates)):
        raise _fail(f"{where}: bricklink alternates must be a list of item numbers")
    colors = bl.get("colors")
    if not (isinstance(colors, list) and colors and all(_str(c) for c in colors)):
        raise _fail(f"{where}: bricklink colors must be a non-empty list of names")
    if not _str(rb.get("part_num")):
        raise _fail(f"{where}: rebrickable part_num is required")
    # rule 3
    if rb["part_num"] != part_id:
        raise _fail(f"rule 3: {where}: rebrickable part_num {rb['part_num']!r} must equal the part ID {part_id}")
    # rule 5
    if part_id != bl["item_no"] and part_id not in alternates:
        raise _fail(f"rule 5: {where}: {part_id} must be the BrickLink item number {bl['item_no']} "
                    f"or one of its alternates {alternates}")
    # rule 9 (color key)
    if col.get("key") != COLOR_KEY:
        raise _fail(f"rule 9: {where}: color key {col.get('key')!r}; only {COLOR_KEY!r} is allowed")
    cats = {}
    for cat in CATALOGS:
        entry = col.get(cat) or {}
        if not _str(entry.get("name")) or not _int(entry.get("id")):
            raise _fail(f"{where}: color {cat} name and id are required (non-null)")
        cats[cat] = CatalogColor(name=entry["name"], id=entry["id"])
    # rule 6
    if cats["bricklink"] != BLACK_BRICKLINK or BLACK_BRICKLINK.name not in colors:
        raise _fail(f"rule 6: {where}: BrickLink's colors for the item must list Black "
                    f"(BrickLink id {BLACK_BRICKLINK.id}); color is {cats['bricklink']}, colors {colors}")
    element_id = col.get("element_id")
    if not _str(element_id) or not element_id.isdigit():
        raise _fail(f"{where}: color element_id must be digits")
    element_ids = col.get("element_ids")
    if not (isinstance(element_ids, list) and element_id in element_ids
            and all(_str(e) and e.isdigit() for e in element_ids)):
        raise _fail(f"{where}: color element_ids must be a list of element IDs that includes {element_id}")
    rgb = col.get("rgb")
    if not (isinstance(rgb, list) and len(rgb) == 3 and all(_int(v) and 0 <= v <= 255 for v in rgb)):
        raise _fail(f"{where}: color rgb must be three integers 0-255")
    # rule 8 (citations)
    numbers_cits = {"bricklink": _citation(by_id, bl.get("citation"), f"{where}.bricklink"),
                    "rebrickable": _citation(by_id, rb.get("citation"), f"{where}.rebrickable")}
    color_cits = {}
    for f in CITATION_FIELDS:
        p = _citation(by_id, (col.get("citations") or {}).get(f), f"{where}.color.citations.{f}")
        color_cits[f] = Citation(id=p.id, title=p.title, url=p.url, accessed=p.accessed)
    # rule 7 (not in the kit)
    in_kit = sorted(({part_id, bl["item_no"], *designs} & kit_parts) | (set(element_ids) & kit_elements))
    if in_kit:
        raise _fail(f"rule 7: {where}: {in_kit} is in the kit 31203 inventory; plaque parts are not kit parts")
    numbers = PartNumbers(
        part_id=part_id, name=row["name"], lego_design_ids=tuple(designs), bricklink_item_type="P",
        bricklink_item_no=bl["item_no"], bricklink_alternates=tuple(alternates),
        bricklink_colors=tuple(colors), rebrickable_part_num=rb["part_num"],
        rebrickable_name=str(rb.get("name") or ""), citations=numbers_cits)
    color = PartColor(
        key=COLOR_KEY, part_id=part_id, element_id=element_id, lego=cats["lego"],
        bricklink=cats["bricklink"], rebrickable=cats["rebrickable"], rgb=tuple(rgb), in_kit=False,
        citations=color_cits, element_ids=tuple(element_ids), notes=str(col.get("notes", "") or ""))
    return PlaquePart(part_id=part_id, kind=kind, studs=studs, name=row["name"], numbers=numbers, color=color)


def parse_plaque_parts(data: Dict[str, Any]) -> PlaquePartTable:
    """Parse and validate (contract rules 3 and 5-9; data-model.md PlaquePart validation)."""
    if not isinstance(data, dict) or data.get("format_version") != "1":
        raise _fail("format_version must be '1'")
    source = data.get("source")
    if not isinstance(source, dict):
        raise _fail("source is required")
    if source.get("disclaimer") != DISCLAIMER:
        raise _fail(f"rule 9: source.disclaimer must be {DISCLAIMER!r}")
    if data.get("disclaimer") != DISCLAIMER:
        raise _fail(f"rule 9: disclaimer must be {DISCLAIMER!r}")
    if not isinstance(source.get("generated_on"), str) or not _DATE_RE.match(source["generated_on"]):
        raise _fail("rule 8: source.generated_on must be YYYY-MM-DD")
    by_id = _snapshots(source)
    terms = source.get("terms")
    if not isinstance(terms, dict) or not all(_str(terms.get(k)) for k in ("text", "url", "sha256", "accessed")):
        raise _fail("source.terms (Rebrickable's terms: text, url, sha256, accessed) is required")
    if not _SHA256_RE.match(terms["sha256"]):
        raise _fail("rule 8: source.terms.sha256 must be 64 lowercase hex characters")
    if not _DATE_RE.match(terms["accessed"]):
        raise _fail("rule 8: source.terms.accessed must be YYYY-MM-DD")
    raw_parts = data.get("parts")
    if not isinstance(raw_parts, dict) or not raw_parts:
        raise _fail("parts must be a non-empty object")
    kit_parts, kit_elements = _kit_ids()
    parts = {pid: _part(pid, row, by_id, kit_parts, kit_elements) for pid, row in raw_parts.items()}
    raw_plaques = data.get("plaques")
    if not isinstance(raw_plaques, dict) or sorted(raw_plaques) != sorted(SIZES):
        raise _fail(f"plaques must list exactly {SIZES}")
    plaques: Dict[str, Plaque] = {}
    used: List[str] = []
    for size in SIZES:
        row, where = raw_plaques[size], f"plaques.{size}"
        if not isinstance(row, dict):
            raise _fail(f"{where} must be an object")
        studs = _studs(row.get("studs"), where)
        slots = {}
        for kind in KINDS:
            pid = row.get(kind)
            if pid not in parts:
                raise _fail(f"{where}: {kind} {pid!r} is not in parts")
            part = parts[pid]
            # rule 7 (slot kind and studs)
            if part.kind != kind:
                raise _fail(f"rule 7: {where}: {kind} {pid} is a {part.kind}")
            if part.studs != studs:
                raise _fail(f"rule 7: {where}: {kind} {pid} has studs {list(part.studs)}, "
                            f"the plaque {list(studs)}")
            slots[kind] = part
            used.append(pid)
        plaques[size] = Plaque(size=size, tile=slots["tile"], plate=slots["plate"], studs=studs)
    if sorted(used) != sorted(parts):
        raise _fail("every part must be the tile or the plate of exactly one plaque")
    return PlaquePartTable(source=dict(source), snapshots=tuple(by_id.values()), parts=parts,
                           plaques=plaques)


@lru_cache(maxsize=None)
def _load(path: Path) -> PlaquePartTable:
    with open(path, "r", encoding="utf-8") as f:
        return parse_plaque_parts(json.load(f))


def load_plaque_parts(path: Optional[Path] = None) -> PlaquePartTable:
    """The shipped plaque part table (package data; no network)."""
    return _load(Path(path) if path else PLAQUE_PARTS_PATH)

"""Colors in which the map parts are made, with cited IDs (FR-016; ``part_colors.json``).

Part 6141 (1x1 round plate, land) and 98138 (1x1 round tile, ocean), the kit's two map parts, and
since feature 016 part 3070b (1x1 square tile, the margin of a non-kit template), which is not in
the kit: every 3070b row has ``in_kit: false`` and the kit-color rules apply to the kit's parts
only. Since feature 005 the table
holds every opaque color of each part that passes the five join rules (``tools/partcolors``), and
``source.terms`` records Rebrickable's terms: free for personal and commercial use with
acknowledgement of Rebrickable as the data source. Kit colors must equal
``kit_colors.json``, which stays the authority for them. Rows with a missing ID or a note that
marks them as an estimate are rejected (constitution V).
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .colors import CATALOGS, CITATION_FIELDS, DATA_DIR, CatalogColor, load_kit_color_table
from .source import DISCLAIMER, Citation

PART_COLORS_PATH = DATA_DIR / "part_colors.json"
PARTS = ("6141", "98138", "3070b")
KIT_PARTS = ("6141", "98138")  # the kit's map parts; 3070b is not in kit 31203 (016)
KIT_ROLE_FOR_PART = {"6141": "land", "98138": "ocean"}
ROLE_FOR_PART = {**KIT_ROLE_FOR_PART, "3070b": "margin"}
_FORBIDDEN_WORDS = ("estimate", "placeholder", "unverified")


@dataclass(frozen=True)
class PartColor:
    key: str
    part_id: str
    element_id: str
    lego: CatalogColor
    bricklink: CatalogColor
    rebrickable: CatalogColor
    rgb: Tuple[int, int, int]
    in_kit: bool
    citations: Dict[str, Citation]
    element_ids: Tuple[str, ...] = ()
    notes: str = ""

    def __hash__(self) -> int:
        return hash((self.part_id, self.key))


@dataclass(frozen=True)
class PartColorTable:
    source: Dict[str, Any]
    citations: Tuple[Citation, ...]
    parts: Dict[str, Tuple[PartColor, ...]]

    def __hash__(self) -> int:
        return id(self)

    def for_part(self, part_id: str) -> Tuple[PartColor, ...]:
        if part_id not in self.parts:
            raise KeyError(f"part {part_id} is not in part_colors.json (known: {sorted(self.parts)})")
        return self.parts[part_id]

    def get(self, part_id: str, key: str) -> Optional[PartColor]:
        for c in self.for_part(part_id):
            if c.key == key:
                return c
        return None

    def by_lego_id(self, part_id: str, lego_id: int) -> Optional[PartColor]:
        """The cited row for ``part_id`` whose LEGO color ID is ``lego_id``, if any."""
        for c in self.for_part(part_id):
            if c.lego.id == lego_id:
                return c
        return None

    def any_part(self, key: str) -> Optional[PartColor]:
        for rows in self.parts.values():
            for c in rows:
                if c.key == key:
                    return c
        return None


def _fail(rule: str) -> ValueError:
    return ValueError(f"part_colors.json: {rule}")


def parse_part_colors(data: Dict[str, Any]) -> PartColorTable:
    source = data.get("source")
    if not isinstance(source, dict) or source.get("disclaimer") != DISCLAIMER:
        raise _fail(f"source.disclaimer must be {DISCLAIMER!r}")
    terms = source.get("terms")
    if not isinstance(terms, dict) or not all(isinstance(terms.get(k), str) and terms[k]
                                              for k in ("text", "url", "sha256", "accessed")):
        raise _fail("source.terms (Rebrickable's terms: text, url, sha256, accessed) is required")
    try:
        cits = [Citation.from_dict(c) for c in source.get("citations") or []]
    except ValueError as exc:
        raise _fail(str(exc)) from exc
    by_id = {c.id: c for c in cits}
    if len(by_id) != len(cits):
        raise _fail("citation ids must be unique")
    kit = {c.key: c for c in load_kit_color_table().colors}
    parts_raw = data.get("parts")
    if not isinstance(parts_raw, dict) or sorted(parts_raw) != sorted(PARTS):
        raise _fail(f"parts must list exactly {PARTS}")
    parts: Dict[str, Tuple[PartColor, ...]] = {}
    for part_id in PARTS:
        rows = parts_raw[part_id]
        if not isinstance(rows, list) or not rows:
            raise _fail(f"parts.{part_id} must be a non-empty list")
        out: List[PartColor] = []
        for i, row in enumerate(rows):
            key = row.get("key")
            where = f"parts.{part_id}[{i}] {key}"
            if not isinstance(key, str) or not key.startswith("lego_"):
                raise _fail(f"{where}: key must start with 'lego_'")
            cats = {}
            for cat in CATALOGS:
                entry = row.get(cat) or {}
                name, cid = entry.get("name"), entry.get("id")
                if not isinstance(name, str) or not name or not isinstance(cid, int) or isinstance(cid, bool):
                    raise _fail(f"{where}: {cat} name and id are required (non-null)")
                cats[cat] = CatalogColor(name=name, id=cid)
            resolved = {}
            for f in CITATION_FIELDS:
                cid = (row.get("citations") or {}).get(f)
                if cid not in by_id:
                    raise _fail(f"{where}: citation {cid!r} for {f} does not resolve to source.citations")
                resolved[f] = by_id[cid]
            rgb = row.get("rgb")
            if not (isinstance(rgb, list) and len(rgb) == 3 and all(isinstance(v, int) and 0 <= v <= 255 for v in rgb)):
                raise _fail(f"{where}: rgb must be three integers 0-255")
            element_id = row.get("element_id")
            if not isinstance(element_id, str) or not element_id.isdigit():
                raise _fail(f"{where}: element_id is required")
            notes = str(row.get("notes", "") or "")
            if any(w in notes.lower() for w in _FORBIDDEN_WORDS):
                raise _fail(f"{where}: entry marked as estimate/placeholder")
            in_kit = bool(row.get("in_kit"))
            if in_kit and part_id not in KIT_PARTS:
                raise _fail(f"{where}: part {part_id} is not in kit 31203; in_kit must be false")
            pc = PartColor(key=key, part_id=part_id, element_id=element_id, lego=cats["lego"],
                           bricklink=cats["bricklink"], rebrickable=cats["rebrickable"],
                           rgb=tuple(rgb), in_kit=in_kit, citations=resolved,
                           element_ids=tuple(row.get("element_ids") or (element_id,)), notes=notes)
            if in_kit:
                k = kit.get(key)
                if k is None or k.role != KIT_ROLE_FOR_PART[part_id] or \
                        (k.element_id, k.lego, k.bricklink, k.rebrickable, tuple(k.rgb)) != \
                        (pc.element_id, pc.lego, pc.bricklink, pc.rebrickable, pc.rgb):
                    raise _fail(f"{where}: kit row must equal kit_colors.json")
            elif key in kit and kit[key].role == ROLE_FOR_PART[part_id]:
                raise _fail(f"{where}: {key} is a kit color of this part; mark it in_kit")
            out.append(pc)
        keys = [c.key for c in out]
        if len(set(keys)) != len(keys):
            raise _fail(f"parts.{part_id}: color keys must be unique")
        missing = [k for k, c in kit.items() if c.role == ROLE_FOR_PART[part_id] and k not in keys]
        if part_id in KIT_PARTS and missing:
            raise _fail(f"parts.{part_id}: kit colors missing: {missing}")
        parts[part_id] = tuple(out)
    return PartColorTable(source=dict(source), citations=tuple(cits), parts=parts)


@lru_cache(maxsize=None)
def _load(path: Path) -> PartColorTable:
    with open(path, "r", encoding="utf-8") as f:
        return parse_part_colors(json.load(f))


def load_part_colors(path: Optional[Path] = None) -> PartColorTable:
    """The shipped part-color table (package data; no network)."""
    return _load(Path(path) if path else PART_COLORS_PATH)


def colors_for_part(part_id: str) -> List[PartColor]:
    """Colors in which ``part_id`` (6141, 98138 or 3070b) is listed; ``KeyError`` for other parts."""
    return list(load_part_colors().for_part(part_id))

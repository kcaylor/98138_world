"""Marketplace part numbers for the kit's two map parts (``part_numbers.json``, feature 005).

Each marketplace numbers the 1x1 round plate differently: BrickLink files it as item 4073 (6141 is
an alternate number), Rebrickable as part 6141, LEGO as design 6141. The 1x1 round tile is 98138 on
both marketplaces (LEGO designs 98138 and 35381). Values come from pinned archived catalog pages
(``tools/partnumbers``); nothing here is typed in by hand.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .colors import DATA_DIR
from .inventory import load_kit_inventory
from .source import DISCLAIMER

PART_NUMBERS_PATH = DATA_DIR / "part_numbers.json"
PARTS = ("6141", "98138")
ROLE_FOR_PART = {"6141": "land", "98138": "ocean"}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class PinnedPage:
    id: str
    title: str
    url: str
    sha256: str
    accessed: str

    def to_dict(self) -> Dict[str, str]:
        return {"id": self.id, "title": self.title, "url": self.url, "sha256": self.sha256,
                "accessed": self.accessed}


@dataclass(frozen=True)
class PartNumbers:
    part_id: str
    name: str
    lego_design_ids: Tuple[str, ...]
    bricklink_item_type: str
    bricklink_item_no: str
    bricklink_alternates: Tuple[str, ...]
    bricklink_colors: Tuple[str, ...]
    rebrickable_part_num: str
    rebrickable_name: str
    citations: Dict[str, PinnedPage]

    def __hash__(self) -> int:
        return hash(self.part_id)


@dataclass(frozen=True)
class PartNumberTable:
    source: Dict[str, Any]
    pages: Tuple[PinnedPage, ...]
    parts: Dict[str, PartNumbers]

    def __hash__(self) -> int:
        return id(self)

    def get(self, part_id: str) -> PartNumbers:
        if part_id not in self.parts:
            raise KeyError(f"part {part_id} is not in part_numbers.json (known: {sorted(self.parts)})")
        return self.parts[part_id]


def _fail(rule: str) -> ValueError:
    return ValueError(f"part_numbers.json: {rule}")


def _str(v: Any) -> bool:
    return isinstance(v, str) and bool(v)


def parse_part_numbers(data: Dict[str, Any]) -> PartNumberTable:
    """Parse and validate (data-model.md PartNumbers rules)."""
    if not isinstance(data, dict) or data.get("format_version") != "1":
        raise _fail("format_version must be '1'")
    source = data.get("source")
    if not isinstance(source, dict) or source.get("disclaimer") != DISCLAIMER:
        raise _fail(f"source.disclaimer must be {DISCLAIMER!r}")
    pages = []
    for i, p in enumerate(source.get("pages") or []):
        if not isinstance(p, dict) or not all(_str(p.get(k)) for k in ("id", "title", "url", "accessed")):
            raise _fail(f"source.pages[{i}]: id, title, url and accessed are required")
        if not isinstance(p.get("sha256"), str) or not _SHA256_RE.match(p["sha256"]):
            raise _fail(f"source.pages[{i}] {p['id']}: sha256 must be 64 lowercase hex characters")
        if not _DATE_RE.match(p["accessed"]):
            raise _fail(f"source.pages[{i}] {p['id']}: accessed must be YYYY-MM-DD")
        pages.append(PinnedPage(p["id"], p["title"], p["url"], p["sha256"], p["accessed"]))
    by_id = {p.id: p for p in pages}
    if len(by_id) != len(pages) or not pages:
        raise _fail("source.pages must be a non-empty list with unique ids")
    raw = data.get("parts")
    if not isinstance(raw, dict) or sorted(raw) != sorted(PARTS):
        raise _fail(f"parts must list exactly {PARTS}")
    inv = load_kit_inventory()
    parts: Dict[str, PartNumbers] = {}
    for part_id in PARTS:
        row, where = raw[part_id], f"parts.{part_id}"
        bl, rb = row.get("bricklink") or {}, row.get("rebrickable") or {}
        if not _str(row.get("name")):
            raise _fail(f"{where}: name is required")
        if bl.get("item_type") != "P" or not _str(bl.get("item_no")):
            raise _fail(f"{where}: bricklink item_type 'P' and item_no are required")
        if not _str(rb.get("part_num")):
            raise _fail(f"{where}: rebrickable part_num is required")
        if rb["part_num"] != part_id:
            raise _fail(f"{where}: rebrickable part_num must be {part_id}")
        alternates = tuple(bl.get("alternates") or ())
        if part_id != bl["item_no"] and part_id not in alternates:
            raise _fail(f"{where}: {part_id} must be the BrickLink item number or an alternate")
        colors = tuple(bl.get("colors") or ())
        if not colors or not all(_str(c) for c in colors):
            raise _fail(f"{where}: bricklink colors must be a non-empty list of names")
        designs = tuple(row.get("lego_design_ids") or ())
        if not designs or part_id not in designs:
            raise _fail(f"{where}: lego_design_ids must include {part_id}")
        cits = {}
        for cat, entry in (("bricklink", bl), ("rebrickable", rb)):
            if entry.get("citation") not in by_id:
                raise _fail(f"{where}: {cat} citation {entry.get('citation')!r} does not resolve to source.pages")
            cits[cat] = by_id[entry["citation"]]
        kit_elements = inv.by_role(ROLE_FOR_PART[part_id])
        if any(bl["item_no"] not in e.part_ids for e in kit_elements):
            raise _fail(f"{where}: BrickLink {bl['item_no']} disagrees with the kit inventory's part_ids")
        parts[part_id] = PartNumbers(
            part_id=part_id, name=row["name"], lego_design_ids=designs, bricklink_item_type="P",
            bricklink_item_no=bl["item_no"], bricklink_alternates=alternates, bricklink_colors=colors,
            rebrickable_part_num=rb["part_num"], rebrickable_name=str(rb.get("name") or ""),
            citations=cits)
    return PartNumberTable(source=dict(source), pages=tuple(pages), parts=parts)


@lru_cache(maxsize=None)
def _load(path: Path) -> PartNumberTable:
    with open(path, "r", encoding="utf-8") as f:
        return parse_part_numbers(json.load(f))


def load_part_numbers(path: Optional[Path] = None) -> PartNumberTable:
    """The shipped part-number table (package data; no network)."""
    return _load(Path(path) if path else PART_NUMBERS_PATH)

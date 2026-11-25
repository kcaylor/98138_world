"""Kit 31203 parts inventory (instructions page 159), shipped as package data.

Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from .colors import DATA_DIR, load_kit_color_table
from .source import SourceDocument

INVENTORY_PATH = DATA_DIR / "kit_31203_inventory.json"
SUPPORTED_KIT = "31203"
ROLES = ("land", "ocean", "section_base", "frame_other")
EXPECTED_LINES = 32
EXPECTED_PIECES = 11694
INVENTORY_PAGE = 159
MAP_ROLE_FOR_PART = {"6141": "land", "98138": "ocean"}


class UnsupportedKitError(ValueError):
    """Raised for any kit other than 31203."""

    def __init__(self, kit_id: str):
        super().__init__(
            f"Kit ID '{kit_id}' not supported. "
            f"Currently only '{SUPPORTED_KIT}' (LEGO World Map) is supported."
        )


def check_kit_id(kit_id: str) -> None:
    if str(kit_id) != SUPPORTED_KIT:
        raise UnsupportedKitError(kit_id)


@dataclass(frozen=True)
class KitElement:
    element_id: str
    quantity: int
    source_page: int
    design_id: Optional[str]
    part_ids: List[str]
    description: str
    color: str
    color_key: Optional[str]
    role: str
    metadata_verified: bool
    citation: str


@dataclass(frozen=True)
class KitInventory:
    kit_id: str
    source: SourceDocument
    elements: List[KitElement]
    totals: Dict[str, int]

    def by_role(self, role: str) -> List[KitElement]:
        return [e for e in self.elements if e.role == role]

    def land_element(self) -> KitElement:
        return self.by_role("land")[0]

    def ocean_elements(self) -> List[KitElement]:
        return self.by_role("ocean")

    def supplied(self, color_key: str) -> int:
        """All elements with ``color_key``, whatever their part (kept for existing callers)."""
        return sum(e.quantity for e in self.elements if e.color_key == color_key)

    def supplied_for(self, part_id: str, color_key: str) -> int:
        """Pieces of ``part_id`` (6141 plate, 98138 tile) in ``color_key`` that one kit supplies.

        Only map elements whose role matches the part count: a Bright Green *plate* gets 0 even
        though the kit has 601 Bright Green *tiles* (feature 005 research R11). Any other part,
        such as the 1x1 square tile 3070b of a template's margin (feature 016), is 0: the kit has
        none, so a one-kit top-up buys every one.
        """
        role = MAP_ROLE_FOR_PART.get(str(part_id))
        if role is None:
            return 0
        return sum(e.quantity for e in self.elements
                   if e.role == role and e.color_key == color_key and str(part_id) in e.part_ids)


def _fail(filename: str, rule: str) -> ValueError:
    return ValueError(f"{filename}: {rule}")


def parse_inventory(data: Dict[str, Any], filename: str = "kit_31203_inventory.json") -> KitInventory:
    """Parse and validate an inventory document (data-model.md KitElement rules)."""
    if data.get("kit_id") != SUPPORTED_KIT:
        raise _fail(filename, f"kit_id must be '{SUPPORTED_KIT}'")
    try:
        source = SourceDocument.from_dict(data.get("source"))
    except ValueError as exc:
        raise _fail(filename, str(exc)) from exc
    elements: List[KitElement] = []
    for i, row in enumerate(data.get("elements") or []):
        eid = row.get("element_id")
        where = f"elements[{i}] ({eid})"
        qty = row.get("quantity")
        if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            raise _fail(filename, f"{where}: quantity must be a positive integer")
        if row.get("source_page") != INVENTORY_PAGE:
            raise _fail(filename, f"{where}: source_page must be {INVENTORY_PAGE}")
        if row.get("role") not in ROLES:
            raise _fail(filename, f"{where}: role must be one of {ROLES}")
        try:
            source.citation(row.get("citation"))
        except KeyError:
            raise _fail(filename, f"{where}: citation '{row.get('citation')}' does not resolve")
        part_ids = row.get("part_ids")
        if not isinstance(part_ids, list) or not part_ids:
            raise _fail(filename, f"{where}: part_ids must be a non-empty list")
        elements.append(KitElement(
            element_id=str(eid), quantity=qty, source_page=row["source_page"],
            design_id=row.get("design_id"), part_ids=list(part_ids),
            description=row.get("description") or "", color=row.get("color") or "",
            color_key=row.get("color_key"), role=row["role"],
            metadata_verified=bool(row.get("metadata_verified")), citation=row["citation"],
        ))
    ids = [e.element_id for e in elements]
    if len(set(ids)) != len(ids):
        raise _fail(filename, "element_id values must be unique")
    pieces = sum(e.quantity for e in elements)
    if len(elements) != EXPECTED_LINES or pieces != EXPECTED_PIECES:
        raise _fail(filename, f"expected {EXPECTED_LINES} lines and {EXPECTED_PIECES} pieces, "
                              f"found {len(elements)} lines and {pieces} pieces")
    totals = data.get("totals") or {}
    if totals != {"lines": len(elements), "pieces": pieces}:
        raise _fail(filename, "totals do not match the elements (lines/pieces)")

    land = [e for e in elements if e.role == "land"]
    if len(land) != 1 or land[0].element_id != "614101" or "6141" not in land[0].part_ids \
            or land[0].color != "White" or land[0].quantity != 3064:
        raise _fail(filename, "expected exactly one land element: 614101, part 6141, White, 3064")
    ocean = [e for e in elements if e.role == "ocean"]
    if len(ocean) != 9 or any("98138" not in e.part_ids for e in ocean) \
            or len({e.color_key for e in ocean}) != 9:
        raise _fail(filename, "expected nine ocean elements, all part 98138, in nine distinct colors")
    bases = [e for e in elements if e.role == "section_base"]
    if [(b.element_id, b.quantity) for b in bases] != [("6302092", 40)]:
        raise _fail(filename, "expected one section_base element: 6302092 x40")

    table = load_kit_color_table()
    for e in land + ocean:
        if not e.metadata_verified:
            raise _fail(filename, f"{e.element_id}: map element metadata must be verified")
        try:
            kc = table.by_key(e.color_key)
        except KeyError:
            raise _fail(filename, f"{e.element_id}: color_key '{e.color_key}' is not a kit color")
        if kc.lego.name != e.color or kc.element_id != e.element_id or kc.role != e.role:
            raise _fail(filename, f"{e.element_id}: color/role disagree with kit_colors.json ({kc.key})")
    for e in elements:
        if e.role not in ("land", "ocean") and e.color_key is not None:
            raise _fail(filename, f"{e.element_id}: only map elements have a color_key")
    return KitInventory(kit_id=SUPPORTED_KIT, source=source, elements=elements,
                        totals={"lines": len(elements), "pieces": pieces})


@lru_cache(maxsize=None)
def _load(path: Path) -> KitInventory:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return parse_inventory(data, path.name)


def load_kit_inventory(kit_id: str = SUPPORTED_KIT, path: Optional[Path] = None) -> KitInventory:
    check_kit_id(kit_id)
    return _load(Path(path) if path else INVENTORY_PATH)

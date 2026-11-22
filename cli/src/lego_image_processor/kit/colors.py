"""The kit's 10 map colors with LEGO, BrickLink and Rebrickable names and IDs (cited).

Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .source import Citation, SourceDocument

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
KIT_COLORS_PATH = DATA_DIR / "kit_colors.json"

ROLES = ("land", "ocean")
CATALOGS = ("lego", "bricklink", "rebrickable")
CITATION_FIELDS = ("lego", "bricklink", "rebrickable", "element")
_FORBIDDEN_WORDS = ("estimate", "placeholder", "unverified")


@dataclass(frozen=True)
class CatalogColor:
    name: str
    id: int


@dataclass(frozen=True)
class KitColor:
    key: str
    role: str
    element_id: str
    lego: CatalogColor
    bricklink: CatalogColor
    rebrickable: CatalogColor
    rgb: Tuple[int, int, int]
    citations: Dict[str, Citation]
    notes: str = ""


@dataclass(frozen=True)
class KitColorTable:
    source: SourceDocument
    colors: Tuple[KitColor, ...]

    def by_key(self, key: str) -> KitColor:
        for c in self.colors:
            if c.key == key:
                return c
        raise KeyError(key)


def _fail(filename: str, rule: str) -> ValueError:
    return ValueError(f"{filename}: {rule}")


def parse_kit_colors(data: Dict[str, Any], filename: str = "kit_colors.json") -> KitColorTable:
    """Parse and validate the color table (data-model.md KitColor rules)."""
    try:
        source = SourceDocument.from_dict(data.get("source"))
    except ValueError as exc:
        raise _fail(filename, str(exc)) from exc
    rows = data.get("colors")
    if not isinstance(rows, list) or len(rows) != 10:
        raise _fail(filename, f"expected exactly 10 colors, found {len(rows) if isinstance(rows, list) else 0}")
    colors: List[KitColor] = []
    for i, row in enumerate(rows):
        where = f"colors[{i}]"
        key = row.get("key")
        if not isinstance(key, str) or not key.startswith("lego_"):
            raise _fail(filename, f"{where}: key must start with 'lego_'")
        role = row.get("role")
        if role not in ROLES:
            raise _fail(filename, f"{key}: role must be one of {ROLES}")
        cats = {}
        for cat in CATALOGS:
            entry = row.get(cat) or {}
            name, cid = entry.get("name"), entry.get("id")
            if not isinstance(name, str) or not name or not isinstance(cid, int) or isinstance(cid, bool):
                raise _fail(filename, f"{key}: {cat} name and id are required (non-null)")
            cats[cat] = CatalogColor(name=name, id=cid)
        cits = row.get("citations") or {}
        resolved = {}
        for field in CITATION_FIELDS:
            cid = cits.get(field)
            try:
                resolved[field] = source.citation(cid)
            except KeyError:
                raise _fail(filename, f"{key}: citation '{cid}' for {field} does not resolve to source.citations")
        rgb = row.get("rgb")
        if not (isinstance(rgb, list) and len(rgb) == 3 and all(isinstance(v, int) and 0 <= v <= 255 for v in rgb)):
            raise _fail(filename, f"{key}: rgb must be three integers 0-255")
        element_id = row.get("element_id")
        if not isinstance(element_id, str) or not element_id:
            raise _fail(filename, f"{key}: element_id is required")
        notes = row.get("notes", "")
        if any(w in str(notes).lower() for w in _FORBIDDEN_WORDS):
            raise _fail(filename, f"{key}: entry marked as estimate/placeholder")
        colors.append(KitColor(key=key, role=role, element_id=element_id, lego=cats["lego"],
                               bricklink=cats["bricklink"], rebrickable=cats["rebrickable"],
                               rgb=tuple(rgb), citations=resolved, notes=notes))
    keys = [c.key for c in colors]
    if len(set(keys)) != len(keys):
        raise _fail(filename, "color keys must be unique")
    roles = [c.role for c in colors]
    if roles.count("land") != 1 or roles.count("ocean") != 9:
        raise _fail(filename, "expected exactly 1 land and 9 ocean colors")
    if len({c.lego.id for c in colors}) != len(colors):
        raise _fail(filename, "lego.id values must be unique")
    if len({c.element_id for c in colors}) != len(colors):
        raise _fail(filename, "element_id values must be unique")
    return KitColorTable(source=source, colors=tuple(colors))


@lru_cache(maxsize=None)
def load_kit_color_table(path: Optional[Path] = None) -> KitColorTable:
    path = Path(path) if path else KIT_COLORS_PATH
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return parse_kit_colors(data, path.name)


def load_kit_colors() -> List[KitColor]:
    """The 10 kit colors: land first, then ocean by descending kit quantity."""
    return list(load_kit_color_table().colors)

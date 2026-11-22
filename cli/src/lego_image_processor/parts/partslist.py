"""Parts list for a layout (feature 005 US1, US3): lots, cited IDs and top-up arithmetic.

A lot is one part in one color. For each lot: needed (positions in the layout), owned (whole kits
from the cited inventory, minus missing pieces, plus loose parts), shortfall, spares (only on
request), to buy and surplus. Map pieces only (Q6): the frame, section bases and other kit parts
are not listed. No prices are estimated (FR-018).
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ..kit.inventory import load_kit_inventory
from ..kit.part_colors import load_part_colors
from ..kit.part_numbers import load_part_numbers
from ..kit.source import DISCLAIMER
from ..layout.grid import CURRENT_SCHEMA_VERSION, LayoutSchemaError, PositionPlacementGrid
from .owned import OwnedInputs, percent_text
from .resolve import ResolvedColor, Unresolved, resolve_color

FORMAT_VERSION = "1"
GRID_WIDTH, GRID_HEIGHT = 128, 80
PART_ORDER = {"6141": 0, "98138": 1}
PART_TYPE = {"6141": "plate", "98138": "tile"}
ACKNOWLEDGEMENT = ("Catalog data: Rebrickable (rebrickable.com), BrickLink, LDraw, Brickset; kit "
                   "inventory from the LEGO 31203 building instructions.")
PRICE_NOTE = ("Prices: none are estimated. Upload the list to BrickLink or Rebrickable to price it; "
              "both price an imported list.")


class LayoutInputError(ValueError):
    """The layout file cannot be used (exit 1)."""


@dataclass(frozen=True)
class LayoutInput:
    path: str
    sha256: str
    grid: PositionPlacementGrid


def read_layout(path: Union[str, Path]) -> LayoutInput:
    """Read a schema 2.0 layout on the 128x80 kit grid; record the SHA-256 of the file's bytes."""
    p = Path(path)
    try:
        raw = p.read_bytes()
    except OSError as exc:
        raise LayoutInputError(f"cannot read layout {path}: {exc.strerror or exc}")
    try:
        grid = PositionPlacementGrid.from_json(raw.decode("utf-8"))
    except LayoutSchemaError as exc:
        raise LayoutInputError(f"{path}: {exc}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LayoutInputError(f"{path}: not a JSON layout file ({exc})")
    except (KeyError, TypeError, ValueError) as exc:
        raise LayoutInputError(f"{path}: not a valid layout ({exc.__class__.__name__}: {exc})")
    check_grid(grid, str(path))
    return LayoutInput(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), grid=grid)


def check_grid(grid: PositionPlacementGrid, where: str = "layout") -> None:
    if grid.schema_version != CURRENT_SCHEMA_VERSION:
        raise LayoutInputError(f"{where}: schema version {grid.schema_version} is not {CURRENT_SCHEMA_VERSION}")
    if (grid.width, grid.height) != (GRID_WIDTH, GRID_HEIGHT):
        raise LayoutInputError(f"{where}: grid is {grid.width}x{grid.height}, expected "
                               f"{GRID_WIDTH}x{GRID_HEIGHT} (kit 31203)")
    seen = set()
    for pos in grid.positions:
        if not (0 <= pos.x < GRID_WIDTH and 0 <= pos.y < GRID_HEIGHT):
            raise LayoutInputError(f"{where}: position ({pos.x}, {pos.y}) is outside the "
                                   f"{GRID_WIDTH}x{GRID_HEIGHT} grid")
        if (pos.x, pos.y) in seen:
            raise LayoutInputError(f"{where}: position ({pos.x}, {pos.y}) appears twice")
        seen.add((pos.x, pos.y))
    if not seen:
        raise LayoutInputError(f"{where}: layout has no positions")


@dataclass(frozen=True)
class Lot:
    part_id: str
    color_key: str
    layout_color_name: str
    layout_color_code: str
    ids: Optional[ResolvedColor]
    reason: Optional[str]
    needed: int
    kit_supply: int = 0
    loose: int = 0
    spares: int = 0

    @property
    def part_type(self) -> str:
        return PART_TYPE[self.part_id]

    @property
    def verified(self) -> bool:
        return self.ids is not None

    @property
    def owned(self) -> int:
        return self.kit_supply + self.loose

    @property
    def shortfall(self) -> int:
        return max(0, self.needed - self.owned)

    @property
    def to_buy(self) -> int:
        return self.shortfall + self.spares

    @property
    def surplus(self) -> int:
        return max(0, self.owned - self.needed)

    @property
    def display_name(self) -> str:
        return self.ids.lego_name if self.ids else self.layout_color_name

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"part_id": self.part_id, "part_type": self.part_type,
                             "color_key": self.color_key, "verified": self.verified}
        if self.ids is None:
            d["reason"] = self.reason
            d["layout_color"] = {"name": self.layout_color_name, "code": self.layout_color_code}
        else:
            r = self.ids
            d["lego"] = {"name": r.lego_name, "id": r.lego_id, "element_id": r.element_id}
            d["bricklink"] = {"item_type": r.bricklink_item_type, "item_no": r.bricklink_item_no,
                              "color_name": r.bricklink_color_name, "color_id": r.bricklink_color_id}
            d["rebrickable"] = {"part_num": r.rebrickable_part_num,
                                "color_name": r.rebrickable_color_name, "color_id": r.rebrickable_color_id}
            d["rgb"] = list(r.rgb)
        d.update(needed=self.needed, kit_supply=self.kit_supply, loose=self.loose, owned=self.owned,
                 shortfall=self.shortfall, spares=self.spares, to_buy=self.to_buy, surplus=self.surplus)
        return d


@dataclass(frozen=True)
class PartsList:
    layout: Dict[str, Any]
    owned: OwnedInputs
    lots: Tuple[Lot, ...]
    citations: Tuple[Dict[str, Any], ...]
    kit_id: str = "31203"

    @property
    def verified_lots(self) -> Tuple[Lot, ...]:
        return tuple(l for l in self.lots if l.verified)

    @property
    def unverified_lots(self) -> Tuple[Lot, ...]:
        return tuple(l for l in self.lots if not l.verified)

    @property
    def lots_to_buy(self) -> Tuple[Lot, ...]:
        return tuple(l for l in self.lots if l.to_buy > 0)

    def totals(self) -> Dict[str, int]:
        lots = self.lots
        return {
            "lots": len(lots),
            "needed": sum(l.needed for l in lots),
            "owned": sum(l.owned for l in lots),
            "to_buy": sum(l.to_buy for l in lots),
            "lots_to_buy": len(self.lots_to_buy),
            "spares": sum(l.spares for l in lots),
            "surplus": sum(l.surplus for l in lots),
            "verified_lots": len(self.verified_lots),
            "unverified_lots": len(self.unverified_lots),
        }

    def to_dict(self) -> Dict[str, Any]:
        o = self.owned
        return {
            "format_version": FORMAT_VERSION,
            "kit": self.kit_id,
            "layout": self.layout,
            "owned": {"kits": o.kits,
                      "owned_files": [{"path": f.path, "sha256": f.sha256} for f in o.owned_files],
                      "missing_files": [{"path": f.path, "sha256": f.sha256} for f in o.missing_files],
                      "ignored_rows": o.ignored_rows,
                      "spares_percent": percent_text(o.spares_percent)},
            "lots": [l.to_dict() for l in self.lots],
            "totals": self.totals(),
            "unverified": [{"part_id": l.part_id, "color_key": l.color_key, "reason": l.reason,
                            "needed": l.needed} for l in self.unverified_lots],
            "citations": list(self.citations),
            "acknowledgement": ACKNOWLEDGEMENT,
            "prices": PRICE_NOTE,
            "disclaimer": DISCLAIMER,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n"


def _map_provenance(meta: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not meta:
        return None
    recipe = meta.get("recipe") or {}
    datasets = []
    for layer in meta.get("layers") or []:
        ds = layer.get("dataset")
        if ds and ds.get("id") not in [d["id"] for d in datasets]:
            datasets.append({k: ds.get(k) for k in ("id", "version", "citation", "license")})
    return {"recipe": {k: recipe.get(k) for k in ("id", "format", "sha256")}, "datasets": datasets}


def _citations(lots: Tuple[Lot, ...]) -> Tuple[Dict[str, Any], ...]:
    inv = load_kit_inventory()
    pc = load_part_colors()
    pn = load_part_numbers()
    out: List[Dict[str, Any]] = [{
        "id": "kit-31203-instructions", "title": inv.source.title, "url": inv.source.url,
        "sha256": inv.source.sha256, "pages": [159], "used_for": "kit supply (parts inventory page)"}]
    seen = {"kit-31203-instructions"}
    color_cits = {c.id: c for c in pc.citations}
    for lot in lots:
        if lot.ids is None:
            continue
        for cid in lot.ids.citation_ids:
            if cid in seen:
                continue
            seen.add(cid)
            page = next((p for p in pn.pages if p.id == cid), None)
            if page is not None:
                out.append(page.to_dict())
            elif cid in color_cits:
                out.append(color_cits[cid].to_dict())
    terms = pc.source.get("terms")
    if terms:
        out.append({"id": "rebrickable-terms", "title": "Rebrickable catalog terms",
                    "url": terms["url"], "sha256": terms["sha256"], "accessed": terms["accessed"],
                    "text": terms["text"]})
    return tuple(out)


def build_parts_list(layout: Union[LayoutInput, PositionPlacementGrid],
                     layout_path: Optional[Union[str, Path]] = None,
                     owned: Optional[OwnedInputs] = None, kit_id: str = "31203",
                     layout_sha256: Optional[str] = None) -> PartsList:
    """Group a layout's positions into lots, resolve them and apply what the maker owns."""
    if isinstance(layout, LayoutInput):
        grid, layout_path, layout_sha256 = layout.grid, layout.path, layout.sha256
    else:
        grid = layout
        check_grid(grid)
        if layout_sha256 is None and layout_path is not None and Path(layout_path).is_file():
            layout_sha256 = hashlib.sha256(Path(layout_path).read_bytes()).hexdigest()
    owned = owned or OwnedInputs()
    inv = load_kit_inventory(kit_id)
    counts: Counter = Counter()
    labels: Dict[Tuple[str, str], Tuple[str, str]] = {}
    codes: Dict[Tuple[str, str], set] = {}
    for pos in grid.positions:
        key = (pos.lego_part_id, pos.color_id)
        counts[key] += 1
        labels.setdefault(key, (pos.color_name, str(pos.lego_color_code)))
        codes.setdefault(key, set()).add(str(pos.lego_color_code))
    p = owned.spares_percent
    lots: List[Lot] = []
    for (part_id, color_key), needed in counts.items():
        name, code = labels[(part_id, color_key)]
        if len(codes[(part_id, color_key)]) > 1:
            res: Union[ResolvedColor, Unresolved] = Unresolved("color code mismatch")
            code = ",".join(sorted(codes[(part_id, color_key)]))
        else:
            res = resolve_color(part_id, color_key, code)
        supply = max(0, owned.kits * inv.supplied_for(part_id, color_key)
                     - owned.missing((part_id, color_key)))
        loose = owned.loose((part_id, color_key))
        shortfall = max(0, needed - supply - loose)
        spares = -((-shortfall * p.numerator) // (100 * p.denominator)) if shortfall else 0
        lots.append(Lot(part_id=part_id, color_key=color_key, layout_color_name=name,
                        layout_color_code=code,
                        ids=res if isinstance(res, ResolvedColor) else None,
                        reason=None if isinstance(res, ResolvedColor) else res.reason,
                        needed=needed, kit_supply=supply, loose=loose, spares=spares))
    lots.sort(key=lambda l: (0, PART_ORDER.get(l.part_id, 9), l.ids.lego_id, l.color_key) if l.verified
              else (1, PART_ORDER.get(l.part_id, 9), 0, l.color_key))
    lots_t = tuple(lots)
    layout_block = {
        "path": None if layout_path is None else str(layout_path),
        "sha256": layout_sha256,
        "schema_version": grid.schema_version,
        "source_image": grid.source_image,
        "positions": grid.total_positions,
        "map": _map_provenance(grid.map_metadata),
    }
    return PartsList(layout=layout_block, owned=owned, lots=lots_t, citations=_citations(lots_t),
                     kit_id=kit_id)

"""The BrickLink price snapshot: model, validation on load, deterministic writing (feature 011).

``bricklink_price_guide.json`` (contracts/price-snapshot-format.md §1) holds per-lot price-guide
aggregates with the retrieval times and query parameters. Every key is allow-listed, so no
credential, header or signature can be carried in; prices are exact ``Decimal`` values written
as strings; each lot's BrickLink IDs must equal the cited tables. No network.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from . import wording
from .lots import LotRef, lot_ref_by_lego_id
from .wording import ATTRIBUTION, DISCLAIMER, ESTIMATE_NOTE

FORMAT_VERSION = "1"
LOT_SET_KINDS = ("recipes", "all-cited", "named")
ERROR_NOT_FOUND = "not found"
_PRICE_RE = re.compile(r"^\d+(\.\d{1,4})?$")
_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")

# Canonical key order of every object (also the allow-list).
TOP_KEYS = ("format_version", "source", "retrieved", "query", "statistic", "lot_set", "complete",
            "lots", "attribution", "estimate_note", "disclaimer")
SOURCE_KEYS = ("title", "publisher", "url", "api", "tool", "disclaimer")
API_KEYS = ("base_url", "endpoint", "documentation", "checked")
DOC_KEYS = ("id", "title", "url")
TOOL_KEYS = ("name", "version", "command")
RETRIEVED_KEYS = ("started_at", "finished_at")
QUERY_KEYS = ("new_or_used", "currency_code", "vat", "country_code", "region", "guide_types")
GUIDE_TYPE_KEYS = ("sold", "stock")
STATISTIC_KEYS = ("average", "low", "high", "also_recorded", "fallback")
LOT_SET_KEYS = ("kind", "recipes", "count")
RECIPE_KEYS = ("id", "sha256")
LOT_KEYS = ("part_id", "lego_color_id", "color_key", "lego_color_name", "bricklink", "retrieved_at",
            "sold", "stock", "error")
BRICKLINK_KEYS = ("item_type", "item_no", "color_id", "color_name")
FIGURE_KEYS = ("qty_avg_price", "avg_price", "min_price", "max_price", "unit_quantity",
               "total_quantity")
PRICE_KEYS = ("qty_avg_price", "avg_price", "min_price", "max_price")

QUERY = {"new_or_used": "N", "currency_code": "USD", "vat": "N", "country_code": None, "region": None}
STATISTIC = {"average": "qty_avg_price", "low": "min_price", "high": "max_price",
             "also_recorded": ["avg_price"]}
# Fixed texts a fetched snapshot records (contracts/price-snapshot-format.md §1).
GUIDE_TYPE_TEXT = {"sold": "sales in the last 6 months (BrickLink's fixed period)",
                   "stock": "items for sale at retrieval time"}
FALLBACK_TEXT = "stock when sold has no data; unpriced when neither has data"


class SnapshotError(ValueError):
    """The price snapshot cannot be used (missing, unreadable or invalid); exit 1 in the CLI."""


class SnapshotMissingError(SnapshotError):
    """No snapshot is packaged yet (the owner has not run ``parts prices fetch``)."""


@dataclass(frozen=True)
class GuideFigures:
    """One lot, one guide type (sold or stock). Money is exact."""

    qty_avg_price: Decimal
    avg_price: Decimal
    min_price: Decimal
    max_price: Decimal
    unit_quantity: int
    total_quantity: int

    def to_dict(self) -> Dict[str, Any]:
        return {"qty_avg_price": money_text(self.qty_avg_price), "avg_price": money_text(self.avg_price),
                "min_price": money_text(self.min_price), "max_price": money_text(self.max_price),
                "unit_quantity": self.unit_quantity, "total_quantity": self.total_quantity}


@dataclass(frozen=True)
class SnapshotLot:
    lot: LotRef
    sold: Optional[GuideFigures]
    stock: Optional[GuideFigures]
    retrieved_at: str
    error: Optional[str] = None

    @property
    def basis(self) -> str:
        return "sold" if self.sold else "stock" if self.stock else "unpriced"

    @property
    def figures(self) -> Optional[GuideFigures]:
        """The figures that price this lot (sold, else stock), or None."""
        return self.sold or self.stock

    def to_dict(self) -> Dict[str, Any]:
        l = self.lot
        return {"part_id": l.part_id, "lego_color_id": l.lego_color_id, "color_key": l.color_key,
                "lego_color_name": l.lego_color_name,
                "bricklink": {"item_type": l.bricklink_item_type, "item_no": l.bricklink_item_no,
                              "color_id": l.bricklink_color_id, "color_name": l.bricklink_color_name},
                "retrieved_at": self.retrieved_at,
                "sold": None if self.sold is None else self.sold.to_dict(),
                "stock": None if self.stock is None else self.stock.to_dict(),
                "error": self.error}


@dataclass(frozen=True)
class PriceSnapshot:
    source: Dict[str, Any]
    retrieved: Dict[str, str]
    query: Dict[str, Any]
    statistic: Dict[str, Any]
    lot_set: Dict[str, Any]
    complete: bool
    lots: Tuple[SnapshotLot, ...]
    format_version: str = FORMAT_VERSION
    attribution: str = ATTRIBUTION
    estimate_note: str = ESTIMATE_NOTE
    disclaimer: str = DISCLAIMER
    # Where it was loaded from (not part of the file).
    sha256: Optional[str] = None
    file_name: Optional[str] = None
    path: Optional[str] = None
    packaged: bool = False
    _index: Dict[Tuple[str, int], SnapshotLot] = field(default_factory=dict, compare=False, repr=False)

    def __post_init__(self) -> None:
        self._index.update({l.lot.key: l for l in self.lots})

    def lot_for(self, part_id: str, lego_color_id: int) -> Optional[SnapshotLot]:
        return self._index.get((str(part_id), int(lego_color_id)))

    @property
    def finished_at(self) -> str:
        return self.retrieved["finished_at"]

    @property
    def retrieved_on(self) -> str:
        return self.finished_at[:10]

    def to_dict(self) -> Dict[str, Any]:
        return {"format_version": self.format_version, "source": self.source,
                "retrieved": self.retrieved, "query": self.query, "statistic": self.statistic,
                "lot_set": self.lot_set, "complete": self.complete,
                "lots": [l.to_dict() for l in self.lots], "attribution": self.attribution,
                "estimate_note": self.estimate_note, "disclaimer": self.disclaimer}


def money_text(d: Decimal) -> str:
    return format(d, "f")


def snapshot_to_json(snapshot: PriceSnapshot) -> str:
    """Canonical bytes: fixed key order, sorted lots, indent 2, trailing newline (FR-004)."""
    return json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False) + "\n"


# --- validation ---------------------------------------------------------------------------------

class _Invalid(Exception):
    def __init__(self, where: str, rule: str):
        super().__init__(f"{where}: {rule}")
        self.where, self.rule = where, rule


def _obj(v: Any, where: str, keys: Tuple[str, ...]) -> Dict[str, Any]:
    """Check an object has exactly ``keys`` and return it in canonical order."""
    if not isinstance(v, dict):
        raise _Invalid(where or "(top level)", "must be an object")
    for k in v:
        if k not in keys:
            raise _Invalid(f"{where}.{k}" if where else k, f"unknown key (allowed: {', '.join(keys)})")
    for k in keys:
        if k not in v:
            raise _Invalid(f"{where}.{k}" if where else k, "is required")
    return {k: v[k] for k in keys}


def _text(v: Any, where: str) -> str:
    if not isinstance(v, str) or not v:
        raise _Invalid(where, "must be a non-empty string")
    return v


def _equal(v: Any, expected: Any, where: str) -> Any:
    if v != expected:
        raise _Invalid(where, f"must be {expected!r}")
    return v


def _int(v: Any, where: str, minimum: int) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or v < minimum:
        raise _Invalid(where, f"must be an integer >= {minimum}")
    return v


def _time(v: Any, where: str) -> datetime:
    if not isinstance(v, str) or not _TIME_RE.match(v):
        raise _Invalid(where, "must be a UTC time YYYY-MM-DDTHH:MM:SSZ")
    try:
        return datetime.strptime(v, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        raise _Invalid(where, "is not a valid date and time")


def _price(v: Any, where: str) -> Decimal:
    if not isinstance(v, str) or not _PRICE_RE.match(v):
        raise _Invalid(where, "must be a decimal string with up to 4 places (for example \"0.0385\")")
    d = Decimal(v)
    if d <= 0:
        raise _Invalid(where, "must be greater than 0")
    return d


def _figures(v: Any, where: str) -> Optional[GuideFigures]:
    if v is None:
        return None
    o = _obj(v, where, FIGURE_KEYS)
    p = {k: _price(o[k], f"{where}.{k}") for k in PRICE_KEYS}
    units = _int(o["unit_quantity"], f"{where}.unit_quantity", 1)
    total = _int(o["total_quantity"], f"{where}.total_quantity", 1)
    if total < units:
        raise _Invalid(f"{where}.total_quantity", "must be >= unit_quantity")
    if not p["min_price"] <= p["max_price"]:
        raise _Invalid(where, "min_price must be <= max_price")
    for k in ("qty_avg_price", "avg_price"):
        if not p["min_price"] <= p[k] <= p["max_price"]:
            raise _Invalid(where, f"{k} must be between min_price and max_price")
    return GuideFigures(unit_quantity=units, total_quantity=total, **p)


def _source(v: Any) -> Dict[str, Any]:
    s = _obj(v, "source", SOURCE_KEYS)
    for k in ("title", "publisher", "url"):
        _text(s[k], f"source.{k}")
    _equal(s["disclaimer"], DISCLAIMER, "source.disclaimer")
    api = _obj(s["api"], "source.api", API_KEYS)
    for k in ("base_url", "endpoint"):
        _text(api[k], f"source.api.{k}")
    docs = api["documentation"]
    if not isinstance(docs, list) or not docs:
        raise _Invalid("source.api.documentation", "must be a non-empty list")
    api["documentation"] = [_obj(d, f"source.api.documentation[{i}]", DOC_KEYS) for i, d in enumerate(docs)]
    for i, d in enumerate(api["documentation"]):
        for k in DOC_KEYS:
            _text(d[k], f"source.api.documentation[{i}].{k}")
    if not isinstance(api["checked"], bool):
        raise _Invalid("source.api.checked", "must be true or false")
    s["api"] = api
    tool = _obj(s["tool"], "source.tool", TOOL_KEYS)
    for k in TOOL_KEYS:
        _text(tool[k], f"source.tool.{k}")
    s["tool"] = tool
    return s


def _query(v: Any) -> Dict[str, Any]:
    q = _obj(v, "query", QUERY_KEYS)
    for k, expected in QUERY.items():
        _equal(q[k], expected, f"query.{k}")
    gt = _obj(q["guide_types"], "query.guide_types", GUIDE_TYPE_KEYS)
    for k in GUIDE_TYPE_KEYS:
        _text(gt[k], f"query.guide_types.{k}")
    q["guide_types"] = gt
    return q


def _statistic(v: Any) -> Dict[str, Any]:
    s = _obj(v, "statistic", STATISTIC_KEYS)
    for k, expected in STATISTIC.items():
        _equal(s[k], expected, f"statistic.{k}")
    _text(s["fallback"], "statistic.fallback")
    return s


def _lot_set(v: Any) -> Dict[str, Any]:
    ls = _obj(v, "lot_set", LOT_SET_KEYS)
    if ls["kind"] not in LOT_SET_KINDS:
        raise _Invalid("lot_set.kind", f"must be one of {', '.join(LOT_SET_KINDS)}")
    if not isinstance(ls["recipes"], list):
        raise _Invalid("lot_set.recipes", "must be a list")
    recipes = []
    for i, r in enumerate(ls["recipes"]):
        r = _obj(r, f"lot_set.recipes[{i}]", RECIPE_KEYS)
        _text(r["id"], f"lot_set.recipes[{i}].id")
        if not isinstance(r["sha256"], str) or not _SHA_RE.match(r["sha256"]):
            raise _Invalid(f"lot_set.recipes[{i}].sha256", "must be 64 lowercase hex characters")
        recipes.append(r)
    if ls["kind"] == "recipes" and not recipes:
        raise _Invalid("lot_set.recipes", "must list the recipes for kind 'recipes'")
    ls["recipes"] = recipes
    _int(ls["count"], "lot_set.count", 0)
    return ls


def _lot(v: Any, where: str, started: datetime, finished: datetime) -> SnapshotLot:
    o = _obj(v, where, LOT_KEYS)
    part_id = o["part_id"]
    if part_id not in ("6141", "98138"):
        raise _Invalid(f"{where}.part_id", "must be '6141' or '98138'")
    lego_id = _int(o["lego_color_id"], f"{where}.lego_color_id", 0)
    ref = lot_ref_by_lego_id(part_id, lego_id)
    if ref is None:
        raise _Invalid(f"{where}.lego_color_id", f"no cited color with LEGO ID {lego_id} for part {part_id}")
    _equal(o["color_key"], ref.color_key, f"{where}.color_key")
    _equal(o["lego_color_name"], ref.lego_color_name, f"{where}.lego_color_name")
    bl = _obj(o["bricklink"], f"{where}.bricklink", BRICKLINK_KEYS)
    expected = {"item_type": ref.bricklink_item_type, "item_no": ref.bricklink_item_no,
                "color_id": ref.bricklink_color_id, "color_name": ref.bricklink_color_name}
    for k in BRICKLINK_KEYS:
        if bl[k] != expected[k]:
            raise _Invalid(f"{where}.bricklink.{k}", f"must be {expected[k]!r} (the cited tables), "
                                                     f"found {bl[k]!r}")
    t = _time(o["retrieved_at"], f"{where}.retrieved_at")
    if not started <= t <= finished:
        raise _Invalid(f"{where}.retrieved_at", "must be between retrieved.started_at and finished_at")
    sold = _figures(o["sold"], f"{where}.sold")
    stock = _figures(o["stock"], f"{where}.stock")
    err = o["error"]
    if err not in (None, ERROR_NOT_FOUND):
        raise _Invalid(f"{where}.error", f"must be null or {ERROR_NOT_FOUND!r}")
    if err == ERROR_NOT_FOUND and (sold is not None or stock is not None):
        raise _Invalid(where, "a lot with error 'not found' must have sold and stock null")
    return SnapshotLot(lot=ref, sold=sold, stock=stock, retrieved_at=o["retrieved_at"], error=err)


def _parse(data: Any) -> PriceSnapshot:
    if isinstance(data, dict) and data.get("format_version") != FORMAT_VERSION:
        raise _Invalid("format_version", f"must be {FORMAT_VERSION!r} (this tool reads format "
                                         f"{FORMAT_VERSION}), found {data.get('format_version')!r}")
    d = _obj(data, "", TOP_KEYS)
    for k, expected in (("attribution", ATTRIBUTION), ("estimate_note", ESTIMATE_NOTE),
                        ("disclaimer", DISCLAIMER)):
        _equal(d[k], expected, k)
    source = _source(d["source"])
    retrieved = _obj(d["retrieved"], "retrieved", RETRIEVED_KEYS)
    started = _time(retrieved["started_at"], "retrieved.started_at")
    finished = _time(retrieved["finished_at"], "retrieved.finished_at")
    if finished < started:
        raise _Invalid("retrieved", "finished_at must not be before started_at")
    query = _query(d["query"])
    statistic = _statistic(d["statistic"])
    lot_set = _lot_set(d["lot_set"])
    if not isinstance(d["complete"], bool):
        raise _Invalid("complete", "must be true or false")
    raw_lots = d["lots"]
    if not isinstance(raw_lots, list):
        raise _Invalid("lots", "must be a list")
    lots: List[SnapshotLot] = []
    for i, raw in enumerate(raw_lots):
        lot = _lot(raw, f"lots[{i}]", started, finished)
        if lots and lot.lot.sort_key <= lots[-1].lot.sort_key:
            rule = "duplicate lot" if lot.lot.key == lots[-1].lot.key else "out of order"
            raise _Invalid(f"lots[{i}]", f"{rule}: lots must be sorted by part (6141, 98138), then "
                                         "LEGO color ID, each once")
        lots.append(lot)
    if d["complete"] != (len(lots) == lot_set["count"]):
        raise _Invalid("complete", f"must be true exactly when lots has lot_set.count entries "
                                   f"({len(lots)} of {lot_set['count']})")
    return PriceSnapshot(source=source, retrieved=retrieved, query=query, statistic=statistic,
                         lot_set=lot_set, complete=d["complete"], lots=tuple(lots))


def parse_figures(data: Any, where: str) -> Optional[GuideFigures]:
    """Validate one guide's figures (the snapshot rules); ``SnapshotError`` names the rule."""
    try:
        return _figures(data, where)
    except _Invalid as exc:
        raise SnapshotError(f"{exc.where}: {exc.rule}") from None


def parse_snapshot_lot(data: Any, where: str, started: str, finished: str) -> SnapshotLot:
    """Validate one lot entry (as saved in a progress file) retrieved in ``[started, finished]``."""
    try:
        return _lot(data, where, _time(started, "started_at"), _time(finished, "finished_at"))
    except _Invalid as exc:
        raise SnapshotError(f"{exc.where}: {exc.rule}") from None


def build_snapshot(*, api_block: Dict[str, Any], tool_version: str, started_at: str, finished_at: str,
                   lot_set: Dict[str, Any], lots: List[SnapshotLot]) -> PriceSnapshot:
    """A fetched snapshot, validated by a round trip through the file rules (FR-004, FR-005)."""
    ordered = sorted(lots, key=lambda l: l.lot.sort_key)
    snap = PriceSnapshot(
        source={"title": wording.SOURCE_TITLE, "publisher": wording.SOURCE_PUBLISHER,
                "url": wording.SOURCE_URL, "api": api_block,
                "tool": {"name": "lego-image-processor", "version": tool_version,
                         "command": "parts prices fetch"},
                "disclaimer": DISCLAIMER},
        retrieved={"started_at": started_at, "finished_at": finished_at},
        query={**QUERY, "guide_types": dict(GUIDE_TYPE_TEXT)},
        statistic={**STATISTIC, "also_recorded": list(STATISTIC["also_recorded"]),
                   "fallback": FALLBACK_TEXT},
        lot_set=dict(lot_set), complete=len(ordered) == lot_set["count"], lots=tuple(ordered))
    return parse_snapshot(json.loads(snapshot_to_json(snap)), name="fetched price snapshot")


def parse_snapshot(data: Any, *, name: str = "price snapshot") -> PriceSnapshot:
    """Validate a decoded snapshot (contracts/price-snapshot-format.md §1)."""
    try:
        return _parse(data)
    except _Invalid as exc:
        raise SnapshotError(f"{name}: {exc.where}: {exc.rule}") from None


def load_snapshot(path: Optional[Union[str, Path]] = None) -> PriceSnapshot:
    """Load and validate a snapshot file; default: the packaged ``bricklink_price_guide.json``."""
    packaged = path is None
    p = Path(wording.PACKAGED_SNAPSHOT_PATH) if packaged else Path(path)
    if packaged and not p.is_file():
        raise SnapshotMissingError(wording.MISSING_SNAPSHOT_MESSAGE)
    try:
        raw = p.read_bytes()
    except OSError as exc:
        raise SnapshotError(f"cannot read price snapshot {p}: {exc.strerror or exc}") from None
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"price snapshot {p}: not JSON ({exc})") from None
    snap = parse_snapshot(data, name=f"price snapshot {p.name}")
    object.__setattr__(snap, "sha256", hashlib.sha256(raw).hexdigest())
    object.__setattr__(snap, "file_name", p.name)
    object.__setattr__(snap, "path", None if packaged else str(path))
    object.__setattr__(snap, "packaged", packaged)
    return snap


def largest_changes(old: PriceSnapshot, new: PriceSnapshot,
                    n: int = 5) -> List[Tuple[LotRef, Decimal, Decimal, Decimal]]:
    """Lots priced in both snapshots, by absolute percent change of the unit average."""
    out = []
    for lot in new.lots:
        prev = old.lot_for(*lot.lot.key)
        if prev is None or prev.figures is None or lot.figures is None:
            continue
        a, b = prev.figures.qty_avg_price, lot.figures.qty_avg_price
        out.append((lot.lot, a, b, (b - a) * 100 / a))
    out.sort(key=lambda c: (-abs(c[3]), c[0].sort_key))
    return out[:n]

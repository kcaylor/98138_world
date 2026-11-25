"""Price estimates for a layout from a price snapshot (feature 011 US1; offline).

Two estimates: **full** (every needed piece; feature 005 parts list with no kit) and **one_kit**
(each lot's ``to_buy`` with one 31203 kit, ``OwnedInputs(kits=1)``). Lots come from feature 005's
``build_parts_list``; this module adds no lot logic of its own. Each verified lot is priced from
the snapshot: sold figures, else stock figures (marked), else unpriced with a reason. Money is
exact ``Decimal``: lines are exact, totals are exact sums rounded half-up to cents at the end,
whole dollars half-up to $1 (FR-015). The JSON has no generation time.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ..layout.grid import PositionPlacementGrid
from ..parts import LayoutInput, Lot, OwnedInputs, PartsList, build_parts_list
from ..parts.partslist import PART_TYPE_TEXT, PLAQUE_PART_TYPE
from .snapshot import GuideFigures, PriceSnapshot, money_text
from .wording import (ALL_COLORS_HINT, ATTRIBUTION, BASIS_SENTENCE, DEFAULT_STALE_DAYS, DISCLAIMER, ESTIMATE_NOTE,
                      LABELS, REASON_NO_DATA, REASON_NOT_IN_SNAPSHOT, SOURCE_TITLE, SOURCE_URL,
                      plaque_lot_hint, reason_unverified)

FORMAT_VERSION = "1"
KINDS = ("full", "one_kit")
STATS = ("average", "low", "high")
CENT = Decimal("0.01")
DOLLAR = Decimal("1")
ZERO = Decimal("0")

Triple = Tuple[Decimal, Decimal, Decimal]


def _plural(n: int, word: str) -> str:
    return f"{n:,} {word}" + ("" if n == 1 else "s")


def _money_dict(t: Optional[Triple]) -> Optional[Dict[str, str]]:
    return None if t is None else dict(zip(STATS, (money_text(x) for x in t)))


@dataclass(frozen=True)
class EstimateLine:
    """One lot of one estimate."""

    lot: Lot
    quantity: int
    basis: str                       # sold | stock | unpriced
    reason: Optional[str] = None     # for unpriced
    unit: Optional[Triple] = None    # (average, low, high)
    line: Optional[Triple] = None    # quantity x unit, exact
    figures: Optional[GuideFigures] = None

    @property
    def name(self) -> str:
        return self.lot.display_name

    @property
    def label(self) -> str:
        """``tile Medium Azur (LEGO 322)`` (``square tile Black (LEGO 26)`` for feature 016's 3070b)."""
        kind = PART_TYPE_TEXT[self.lot.part_type]
        if self.lot.ids is None:
            return f"{kind} {self.lot.layout_color_name} (code {self.lot.layout_color_code})"
        return f"{kind} {self.lot.ids.lego_name} (LEGO {self.lot.ids.lego_id})"

    def to_dict(self) -> Dict[str, Any]:
        l = self.lot
        if l.ids is None:
            code = l.layout_color_code
            lego = {"name": l.layout_color_name, "id": int(code) if code.isdigit() else code}
            bricklink = None
        else:
            lego = {"name": l.ids.lego_name, "id": l.ids.lego_id}
            bricklink = {"item_no": l.ids.bricklink_item_no, "color_id": l.ids.bricklink_color_id,
                         "color_name": l.ids.bricklink_color_name}
        f = self.figures
        return {"part_id": l.part_id, "part_type": l.part_type, "color_key": l.color_key,
                "lego": lego, "bricklink": bricklink, "quantity": self.quantity,
                "basis": self.basis, "reason": self.reason,
                "unit": _money_dict(self.unit), "line": _money_dict(self.line),
                "count": None if f is None else {"unit_quantity": f.unit_quantity,
                                                 "total_quantity": f.total_quantity}}


@dataclass(frozen=True)
class Estimate:
    """One of the two estimates (``full`` or ``one_kit``)."""

    kind: str
    owned_kits: int
    lines: Tuple[EstimateLine, ...]

    @property
    def label(self) -> str:
        return LABELS[self.kind]

    @property
    def exact_totals(self) -> Dict[str, Decimal]:
        priced = [l.line for l in self.lines if l.line is not None]
        return {s: sum((t[i] for t in priced), ZERO) for i, s in enumerate(STATS)}

    @property
    def totals(self) -> Dict[str, Decimal]:
        return {s: v.quantize(CENT, rounding=ROUND_HALF_UP) for s, v in self.exact_totals.items()}

    @property
    def whole_dollars(self) -> Dict[str, int]:
        return {s: int(v.quantize(DOLLAR, rounding=ROUND_HALF_UP)) for s, v in self.exact_totals.items()}

    @property
    def pieces(self) -> int:
        return sum(l.quantity for l in self.lines)

    @property
    def lots(self) -> int:
        return len(self.lines)

    @property
    def by_basis(self) -> Dict[str, Dict[str, int]]:
        out = {b: {"lots": 0, "pieces": 0} for b in ("sold", "stock", "unpriced")}
        for l in self.lines:
            out[l.basis]["lots"] += 1
            out[l.basis]["pieces"] += l.quantity
        return out

    @property
    def unpriced_lines(self) -> Tuple[EstimateLine, ...]:
        return tuple(l for l in self.lines if l.basis == "unpriced")

    @property
    def stock_lines(self) -> Tuple[EstimateLine, ...]:
        return tuple(l for l in self.lines if l.basis == "stock")

    @property
    def complete(self) -> bool:
        return not self.unpriced_lines

    @property
    def nothing_to_buy(self) -> bool:
        return not self.lines

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind, "label": self.label, "owned_kits": self.owned_kits,
            "totals": {s: money_text(v) for s, v in self.totals.items()},
            "whole_dollars": self.whole_dollars,
            "pieces": self.pieces, "lots": self.lots, "by_basis": self.by_basis,
            "complete": self.complete, "nothing_to_buy": self.nothing_to_buy,
            "lines": [l.to_dict() for l in self.lines],
            "unpriced": [{"part_id": l.lot.part_id, "part_type": l.lot.part_type,
                          "color_key": l.lot.color_key, "name": l.name, "quantity": l.quantity,
                          "reason": l.reason} for l in self.unpriced_lines],
        }


@dataclass(frozen=True)
class EstimateReport:
    layout: Dict[str, Any]
    snapshot: Dict[str, Any]
    staleness: Dict[str, Any]
    estimates: Dict[str, Estimate]
    notes: Tuple[str, ...]
    kit_id: str = "31203"
    _snapshot_obj: Optional[PriceSnapshot] = field(default=None, compare=False, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {"format_version": FORMAT_VERSION, "kind": "price-estimate", "kit": self.kit_id,
                "layout": self.layout, "snapshot": self.snapshot, "staleness": self.staleness,
                "estimates": {k: self.estimates[k].to_dict() for k in KINDS},
                "notes": list(self.notes), "estimate_note": ESTIMATE_NOTE,
                "attribution": ATTRIBUTION, "disclaimer": DISCLAIMER}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n"

    def manifest_entry(self, kind: str) -> Dict[str, Any]:
        """One estimate as the web manifest's ``variants[C].estimates[kind]`` (contracts/web.md).

        Totals are strings (cents); ``whole_dollars`` are the integers the site shows, so the
        service never rounds money.
        """
        if kind not in KINDS:
            raise ValueError(f"unknown estimate kind {kind!r}; use {', '.join(KINDS)}")
        e = self.estimates[kind]
        b = e.by_basis
        return {"label": e.label, "totals": {s: money_text(v) for s, v in e.totals.items()},
                "whole_dollars": e.whole_dollars, "pieces": e.pieces, "complete": e.complete,
                "nothing_to_buy": e.nothing_to_buy, "unpriced": dict(b["unpriced"]),
                "stock": dict(b["stock"])}

    def prices_block(self) -> Dict[str, Any]:
        """The web manifest's top-level ``prices`` block (contracts/web.md)."""
        s = self.snapshot
        snap = self._snapshot_obj
        lots = len(snap.lots) if snap is not None else None
        return {"snapshot": {"file": s["file"], "sha256": s["sha256"],
                             "retrieved_at": s["retrieved_at"],
                             "retrieved_on": s["retrieved_at"][:10], "complete": s["complete"],
                             "lots": lots},
                "source": dict(s["source"]), "basis": BASIS_SENTENCE,
                "estimate_note": ESTIMATE_NOTE, "attribution": ATTRIBUTION,
                "staleness": dict(self.staleness)}


# --- building -----------------------------------------------------------------------------------

def _price_line(lot: Lot, quantity: int, snapshot: PriceSnapshot) -> EstimateLine:
    if lot.ids is None:
        return EstimateLine(lot, quantity, "unpriced", reason_unverified(lot.reason or "unverified"))
    entry = snapshot.lot_for(lot.part_id, lot.ids.lego_id)
    if entry is None:
        return EstimateLine(lot, quantity, "unpriced", REASON_NOT_IN_SNAPSHOT)
    f = entry.figures
    if f is None:
        return EstimateLine(lot, quantity, "unpriced", REASON_NO_DATA)
    unit = (f.qty_avg_price, f.min_price, f.max_price)
    q = Decimal(quantity)
    return EstimateLine(lot, quantity, entry.basis, None, unit, tuple(q * u for u in unit), f)


def _estimate(kind: str, pl: PartsList, snapshot: PriceSnapshot) -> Estimate:
    qty = (lambda l: l.needed) if kind == "full" else (lambda l: l.to_buy)
    lines = tuple(_price_line(l, qty(l), snapshot) for l in pl.lots if qty(l) > 0)
    return Estimate(kind=kind, owned_kits=pl.owned.kits, lines=lines)


def plaque_specs(lines) -> List[str]:
    """The ``--lot`` specs of the plaque-tile lines among ``lines`` (feature 017), each once."""
    return list(dict.fromkeys(f"{l.lot.part_id}:{l.lot.ids.lego_id}" for l in lines
                              if l.lot.part_type == PLAQUE_PART_TYPE and l.lot.ids is not None))


def _check_lists(full: PartsList, one_kit: PartsList) -> None:
    for name, pl, kits in (("full", full, 0), ("one_kit", one_kit, 1)):
        o = pl.owned
        if o.kits != kits:
            raise ValueError(f"the {name} parts list must have {kits} kit(s), found {o.kits}")
        if o.owned_files or o.missing_files or o.spares_percent:
            raise ValueError(f"the {name} parts list must have no owned or missing files and no spares")
    if full.layout != one_kit.layout:
        raise ValueError("the full and one-kit parts lists come from different layouts (SHA-256 "
                         f"{full.layout.get('sha256')} vs {one_kit.layout.get('sha256')})")


def snapshot_reference(snapshot: PriceSnapshot) -> Dict[str, Any]:
    return {"file": snapshot.file_name, "path": snapshot.path, "packaged": snapshot.packaged,
            "sha256": snapshot.sha256, "retrieved_at": snapshot.finished_at,
            "complete": snapshot.complete,
            "source": {"title": snapshot.source.get("title", SOURCE_TITLE),
                       "url": snapshot.source.get("url", SOURCE_URL)},
            "statistic": {k: snapshot.statistic[k] for k in STATS},
            "query": {k: snapshot.query[k] for k in ("new_or_used", "currency_code", "vat",
                                                    "country_code", "region")}}


def _staleness(snapshot: PriceSnapshot, as_of: date, stale_days: int) -> Dict[str, Any]:
    if isinstance(stale_days, bool) or not isinstance(stale_days, int) or stale_days < 1:
        raise ValueError(f"stale_days must be an integer >= 1, got {stale_days!r}")
    retrieved = date.fromisoformat(snapshot.retrieved_on)
    age = (as_of - retrieved).days
    return {"as_of": as_of.isoformat(), "age_days": age, "threshold_days": stale_days,
            "stale": age > stale_days}


def _notes(snapshot: PriceSnapshot, staleness: Dict[str, Any],
           estimates: Dict[str, Estimate]) -> Tuple[str, ...]:
    notes: List[str] = []
    if staleness["stale"]:
        notes.append(f"Prices are from {snapshot.retrieved_on}, {staleness['age_days']:,} days before "
                     f"{staleness['as_of']}; they may be out of date.")
    if not snapshot.complete:
        notes.append(f"The price snapshot is partial: {len(snapshot.lots)} of "
                     f"{snapshot.lot_set['count']} lots.")
    for k in KINDS:
        e = estimates[k]
        if not e.complete:
            u = e.by_basis["unpriced"]
            notes.append(f"Incomplete: {_plural(u['pieces'], 'piece')} in {_plural(u['lots'], 'color')} "
                         f"could not be priced ({e.label[0].lower() + e.label[1:]}).")
    missing = [l for e in estimates.values() for l in e.lines if l.reason == REASON_NOT_IN_SNAPSHOT]
    if any(l.lot.part_type != PLAQUE_PART_TYPE for l in missing):
        notes.append(f"Fetch every cited color with: {ALL_COLORS_HINT}")
    for spec in plaque_specs(missing):  # feature 017: --all-colors does not cover the plaque tile
        hint = plaque_lot_hint(spec)
        notes.append(f"{hint[0].upper()}{hint[1:]}.")
    stock = estimates["full"].stock_lines
    if stock:
        notes.append("Priced from current for-sale listings (no sales in 6 months): "
                     + ", ".join(l.label for l in stock))
    if estimates["one_kit"].nothing_to_buy:
        notes.append("One kit covers every piece.")
    return tuple(notes)


def estimate_parts_lists(full: PartsList, one_kit: PartsList, snapshot: PriceSnapshot, *,
                         as_of: date, stale_days: int = DEFAULT_STALE_DAYS) -> EstimateReport:
    """Estimate from already built parts lists: ``full`` (no kit) and ``one_kit`` (one kit)."""
    _check_lists(full, one_kit)
    staleness = _staleness(snapshot, as_of, stale_days)
    estimates = {"full": _estimate("full", full, snapshot),
                 "one_kit": _estimate("one_kit", one_kit, snapshot)}
    return EstimateReport(layout=full.layout, snapshot=snapshot_reference(snapshot),
                          staleness=staleness, estimates=estimates,
                          notes=_notes(snapshot, staleness, estimates), kit_id=full.kit_id,
                          _snapshot_obj=snapshot)


def estimate_layout(layout: Union[LayoutInput, PositionPlacementGrid], snapshot: PriceSnapshot, *,
                    as_of: date, stale_days: int = DEFAULT_STALE_DAYS,
                    layout_path: Optional[Union[str, Path]] = None,
                    layout_sha256: Optional[str] = None) -> EstimateReport:
    """Build the full and one-kit parts lists (feature 005) and estimate them."""
    full = build_parts_list(layout, layout_path=layout_path, layout_sha256=layout_sha256)
    one_kit = build_parts_list(layout, layout_path=layout_path, layout_sha256=layout_sha256,
                               owned=OwnedInputs(kits=1))
    return estimate_parts_lists(full, one_kit, snapshot, as_of=as_of, stale_days=stale_days)

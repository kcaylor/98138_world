"""Estimate arithmetic, bases, staleness and JSON (011 T013, T017; FR-012 to FR-017)."""

import ast
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from lego_image_processor.kit import load_official_design
from lego_image_processor.parts import OwnedInputs, build_parts_list, parse_percent
from lego_image_processor.parts.owned import OwnedFile
from lego_image_processor.prices.estimate import (Estimate, EstimateLine, EstimateReport,
                                                  estimate_layout, estimate_parts_lists)
from lego_image_processor.prices.snapshot import load_snapshot, parse_snapshot
from lego_image_processor.prices.wording import (ATTRIBUTION, DISCLAIMER, ESTIMATE_NOTE,
                                                 REASON_NO_DATA, REASON_NOT_IN_SNAPSHOT)

from ..parts.layouts import SMALL, UNCITED, make_grid
from .conftest import FIXTURE_SNAPSHOT, figures, lot_entry, snapshot_dict

AS_OF = date(2026, 12, 5)


def _snap(lots, **kw):
    return parse_snapshot(snapshot_dict(lots, **kw))


def _small_snapshot():
    return _snap([
        lot_entry("6141", "lego_white", sold=figures("0.0385", "0.0100", "0.5000")),
        lot_entry("6141", "lego_brick_yellow", sold=None, stock=figures("0.0500", "0.0200", "1.0000")),
        lot_entry("98138", "lego_bright_red", sold=None, stock=None, error="not found"),
        # Medium Azur: no entry
    ])


def _report(grid, snap, **kw):
    kw.setdefault("as_of", AS_OF)
    return estimate_layout(grid, snap, **kw)


def test_bases_reasons_and_exact_lines():
    r = _report(make_grid(SMALL), _small_snapshot())
    full = r.estimates["full"]
    assert isinstance(full, Estimate) and full.kind == "full" and full.owned_kits == 0
    by_key = {l.lot.color_key: l for l in full.lines}
    assert all(isinstance(l, EstimateLine) for l in full.lines)
    white = by_key["lego_white"]
    assert (white.basis, white.reason, white.quantity) == ("sold", None, 30)
    assert white.unit == (Decimal("0.0385"), Decimal("0.0100"), Decimal("0.5000"))
    assert white.line == (Decimal("1.1550"), Decimal("0.3000"), Decimal("15.0000"))
    yellow = by_key["lego_brick_yellow"]
    assert yellow.basis == "stock" and yellow.line == (Decimal("0.6000"), Decimal("0.2400"), Decimal("12.0000"))
    red = by_key["lego_bright_red"]
    assert (red.basis, red.reason, red.unit, red.line) == ("unpriced", REASON_NO_DATA, None, None)
    azur = by_key["lego_medium_azur"]
    assert (azur.basis, azur.reason) == ("unpriced", REASON_NOT_IN_SNAPSHOT)
    assert full.totals == {"average": Decimal("1.76"), "low": Decimal("0.54"), "high": Decimal("27.00")}
    assert full.whole_dollars == {"average": 2, "low": 1, "high": 27}
    assert full.by_basis == {"sold": {"lots": 1, "pieces": 30}, "stock": {"lots": 1, "pieces": 12},
                             "unpriced": {"lots": 2, "pieces": 27}}
    assert full.complete is False and full.nothing_to_buy is False
    assert full.pieces == 69 == build_parts_list(make_grid(SMALL)).totals()["needed"]


def test_unverified_lot_is_unpriced_with_the_parts_reason():
    r = _report(make_grid(UNCITED), _small_snapshot())
    line = next(l for l in r.estimates["full"].lines if l.lot.color_key == "lego_medium_blue")
    assert line.basis == "unpriced"
    assert line.reason == "no verified BrickLink IDs (no cited color for part)"
    d = next(x for x in r.to_dict()["estimates"]["full"]["lines"] if x["color_key"] == "lego_medium_blue")
    assert d["bricklink"] is None and d["lego"] == {"name": "Medium Blue", "id": 102}
    assert d["unit"] is None and d["line"] is None and d["count"] is None


def test_totals_round_once_at_the_end():
    grid = make_grid([("plate", "lego_white", "White", "1", 1),
                      ("plate", "lego_brick_yellow", "Brick Yellow", "5", 1),
                      ("tile", "lego_medium_azur", "Medium Azur", "322", 1)])
    half = figures("0.0050", "0.0050", "0.0050")
    snap = _snap([lot_entry("6141", "lego_white", sold=half), lot_entry("6141", "lego_brick_yellow", sold=half),
                  lot_entry("98138", "lego_medium_azur", sold=figures("2.4900", "2.4900", "2.4900"))])
    full = _report(grid, snap).estimates["full"]
    # per-line rounding would give 0.01 + 0.01 + 2.49 = 2.51; the exact sum 2.5000 rounds to 2.50
    assert full.totals["average"] == Decimal("2.50")
    assert full.whole_dollars["average"] == 3              # half-up, not half-even
    assert full.complete is True


def test_one_kit_prices_only_to_buy():
    r = _report(make_grid(SMALL), _small_snapshot())
    one = r.estimates["one_kit"]
    assert one.kind == "one_kit" and one.owned_kits == 1
    topup = build_parts_list(make_grid(SMALL), owned=OwnedInputs(kits=1))
    assert {l.lot.color_key: l.quantity for l in one.lines} == \
        {l.color_key: l.to_buy for l in topup.lots if l.to_buy}
    assert one.pieces == topup.totals()["to_buy"] == 19
    assert one.totals["average"] == Decimal("0.60")       # brick yellow from stock; red unpriced


def test_official_layout_one_kit_nothing_to_buy():
    r = _report(load_official_design().to_layout(), load_snapshot(FIXTURE_SNAPSHOT))
    one = r.estimates["one_kit"]
    assert one.nothing_to_buy and one.lines == () and one.complete
    assert one.totals == {"average": Decimal("0.00"), "low": Decimal("0.00"), "high": Decimal("0.00")}
    d = r.to_dict()
    assert d["estimates"]["one_kit"]["totals"] == {"average": "0.00", "low": "0.00", "high": "0.00"}
    assert d["notes"][-1] == "One kit covers every piece."
    full = r.estimates["full"]
    assert full.pieces == 10240 and full.complete and len(full.lines) == 10
    assert full.totals["low"] <= full.totals["average"] <= full.totals["high"]


def test_staleness():
    snap = _small_snapshot()               # finished 2026-12-01
    r = _report(make_grid(SMALL), snap, as_of=date(2027, 3, 1))     # 90 days: not stale
    assert r.staleness == {"as_of": "2027-03-01", "age_days": 90, "threshold_days": 90, "stale": False}
    stale = _report(make_grid(SMALL), snap, as_of=date(2027, 3, 31))
    assert stale.staleness["stale"] is True and stale.staleness["age_days"] == 120
    assert stale.notes[0] == "Prices are from 2026-12-01, 120 days before 2027-03-31; they may be out of date."
    assert stale.estimates["full"].totals == r.estimates["full"].totals
    assert _report(make_grid(SMALL), snap, as_of=date(2027, 3, 1), stale_days=30).staleness["stale"]
    with pytest.raises(ValueError):
        _report(make_grid(SMALL), snap, stale_days=0)


def test_notes_in_contract_order():
    snap = _snap([lot_entry("6141", "lego_white"),
                  lot_entry("6141", "lego_brick_yellow", sold=None, stock=figures("0.0500", "0.0200", "1.0000"))],
                 complete=False, count=4)
    r = _report(make_grid(SMALL), snap, as_of=date(2027, 6, 1))
    notes = r.notes
    assert notes[0].startswith("Prices are from 2026-12-01")
    assert notes[1] == "The price snapshot is partial: 2 of 4 lots."
    assert notes[2] == "Incomplete: 27 pieces in 2 colors could not be priced (every piece)."
    assert notes[3] == "Incomplete: 7 pieces in 1 color could not be priced (on top of one 31203 kit)."
    assert notes[4] == ("Fetch every cited color with: lego-image-processor parts prices fetch "
                        "--all-colors")
    assert notes[5] == ("Priced from current for-sale listings (no sales in 6 months): "
                        "plate Brick Yellow (LEGO 5)")
    assert len(notes) == 6


def _lists(grid):
    return build_parts_list(grid), build_parts_list(grid, owned=OwnedInputs(kits=1))


def test_estimate_parts_lists_checks_the_lists():
    grid = make_grid(SMALL)
    full, one = _lists(grid)
    snap = _small_snapshot()
    assert estimate_parts_lists(full, one, snap, as_of=AS_OF).to_json() == \
        estimate_layout(grid, snap, as_of=AS_OF).to_json()
    bad = [
        (one, one), (full, full),
        (full, build_parts_list(grid, owned=OwnedInputs(kits=1, spares_percent=parse_percent(5)))),
        (full, build_parts_list(grid, owned=OwnedInputs(kits=1, owned_files=(OwnedFile("o.csv", "0" * 64, {}, 0),)))),
        (full, build_parts_list(grid, owned=OwnedInputs(kits=1), layout_sha256="f" * 64)),
    ]
    for f, o in bad:
        with pytest.raises(ValueError):
            estimate_parts_lists(f, o, snap, as_of=AS_OF)


def test_json_is_deterministic_and_has_no_generation_time():
    r = _report(make_grid(SMALL), _small_snapshot())
    a, b = r.to_json(), _report(make_grid(SMALL), _small_snapshot()).to_json()
    assert a == b and a.endswith("}\n")
    d = json.loads(a)
    assert list(d) == ["format_version", "kind", "kit", "layout", "snapshot", "staleness",
                       "estimates", "notes", "estimate_note", "attribution", "disclaimer"]
    assert d["kind"] == "price-estimate" and d["format_version"] == "1"
    assert "generated" not in a and "generated_at" not in a
    assert d["estimate_note"] == ESTIMATE_NOTE and d["attribution"] == ATTRIBUTION
    assert d["disclaimer"] == DISCLAIMER
    full = d["estimates"]["full"]
    assert full["totals"] == {"average": "1.76", "low": "0.54", "high": "27.00"}
    assert full["whole_dollars"] == {"average": 2, "low": 1, "high": 27}
    white = full["lines"][0]
    assert white["unit"] == {"average": "0.0385", "low": "0.0100", "high": "0.5000"}
    assert white["line"] == {"average": "1.1550", "low": "0.3000", "high": "15.0000"}
    assert white["count"] == {"unit_quantity": 100, "total_quantity": 10000}
    assert white["bricklink"] == {"item_no": "4073", "color_id": 1, "color_name": "White"}
    assert full["unpriced"][0] == {"part_id": "98138", "part_type": "tile", "color_key": "lego_bright_red",
                                   "name": "Bright Red", "quantity": 7, "reason": REASON_NO_DATA}
    snap = d["snapshot"]
    assert snap["packaged"] is False and snap["retrieved_at"] == "2026-12-01T18:03:05Z"
    assert snap["statistic"] == {"average": "qty_avg_price", "low": "min_price", "high": "max_price"}


def test_report_records_the_snapshot_file():
    r = _report(make_grid(SMALL), load_snapshot(FIXTURE_SNAPSHOT))
    s = r.to_dict()["snapshot"]
    assert s["file"] == "bricklink_price_guide.json" and s["path"] == str(FIXTURE_SNAPSHOT)
    assert len(s["sha256"]) == 64 and s["complete"] is True
    assert isinstance(r, EstimateReport)


def test_parts_does_not_import_prices():
    parts_dir = Path(__file__).resolve().parents[3] / "src" / "lego_image_processor" / "parts"
    for py in parts_dir.glob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert "prices" not in (node.module or ""), py.name
            elif isinstance(node, ast.Import):
                assert not any("prices" in a.name for a in node.names), py.name


# --- square tiles (feature 016 T064; spec Edge Cases, research R15) -----------------------------

FIXTURE_3070B = FIXTURE_SNAPSHOT.parent / "bricklink_price_guide_3070b.json"


def test_winkel_estimate_is_incomplete_without_square_tile_prices(confirmed_winkel):
    from ...winkel_layouts import winkel_grid
    grid = winkel_grid(confirmed_winkel)
    r = _report(grid, load_snapshot(FIXTURE_SNAPSHOT))
    n = confirmed_winkel.counts["margin"]
    for kind in ("full", "one_kit"):
        e = r.estimates[kind]
        assert not e.complete
        un = e.unpriced_lines
        assert [(l.lot.part_id, l.lot.part_type, l.lot.color_key, l.quantity, l.reason) for l in un] == \
            [("3070b", "square_tile", "lego_black", n, REASON_NOT_IN_SNAPSHOT)]
        d = e.to_dict()
        assert d["complete"] is False and d["unpriced"][0]["part_id"] == "3070b"
        line = d["lines"][-1]
        assert (line["part_type"], line["basis"], line["reason"]) == ("square_tile", "unpriced",
                                                                     REASON_NOT_IN_SNAPSHOT)
    assert r.to_dict()["layout"]["template"]["id"] == "winkel-tripel"
    assert any("could not be priced" in note for note in r.notes)


def test_winkel_estimate_is_complete_with_the_3070b_fixture(confirmed_winkel):
    from ...winkel_layouts import winkel_grid
    snap = load_snapshot(FIXTURE_3070B)
    r = _report(winkel_grid(confirmed_winkel), snap)
    full = r.estimates["full"]
    assert full.complete and r.estimates["one_kit"].complete and full.pieces == 10240
    sq = [l for l in full.lines if l.lot.part_id == "3070b"]
    assert len(sq) == 1 and sq[0].basis == "sold"
    unit = snap.lot_for("3070b", 26).figures.qty_avg_price
    assert sq[0].line[0] == unit * confirmed_winkel.counts["margin"]


def test_kit_estimates_unchanged_by_the_square_tile_fixture():
    grid = load_official_design().to_layout()
    a = _report(grid, load_snapshot(FIXTURE_SNAPSHOT)).to_dict()
    b = _report(grid, load_snapshot(FIXTURE_3070B)).to_dict()
    assert a["estimates"] == b["estimates"] and a["notes"] == b["notes"] and a["layout"] == b["layout"]
    assert "template" not in a["layout"]

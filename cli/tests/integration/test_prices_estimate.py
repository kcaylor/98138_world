"""Estimates of the official layout and a land-elevation fixture build (011 T022; US1-1 to US1-4,
SC-003, SC-007). Offline: the fixture snapshot and the dataset fixtures only."""

import socket
import time
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import pytest

from lego_image_processor.kit import load_official_design
from lego_image_processor.maps.build import build_map
from lego_image_processor.maps.recipe import load_recipe
from lego_image_processor.parts import OwnedInputs, build_parts_list, read_layout
from lego_image_processor.prices import estimate_layout, load_snapshot
from lego_image_processor.prices.wording import ALL_COLORS_HINT, REASON_NOT_IN_SNAPSHOT

from ..conftest import NetworkBlockedError
from ..unit.prices.conftest import FIXTURE_SNAPSHOT

AS_OF = date(2026, 12, 5)


@pytest.fixture(scope="module")
def snapshot():
    return load_snapshot(FIXTURE_SNAPSHOT)


@pytest.fixture
def elevation(fixture_registry):
    fixture_registry.place_all()
    return build_map(load_recipe("land-elevation")).layout


def _hand_sums(pl, snapshot, qty):
    sums = {"average": Decimal(0), "low": Decimal(0), "high": Decimal(0)}
    for lot in pl.lots:
        q = qty(lot)
        if not q:
            continue
        entry = snapshot.lot_for(lot.part_id, lot.ids.lego_id)
        if entry is None or entry.figures is None:
            continue
        f = entry.figures
        sums["average"] += q * f.qty_avg_price
        sums["low"] += q * f.min_price
        sums["high"] += q * f.max_price
    return {k: v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for k, v in sums.items()}


def test_official_layout(snapshot):
    grid = load_official_design().to_layout()
    r = estimate_layout(grid, snapshot, as_of=AS_OF)
    full = r.estimates["full"]
    pl = build_parts_list(grid)
    assert len(pl.lots) == 10 and full.lots == 10
    assert full.totals == _hand_sums(pl, snapshot, lambda l: l.needed)
    assert full.complete and full.pieces == 10240
    one = r.estimates["one_kit"]
    assert one.nothing_to_buy and one.totals["average"] == Decimal("0.00")
    assert "One kit covers every piece." in r.notes


def test_land_elevation_fixture_build(elevation, snapshot):
    r = estimate_layout(elevation, snapshot, as_of=AS_OF)
    topup = build_parts_list(elevation, owned=OwnedInputs(kits=1))
    one = r.estimates["one_kit"]
    # US1-2: the top-up prices exactly each lot's to_buy with one kit
    assert {(l.lot.part_id, l.lot.color_key): l.quantity for l in one.lines} == \
        {(l.part_id, l.color_key): l.to_buy for l in topup.lots if l.to_buy > 0}
    assert one.pieces == topup.totals()["to_buy"] > 0
    assert one.totals == _hand_sums(topup, snapshot, lambda l: l.to_buy)
    full = r.estimates["full"]
    assert full.pieces == 10240
    assert full.totals == _hand_sums(build_parts_list(elevation), snapshot, lambda l: l.needed)
    # US1-3: one tile lot priced from stock, counted in by_basis
    stock = [l for l in full.lines if l.basis == "stock"]
    assert [l.lot.color_key for l in stock] == ["lego_medium_azur"]
    assert full.by_basis["stock"] == {"lots": 1, "pieces": stock[0].quantity}
    # US1-4: Dark Brown is not in the snapshot; the estimate is incomplete with counts and the hint
    brown = [l for l in full.lines if l.basis == "unpriced"]
    assert [(l.lot.color_key, l.reason) for l in brown] == [("lego_dark_brown", REASON_NOT_IN_SNAPSHOT)]
    assert not full.complete
    assert full.by_basis["unpriced"] == {"lots": 1, "pieces": brown[0].quantity}
    assert any(n.startswith(f"Incomplete: {brown[0].quantity:,} pieces in 1 color") for n in r.notes)
    assert any(ALL_COLORS_HINT in n for n in r.notes)
    d = r.to_dict()["estimates"]["full"]["unpriced"]
    assert d == [{"part_id": "6141", "part_type": "plate", "color_key": "lego_dark_brown",
                  "name": "Dark Brown", "quantity": brown[0].quantity, "reason": REASON_NOT_IN_SNAPSHOT}]


def test_estimate_from_file_under_two_seconds(tmp_path, snapshot):
    """SC-003: a 10,240-position layout, read from file, both estimates and JSON."""
    path = tmp_path / "official.json"
    path.write_text(load_official_design().to_layout().to_json(), encoding="utf-8")
    start = time.perf_counter()
    r = estimate_layout(read_layout(path), load_snapshot(FIXTURE_SNAPSHOT), as_of=AS_OF)
    r.to_json()
    assert time.perf_counter() - start < 2.0


def test_runs_under_the_socket_guard(snapshot):
    """SC-007: the suite-wide guard is on, and estimating needs no network."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(NetworkBlockedError):
            s.connect(("192.0.2.1", 443))
    finally:
        s.close()
    assert estimate_layout(load_official_design().to_layout(), snapshot, as_of=AS_OF).estimates["full"].complete


# --- a map on the Winkel tripel template (feature 016 T064) --------------------------------------

def test_winkel_fixture_build(confirmed_winkel, fixture_registry, snapshot):
    from ..unit.prices.conftest import FIXTURE_DIR
    fixture_registry.place_all()
    grid = build_map(load_recipe("ocean-sst"), template="winkel-tripel").layout
    n = confirmed_winkel.counts["margin"]
    r = estimate_layout(grid, snapshot, as_of=AS_OF)
    full = r.estimates["full"]
    assert not full.complete and full.pieces == 10240
    assert [(l.lot.part_id, l.quantity, l.reason) for l in full.unpriced_lines] == \
        [("3070b", n, REASON_NOT_IN_SNAPSHOT)]
    one = r.estimates["one_kit"]
    assert [(l.lot.part_id, l.quantity) for l in one.unpriced_lines] == [("3070b", n)]
    complete = estimate_layout(grid, load_snapshot(FIXTURE_DIR / "bricklink_price_guide_3070b.json"),
                               as_of=AS_OF)
    assert complete.estimates["full"].complete and complete.estimates["one_kit"].complete
    # plates and round tiles are priced the same with either snapshot
    same = {(l.lot.part_id, l.lot.color_key): l.line for l in full.lines if l.lot.part_id != "3070b"}
    assert same == {(l.lot.part_id, l.lot.color_key): l.line
                    for l in complete.estimates["full"].lines if l.lot.part_id != "3070b"}


# --- a map with the in-margin plaque (feature 017 T072) ------------------------------------------

def _plaque_build(fixture_registry, corner="bottom-left"):
    from lego_image_processor.maps.margin import MarginTreatment
    fixture_registry.place_all()
    return build_map(load_recipe("ocean-sst"), template="winkel-tripel",
                     margin=MarginTreatment(plaque=corner, plaque_source="option")).layout


def test_plaque_fixture_build(confirmed_winkel, fixture_registry):
    from ..unit.prices.conftest import FIXTURE_DIR
    grid = _plaque_build(fixture_registry)
    r = estimate_layout(grid, load_snapshot(FIXTURE_DIR / "bricklink_price_guide_3070b.json"), as_of=AS_OF)
    for kind in ("full", "one_kit"):
        e = r.estimates[kind]
        assert not e.complete
        assert [(l.lot.part_id, l.quantity, l.reason) for l in e.unpriced_lines] == \
            [("10202", 1, REASON_NOT_IN_SNAPSHOT)]
    assert r.estimates["full"].pieces == 10205
    complete = estimate_layout(grid, load_snapshot(FIXTURE_DIR / "bricklink_price_guide_plaque.json"),
                               as_of=AS_OF)
    assert complete.estimates["full"].complete and complete.estimates["one_kit"].complete


def test_parts_estimate_with_a_named_snapshot_of_every_recipe_lot_and_the_plaque(
        confirmed_winkel, fixture_registry, tmp_path):
    """T091: the owner's refresh (every ``recipe_lots()`` lot plus ``10202:26``, a ``named``
    snapshot) makes ``parts estimate`` complete with and without a plaque."""
    import json

    from click.testing import CliRunner

    from lego_image_processor.cli.main import cli
    from lego_image_processor.prices.snapshot import parse_snapshot, snapshot_to_json

    from ..unit.prices.test_estimate import named_snapshot_of_every_recipe_lot_and_the_plaque
    snap = tmp_path / "named.json"
    snap.write_text(snapshot_to_json(named_snapshot_of_every_recipe_lot_and_the_plaque()), encoding="utf-8")
    assert parse_snapshot(json.loads(snap.read_text(encoding="utf-8"))).lot_set["kind"] == "named"
    layouts = {"kit": load_official_design().to_layout(),
               "plaque": _plaque_build(fixture_registry),
               "winkel": build_map(load_recipe("ocean-sst"), template="winkel-tripel").layout}
    for name, grid in layouts.items():
        p = tmp_path / f"{name}.json"
        p.write_text(grid.to_json(), encoding="utf-8")
        r = CliRunner().invoke(cli, ["parts", "estimate", str(p), "--prices", str(snap), "--as-of",
                                     "2026-12-05", "--format", "json"])
        assert r.exit_code == 0, r.output
        d = json.loads(r.output)
        assert d["snapshot"]["complete"] is True, name
        assert d["estimates"]["full"]["complete"] and d["estimates"]["one_kit"]["complete"], name
        assert ("10202" in {l["part_id"] for l in d["estimates"]["full"]["lines"]}) == (name == "plaque")

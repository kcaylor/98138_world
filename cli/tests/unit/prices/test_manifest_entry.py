"""The web subset of an estimate report (011 T038; contracts/web.md "Manifest additions")."""

import json
from datetime import date

import pytest

from lego_image_processor.kit import load_official_design
from lego_image_processor.prices.estimate import estimate_layout
from lego_image_processor.prices.snapshot import load_snapshot, parse_snapshot
from lego_image_processor.prices.wording import ATTRIBUTION, BASIS_SENTENCE, ESTIMATE_NOTE

from ..parts.layouts import SMALL, UNCITED, make_grid
from .conftest import FIXTURE_SNAPSHOT, figures, lot_entry, snapshot_dict

AS_OF = date(2026, 12, 5)
ENTRY_KEYS = {"label", "totals", "whole_dollars", "pieces", "complete", "nothing_to_buy",
              "unpriced", "stock"}


def _small():
    return parse_snapshot(snapshot_dict([
        lot_entry("6141", "lego_white", sold=figures("0.0385", "0.0100", "0.5000")),
        lot_entry("6141", "lego_brick_yellow", sold=None, stock=figures("0.0500", "0.0200", "1.0000")),
        lot_entry("98138", "lego_bright_red", sold=None, stock=None, error="not found"),
    ]))


def test_entry_keys_and_values_match_the_estimate():
    r = estimate_layout(make_grid(UNCITED), _small(), as_of=AS_OF)
    for kind in ("full", "one_kit"):
        e = r.estimates[kind]
        m = r.manifest_entry(kind)
        assert set(m) == ENTRY_KEYS
        assert m["label"] == e.label
        assert m["totals"] == {k: format(v, "f") for k, v in e.totals.items()}
        assert all(isinstance(v, str) for v in m["totals"].values())
        assert m["whole_dollars"] == e.whole_dollars
        assert all(type(v) is int for v in m["whole_dollars"].values())
        assert m["pieces"] == e.pieces
        assert m["complete"] is e.complete and m["nothing_to_buy"] is e.nothing_to_buy
        assert m["unpriced"] == e.by_basis["unpriced"]
        assert m["stock"] == e.by_basis["stock"]
    full = r.manifest_entry("full")
    assert full["label"] == "Every piece"
    assert full["complete"] is False and full["unpriced"]["lots"] >= 2   # Bright Red + Medium Blue
    assert full["stock"]["lots"] == 1
    assert r.manifest_entry("one_kit")["label"] == "On top of one 31203 kit"


def test_entry_is_json_ready():
    r = estimate_layout(make_grid(SMALL), _small(), as_of=AS_OF)
    for kind in ("full", "one_kit"):
        assert json.loads(json.dumps(r.manifest_entry(kind))) == r.manifest_entry(kind)


def test_unknown_kind():
    r = estimate_layout(make_grid(SMALL), _small(), as_of=AS_OF)
    with pytest.raises(ValueError, match="full, one_kit"):
        r.manifest_entry("half")


def test_official_one_kit_nothing_to_buy():
    r = estimate_layout(load_official_design().to_layout(), load_snapshot(FIXTURE_SNAPSHOT), as_of=AS_OF)
    one = r.manifest_entry("one_kit")
    assert one["nothing_to_buy"] is True and one["complete"] is True and one["pieces"] == 0
    assert one["whole_dollars"] == {"average": 0, "low": 0, "high": 0}
    full = r.manifest_entry("full")
    assert full["pieces"] == 10240 and full["complete"] is True
    assert full["whole_dollars"]["low"] <= full["whole_dollars"]["average"] <= full["whole_dollars"]["high"]


def test_prices_block():
    snap = load_snapshot(FIXTURE_SNAPSHOT)
    r = estimate_layout(load_official_design().to_layout(), snap, as_of=AS_OF)
    b = r.prices_block()
    assert set(b) == {"snapshot", "source", "basis", "estimate_note", "attribution", "staleness"}
    assert b["snapshot"] == {"file": "bricklink_price_guide.json", "sha256": snap.sha256,
                             "retrieved_at": "2026-12-01T18:03:05Z", "retrieved_on": "2026-12-01",
                             "complete": True, "lots": len(snap.lots)}
    assert b["source"] == {"title": "BrickLink price guide (BrickLink API)",
                           "url": "https://www.bricklink.com"}
    assert b["basis"] == BASIS_SENTENCE
    assert b["estimate_note"] == ESTIMATE_NOTE and b["attribution"] == ATTRIBUTION
    assert b["staleness"] == {"as_of": "2026-12-05", "age_days": 4, "threshold_days": 90,
                              "stale": False}
    assert json.loads(json.dumps(b)) == b


def test_prices_block_stale_and_partial():
    snap = parse_snapshot(snapshot_dict(complete=False, count=19))
    r = estimate_layout(make_grid(SMALL), snap, as_of=date(2027, 6, 1))
    b = r.prices_block()
    assert b["snapshot"]["complete"] is False and b["snapshot"]["lots"] == 2
    assert b["snapshot"]["file"] is None and b["snapshot"]["sha256"] is None   # parsed, not loaded
    assert b["staleness"]["stale"] is True and b["staleness"]["age_days"] == 182

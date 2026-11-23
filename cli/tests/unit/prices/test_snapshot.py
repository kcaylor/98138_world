"""Price snapshot model, validation and deterministic writing (011 T008, T011; FR-001 to FR-004)."""

import hashlib
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from lego_image_processor.prices import snapshot as snapmod
from lego_image_processor.prices import wording
from lego_image_processor.prices.lots import lot_ref
from lego_image_processor.prices.snapshot import (GuideFigures, PriceSnapshot, SnapshotError,
                                                  SnapshotMissingError, largest_changes,
                                                  load_snapshot, parse_snapshot, snapshot_to_json)

from .conftest import FIXTURE_DIR, FIXTURE_SNAPSHOT, deep, figures, lot_entry, snapshot_dict


def _reject(write_snapshot, data, path_text):
    p = write_snapshot(data)
    with pytest.raises(SnapshotError) as exc:
        load_snapshot(p)
    assert path_text in str(exc.value), str(exc.value)
    return str(exc.value)


def test_valid_snapshot_loads(write_snapshot, snap_dict):
    p = write_snapshot(snap_dict)
    s = load_snapshot(p)
    assert isinstance(s, PriceSnapshot)
    assert s.complete is True and len(s.lots) == 2
    white = s.lot_for("6141", 1)
    assert white.lot == lot_ref("6141", "lego_white")
    assert isinstance(white.sold, GuideFigures)
    assert white.sold.qty_avg_price == Decimal("0.0400") and str(white.sold.qty_avg_price) == "0.0400"
    assert white.basis == "sold"
    assert s.sha256 == hashlib.sha256(p.read_bytes()).hexdigest()
    assert s.file_name == "snap.json" and s.path == str(p) and s.packaged is False
    assert s.lot_for("6141", 999) is None


@pytest.mark.parametrize("mutate,where", [
    (lambda d: d.update(format_version="2"), "format_version"),
    (lambda d: d.update(extra=1), "extra"),
    (lambda d: d["source"].update(token="x"), "source.token"),
    (lambda d: d["lots"][0].update(oauth_signature="x"), "lots[0].oauth_signature"),
    (lambda d: d["lots"][0]["sold"].update(Authorization="OAuth x"), "lots[0].sold.Authorization"),
    (lambda d: d.update(attribution="Price data: BrickLink. Endorsed by BrickLink."), "attribution"),
    (lambda d: d.update(estimate_note="cheap"), "estimate_note"),
    (lambda d: d.update(disclaimer="x"), "disclaimer"),
    (lambda d: d["source"].update(disclaimer="x"), "source.disclaimer"),
    (lambda d: d["lots"][0]["sold"].update(min_price="0.01000"), "lots[0].sold.min_price"),
    (lambda d: d["lots"][0]["sold"].update(min_price=0.01), "lots[0].sold.min_price"),
    (lambda d: d["lots"][0]["sold"].update(min_price="-0.01"), "lots[0].sold.min_price"),
    (lambda d: d["lots"][0]["sold"].update(min_price="0"), "lots[0].sold.min_price"),
    (lambda d: d["lots"][0]["sold"].update(min_price="0.0500"), "lots[0].sold"),
    (lambda d: d["lots"][0]["sold"].update(max_price="0.0300"), "lots[0].sold"),
    (lambda d: d["lots"][0]["sold"].update(avg_price="0.6000"), "lots[0].sold"),
    (lambda d: d["lots"][0]["sold"].update(unit_quantity=0), "lots[0].sold.unit_quantity"),
    (lambda d: d["lots"][0]["sold"].update(total_quantity=5), "lots[0].sold.total_quantity"),
    (lambda d: d["lots"][0].update(error="not found"), "lots[0]"),
    (lambda d: d["lots"][0].update(error="boom", sold=None, stock=None), "lots[0].error"),
    (lambda d: d["lots"].reverse(), "lots"),
    (lambda d: d["lots"].append(deep(d["lots"][0])) or d["lot_set"].update(count=3), "lots"),
    (lambda d: d["lots"][0]["bricklink"].update(item_no="6141"), "lots[0].bricklink"),
    (lambda d: d["lots"][0]["bricklink"].update(color_id=2), "lots[0].bricklink"),
    (lambda d: d["lots"][0]["bricklink"].update(color_name="Blanc"), "lots[0].bricklink"),
    (lambda d: d["lots"][0].update(lego_color_name="Snow"), "lots[0].lego_color_name"),
    (lambda d: d["lots"][0].update(color_key="lego_black"), "lots[0].color_key"),
    (lambda d: d["lots"][0].update(retrieved_at="2026-12-01T19:00:00Z"), "lots[0].retrieved_at"),
    (lambda d: d["lots"][0].update(retrieved_at="2026-12-01 18:02:30"), "lots[0].retrieved_at"),
    (lambda d: d["retrieved"].update(finished_at="2026-12-01T18:00:00Z"), "retrieved"),
    (lambda d: d["lot_set"].update(count=3), "complete"),
    (lambda d: d["query"].update(currency_code="EUR"), "query.currency_code"),
    (lambda d: d["lot_set"].update(kind="some"), "lot_set.kind"),
])
def test_invalid_snapshots_are_rejected_naming_the_path(write_snapshot, snap_dict, mutate, where):
    mutate(snap_dict)
    _reject(write_snapshot, snap_dict, where)


def test_not_found_lot_with_no_figures_is_valid(write_snapshot):
    d = snapshot_dict([lot_entry("6141", "lego_white", sold=None, stock=None, error="not found")])
    s = load_snapshot(write_snapshot(d))
    assert s.lots[0].basis == "unpriced" and s.lots[0].error == "not found"


def test_stock_only_lot_has_stock_basis(write_snapshot):
    d = snapshot_dict([lot_entry("6141", "lego_white", sold=None)])
    assert load_snapshot(write_snapshot(d)).lots[0].basis == "stock"


def test_partial_snapshot_loads(write_snapshot):
    d = snapshot_dict(complete=False, count=5)
    s = load_snapshot(write_snapshot(d))
    assert s.complete is False and s.lot_set["count"] == 5


def test_missing_packaged_snapshot(monkeypatch, tmp_path):
    monkeypatch.setattr(wording, "PACKAGED_SNAPSHOT_PATH", tmp_path / "bricklink_price_guide.json")
    with pytest.raises(SnapshotMissingError) as exc:
        load_snapshot()
    assert "no price snapshot is packaged yet" in str(exc.value)
    assert isinstance(exc.value, SnapshotError)


def test_packaged_snapshot_is_marked_packaged(monkeypatch, write_snapshot, snap_dict):
    p = write_snapshot(snap_dict, name="bricklink_price_guide.json")
    monkeypatch.setattr(wording, "PACKAGED_SNAPSHOT_PATH", p)
    s = load_snapshot()
    assert s.packaged is True and s.path is None and s.file_name == "bricklink_price_guide.json"


def test_unreadable_and_not_json(write_snapshot, tmp_path):
    with pytest.raises(SnapshotError, match="cannot read"):
        load_snapshot(tmp_path / "absent.json")
    with pytest.raises(SnapshotError, match="not JSON"):
        load_snapshot(write_snapshot(None, raw=b"{nope"))
    with pytest.raises(SnapshotError):
        load_snapshot(write_snapshot(None, raw=b"[]"))


def test_canonical_json_round_trip(write_snapshot, snap_dict):
    # keys shuffled on disk; the writer restores the canonical order
    shuffled = dict(reversed(list(snap_dict.items())))
    s = load_snapshot(write_snapshot(shuffled))
    text = snapshot_to_json(s)
    assert text.endswith("}\n") and not text.endswith("\n\n")
    assert list(json.loads(text)) == list(snap_dict)
    assert json.loads(text) == snap_dict
    again = load_snapshot(write_snapshot(None, name="again.json", raw=text.encode("utf-8")))
    assert snapshot_to_json(again) == text
    assert text == json.dumps(snap_dict, indent=2, ensure_ascii=False) + "\n"


def test_parse_snapshot_from_dict(snap_dict):
    s = parse_snapshot(snap_dict)
    assert s.sha256 is None and len(s.lots) == 2


def test_largest_changes(snap_dict):
    old = deep(snap_dict)
    new = deep(snap_dict)
    new["lots"][0]["sold"] = figures(avg="0.0500")          # +25 %
    new["lots"][1]["sold"] = figures(avg="0.0300")          # -25 %, tie -> lot order
    changes = largest_changes(parse_snapshot(old), parse_snapshot(new))
    assert [c[0].key for c in changes] == [("6141", 1), ("98138", 140)]
    lot, a, b, pct = changes[0]
    assert (a, b) == (Decimal("0.0400"), Decimal("0.0500")) and pct == Decimal("25")
    new["lots"][1]["sold"] = figures(avg="0.0100")          # -75 %
    changes = largest_changes(parse_snapshot(old), parse_snapshot(new), n=1)
    assert len(changes) == 1 and changes[0][0].key == ("98138", 140) and changes[0][3] == Decimal("-75")


def test_largest_changes_skip_lots_missing_on_either_side(snap_dict):
    old = deep(snap_dict)
    old["lots"] = old["lots"][:1]
    old["lot_set"]["count"] = 1
    new = deep(snap_dict)
    new["lots"][0]["sold"] = figures(avg="0.0400")
    assert largest_changes(parse_snapshot(old), parse_snapshot(new)) == [
        (lot_ref("6141", "lego_white"), Decimal("0.0400"), Decimal("0.0400"), Decimal("0"))]


# --- the committed test fixture (T011) ---------------------------------------------------------

def test_fixture_snapshot_loads_and_matches_its_source_record():
    s = load_snapshot(FIXTURE_SNAPSHOT)
    assert s.complete and s.lot_set["kind"] == "named"
    src = json.loads((FIXTURE_DIR / "bricklink_price_guide.source.json").read_text(encoding="utf-8"))
    assert src["synthetic"] is True and src["sha256"] == s.sha256
    assert src["disclaimer"] == wording.DISCLAIMER and "not BrickLink data" in src["note"]


def test_fixture_covers_the_official_layout_with_a_stock_lot_and_no_dark_brown():
    from lego_image_processor.kit import load_official_design
    from lego_image_processor.parts import build_parts_list
    s = load_snapshot(FIXTURE_SNAPSHOT)
    pl = build_parts_list(load_official_design().to_layout())
    for lot in pl.lots:
        assert s.lot_for(lot.part_id, lot.ids.lego_id) is not None, lot.color_key
    assert s.lot_for("6141", 308) is None                      # Dark Brown: not in the snapshot
    stock = [l for l in s.lots if l.basis == "stock"]
    assert len(stock) == 1 and stock[0].lot.part_id == "98138"


def test_fixture_generator_reproduces_identical_bytes(tmp_path):
    tool = Path(__file__).resolve().parents[3] / "tools" / "fixtures011" / "make_price_fixture.py"
    r = subprocess.run([sys.executable, str(tool), "--out", str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    for name in ("bricklink_price_guide.json", "bricklink_price_guide.source.json"):
        assert (tmp_path / name).read_bytes() == (FIXTURE_DIR / name).read_bytes(), name

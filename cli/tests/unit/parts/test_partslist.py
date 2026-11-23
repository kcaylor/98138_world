"""Parts list (005 T013, T017, T029): layout input, lots, order, JSON, top-up arithmetic."""

import json
from fractions import Fraction

import pytest

from lego_image_processor.parts import (LayoutInputError, OwnedInputs, build_parts_list,
                                        parse_owned_csv, read_layout)
from lego_image_processor.parts.partslist import DISCLAIMER

from .layouts import LAND_ELEVATION, MISMATCH, SMALL, UNCITED, make_grid


def _lot(pl, part, key):
    return next(l for l in pl.lots if (l.part_id, l.color_key) == (part, key))


# --- layout input (T013) ------------------------------------------------------------------------

def test_read_layout_hashes_bytes_and_keeps_map_metadata(tmp_path):
    meta = {"recipe": {"id": "r", "format": "1", "title": "R", "sha256": "ab" * 32},
            "layers": [{"class": "land", "dataset": {"id": "d", "version": "1", "citation": "C",
                                                      "license": "L", "title": "x"}},
                       {"class": "ocean"}]}
    p = tmp_path / "l.json"
    p.write_text(make_grid(SMALL, source_image="recipe:r", map_metadata=meta).to_json(), encoding="utf-8")
    li = read_layout(p)
    import hashlib
    assert li.sha256 == hashlib.sha256(p.read_bytes()).hexdigest()
    pl = build_parts_list(li)
    assert pl.layout["map"] == {"recipe": {"id": "r", "format": "1", "sha256": "ab" * 32},
                                "datasets": [{"id": "d", "version": "1", "citation": "C", "license": "L"}]}
    assert pl.layout["sha256"] == li.sha256 and pl.layout["source_image"] == "recipe:r"


def test_read_layout_errors(tmp_path):
    with pytest.raises(LayoutInputError, match="cannot read"):
        read_layout(tmp_path / "absent.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(LayoutInputError, match="JSON"):
        read_layout(bad)
    d = json.loads(make_grid(SMALL).to_json())
    d["metadata"]["schema_version"] = "1.0"
    old = tmp_path / "old.json"
    old.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(LayoutInputError, match="schema"):
        read_layout(old)
    d = json.loads(make_grid(SMALL).to_json())
    d["positions"][0]["x"] = 128
    out = tmp_path / "out.json"
    out.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(LayoutInputError, match="outside"):
        read_layout(out)
    d = json.loads(make_grid(SMALL).to_json())
    d["positions"][1].update(x=d["positions"][0]["x"], y=d["positions"][0]["y"])
    dup = tmp_path / "dup.json"
    dup.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(LayoutInputError, match="twice"):
        read_layout(dup)


# --- lots, order, totals, JSON (T017) -----------------------------------------------------------

def test_lots_grouped_and_ordered():
    pl = build_parts_list(make_grid(UNCITED + MISMATCH[-1:]))
    order = [(l.part_id, l.color_key) for l in pl.lots]
    assert order == [("6141", "lego_white"), ("6141", "lego_brick_yellow"),
                     ("98138", "lego_bright_red"), ("98138", "lego_medium_azur"),
                     ("6141", "lego_black"), ("6141", "lego_medium_blue")]  # unverified last
    assert [l.needed for l in pl.lots] == [30, 12, 7, 20, 4, 5]
    assert _lot(pl, "6141", "lego_medium_blue").reason == "no cited color for part"
    assert _lot(pl, "6141", "lego_black").reason == "no cited color for part"  # LEGO ID 999
    t = pl.totals()
    assert t == {"lots": 6, "needed": 78, "owned": 0, "to_buy": 78, "lots_to_buy": 6, "spares": 0,
                 "surplus": 0, "verified_lots": 4, "unverified_lots": 2,
                 "leftover": 0}


def test_json_shape_and_determinism():
    pl = build_parts_list(make_grid(UNCITED), layout_path="x.json")
    a, b = pl.to_json(), build_parts_list(make_grid(UNCITED), layout_path="x.json").to_json()
    assert a == b
    d = json.loads(a)
    assert list(d) == ["format_version", "kit", "layout", "owned", "lots", "leftovers", "totals", "unverified",
                       "citations", "acknowledgement", "prices", "disclaimer"]
    assert d["disclaimer"] == DISCLAIMER and "Rebrickable" in d["acknowledgement"]
    assert d["layout"]["map"] is None
    v = d["lots"][0]
    assert list(v) == ["part_id", "part_type", "color_key", "verified", "lego", "bricklink",
                       "rebrickable", "rgb", "needed", "kit_supply", "loose", "owned", "shortfall",
                       "spares", "to_buy", "surplus"]
    assert v["bricklink"] == {"item_type": "P", "item_no": "4073", "color_name": "White", "color_id": 1}
    assert v["rebrickable"] == {"part_num": "6141", "color_name": "White", "color_id": 15}
    u = d["lots"][-1]
    assert u["verified"] is False and u["layout_color"] == {"name": "Medium Blue", "code": "102"}
    assert not {"lego", "bricklink", "rebrickable"} & set(u)
    assert d["owned"]["spares_percent"] == "0"
    ids = [c["id"] for c in d["citations"]]
    assert ids[0] == "kit-31203-instructions" and "rebrickable-terms" in ids
    assert {"bricklink-4073", "rebrickable-6141", "bricklink-98138", "rebrickable-98138"} <= set(ids)
    assert "generated_at" not in a and "2026-11-22T" not in a


# --- top-up arithmetic (T029) -------------------------------------------------------------------

def test_kits_and_shortfall():
    grid = make_grid(LAND_ELEVATION)
    pl = build_parts_list(grid, owned=OwnedInputs(kits=1))
    white, bbg = _lot(pl, "6141", "lego_white"), _lot(pl, "98138", "lego_bright_bluish_green")
    assert (white.kit_supply, white.shortfall, white.surplus) == (3064, 0, 2914)
    assert (bbg.kit_supply, bbg.shortfall, bbg.to_buy) == (1879, 3145, 3145)
    # Bright Green on the plate: the kit's 601 Bright Green pieces are tiles (research R11)
    assert _lot(pl, "6141", "lego_bright_green").kit_supply == 0
    assert pl.totals()["to_buy"] == 6382 and pl.totals()["lots_to_buy"] == 11


def test_owned_missing_and_spares(write_csv):
    grid = make_grid(LAND_ELEVATION)
    loose = parse_owned_csv(write_csv("loose.csv", "Part,Color,Quantity\n98138,3,1000\n"))
    missing = parse_owned_csv(write_csv("missing.csv", "Element,Quantity\n6322819,12\n"))
    pl = build_parts_list(grid, owned=OwnedInputs(kits=1, owned_files=(loose,), missing_files=(missing,),
                                                  spares_percent=Fraction(2)))
    bbg = _lot(pl, "98138", "lego_bright_bluish_green")
    assert (bbg.loose, bbg.owned, bbg.shortfall, bbg.spares, bbg.to_buy) == (1000, 2879, 2145, 43, 2188)
    azur = _lot(pl, "98138", "lego_medium_azur")
    assert (azur.kit_supply, azur.surplus, azur.spares) == (1607 - 12, 1595 - 1436, 0)
    assert _lot(pl, "6141", "lego_white").spares == 0  # no shortfall, no spares


def test_missing_never_below_zero(write_csv):
    missing = parse_owned_csv(write_csv("m.csv", "Part,Color,Quantity\n98138,322,5000\n6141,15,7\n"))
    pl = build_parts_list(make_grid(SMALL), owned=OwnedInputs(kits=0, missing_files=(missing,)))
    assert _lot(pl, "98138", "lego_medium_azur").kit_supply == 0
    pl = build_parts_list(make_grid(SMALL), owned=OwnedInputs(kits=2, missing_files=(missing,)))
    assert _lot(pl, "98138", "lego_medium_azur").kit_supply == 0
    assert _lot(pl, "6141", "lego_white").kit_supply == 2 * 3064 - 7


def test_spares_ceil_exact():
    grid = make_grid([("plate", "lego_brick_yellow", "Brick Yellow", "5", 2145)])
    for pct, expected in ((Fraction(2), 43), (Fraction(1, 10), 3), (Fraction(0), 0), (Fraction(100), 2145)):
        lot = build_parts_list(grid, owned=OwnedInputs(spares_percent=pct)).lots[0]
        assert lot.spares == expected

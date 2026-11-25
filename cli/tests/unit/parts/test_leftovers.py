"""Leftovers in the box (feature 014 FR-001..FR-005): kit supply minus pieces used, per part+color."""

import pytest

from lego_image_processor.kit import load_official_design
from lego_image_processor.kit.inventory import load_kit_inventory
from lego_image_processor.parts import OwnedInputs, build_parts_list, to_bricklink_xml, to_rebrickable_csv
from lego_image_processor.parts.owned import OwnedFile

from .layouts import LAND_ELEVATION, SMALL, make_grid


def _kit_rows():
    inv = load_kit_inventory()
    return {("6141" if e.role == "land" else "98138", e.color_key): e.quantity
            for e in inv.by_role("land") + inv.by_role("ocean")}


def _by_key(pl):
    return {(l.part_id, l.color_key): l for l in pl.leftovers}


def test_official_one_kit_leftovers_are_the_kit_extras():
    design = load_official_design()
    pl = build_parts_list(design.to_layout(), owned=OwnedInputs(kits=1))
    rows = _by_key(pl)
    assert len(rows) == 10 and set(rows) == set(_kit_rows())
    extras = {c.key: c.supplied - c.used for c in design.counts}
    assert {k[1]: l.leftover for k, l in rows.items()} == extras
    white = rows[("6141", "lego_white")]
    assert (white.kit_supply, white.used, white.leftover) == (3064, 3062, 2)
    assert pl.totals()["leftover"] == sum(_kit_rows().values()) - 10240 == 890


def test_supplies_come_from_the_inventory():
    pl = build_parts_list(make_grid(SMALL), owned=OwnedInputs(kits=1))
    assert {k: l.kit_supply for k, l in _by_key(pl).items()} == _kit_rows()


def test_unused_kit_colors_left_over_whole_and_used_counted():
    pl = build_parts_list(make_grid(LAND_ELEVATION), owned=OwnedInputs(kits=1))
    rows = _by_key(pl)
    coral = rows[("98138", "lego_vibrant_coral")]
    assert (coral.used, coral.leftover) == (0, 601)
    assert rows[("6141", "lego_white")].used == 150
    assert rows[("6141", "lego_white")].leftover == 3064 - 150
    # More used than supplied: never negative (Bright Bluish Green 5,024 > 1,879).
    bbg = rows[("98138", "lego_bright_bluish_green")]
    assert (bbg.used, bbg.leftover) == (5024, 0)
    # A Bright Green plate does not use the kit's Bright Green tiles (005 R11).
    assert rows[("98138", "lego_bright_green")].used == 0
    assert pl.totals()["leftover"] == sum(l.leftover for l in pl.leftovers)


@pytest.mark.parametrize("kits", [0, 2])
def test_kits_scale_supply(kits):
    pl = build_parts_list(make_grid(SMALL), owned=OwnedInputs(kits=kits))
    rows = _by_key(pl)
    assert all(l.kit_supply == kits * _kit_rows()[k] for k, l in rows.items())
    if kits == 0:
        assert pl.totals()["leftover"] == 0


def test_missing_reduces_supply_loose_does_not_add():
    key = ("98138", "lego_medium_azur")
    f = OwnedFile(path="m.csv", sha256="0" * 64, quantities={key: 7}, ignored_rows=0)
    pl = build_parts_list(make_grid(SMALL), owned=OwnedInputs(kits=1, missing_files=(f,),
                                                              owned_files=(f,)))
    row = _by_key(pl)[key]
    assert (row.kit_supply, row.used, row.leftover) == (1607 - 7, 20, 1607 - 7 - 20)


def test_json_shape_and_order():
    d = build_parts_list(make_grid(SMALL), owned=OwnedInputs(kits=1)).to_dict()
    rows = d["leftovers"]
    assert [r["part_type"] for r in rows] == ["plate"] + ["tile"] * 9
    assert set(rows[0]) == {"part_id", "part_type", "color_key", "lego", "rgb", "kit_supply", "used",
                            "leftover"}
    assert rows[0]["lego"] == {"name": "White", "id": 1, "element_id": "614101"}
    ids = [r["lego"]["id"] for r in rows[1:]]
    assert ids == sorted(ids)
    assert d["totals"]["leftover"] == sum(r["leftover"] for r in rows)


def test_exports_do_not_change():
    lay = make_grid(LAND_ELEVATION)
    pl = build_parts_list(lay, owned=OwnedInputs(kits=1))
    xml, csv = to_bricklink_xml(pl), to_rebrickable_csv(pl)
    assert "601" not in csv.split("Quantity", 1)[1].split(",")  # Coral leftover is not listed
    assert xml.count("<ITEM>") == len(pl.lots_to_buy)

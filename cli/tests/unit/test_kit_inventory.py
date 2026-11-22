"""Loader tests for the generated kit 31203 inventory (kit_31203_inventory.json)."""

import json
from pathlib import Path

import pytest

from lego_image_processor.kit import (
    KitElement, KitInventory, UnsupportedKitError, load_kit_colors, load_kit_inventory,
)
from lego_image_processor.kit.inventory import INVENTORY_PATH, parse_inventory

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "kit31203"


@pytest.fixture(scope="module")
def inv():
    return load_kit_inventory()


def test_matches_page_159(inv):
    expected = json.loads((FIXTURES / "inventory_expected.json").read_text())
    got = {e.element_id: e.quantity for e in inv.elements}
    assert got == {e["element_id"]: e["quantity"] for e in expected["elements"]}
    assert len(inv.elements) == 32
    assert sum(e.quantity for e in inv.elements) == 11694
    assert inv.totals == {"lines": 32, "pieces": 11694}


def test_every_line_cited(inv):
    for e in inv.elements:
        assert isinstance(e, KitElement)
        assert e.source_page == 159
        assert inv.source.citation(e.citation)
        assert e.description and e.color and e.part_ids


def test_land_element(inv):
    land = inv.land_element()
    assert land.element_id == "614101"
    assert land.design_id == "6141"
    assert land.part_ids == ["6141", "4073"]
    assert land.color == "White"
    assert land.color_key == "lego_white"
    assert land.quantity == 3064
    assert land.role == "land"


def test_ocean_elements(inv):
    ocean = inv.ocean_elements()
    assert len(ocean) == 9
    for e in ocean:
        assert "98138" in e.part_ids and "35381" in e.part_ids
        assert e.design_id == "35381"
    assert len({e.color_key for e in ocean}) == 9
    assert sum(e.quantity for e in ocean) == 8066


def test_section_base(inv):
    bases = inv.by_role("section_base")
    assert [(b.element_id, b.quantity) for b in bases] == [("6302092", 40)]


def test_metadata_verified(inv):
    for e in inv.by_role("land") + inv.by_role("ocean"):
        assert e.metadata_verified is True
    unverified = {e.element_id for e in inv.elements if not e.metadata_verified}
    assert unverified == {"4121715", "4160228"}
    for eid in unverified:
        e = next(x for x in inv.elements if x.element_id == eid)
        assert e.role == "frame_other"
        assert e.color_key is None


def test_supplied(inv):
    assert inv.supplied("lego_white") == 3064
    assert inv.supplied("lego_bright_bluish_green") == 1879
    assert inv.supplied("lego_earth_blue") == 393
    assert inv.supplied("lego_bright_red") == 0


def test_map_colors_agree_with_color_table(inv):
    by_key = {c.key: c for c in load_kit_colors()}
    for e in inv.by_role("land") + inv.by_role("ocean"):
        assert by_key[e.color_key].lego.name == e.color
        assert by_key[e.color_key].element_id == e.element_id
        assert by_key[e.color_key].role == e.role


def test_source_block(inv):
    assert inv.kit_id == "31203"
    assert isinstance(inv, KitInventory)
    assert inv.source.pages == [159]
    assert inv.source.generator == "cli/tools/kit31203 extract"


def test_unsupported_kit():
    with pytest.raises(UnsupportedKitError, match="Kit ID '999' not supported"):
        load_kit_inventory("999")
    assert issubclass(UnsupportedKitError, ValueError)


@pytest.mark.parametrize("mutate,rule", [
    (lambda d: d["elements"].pop(), "pieces"),
    (lambda d: next(e for e in d["elements"] if e["role"] == "land").update(role="frame_other"), "land"),
    (lambda d: next(e for e in d["elements"] if e["role"] == "ocean").update(color="Black"), "kit_colors"),
    (lambda d: d["elements"][0].update(quantity=0), "quantity"),
    (lambda d: d["elements"][1].update(element_id=d["elements"][0]["element_id"]), "unique"),
    (lambda d: d["elements"][0].update(source_page=158), "source_page"),
])
def test_malformed_rejected(mutate, rule):
    data = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    # keep totals consistent with the edit where the rule is not about totals
    mutate(data)
    with pytest.raises(ValueError) as info:
        parse_inventory(data, "bad_inventory.json")
    assert "bad_inventory.json" in str(info.value)
    assert rule in str(info.value)


def test_supplied_for_looks_up_by_part_and_color(inv):
    """005 research R11: supply depends on the part, not only on the color key."""
    assert inv.supplied("lego_bright_green") == 601            # part-blind (tile supply)
    assert inv.supplied_for("6141", "lego_bright_green") == 0  # no Bright Green plates in the kit
    assert inv.supplied_for("98138", "lego_bright_green") == 601
    assert inv.supplied_for("6141", "lego_white") == 3064
    assert inv.supplied_for("98138", "lego_white") == 0
    assert inv.supplied_for("98138", "lego_bright_bluish_green") == 1879
    assert inv.supplied_for("3001", "lego_white") == 0

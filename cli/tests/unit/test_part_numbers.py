"""Marketplace part numbers (005 FR-001, T006): shipped values and loader validation."""

import copy
import json

import pytest

from lego_image_processor.kit.part_numbers import (PART_NUMBERS_PATH, load_part_numbers,
                                                   parse_part_numbers)

DATA = json.loads(PART_NUMBERS_PATH.read_text(encoding="utf-8"))


def test_shipped_part_numbers():
    t = load_part_numbers()
    plate, tile = t.get("6141"), t.get("98138")
    assert (plate.bricklink_item_type, plate.bricklink_item_no) == ("P", "4073")
    assert "6141" in plate.bricklink_alternates
    assert plate.rebrickable_part_num == "6141" and plate.lego_design_ids == ("6141",)
    assert (tile.bricklink_item_no, tile.rebrickable_part_num) == ("98138", "98138")
    assert tile.lego_design_ids == ("98138", "35381")
    assert "White" in plate.bricklink_colors and "Dark Turquoise" in tile.bricklink_colors
    for p in (plate, tile):
        assert set(p.citations) == {"bricklink", "rebrickable"}
        assert all(len(c.sha256) == 64 and "web.archive.org" in c.url for c in p.citations.values())
    with pytest.raises(KeyError):
        t.get("3001")


def _bad(mutate):
    d = copy.deepcopy(DATA)
    mutate(d)
    return d


@pytest.mark.parametrize("mutate,match", [
    (lambda d: d["parts"].pop("98138"), "exactly"),
    (lambda d: d["source"]["pages"][0].update(sha256="abc"), "sha256"),
    (lambda d: d["source"]["pages"][0].pop("sha256"), "sha256"),
    (lambda d: d["parts"]["6141"]["bricklink"].update(alternates=["15570"]), "alternate"),
    (lambda d: d["parts"]["6141"]["bricklink"].update(item_no=""), "item_no"),
    (lambda d: d["parts"]["6141"]["rebrickable"].update(part_num="4073"), "part_num"),
    (lambda d: d["parts"]["98138"]["bricklink"].update(citation="nowhere"), "citation"),
    (lambda d: d["parts"]["98138"]["bricklink"].update(item_no="39797", alternates=["98138"]),
     "kit inventory"),
    (lambda d: d["source"].update(disclaimer="x"), "disclaimer"),
])
def test_loader_rejects(mutate, match):
    with pytest.raises(ValueError, match=match):
        parse_part_numbers(_bad(mutate))


# --- feature 016 (T014): the 1x1 square tile 3070b, not in the kit (research R10) ---------------

def test_parts_are_exactly_the_kit_parts_and_the_square_tile():
    from lego_image_processor.kit.part_numbers import KIT_PARTS, PARTS
    assert PARTS == ("6141", "98138", "3070b") and KIT_PARTS == ("6141", "98138")
    assert list(load_part_numbers().parts) == ["6141", "98138", "3070b"]
    with pytest.raises(ValueError, match="exactly"):
        parse_part_numbers(_bad(lambda d: d["parts"].pop("3070b")))


def test_shipped_square_tile_numbers():
    sq = load_part_numbers().get("3070b")
    # BrickLink files the 3070b design as item 3070 (3070b is an alternate there)
    assert (sq.bricklink_item_type, sq.bricklink_item_no) == ("P", "3070")
    assert "3070b" in sq.bricklink_alternates
    assert sq.rebrickable_part_num == "3070b"
    assert "3070" in sq.lego_design_ids and "3070b" not in sq.lego_design_ids
    assert "Black" in sq.bricklink_colors
    assert {c.id for c in sq.citations.values()} == {"bricklink-3070", "rebrickable-3070b"}
    assert all(len(c.sha256) == 64 and "web.archive.org" in c.url for c in sq.citations.values())


@pytest.mark.parametrize("mutate,match", [
    # rules that hold for every part
    (lambda d: d["parts"]["3070b"]["bricklink"].update(alternates=["30039"]), "alternate"),
    (lambda d: d["parts"]["3070b"]["rebrickable"].update(part_num="3070"), "part_num"),
    (lambda d: d["parts"]["3070b"].update(lego_design_ids=[]), "lego_design_ids"),
])
def test_square_tile_loader_rules(mutate, match):
    with pytest.raises(ValueError, match=match):
        parse_part_numbers(_bad(mutate))


def test_kit_rules_do_not_apply_to_the_square_tile():
    # not in the kit inventory, and its design IDs need not include "3070b" (LEGO design 3070)
    d = _bad(lambda d: d["parts"]["3070b"].update(lego_design_ids=["3070"]))
    assert parse_part_numbers(d).get("3070b").lego_design_ids == ("3070",)
    # the kit parts keep both kit rules
    with pytest.raises(ValueError, match="lego_design_ids"):
        parse_part_numbers(_bad(lambda d: d["parts"]["6141"].update(lego_design_ids=["4073"])))

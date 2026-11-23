"""Lot keys and lot sets (011 T006; FR-007, research R5)."""

import pytest

from lego_image_processor.kit.part_colors import load_part_colors
from lego_image_processor.kit.part_numbers import load_part_numbers
from lego_image_processor.maps.recipe import bundled_recipes, load_recipe, parse_recipe
from lego_image_processor.prices.lots import (LotRef, all_cited_lots, lot_ref, parse_lot,
                                              recipe_lots)


def test_lot_ref_plate_white_from_the_cited_tables():
    lot = lot_ref("6141", "lego_white")
    row = load_part_colors().get("6141", "lego_white")
    assert isinstance(lot, LotRef)
    assert (lot.part_id, lot.color_key, lot.lego_color_id, lot.lego_color_name) == \
        ("6141", "lego_white", row.lego.id, row.lego.name)
    assert (lot.bricklink_item_type, lot.bricklink_item_no) == ("P", "4073")
    assert (lot.bricklink_color_id, lot.bricklink_color_name) == (row.bricklink.id, row.bricklink.name)
    assert lot.key == ("6141", 1)
    assert lot.part_type == "plate"


def test_lot_ref_kit_tile():
    lot = lot_ref("98138", "lego_earth_blue")
    row = load_part_colors().get("98138", "lego_earth_blue")
    assert (lot.bricklink_item_type, lot.bricklink_item_no) == ("P", "98138")
    assert lot.lego_color_id == 140 and lot.bricklink_color_id == row.bricklink.id
    assert lot.part_type == "tile"


def test_lot_ref_unknown_color():
    with pytest.raises(ValueError, match="lego_nope"):
        lot_ref("6141", "lego_nope")


def test_recipe_lots_default_set():
    lots = recipe_lots()
    assert len(lots) == 19
    assert sum(l.part_id == "6141" for l in lots) == 10
    assert sum(l.part_id == "98138" for l in lots) == 9
    assert len({l.key for l in lots}) == 19
    assert list(lots) == sorted(lots, key=lambda l: (0 if l.part_id == "6141" else 1, l.lego_color_id))
    # the land-elevation shadow color (Earth Blue, the default shadow) is included
    assert ("98138", 140) in {l.key for l in lots}


def test_recipe_lots_include_the_shadow_color():
    text = load_recipe("land-elevation").path.read_text(encoding="utf-8")
    text += '\n[shadow]\ncolor = "lego_black"\n'
    shadowed = parse_recipe(text)
    lots = recipe_lots([shadowed])
    assert ("98138", lot_ref("98138", "lego_black").lego_color_id) in {l.key for l in lots}
    no_shadow = parse_recipe(text.replace('[shadow]\ncolor = "lego_black"', '[shadow]\nenabled = false'))
    assert ("98138", 140) not in {l.key for l in recipe_lots([no_shadow])}


def test_one_extra_declared_color_adds_exactly_that_lot():
    recipes = [load_recipe(p) for p in bundled_recipes().values()]
    base = {l.key for l in recipe_lots(recipes)}
    official = load_recipe("official-31203")
    text = official.path.read_text(encoding="utf-8").replace(
        'colors = ["lego_white"]\nweights = [1]', 'colors = ["lego_white", "lego_black"]\nweights = [1, 1]\n[land.texture]\nkind = "mix"')
    extra = parse_recipe(text, path=official.path)
    lots = {l.key for l in recipe_lots(recipes + [extra])}
    assert lots - base == {("6141", lot_ref("6141", "lego_black").lego_color_id)}


def test_all_cited_lots():
    lots = all_cited_lots()
    assert len(lots) == 84
    assert sum(l.part_id == "6141" for l in lots) == 44
    assert sum(l.part_id == "98138" for l in lots) == 40
    pn = load_part_numbers()
    for l in lots:
        assert l.bricklink_color_name in pn.get(l.part_id).bricklink_colors


def test_parse_lot():
    lot = parse_lot("98138:140")
    assert lot == lot_ref("98138", "lego_earth_blue")
    assert parse_lot(" 6141:1 ") == lot_ref("6141", "lego_white")
    for bad in ("98138:9999", "3001:1", "x", "98138:", "98138:abc"):
        with pytest.raises(ValueError, match=bad.strip() if bad.strip() else "lot"):
            parse_lot(bad)

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

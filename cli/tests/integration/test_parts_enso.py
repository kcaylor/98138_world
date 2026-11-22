"""ENSO layouts: the build report's extra tiles equal `parts list --kits 1` (feature 009, US3-1,
FR-016; data-model.md Report.extra_tiles). Not affiliated with or endorsed by The LEGO Group.
"""

import pytest

from lego_image_processor.maps.build import build_map
from lego_image_processor.maps.recipe import load_recipe
from lego_image_processor.maps.suitability import extra_tiles
from lego_image_processor.parts import OwnedInputs, build_parts_list


@pytest.mark.parametrize("recipe_id", ["ocean-el-nino", "ocean-la-nina"])
def test_report_extras_equal_parts_to_buy(fixture_registry, recipe_id):
    fixture_registry.place_all()
    res = build_map(load_recipe(recipe_id))
    ocean = next(layer for layer in res.report["layers"] if layer["class"] == "ocean")
    pl = build_parts_list(res.layout, owned=OwnedInputs(kits=1))
    tiles = {l.color_key: l for l in pl.lots if l.part_id == "98138"}
    assert sum(l.to_buy for l in tiles.values()) == extra_tiles(ocean["supply"])
    for row in ocean["supply"]:
        expected = max(0, row["used"] - row["supplied"])
        got = tiles[row["key"]].to_buy if row["key"] in tiles else 0
        assert got == expected, row["key"]
    plates = [l for l in pl.lots if l.part_id == "6141"]
    assert plates and all(l.to_buy == 0 for l in plates)

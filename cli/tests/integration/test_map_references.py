"""SC-005, SC-009: bundled recipes use cited colors and registered, small, open datasets."""

import pytest

from lego_image_processor.datasets import load_registry
from lego_image_processor.kit.part_colors import load_part_colors
from lego_image_processor.maps.recipe import bundled_recipes, load_recipe

RECIPES = sorted(bundled_recipes())


@pytest.mark.parametrize("rid", RECIPES)
def test_every_color_is_cited(rid):
    table = load_part_colors()
    r = load_recipe(rid)
    for layer in r.layers:
        for key in layer.colors:
            c = table.get(layer.part_id, key)
            assert c is not None, (rid, key)
            for cat in (c.lego, c.bricklink, c.rebrickable):
                assert cat.name and isinstance(cat.id, int)
            assert c.element_id.isdigit()
            assert {"lego", "bricklink", "rebrickable", "element"} <= set(c.citations)


@pytest.mark.parametrize("rid", RECIPES)
def test_datasets_registered(rid):
    ids = {e.id for e in load_registry().entries}
    for e in load_recipe(rid).datasets():
        assert e.id in ids and e.license and e.citation


def test_downloads_for_all_bundled_recipes_under_15_mb():
    needed = {e.id: e for rid in RECIPES for e in load_recipe(rid).datasets() if e.kind == "download"}
    assert sum(e.size for e in needed.values()) < 15_000_000

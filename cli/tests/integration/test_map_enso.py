"""The ENSO maps on the derived fixtures (feature 009: US1, US2; SC-002-SC-005).

Not affiliated with or endorsed by The LEGO Group.
"""

import numpy as np
import pytest

from lego_image_processor.layout.arrangement import arrange_grid, parse_arrangement
from lego_image_processor.maps.build import build_map, land_mask_array
from lego_image_processor.maps.projection import load_kit_projection
from lego_image_processor.maps.recipe import bundled_recipes, load_recipe
from lego_image_processor.maps.suitability import extra_tiles, kit_supply

BOUNDS = (-9, -1.5, -0.5, -0.25, -0.1, 0.1, 0.3, 0.5, 1.0, 9)
COLORS = ("lego_earth_blue", "lego_bright_bluish_green", "lego_medium_azur", "lego_bright_green",
          "lego_bright_yellowish_green", "lego_brick_yellow", "lego_flame_yellowish_orange",
          "lego_bright_orange", "lego_vibrant_coral")
SC004_BOUND = 1200
DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."


@pytest.fixture
def built(fixture_registry):
    fixture_registry.place_all()
    return {rid: build_map(load_recipe(rid)) for rid in ("ocean-el-nino", "ocean-la-nina")}


def _ocean(result):
    return next(layer for layer in result.report["layers"] if layer["class"] == "ocean")


def nino34_classes(result):
    """Ocean classes of the cells whose centres lie in Niño 3.4 (5S-5N, 170W-120W)."""
    proj = load_kit_projection()
    arr = result.arrangement
    land = arr.roll(land_mask_array())
    cl = result.classes["ocean"]
    out = []
    H, W = land.shape
    for y in range(H):
        for x in range(W):
            if land[y, x]:
                continue
            lat, lon = proj.cell_center(y, arr.to_kit(x))
            if -5 <= lat <= 5 and -170 <= lon <= -120:
                out.append(int(cl[y, x]))
    return np.array(out)


def _common_checks(result, dataset_id):
    r = result.recipe
    assert result.layout.arrangement["id"] == "B"
    assert result.report["arrangement_source"] == "recipe"
    assert r.ocean.role == "data" and r.ocean.variable == "ssta"
    assert r.ocean.dataset.id == dataset_id
    assert r.ocean.classification.method == "bins"
    assert r.ocean.classification.bounds == BOUNDS
    assert r.ocean.colors == COLORS
    assert r.ocean.texture.kind == "none"
    assert r.land.role == "background" and r.land.colors == ("lego_white",)
    assert r.shadow.enabled and r.shadow.color == "lego_earth_blue"
    ocean = _ocean(result)
    assert ocean["filled_share"] < 0.05
    assert "outside_bounds" not in ocean
    assert result.report["shadow"]["cells"] == 390
    tiles = kit_supply()["98138"]
    for p in result.layout.positions:
        if p.part_type == "tile":
            assert p.color_id in tiles, p.color_id
        else:
            assert p.color_id == "lego_white"
    assert extra_tiles(ocean["supply"]) <= SC004_BOUND
    land = next(layer for layer in result.report["layers"] if layer["class"] == "land")
    assert extra_tiles(land["supply"]) == 0
    ds = result.layout.map_metadata["layers"][1]["dataset"]
    assert ds["license"] and ds["citation"] and ds["doi"] == "10.1175/JCLI-D-16-0836.1"
    assert DISCLAIMER in bundled_recipes()[r.id].read_text(encoding="utf-8")


class TestElNino:
    def test_builds_as_b_with_the_legend(self, built):
        _common_checks(built["ocean-el-nino"], "ersst-v5-1997-12")

    def test_title_and_description(self, built):
        r = built["ocean-el-nino"].recipe
        for text in (r.title, r.description):
            assert "El Niño" in text and "December 1997" in text

    def test_nino34_is_warm(self, built):
        cls = nino34_classes(built["ocean-el-nino"])
        assert cls.size >= 40
        warm = sum(BOUNDS[c] >= 0.5 for c in cls)
        assert warm / cls.size >= 0.9

    def test_rehang_without_rebuild(self, built):
        res = built["ocean-el-nino"]
        a = arrange_grid(res.layout, parse_arrangement("A"))
        assert a.arrangement["id"] == "A"
        delta = parse_arrangement("A").column_shift - parse_arrangement("B").column_shift
        before = {(p.x, p.y): p.color_id for p in res.layout.positions}
        for p in a.positions:
            assert before[((p.x - delta) % 128, p.y)] == p.color_id


class TestLaNina:
    def test_builds_as_b_with_the_same_legend(self, built):
        _common_checks(built["ocean-la-nina"], "ersst-v5-1988-12")
        en, ln = built["ocean-el-nino"].recipe.ocean, built["ocean-la-nina"].recipe.ocean
        assert en.classification.bounds == ln.classification.bounds
        assert en.colors == ln.colors

    def test_title_and_description(self, built):
        r = built["ocean-la-nina"].recipe
        for text in (r.title, r.description):
            assert "La Niña" in text and "December 1988" in text

    def test_nino34_is_cold(self, built):
        cls = nino34_classes(built["ocean-la-nina"])
        assert cls.size >= 40
        cold = sum(BOUNDS[c + 1] <= -0.5 for c in cls)
        assert cold / cls.size >= 0.9

    def test_same_color_same_class(self, built):
        en, ln = built["ocean-el-nino"], built["ocean-la-nina"]
        land = en.arrangement.roll(land_mask_array())
        ocean = ~land
        ce, cn = en.classes["ocean"], ln.classes["ocean"]
        colors_e = {(p.x, p.y): p.color_id for p in en.layout.positions}
        colors_n = {(p.x, p.y): p.color_id for p in ln.layout.positions}
        checked = 0
        for y, x in zip(*np.nonzero(ocean)):
            if ce[y, x] < 0 or cn[y, x] < 0:  # shadow cells are not classified
                continue
            if colors_e[(x, y)] == colors_n[(x, y)]:
                assert ce[y, x] == cn[y, x]
                checked += 1
        assert checked > 0

    def test_empty_class_does_not_fail(self, built):
        codes = [w["code"] for w in built["ocean-la-nina"].report["warnings"]]
        assert "over_supply" in codes  # warnings are reported, the build succeeds

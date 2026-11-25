"""Neighbourhood rules on a non-kit template (T050; FR-008; research R7; spec Edge Cases).

The land shadow is ``shadow_mask(land) & ocean``: a land stud whose eastern neighbour is margin
casts none (on the kit ``ocean = ~land``, so nothing changes there). Halo, ``mix`` and ``blend``
never color a margin stud; nearest fill draws only from layer studs; nothing wraps at the board
edges. Not affiliated with or endorsed by The LEGO Group.
"""

import numpy as np
import pytest

from lego_image_processor.datasets.grid import SourceGrid
from lego_image_processor.maps.build import build_map, land_mask_array
from lego_image_processor.maps.recipe import load_recipe, parse_recipe
from lego_image_processor.maps.reproject import reproject_layer
from lego_image_processor.maps.texture import shadow_mask

HEAD = """
format = "1"
id = "bg-map"
title = "Background"
"""

LAND_BG = """
[land]
role = "background"
colors = ["lego_white"]
weights = [1]
"""

HALO = """
[ocean]
role = "background"
colors = ["lego_bright_bluish_green", "lego_medium_azur"]

[ocean.texture]
kind = "halo"
inner = 1.5
outer = 3.0
spacing = 2.0
"""

MIX = """
[ocean]
role = "background"
colors = ["lego_medium_azur", "lego_earth_blue", "lego_bright_bluish_green"]
weights = [2, 1, 1]

[ocean.texture]
kind = "mix"
cluster = 1.5
"""

MIX_LAND = """
[land]
role = "background"
colors = ["lego_white", "lego_brick_yellow"]
weights = [1, 1]

[land.texture]
kind = "mix"
cluster = 2.0
"""


def _grid_by_type(result):
    out = {}
    for p in result.layout.positions:
        out[(p.y, p.x)] = (p.part_type, p.color_id)
    return out


class TestShadowMask:
    def test_ocean_argument(self, confirmed_winkel):
        land, ocean = np.array(confirmed_winkel.land), np.array(confirmed_winkel.ocean)
        s = shadow_mask(land, ocean=ocean)
        assert (s == (shadow_mask(land) & ocean)).all()
        assert not (s & ~ocean).any()

    def test_kit_unchanged(self):
        land = land_mask_array()
        assert (shadow_mask(land, ocean=~land) == shadow_mask(land)).all()

    def test_land_next_to_margin_casts_none(self, confirmed_winkel):
        t = confirmed_winkel
        land, margin = np.array(t.land), np.array(t.margin)
        edge = np.zeros_like(land)
        edge[:, :-1] = land[:, :-1] & margin[:, 1:]  # land studs whose eastern neighbour is margin
        assert edge.any()
        r = build_map(parse_recipe(HEAD + LAND_BG + HALO), template="winkel-tripel")
        by = _grid_by_type(r)
        ys, xs = np.nonzero(edge)
        for y, x in zip(ys, xs):
            assert by[(y, x + 1)] == ("square_tile", "lego_black")
        # every shadow cell is an ocean stud whose western neighbour is land
        shadow_color = r.recipe.shadow.color
        s = shadow_mask(land, ocean=np.array(t.ocean))
        assert r.report["shadow"]["cells"] == int(s.sum())
        for y, x in zip(*np.nonzero(s)):
            assert by[(y, x)] == ("tile", shadow_color)

    def test_no_wrap(self):
        land = np.zeros((4, 6), bool)
        land[:, -1] = True
        ocean = ~land
        assert not shadow_mask(land, ocean=ocean)[:, 0].any()


class TestBackgrounds:
    @pytest.mark.parametrize("ocean", [HALO, MIX])
    def test_margin_never_takes_a_layer_color(self, confirmed_winkel, ocean):
        t = confirmed_winkel
        r = build_map(parse_recipe(HEAD + LAND_BG + ocean), template="winkel-tripel")
        by = _grid_by_type(r)
        margin = np.array(t.margin)
        for (y, x), (part, color) in by.items():
            if margin[y, x]:
                assert (part, color) == ("square_tile", "lego_black")
            else:
                assert part == ("plate" if t.land[y, x] else "tile")

    def test_halo_ring_is_near_land(self, confirmed_winkel):
        from scipy.ndimage import distance_transform_edt

        t = confirmed_winkel
        r = build_map(parse_recipe(HEAD + LAND_BG + HALO), template="winkel-tripel")
        dist = distance_transform_edt(~np.array(t.land))
        for p in r.layout.positions:
            if p.part_type == "tile" and p.color_id == "lego_medium_azur":
                assert dist[p.y, p.x] <= 3.0

    def test_mix_on_land_counts(self, confirmed_winkel):
        t = confirmed_winkel
        r = build_map(parse_recipe(HEAD + MIX_LAND + MIX), template="winkel-tripel")
        land = r.report["layers"][0]
        assert land["cells"] == t.counts["land"]
        assert sum(c["cells"] for c in land["class_counts"]) == t.counts["land"]


class TestDataLayers:
    def test_nearest_fill_draws_only_from_layer_studs(self, confirmed_winkel):
        t = confirmed_winkel
        tp = t.grid_projection
        lat = np.arange(-85.0, 90, 10.0)
        lon = np.arange(-175.0, 180, 10.0)
        g = SourceGrid(values=np.arange(lat.size * lon.size, dtype=float).reshape(lat.size, lon.size),
                       lat=lat, lon=lon)
        mask = np.array(t.ocean)
        f = reproject_layer(g, tp, mask, "ocean")
        sampled = mask & (f.samples > 0)
        assert f.filled.any()
        assert np.isin(f.values[f.filled], f.values[sampled]).all()
        assert np.isnan(f.values[~mask]).all()

    def test_blend_never_colors_the_margin(self, confirmed_winkel, fixture_registry):
        fixture_registry.place_all()
        t = confirmed_winkel
        r = build_map(load_recipe("ocean-sst"), template="winkel-tripel")  # rank-to-supply + blend
        margin = np.array(t.margin)
        for p in r.layout.positions:
            assert (p.part_type == "square_tile") == bool(margin[p.y, p.x])
            if margin[p.y, p.x]:
                assert p.color_id == "lego_black"
        ocean = r.report["layers"][1]
        assert ocean["cells"] + r.report["shadow"]["cells"] == t.counts["ocean"]

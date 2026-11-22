"""Land shadow and coastal halo (004 amendment 2026-11-22: FR-026-FR-032)."""

import numpy as np
import pytest

from lego_image_processor.maps.recipe import RecipeError, parse_recipe
from lego_image_processor.maps.texture import fill_halo, shadow_mask

from .test_recipe import BASE

HALO_OCEAN = """
[ocean]
role = "background"
colors = ["lego_bright_bluish_green", "lego_medium_azur"]

[ocean.texture]
kind = "halo"
inner = 1.5
outer = 3.0
spacing = 2.0
"""


def _halo_recipe(texture=HALO_OCEAN):
    return BASE[:BASE.index("[ocean]")] + texture


def _err(text):
    with pytest.raises(RecipeError) as e:
        parse_recipe(text)
    return e.value


class TestShadowRecipe:
    def test_default_on_east_earth_blue(self):
        s = parse_recipe(BASE).shadow
        assert (s.enabled, s.color, s.direction) == (True, "lego_earth_blue", "east")

    def test_disable_and_color(self):
        assert parse_recipe(BASE + '\n[shadow]\nenabled = false\n').shadow.enabled is False
        s = parse_recipe(BASE + '\n[shadow]\ncolor = "lego_medium_azur"\n').shadow
        assert s.enabled and s.color == "lego_medium_azur"

    def test_direction_validated(self):
        assert _err(BASE + '\n[shadow]\ndirection = "west"\n').path == "shadow.direction"

    def test_color_must_be_tile_color(self):
        assert _err(BASE + '\n[shadow]\ncolor = "lego_plaid"\n').path == "shadow.color"

    def test_enabled_must_be_bool(self):
        assert _err(BASE + '\n[shadow]\nenabled = 1\n').path == "shadow.enabled"

    def test_unknown_key(self):
        assert _err(BASE + '\n[shadow]\nwidth = 2\n').path == "shadow.width"


class TestHaloRecipe:
    def test_parse(self):
        r = parse_recipe(_halo_recipe())
        t = r.ocean.texture
        assert (t.kind, t.inner, t.outer, t.spacing) == ("halo", 1.5, 3.0, 2.0)
        assert r.ocean.colors == ("lego_bright_bluish_green", "lego_medium_azur")

    def test_defaults(self):
        t = parse_recipe(_halo_recipe(HALO_OCEAN.replace("inner = 1.5\nouter = 3.0\nspacing = 2.0\n", ""))).ocean.texture
        assert (t.inner, t.outer, t.spacing) == (1.5, 3.0, 2.0)

    def test_needs_two_colors(self):
        e = _err(_halo_recipe(HALO_OCEAN.replace(', "lego_medium_azur"', "")))
        assert e.path == "ocean.colors"

    def test_ocean_only(self):
        text = BASE.replace('colors = ["lego_white"]\nweights = [1]',
                            'colors = ["lego_white", "lego_dark_green"]\n[land.texture]\nkind = "halo"')
        assert _err(text).path == "land.texture.kind"

    def test_no_weights(self):
        e = _err(_halo_recipe(HALO_OCEAN.replace('"lego_medium_azur"]', '"lego_medium_azur"]\nweights = [1, 1]')))
        assert e.path == "ocean.weights"

    def test_radii(self):
        assert _err(_halo_recipe(HALO_OCEAN.replace("outer = 3.0", "outer = 1.0"))).path == "ocean.texture.outer"
        assert _err(_halo_recipe(HALO_OCEAN.replace("inner = 1.5", "inner = 0"))).path == "ocean.texture.inner"
        assert _err(_halo_recipe(HALO_OCEAN.replace("spacing = 2.0", "spacing = -1"))).path == "ocean.texture.spacing"

    def test_halo_on_data_layer(self):
        e = _err(BASE.replace('kind = "blend"\nwidth = 0.25', 'kind = "halo"'))
        assert e.path == "ocean.texture.kind"


def _island():
    land = np.zeros((40, 60), bool)
    land[15:25, 20:30] = True
    land[:, 0] = True          # a land column on the west edge
    return land


class TestShadowMask:
    def test_cells_east_of_land(self):
        land = _island()
        s = shadow_mask(land)
        assert not (s & land).any()
        expect = np.zeros_like(land)
        expect[15:25, 30] = True
        expect[:, 1] = True
        assert (s == expect).all()

    def test_no_wrap_at_west_edge(self):
        land = np.zeros((4, 6), bool)
        land[:, -1] = True     # land on the east edge must not shade column 0
        assert not shadow_mask(land)[:, 0].any()


class TestHalo:
    def _fill(self, seed=7):
        land = _island()
        ocean = ~land & ~shadow_mask(land)
        return land, ocean, fill_halo(ocean, land, inner=1.5, outer=3.0, spacing=2.0, seed=seed)

    def test_ring_band_and_base(self):
        from scipy.ndimage import distance_transform_edt
        land, ocean, c = self._fill()
        d = distance_transform_edt(~land)
        assert (c[~ocean] == -1).all()
        assert (c[ocean & (d <= 1.5)] == 1).all()
        assert (c[ocean & (d > 3.0)] == 0).all()
        band = ocean & (d > 1.5) & (d <= 3.0)
        share = (c[band] == 1).mean()
        assert 0.1 < share < 0.6   # a partial, even fade

    def test_band_points_min_spacing(self):
        from scipy.ndimage import distance_transform_edt
        land, ocean, c = self._fill()
        d = distance_transform_edt(~land)
        ys, xs = np.nonzero(ocean & (d > 1.5) & (d <= 3.0) & (c == 1))
        pts = np.stack([ys, xs], 1).astype(float)
        gaps = np.sqrt(((pts[:, None] - pts[None]) ** 2).sum(-1)) + np.eye(len(pts)) * 99
        assert gaps.min() >= 2.0

    def test_deterministic_by_seed(self):
        a, b, c = self._fill(3)[2], self._fill(3)[2], self._fill(4)[2]
        assert (a == b).all() and (a != c).any()

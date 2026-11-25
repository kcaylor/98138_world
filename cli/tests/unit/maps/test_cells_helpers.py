"""Public helpers of ``maps/cells.py`` that the sticker legend shares with ``map cells`` (feature
017, research R7): ``derived_bounds`` (unrounded rank boundaries) and ``variable_units``.

``cells.json`` must not change (guard G3 holds its bytes); here the rounding of the public bounds
is pinned to the bounds ``map cells`` wrote before feature 017 (fixtures, combination A).
Not affiliated with or endorsed by The LEGO Group.
"""

import dataclasses

import numpy as np
import pytest

from lego_image_processor.maps import cells
from lego_image_processor.maps.build import build_map, land_mask_array
from lego_image_processor.maps.cells import derived_bounds, map_cells, variable_units
from lego_image_processor.maps.recipe import load_recipe
from lego_image_processor.maps.texture import shadow_mask

# ``map cells`` bounds of the ocean layer before feature 017 (6038d9c code, dataset fixtures, A),
# and the unrounded boundaries they come from
CELLS_BOUNDS = {
    "ocean-sst": [-1.8, -1.8, 0.01, 10.97, 15.8, 22.22, 25.4, 27.14, 28.26, 29.76],
    "official-31203-bathymetry": [0, 784, 2296, 2610, 2877, 3562, 4320, 4572, 6170],
}
UNROUNDED = {
    "ocean-sst": [-1.799999475479126, -1.799999475479126, 0.009135623695328832, 10.96854281425476,
                  15.796077251434326, 22.218233108520508, 25.401597023010254, 27.138527870178223,
                  28.259238243103027, 29.7585391998291],
    "official-31203-bathymetry": [0.0, 783.5, 2295.722222222222, 2609.8055555555557,
                                  2876.8333333333335, 3561.8333333333335, 4319.930555555556,
                                  4572.5, 6169.666666666667],
}


class TestDerivedBounds:
    def test_midpoints_between_classes_with_outer_bounds(self):
        got = derived_bounds(np.array([1.0, 2.0, 3.0, 4.0]), np.array([0, 0, 1, 1]), 2)
        assert got == [1.0, 2.5, 4.0]

    def test_values_need_not_be_sorted(self):
        got = derived_bounds(np.array([4.0, 1.0, 3.0, 2.0]), np.array([1, 0, 1, 0]), 2)
        assert got == [1.0, 2.5, 4.0]

    def test_unrounded_floats(self):
        got = derived_bounds(np.array([100.25, 200.5, 300.75, 401.0]), np.array([0, 1, 1, 2]), 3)
        assert got == [100.25, 150.375, 350.875, 401.0]
        assert all(type(b) is float for b in got)

    def test_empty_class_repeats_a_bound(self):
        got = derived_bounds(np.array([1.0, 2.0, 3.0, 4.0]), np.array([0, 0, 2, 2]), 3)
        assert got == [1.0, 2.5, 2.5, 4.0]

    @pytest.mark.parametrize("recipe_id", sorted(CELLS_BOUNDS))
    def test_rounding_gives_the_cells_json_bounds(self, fixture_registry, recipe_id):
        fixture_registry.place_all()
        result = build_map(load_recipe(recipe_id), cache_dir=fixture_registry.cache_dir)
        assert result.arrangement.id == "A"
        land = result.arrangement.roll(land_mask_array())
        mask = ~land & ~shadow_mask(land, result.recipe.shadow.direction)
        vals = np.where(mask, result.fields["ocean"].values, np.nan)
        ok = mask & np.isfinite(vals)
        n = len(result.recipe.ocean.colors)

        raw = derived_bounds(vals[ok], result.classes["ocean"][ok], n)
        assert raw == pytest.approx(UNROUNDED[recipe_id], rel=1e-12, abs=1e-12)
        assert any(b != round(b, 2) for b in raw)  # not rounded yet
        d = cells._decimals(vals)
        assert [cells._round(b, d) for b in raw] == CELLS_BOUNDS[recipe_id]
        block = map_cells(result)["layers"]["ocean"]
        assert block["bounds"] == CELLS_BOUNDS[recipe_id]
        assert block["bounds_source"] == "built classes"


class TestVariableUnits:
    @pytest.mark.parametrize("recipe_id, layer, units", [
        ("ocean-sst", "ocean", "°C"),
        ("ocean-el-nino", "ocean", "°C"),
        ("official-31203-bathymetry", "ocean", "m"),
        ("land-elevation", "land", "m"),
        ("living-planet", "land", "g C m-2 yr-1"),
        ("living-planet", "ocean", "mg m-3"),   # log10 layer: no "log10" prefix
        ("rainfall", "ocean", "mm/day"),
        ("land-elevation", "ocean", ""),        # background layer: no dataset
    ])
    def test_bundled_layers(self, recipe_id, layer, units):
        assert variable_units(getattr(load_recipe(recipe_id), layer)) == units

    @pytest.mark.parametrize("spelling, units", [("degC", "°C"), ("DEGC", "°C"),
                                                 ("degree_C", "°C"), ("degrees_C", "°C"),
                                                 ("Celsius", "°C"), ("K", "K"), ("", "")])
    def test_registry_spelling(self, spelling, units):
        layer = load_recipe("ocean-sst").ocean
        entry = dataclasses.replace(layer.dataset, variables={layer.variable: {"units": spelling}})
        assert variable_units(dataclasses.replace(layer, dataset=entry)) == units

    def test_cells_json_keeps_the_log10_prefix(self):
        layer = load_recipe("living-planet").ocean
        assert layer.transform == "log10"
        assert cells._units(layer) == "log10 mg m-3"
        assert cells._units(load_recipe("ocean-sst").ocean) == "°C"

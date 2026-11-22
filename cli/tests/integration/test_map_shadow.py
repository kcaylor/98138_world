"""Land shadow and coastal halo on the bundled maps (004 amendment 2026-11-22: FR-026-FR-032)."""

import numpy as np
import pytest

from lego_image_processor.kit import load_official_design
from lego_image_processor.layout.kit_spec import load_kit_specification
from lego_image_processor.maps.build import build_map, land_mask_array
from lego_image_processor.maps.recipe import load_recipe, parse_recipe
from lego_image_processor.maps.texture import shadow_mask

SHADOW_CELLS = 392


def _grid(layout):
    g = np.empty((80, 128), dtype=object)
    for p in layout.positions:
        g[p.y, p.x] = p.color_id
    return g


def test_kit_shadow_is_392_cells_and_matches_official():
    # Measured on the official design: 391 of the 392 cells east of land are Earth Blue.
    s = shadow_mask(land_mask_array())
    assert int(s.sum()) == SHADOW_CELLS
    d = load_official_design()
    official = np.array([[d.color_at(x, y) for x in range(128)] for y in range(80)], dtype=object)
    assert int((official[s] == "lego_earth_blue").sum()) == 391
    assert load_kit_specification().get_tile_quantity("lego_earth_blue") >= SHADOW_CELLS


@pytest.fixture
def maps(fixture_registry):
    fixture_registry.place_all()
    cache = {}

    class _Maps:
        def __getitem__(self, rid):
            if rid not in cache:
                cache[rid] = build_map(load_recipe(rid))
            return cache[rid]
    return _Maps()


@pytest.mark.parametrize("rid", ["official-31203-bathymetry", "ocean-sst", "land-elevation"])
def test_shadow_on_by_default(maps, rid):
    m = maps[rid]
    s = shadow_mask(land_mask_array())
    g = _grid(m.layout)
    assert (g[s] == "lego_earth_blue").all()
    assert m.report["shadow"] == {"enabled": True, "color": "lego_earth_blue", "direction": "east",
                                  "cells": SHADOW_CELLS}
    assert m.layout.map_metadata["shadow"] == {"enabled": True, "color": "lego_earth_blue",
                                               "direction": "east", "cells": SHADOW_CELLS}
    ocean = next(l for l in m.report["layers"] if l["class"] == "ocean")
    assert ocean["cells"] == 7178 - SHADOW_CELLS
    blue = next(r for r in ocean["supply"] if r["key"] == "lego_earth_blue")
    assert blue["used"] == int((g == "lego_earth_blue").sum())


def test_official_recipe_disables_shadow(maps):
    m = maps["official-31203"]
    assert m.report["shadow"]["enabled"] is False and m.report["shadow"]["cells"] == 0
    assert m.agreement["total"] == {"agree": 10_240, "cells": 10_240}


def test_sst_within_one_kit_with_shadow(maps):
    spec = load_kit_specification()
    counts = maps["ocean-sst"].layout.compute_statistics().color_frequency_by_part_type["tile"]
    assert all(n <= spec.get_tile_quantity(k) for k, n in counts.items())
    assert counts["lego_earth_blue"] <= 393


def test_land_elevation_ocean_is_halo(maps):
    from scipy.ndimage import distance_transform_edt
    land = land_mask_array()
    s = shadow_mask(land)
    g = _grid(maps["land-elevation"].layout)
    d = distance_transform_edt(~land)
    ocean = ~land & ~s
    assert set(g[~land]) == {"lego_bright_bluish_green", "lego_medium_azur", "lego_earth_blue"}
    assert (g[ocean & (d <= 1.5)] == "lego_medium_azur").all()
    assert (g[ocean & (d > 3.0)] == "lego_bright_bluish_green").all()
    band = ocean & (d > 1.5) & (d <= 3.0)
    assert 0 < (g[band] == "lego_medium_azur").sum() < band.sum()
    assert int((g == "lego_earth_blue").sum()) == SHADOW_CELLS


def test_shadow_off_and_other_color(maps):
    text = load_recipe("ocean-sst").path.read_text(encoding="utf-8")
    off = build_map(parse_recipe(text + '\n[shadow]\nenabled = false\n'))
    assert off.report["shadow"]["cells"] == 0
    ocean = next(l for l in off.report["layers"] if l["class"] == "ocean")
    assert ocean["cells"] == 7178
    azur = parse_recipe(text.replace('"rank-to-supply"', '"quantile"') + '\n[shadow]\ncolor = "lego_medium_azur"\n')
    g = _grid(build_map(azur).layout)
    assert (g[shadow_mask(land_mask_array())] == "lego_medium_azur").all()


def test_check_prints_shadow(fixture_registry):
    from click.testing import CliRunner
    from lego_image_processor.cli.main import cli

    fixture_registry.place_all()
    res = CliRunner().invoke(cli, ["map", "check", "ocean-sst"])
    assert res.exit_code == 0, res.output
    assert "Land shadow (cast east): 392 cells of lego_earth_blue" in res.output
    res = CliRunner().invoke(cli, ["map", "check", "official-31203"])
    assert "Land shadow" not in res.output

"""Ice regions (feature 012, FR-003): rules, packaged data, arrangement roll."""

import json

import numpy as np
import pytest

from lego_image_processor.datasets.grid import SourceGrid
from lego_image_processor.layout.arrangement import parse_arrangement
from lego_image_processor.maps.build import land_mask_array
from lego_image_processor.maps.ice import (
    ICE_PATH, LAND_ICE_REGIONS, SEA_ICE_RULE, IceRegions, derive_ice_regions, in_region,
    land_ice_mask, load_ice_regions, parse_ice_regions, sea_ice_mask,
)
from lego_image_processor.maps.projection import load_kit_projection

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."


@pytest.fixture(scope="module")
def proj():
    return load_kit_projection()


@pytest.fixture(scope="module")
def land():
    return land_mask_array()


class TestRegions:
    def test_antarctica(self):
        ant = LAND_ICE_REGIONS[0]
        assert ant["name"] == "Antarctica"
        assert in_region(-75.0, 10.0, ant)
        assert not in_region(-50.0, 10.0, ant)

    def test_greenland_excludes_iceland(self):
        gl = LAND_ICE_REGIONS[1]
        assert gl["name"] == "Greenland"
        assert in_region(72.0, -40.0, gl)
        assert not in_region(65.0, -18.0, gl)      # Iceland
        assert in_region(65.0, -40.0, gl)          # south-east Greenland, west of the exclusion
        assert not in_region(72.0, 20.0, gl)       # Svalbard


class TestLandIce:
    def test_only_land_cells(self, land, proj):
        m = land_ice_mask(land, proj)
        assert m.shape == land.shape
        assert m.any()
        assert not (m & ~land).any()

    def test_bottom_rows_and_greenland(self, land, proj):
        m = land_ice_mask(land, proj)
        # every land cell of the southernmost row is Antarctica
        assert (m[-1] == land[-1]).all()
        lat, lon = proj.cell_center(8, 0)
        r, c = 8, int(((-40.0 - proj.left_edge_lon) % 360) // proj.deg_per_col)
        if land[r, c]:
            assert m[r, c]


class TestSeaIce:
    def _grid(self, values):
        lat = np.linspace(-89, 89, values.shape[0])
        lon = np.linspace(-179, 179, values.shape[1])
        return SourceGrid(values=values, lat=lat, lon=lon)

    def test_cold_or_unobserved_polar(self, land, proj):
        vals = np.full((90, 180), 10.0)
        vals[-3:, :] = -1.8          # near the north pole: frozen all year
        vals[:6, :] = np.nan         # far south (89-79° S): no value at all
        m = sea_ice_mask(self._grid(vals), land, proj)
        assert not (m & land).any()
        assert m[0][~land[0]].all()                  # row 0 (≈ 90° N) is frozen
        assert m[-1][~land[-1]].all()                # row 79: no value, poleward of 60°
        mid = proj.height // 2
        assert not m[mid].any()

    def test_threshold_is_inclusive(self, land, proj):
        vals = np.full((90, 180), SEA_ICE_RULE["max_value"])
        m = sea_ice_mask(self._grid(vals), land, proj)
        assert (m == ~land).all()

    def test_unobserved_equatorial_is_not_ice(self, land, proj):
        vals = np.full((90, 180), 20.0)
        vals[40:50, :] = np.nan
        m = sea_ice_mask(self._grid(vals), land, proj)
        # only the polar rows the source never reaches (row 0, beyond 89° N) are unobserved ice
        assert not m[1:].any()


class TestPackaged:
    def test_loads_and_agrees_with_mask(self, land):
        ice = load_ice_regions()
        assert isinstance(ice, IceRegions)
        assert ice.land.shape == (80, 128) and ice.sea.shape == (80, 128)
        assert not (ice.land & ~land).any()
        assert not (ice.sea & land).any()
        assert ice.land.sum() > 100 and ice.sea.sum() > 100

    def test_source_block(self):
        data = json.loads(ICE_PATH.read_text(encoding="utf-8"))
        src = data["source"]
        assert src["disclaimer"] == DISCLAIMER
        assert src["sea_ice"]["dataset"]["id"] == "ersst-v5-ltm-1991-2020"
        assert len(src["sea_ice"]["dataset"]["sha256"]) == 64
        assert src["generator"].startswith("cli/tools/kit31203 ice-mask")
        assert data["land_ice"]["count"] == len(data["land_ice"]["cells"])

    def test_land_ice_matches_rule(self, land, proj):
        assert (load_ice_regions().land == land_ice_mask(land, proj)).all()

    def test_rejects_cells_on_wrong_class(self):
        data = json.loads(ICE_PATH.read_text(encoding="utf-8"))
        bad = dict(data, sea_ice=dict(data["sea_ice"], cells=data["sea_ice"]["cells"] + [data["land_ice"]["cells"][0]],
                                      count=data["sea_ice"]["count"] + 1))
        with pytest.raises(ValueError, match="sea_ice"):
            parse_ice_regions(bad)

    def test_rolled(self):
        ice = load_ice_regions()
        b = parse_arrangement("B")
        r = ice.rolled(b)
        assert (r.land == b.roll(ice.land)).all() and (r.sea == b.roll(ice.sea)).all()

    def test_derive_round_trip(self, land, proj):
        # derive_ice_regions with an all-warm field gives the land ice only
        grid = SourceGrid(values=np.full((90, 180), 25.0), lat=np.linspace(-89, 89, 90),
                          lon=np.linspace(-179, 179, 180))
        ice = derive_ice_regions(grid, land=land, projection=proj)
        assert (ice.land == land_ice_mask(land, proj)).all()
        assert not ice.sea[1:].any()     # row 0 (beyond 89° N) has no source value

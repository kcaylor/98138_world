"""Geographic rules on a non-kit template (T048; FR-008; spec Edge Cases; research R6).

No-data latitudes, region overrides (Antarctica, Greenland), dataset overrides (sea ice), the
land/ocean split of ``class_rule.land_from`` and the recipes' ice-sheet and sea-ice overrides use
each stud's own template location, so the same place gets the same rule on the kit and on Winkel.
Map builds never read ``maps/ice.py`` (template ice regions are for ``map cells``, Phase 6).
Not affiliated with or endorsed by The LEGO Group.
"""

import numpy as np
import pytest

from lego_image_processor.datasets.grid import SourceGrid
from lego_image_processor.maps.build import build_map
from lego_image_processor.maps.nodata import cell_latitudes, cell_max, no_data_cells
from lego_image_processor.maps.overrides import override_cells
from lego_image_processor.maps.projection import load_kit_projection
from lego_image_processor.maps.recipe import NoData, Override, Region, load_recipe
from lego_image_processor.maps.reproject import reproject_layer, source_cells
from lego_image_processor.templates import kit_template

KIT = load_kit_projection()


def _grid(step=1.0, fn=lambda lat, lon: lat + 0 * lon, **kw):
    lat = np.arange(-90 + step / 2, 90, step)
    lon = np.arange(-180 + step / 2, 180, step)
    return SourceGrid(values=fn(lat[:, None], lon[None, :]).astype(float), lat=lat, lon=lon, **kw)


def _stud(template, lat, lon):
    rc = template.stud_at(lat, lon)
    assert rc is not None, (lat, lon)
    return rc


@pytest.fixture
def w(confirmed_winkel):
    return confirmed_winkel


class TestNoData:
    def test_cell_latitudes_are_stud_locations(self, w):
        lats = cell_latitudes(w.grid_projection)
        lat, _ = w.locations()
        assert np.array_equal(lats, np.abs(lat), equal_nan=True)

    def test_unobserved_uses_each_studs_latitude(self, w):
        g = _grid(2.0, lambda lat, lon: np.where(np.abs(lat) > 70, np.nan, 1.0) + 0 * lon)
        mask = np.array(w.ocean)
        f = reproject_layer(g, w.grid_projection, mask, "ocean")
        nd = NoData("lego_white", "unobserved", 60.0)
        out = no_data_cells(nd, g, f, mask, w.grid_projection, "ocean")
        lat, _ = w.locations()
        assert (out == (mask & f.filled & (np.abs(np.nan_to_num(lat)) > 60))).all()
        assert out.any() and not (out & ~mask).any()
        # the same place, the same rule: well north of 70 the stud is no-data on both templates
        kf = reproject_layer(g, KIT, ~kit_template().land, "ocean")
        kout = no_data_cells(nd, g, kf, ~np.array(kit_template().land), KIT, "ocean")
        for place in ((85.0, 0.0), (-75.0, -150.0)):
            if w.class_at(*_stud(w, *place)) == "ocean" and kit_template().class_at(*_stud(kit_template(), *place)) == "ocean":
                assert out[_stud(w, *place)] and kout[_stud(kit_template(), *place)]

    def test_cell_max_bins_by_forward_projection(self, w):
        g = _grid(1.0, counts=None)
        counts = np.arange(g.values.size, dtype=float).reshape(g.values.shape)
        out = cell_max(g, counts, np.ones(g.values.shape, bool), w.grid_projection)
        cell = source_cells(g, w.grid_projection)
        expect = np.zeros(w.height * w.width)
        ok = cell >= 0
        np.maximum.at(expect, cell[ok], counts[ok])
        assert (out == expect.reshape(out.shape)).all()
        assert (out[~np.array(w.on_globe)] == 0).all()

    def test_share_rule_on_template_studs(self, w):
        g = _grid(1.0, lambda lat, lon: np.where(lat < -65, np.nan, 1.0) + 0 * lon)
        g.missing = ~np.isfinite(g.values)
        mask = np.array(w.land)
        f = reproject_layer(g, w.grid_projection, mask, "land")
        out = no_data_cells(NoData("lego_white", "share", 55.0, min_share=0.5), g, f, mask,
                            w.grid_projection, "land")
        lat, _ = w.locations()
        assert out.any() and not (out & ~mask).any()
        assert (np.nan_to_num(lat)[out] < -60).all()


class TestRegionOverrides:
    def _rainfall_land(self):
        return load_recipe("rainfall").land.overrides  # Antarctica, Greenland (without Iceland)

    def test_regions_use_stud_locations(self, w, fixture_registry):
        ovr = self._rainfall_land()
        mask = np.array(w.land)
        out = override_cells(ovr, mask, np.zeros_like(mask), w.grid_projection, "land")
        lat, lon = w.locations()
        ant = mask & (np.nan_to_num(lat) < -60)
        assert (out[0] == ant).all()
        grl = mask & ~ant & (np.nan_to_num(lat) > 59) & (np.nan_to_num(lon) > -75) & (np.nan_to_num(lon) < -10)
        grl &= ~((np.nan_to_num(lat) < 67) & (np.nan_to_num(lon) > -26))
        assert (out[1] == grl).all() and out[1].any()
        assert not (out[0] | out[1])[~np.array(w.on_globe)].any()

    def test_same_place_same_rule(self, w, fixture_registry):
        ovr = self._rainfall_land()
        kit = kit_template()
        wo = override_cells(ovr, np.array(w.land), np.zeros(w.land.shape, bool), w.grid_projection, "land")
        ko = override_cells(ovr, np.array(kit.land), np.zeros(kit.land.shape, bool), KIT, "land")
        for place, which in (((-80.0, 30.0), 0), ((72.0, -40.0), 1)):
            assert wo[which][_stud(w, *place)] and ko[which][_stud(kit, *place)]
        for place in ((64.9, -18.6), (48.9, 2.3)):  # Iceland is excluded; Paris is neither
            assert not any(o[_stud(w, *place)] for o in wo)
            assert not any(o[_stud(kit, *place)] for o in ko)

    def test_taken_studs_are_skipped(self, w):
        o = Override(name="south", color="lego_white", region=Region(lat_max=-60.0))
        mask = np.array(w.land)
        taken = np.zeros_like(mask)
        taken[70:, :] = True
        out = override_cells((o,), mask, taken, w.grid_projection, "land")[0]
        assert out.any() and not (out & taken).any()


class TestDatasetOverride:
    def test_sea_ice_uses_stud_locations(self, w, fixture_registry):
        fixture_registry.place_all()
        ovr = load_recipe("rainfall").ocean.overrides  # sea ice: NSIDC points, mean >= 0.7 or unobserved > 60
        mask = np.array(w.ocean)
        out = override_cells(ovr, mask, np.zeros_like(mask), w.grid_projection, "ocean")[0]
        assert out.any() and not (out & ~mask).any()
        lat, _ = w.locations()
        assert (np.abs(lat[out]) > 50).all()
        kit = kit_template()
        kout = override_cells(ovr, ~np.array(kit.land), np.zeros(kit.land.shape, bool), KIT, "ocean")[0]
        place = (88.0, 0.0)  # the Arctic Ocean near the pole: sea ice on both templates
        assert out[_stud(w, *place)] and kout[_stud(kit, *place)]


class TestLandFrom:
    def test_land_layer_takes_only_land_pixels(self, w, fixture_registry):
        """``class_rule.land_from`` splits source pixels in the reader; on a template the land
        studs still average land pixels only (living-planet's NPP takes its land from ETOPO 2022)."""
        from lego_image_processor.datasets.cache import resolve
        from lego_image_processor.datasets.readers import read_dataset

        fixture_registry.place_all()
        layer = load_recipe("living-planet").land
        assert layer.dataset.mask_dataset_id == "etopo2022-surface-10m"
        g = read_dataset(layer.dataset, resolve(layer.dataset), layer.variable, transform=layer.transform)
        assert g.land is not None and g.land.any() and not g.land.all()
        mask = np.array(w.land)
        f = reproject_layer(g, w.grid_projection, mask, "land")
        land_only = SourceGrid(values=np.where(g.land, g.values, np.nan), lat=g.lat, lon=g.lon)
        f2 = reproject_layer(land_only, w.grid_projection, mask, "land")
        assert np.array_equal(f.values, f2.values, equal_nan=True)
        assert (f.samples == f2.samples).all()


class TestBuilds:
    def test_rainfall_ice_on_template_locations(self, w, fixture_registry):
        """The recipe's ice-sheet overrides (Antarctica, Greenland) and sea ice on Winkel."""
        fixture_registry.place_all()
        r = build_map(load_recipe("rainfall"), template="winkel-tripel")
        lat, lon = w.locations()
        white_land = np.zeros(w.land.shape, bool)
        for p in r.layout.positions:
            if p.part_type == "plate" and p.color_id == "lego_white":
                white_land[p.y, p.x] = True
        assert (white_land[np.array(w.land) & (np.nan_to_num(lat) < -60)]).all()
        land_report = r.report["layers"][0]
        assert [o["name"] for o in land_report["overrides"]] == ["Antarctica", "Greenland"]
        assert all(o["cells"] > 0 for o in land_report["overrides"])
        assert r.report["layers"][1]["overrides"][0]["cells"] > 0

    def test_living_planet_no_data_rules(self, w, fixture_registry):
        """The existing no-data rules apply to studs without data (spec Edge Cases)."""
        fixture_registry.place_all()
        r = build_map(load_recipe("living-planet"), template="winkel-tripel")
        lat, _ = w.locations()
        ocean = r.report["layers"][1]
        assert ocean["no_data"]["cells"] > 0
        for p in r.layout.positions:
            if p.part_type == "tile" and p.color_id == "lego_white":
                assert abs(lat[p.y, p.x]) > 60  # ocean no-data poleward of min_lat only

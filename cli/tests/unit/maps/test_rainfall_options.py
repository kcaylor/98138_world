"""Recipe options of feature 013: sampling, overrides and legend (FR-004-FR-006; contract
specs/013-rainfall/contracts/recipe-and-datasets.md).

Not affiliated with or endorsed by The LEGO Group.
"""

import numpy as np
import pytest

from lego_image_processor.datasets.grid import SourceGrid
from lego_image_processor.layout.arrangement import parse_arrangement
from lego_image_processor.maps.build import build_map, land_mask_array, override_class
from lego_image_processor.maps.overrides import override_cells
from lego_image_processor.maps.projection import load_kit_projection
from lego_image_processor.maps.recipe import Override, Region, RecipeError, load_recipe, parse_recipe
from lego_image_processor.maps.reproject import bilinear, cell_centres, cell_means, reproject_layer
from lego_image_processor.maps.texture import shadow_mask

PROJ = load_kit_projection()
LAND = land_mask_array()
LAT, LON = cell_centres(PROJ)

BASE = """
format = "1"
id = "test-013"
title = "T"
[land]
role = "data"
dataset = "gpcp-v23-ltm-1991-2020"
variable = "precip"
colors = ["lego_brick_yellow", "lego_dark_green"]
{land_extra}
[land.classification]
method = "bins"
bounds = [0, 1, 1000]
{land_tables}
[ocean]
role = "background"
colors = ["lego_earth_blue"]
"""


def _recipe(land_extra="", land_tables=""):
    return parse_recipe(BASE.format(land_extra=land_extra, land_tables=land_tables))


class TestRecipe:
    def test_defaults_unchanged(self):
        r = _recipe()
        assert r.land.sampling == "mean" and r.land.overrides == () and r.land.legend is None

    def test_sampling(self):
        assert _recipe('sampling = "bilinear"').land.sampling == "bilinear"
        with pytest.raises(RecipeError, match="land.sampling: must be one of mean, bilinear"):
            _recipe('sampling = "cubic"')

    def test_bilinear_not_categorical(self):
        text = BASE.format(land_extra='sampling = "bilinear"', land_tables="").replace(
            'method = "bins"\nbounds = [0, 1, 1000]',
            'method = "categorical"\ncategories = {a = "lego_brick_yellow", b = "lego_dark_green"}')
        with pytest.raises(RecipeError, match="bilinear needs ordered"):
            parse_recipe(text)

    def test_region_and_dataset_overrides(self):
        r = _recipe(land_tables="""
[[land.override]]
name = "polar"
color = "lego_white"
lat_max = -60
exclude = [{ lon_min = 0, lon_max = 10 }]
[[land.override]]
name = "ice"
color = "lego_white"
dataset = "nsidc-cdr-v6-seaice-minimum-1991-2020"
variable = "cdr_seaice_conc_monthly"
min_value = 0.5
unobserved_lat = 70
""")
        a, b = r.land.overrides
        assert a.kind == "region" and a.region == Region(lat_max=-60.0) and a.exclude == (Region(lon_min=0.0, lon_max=10.0),)
        assert b.kind == "dataset" and b.min_value == 0.5 and b.unobserved_lat == 70
        ids = [e.id for e in r.datasets()]
        assert ids == ["gpcp-v23-ltm-1991-2020", "nsidc-cdr-v6-seaice-minimum-1991-2020"]
        assert a.provenance(3) == {"name": "polar", "kind": "region", "color": "lego_white",
                                   "region": {"lat_max": -60.0},
                                   "exclude": [{"lon_min": 0.0, "lon_max": 10.0}], "cells": 3}

    @pytest.mark.parametrize("table,match", [
        ('name = "a"\ncolor = "lego_white"', "either region bounds"),
        ('name = "a"\ncolor = "lego_white"\nlat_max = 1\ndataset = "gpcp-v23-ltm-1991-2020"', "not both"),
        ('color = "lego_white"\nlat_max = 1', r"override\[0\].name: is required"),
        ('name = "a"\nlat_max = 1', "color: is required"),
        ('name = "a"\ncolor = "lego_light_royal_blue"\nlat_max = 1', "not a color of the land part"),
        ('name = "a"\ncolor = "lego_white"\nlat_max = 100', "between -90 and 90"),
        ('name = "a"\ncolor = "lego_white"\nlon_min = 10\nlon_max = 5', "lon_min: must be below lon_max"),
        ('name = "a"\ncolor = "lego_white"\nlat_max = 1\nexclude = [{}]', "exclude\\[0\\]: needs at least one"),
        ('name = "a"\ncolor = "lego_white"\nlat_max = 1\nshape = "x"', "unknown key"),
        ('name = "a"\ncolor = "lego_white"\ndataset = "nope"\nvariable = "v"\nmin_value = 1', "unknown dataset"),
        ('name = "a"\ncolor = "lego_white"\ndataset = "gpcp-v23-ltm-1991-2020"\nvariable = "v"\nmin_value = 1',
         "has no variable"),
        ('name = "a"\ncolor = "lego_white"\ndataset = "gpcp-v23-ltm-1991-2020"\nvariable = "precip"',
         "min_value: is required"),
        ('name = "a"\ncolor = "lego_white"\ndataset = "kit31203-design"\nvariable = "color"\nmin_value = 1',
         "categorical"),
        ('name = "a"\ncolor = "lego_white"\ndataset = "gpcp-v23-ltm-1991-2020"\nvariable = "precip"\n'
         'min_value = 1\nunobserved_lat = 95', "between 0 and 90"),
        ('name = "a"\ncolor = "lego_white"\ndataset = "gpcp-v23-ltm-1991-2020"\nvariable = "precip"\n'
         'min_value = 1\nexclude = [{lat_max = 1}]', "region overrides only"),
    ])
    def test_override_rules(self, table, match):
        with pytest.raises(RecipeError, match=match):
            _recipe(land_tables=f"[[land.override]]\n{table}\n")

    def test_duplicate_override_names(self):
        t = '[[land.override]]\nname = "a"\ncolor = "lego_white"\nlat_max = 1\n'
        with pytest.raises(RecipeError, match="duplicate override name"):
            _recipe(land_tables=t + t)

    def test_legend(self):
        assert _recipe(land_tables='[land.legend]\nunits = "mm/yr"\nfactor = 365\n').land.legend.to_dict() == {
            "units": "mm/yr", "factor": 365.0}
        for t, m in (('units = "x"', "factor: is required"), ('units = "x"\nfactor = 0', "must be > 0"),
                     ('factor = 2', "units: is required"), ('units = "x"\nfactor = 2\nscale = 1', "unknown key")):
            with pytest.raises(RecipeError, match=m):
                _recipe(land_tables=f"[land.legend]\n{t}\n")

    def test_background_rejects_new_keys(self):
        text = BASE.format(land_extra="", land_tables="") + 'sampling = "bilinear"\n'
        with pytest.raises(RecipeError, match="ocean.sampling: a background layer"):
            parse_recipe(text)


def _grid(values, lat, lon, land=None):
    return SourceGrid(values=np.asarray(values, dtype=float), lat=np.asarray(lat, float),
                      lon=np.asarray(lon, float), land=land)


class TestBilinear:
    lat = -88.75 + 2.5 * np.arange(72)
    lon = -178.75 + 2.5 * np.arange(144)

    def test_exact_on_a_linear_field_and_clamped(self):
        v = np.repeat(self.lat[:, None], 144, axis=1)          # value = latitude
        vals, have = bilinear(_grid(v, self.lat, self.lon), PROJ)
        assert have.all()
        inside = np.abs(LAT) <= 88.75
        assert np.allclose(vals[inside], LAT[inside])
        assert np.allclose(vals[LAT > 88.75], 88.75) and np.allclose(vals[LAT < -88.75], -88.75)

    def test_periodic_in_longitude(self):
        lon = -178.0 + 2.5 * np.arange(144)                    # last column 179.5
        f = np.sin(np.radians(lon))
        vals, _ = bilinear(_grid(np.repeat(f[None, :], 72, axis=0), self.lat, lon), PROJ)
        assert np.allclose(vals, np.sin(np.radians(LON)), atol=1e-3)
        # a cell centre west of the first column wraps to the last one, across the date line
        col = int(np.argmin(LON[0]))
        assert LON[0, col] < lon[0]
        t = (LON[0, col] + 360 - lon[-1]) / 2.5
        assert vals[40, col] == pytest.approx((1 - t) * f[-1] + t * f[0])

    def test_missing_corners_are_dropped(self):
        v = np.ones((72, 144))
        v[:, ::2] = np.nan
        vals, have = bilinear(_grid(v, self.lat, self.lon), PROJ)
        assert have.all() and np.allclose(vals, 1.0)
        none = np.full((72, 144), np.nan)
        _, have = bilinear(_grid(none, self.lat, self.lon), PROJ)
        assert not have.any()

    def test_class_corners_only(self):
        land = np.zeros((72, 144), bool)
        land[:, :72] = True
        v = np.where(land, 5.0, 1.0)
        vals, have = bilinear(_grid(v, self.lat, self.lon, land=land), PROJ, "ocean")
        assert np.allclose(vals[have], 1.0)

    def test_errors(self):
        with pytest.raises(ValueError, match="regular latitude/longitude grid"):
            bilinear(SourceGrid(values=np.zeros(3), lat=np.zeros(3), lon=np.zeros(3), points=True), PROJ)
        with pytest.raises(ValueError, match="evenly spaced"):
            bilinear(_grid(np.zeros((3, 144)), [0, 1, 3], self.lon), PROJ)
        with pytest.raises(ValueError, match="global longitude"):
            bilinear(_grid(np.zeros((72, 10)), self.lat, np.arange(10.0)), PROJ)

    def test_reproject_bilinear_keeps_samples_and_fills_nothing(self):
        v = np.repeat(self.lat[:, None], 144, axis=1)
        g = _grid(v, self.lat, self.lon)
        mean = reproject_layer(g, PROJ, ~LAND, "ocean")
        bil = reproject_layer(g, PROJ, ~LAND, "ocean", sampling="bilinear")
        assert np.array_equal(mean.samples, bil.samples) and mean.variance_lost == bil.variance_lost
        assert mean.filled.any() and not bil.filled.any()       # 2.5 degree rows skip some kit rows
        with pytest.raises(ValueError, match="unknown sampling"):
            reproject_layer(g, PROJ, ~LAND, "ocean", sampling="nearest")


class TestCellMeansAndOverrides:
    def test_points_cell_means(self):
        lat0, lon0 = LAT[10, 20], LON[10, 20]
        g = SourceGrid(values=np.array([1.0, 3.0, np.nan]), lat=np.array([lat0, lat0, lat0]),
                       lon=np.array([lon0, lon0, lon0]), points=True)
        mean, n = cell_means(g, PROJ)
        assert n[10, 20] == 2 and mean[10, 20] == 2.0 and n.sum() == 2 and np.isnan(mean[0, 0])

    def test_region_order_and_taken(self):
        mask = LAND.copy()
        taken = np.zeros_like(mask)
        taken[LAT < -80] = True
        o1 = Override(name="a", color="lego_white", region=Region(lat_max=-60))
        o2 = Override(name="b", color="lego_white", region=Region(lat_max=-50),
                      exclude=(Region(lon_min=0),))
        c1, c2 = override_cells([o1, o2], mask, taken, PROJ, "land")
        assert (LAT[c1] < -60).all() and (LAT[c1] >= -80).all() and not (c1 & taken).any()
        assert not (c1 & c2).any() and (LAT[c2] < -50).all() and (LON[c2] <= 0).all()
        assert (mask[c1 | c2]).all()


@pytest.fixture
def placed(fixture_registry):
    return fixture_registry.place_all()


def test_dataset_override_rule(placed):
    from lego_image_processor.datasets import get_entry

    o = Override(name="ice", color="lego_white", dataset=get_entry("nsidc-cdr-v6-seaice-minimum-1991-2020"),
                 variable="cdr_seaice_conc_monthly", min_value=0.7, unobserved_lat=60)
    ocean = ~LAND & ~shadow_mask(LAND)
    (cells,) = override_cells([o], ocean, np.zeros_like(ocean), PROJ, "ocean")
    assert cells.any() and (np.abs(LAT[cells]) > 40).all() and not (cells & ~ocean).any()
    o_strict = Override(name="ice", color="lego_white", dataset=o.dataset, variable=o.variable, min_value=2.0)
    (none,) = override_cells([o_strict], ocean, np.zeros_like(ocean), PROJ, "ocean")
    assert not none.any()                                      # concentration never reaches 2


def test_build_rainfall_arrangement_b_is_a_rolled(placed):
    r = load_recipe("rainfall")
    a = build_map(r)
    b = build_map(r, arrangement=parse_arrangement("B"))
    arr = parse_arrangement("B")
    for cls in ("land", "ocean"):
        ca, cb = a.classes[cls], b.classes[cls]
        layer_a = LAND if cls == "land" else ~LAND & ~shadow_mask(LAND)
        # per-cell classes and overrides equal A's rolled, away from the shadow (it is recomputed)
        rolled = arr.roll(np.where(layer_a, ca, -99))
        layer_b = arr.roll(LAND) if cls == "land" else ~arr.roll(LAND) & ~shadow_mask(arr.roll(LAND))
        both = layer_b & (rolled != -99)
        assert np.array_equal(cb[both], rolled[both])
    assert (a.classes["land"] == override_class(0)).any() and (a.classes["ocean"] == override_class(0)).any()

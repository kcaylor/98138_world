"""No-data rules on the kit grid and in the build (feature 012, FR-008, FR-009; research R5).

Not affiliated with or endorsed by The LEGO Group.
"""

import hashlib

import numpy as np
import pytest

from lego_image_processor.datasets.grid import SourceGrid
from lego_image_processor.layout.arrangement import parse_arrangement
from lego_image_processor.maps.build import NO_DATA_CLASS, build_map, land_mask_array
from lego_image_processor.maps.classify import MapBuildError
from lego_image_processor.maps.nodata import apply_value, cell_latitudes, no_data_cells
from lego_image_processor.maps.projection import load_kit_projection
from lego_image_processor.maps.recipe import NoData, parse_recipe
from lego_image_processor.maps.reproject import reproject_layer

PROJ = load_kit_projection()
LAND = land_mask_array()
LATS = cell_latitudes(PROJ)


def _grid(values, land=None, counts=None):
    lat = -89.5 + np.arange(180)
    lon = -179.5 + np.arange(360)
    return SourceGrid(values=values, lat=lat, lon=lon, land=land, counts=counts)


def _lat2d():
    return np.repeat((-89.5 + np.arange(180))[:, None], 360, axis=1)


class TestRules:
    def test_apply_value_fills_only_class_pixels(self):
        lat = _lat2d()
        land = lat > 0
        v = np.where(lat > 45, np.nan, 1.0)
        g = apply_value(_grid(v, land=land), NoData("lego_white", "share", 55, value=0.0, min_share=0.5), "land")
        assert (g.values[lat > 45] == 0).all()               # northern land: filled
        assert g.missing.sum() == ((lat > 45) & land).sum()
        g2 = apply_value(_grid(v.copy(), land=land), None, "land")
        assert np.isnan(g2.values[lat > 45]).all() and g2.missing.any()

    def test_unobserved_is_filled_and_poleward(self):
        lat = _lat2d()
        g = _grid(np.where(np.abs(lat) < 50, 1.0, np.nan))
        ocean = ~LAND
        fld = reproject_layer(g, PROJ, ocean, "ocean")
        nd = no_data_cells(NoData("lego_white", "unobserved", 60), g, fld, ocean, PROJ, "ocean")
        assert nd.any()
        assert (LATS[nd] > 60).all() and (fld.filled[nd]).all()
        # filled cells between 50 and 60 degrees are not no-data: nearest fill as before
        assert (fld.filled & ocean & (LATS > 52) & (LATS <= 60) & ~nd).any()

    def test_sparse_steps(self):
        lat = _lat2d()
        counts = np.where(np.abs(lat) > 75, 3, 100)
        g = _grid(np.ones((180, 360)), counts=counts)
        ocean = ~LAND
        fld = reproject_layer(g, PROJ, ocean, "ocean")
        nd = no_data_cells(NoData("lego_white", "unobserved", 60, sparse_lat=70, min_steps=12), g, fld,
                           ocean, PROJ, "ocean")
        assert nd.any() and (LATS[nd] > 70).all()
        assert (nd & ~fld.filled).any()  # observed but sparse cells count too
        g.counts = None
        with pytest.raises(ValueError, match="valid-step counts"):
            no_data_cells(NoData("lego_white", "unobserved", 60, sparse_lat=70, min_steps=12), g, fld,
                          ocean, PROJ, "ocean")

    def test_share_counts_missing_poleward_class_pixels(self):
        lat = _lat2d()
        land = np.ones((180, 360), bool)
        v = np.where(lat > 50, np.nan, 5.0)          # everything north of 50 lacks a value
        nd_rule = NoData("lego_white", "share", 55, value=0.0, min_share=0.5)
        g = apply_value(_grid(v, land=land), nd_rule, "land")
        fld = reproject_layer(g, PROJ, LAND, "land")
        nd = no_data_cells(nd_rule, g, fld, LAND, PROJ, "land")
        assert nd.any() and (LATS[nd] > 52).all() and (lat[0, 0] < 0)
        # southern hemisphere land has values: never no-data
        south = np.zeros_like(LAND)
        south[PROJ.height // 2 + 5:] = True
        assert not (nd & south).any()

    def test_no_rule(self):
        g = _grid(np.ones((180, 360)))
        fld = reproject_layer(g, PROJ, LAND, "land")
        assert not no_data_cells(None, g, fld, LAND, PROJ, "land").any()


# --- through build_map, with a local .npy ocean layer: NaN north of 50N (never observed) -------

def _npy(tmp_path):
    lat = _lat2d()
    a = np.where(lat > 50, np.nan, np.where(lat > 0, -100.0, -10.0))  # all <= split_at: ocean
    f = tmp_path / "v.npy"
    np.save(f, a)
    return f, hashlib.sha256(f.read_bytes()).hexdigest()


def _recipe(tmp_path, no_data=True, shadow=""):
    f, sha = _npy(tmp_path)
    table = '[ocean.no_data]\ncolor = "lego_white"\nrule = "unobserved"\nmin_lat = 55\n' if no_data else ""
    return parse_recipe(f'''format = "1"
id = "nd-test"
title = "No data"
[land]
role = "background"
colors = ["lego_white"]
[ocean]
role = "data"
colors = ["lego_earth_blue", "lego_medium_azur"]
[ocean.local]
path = "{f}"
format = "npy"
sha256 = "{sha}"
variable = "v"
citation = "c"
license = "l"
lat = [-90, 90]
lon = [-180, 180]
split_at = 0
[ocean.classification]
method = "bins"
bounds = [-1000, -50, 0]
{table}
{shadow}
''')


class TestBuild:
    def test_cells_color_supply_and_provenance(self, tmp_path):
        r = build_map(_recipe(tmp_path))
        nd = r.classes["ocean"] == NO_DATA_CLASS
        assert nd.any() and not (nd & LAND).any() and (LATS[nd] > 55).all()
        colors = {(p.y, p.x): p.color_id for p in r.layout.positions}
        assert all(colors[(y, x)] == "lego_white" for y, x in zip(*np.nonzero(nd)))
        shadow = np.array([[colors[(y, x)] == "lego_earth_blue" for x in range(128)] for y in range(80)])
        rep = r.report["layers"][1]
        n = int(nd.sum())
        assert rep["no_data"] == {"rule": "unobserved", "color": "lego_white", "min_lat": 55.0, "cells": n}
        assert rep["cells"] == int((~LAND).sum()) - n - r.report["shadow"]["cells"]
        white = next(row for row in rep["supply"] if row["key"] == "lego_white")
        assert white["used"] == n and not white["in_kit"]
        assert r.layout.map_metadata["layers"][1]["no_data"]["cells"] == n
        # the shadow wins: no shadow cell is no-data
        sh = r.report["shadow"]["cells"]
        assert sh > 0 and shadow.sum() >= sh

    def test_without_rule_unchanged(self, tmp_path):
        r = build_map(_recipe(tmp_path, no_data=False))
        assert not (r.classes["ocean"] == NO_DATA_CLASS).any()
        assert "no_data" not in r.report["layers"][1]
        assert "no_data" not in r.layout.map_metadata["layers"][1]
        assert r.report["layers"][1]["filled_cells"] > 0

    def test_arrangement_b_is_a_rolled(self, tmp_path):
        rec = _recipe(tmp_path, shadow="[shadow]\nenabled = false")
        a = build_map(rec)
        b = build_map(rec, arrangement=parse_arrangement("B"))
        arr = parse_arrangement("B")
        assert np.array_equal(arr.roll(a.classes["ocean"] == NO_DATA_CLASS), b.classes["ocean"] == NO_DATA_CLASS)

    def test_rule_leaving_no_cells(self, tmp_path, monkeypatch):
        import lego_image_processor.maps.build as build

        monkeypatch.setattr(build, "no_data_cells", lambda rule, grid, fld, mask, *a: mask.copy())
        with pytest.raises(MapBuildError, match="no cells to classify"):
            build_map(_recipe(tmp_path))

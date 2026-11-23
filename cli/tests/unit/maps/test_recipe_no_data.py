"""Recipe keys of feature 012: transform = "log10" and the [<layer>.no_data] table (FR-007, FR-008;
contracts/recipe-and-datasets.md)."""

import math

import pytest

from lego_image_processor.maps.recipe import NoData, RecipeError, load_recipe, parse_recipe

HEAD = 'format = "1"\nid = "tt"\ntitle = "T"\n'
WHITE_LAND = '[land]\nrole = "background"\ncolors = ["lego_white"]\n'
OCEAN = '''[ocean]
role = "data"
dataset = "modis-aqua-chla-2013-2024"
variable = "chlor_a"
transform = "log10"
colors = ["lego_bright_blue", "lego_dark_azur"]
[ocean.classification]
method = "bins"
bounds = [0.001, 0.1, 100]
'''
NPP = '''[land]
role = "data"
dataset = "mod17a3-npp-mean-2000-2015"
variable = "npp"
colors = ["lego_brick_yellow", "lego_dark_green"]
[land.classification]
method = "bins"
bounds = [0, 500, 1e9]
'''
WATER = '[ocean]\nrole = "background"\ncolors = ["lego_bright_bluish_green"]\n'


def _ocean(extra=""):
    return parse_recipe(HEAD + WHITE_LAND + OCEAN + extra)


def _land(extra=""):
    return parse_recipe(HEAD + NPP + extra + WATER)


def _err(text):
    with pytest.raises(RecipeError) as e:
        parse_recipe(text)
    return e.value


class TestLog10:
    def test_bounds_in_data_units_compared_on_log10(self):
        r = _ocean()
        assert r.ocean.transform == "log10"
        assert r.ocean.classification.bounds == pytest.approx((-3.0, -1.0, 2.0))

    def test_non_positive_bound(self):
        e = _err(HEAD + WHITE_LAND + OCEAN.replace("[0.001, 0.1, 100]", "[0, 0.1, 100]"))
        assert e.path == "ocean.classification.bounds[0]" and "log10" in e.rule

    def test_unknown_transform(self):
        e = _err(HEAD + WHITE_LAND + OCEAN.replace('"log10"', '"ln"'))
        assert e.path == "ocean.transform" and "log10" in e.rule


class TestNoDataOcean:
    TABLE = '[ocean.no_data]\ncolor = "lego_white"\nrule = "unobserved"\nmin_lat = 60\n'

    def test_unobserved(self):
        nd = _ocean(self.TABLE).ocean.no_data
        assert nd == NoData(color="lego_white", rule="unobserved", min_lat=60.0)
        assert nd.provenance(5) == {"rule": "unobserved", "color": "lego_white", "min_lat": 60.0, "cells": 5}

    def test_sparse(self):
        nd = _ocean(self.TABLE + "sparse_lat = 70\nmin_steps = 12\n").ocean.no_data
        assert (nd.sparse_lat, nd.min_steps) == (70.0, 12)

    @pytest.mark.parametrize("extra,path", [
        ("sparse_lat = 70\n", "ocean.no_data.min_steps"),
        ("min_steps = 12\n", "ocean.no_data.sparse_lat"),
        ("sparse_lat = 50\nmin_steps = 12\n", "ocean.no_data.sparse_lat"),
        ("sparse_lat = 70\nmin_steps = 0\n", "ocean.no_data.min_steps"),
        ("sparse_lat = 70\nmin_steps = 1.5\n", "ocean.no_data.min_steps"),
        ("min_share = 0.5\n", "ocean.no_data.min_share"),
        ("bogus = 1\n", "ocean.no_data.bogus"),
    ])
    def test_bad_keys(self, extra, path):
        assert _err(HEAD + WHITE_LAND + OCEAN + self.TABLE + extra).path == path

    @pytest.mark.parametrize("table,path", [
        ('[ocean.no_data]\nrule = "unobserved"\nmin_lat = 60\n', "ocean.no_data.color"),
        ('[ocean.no_data]\ncolor = "lego_white"\nmin_lat = 60\n', "ocean.no_data.rule"),
        ('[ocean.no_data]\ncolor = "lego_white"\nrule = "x"\nmin_lat = 60\n', "ocean.no_data.rule"),
        ('[ocean.no_data]\ncolor = "lego_white"\nrule = "unobserved"\n', "ocean.no_data.min_lat"),
        ('[ocean.no_data]\ncolor = "lego_white"\nrule = "unobserved"\nmin_lat = 95\n', "ocean.no_data.min_lat"),
        ('[ocean.no_data]\ncolor = "lego_nope"\nrule = "unobserved"\nmin_lat = 60\n', "ocean.no_data.color"),
        ('[ocean.no_data]\ncolor = 3\nrule = "unobserved"\nmin_lat = 60\n', "ocean.no_data.color"),
        ('[ocean.no_data]\ncolor = "lego_white"\nrule = "unobserved"\nmin_lat = 60\nvalue = 0\n',
         "ocean.no_data.value"),  # the ERDDAP file does not split land and ocean
    ])
    def test_bad_tables(self, table, path):
        assert _err(HEAD + WHITE_LAND + OCEAN + table).path == path

    def test_min_steps_needs_climatology_mean(self):
        text = (HEAD + WHITE_LAND + OCEAN.replace("modis-aqua-chla-2013-2024", "ersst-v5-1997-12")
                .replace('"chlor_a"', '"ssta"').replace('transform = "log10"\n', "")
                .replace("[0.001, 0.1, 100]", "[-9, 0, 9]") + self.TABLE + "sparse_lat = 70\nmin_steps = 2\n")
        e = _err(text)
        assert e.path == "ocean.no_data.min_steps" and "climatology-mean" in e.rule

    def test_background_layer_rejects_no_data(self):
        text = HEAD + WHITE_LAND + '[land.no_data]\ncolor = "lego_white"\nrule = "share"\nmin_lat = 1\nmin_share = 0.5\n' + WATER
        assert _err(text).path == "land.no_data"


class TestNoDataLand:
    TABLE = '[land.no_data]\nvalue = 0\ncolor = "lego_white"\nrule = "share"\nmin_lat = 55\nmin_share = 0.5\n'

    def test_share(self):
        nd = _land(self.TABLE).land.no_data
        assert nd == NoData(color="lego_white", rule="share", min_lat=55.0, value=0.0, min_share=0.5)

    @pytest.mark.parametrize("old,new,path", [
        ("min_share = 0.5\n", "", "land.no_data.min_share"),
        ("min_share = 0.5", "min_share = 1.0", "land.no_data.min_share"),
        ("min_share = 0.5", "min_share = 0.5\nmin_steps = 3", "land.no_data.min_steps"),
        ('color = "lego_white"', 'color = "lego_dark_azur"', "land.no_data.color"),  # not a 6141 color
    ])
    def test_bad(self, old, new, path):
        assert _err(HEAD + NPP + self.TABLE.replace(old, new) + WATER).path == path

    def test_value_needs_a_land_ocean_split(self, tmp_path):
        import hashlib

        import numpy as np

        f = tmp_path / "v.npy"
        np.save(f, np.zeros((2, 2)))
        sha = hashlib.sha256(f.read_bytes()).hexdigest()
        local = f'''[land]
role = "data"
colors = ["lego_brick_yellow", "lego_dark_green"]
[land.local]
path = "{f}"
format = "npy"
sha256 = "{sha}"
variable = "v"
citation = "c"
license = "l"
lat = [-90, 90]
lon = [-180, 180]
[land.classification]
method = "bins"
bounds = [0, 1, 2]
'''
        e = _err(HEAD + local + self.TABLE + WATER)
        assert e.path == "land.no_data.value"
        ok = local.replace('lon = [-180, 180]', 'lon = [-180, 180]\nsplit_at = 0')
        assert parse_recipe(HEAD + ok + self.TABLE + WATER).land.no_data.value == 0.0


def test_recipe_datasets_include_the_land_mask():
    r = _land()
    assert [e.id for e in r.datasets()] == ["mod17a3-npp-mean-2000-2015", "etopo2022-surface-10m"]


def test_bundled_living_planet():
    r = load_recipe("living-planet")
    assert r.land.no_data.rule == "share" and r.ocean.no_data.rule == "unobserved"
    assert r.ocean.no_data.sparse_lat == 70 and r.ocean.no_data.min_steps == 12
    assert r.shadow.color == "lego_black" and r.arrangement is None
    assert r.land.texture.kind == "blend" and r.land.texture.width == 0.25
    assert r.ocean.texture.kind == "none"
    assert r.ocean.classification.bounds[1] == pytest.approx(math.log10(0.08))
    assert [e.id for e in r.datasets()] == ["mod17a3-npp-mean-2000-2015", "etopo2022-surface-10m",
                                            "modis-aqua-chla-2013-2024"]


def test_value_with_log10_must_be_positive(tmp_path):
    import hashlib

    import numpy as np

    f = tmp_path / "c.npy"
    np.save(f, np.ones((2, 2)))
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    text = HEAD + WHITE_LAND + f'''[ocean]
role = "data"
transform = "log10"
colors = ["lego_bright_blue", "lego_dark_azur"]
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
bounds = [0.01, 1, 100]
[ocean.no_data]
color = "lego_white"
rule = "unobserved"
min_lat = 60
value = 0
'''
    assert _err(text).path == "ocean.no_data.value"
    assert parse_recipe(text.replace("value = 0", "value = 0.5")).ocean.no_data.value == 0.5

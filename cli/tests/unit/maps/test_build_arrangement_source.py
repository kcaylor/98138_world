"""Arrangement precedence: option > recipe > default (feature 009, FR-011, FR-012;
data-model.md ArrangementResolution; contracts/recipe-arrangement.md).

Recipes here have background layers only, so no dataset is needed. Not affiliated with or
endorsed by The LEGO Group.
"""

import hashlib
import json

import pytest

from lego_image_processor.layout.arrangement import parse_arrangement
from lego_image_processor.maps.build import build_map, check_recipe, resolve_arrangement
from lego_image_processor.maps.classify import MapBuildError
from lego_image_processor.maps.recipe import parse_recipe

BG = """
format = "1"
id = "bg-map"
title = "Background"
{arrangement}

[land]
role = "background"
colors = ["lego_white"]
weights = [1]

[ocean]
role = "background"
colors = ["lego_medium_azur"]
weights = [1]
"""


def _recipe(arrangement_line=""):
    return parse_recipe(BG.format(arrangement=arrangement_line))


def _layout_json(result):
    d = json.loads(result.layout.to_json())
    d.get("metadata", {}).pop("generated_at", None)
    d.pop("generated_at", None)
    return d


class TestResolve:
    def test_recipe(self):
        a, src = resolve_arrangement(_recipe('arrangement = "B"'))
        assert (a.id, src) == ("B", "recipe")

    def test_option_wins(self):
        a, src = resolve_arrangement(_recipe('arrangement = "B"'), parse_arrangement("A"))
        assert (a.id, src) == ("A", "option")

    def test_default(self):
        a, src = resolve_arrangement(_recipe())
        assert (a.id, src) == ("A", "default")


class TestBuild:
    def test_recipe_arrangement_used(self):
        r = build_map(_recipe('arrangement = "B"'))
        assert r.report["arrangement"]["id"] == "B"
        assert r.report["arrangement_source"] == "recipe"
        assert r.layout.arrangement["id"] == "B"

    def test_option_overrides_recipe(self):
        r = build_map(_recipe('arrangement = "B"'), arrangement=parse_arrangement("C"))
        assert r.report["arrangement"]["id"] == "C"
        assert r.report["arrangement_source"] == "option"
        assert r.layout.arrangement["id"] == "C"

    def test_default(self):
        r = build_map(_recipe())
        assert r.report["arrangement"]["id"] == "A"
        assert r.report["arrangement_source"] == "default"

    def test_check_recipe_reports_source(self):
        rep = check_recipe(_recipe('arrangement = "B"'))
        assert rep["arrangement"]["id"] == "B" and rep["arrangement_source"] == "recipe"
        rep = check_recipe(_recipe('arrangement = "B"'), arrangement=parse_arrangement("A"))
        assert rep["arrangement"]["id"] == "A" and rep["arrangement_source"] == "option"

    def test_no_key_equals_explicit_a(self):
        """SC-006: a recipe without the key builds exactly as before (explicit A)."""
        implicit = build_map(_recipe())
        explicit = build_map(_recipe(), arrangement=parse_arrangement("A"))
        assert _layout_json(implicit) == _layout_json(explicit)


def test_netcdf4_local_file_is_a_build_error(tmp_path):
    p = tmp_path / "month.nc"
    p.write_bytes(b"\x89HDF\r\n\x1a\n" + b"\0" * 128)
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    text = f"""
format = "1"
id = "local-nc4"
title = "Local netCDF-4"

[land]
role = "background"
colors = ["lego_white"]
weights = [1]

[ocean]
role = "data"
colors = ["lego_earth_blue", "lego_medium_azur"]

[ocean.local]
path = "{p}"
format = "netcdf3"
sha256 = "{sha}"
variable = "ssta"
citation = "Test."
license = "Test."
missing_is_land = true

[ocean.classification]
method = "bins"
bounds = [-9, 0, 9]
"""
    recipe = parse_recipe(text)
    with pytest.raises(MapBuildError, match=r"cannot read local-month.*netCDF-4/HDF5"):
        build_map(recipe)

"""The sticker legend from a built map (feature 017, T026; FR-005, FR-006; research R7, R8; spec
Clarifications on legend labels; data-model.md Swatch, Meaning).

Maps are built from the dataset fixtures (``fixture_registry``) from the bundled recipes, which
carry their approved sticker tables (T043); ``tests.stickers_support.fallback_recipe`` gives a
recipe without its table (the default no-data label).
Not affiliated with or endorsed by The LEGO Group.
"""

import json

import pytest

from lego_image_processor.kit.part_colors import load_part_colors
from lego_image_processor.layout.arrangement import parse_arrangement
from lego_image_processor.maps.build import build_map
from lego_image_processor.maps.recipe import bundled_recipes, load_recipe, parse_recipe
from lego_image_processor.stickers.legend import (
    NO_DATA_LABEL, SHADOW_LABEL, SOURCE_BINS, SOURCE_BUILT, Legend, Meaning, Swatch, map_legend,
)
from tests.stickers_support import fallback_recipe, sticker_recipe

DEMO = '''format = "1"
id = "legend-demo"
title = "Legend demo"
description = "Three depth classes, one of them empty."
[land]
role = "background"
colors = ["lego_white"]
[ocean]
role = "data"
dataset = "etopo2022-surface-10m"
variable = "z"
transform = "negate"
colors = ["lego_medium_azur", "lego_bright_bluish_green", "lego_earth_blue"]
[ocean.classification]
method = "bins"
bounds = [-9000, 200, 11000, 12000]
[ocean.no_data]   # no source pixel lies poleward of 90 degrees: no no-data cell
color = "lego_white"
rule = "share"
min_lat = 90
min_share = 0.99
[[ocean.override]]   # no cell centre lies strictly between 89.9 and 90 degrees
name = "North Pole"
color = "lego_white"
lat_min = 89.9
lat_max = 90
[shadow]
enabled = false
'''


@pytest.fixture
def build(fixture_registry):
    fixture_registry.place_all()

    def _build(recipe, arrangement=None):
        if isinstance(recipe, str):
            recipe = load_recipe(recipe)
        return build_map(recipe, cache_dir=fixture_registry.cache_dir, compare_official=False,
                         arrangement=parse_arrangement(arrangement) if arrangement else None)
    return _build


def labels(legend, layer):
    return [s.label for s in legend.group(layer).swatches]


def class_labels(legend, layer):
    return [m.label for s in legend.group(layer).swatches for m in s.meanings if m.kind == "class"]


class TestBins:
    def test_land_elevation_open_end_classes(self, build):
        lg = map_legend(build("land-elevation"))
        land = lg.group("land").swatches
        assert len(land) == 10
        assert class_labels(lg, "land") == [
            "below 150 m", "150 to 300 m", "300 to 500 m", "500 to 750 m", "750 to 1,000 m",
            "1,000 to 1,500 m", "1,500 to 2,000 m", "2,000 to 2,500 m", "2,500 to 3,000 m",
            "3,000 m and above"]
        first, last = land[0].meanings[0], land[-1].meanings[0]
        assert first.range == (None, 150) and last.range == (3000, None)
        assert {m.units for s in land for m in s.meanings} == {"m"}
        assert {m.source for s in land for m in s.meanings} == {SOURCE_BINS} == {"recipe bins"}
        assert all(m.step is None for s in land for m in s.meanings)
        # the outer bounds 0 and 9,000 only close the list and are never printed
        assert not any("9,000" in t or t.startswith("0 ") for t in labels(lg, "land"))

    def test_log10_layer_in_data_units(self, build):
        lg = map_legend(build(sticker_recipe("living-planet")))
        assert class_labels(lg, "ocean") == [
            "below 0.08 mg m-3", "0.08 to 0.15 mg m-3", "0.15 to 0.3 mg m-3", "0.3 to 1 mg m-3",
            "1 mg m-3 and above"]
        assert class_labels(lg, "land") == [
            "below 100 g C m-2 yr-1", "100 to 250 g C m-2 yr-1", "250 to 400 g C m-2 yr-1",
            "400 to 600 g C m-2 yr-1", "600 to 850 g C m-2 yr-1", "850 g C m-2 yr-1 and above"]
        assert not any("log10" in t for t in labels(lg, "ocean"))

    def test_second_legend_unit_only(self, build):
        lg = map_legend(build("rainfall"))
        assert class_labels(lg, "land") == [
            "below 182.5 mm/yr", "182.5 to 365 mm/yr", "365 to 547.5 mm/yr",
            "547.5 to 912.5 mm/yr", "912.5 to 1,460 mm/yr", "1,460 mm/yr and above"]
        assert class_labels(lg, "ocean") == [
            "below 273.75 mm/yr", "273.75 to 547.5 mm/yr", "547.5 to 1,095 mm/yr",
            "1,095 to 1,825 mm/yr", "1,825 mm/yr and above"]
        text = " ".join(labels(lg, "land") + labels(lg, "ocean"))
        assert "mm/day" not in text
        m = lg.group("land").swatches[0].meanings[0]
        assert (m.range, m.units) == ((None, 182.5), "mm/yr")

    def test_enso_maps_share_one_legend(self, build):
        nino = map_legend(build("ocean-el-nino"))
        assert class_labels(nino, "ocean") == [
            "below -1.5 °C", "-1.5 to -0.5 °C", "-0.5 to -0.25 °C", "-0.25 to -0.1 °C",
            "-0.1 to 0.1 °C", "0.1 to 0.3 °C", "0.3 to 0.5 °C", "0.5 to 1 °C", "1 °C and above"]
        assert labels(nino, "ocean")[0] == "below -1.5 °C; land shadow"
        nina = map_legend(build("ocean-la-nina"))
        assert nina.to_list() == nino.to_list()


class TestRank:
    def test_ocean_sst(self, build):
        lg = map_legend(build("ocean-sst"))
        assert labels(lg, "ocean") == [
            "-2 °C; land shadow", "-2 to 0 °C", "0 to 11 °C", "11 to 16 °C", "16 to 22 °C",
            "22 to 25 °C", "25 to 27 °C", "27 to 28 °C", "28 to 30 °C"]
        ocean = lg.group("ocean").swatches
        first = ocean[0]
        assert first.color == "lego_earth_blue"
        assert [m.kind for m in first.meanings] == ["class", "shadow"]
        m = first.meanings[0]
        assert (m.range, m.units, m.source, m.step) == ((-2, -2), "°C", SOURCE_BUILT, 1)
        assert ocean[-1].meanings[0].range == (28, 30)   # outer bounds included for rank layers
        assert len(lg) == 10                               # land 1 + ocean 9

    def test_bathymetry_at_100_m(self, build):
        lg = map_legend(build("official-31203-bathymetry"))
        assert labels(lg, "ocean") == [
            "0 to 800 m", "800 to 2,300 m", "2,300 to 2,600 m", "2,600 to 2,900 m",
            "2,900 to 3,600 m", "3,600 to 4,300 m", "4,300 to 4,600 m", "4,600 to 6,200 m",
            SHADOW_LABEL]
        assert {m.step for s in lg.group("ocean").swatches for m in s.meanings
                if m.kind == "class"} == {100}
        assert lg.group("ocean").swatches[-1].color == "lego_earth_blue"


class TestCategoricalAndBackground:
    def test_kit_design_colors_without_values(self, build):
        lg = map_legend(build("official-31203"))
        ocean = lg.group("ocean")
        assert ocean.heading == "Ocean: the kit design's colors"
        table = load_part_colors()
        r = load_recipe("official-31203")
        assert [s.color for s in ocean.swatches] == list(r.ocean.colors)
        for s in ocean.swatches:
            (m,) = s.meanings
            assert m.kind == "category" and m.range is None and m.units is None
            assert m.label == s.lego_name == table.get("98138", s.color).lego.name
            assert not any(ch.isdigit() for ch in m.label)
        assert len(ocean.swatches) == 9
        assert lg.group("land").heading == "Land"
        assert labels(lg, "land") == ["land"]
        assert lg.group("land").swatches[0].meanings[0].kind == "background"
        # the shadow is off in this recipe
        assert not any(m.kind == "shadow" for s in lg for m in s.meanings)

    def test_halo_roles_and_the_shadow(self, build):
        lg = map_legend(build("land-elevation"))
        assert labels(lg, "ocean") == ["offshore", "coast ring", "land shadow"]
        assert [s.color for s in lg.group("ocean").swatches] == [
            "lego_bright_bluish_green", "lego_medium_azur", "lego_earth_blue"]
        assert [m.kind for s in lg.group("ocean").swatches for m in s.meanings] == [
            "background", "background", "shadow"]
        assert lg.group("ocean").heading == "Ocean"
        assert len(lg) == 13


class TestNoDataOverridesShadow:
    def test_no_data_labels_from_the_sticker_table(self, build):
        lg = map_legend(build(sticker_recipe("living-planet")))
        land, ocean = lg.group("land").swatches, lg.group("ocean").swatches
        assert land[-1].color == "lego_white" and land[-1].label == "ice"
        assert land[-1].meanings[0].kind == "no_data"
        assert [s.color for s in ocean[-2:]] == ["lego_white", "lego_black"]
        assert [s.label for s in ocean[-2:]] == ["sea ice", "land shadow"]
        assert (len(land), len(ocean)) == (7, 7)

    def test_no_data_label_default(self, build):
        lg = map_legend(build(fallback_recipe("living-planet")))   # without its table
        assert lg.group("land").swatches[-1].label == NO_DATA_LABEL == "no data"
        assert lg.group("ocean").swatches[-2].label == "no data"

    def test_override_names_merge_on_one_swatch(self, build):
        lg = map_legend(build("rainfall"))
        land, ocean = lg.group("land").swatches, lg.group("ocean").swatches
        assert land[-1].color == "lego_white" and land[-1].label == "Antarctica; Greenland"
        assert [m.kind for m in land[-1].meanings] == ["override", "override"]
        assert [s.color for s in ocean[-2:]] == ["lego_white", "lego_black"]
        assert [s.label for s in ocean[-2:]] == ["sea ice", "land shadow"]
        assert ocean[-2].meanings[0].kind == "override"
        assert (len(land), len(ocean)) == (7, 7)

    def test_empty_classes_listed_and_empty_extras_left_out(self, build):
        r = parse_recipe(DEMO)
        result = build(r)
        assert int((result.classes["ocean"] == 2).sum()) == 0    # no ocean deeper than 11 km
        (ocean,) = [r for r in result.report["layers"] if r["class"] == "ocean"]
        assert ocean["no_data"]["cells"] == 0 and ocean["overrides"][0]["cells"] == 0
        lg = map_legend(result)
        assert labels(lg, "ocean") == ["below 200 m", "200 to 11,000 m", "11,000 m and above"]
        assert not any(m.kind in ("no_data", "override", "shadow") for s in lg for m in s.meanings)

    def test_order_land_group_then_ocean_group(self, build):
        lg = map_legend(build("rainfall"))
        assert [g.layer for g in lg.groups] == ["land", "ocean"]
        assert [s.layer for s in lg][:7] == ["land"] * 7
        kinds = [m.kind for s in lg.group("ocean").swatches for m in s.meanings]
        assert kinds == ["class"] * 5 + ["override", "shadow"]


class TestSwatches:
    @pytest.mark.parametrize("recipe_id", ["rainfall", "ocean-sst", "official-31203"])
    def test_cited_srgb_and_names(self, build, recipe_id):
        table = load_part_colors()
        lg = map_legend(build(recipe_id))
        for s in lg:
            assert isinstance(s, Swatch)
            assert s.part_id == {"land": "6141", "ocean": "98138"}[s.layer]
            c = table.get(s.part_id, s.color)
            assert s.rgb == tuple(c.rgb) and s.lego_name == c.lego.name
        keys = [(s.part_id, s.color) for s in lg]
        assert len(keys) == len(set(keys))   # one swatch per part and color

    def test_to_list(self, build):
        lg = map_legend(build("ocean-sst"))
        assert isinstance(lg, Legend)
        out = lg.to_list()
        json.dumps(out, ensure_ascii=False)
        s = out[1]
        assert list(s) == ["layer", "part_id", "color", "lego_name", "rgb", "meanings"]
        assert s["meanings"][0] == {"kind": "class", "label": "-2 °C", "range": [-2, -2],
                                    "units": "°C", "source": "built classes", "step": 1}
        assert s["meanings"][1] == {"kind": "shadow", "label": "land shadow"}
        assert out[0]["meanings"] == [{"kind": "background", "label": "land"}]

    def test_meaning_to_dict_for_bins(self):
        m = Meaning("class", "below 150 m", range=(None, 150), units="m", source=SOURCE_BINS)
        assert m.to_dict() == {"kind": "class", "label": "below 150 m", "range": [None, 150],
                               "units": "m", "source": "recipe bins"}

    def test_reads_the_built_map_only(self, build, monkeypatch):
        result = build("ocean-sst")

        def boom(*a, **k):
            raise AssertionError("the legend must not read or classify data")
        import lego_image_processor.maps.build as mb
        monkeypatch.setattr(mb, "read_dataset", boom)
        monkeypatch.setattr(mb, "classify", boom)
        monkeypatch.setattr(mb, "reproject_layer", boom)
        assert len(map_legend(result)) == 10


class TestCombinations:
    """FR-006, SC-003: one legend per map, the same for A, B and C."""

    @pytest.mark.parametrize("recipe_id", ["ocean-sst", "official-31203-bathymetry"])
    def test_rank_maps_identical_in_a_b_c(self, build, recipe_id):
        a, b, c = (map_legend(build(recipe_id, x)) for x in ("A", "B", "C"))
        assert a.to_list() == b.to_list() == c.to_list()
        assert a == b == c

    @pytest.mark.parametrize("recipe_id", sorted(bundled_recipes()))
    def test_every_bundled_map_identical_in_a_b_c(self, build, recipe_id):
        r = sticker_recipe(recipe_id)
        lists = [map_legend(build(r, x)).to_list() for x in ("A", "B", "C")]
        assert lists[0] == lists[1] == lists[2]

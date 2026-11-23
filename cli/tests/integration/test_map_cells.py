"""Per-cell chooser data (feature 012, FR-001, FR-004, FR-005; SC-001)."""

import numpy as np
import pytest

from lego_image_processor.layout.arrangement import parse_arrangement
from lego_image_processor.maps.build import build_map
from lego_image_processor.maps.cells import CELLS_FORMAT, PREVIEW_NOTE, map_cells
from lego_image_processor.maps.ice import load_ice_regions
from lego_image_processor.maps.recipe import load_recipe

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."


def _build(rid, arrangement=None):
    return build_map(load_recipe(rid), compare_official=False,
                     arrangement=parse_arrangement(arrangement) if arrangement else None)


def _default_colors(cells):
    """The default chooser rendering: each cell's color key (the script does the same)."""
    out = []
    kinds = cells["cells"]
    layers = cells["layers"]
    for i, k in enumerate(kinds):
        if k == "S":
            out.append(cells["shadow"]["color"])
        else:
            layer = layers["land" if k == "L" else "ocean"]
            out.append(layer["colors"][layer["classes"][i]])
    return out


def _layout_colors(result):
    return [p.color_id for p in sorted(result.layout.positions, key=lambda p: (p.y, p.x))]


@pytest.fixture
def placed(fixture_registry):
    fixture_registry.place_all()
    return fixture_registry


class TestFormat:
    def test_header(self):
        c = map_cells(_build("official-31203"))
        assert c["format_version"] == CELLS_FORMAT == "1"
        assert c["width"] == 128 and c["height"] == 80
        assert c["recipe"]["id"] == "official-31203" and len(c["recipe"]["sha256"]) == 64
        assert c["arrangement"] == "A"
        assert c["disclaimer"] == DISCLAIMER
        assert c["note"] == PREVIEW_NOTE and "Preview only" in PREVIEW_NOTE
        assert len(c["cells"]) == 128 * 80 and set(c["cells"]) <= {"L", "O", "S"}

    def test_palette_cited_and_sorted(self):
        c = map_cells(_build("official-31203"))
        for part, n in (("6141", 44), ("98138", 40)):
            rows = c["palette"][part]
            assert len(rows) == n
            ls = [r["lightness"] for r in rows]
            assert ls == sorted(ls, reverse=True)
            white = next(r for r in rows if r["key"] == "lego_white")
            assert white["lightness"] == 100 and white["rgb"] == [255, 255, 255]
            for r in rows:
                assert r["lego"]["name"] and r["bricklink"]["name"] and isinstance(r["in_kit"], bool)
        assert sum(r["in_kit"] for r in c["palette"]["98138"]) == 9
        assert [r["key"] for r in c["palette"]["6141"] if r["in_kit"]] == ["lego_white"]

    def test_categorical_ocean_and_background_land(self):
        c = map_cells(_build("official-31203"))
        ocean, land = c["layers"]["ocean"], c["layers"]["land"]
        assert ocean["method"] == "categorical" and ocean["editable_classes"] is False
        assert ocean["categories"] == ocean["colors"]
        assert ocean["values"] is None
        assert land["role"] == "background" and land["method"] == "background"
        assert land["class_labels"] == ["land"] and land["editable_classes"] is False

    def test_shadow_off_for_official(self):
        c = map_cells(_build("official-31203"))
        assert c["shadow"]["enabled"] is False and "S" not in c["cells"]

    def test_ice_lists_rolled(self):
        c = map_cells(_build("official-31203", "B"))
        ice = load_ice_regions().rolled(parse_arrangement("B"))
        assert c["ice"]["land"] == [int(i) for i in np.flatnonzero(ice.land.ravel())]
        assert c["ice"]["sea"] == [int(i) for i in np.flatnonzero(ice.sea.ravel())]
        assert c["ice"]["source"]["sea_ice"]["dataset"]["id"] == "ersst-v5-ltm-1991-2020"


class TestDefaultEqualsBuild:
    @pytest.mark.parametrize("arr", ["A", "B", "C"])
    def test_official(self, arr):
        r = _build("official-31203", arr)
        assert _default_colors(map_cells(r)) == _layout_colors(r)

    @pytest.mark.parametrize("rid", ["ocean-sst", "land-elevation", "official-31203-bathymetry",
                                     "ocean-el-nino"])
    def test_data_maps(self, placed, rid):
        for arr in ("A", "C"):
            r = _build(rid, arr)
            assert _default_colors(map_cells(r)) == _layout_colors(r)

    def test_does_not_change_layout(self, placed):
        r = _build("ocean-sst")
        before = r.layout.to_json()
        map_cells(r)
        assert r.layout.to_json() == before == _build("ocean-sst").layout.to_json()


class TestDataLayers:
    def test_bins_bounds_from_recipe(self, placed):
        c = map_cells(_build("land-elevation"))
        land = c["layers"]["land"]
        assert land["method"] == "bins" and land["bounds_source"] == "recipe"
        assert land["bounds"] == [0, 150, 300, 500, 750, 1000, 1500, 2000, 2500, 3000, 9000]
        assert land["units"] == "m" and land["editable_classes"] is True
        assert land["texture"] == "blend"

    def test_rank_bounds_from_built_classes(self, placed):
        c = map_cells(_build("ocean-sst"))
        ocean = c["layers"]["ocean"]
        assert ocean["method"] == "rank-to-supply" and ocean["bounds_source"] == "built classes"
        b = ocean["bounds"]
        assert len(b) == len(ocean["colors"]) + 1
        assert all(x <= y for x, y in zip(b, b[1:]))
        assert b[0] == ocean["range"][0] and b[-1] == ocean["range"][1]
        assert ocean["units"] == "°C"

    def test_values_only_on_layer_cells(self, placed):
        c = map_cells(_build("ocean-sst"))
        ocean = c["layers"]["ocean"]
        for i, k in enumerate(c["cells"]):
            if k == "O":
                assert isinstance(ocean["values"][i], (int, float)) and ocean["classes"][i] >= 0
            else:
                assert ocean["values"][i] is None and ocean["classes"][i] == -1

    def test_no_value_cells(self, placed):
        r = _build("ocean-sst")
        c = map_cells(r)
        want = [int(i) for i in np.flatnonzero(r.fields["ocean"].filled.ravel())]
        assert c["layers"]["ocean"]["no_value"] == want
        assert c["layers"]["ocean"]["no_value_ice"] == len(set(want) & set(c["ice"]["sea"]))

    def test_rounding(self, placed):
        sst = map_cells(_build("ocean-sst"))["layers"]["ocean"]["values"]
        elev = map_cells(_build("land-elevation"))["layers"]["land"]["values"]
        assert all(v is None or round(v, 2) == v for v in sst)
        assert all(v is None or float(v).is_integer() for v in elev)

    def test_halo_background(self, placed):
        ocean = map_cells(_build("land-elevation"))["layers"]["ocean"]
        assert ocean["role"] == "background" and ocean["texture"] == "halo"
        assert ocean["class_labels"] == ["offshore", "coast ring"]
        assert ocean["colors"] == ["lego_bright_bluish_green", "lego_medium_azur"]

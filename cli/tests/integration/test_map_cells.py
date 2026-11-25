"""Per-cell chooser data (feature 015, FR-001, FR-004, FR-005; SC-001)."""

import json

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
    """The default chooser rendering: each cell's color key (the script does the same). Feature 016:
    a margin cell (``M``) takes the ring color on the ring, the margin color elsewhere. Feature 017:
    a plaque cell (``P``) takes the plaque's color."""
    out = []
    kinds = cells["cells"]
    layers = cells["layers"]
    margin = cells.get("margin") or {}
    ring = set((margin.get("ring") or {}).get("cells", ()))
    for i, k in enumerate(kinds):
        if k == "P":
            out.append(cells["plaque"]["color"])
        elif k == "M":
            out.append(margin["ring"]["color"] if i in ring else margin["color"])
        elif k == "S":
            out.append(cells["shadow"]["color"])
        else:
            layer = layers["land" if k == "L" else "ocean"]
            out.append(layer["colors"][layer["classes"][i]])
    return out


def _layout_colors(result):
    """Each stud's color key in the layout; the studs under a recorded plaque (feature 017) take the
    plaque's color."""
    by_stud = {(p.x, p.y): p.color_id for p in result.layout.positions}
    plaque = result.layout.plaque
    for xy in result.layout.plaque_positions:
        by_stud[xy] = plaque["color"]
    return [by_stud[(x, y)] for y in range(result.layout.height) for x in range(result.layout.width)]


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
        def stable(layout):  # generated_at has one-second resolution; two builds may differ
            d = json.loads(layout.to_json())
            d.get("metadata", {}).pop("generated_at", None)
            d.pop("generated_at", None)
            return d

        r = _build("ocean-sst")
        before = r.layout.to_json()
        map_cells(r)
        assert r.layout.to_json() == before
        assert stable(r.layout) == stable(_build("ocean-sst").layout)


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


@pytest.mark.parametrize("rid", ["living-planet", "rainfall"])
def test_recipes_with_no_data_and_overrides(placed, rid):
    """Feature 015 on the 012/013 recipes: cells left without a value (living-planet ``no_data``)
    are skipped for the range, and the chooser's default colors equal the built layout."""
    result = _build(rid)
    cells = map_cells(result)
    for name, layer in cells["layers"].items():
        if layer.get("range") is not None:
            lo, hi = layer["range"]
            assert np.isfinite(lo) and np.isfinite(hi) and lo <= hi, name
        if layer.get("bounds"):
            assert all(np.isfinite(b) for b in layer["bounds"]), name
    assert len(cells["cells"]) == 10240


def test_log10_layer_units_say_log10(placed):
    """living-planet's chlorophyll is classified on log10: the chooser's numbers and label agree."""
    ocean = map_cells(_build("living-planet"))["layers"]["ocean"]
    assert ocean["transform"] == "log10" and ocean["units"].startswith("log10")


class TestPaletteParts:
    """016 T014: the palette lists the template's parts; kit cells.json keeps 6141 and 98138 only."""

    def test_default_is_the_kit_parts(self):
        from lego_image_processor.maps.cells import part_palette
        assert list(part_palette()) == ["6141", "98138"]
        assert list(part_palette(("6141", "98138", "3070b"))) == ["6141", "98138", "3070b"]
        assert any(r["key"] == "lego_black" for r in part_palette(("3070b",))["3070b"])

    def test_kit_cells_have_no_square_tile(self):
        c = map_cells(_build("official-31203"))
        assert list(c["palette"]) == ["6141", "98138"]


# --- Feature 016 (T079): map cells on a template (FR-020a; contracts/recipe-and-outputs.md) -----

class TestTemplateCells:
    """``map_cells`` on ``confirmed_winkel`` with the dataset fixtures: ``M`` cells, the ``template``
    and ``margin`` blocks, the 3070b palette and the template's own ice regions."""

    def _build(self, rid, template, **kw):
        return build_map(load_recipe(rid), compare_official=False, template=template, **kw)

    def test_cells_classes_and_counts(self, placed, confirmed_winkel):
        t = confirmed_winkel
        r = self._build("ocean-sst", t)
        c = map_cells(r)
        kinds = np.array(list(c["cells"])).reshape(80, 128)
        assert (kinds == "M").sum() == t.counts["margin"]
        assert ((kinds == "M") == t.margin).all()
        assert ((kinds == "L") == t.land).all()
        assert (np.isin(kinds, ["O", "S"]) == t.ocean).all()
        assert c["shadow"]["cells"] == int((kinds == "S").sum()) > 0
        assert c["arrangement"] == "A" and c["width"] == 128 and c["height"] == 80
        for name, layer in c["layers"].items():
            cls = np.array(layer["classes"]).reshape(80, 128)
            assert (cls[t.margin] == -1).all(), name
            if layer.get("values") is not None:
                assert all(layer["values"][i] is None for i in np.flatnonzero(t.margin.ravel())), name
        assert c["layers"]["land"]["cells"] == t.counts["land"]
        assert c["layers"]["ocean"]["cells"] == t.counts["ocean"] - c["shadow"]["cells"]

    def test_template_block_cites_etopo(self, placed, confirmed_winkel):
        from lego_image_processor.datasets.registry import load_registry
        from lego_image_processor.templates import PACKAGED_REGISTRY

        c = map_cells(self._build("ocean-sst", confirmed_winkel))
        e = load_registry(PACKAGED_REGISTRY).get("etopo2022-surface-10m")
        assert c["template"] == {"id": "winkel-tripel", "title": confirmed_winkel.title,
                                 "dataset": {"id": e.id, "version": e.version, "citation": e.citation,
                                             "license": e.license}}
        assert list(c).index("template") == list(c).index("arrangement") + 1

    def test_margin_block(self, placed, confirmed_winkel):
        from lego_image_processor.maps.margin import MarginTreatment

        c = map_cells(self._build("ocean-sst", confirmed_winkel))
        assert c["margin"] == {"part_id": "3070b", "color": "lego_black", "ring": None}
        assert list(c).index("margin") == list(c).index("shadow") + 1
        r = self._build("ocean-sst", confirmed_winkel,
                        margin=MarginTreatment(color="lego_white", ring="lego_bright_yellow"))
        c = map_cells(r)
        ring = [int(i) for i in np.flatnonzero(confirmed_winkel.ring.ravel())]
        assert c["margin"] == {"part_id": "3070b", "color": "lego_white",
                               "ring": {"color": "lego_bright_yellow", "cells": ring}}
        assert len(ring) == confirmed_winkel.counts["ring"]

    def test_palette_adds_the_square_tile(self, placed, confirmed_winkel):
        from lego_image_processor.kit.part_colors import load_part_colors

        c = map_cells(self._build("ocean-sst", confirmed_winkel))
        assert list(c["palette"]) == ["6141", "98138", "3070b"]
        rows = c["palette"]["3070b"]
        assert len(rows) == len(load_part_colors().for_part("3070b"))
        ls = [x["lightness"] for x in rows]
        assert ls == sorted(ls, reverse=True)
        black = next(x for x in rows if x["key"] == "lego_black")
        assert black["in_kit"] is False and black["lightness"] < 20

    def test_ice_from_the_template_file(self, placed, confirmed_winkel):
        from lego_image_processor.maps.ice import load_template_ice

        c = map_cells(self._build("ocean-sst", confirmed_winkel))
        ice = load_template_ice(confirmed_winkel)
        assert c["ice"]["land"] == [int(i) for i in np.flatnonzero(ice.land.ravel())]
        assert c["ice"]["sea"] == [int(i) for i in np.flatnonzero(ice.sea.ravel())]
        assert c["ice"]["color"] == "lego_white"
        assert c["ice"]["source"]["sea_ice"]["dataset"]["id"] == "ersst-v5-ltm-1991-2020"
        kinds = c["cells"]
        assert all(kinds[i] == "L" for i in c["ice"]["land"])
        assert all(kinds[i] in "OS" for i in c["ice"]["sea"])

    @pytest.mark.parametrize("rid", ["ocean-sst", "land-elevation", "official-31203-bathymetry"])
    def test_default_rendering_equals_layout(self, placed, confirmed_winkel, rid):
        r = self._build(rid, confirmed_winkel)
        assert _default_colors(map_cells(r)) == _layout_colors(r)

    def test_default_rendering_with_a_ring(self, placed, confirmed_winkel):
        from lego_image_processor.maps.margin import MarginTreatment

        r = self._build("ocean-sst", confirmed_winkel, margin=MarginTreatment(ring="lego_white"))
        assert _default_colors(map_cells(r)) == _layout_colors(r)

    @pytest.mark.parametrize("rid", ["living-planet", "rainfall"])
    def test_recipes_with_no_data_and_overrides(self, placed, confirmed_winkel, rid):
        c = map_cells(self._build(rid, confirmed_winkel))
        assert len(c["cells"]) == 10240 and c["cells"].count("M") == confirmed_winkel.counts["margin"]
        for name, layer in c["layers"].items():
            if layer.get("range") is not None:
                lo, hi = layer["range"]
                assert np.isfinite(lo) and np.isfinite(hi) and lo <= hi, name

    def test_kit_cells_have_no_template_keys(self, placed):
        c = map_cells(_build("ocean-sst"))
        assert "template" not in c and "margin" not in c
        assert "M" not in c["cells"] and list(c["palette"]) == ["6141", "98138"]


# --- Feature 017 (T076): map cells with the in-margin plaque (contracts/in-margin-plaque.md) ------

class TestPlaqueCells:
    """``map_cells`` of ``ocean-sst`` on ``confirmed_winkel`` with the plaque in a corner: ``P``
    cells and a ``plaque`` block; files without a plaque are unchanged."""

    def _build(self, corner=None, **kw):
        from lego_image_processor.maps.margin import MarginTreatment

        margin = None if corner is None else MarginTreatment(plaque=corner, plaque_source="option", **kw)
        return build_map(load_recipe("ocean-sst"), compare_official=False, template="winkel-tripel",
                         margin=margin)

    @pytest.mark.parametrize("corner", ["bottom-left", "top-right"])
    def test_p_cells_and_the_plaque_block(self, placed, confirmed_winkel, corner):
        from lego_image_processor.kit.plaque_parts import load_plaque_parts

        tile = load_plaque_parts().plaques["small"].tile
        r = self._build(corner)
        c = map_cells(r)
        kinds = np.array(list(c["cells"])).reshape(80, 128)
        mask = r.plaque.mask((80, 128))
        assert ((kinds == "P") == mask).all() and (kinds == "P").sum() == 36
        assert (kinds == "M").sum() == confirmed_winkel.counts["margin"] - 36
        cells = [int(i) for i in np.flatnonzero(mask.ravel())]
        assert c["plaque"] == {"part_id": tile.part_id, "color": tile.color.key,
                               "rgb": [int(v) for v in tile.color.rgb], "corner": corner, "cells": cells}
        assert list(c).index("plaque") == list(c).index("margin") + 1
        assert c["palette"] == map_cells(self._build())["palette"]  # the palette is unchanged
        for name, layer in c["layers"].items():
            assert all(layer["classes"][i] == -1 for i in cells), name

    def test_default_rendering_equals_layout(self, placed):
        r = self._build("bottom-left")
        assert _default_colors(map_cells(r)) == _layout_colors(r)

    def test_with_a_ring(self, placed):
        r = self._build("bottom-left", ring="lego_white")
        c = map_cells(r)
        assert not set(c["plaque"]["cells"]) & set(c["margin"]["ring"]["cells"])
        assert _default_colors(c) == _layout_colors(r)

    def test_without_a_plaque_unchanged(self, placed):
        from lego_image_processor.maps.margin import MarginTreatment

        a = map_cells(self._build())
        b = map_cells(build_map(load_recipe("ocean-sst"), compare_official=False, template="winkel-tripel",
                                margin=MarginTreatment()))
        assert "plaque" not in a and "P" not in a["cells"]
        assert a == b

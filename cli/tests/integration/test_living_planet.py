"""The living-planet map on the derived fixtures (feature 012: US1, FR-008-FR-010).

Not affiliated with or endorsed by The LEGO Group.
"""

import numpy as np
import pytest

from lego_image_processor.layout.arrangement import parse_arrangement
from lego_image_processor.maps.build import NO_DATA_CLASS, build_map, land_mask_array
from lego_image_processor.maps.recipe import load_recipe

LAND_COLORS = {"lego_brick_yellow", "lego_sand_yellow", "lego_sand_green", "lego_bright_yellowish_green",
               "lego_bright_green", "lego_dark_green", "lego_white"}
OCEAN_COLORS = {"lego_bright_blue", "lego_dark_azur", "lego_medium_azur", "lego_bright_bluish_green",
                "lego_earth_green", "lego_white", "lego_black"}
DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."


@pytest.fixture
def placed(fixture_registry):
    return fixture_registry.place_all()


@pytest.fixture
def built(placed):
    return build_map(load_recipe("living-planet"))


def _colors(result):
    return np.array([[None] * 128 for _ in range(80)], dtype=object), {
        (p.y, p.x): (p.color_id, p.lego_part_id) for p in result.layout.positions}


def test_parts_and_colors(built):
    _, cells = _colors(built)
    land = land_mask_array()
    for (y, x), (color, part) in cells.items():
        if land[y, x]:
            assert part == "6141" and color in LAND_COLORS
        else:
            assert part == "98138" and color in OCEAN_COLORS
    used = {c for c, _ in cells.values()}
    assert {"lego_black", "lego_white", "lego_bright_blue", "lego_dark_green"} <= used


def test_no_data_rules_report_and_metadata(built):
    land_rep, ocean_rep = built.report["layers"]
    assert land_rep["no_data"]["rule"] == "share" and land_rep["no_data"]["cells"] > 50
    assert ocean_rep["no_data"]["rule"] == "unobserved" and ocean_rep["no_data"]["cells"] > 50
    assert ocean_rep["transform"] == "log10"
    assert ocean_rep["class_bounds"] == pytest.approx([0.001, 0.08, 0.15, 0.3, 1.0, 1000])
    assert built.report["shadow"] == {"enabled": True, "color": "lego_black", "direction": "east",
                                      "cells": built.report["shadow"]["cells"]}
    white = {r["key"]: r["used"] for r in ocean_rep["supply"]}["lego_white"]
    assert white == ocean_rep["no_data"]["cells"]
    meta = built.layout.map_metadata
    assert meta["layers"][0]["land_from"]["dataset"] == "etopo2022-surface-10m"
    assert meta["layers"][1]["no_data"]["cells"] == ocean_rep["no_data"]["cells"]
    assert [c["id"] for c in built.report["citations"]] == [
        "mod17a3-npp-mean-2000-2015", "etopo2022-surface-10m", "modis-aqua-chla-2013-2024"]
    assert built.report["disclaimer"] == DISCLAIMER


def test_ice_is_polar(built):
    from lego_image_processor.maps.nodata import cell_latitudes
    from lego_image_processor.maps.projection import load_kit_projection

    lats = cell_latitudes(load_kit_projection())
    # ocean: cell-centre latitude. Land: pixel latitude, and a kit land cell without any land
    # pixel takes the nearest cell's share (as in the prototype, e.g. two sub-Antarctic island
    # cells near 44S and 51S on real data), so its centre may lie well short of 55.
    for cls, lat in (("land", 40), ("ocean", 60)):
        nd = built.classes[cls] == NO_DATA_CLASS
        assert nd.any() and (lats[nd] > lat).all()


def test_shadow_cells_are_black_and_never_ice(built):
    _, cells = _colors(built)
    land = land_mask_array()
    for y in range(80):
        for x in range(1, 128):
            if land[y, x - 1] and not land[y, x]:
                assert cells[(y, x)][0] == "lego_black"


def test_arrangement_b_per_cell_classes_match_a(placed):
    rec = load_recipe("living-planet")
    a = build_map(rec)
    b = build_map(rec, arrangement=parse_arrangement("B"))
    arr = parse_arrangement("B")
    assert np.array_equal(arr.roll(a.classes["land"]), b.classes["land"])
    nd_a = a.classes["ocean"] == NO_DATA_CLASS
    nd_b = b.classes["ocean"] == NO_DATA_CLASS
    # per-cell rules in kit columns; the shadow (cast on the board as hung) may cover a few
    assert (nd_b <= arr.roll(nd_a)).all() and nd_b.sum() >= nd_a.sum() - 20


def test_layout_validates_mask_and_lists_extras(built):
    from lego_image_processor.layout.validator import (ColorUnavailableViolation, LayoutValidator,
                                                       MaskMismatchViolation)
    from lego_image_processor.layout.kit_spec import load_kit_specification
    from lego_image_processor.palette.loader import LegoPalette

    v = LayoutValidator(kit_spec=load_kit_specification("31203"), palette=LegoPalette.load_default())
    rep = v.validate(built.layout, "lp.json")
    assert not any(isinstance(v, MaskMismatchViolation) for v in rep.violations)
    assert any(isinstance(v, ColorUnavailableViolation) for v in rep.violations)  # beyond one kit
    assert not rep.buildable


def test_bundled_recipe_mentions_disclaimer():
    text = load_recipe("living-planet").path.read_text(encoding="utf-8")
    assert DISCLAIMER in text

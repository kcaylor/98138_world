"""The rainfall map on the derived fixtures (feature 013: US1, FR-005-FR-008).

Not affiliated with or endorsed by The LEGO Group.
"""

import numpy as np
import pytest

from lego_image_processor.maps.build import build_map, land_mask_array, override_class
from lego_image_processor.maps.projection import load_kit_projection
from lego_image_processor.maps.recipe import load_recipe
from lego_image_processor.maps.reproject import cell_centres

LAND_COLORS = {"lego_brick_yellow", "lego_sand_yellow", "lego_sand_green", "lego_bright_yellowish_green",
               "lego_bright_green", "lego_dark_green", "lego_white"}
OCEAN_COLORS = {"lego_light_royal_blue", "lego_medium_azur", "lego_dark_azur", "lego_bright_blue",
                "lego_earth_blue", "lego_white", "lego_black"}
DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
LAT, LON = cell_centres(load_kit_projection())


@pytest.fixture
def built(fixture_registry):
    fixture_registry.place_all()
    return build_map(load_recipe("rainfall"))


def _cells(result):
    return {(p.y, p.x): (p.color_id, p.lego_part_id) for p in result.layout.positions}


def test_recipe_matches_the_approved_design():
    r = load_recipe("rainfall")
    assert (r.id, r.title, r.arrangement) == ("rainfall", "Rainfall", None)   # default A
    assert r.land.colors == ("lego_brick_yellow", "lego_sand_yellow", "lego_sand_green",
                             "lego_bright_yellowish_green", "lego_bright_green", "lego_dark_green")
    assert r.land.classification.bounds == (0, 0.5, 1.0, 1.5, 2.5, 4.0, 1000)
    assert r.ocean.colors == ("lego_light_royal_blue", "lego_medium_azur", "lego_dark_azur",
                              "lego_bright_blue", "lego_earth_blue")
    assert r.ocean.classification.bounds == (0, 0.75, 1.5, 3.0, 5.0, 1000)
    assert r.land.sampling == r.ocean.sampling == "bilinear"
    assert [o.name for o in r.land.overrides] == ["Antarctica", "Greenland"]
    assert [(o.kind, o.dataset.id, o.min_value, o.unobserved_lat) for o in r.ocean.overrides] == [
        ("dataset", "nsidc-cdr-v6-seaice-minimum-1991-2020", 0.7, 60.0)]
    assert r.shadow.color == "lego_black"
    assert r.land.legend.to_dict() == r.ocean.legend.to_dict() == {"units": "mm/yr", "factor": 365.0}
    assert DISCLAIMER in r.path.read_text(encoding="utf-8")


def test_parts_and_colors(built):
    land = land_mask_array()
    for (y, x), (color, part) in _cells(built).items():
        if land[y, x]:
            assert part == "6141" and color in LAND_COLORS
        else:
            assert part == "98138" and color in OCEAN_COLORS


def test_ice_sheets_and_sea_ice(built):
    land = land_mask_array()
    cells = _cells(built)
    antarctic = land & (LAT < -60)
    assert antarctic.any() and all(cells[(y, x)][0] == "lego_white" for y, x in zip(*np.nonzero(antarctic)))
    iceland = land & (LAT > 59) & (LAT < 67) & (LON > -26) & (LON < -10)
    assert iceland.any() and all(cells[(y, x)][0] != "lego_white" for y, x in zip(*np.nonzero(iceland)))
    white_land = land & np.array([[cells[(y, x)][0] == "lego_white" for x in range(128)] for y in range(80)])
    assert (np.abs(LAT[white_land]) > 59).all()
    sea_ice = built.classes["ocean"] == override_class(0)
    assert sea_ice.any() and (np.abs(LAT[sea_ice]) > 40).all()


def test_report_and_metadata(built):
    land_rep, ocean_rep = built.report["layers"]
    assert [(o["name"], o["kind"], o["color"]) for o in land_rep["overrides"]] == [
        ("Antarctica", "region", "lego_white"), ("Greenland", "region", "lego_white")]
    assert ocean_rep["overrides"][0]["dataset"] == "nsidc-cdr-v6-seaice-minimum-1991-2020"
    white = {r["key"]: r["used"] for r in ocean_rep["supply"]}["lego_white"]
    assert white == ocean_rep["overrides"][0]["cells"] > 0
    lw = {r["key"]: r["used"] for r in land_rep["supply"]}["lego_white"]
    assert lw == sum(o["cells"] for o in land_rep["overrides"])
    assert land_rep["legend"] == {"units": "mm/yr", "factor": 365.0} and land_rep["sampling"] == "bilinear"
    assert land_rep["filled_cells"] == 0 and ocean_rep["filled_cells"] == 0      # bilinear: no fill
    assert sum(c["cells"] for c in land_rep["class_counts"]) == land_rep["cells"]
    assert land_rep["cells"] + lw == int(land_mask_array().sum())
    meta = built.layout.map_metadata
    assert meta["layers"][0]["overrides"][1]["exclude"] == [{"lat_max": 67.0, "lon_min": -26.0}]
    assert meta["layers"][1]["overrides"][0]["cells"] == white and meta["layers"][1]["sampling"] == "bilinear"
    cites = built.report["citations"]
    assert [c["id"] for c in cites] == ["gpcp-v23-ltm-1991-2020", "nsidc-cdr-v6-seaice-minimum-1991-2020"]
    assert cites[1]["files"] == 4 and len(cites[1]["files_sha256"]) == 64
    assert built.report["disclaimer"] == DISCLAIMER


def test_shadow_cells_are_black(built):
    cells = _cells(built)
    land = land_mask_array()
    for y in range(80):
        for x in range(1, 128):
            if land[y, x - 1] and not land[y, x]:
                assert cells[(y, x)][0] == "lego_black"


def test_parts_list_beyond_one_kit(built):
    from lego_image_processor.parts import OwnedInputs, build_parts_list

    pl = build_parts_list(built.layout, owned=OwnedInputs(kits=1))
    assert pl.totals()["to_buy"] > 6000

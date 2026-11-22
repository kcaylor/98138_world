"""land-elevation on the ETOPO fixture (US4 scenarios 1, 3; SC-009)."""

import json

import numpy as np
import pytest
from click.testing import CliRunner

from lego_image_processor.cli.main import cli
from lego_image_processor.kit.part_colors import load_part_colors
from lego_image_processor.maps import build as b
from lego_image_processor.maps.build import build_map, land_mask_array
from lego_image_processor.maps.recipe import load_recipe


@pytest.fixture
def built(fixture_registry):
    fixture_registry.place_all()
    return build_map(load_recipe("land-elevation"))


def test_land_uses_cited_plate_colors(built):
    table = load_part_colors()
    for p in built.layout.positions:
        if p.part_type == "plate":
            c = table.get("6141", p.color_id)
            assert c is not None and p.color_name == c.lego.name and p.lego_color_code == str(c.lego.id)


def test_monotonic_before_texture(fixture_registry):
    fixture_registry.place_all()
    r = load_recipe("land-elevation")
    mask = land_mask_array()
    _, fld, cr = b._layer_classes(r.land, mask, r.seed, None)
    v, c = fld.values[mask], cr.classes[mask]
    assert (np.diff(c[np.argsort(v, kind="stable")]) >= 0).all()


def test_no_empty_class_and_distinct_colors(built):
    land = next(l for l in built.report["layers"] if l["class"] == "land")
    assert all(c["cells"] > 0 for c in land["class_counts"])
    assert land["min_neighbour_delta_e00"]["delta_e00"] >= 5


def test_ocean_background_is_quiet_blue(built):
    # A land map's ocean is a calm background: the base, its coastal halo and the Earth Blue shadow.
    counts = built.layout.compute_statistics().color_frequency_by_part_type["tile"]
    assert set(counts) == {"lego_bright_bluish_green", "lego_medium_azur", "lego_earth_blue"}
    assert counts["lego_bright_bluish_green"] > sum(counts.values()) / 2


def test_validate_lists_non_kit_plates(built, tmp_path):
    path = tmp_path / "elev.json"
    path.write_text(built.layout.to_json(), encoding="utf-8")
    report = tmp_path / "report.json"
    result = CliRunner().invoke(cli, ["validate", str(path), "-o", str(report)])
    assert result.exit_code == 0, result.output
    assert "PARTIALLY BUILDABLE" in result.output
    v = json.loads(report.read_text())["violations"]
    unavailable = {x["color_id"] for x in v if x["type"] == "color_unavailable"}
    used = {p.color_id for p in built.layout.positions if p.part_type == "plate"} - {"lego_white"}
    assert unavailable == used
    assert all(x["part_id"] == "6141" for x in v if x["type"] == "color_unavailable")

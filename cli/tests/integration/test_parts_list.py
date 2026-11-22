"""Parts lists from every layout source (005 T019, T037; SC-001, SC-002, SC-005)."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from lego_image_processor.cli.main import cli
from lego_image_processor.kit import load_official_design
from lego_image_processor.kit.part_colors import load_part_colors
from lego_image_processor.maps.build import build_map
from lego_image_processor.maps.recipe import bundled_recipes, load_recipe
from lego_image_processor.parts import build_parts_list, read_layout

IMAGES = Path(__file__).resolve().parents[1] / "fixtures" / "images"


def test_official_layout_has_ten_verified_lots():
    design = load_official_design()
    pl = build_parts_list(design.to_layout())
    assert len(pl.lots) == 10 and all(l.verified for l in pl.lots)
    assert pl.totals()["needed"] == 10240
    assert {l.color_key: l.needed for l in pl.lots} == {c.key: c.used for c in design.counts}
    plate = [l for l in pl.lots if l.part_id == "6141"]
    assert len(plate) == 1 and plate[0].ids.bricklink_item_no == "4073"
    assert plate[0].ids.rebrickable_part_num == "6141"
    assert all(l.ids.bricklink_item_no == "98138" == l.ids.rebrickable_part_num
               for l in pl.lots if l.part_id == "98138")


@pytest.mark.parametrize("recipe_id", sorted(bundled_recipes()))
def test_every_bundled_recipe_is_fully_verified(fixture_registry, recipe_id):
    """SC-002, on the dataset fixtures."""
    fixture_registry.place_all()
    result = build_map(load_recipe(recipe_id))
    pl = build_parts_list(result.layout)
    assert pl.unverified_lots == ()
    assert pl.layout["map"]["recipe"]["id"] == recipe_id


def test_recipe_layout_records_provenance(fixture_registry, tmp_path):
    fixture_registry.place_all()
    path = tmp_path / "elev.json"
    path.write_text(build_map(load_recipe("land-elevation")).layout.to_json(), encoding="utf-8")
    d = json.loads(build_parts_list(read_layout(path)).to_json())
    assert d["layout"]["source_image"] == "recipe:land-elevation"
    assert d["layout"]["map"]["recipe"]["id"] == "land-elevation"
    ds = d["layout"]["map"]["datasets"]
    assert [x["id"] for x in ds] == ["etopo2022-surface-10m"] and ds[0]["license"] and ds[0]["citation"]
    assert len(d["layout"]["sha256"]) == 64
    assert d["disclaimer"] == "Not affiliated with or endorsed by The LEGO Group."


def test_image_fixture_layout_fully_verified(tmp_path):
    """SC-005: after US4, the feature-002 image fixture has no unverified lots."""
    out = tmp_path / "img.json"
    r = CliRunner().invoke(cli, ["layout", str(IMAGES / "test_128x80_quantized.png"), "-o", str(out), "-q"])
    assert r.exit_code == 0, r.output
    pl = build_parts_list(read_layout(out))
    assert pl.unverified_lots == ()
    assert {l.color_key for l in pl.lots} >= {"lego_bright_red", "lego_white", "lego_nougat"}
    exported = CliRunner().invoke(cli, ["parts", "export", str(out), "--rebrickable", str(tmp_path / "i.csv")])
    assert exported.exit_code == 0, exported.output


def test_kit_part_colors_lists_wider_table():
    r = CliRunner().invoke(cli, ["kit", "part-colors", "--format", "json"])
    assert r.exit_code == 0
    rows = json.loads(r.output)["colors"]
    assert sum(1 for x in rows if x["part_id"] == "6141") == 44
    assert sum(1 for x in rows if x["part_id"] == "98138") == 40
    table = load_part_colors()
    assert table.get("98138", "lego_bright_red").bricklink.id == 5

"""Build sheets for recipe and image layouts (006 T020; US2, SC-002)."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from lego_image_processor.cli.main import cli
from lego_image_processor.maps.build import build_map
from lego_image_processor.maps.recipe import bundled_recipes, load_recipe
from lego_image_processor.parts import read_layout
from lego_image_processor.sheets import build_sheet_set, render_svg
from lego_image_processor.sheets.model import Circle, Text

IMAGES = Path(__file__).resolve().parents[1] / "fixtures" / "images"


def _text(page):
    return " ".join(i.text for i in page.items if isinstance(i, Text))


def _check_studs(layout, s):
    entries = {(e.lot.part_id, e.lot.color_key): e for e in s.legend}
    by_xy = {(p.x, p.y): entries[(p.lego_part_id, p.color_id)] for p in layout.grid.positions}
    n = 0
    for page in s.pages:
        for c in page.items:
            if isinstance(c, Circle) and c.tag == "stud":
                d = dict(c.data)
                e = by_xy[(int(d["x"]), int(d["y"]))]
                assert c.fill == e.rgb and int(d["lot"]) == e.number
                n += 1
    assert n == 10240


@pytest.mark.parametrize("recipe_id", sorted(bundled_recipes()))
def test_every_bundled_recipe(fixture_registry, tmp_path, recipe_id):
    """SC-002 on every bundled recipe (dataset fixtures); provenance on the overview."""
    fixture_registry.place_all()
    result = build_map(load_recipe(recipe_id))
    path = tmp_path / f"{recipe_id}.json"
    path.write_text(result.layout.to_json(), encoding="utf-8")
    layout = read_layout(path)
    s = build_sheet_set(layout)
    _check_studs(layout, s)
    overview = _text(s.pages[0])
    recipe = result.layout.map_metadata["recipe"]
    assert recipe["id"] in overview and recipe["title"] in overview and s.title == recipe["title"]
    assert layout.sha256 in overview
    for layer in result.layout.map_metadata["layers"]:
        ds = layer.get("dataset")
        if ds:
            assert ds["license"] in overview and ds["citation"] in overview
    assert "without cited IDs" not in overview


def test_image_fixture_layout(tmp_path):
    out = tmp_path / "img.json"
    r = CliRunner().invoke(cli, ["layout", str(IMAGES / "test_128x80_quantized.png"), "-o", str(out), "-q"])
    assert r.exit_code == 0, r.output
    layout = read_layout(out)
    s = build_sheet_set(layout)
    _check_studs(layout, s)
    overview = _text(s.pages[0])
    assert f"Source image: {layout.grid.source_image}" in overview and "img.json" == s.title
    assert all(e.verified for e in s.legend)
    files = render_svg(s)
    assert len(files) == len(s.pages)

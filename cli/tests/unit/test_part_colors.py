"""Part-color table (FR-016; data-model.md PartColor; contracts/data-files.md part_colors.json)."""

import copy
import json

import pytest

from lego_image_processor.kit import load_kit_color_table
from lego_image_processor.kit.part_colors import (
    PART_COLORS_PATH, colors_for_part, load_part_colors, parse_part_colors,
)


@pytest.fixture(scope="module")
def raw():
    return json.loads(PART_COLORS_PATH.read_text(encoding="utf-8"))


def test_kit_colors_available_for_their_part():
    plate = {c.key for c in colors_for_part("6141")}
    tile = {c.key for c in colors_for_part("98138")}
    kit = load_kit_color_table()
    assert "lego_white" in plate
    assert {c.key for c in kit.colors if c.role == "ocean"} <= tile


def test_kit_rows_equal_kit_colors():
    kit = {c.key: c for c in load_kit_color_table().colors}
    for part in ("6141", "98138"):
        for c in colors_for_part(part):
            if c.in_kit:
                k = kit[c.key]
                assert (c.element_id, c.lego, c.bricklink, c.rebrickable, c.rgb) == \
                       (k.element_id, k.lego, k.bricklink, k.rebrickable, k.rgb)
                assert (k.role == "land") == (part == "6141")


def test_unknown_part():
    with pytest.raises(KeyError, match="3001"):
        colors_for_part("3001")


def test_get():
    t = load_part_colors()
    assert t.get("6141", "lego_white").lego.name == "White"
    assert t.get("6141", "lego_earth_blue").bricklink.name == "Dark Blue"  # 005: wider table
    assert t.get("6141", "lego_medium_blue") is None  # excluded by rule 5 (not on BrickLink 4073)
    assert t.get("98138", "lego_medium_blue") is not None


def test_every_row_has_ids_and_citations(raw):
    t = load_part_colors()
    for part, rows in t.parts.items():
        for c in rows:
            for cat in (c.lego, c.bricklink, c.rebrickable):
                assert cat.name and isinstance(cat.id, int)
            assert set(c.citations) >= {"lego", "bricklink", "rebrickable", "element"}


def _first_row(data):
    return data["parts"]["6141"][0]


def test_null_id_rejected(raw):
    data = copy.deepcopy(raw)
    _first_row(data)["bricklink"]["id"] = None
    with pytest.raises(ValueError, match="bricklink"):
        parse_part_colors(data)


def test_placeholder_rejected(raw):
    data = copy.deepcopy(raw)
    _first_row(data)["notes"] = "estimate from a photo"
    with pytest.raises(ValueError, match="estimate"):
        parse_part_colors(data)


def test_duplicate_key_rejected(raw):
    data = copy.deepcopy(raw)
    data["parts"]["6141"].append(copy.deepcopy(_first_row(data)))
    with pytest.raises(ValueError, match="unique"):
        parse_part_colors(data)


def test_kit_row_must_match_kit_table(raw):
    data = copy.deepcopy(raw)
    row = next(r for r in data["parts"]["6141"] if r["key"] == "lego_white")
    row["element_id"] = "999999"
    with pytest.raises(ValueError, match="kit_colors.json"):
        parse_part_colors(data)


def test_citation_must_resolve(raw):
    data = copy.deepcopy(raw)
    _first_row(data)["citations"]["lego"] = "nowhere"
    with pytest.raises(ValueError, match="nowhere"):
        parse_part_colors(data)


def test_terms_are_required(raw):
    """005 FR-002: Rebrickable's confirmed terms replace the open license note."""
    from lego_image_processor.kit.part_colors import parse_part_colors
    assert raw["source"]["terms"]["text"].startswith("Free for personal and commercial use")
    assert "license_note" not in raw["source"]
    bad = copy.deepcopy(raw)
    bad["source"].pop("terms")
    with pytest.raises(ValueError, match="terms"):
        parse_part_colors(bad)


# --- feature 016 (T014): the 1x1 square tile 3070b, not in the kit (research R10) ---------------

def test_parts_are_exactly_the_kit_parts_and_the_square_tile(raw):
    from lego_image_processor.kit.part_colors import KIT_PARTS, PARTS
    assert PARTS == ("6141", "98138", "3070b") and KIT_PARTS == ("6141", "98138")
    assert list(load_part_colors().parts) == ["6141", "98138", "3070b"]
    missing = copy.deepcopy(raw)
    missing["parts"].pop("3070b")
    with pytest.raises(ValueError, match="exactly"):
        parse_part_colors(missing)
    extra = copy.deepcopy(raw)
    extra["parts"]["3001"] = extra["parts"]["3070b"]
    with pytest.raises(ValueError, match="exactly"):
        parse_part_colors(extra)


def test_square_tile_colors():
    t = load_part_colors()
    rows = t.for_part("3070b")
    assert rows == tuple(colors_for_part("3070b"))
    assert rows and not any(c.in_kit for c in rows)
    black = t.get("3070b", "lego_black")
    assert black is not None and black.lego.name == "Black" and black.bricklink.name == "Black"
    assert black.part_id == "3070b" and black.element_id.isdigit()


def test_square_tile_row_cannot_be_in_kit(raw):
    data = copy.deepcopy(raw)
    data["parts"]["3070b"][0]["in_kit"] = True
    with pytest.raises(ValueError, match="3070b"):
        parse_part_colors(data)


def test_kit_blocks_and_citations_equal_the_golden_digests():
    """SC-001: the 6141 and 98138 blocks and their citations are those of commit 6038d9c (as af3ce57)."""
    from pathlib import Path

    from maptemplates.golden import reference_digests
    golden = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "golden" /
                         "kit_outputs.json").read_text(encoding="utf-8"))
    assert reference_digests() == golden["reference_data"]

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

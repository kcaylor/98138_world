"""Loader tests for the curated, cited kit color table (kit_colors.json)."""

import json
import socket

import pytest

from lego_image_processor.kit import colors as kit_colors_mod
from lego_image_processor.kit import CatalogColor, KitColor, load_kit_colors
from lego_image_processor.kit.colors import KIT_COLORS_PATH, load_kit_color_table


@pytest.fixture
def no_network(monkeypatch):
    def guard(*a, **k):
        raise AssertionError("network access attempted")
    monkeypatch.setattr(socket, "socket", guard)
    monkeypatch.setattr(socket, "create_connection", guard)


def test_ten_colors_offline(no_network):
    load_kit_color_table.cache_clear()
    colors = load_kit_colors()
    assert len(colors) == 10
    assert all(isinstance(c, KitColor) for c in colors)


def test_keys_roles_and_ids():
    colors = load_kit_colors()
    keys = [c.key for c in colors]
    assert len(set(keys)) == 10
    assert [c.role for c in colors].count("land") == 1
    assert [c.role for c in colors].count("ocean") == 9
    assert colors[0].key == "lego_white" and colors[0].role == "land"
    assert len({c.lego.id for c in colors}) == 10
    for c in colors:
        for cat in (c.lego, c.bricklink, c.rebrickable):
            assert isinstance(cat, CatalogColor)
            assert cat.name and isinstance(cat.id, int)
        assert c.key.startswith("lego_")
        assert len(c.rgb) == 3 and all(0 <= v <= 255 for v in c.rgb)
        assert c.element_id


def test_expected_mappings():
    by_key = {c.key: c for c in load_kit_colors()}
    bbg = by_key["lego_bright_bluish_green"]
    assert (bbg.lego.name, bbg.lego.id) == ("Bright Bluish Green", 107)
    assert (bbg.bricklink.name, bbg.bricklink.id) == ("Dark Turquoise", 39)
    assert (bbg.rebrickable.name, bbg.rebrickable.id) == ("Dark Turquoise", 3)
    assert bbg.rgb == (0, 143, 155)
    assert bbg.element_id == "6311437"
    assert by_key["lego_white"].element_id == "614101"
    assert by_key["lego_earth_blue"].bricklink.id == 63


def test_every_citation_resolves():
    table = load_kit_color_table()
    for c in table.colors:
        assert set(c.citations) == {"lego", "bricklink", "rebrickable", "element"}
        for cit in c.citations.values():
            assert cit.url.startswith("http")
            assert table.source.citation(cit.id) == cit


def test_no_estimates_or_placeholders():
    raw = KIT_COLORS_PATH.read_text(encoding="utf-8").lower()
    for word in ("estimate", "placeholder", "unverified", "todo", "tbd"):
        assert word not in raw


def test_source_block():
    src = load_kit_color_table().source
    assert src.pages == [159]
    assert src.generator == "curated by hand"
    assert {c.id for c in src.citations} == {"ldraw", "bricklink", "rebrickable", "brickset"}


def _write_variant(tmp_path, mutate):
    data = json.loads(KIT_COLORS_PATH.read_text(encoding="utf-8"))
    mutate(data)
    path = tmp_path / "kit_colors.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.mark.parametrize("mutate,rule", [
    (lambda d: d["colors"].pop(), "10"),
    (lambda d: d["colors"][1].update(key="lego_white"), "unique"),
    (lambda d: d["colors"][1].update(role="land"), "land"),
    (lambda d: d["colors"][2]["bricklink"].update(id=None), "bricklink"),
    (lambda d: d["colors"][3]["citations"].update(rebrickable="nowhere"), "citation"),
    (lambda d: d["colors"][4]["lego"].update(id=1), "lego.id"),
    (lambda d: d["colors"][5].update(notes="estimate"), "estimate"),
])
def test_malformed_copy_rejected(tmp_path, mutate, rule):
    path = _write_variant(tmp_path, mutate)
    with pytest.raises(ValueError) as info:
        kit_colors_mod.load_kit_color_table(path)
    assert str(path.name) in str(info.value)
    assert rule in str(info.value)

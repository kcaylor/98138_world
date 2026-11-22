"""The official kit 31203 design shipped as package data (feature 003 US2)."""

import copy
import json

import pytest

from lego_image_processor.kit import (
    DesignGrid, Section, UnsupportedKitError, load_kit_colors, load_official_design,
)
from lego_image_processor.kit.design import DESIGN_PATH, SECTION_PAGES, parse_design


@pytest.fixture(scope="module")
def design():
    return load_official_design()


@pytest.fixture
def raw():
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


class TestLoad:
    def test_dimensions(self, design):
        assert isinstance(design, DesignGrid)
        assert (design.width, design.height) == (128, 80)
        assert len(design.rows) == 80 and all(len(r) == 128 for r in design.rows)

    def test_exactly_ten_kit_colors(self, design):
        keys = {design.color_at(x, y) for y in range(80) for x in range(128)}
        assert keys == {c.key for c in load_kit_colors()}
        assert design.palette == [c.key for c in load_kit_colors()]

    def test_counts(self, design):
        assert sum(c.used for c in design.counts) == 10240
        for c in design.counts:
            assert c.spare == c.supplied - c.used
            assert c.spare >= 0
        white = next(c for c in design.counts if c.key == "lego_white")
        assert (white.used, white.supplied) == (3062, 3064)

    def test_sections(self, design):
        assert len(design.sections) == 40
        assert all(isinstance(s, Section) for s in design.sections)
        assert len({(s.col, s.row) for s in design.sections}) == 40
        assert {(s.col, s.row) for s in design.sections} == {(c, r) for c in range(8) for r in range(5)}
        assert sorted(s.page for s in design.sections) == sorted(SECTION_PAGES)
        assert all(s.order_check for s in design.sections)
        assert {tuple(s.image_size) for s in design.sections} == {(154, 154), (154, 153)}
        assert design.source.pages == list(SECTION_PAGES)

    def test_classification_all_resolved(self, design):
        cl = design.classification
        assert cl["flagged"] == cl["resolved"]
        assert cl["ambiguity_ratio_threshold"] == 0.6

    def test_color_at_and_land_positions(self, design):
        land = design.land_positions()
        assert len(land) == 3062
        x, y = next(iter(land))
        assert design.color_at(x, y) == "lego_white"
        assert design.color_at(0, 0) != "lego_white"
        with pytest.raises(IndexError):
            design.color_at(128, 0)

    def test_cached(self):
        assert load_official_design() is load_official_design()

    def test_unsupported_kit(self):
        with pytest.raises(UnsupportedKitError):
            load_official_design("10000")


class TestValidation:
    @pytest.mark.parametrize("mutate,rule", [
        (lambda d: d.update(width=127), "128"),
        (lambda d: d["rows"].pop(), "80 rows"),
        (lambda d: d["rows"].__setitem__(0, d["rows"][0][:-1]), "128"),
        (lambda d: d["rows"].__setitem__(0, "z" + d["rows"][0][1:]), "palette"),
        (lambda d: d["palette"].__setitem__(9, "lego_purple"), "palette"),
        (lambda d: d["sections"].pop(), "40 sections"),
        (lambda d: d["sections"][1].update(col=0, row=0), "unique"),
        (lambda d: d["sections"][0].update(page=23), "pages"),
        (lambda d: d["sections"][0].update(order_check=False), "order_check"),
        (lambda d: d["sections"][0].update(image_size=[247, 247]), "image_size"),
        (lambda d: d["counts"][0].update(used=1), "used"),
        (lambda d: d["counts"][0].update(spare=0), "spare"),
        (lambda d: d["classification"].update(resolved=d["classification"]["flagged"] + 1), "flagged"),
        (lambda d: d["source"].update(sha256="0" * 64), "sha256"),
    ])
    def test_malformed_copy_raises_naming_rule(self, raw, mutate, rule):
        data = copy.deepcopy(raw)
        mutate(data)
        with pytest.raises(ValueError) as exc:
            parse_design(data, "copy.json")
        assert "copy.json" in str(exc.value)
        assert rule in str(exc.value)

    def test_nine_colors_rejected(self, raw):
        data = copy.deepcopy(raw)
        data["rows"] = [r.replace("9", "1") for r in data["rows"]]
        with pytest.raises(ValueError) as exc:
            parse_design(data, "copy.json")
        assert "10 distinct" in str(exc.value)

    def test_load_from_path(self, raw, tmp_path):
        p = tmp_path / "d.json"
        p.write_text(json.dumps(raw))
        assert load_official_design(path=p).width == 128

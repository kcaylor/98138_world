"""A map with the in-margin plaque (feature 017 T065; US3-1, US3-6, SC-009; FR-023;
contracts/in-margin-plaque.md "Layout JSON", "Counts" and "Report").

``ocean-sst`` on ``confirmed_winkel`` and the dataset fixtures, with and without the plaque in the
bottom-left corner: the plaque's 36 studs carry no piece, every other position (land, ocean and the
rest of the margin) equals the build without it, and the margin counts drop by the plaque's studs
while ``metadata.template`` keeps the template's own counts. Counts come from the loaded template.
Not affiliated with or endorsed by The LEGO Group.
"""

import json

import pytest

from lego_image_processor.maps.build import build_map
from lego_image_processor.maps.margin import MarginTreatment, resolve_margin
from lego_image_processor.maps.recipe import bundled_recipes, load_recipe, parse_recipe

STUDS = {"row": 73, "col": 1, "height": 6, "width": 6}


@pytest.fixture
def data(fixture_registry):
    return fixture_registry.place_all()


def _plaque(corner="bottom-left", ring=None):
    return MarginTreatment(ring=ring, plaque=corner, plaque_source="option")


def _build(margin=None, recipe=None):
    return build_map(recipe or load_recipe("ocean-sst"), template="winkel-tripel", margin=margin)


def _by_stud(layout):
    return {(p.x, p.y): p.to_dict() for p in layout.positions}


@pytest.fixture
def pair(confirmed_winkel, data):
    return _build(), _build(_plaque())


class TestOceanSstBottomLeft:
    def test_other_positions_equal_the_build_without_it(self, pair):  # US3-1, SC-009
        plain, plaque = pair
        covered = plaque.plaque.positions()
        a, b = _by_stud(plain.layout), _by_stud(plaque.layout)
        assert len(covered) == 36 and not covered & set(b)
        assert set(a) - set(b) == covered
        assert all(b[k] == a[k] for k in b)  # land, ocean and the other margin positions
        for kind in ("land_positions", "ocean_positions"):
            assert getattr(plaque.layout, kind) == getattr(plain.layout, kind)
        assert all(a[k]["part_type"] == "square_tile" for k in covered)

    def test_layout_metadata(self, pair, confirmed_winkel):
        plain, plaque = pair
        c = confirmed_winkel.counts
        d = json.loads(plaque.layout.to_json())
        m = d["metadata"]
        assert m["plaque"] == {"part_id": "10202", "color": "lego_black", "corner": "bottom-left",
                               "studs": STUDS, "cells": 36}
        assert len(d["positions"]) == 10204
        assert m["margin_positions"] == c["margin"] - 36
        assert m["map"]["margin"]["cells"] == {"margin": c["margin"] - 36, "ring": 0}
        assert m["template"] == json.loads(plain.layout.to_json())["metadata"]["template"]
        assert m["template"]["counts"]["margin"] == c["margin"]
        assert m["margin_positions"] + m["plaque"]["cells"] == m["template"]["counts"]["margin"]
        s = d["statistics"]
        assert (s["margin_tile_count"], s["plaque_tile_count"]) == (c["margin"] - 36, 1)
        p = json.loads(plain.layout.to_json())
        assert "plaque" not in p["metadata"] and "plaque_tile_count" not in p["statistics"]

    def test_report(self, pair, confirmed_winkel):
        plain, plaque = pair
        c = confirmed_winkel.counts
        rm = plaque.report["margin"]
        assert rm["plaque"] == {"corner": "bottom-left", "source": "option", "studs": STUDS, "part_id": "10202"}
        assert rm["cells"] == {"margin": c["margin"] - 36, "ring": 0}
        assert {k: v for k, v in rm.items() if k not in ("plaque", "cells")} == \
            {k: v for k, v in plain.report["margin"].items() if k != "cells"}
        assert "plaque" not in plain.report["margin"]
        assert plaque.report["template"] == plain.report["template"]  # the template's own counts

    def test_everything_else_equal(self, pair):
        """The layout JSON differs from the build without the plaque only where the plaque is."""
        plain, plaque = (json.loads(r.layout.to_json()) for r in pair)
        for d in (plain, plaque):
            d["metadata"].pop("generated_at")
        covered = {(x, y) for y in range(73, 79) for x in range(1, 7)}
        plain["positions"] = [p for p in plain["positions"] if (p["x"], p["y"]) not in covered]
        assert plain["positions"] == plaque["positions"]
        pm, qm = plain["metadata"], plaque["metadata"]
        assert {k: v for k, v in pm.items() if k not in ("margin_positions", "map")} == \
            {k: v for k, v in qm.items() if k not in ("margin_positions", "map", "plaque")}
        assert {k: v for k, v in pm["map"].items() if k != "margin"} == \
            {k: v for k, v in qm["map"].items() if k != "margin"}

    def test_with_a_ring(self, confirmed_winkel, data):
        t = confirmed_winkel
        plain = _build(MarginTreatment(ring="lego_bright_yellow"))
        plaque = _build(_plaque("bottom-left", "lego_bright_yellow"))
        a, b = _by_stud(plain.layout), _by_stud(plaque.layout)
        ring = {k for k, v in a.items() if v["color_id"] == "lego_bright_yellow"}
        assert len(ring) == t.counts["ring"] and ring <= set(b)  # the plaque never covers the ring
        assert plaque.report["margin"]["cells"] == {"margin": t.counts["margin"] - t.counts["ring"] - 36,
                                                    "ring": t.counts["ring"]}

    @pytest.mark.parametrize("corner", ["top-left", "top-right", "bottom-right"])
    def test_other_corners(self, confirmed_winkel, data, corner):
        r = _build(_plaque(corner))
        assert len(r.layout.positions) == 10204 and r.report["margin"]["plaque"]["corner"] == corner


class TestRecipeCorner:
    TABLE = '\n[margin]\nplaque = "top-left"\n'

    def _recipe(self):
        return parse_recipe(bundled_recipes()["ocean-sst"].read_text(encoding="utf-8") + self.TABLE)

    def test_recipe_corner_is_placed(self, confirmed_winkel, data):
        r = _build(recipe=self._recipe())
        assert r.report["margin"]["plaque"]["source"] == "recipe"
        assert json.loads(r.layout.to_json())["metadata"]["plaque"]["corner"] == "top-left"

    def test_none_builds_without_a_plaque(self, confirmed_winkel, data):  # US3-6
        recipe = self._recipe()
        r = _build(resolve_margin(recipe.margin, plaque="none"), recipe=recipe)
        assert r.plaque is None and len(r.layout.positions) == 10240
        assert "plaque" not in json.loads(r.layout.to_json())["metadata"]
        assert "plaque" not in r.report["margin"]

    def test_kit_build_places_nothing(self, data):  # E2: the recipe key is ignored on the kit
        r = build_map(self._recipe())
        assert r.plaque is None and len(r.layout.positions) == 10240
        assert "plaque" not in json.loads(r.layout.to_json())["metadata"]

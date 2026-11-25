"""Maps on the Winkel tripel template (T056; US1-1 - US1-5, FR-006 - FR-013, SC-002, SC-004;
contracts/recipe-and-outputs.md; data-model.md Layout (extended), SuitabilityReport, TemplateDataset).

Runs on ``confirmed_winkel`` (the package template with a test confirmation until the owner
confirms it) and the dataset fixtures. Counts come from the loaded template, never from examples.
Not affiliated with or endorsed by The LEGO Group.
"""

import json

import numpy as np
import pytest

from lego_image_processor.datasets.registry import load_registry
from lego_image_processor.kit.part_colors import load_part_colors
from lego_image_processor.maps.build import build_map, check_recipe
from lego_image_processor.maps.margin import MarginTreatment, ring_cells
from lego_image_processor.maps.recipe import bundled_recipes, load_recipe, parse_recipe
from lego_image_processor.templates import KIT_TEMPLATE_ID, PACKAGED_REGISTRY

ELIGIBLE = ("land-elevation", "living-planet", "ocean-sst", "official-31203-bathymetry", "rainfall")
PART_FOR_TYPE = {"plate": "6141", "tile": "98138", "square_tile": "3070b"}
TEMPLATE_KEYS = {"template", "template_source", "margin"}


@pytest.fixture
def data(fixture_registry):
    return fixture_registry.place_all()


@pytest.fixture
def sst(confirmed_winkel, data):
    return build_map(load_recipe("ocean-sst"), template="winkel-tripel")


def _with_key(rid, line):
    """A bundled recipe's text with one top-level line added after its seed."""
    text = bundled_recipes()[rid].read_text(encoding="utf-8")
    return parse_recipe(text.replace("seed = 31203\n", f"seed = 31203\n{line}\n", 1))


def _with_table(rid, table):
    """A bundled recipe's text with a top-level table appended."""
    return parse_recipe(bundled_recipes()[rid].read_text(encoding="utf-8") + "\n" + table)


def _strip(d):
    d = json.loads(d) if isinstance(d, str) else dict(d)
    d.get("metadata", {}).pop("generated_at", None)
    d.pop("generated_at", None)
    return d


class TestOceanSst:
    def test_counts_equal_the_template(self, sst, confirmed_winkel):  # US1-1, SC-002 on fixtures
        c = confirmed_winkel.counts
        lay = sst.layout
        assert lay.total_positions == len(lay.positions) == 10240
        assert (lay.land_positions, lay.ocean_positions, lay.margin_positions) == (c["land"], c["ocean"], c["margin"])
        d = json.loads(lay.to_json())
        assert d["metadata"]["margin_positions"] == c["margin"]
        assert d["statistics"]["margin_tile_count"] == c["margin"]
        assert sum(d["statistics"]["color_frequency_by_part_type"]["square_tile"].values()) == c["margin"]

    def test_parts_and_colors(self, sst, confirmed_winkel):  # US1-4
        t = confirmed_winkel
        table = load_part_colors()
        for p in sst.layout.positions:
            cls = t.class_at(p.y, p.x)
            want = {"land": "plate", "ocean": "tile", "margin": "square_tile"}[cls]
            assert p.part_type == want and p.lego_part_id == PART_FOR_TYPE[want]
            assert table.get(p.lego_part_id, p.color_id) is not None
            if cls == "margin":
                assert p.color_id == "lego_black" and p.lego_color_code == "26"

    def test_metadata_template(self, sst, confirmed_winkel):
        t = confirmed_winkel
        m = json.loads(sst.layout.to_json())["metadata"]
        rec = m["template"]
        assert rec["id"] == "winkel-tripel" and rec["title"] == t.title
        assert rec["projection"] == {"name": "winkel-tripel", "proj": "+proj=wintri +lat_1=50.4598 +lon_0=11.1 +R=1"}
        assert rec["board"] == {"modules": [8, 5], "width": 128, "height": 80}
        assert rec["parts"] == {"land": "6141", "ocean": "98138", "margin": "3070b"}
        assert rec["counts"] == {k: t.counts[k] for k in ("land", "ocean", "margin", "ring")}
        src = rec["source"]
        assert src["file"] == "templates/winkel-tripel.json"
        assert src["sha256"] == t.file_sha256 and len(src["sha256"]) == 64
        assert src["layout_sha256"] == t.layout_sha256
        assert src["confirmation"] == {"role": "project owner", "date": t.confirmation.date}
        entry = load_registry(PACKAGED_REGISTRY).get("etopo2022-surface-10m")
        assert rec["dataset"] == {"id": entry.id, "version": entry.version, "title": entry.title,
                                  "publisher": entry.publisher, "license": entry.license,
                                  "citation": entry.citation, "doi": entry.doi}
        assert m["arrangement"]["id"] == "A"
        assert m["map"]["margin"] == {"part_id": "3070b", "color": "lego_black", "ring": None,
                                      "cells": {"margin": t.counts["margin"], "ring": 0}}

    def test_report(self, sst, confirmed_winkel):  # FR-013
        t = confirmed_winkel
        rep = sst.report
        assert rep["template"] == {"id": "winkel-tripel", "title": t.title,
                                   "counts": {k: t.counts[k] for k in ("land", "ocean", "margin", "ring")},
                                   "dataset": t.dataset.to_dict()}
        assert rep["template_source"] == "option"
        assert rep["margin"] == json.loads(sst.layout.to_json())["metadata"]["map"]["margin"]
        ids = [c["id"] for c in rep["citations"]]
        assert ids == ["ersst-v5-ltm-1991-2020", "etopo2022-surface-10m"]  # once, after the recipe's
        assert rep["citations"][-1] == t.dataset.to_dict()
        ocean = rep["layers"][1]
        assert ocean["cells"] + rep["shadow"]["cells"] == t.counts["ocean"]
        assert rep["layers"][0]["cells"] == t.counts["land"]

    def test_check_agrees(self, sst):
        rep = check_recipe(load_recipe("ocean-sst"), template="winkel-tripel")
        assert _strip(rep) == _strip(sst.report)

    def test_deterministic(self, sst):
        again = build_map(load_recipe("ocean-sst"), template="winkel-tripel")
        assert _strip(again.layout.to_json()) == _strip(sst.layout.to_json())


class TestRing:
    def test_ring_color_colors_exactly_the_ring(self, confirmed_winkel, data):  # US1-5
        t = confirmed_winkel
        r = build_map(load_recipe("ocean-sst"), template="winkel-tripel",
                      margin=MarginTreatment("lego_black", "lego_bright_yellow"))
        ring = ring_cells(t)
        got = np.zeros_like(ring)
        for p in r.layout.positions:
            if p.color_id == "lego_bright_yellow":
                assert p.part_type == "square_tile"
                got[p.y, p.x] = True
            elif p.part_type == "square_tile":
                assert p.color_id == "lego_black"
        assert (got == ring).all() and int(got.sum()) == t.counts["ring"]
        cells = json.loads(r.layout.to_json())["metadata"]["map"]["margin"]["cells"]
        assert cells == {"margin": t.counts["margin"] - t.counts["ring"], "ring": t.counts["ring"]}

    def test_recipe_margin_table(self, confirmed_winkel, data):
        r = build_map(_with_table("ocean-sst", '[margin]\ncolor = "lego_dark_stone_grey"\nring = "lego_white"\n'),
                      template="winkel-tripel")
        margin = r.report["margin"]
        assert (margin["color"], margin["ring"]) == ("lego_dark_stone_grey", "lego_white")
        colors = {p.color_id for p in r.layout.positions if p.part_type == "square_tile"}
        assert colors == {"lego_dark_stone_grey", "lego_white"}


class TestResolution:
    def test_recipe_key_used(self, confirmed_winkel, data):  # US1-2
        r = build_map(_with_key("ocean-sst", 'template = "winkel-tripel"'))
        assert r.layout.template["id"] == "winkel-tripel" and r.report["template_source"] == "recipe"

    def test_option_kit_wins_and_is_unchanged(self, confirmed_winkel, data):  # US1-2, US1-3
        keyed = build_map(_with_key("ocean-sst", 'template = "winkel-tripel"'), template=KIT_TEMPLATE_ID)
        plain = build_map(load_recipe("ocean-sst"))
        a, b = _strip(keyed.layout.to_json()), _strip(plain.layout.to_json())
        assert a["positions"] == b["positions"] and a["statistics"] == b["statistics"]
        a["metadata"]["map"]["recipe"].pop("sha256"), b["metadata"]["map"]["recipe"].pop("sha256")
        assert a == b
        ra, rb = _strip(keyed.report), _strip(plain.report)
        ra.pop("recipe_sha256"), rb.pop("recipe_sha256")
        assert ra == rb and not TEMPLATE_KEYS & set(ra)

    def test_margin_on_a_kit_build_changes_nothing(self, data):
        with_margin = build_map(_with_table("ocean-sst", '[margin]\nring = "lego_white"\n'))
        plain = build_map(load_recipe("ocean-sst"))
        a, b = _strip(with_margin.layout.to_json()), _strip(plain.layout.to_json())
        assert a["positions"] == b["positions"]
        assert "template" not in a["metadata"] and "margin" not in a["metadata"]["map"]
        assert with_margin.margin is None and with_margin.template.id == KIT_TEMPLATE_ID


class TestKitOutputsHaveNoTemplateKeys:
    def test_kit_layout_and_report(self, data):
        r = build_map(load_recipe("ocean-sst"))
        d = json.loads(r.layout.to_json())
        assert not {"template", "margin_positions"} & set(d["metadata"])
        assert "margin" not in d["metadata"]["map"]
        assert "margin_tile_count" not in d["statistics"]
        assert set(d["statistics"]["color_frequency_by_part_type"]) == {"plate", "tile"}
        assert not TEMPLATE_KEYS & set(r.report)
        assert [c["id"] for c in r.report["citations"]] == ["ersst-v5-ltm-1991-2020"]


@pytest.mark.parametrize("rid", ELIGIBLE)
def test_eligible_recipes_build(rid, confirmed_winkel, data):  # SC-004, SC-002 on fixtures
    t = confirmed_winkel
    r = build_map(load_recipe(rid), template="winkel-tripel")
    lay = r.layout
    assert (lay.land_positions, lay.ocean_positions, lay.margin_positions) == (
        t.counts["land"], t.counts["ocean"], t.counts["margin"])
    assert lay.land_positions <= 3064 and lay.ocean_positions <= 8066
    ids = [c["id"] for c in r.report["citations"]]
    assert ids.count("etopo2022-surface-10m") == 1
    assert r.agreement is None

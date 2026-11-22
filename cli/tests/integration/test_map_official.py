"""Exact acceptance tier (FR-004-FR-006, FR-012, FR-020, SC-001): official-31203 from its recipe."""

import json

import pytest

from lego_image_processor.kit import load_official_design
from lego_image_processor.layout.grid import PositionPlacementGrid
from lego_image_processor.layout.kit_spec import load_kit_specification
from lego_image_processor.layout.validator import LayoutValidator
from lego_image_processor.maps.build import build_map
from lego_image_processor.maps.recipe import load_recipe
from lego_image_processor.palette.loader import LegoPalette

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    empty = tmp_path_factory.mktemp("empty-cache")
    return build_map(load_recipe("official-31203"), cache_dir=empty)


def test_matches_official_design_exactly(built):
    official = {(p.x, p.y): p for p in load_official_design().to_layout().positions}
    ours = built.layout.positions
    assert len(ours) == 10_240
    same = sum(1 for p in ours if (p.color_id, p.part_type, p.lego_part_id, p.color_name, p.lego_color_code)
               == (official[(p.x, p.y)].color_id, official[(p.x, p.y)].part_type,
                   official[(p.x, p.y)].lego_part_id, official[(p.x, p.y)].color_name,
                   official[(p.x, p.y)].lego_color_code))
    assert same == 10_240
    assert built.layout.land_positions == 3_062
    assert built.agreement["total"] == {"agree": 10_240, "cells": 10_240}


def test_fully_buildable(built):
    report = LayoutValidator(load_kit_specification(), LegoPalette.load_default()).validate(built.layout, "x")
    assert report.buildable and report.violations == []


def test_deterministic(built, tmp_path):
    again = build_map(load_recipe("official-31203"), cache_dir=tmp_path)
    assert [p.to_dict() for p in again.layout.positions] == [p.to_dict() for p in built.layout.positions]


def test_provenance(built):
    meta = json.loads(built.layout.to_json())["metadata"]
    assert meta["schema_version"] == "2.0"
    assert meta["source_image"] == "recipe:official-31203"
    m = meta["map"]
    assert m["recipe"]["id"] == "official-31203" and m["recipe"]["format"] == "1"
    assert m["recipe"]["sha256"] == load_recipe("official-31203").sha256
    assert [l["role"] for l in m["layers"]] == ["background", "data"]
    ds = m["layers"][1]["dataset"]
    assert ds["id"] == "kit31203-design" and ds["license"] and ds["citation"]
    assert m["disclaimer"] == DISCLAIMER
    again = PositionPlacementGrid.from_json(built.layout.to_json())
    assert again.map_metadata == m

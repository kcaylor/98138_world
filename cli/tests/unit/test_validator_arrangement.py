"""validate checks the land/sea mask under the layout's arrangement (feature 007 US3, FR-012)."""

import pytest

from lego_image_processor.layout.arrangement import arrange_grid, parse_arrangement
from lego_image_processor.layout.grid import PositionPlacementGrid
from lego_image_processor.layout.kit_spec import load_kit_specification
from lego_image_processor.layout.validator import LayoutValidator
from lego_image_processor.maps.build import build_map
from lego_image_processor.maps.recipe import load_recipe
from lego_image_processor.palette.loader import LegoPalette


@pytest.fixture(scope="module")
def official():
    return build_map(load_recipe("official-31203")).layout


def _validate(grid):
    v = LayoutValidator(kit_spec=load_kit_specification("31203"), palette=LegoPalette.load_default())
    return v.validate(grid, layout_file="x.json")


@pytest.mark.parametrize("aid", ["A", "B", "C"])
def test_arranged_official_is_buildable(official, aid):
    r = _validate(arrange_grid(official, parse_arrangement(aid)))
    assert r.buildable, [v.to_dict() for v in r.violations]
    assert r.arrangement == aid
    assert r.to_dict()["arrangement"] == aid


def test_b_positions_labelled_a_fail(official):
    b = arrange_grid(official, parse_arrangement("B"))
    relabelled = PositionPlacementGrid(width=128, height=80, positions=b.positions, source_image="x",
                                       arrangement=None)
    r = _validate(relabelled)
    assert not r.buildable
    mm = [v for v in r.violations if v.type == "mask_mismatch"]
    assert len(mm) == 1
    d = mm[0].to_dict()
    assert d["arrangement"] == "A" and d["positions_required"] > 0
    assert len(d["examples"]) == 10
    assert r.buildability_score < 1.0

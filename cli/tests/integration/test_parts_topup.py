"""Kit top-up and performance (005 T031, T040; SC-001, SC-003, SC-006)."""

import time

import pytest

from lego_image_processor.kit import load_official_design
from lego_image_processor.parts import (OwnedInputs, build_parts_list, read_layout,
                                        to_bricklink_xml, to_rebrickable_csv)

from ..unit.parts.layouts import LAND_ELEVATION, make_grid


def test_official_with_one_kit_buys_nothing():
    design = load_official_design()
    pl = build_parts_list(design.to_layout(), owned=OwnedInputs(kits=1))
    assert pl.totals()["to_buy"] == 0 and pl.lots_to_buy == ()
    extras = {c.key: c.supplied - c.used for c in design.counts}
    assert {l.color_key: l.surplus for l in pl.lots} == extras
    white = next(l for l in pl.lots if l.color_key == "lego_white")
    assert white.surplus == 2
    assert to_bricklink_xml(pl) is None and to_rebrickable_csv(pl) is None


@pytest.mark.parametrize("kits,lots,pieces", [(0, 13, 10240), (1, 11, 6382), (2, 10, 4178), (3, 9, 2912)])
def test_land_elevation_top_up(kits, lots, pieces):
    """SC-003 on a synthetic layout with the real-data counts (research R6)."""
    pl = build_parts_list(make_grid(LAND_ELEVATION), owned=OwnedInputs(kits=kits))
    t = pl.totals()
    assert (t["lots_to_buy"], t["to_buy"]) == (lots, pieces)


def test_list_and_export_under_two_seconds(tmp_path):
    """SC-006: a 10,240-position layout, from file to both exports."""
    path = tmp_path / "official.json"
    path.write_text(load_official_design().to_layout().to_json(), encoding="utf-8")
    start = time.perf_counter()
    pl = build_parts_list(read_layout(path))
    pl.to_json()
    assert to_bricklink_xml(pl) and to_rebrickable_csv(pl)
    assert time.perf_counter() - start < 2.0

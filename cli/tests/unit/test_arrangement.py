"""Arrangements A, B, C of the kit's three frames (feature 007, FR-001-FR-003, FR-009, FR-010)."""

import json

import numpy as np
import pytest

from lego_image_processor.layout.arrangement import (
    ARRANGEMENT_IDS, ArrangementError, arrange_grid, arrangement_of, frames, load_arrangements,
    parse_arrangement)
from lego_image_processor.layout.grid import PositionPlacementGrid
from lego_image_processor.layout.position import PositionPlacement

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."


def test_data_file_is_cited():
    data = load_arrangements()
    src = data.source
    assert src["pages"] == [7, 8]
    assert src["citation"] == "LEGO 31203 building instructions, pp. 7–8"
    design = json.loads((__import__("lego_image_processor.kit.colors", fromlist=["DATA_DIR"]).DATA_DIR
                         / "kit_31203_design.json").read_text())["source"]
    assert src["url"] == design["url"] and src["sha256"] == design["sha256"]
    assert data.disclaimer == DISCLAIMER


def test_frames():
    f = frames()
    assert [(x.number, x.name, x.columns) for x in f] == [
        (1, "America", (0, 31)), (2, "Europe & Africa", (32, 95)), (3, "Asia & Australia", (96, 127))]
    assert [x.section_columns for x in f] == ["A-B", "C-F", "G-H"]


@pytest.mark.parametrize("aid,order,shift,name", [
    ("A", (1, 2, 3), 0, "europe-africa"), ("B", (3, 1, 2), 32, "americas"),
    ("C", (2, 3, 1), -32, "asia-australia")])
def test_arrangements(aid, order, shift, name):
    a = parse_arrangement(aid)
    assert (a.id, a.frame_order, a.column_shift, a.name) == (aid, order, shift, name)
    assert parse_arrangement(name) is a
    assert parse_arrangement(aid.lower()) is a
    assert parse_arrangement(name.upper()) is a


def test_ids():
    assert ARRANGEMENT_IDS == ("A", "B", "C")
    assert parse_arrangement(None).id == "A"


def test_unknown():
    with pytest.raises(ArrangementError, match="A, B, C, europe-africa, americas, asia-australia"):
        parse_arrangement("D")


def test_shift_matches_frame_order():
    """B: display 0-31 is frame 3 (kit 96-127); C: display 0-63 is frame 2 (kit 32-95)."""
    b, c = parse_arrangement("B"), parse_arrangement("C")
    assert [b.to_kit(x) for x in (0, 31, 32, 63, 64, 127)] == [96, 127, 0, 31, 32, 95]
    assert [c.to_kit(x) for x in (0, 63, 64, 95, 96, 127)] == [32, 95, 96, 127, 0, 31]
    for a in (b, c, parse_arrangement("A")):
        assert all(a.to_kit(a.to_display(x)) == x for x in range(128))


def test_roll_unroll():
    kit = np.arange(80 * 128).reshape(80, 128)
    for aid in ARRANGEMENT_IDS:
        a = parse_arrangement(aid)
        disp = a.roll(kit)
        assert disp[5, a.to_display(7)] == kit[5, 7]
        assert (a.unroll(disp) == kit).all()


@pytest.mark.parametrize("aid,spans,bounds", [
    ("A", [(1, 0, 31), (2, 32, 95), (3, 96, 127)], (32, 96)),
    ("B", [(3, 0, 31), (1, 32, 63), (2, 64, 127)], (32, 64)),
    ("C", [(2, 0, 63), (3, 64, 95), (1, 96, 127)], (64, 96))])
def test_spans_and_boundaries(aid, spans, bounds):
    a = parse_arrangement(aid)
    assert [(f.number, s, e) for f, s, e in a.frame_spans()] == spans
    assert a.boundaries() == bounds


def test_frame_of_display_column():
    b = parse_arrangement("B")
    assert [b.frame_at(x).number for x in (0, 31, 32, 63, 64, 127)] == [3, 3, 1, 1, 2, 2]


def test_record():
    r = parse_arrangement("B").record()
    assert r["id"] == "B" and r["name"] == "americas" and r["frame_order"] == [3, 1, 2]
    assert r["column_shift"] == 32 and r["centre"] == "America"
    assert r["source"]["pages"] == [7, 8] and r["source"]["sha256"]
    assert parse_arrangement("A").describe() == "A (europe-africa, frames 1·2·3, Europe and Africa in the centre)"


# --- layouts -----------------------------------------------------------------------------------

def _grid(n_rows=80, arrangement=None, width=128):
    pos = []
    for y in range(n_rows):
        for x in range(width):
            land = (x * 7 + y * 3) % 5 == 0
            pos.append(PositionPlacement(x=x, y=y, color_id="lego_white" if land else "lego_earth_blue",
                                         color_name="White" if land else "Earth Blue",
                                         lego_color_code="1" if land else "140",
                                         part_type="plate" if land else "tile",
                                         lego_part_id="6141" if land else "98138"))
    return PositionPlacementGrid(width=width, height=80, positions=pos, source_image="t.png",
                                 generated_at="2026-11-22T00:00:00Z",
                                 map_metadata={"recipe": {"id": "x"}}, arrangement=arrangement)


def test_grid_without_arrangement_is_a():
    g = _grid()
    assert arrangement_of(g).id == "A"
    assert "arrangement" not in json.loads(g.to_json())["metadata"]


def test_grid_round_trip_record():
    g = _grid(arrangement=parse_arrangement("C").record())
    data = json.loads(g.to_json())
    assert data["metadata"]["arrangement"]["id"] == "C"
    g2 = PositionPlacementGrid.from_json(g.to_json())
    assert arrangement_of(g2).id == "C"
    assert g2.arrangement == g.arrangement


def test_unknown_recorded_arrangement():
    g = _grid(arrangement={"id": "Z"})
    with pytest.raises(ArrangementError, match="Z"):
        arrangement_of(g)


def test_arrange_a_to_b_moves_columns():
    g = _grid()
    b = arrange_grid(g, parse_arrangement("B"))
    assert b.arrangement["id"] == "B"
    assert b.map_metadata == g.map_metadata and b.generated_at == g.generated_at
    for p in g.positions[:300]:
        q = b.get_position((p.x + 32) % 128, p.y)
        assert q.to_dict() | {"x": p.x} == p.to_dict()
    assert [(p.y, p.x) for p in b.positions] == sorted((p.y, p.x) for p in b.positions)


def test_arrange_b_to_c_equals_a_to_c():
    g = _grid()
    via = arrange_grid(arrange_grid(g, parse_arrangement("B")), parse_arrangement("C"))
    direct = arrange_grid(g, parse_arrangement("C"))
    assert [p.to_dict() for p in via.positions] == [p.to_dict() for p in direct.positions]


@pytest.mark.parametrize("aid", ["B", "C"])
def test_round_trip_is_byte_identical(aid):
    g = _grid()
    back = arrange_grid(arrange_grid(g, parse_arrangement(aid)), parse_arrangement("A"))
    a = json.loads(g.to_json())["positions"]
    b = json.loads(back.to_json())["positions"]
    assert json.dumps(a) == json.dumps(b)


def test_identity():
    g = _grid(arrangement=parse_arrangement("B").record())
    same = arrange_grid(g, parse_arrangement("B"))
    assert [p.to_dict() for p in same.positions] == [p.to_dict() for p in g.positions]


def test_partial_layout():
    g = _grid(n_rows=3)
    b = arrange_grid(g, parse_arrangement("B"))
    assert len(b.positions) == 3 * 128


def test_wrong_width():
    with pytest.raises(ArrangementError, match="128"):
        arrange_grid(_grid(n_rows=1, width=64), parse_arrangement("B"))


def test_position_outside_grid():
    g = _grid(n_rows=1)
    g.add_position(PositionPlacement(x=130, y=0, color_id="lego_white", color_name="White",
                                     lego_color_code="1", part_type="plate", lego_part_id="6141"))
    with pytest.raises(ArrangementError, match="outside"):
        arrange_grid(g, parse_arrangement("B"))

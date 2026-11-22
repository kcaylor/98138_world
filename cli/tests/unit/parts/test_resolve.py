"""resolve_color (005 T015, FR-005): cited IDs or a reason, never invented IDs."""

from lego_image_processor.parts import (REASON_CODE_MISMATCH, REASON_NO_COLOR, ResolvedColor,
                                        Unresolved, resolve_color)


def test_kit_plate_color():
    r = resolve_color("6141", "lego_white", "1")
    assert isinstance(r, ResolvedColor)
    assert (r.bricklink_item_type, r.bricklink_item_no, r.bricklink_color_id) == ("P", "4073", 1)
    assert (r.rebrickable_part_num, r.rebrickable_color_id) == ("6141", 15)
    assert (r.lego_name, r.lego_id, r.element_id) == ("White", 1, "614101")


def test_non_kit_plate_color_from_part_table():
    r = resolve_color("6141", "lego_brick_yellow", 5)
    assert isinstance(r, ResolvedColor)
    assert r.bricklink_item_no == "4073"
    assert (r.bricklink_color_name, r.bricklink_color_id) == ("Tan", 2)
    assert (r.rebrickable_color_name, r.rebrickable_color_id) == ("Tan", 19)


def test_tile_numbers():
    r = resolve_color("98138", "lego_bright_bluish_green", "107")
    assert (r.bricklink_item_no, r.rebrickable_part_num) == ("98138", "98138")
    assert (r.bricklink_color_id, r.rebrickable_color_id) == (39, 3)
    assert r.element_id == "6311437"
    assert {"bricklink-98138", "rebrickable-98138"} <= set(r.citation_ids)


def test_uncited_color():
    # Medium Blue is excluded for the plate (not on BrickLink's 4073 page) but cited for the tile
    assert resolve_color("6141", "lego_medium_blue", "102") == Unresolved(REASON_NO_COLOR)
    assert isinstance(resolve_color("98138", "lego_medium_blue", "102"), ResolvedColor)
    assert resolve_color("6141", "lego_unknown", "1") == Unresolved(REASON_NO_COLOR)
    assert resolve_color("3001", "lego_white", "1") == Unresolved(REASON_NO_COLOR)


def test_code_mismatch():
    assert resolve_color("6141", "lego_white", "2") == Unresolved(REASON_CODE_MISMATCH)
    assert resolve_color("6141", "lego_white", "x") == Unresolved(REASON_CODE_MISMATCH)
    assert resolve_color("6141", "lego_white", None) == Unresolved(REASON_CODE_MISMATCH)

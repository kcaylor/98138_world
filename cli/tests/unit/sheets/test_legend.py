"""Legend entries (006 T007, FR-003, FR-005)."""

from lego_image_processor.parts import build_parts_list
from lego_image_processor.sheets import build_legend, lot_numbers, text_color

from .layouts import every_cited_color, full_grid


def test_numbers_follow_parts_list_order(few_grid):
    pl = build_parts_list(few_grid)
    legend = build_legend(pl)
    assert [e.number for e in legend] == list(range(1, len(pl.lots) + 1))
    assert [e.lot for e in legend] == list(pl.lots)
    # Plates first, then tiles (005 lot order).
    assert [e.lot.part_type for e in legend] == ["plate"] * 3 + ["tile"] * 3


def test_same_color_on_plate_and_tile_gets_two_numbers(few_grid):
    legend = build_legend(build_parts_list(few_grid))
    green = [e for e in legend if e.lot.color_key == "lego_bright_green"]
    assert len(green) == 2 and {e.lot.part_type for e in green} == {"plate", "tile"}
    assert green[0].number != green[1].number
    numbers = lot_numbers(legend)
    assert numbers[("6141", "lego_bright_green")] != numbers[("98138", "lego_bright_green")]


def test_text_color_by_contrast():
    assert text_color((255, 255, 255)) == (0, 0, 0)
    assert text_color((0, 0, 0)) == (255, 255, 255)
    assert text_color((10, 57, 94)) == (255, 255, 255)  # Earth Blue
    assert text_color((228, 205, 158)) == (0, 0, 0)  # Brick Yellow


def test_verified_entry_uses_cited_rgb_and_ids(few_grid):
    legend = build_legend(build_parts_list(few_grid))
    white = next(e for e in legend if e.lot.color_key == "lego_white")
    assert white.verified and white.rgb == white.lot.ids.rgb
    assert white.text_color == (0, 0, 0)
    text = " ".join(white.label_lines)
    assert "White (1)" in text and "4073" in text and "6141" in text and "614101" in text
    tile = next(e for e in legend if e.lot.part_id == "98138")
    assert "98138" in " ".join(tile.label_lines)


def test_unverified_entry(uncited_grid):
    legend = build_legend(build_parts_list(uncited_grid))
    blue = next(e for e in legend if e.lot.color_key == "lego_medium_blue")
    assert not blue.verified
    text = " ".join(blue.label_lines)
    assert "no cited IDs" in text and "Medium Blue" in text and "102" in text
    assert "4073" not in text  # never an invented ID
    assert blue.rgb != (128, 128, 128)  # display colour from the 001 palette
    assert blue.number == len(legend)  # unverified lots come last (005 lot order)


def test_unknown_uncited_color_is_mid_grey():
    legend = build_legend(build_parts_list(full_grid(every_cited_color())))
    assert len(legend) == 90
    odd = next(e for e in legend if e.lot.color_key == "lego_uncited_0")
    assert odd.rgb == (128, 128, 128)
    assert all(line.encode("latin-1") for e in legend for line in e.label_lines)


# --- the square tile (feature 016 T066; data-model.md LegendRow) ---------------------------------

def test_square_tile_legend_row(confirmed_winkel):
    from lego_image_processor.kit.part_numbers import load_part_numbers
    from lego_image_processor.sheets.legend import PART_LABEL
    from ...winkel_layouts import winkel_grid
    legend = build_legend(build_parts_list(winkel_grid(confirmed_winkel)))
    sq = legend[-1]
    assert (sq.lot.part_type, sq.part_label) == ("square_tile", "tile 1x1 square") == \
        ("square_tile", PART_LABEL["square_tile"])
    first, second = sq.label_lines
    assert "Black (26) · tile 1x1 square · element 307026" == first
    item = load_part_numbers().get("3070b").bricklink_item_no
    assert f"BrickLink {item} / Black (11)" in second and "Rebrickable 3070b / Black (0)" in second

"""Sections of the kit board (006 T003, FR-001)."""

import pytest

from lego_image_processor.kit import load_official_design
from lego_image_processor.sheets import parse_section_labels, section_for, sections


def test_forty_sections_in_column_order():
    s = sections()
    assert len(s) == 40
    assert [x.label for x in s[:6]] == ["A1", "A2", "A3", "A4", "A5", "B1"]
    assert s[-1].label == "H5"


def test_ranges_cover_grid_exactly():
    seen = set()
    for s in sections():
        assert s.x_range == (16 * s.col, 16 * s.col + 15)
        assert s.y_range == (16 * s.row, 16 * s.row + 15)
        cells = {(x, y) for x in range(s.x_range[0], s.x_range[1] + 1)
                 for y in range(s.y_range[0], s.y_range[1] + 1)}
        assert len(cells) == 256 and not (cells & seen)
        seen |= cells
    assert seen == {(x, y) for x in range(128) for y in range(80)}


def test_c2_and_frames():
    c2 = next(s for s in sections() if s.label == "C2")
    assert (c2.col, c2.row, c2.x_range, c2.y_range, c2.frame) == (2, 1, (32, 47), (16, 31), 2)
    frames = {s.label[0]: s.frame for s in sections()}
    assert frames == {"A": 1, "B": 1, "C": 2, "D": 2, "E": 2, "F": 2, "G": 3, "H": 3}


def test_order_follows_instruction_pages():
    s = sections()
    pages = [x.instruction_page for x in s]
    assert pages == sorted(pages)
    design = {(d.col, d.row): d.page for d in load_official_design().sections}
    assert all(design[(x.col, x.row)] == x.instruction_page for x in s)
    assert [x.order for x in s] == list(range(1, 41))


def test_section_for():
    assert section_for(0, 0).label == "A1"
    assert section_for(127, 79).label == "H5"
    assert section_for(40, 20).label == "C2"
    with pytest.raises(ValueError):
        section_for(128, 0)


def test_parse_labels_board_order_and_errors():
    assert [s.label for s in parse_section_labels("C2,b2")] == ["B2", "C2"]
    assert [s.label for s in parse_section_labels(["H5", "A1", "A1"])] == ["A1", "H5"]
    assert len(parse_section_labels(None)) == 40
    with pytest.raises(ValueError, match=r"J9.*A1.*H5"):
        parse_section_labels("B2,J9")
    with pytest.raises(ValueError):
        parse_section_labels(" , ")

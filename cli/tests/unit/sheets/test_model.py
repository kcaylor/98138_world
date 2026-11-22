"""Page model (006 T005): paper sizes in mm, drawing items, Latin-1 text."""

import pytest

from lego_image_processor.sheets.model import (PAPERS, Circle, Line, Page, Rect, Text, is_latin1,
                                               latin1_safe, paper_size)


def test_paper_sizes():
    assert (PAPERS["letter"].width_mm, PAPERS["letter"].height_mm) == (215.9, 279.4)
    assert (PAPERS["a4"].width_mm, PAPERS["a4"].height_mm) == (210.0, 297.0)
    assert paper_size("A4") is PAPERS["a4"]
    with pytest.raises(ValueError, match="letter"):
        paper_size("legal")


def test_items_are_frozen_and_hashable():
    items = (Rect(1, 2, 3, 4, fill=(1, 2, 3)), Circle(1, 1, 0.5, fill=(0, 0, 0)),
             Line(0, 0, 1, 1), Text(1, 1, "A1", 9))
    page = Page(size=PAPERS["letter"], items=items, number=1, total=2, kind="overview")
    assert hash(page) == hash(Page(size=PAPERS["letter"], items=items, number=1, total=2,
                                   kind="overview"))
    with pytest.raises(AttributeError):
        items[0].x = 5


def test_latin1():
    assert is_latin1("Café · A1")
    assert not is_latin1("ΔE")
    assert is_latin1("16×16")  # the multiplication sign is Latin-1 (U+00D7)
    assert not is_latin1("≈")
    assert latin1_safe("ΔE ≈ 2") == "?E ? 2"
    assert latin1_safe("plain") == "plain"

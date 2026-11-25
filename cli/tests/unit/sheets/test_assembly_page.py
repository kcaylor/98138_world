"""Assembly page for every combination (feature 010 US2, FR-007-FR-010).

Not affiliated with or endorsed by The LEGO Group.
"""

import io

import pytest
from pypdf import PdfReader

from lego_image_processor.layout.arrangement import arrange_grid, parse_arrangement
from lego_image_processor.sheets import build_sheet_set, render_pdf, render_svg
from lego_image_processor.sheets.model import Line, Rect, Text

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."


def items(page, kind, tag):
    return [i for i in page.items if isinstance(i, kind) and i.tag == tag]


def joined(page):
    """All text of a page, wrapped lines joined with spaces."""
    return " ".join(i.text for i in page.items if isinstance(i, Text))


@pytest.fixture(scope="module")
def sets(official_grid):
    return {aid: build_sheet_set(arrange_grid(official_grid, parse_arrangement(aid)),
                                 layout_path=f"{aid}.json") for aid in "ABCDE"}


def assembly(s):
    pages = [p for p in s.pages if p.kind == "assembly"]
    assert len(pages) == 1
    return pages[0]


@pytest.mark.parametrize("aid", list("ABCDE"))
def test_one_assembly_page_last(sets, aid):
    s = sets[aid]
    kinds = [p.kind for p in s.pages]
    assert kinds[-1] == "assembly" and kinds.count("assembly") == 1
    assert kinds[:-1] == ["overview"] + ["legend"] * kinds.count("legend") + ["section"] * 40
    n = len(s.pages)
    assert [p.number for p in s.pages] == list(range(1, n + 1)) and all(p.total == n for p in s.pages)
    assert s.page_kinds["assembly"] == 1
    page = assembly(s)
    text = joined(page)
    assert DISCLAIMER in text and f"Page {n} of {n}" in text
    assert f"Assembly: combination {aid}" in text
    assert "pp. 140-153" in text and "201 of the 205" in text
    assert items(page, Line, "scale-bar") or any(i.tag.startswith("scale") for i in page.items)


def test_d_page(sets):
    page = assembly(sets["D"])
    text = joined(page)
    assert "not one of the three combinations in the building instructions" in text
    assert "pp. 134-140" in text
    assert "Unpeg frame 2 between strips D and E" in text and "15 connector pegs" in text
    assert "E F G H A B C D" in text and "2b · 3 · 1 · 2a" in text
    assert "F|G, H|A and B|C" in text
    strips = [dict(r.data)["strip"] for r in items(page, Rect, "strip")]
    assert strips == list("EFGHABCD")
    made = [dict(l.data)["joint"] for l in items(page, Line, "joint-make")]
    assert sorted(set(made)) == ["B|C", "F|G", "H|A"]
    assert [dict(l.data)["joint"] for l in items(page, Line, "joint-unpeg")][:1] == ["D|E"]
    groups = [dict(t.data)["group"] for t in items(page, Text, "group-label")]
    assert groups == ["2b", "3", "1", "2a"]


def test_e_page(sets):
    page = assembly(sets["E"])
    text = joined(page)
    assert "Unpeg frame 2 between strips C and D" in text
    assert [dict(r.data)["strip"] for r in items(page, Rect, "strip")] == list("DEFGHABC")
    assert sorted({dict(l.data)["joint"] for l in items(page, Line, "joint-make")}) == ["B|C", "F|G", "H|A"]


@pytest.mark.parametrize("aid,joints", [("A", ["B|C", "F|G"]), ("B", ["B|C", "H|A"]), ("C", ["F|G", "H|A"])])
def test_a_to_c_pages(sets, aid, joints):
    page = assembly(sets[aid])
    text = joined(page)
    assert "is one of the three combinations in the building instructions" in text
    assert "pp. 7-8 and 139" in text
    assert "Unpeg" not in text and not items(page, Line, "joint-unpeg")
    assert sorted({dict(l.data)["joint"] for l in items(page, Line, "joint-make")}) == joints


def test_overview_mentions_assembly_and_groups(sets):
    ov = joined(sets["D"].pages[0])
    assert "1 assembly page" in ov
    assert "frames 2b·3·1·2a" in ov and "not one of the three combinations" in ov
    assert "Frame 2b: Europe & Africa" in ov and "Frame 2a: Europe & Africa" in ov
    a = joined(sets["A"].pages[0])
    assert "1 assembly page" in a and "Combination A (europe-africa): frames 1·2·3" in a


def test_d_section_pages_name_the_part(sets):
    page = next(p for p in sets["D"].pages if p.kind == "section" and p.label == "A1")
    assert "frame 2 of 3 (Europe & Africa), part 2b · kit section E1" in joined(page)
    page = next(p for p in sets["D"].pages if p.kind == "section" and p.label == "C1")
    assert "frame 3 of 3 (Asia & Australia) · kit section G1" in joined(page)
    page = next(p for p in sets["B"].pages if p.kind == "section" and p.label == "A1")
    assert "part" not in joined(page).split("·")[1]


def test_subset_keeps_assembly(official_grid):
    s = build_sheet_set(arrange_grid(official_grid, parse_arrangement("D")), sections="A1")
    assert [p.kind for p in s.pages][-1] == "assembly" and s.page_kinds["section"] == 1


def test_renders_pdf_and_svg(sets):
    s = sets["D"]
    reader = PdfReader(io.BytesIO(render_pdf(s)))
    last = reader.pages[-1].extract_text()
    assert "Assembly: combination D" in last and DISCLAIMER in last
    files = render_svg(s)
    assert len(files) == len(s.pages)
    assert "Assembly: combination D" in files[-1][1] and 'class="joint-make"' in files[-1][1]


def test_drawn_inside_page(sets):
    for aid in "ABCDE":
        page = assembly(sets[aid])
        W, H = page.size.width_mm, page.size.height_mm
        for i in page.items:
            xs = [getattr(i, k) for k in ("x", "x1", "x2", "cx") if hasattr(i, k)]
            ys = [getattr(i, k) for k in ("y", "y1", "y2", "cy") if hasattr(i, k)]
            assert all(0 <= v <= W for v in xs) and all(0 <= v <= H for v in ys), i
        steps = [t for t in page.items if isinstance(t, Text) and t.tag == "step"]
        assert steps and max(t.y for t in steps) < H - 24.0

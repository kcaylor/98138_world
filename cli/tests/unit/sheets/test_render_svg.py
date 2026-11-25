"""SVG backend (006 T021, T028): one file per page, studs match the layout, no raster images."""

import xml.etree.ElementTree as ET

import pytest

from lego_image_processor.kit.source import DISCLAIMER
from lego_image_processor.sheets import build_sheet_set, render_svg

NS = {"s": "http://www.w3.org/2000/svg"}


@pytest.fixture(scope="module")
def few_svg(few_grid):
    s = build_sheet_set(few_grid, layout_path="few.json")
    return s, render_svg(s)


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(rgb)


def test_one_file_per_page(few_svg):
    s, files = few_svg
    assert [name for name, _ in files] == [f"page-{i:02d}.svg" for i in range(1, len(s.pages) + 1)]


def test_page_size_and_disclaimer(few_svg):
    _, files = few_svg
    for _, text in files:
        root = ET.fromstring(text)
        assert root.get("width") == "215.90mm" and root.get("height") == "279.40mm"
        assert root.get("viewBox") == "0 0 215.90 279.40"
        all_text = " ".join(t.text or "" for t in root.iter("{http://www.w3.org/2000/svg}text"))
        assert DISCLAIMER in all_text
        assert "<image" not in text and "data:image" not in text


def test_section_studs_match_layout(few_grid, few_svg):
    s, files = few_svg
    by_xy = {(p.x, p.y): p for p in few_grid.positions}
    entries = {(e.lot.part_id, e.lot.color_key): e for e in s.legend}
    index = [i for i, p in enumerate(s.pages) if p.kind == "section" and p.label == "C2"][0]
    root = ET.fromstring(files[index][1])
    studs = root.findall(".//s:circle[@class='stud']", NS)
    assert len(studs) == 256
    numbers = {(t.get("data-x"), t.get("data-y")): t.text
               for t in root.findall(".//s:text[@class='stud-number']", NS)}
    for c in studs:
        x, y = int(c.get("data-x")), int(c.get("data-y"))
        e = entries[(by_xy[(x, y)].lego_part_id, by_xy[(x, y)].color_id)]
        assert c.get("fill") == _hex(e.rgb) and c.get("data-lot") == str(e.number)
        assert numbers[(c.get("data-x"), c.get("data-y"))] == str(e.number)


def test_byte_identical_and_escaped(few_grid, few_svg):
    _, files = few_svg
    assert render_svg(build_sheet_set(few_grid, layout_path="few.json")) == files
    s = build_sheet_set(few_grid, title="A & B <Δ>", sections="A1")
    text = render_svg(s)[0][1]
    assert "A &amp; B &lt;Δ&gt;" in text
    ET.fromstring(text)


@pytest.mark.parametrize("paper", ["letter", "a4"])
def test_svg_pitch_is_8mm(few_grid, paper):
    """SC-003 in SVG coordinates (user units are millimetres)."""
    s = build_sheet_set(few_grid, paper=paper, sections="C2")
    root = ET.fromstring(render_svg(s)[-2][1])  # the last page is the assembly page (feature 010)
    studs = root.findall(".//s:circle[@class='stud']", NS)
    xs = sorted({float(c.get("cx")) for c in studs})
    ys = sorted({float(c.get("cy")) for c in studs})
    assert len(xs) == len(ys) == 16
    assert all(abs((b - a) - 8.0) <= 0.05 for a, b in zip(xs, xs[1:]))
    assert all(abs((b - a) - 8.0) <= 0.05 for a, b in zip(ys, ys[1:]))
    assert all(c.get("r") == "3.50" for c in studs)

"""Build sheets for the official design (006 T015, T027, T028; SC-001 to SC-006)."""

import io
import re
import time
import xml.etree.ElementTree as ET
from collections import Counter

import pytest
from pypdf import PdfReader

from lego_image_processor.kit import load_official_design
from lego_image_processor.kit.source import DISCLAIMER
from lego_image_processor.parts import build_parts_list, read_layout
from lego_image_processor.sheets import build_sheet_set, render_pdf, render_svg, sections
from lego_image_processor.sheets.model import Circle

SVG = "{http://www.w3.org/2000/svg}"


@pytest.fixture(scope="module")
def official(tmp_path_factory):
    path = tmp_path_factory.mktemp("official") / "official.json"
    path.write_text(load_official_design().to_layout().to_json(), encoding="utf-8")
    layout = read_layout(path)
    start = time.perf_counter()
    s = build_sheet_set(layout)
    pdf = render_pdf(s)
    elapsed = time.perf_counter() - start
    return layout, s, pdf, elapsed


def test_full_set_pages(official):
    _, s, pdf, _ = official
    reader = PdfReader(io.BytesIO(pdf))
    assert len(reader.pages) == len(s.pages) == 42  # overview, 1 legend page, 40 sections
    expected = [x.label for x in sections()]
    for label, page in zip(expected, reader.pages[2:]):
        assert f"Section {label}" in page.extract_text()


def test_studs_match_layout_on_every_section(official):
    """SC-002: every stud's colour and number equal the layout position's lot."""
    layout, s, _, _ = official
    entries = {(e.lot.part_id, e.lot.color_key): e for e in s.legend}
    by_xy = {(p.x, p.y): entries[(p.lego_part_id, p.color_id)] for p in layout.grid.positions}
    seen = set()
    for page in s.pages:
        if page.kind != "section":
            continue
        studs = [i for i in page.items if isinstance(i, Circle) and i.tag == "stud"]
        assert len(studs) == 256
        for c in studs:
            d = dict(c.data)
            xy = (int(d["x"]), int(d["y"]))
            assert c.fill == by_xy[xy].rgb and int(d["lot"]) == by_xy[xy].number
            seen.add(xy)
    assert len(seen) == 10240


def test_counts_sum_to_parts_list(official):
    """SC-001: the 40 count tables sum to 10,240 and equal the parts list per lot."""
    layout, s, _, _ = official
    total = Counter()
    for c in s.counts:
        assert c.total == 256
        total.update(c.counts)
    pl = build_parts_list(layout)
    assert {i + 1: l.needed for i, l in enumerate(pl.lots)} == dict(total)
    assert sum(total.values()) == 10240


def test_performance_and_size(official):
    """SC-004: under 10 s and under 5 MB."""
    _, _, pdf, elapsed = official
    assert elapsed < 10 and len(pdf) < 5_000_000


def test_pdf_text_on_every_page_and_no_images(official):
    """SC-006 for the PDF: the disclaimer on every page, no raster image."""
    _, s, pdf, _ = official
    reader = PdfReader(io.BytesIO(pdf))
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        assert DISCLAIMER in text and f"Page {i} of 42" in text
        assert "Print at 100% (no fit-to-page)" in text
    assert re.search(rb"/Subtype\s*/Image", pdf) is None


def test_svg_every_page(official):
    """SC-006 for SVG; SC-005 byte-identical."""
    _, s, _, _ = official
    files = render_svg(s)
    assert len(files) == 42
    for name, text in files:
        root = ET.fromstring(text)
        assert root.find(f".//{SVG}image") is None
        assert DISCLAIMER in [t.text for t in root.iter(f"{SVG}text")]
    assert render_svg(s) == files


def test_pdf_byte_identical(official):
    layout, _, pdf, _ = official
    assert render_pdf(build_sheet_set(layout)) == pdf

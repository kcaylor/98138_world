"""PDF backend (006 T013, T028): pages, size, text, no raster images, byte-identical."""

import io
import re

import pytest
from pypdf import PdfReader

from lego_image_processor.kit.source import DISCLAIMER
from lego_image_processor.sheets import build_sheet_set, render_pdf

MM = 72 / 25.4


@pytest.fixture(scope="module")
def few_pdf(few_grid):
    s = build_sheet_set(few_grid, layout_path="few.json")
    return s, render_pdf(s)


def test_pages_and_size(few_pdf):
    s, pdf = few_pdf
    reader = PdfReader(io.BytesIO(pdf))
    assert len(reader.pages) == len(s.pages)
    box = reader.pages[0].mediabox
    assert abs(float(box.width) - 215.9 * MM) < 0.01 and abs(float(box.height) - 279.4 * MM) < 0.01


def test_text_extractable(few_pdf):
    s, pdf = few_pdf
    reader = PdfReader(io.BytesIO(pdf))
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        assert DISCLAIMER in text and f"Page {i + 1} of {len(s.pages)}" in text
    labels = [p.label for p in s.pages if p.kind == "section"]
    first = len(s.pages) - 40
    for label, page in zip(labels, reader.pages[first:]):
        assert f"Section {label}" in page.extract_text()


def test_no_raster_images(few_pdf):
    _, pdf = few_pdf
    reader = PdfReader(io.BytesIO(pdf))
    for page in reader.pages:
        res = page.get("/Resources") or {}
        xobjects = res.get("/XObject") or {}
        for name in xobjects:
            assert xobjects[name].get_object().get("/Subtype") != "/Image"
    assert re.search(rb"/Subtype\s*/Image", pdf) is None


def test_byte_identical(few_grid, few_pdf):
    _, pdf = few_pdf
    again = render_pdf(build_sheet_set(few_grid, layout_path="few.json"))
    assert again == pdf
    assert b"/CreationDate" not in pdf or b"D:20000101" in pdf


def test_a4_size(few_grid):
    pdf = render_pdf(build_sheet_set(few_grid, paper="a4", sections="A1"))
    box = PdfReader(io.BytesIO(pdf)).pages[0].mediabox
    assert abs(float(box.width) - 210 * MM) < 0.01 and abs(float(box.height) - 297 * MM) < 0.01


def test_non_latin1_title_rejected(few_grid):
    s = build_sheet_set(few_grid, title="Δ map", sections="A1")
    with pytest.raises(ValueError, match="Latin-1"):
        render_pdf(s)

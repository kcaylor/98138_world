"""Sticker files: the print sheet PDF, the two SVGs and the JSON summary (feature 017, T034;
FR-007, FR-008, FR-011 - FR-013, FR-015, FR-026, SC-001, SC-004; research R4;
contracts/sticker-files.md; data-model.md "Sticker files").

Maps are built from the dataset fixtures (``fixture_registry``); final texts come from the
bundled recipes' approved sticker tables (T043; ``tests.stickers_support.sticker_recipe``).
Not affiliated with or endorsed by The LEGO Group.
"""

import io
import json
import re
import xml.etree.ElementTree as ET

import pytest
from pypdf import PdfReader

from lego_image_processor import __version__
from lego_image_processor.kit.plaque_parts import load_plaque_parts
from lego_image_processor.kit.source import DISCLAIMER
from lego_image_processor.layout.arrangement import parse_arrangement
from lego_image_processor.maps.build import build_map
from lego_image_processor.maps.recipe import parse_recipe
from lego_image_processor.sheets.compose import text_width
from lego_image_processor.stickers import (StickerError, print_sheet, render_sticker_json,
                                           render_sticker_pdf, render_sticker_svgs, sticker_set)
from tests.stickers_support import sticker_recipe

MM = 72 / 25.4
SVG = "{http://www.w3.org/2000/svg}"
SUBJECT = f"Map stickers for 98138.world. {DISCLAIMER}"
PAPER_MM = {"letter": (215.9, 279.4), "a4": (210.0, 297.0)}
CUT = {"small": (45.8, 45.8), "large": (125.8, 61.8)}
CANVAS = {"small": (59.8, 59.8), "large": (139.8, 75.8)}
CUT_AT = {"large": (19.0, 41.0), "small": (19.0, 118.8)}

PLAIN = '''format = "1"
id = "plain-map"
title = "Plain map"
description = "White land on depth classes."
[land]
role = "background"
colors = ["lego_white"]
[ocean]
role = "data"
dataset = "etopo2022-surface-10m"
variable = "z"
transform = "negate"
colors = ["lego_medium_azur", "lego_bright_bluish_green", "lego_earth_blue"]
[ocean.classification]
method = "bins"
bounds = [-9000, 200, 4000, 12000]
'''


@pytest.fixture
def build(fixture_registry):
    fixture_registry.place_all()

    def _build(recipe, arrangement=None):
        if isinstance(recipe, str):
            recipe = sticker_recipe(recipe)
        return build_map(recipe, cache_dir=fixture_registry.cache_dir, compare_official=False,
                         arrangement=parse_arrangement(arrangement) if arrangement else None)
    return _build


@pytest.fixture
def sst(build):
    return sticker_set(build("ocean-sst"))


def page_stream(pdf: bytes) -> bytes:
    return PdfReader(io.BytesIO(pdf)).pages[0].get_contents().get_data()


def unpainted_rects(pdf: bytes):
    """(x, y, w, h) in pt of every ``re n`` path (rectangle, no fill, no stroke)."""
    nums = rb"(-?[\d.]+)"
    pattern = rb"\s".join([nums] * 4) + rb"\s+re\s+n\b"
    return [tuple(float(v) for v in m.groups()) for m in re.finditer(pattern, page_stream(pdf))]


def svg_root(text: str):
    return ET.fromstring(text.encode("utf-8"))


def children(root):
    return list(root)


# --- the print sheet PDF ------------------------------------------------------------------------

class TestPdf:
    @pytest.mark.parametrize("paper", ["letter", "a4"])
    def test_one_page_of_the_paper_size(self, sst, paper):
        reader = PdfReader(io.BytesIO(render_sticker_pdf(sst, paper=paper)))
        assert len(reader.pages) == 1
        box = reader.pages[0].mediabox
        w, h = PAPER_MM[paper]
        assert abs(float(box.width) - w * MM) < 0.01 and abs(float(box.height) - h * MM) < 0.01

    def test_letter_is_the_default(self, sst):
        assert render_sticker_pdf(sst) == render_sticker_pdf(sst, paper="letter")

    def test_metadata(self, sst):
        meta = PdfReader(io.BytesIO(render_sticker_pdf(sst))).metadata
        assert meta.title == f"Map stickers: {sst.text.title}"
        assert meta.title == "Map stickers: Ocean temperature"
        assert meta.author == "98138.world"
        assert meta.subject == SUBJECT
        assert meta.creator == f"lego-image-processor {__version__}"

    def test_standard_helvetica_not_embedded(self, sst):
        pdf = render_sticker_pdf(sst)
        fonts = PdfReader(io.BytesIO(pdf)).pages[0]["/Resources"]["/Font"]
        names = {fonts[k].get_object()["/BaseFont"] for k in fonts}
        assert names == {"/Helvetica", "/Helvetica-Bold"}
        for key in (b"/FontFile", b"/FontFile2", b"/FontFile3"):
            assert key not in pdf

    def test_no_image(self, sst):
        pdf = render_sticker_pdf(sst)
        res = PdfReader(io.BytesIO(pdf)).pages[0].get("/Resources") or {}
        for name in res.get("/XObject") or {}:
            assert res["/XObject"][name].get_object().get("/Subtype") != "/Image"
        assert re.search(rb"/Subtype\s*/Image", pdf) is None

    @pytest.mark.parametrize("paper", ["letter", "a4"])
    def test_cut_lines_are_unpainted_rectangles_of_the_cut_size(self, sst, paper):
        pdf = render_sticker_pdf(sst, paper=paper)
        rects = unpainted_rects(pdf)
        assert len(rects) == 2
        H = PAPER_MM[paper][1]
        for size, (x, y, w, h) in zip(("large", "small"), rects):
            cw, ch = CUT[size]
            assert abs(w / MM - cw) <= 0.1 and abs(h / MM - ch) <= 0.1, size
            cx, cy = CUT_AT[size]
            assert abs(x / MM - cx) <= 0.1 and abs(y / MM - (H - cy - ch)) <= 0.1, size

    def test_text_on_the_page(self, sst):
        text = " ".join(PdfReader(io.BytesIO(render_sticker_pdf(sst))).pages[0]
                        .extract_text().split())
        for want in ("Map stickers: Ocean temperature", "Printed colors only approximate the LEGO "
                     "colors.", "The sticker is printed, not a LEGO part.", "98138.world",
                     "Print at 100% (no fit-to-page)", "Page 1 of 1", DISCLAIMER,
                     "ersst-v5-ltm-1991-2020"):
            assert want in text, want

    def test_both_stickers_and_the_page_carry_the_disclaimer(self, sst):
        for st in (sst.small, sst.large):
            assert " ".join(st.block("disclaimer").lines) == DISCLAIMER
        page = print_sheet(sst, "letter").page
        disc = [t.text for t in page.items if getattr(t, "tag", "") == "disclaimer"]
        n_sticker = len(sst.small.block("disclaimer").lines) + len(sst.large.block("disclaimer").lines)
        assert len(disc) == n_sticker + 1 and disc[-1] == DISCLAIMER   # + the footer's
        stream = page_stream(render_sticker_pdf(sst))
        for st in (sst.small, sst.large):
            for line in st.block("disclaimer").lines:
                assert f"({line})".encode("latin-1") in stream

    def test_same_input_same_bytes(self, build, sst):
        pdf = render_sticker_pdf(sst)
        assert render_sticker_pdf(sst) == pdf
        assert render_sticker_pdf(sticker_set(build("ocean-sst"))) == pdf
        assert b"D:20000101" in pdf or b"/CreationDate" not in pdf

    def test_papers_differ(self, sst):
        assert render_sticker_pdf(sst, paper="a4") != render_sticker_pdf(sst, paper="letter")

    @pytest.mark.parametrize("field,table", [
        ("line", '[sticker]\nline = "Depth classes → three colors."\n'),
        ("title", '[sticker]\ntitle = "Depth ≈ color"\nline = "Depth classes."\n'),
    ])
    def test_a_field_outside_latin1_stops_with_use_svg(self, build, field, table):
        s = sticker_set(build(parse_recipe(PLAIN + table)))
        with pytest.raises(StickerError) as err:
            render_sticker_pdf(s)
        assert field in str(err.value) and "use --format svg" in str(err.value)
        assert err.value.field == field

    def test_a_legend_label_outside_latin1_names_the_legend(self, build):
        recipe = parse_recipe(PLAIN + '[[ocean.override]]\nname = "南極"\n'
                              'color = "lego_white"\nlat_min = -90\nlat_max = -50\n')
        s = sticker_set(build(recipe))
        with pytest.raises(StickerError) as err:
            render_sticker_pdf(s)
        assert "legend: ocean" in str(err.value) and "use --format svg" in str(err.value)

    def test_an_unknown_paper(self, sst):
        with pytest.raises(ValueError):
            render_sticker_pdf(sst, paper="legal")


# --- the two SVG files --------------------------------------------------------------------------

class TestSvg:
    def test_two_files_small_then_large(self, sst):
        files = render_sticker_svgs(sst)
        assert [name for name, _ in files] == ["sticker-small.svg", "sticker-large.svg"]
        assert all(text.startswith('<?xml version="1.0" encoding="UTF-8"?>\n<svg ')
                   for _, text in files)
        assert all(text.endswith("</svg>\n") and "\r" not in text for _, text in files)

    @pytest.mark.parametrize("index,size", [(0, "small"), (1, "large")])
    def test_canvas_in_mm(self, sst, index, size):
        root = svg_root(render_sticker_svgs(sst)[index][1])
        w, h = CANVAS[size]
        assert root.get("width") == f"{w:.2f}mm" and root.get("height") == f"{h:.2f}mm"
        assert root.get("viewBox") == f"0 0 {w:.2f} {h:.2f}"
        assert root.get("font-family") == "Helvetica, Arial, sans-serif"

    @pytest.mark.parametrize("index,size", [(0, "small"), (1, "large")])
    def test_element_order(self, sst, index, size):
        root = svg_root(render_sticker_svgs(sst)[index][1])
        kids = children(root)
        assert [k.tag for k in kids[:3]] == [SVG + "title", SVG + "desc", SVG + "metadata"]
        paper = kids[3]
        w, h = CANVAS[size]
        assert paper.tag == SVG + "rect" and paper.get("fill") == "#ffffff"
        assert (paper.get("x"), paper.get("y")) == ("0", "0")
        assert (paper.get("width"), paper.get("height")) == (f"{w:.2f}", f"{h:.2f}")
        drawn = kids[4:-1]
        classes = [k.get("class") for k in drawn]
        assert classes[0] == "bleed"
        assert classes[1:9] == ["cut-mark"] * 8
        assert classes[9] == "sticker-bg"
        assert "cut-mark" not in classes[10:] and "bleed" not in classes[10:]
        assert kids[-1].tag == SVG + "g" and kids[-1].get("id") == "cut-line"

    @pytest.mark.parametrize("index,size", [(0, "small"), (1, "large")])
    def test_cut_line_group(self, sst, index, size):
        root = svg_root(render_sticker_svgs(sst)[index][1])
        group = children(root)[-1]
        rects = list(group)
        assert len(rects) == 1
        r = rects[0]
        assert r.tag == SVG + "rect" and r.get("class") == "cut-line"
        assert (r.get("x"), r.get("y")) == ("7.00", "7.00")
        cw, ch = CUT[size]
        assert abs(float(r.get("width")) - cw) <= 0.1 and abs(float(r.get("height")) - ch) <= 0.1
        assert r.get("fill") == "none" and r.get("stroke") == "#ff00ff"
        assert r.get("stroke-width") == "0.10"
        assert len(root.findall(f".//{SVG}rect[@class='cut-line']")) == 1

    def test_bleed_and_background_in_cited_black(self, sst):
        black = "#%02x%02x%02x" % tuple(load_plaque_parts().plaques["large"].tile.color.rgb)
        for _, text in render_sticker_svgs(sst):
            root = svg_root(text)
            for cls in ("bleed", "sticker-bg"):
                (el,) = root.findall(f"{SVG}rect[@class='{cls}']")
                assert el.get("fill") == black

    def test_title_and_desc(self, sst):
        small, large = (svg_root(t) for _, t in render_sticker_svgs(sst))
        assert small.find(SVG + "title").text == "Small sticker: Ocean temperature (98138.world)"
        assert large.find(SVG + "title").text == "Large sticker: Ocean temperature (98138.world)"
        assert small.find(SVG + "desc").text == DISCLAIMER
        assert large.find(SVG + "desc").text == DISCLAIMER

    def test_metadata_carries_every_citation(self, build):
        s = sticker_set(build("rainfall"))
        for _, text in render_sticker_svgs(s):
            meta = svg_root(text).find(SVG + "metadata").text
            assert f"Recipe {s.recipe.id} (SHA-256 {s.recipe.sha256})" in meta
            assert len(s.credits) == 2
            for c in s.credits:
                for part in (c.dataset, c.version, c.title, c.citation, c.license):
                    assert part in meta, part
                if c.acknowledgement:
                    assert c.acknowledgement in meta
            assert f"Made with lego-image-processor {__version__}." in meta

    def test_metadata_does_not_depend_on_the_arrangement(self, sst):
        for _, text in render_sticker_svgs(sst):
            meta = svg_root(text).find(SVG + "metadata").text
            assert "hung as" not in meta and "arrangement" not in meta.lower()

    def test_metadata_is_not_drawn(self, sst):
        for _, text in render_sticker_svgs(sst):
            meta = svg_root(text).find(SVG + "metadata")
            assert list(meta) == []

    def test_every_text_carries_its_helvetica_width(self, sst):
        for _, text in render_sticker_svgs(sst):
            texts = svg_root(text).findall(f".//{SVG}text")
            assert texts
            for t in texts:
                size_pt = float(t.get("font-size")) / (25.4 / 72)
                bold = t.get("font-weight") == "bold"
                want = text_width(t.text, size_pt, bold)
                # font-size is written with two decimals in mm (at most 0.005 mm off)
                tol = 0.006 + want * 0.005 / float(t.get("font-size"))
                assert abs(float(t.get("textLength")) - want) <= tol, t.text
                assert t.get("lengthAdjust") == "spacingAndGlyphs"

    def test_text_lengths_are_the_item_widths(self, sst):
        _, large = render_sticker_svgs(sst)[1]
        items = [i for i in sst.large.items if type(i).__name__ == "Text"]
        lengths = re.findall(r'<text [^>]*textLength="([\d.]+)"', large)
        assert lengths == [f"{text_width(i.text, i.size_pt, i.bold):.2f}" for i in items]

    def test_content_and_tags(self, sst):
        small, large = (svg_root(t) for _, t in render_sticker_svgs(sst))
        small_text = " ".join(t.text for t in small.iter(SVG + "text"))
        large_text = " ".join(t.text for t in large.iter(SVG + "text"))
        assert "Ocean temperature" in small_text and "98138.world" not in small_text
        assert "Ocean temperature" in large_text and "98138.world" in large_text
        assert "Data:" in large_text
        swatches = large.findall(f"{SVG}circle[@class='swatch']")
        assert len(swatches) == len(sst.legend)
        assert all(s.get("data-layer") and s.get("data-color") and s.get("data-part")
                   for s in swatches)
        assert small.findall(f"{SVG}circle[@class='swatch']") == []

    def test_no_image(self, sst):
        for _, text in render_sticker_svgs(sst):
            assert "<image" not in text and "data:image" not in text

    def test_unicode_text_is_allowed(self, build):
        s = sticker_set(build(parse_recipe(
            PLAIN + '[sticker]\nline = "Depth classes → three colors."\n')))
        small, large = render_sticker_svgs(s)
        assert "Depth classes → three colors." in " ".join(
            t.text for t in svg_root(large[1]).iter(SVG + "text"))
        assert "→" in small[1]

    def test_same_input_same_text(self, build, sst):
        files = render_sticker_svgs(sst)
        assert render_sticker_svgs(sst) == files
        assert render_sticker_svgs(sticker_set(build("ocean-sst"))) == files

    def test_a_b_c_builds_give_the_same_files(self, build):
        files = {c: render_sticker_svgs(sticker_set(build("ocean-sst", c))) for c in "ABC"}
        assert files["A"] == files["B"] == files["C"]

    def test_numbers_with_two_decimals(self, sst):
        for _, text in render_sticker_svgs(sst):
            for value in re.findall(r' (?:x|y|cx|cy|r|width|height|x1|y1|x2|y2)="([^"]+)"', text):
                assert re.fullmatch(r"-?\d+\.\d\d(mm)?|0", value), value


# --- the JSON summary ---------------------------------------------------------------------------

class TestJson:
    def test_written_with_utf8_and_indent_2(self, sst):
        text = render_sticker_json(sst)
        assert text == json.dumps(sst.to_dict(), ensure_ascii=False, indent=2) + "\n"
        assert "°C" in text and "\\u00b0" not in text

    def test_field_order(self, sst):
        data = json.loads(render_sticker_json(sst))
        assert list(data) == ["format_version", "recipe", "template", "arrangement", "text",
                              "stickers", "legend", "credits", "plaques", "notes",
                              "tool_version", "disclaimer"]

    def test_content(self, sst):
        data = json.loads(render_sticker_json(sst))
        assert data["format_version"] == "1"
        assert data["recipe"] == {"id": "ocean-sst", "title": sst.recipe.title,
                                  "sha256": sst.recipe.sha256}
        assert data["template"] == {"id": "kit-31203"}
        assert data["arrangement"] == "A"
        assert list(data["text"]) == ["title", "title_source", "line", "line_source"]
        assert list(data["stickers"]) == ["small", "large"]
        assert data["notes"] == {"printed": "The sticker is printed, not a LEGO part.",
                                 "colors": "Printed colors only approximate the LEGO colors."}
        assert data["tool_version"] == __version__
        assert data["disclaimer"] == DISCLAIMER
        assert [c["dataset"] for c in data["credits"]] == ["ersst-v5-ltm-1991-2020"]

    def test_plaques_with_cited_ids(self, sst):
        table = load_plaque_parts()
        data = json.loads(render_sticker_json(sst))
        assert [p["size"] for p in data["plaques"]] == ["small", "large"]
        for p in data["plaques"]:
            plaque = table.plaques[p["size"]]
            assert [x["role"] for x in p["parts"]] == ["tile", "plate"]
            for got, part in zip(p["parts"], plaque.parts):
                assert got["part_id"] == part.part_id and got["quantity"] == 1
                assert got["element_id"] == part.color.element_id
                assert got["bricklink_item"] == part.numbers.bricklink_item_no
                assert got["rebrickable_part"] == part.numbers.rebrickable_part_num
                assert got["color"]["bricklink"] == {"name": part.color.bricklink.name,
                                                     "id": part.color.bricklink.id}
                assert got["citations"]

    def test_same_input_same_text(self, build, sst):
        assert render_sticker_json(sticker_set(build("ocean-sst"))) == render_sticker_json(sst)

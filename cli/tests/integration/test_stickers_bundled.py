"""The sticker sets of the eight bundled maps (feature 017, T039; FR-001 - FR-006, FR-012,
SC-001 - SC-004; spec US1 acceptance scenarios 1 - 8).

Every map is built from the dataset fixtures (``fixture_registry``), with the bundled recipes'
approved sticker tables (T042 - T043; ``tests.stickers_support.sticker_recipe``).

- Fit (SC-002): every text of both stickers and of the print sheet at 5 pt or more, inside its
  area, on Letter and A4.
- Cut lines (SC-001): within 0.1 mm of their sizes in the page model, both SVGs and the PDF.
- No image, the disclaimer in each file (SC-004); no "Official" in a sticker title (FR-004).
- A, B, C, D and E (SC-003, FR-006; D and E since feature 010 merged): ``to_dict()`` without
  ``arrangement`` and both SVG files are identical; the print sheets differ only in the line
  "legend values from the build hung as <C>", so PDF bytes are compared within one arrangement;
  a set made twice gives the same PDF, SVG and JSON bytes (FR-012).
- Acceptance content of ocean-sst, land-elevation, rainfall, official-31203 and living-planet.

Not affiliated with or endorsed by The LEGO Group.
"""

import io
import json
import re
import xml.etree.ElementTree as ET

import pytest
from pypdf import PdfReader

from lego_image_processor.datasets.registry import load_registry
from lego_image_processor.kit.part_colors import load_part_colors
from lego_image_processor.kit.plaque_parts import load_plaque_parts
from lego_image_processor.kit.source import DISCLAIMER
from lego_image_processor.layout.arrangement import parse_arrangement
from lego_image_processor.maps.build import build_map
from lego_image_processor.maps.recipe import bundled_recipes, load_recipe
from lego_image_processor.sheets.compose import PRINT_NOTE, text_width
from lego_image_processor.sheets.model import PAPERS, PT_MM, Circle, Line, Rect, Text
from lego_image_processor.stickers import (print_sheet, render_sticker_json, render_sticker_pdf,
                                           render_sticker_svgs, sticker_set)
from lego_image_processor.stickers.text import wrap_words
from tests.stickers_support import sticker_recipe

RECIPES = sorted(bundled_recipes())
PAPER_IDS = ("letter", "a4")
ARRANGEMENTS = ("A", "B", "C", "D", "E")   # D and E: feature 010
MM = 72 / 25.4
SVG = "{http://www.w3.org/2000/svg}"
EPS = 1e-6
CAP, DESCENT = 0.718, 0.21          # Helvetica cap height and descender (em)
CUT = {"small": (45.8, 45.8), "large": (125.8, 61.8)}
CANVAS = {"small": (59.8, 59.8), "large": (139.8, 75.8)}
CUT_AT = {"large": (19.0, 41.0), "small": (19.0, 118.8)}
OUTLINE, OUTLINE_MM = (210, 210, 210), 0.15
SVG_NAMES = ("sticker-small.svg", "sticker-large.svg")


@pytest.fixture
def build(fixture_registry):
    fixture_registry.place_all()

    def _build(recipe_id, arrangement=None):
        return build_map(sticker_recipe(recipe_id), cache_dir=fixture_registry.cache_dir,
                         compare_official=False,
                         arrangement=parse_arrangement(arrangement) if arrangement else None)
    return _build


@pytest.fixture
def make(build):
    """The sticker set of a bundled map, built in its own arrangement or the one given."""
    def _make(recipe_id, arrangement=None):
        return sticker_set(build(recipe_id, arrangement))
    return _make


def norm(text):
    return " ".join(text.split())


def joined(block):
    return norm(" ".join(block.lines))


def tagged(items, tag, kind=None):
    return [i for i in items if i.tag == tag and (kind is None or isinstance(i, kind))]


def text_extent(t: Text):
    """(left, top, right, bottom) of a text item from Helvetica's metrics."""
    w = text_width(t.text, t.size_pt, t.bold)
    left = {"left": t.x, "center": t.x - w / 2, "right": t.x - w}[t.align]
    em = t.size_pt * PT_MM
    return left, t.y - CAP * em, left + w, t.y + DESCENT * em


def inside(box, area):
    x, y, w, h = area
    return (box[0] >= x - EPS and box[1] >= y - EPS and box[2] <= x + w + EPS
            and box[3] <= y + h + EPS)


def unpainted_rects(pdf: bytes):
    """(x, y, w, h) in pt of every ``re n`` path (a rectangle neither filled nor stroked)."""
    stream = PdfReader(io.BytesIO(pdf)).pages[0].get_contents().get_data()
    nums = rb"(-?[\d.]+)"
    pattern = rb"\s".join([nums] * 4) + rb"\s+re\s+n\b"
    return [tuple(float(v) for v in m.groups()) for m in re.finditer(pattern, stream)]


def svg_root(text: str):
    return ET.fromstring(text.encode("utf-8"))


def svg_texts(root, cls=None):
    return [e.text or "" for e in root.iter(f"{SVG}text") if cls is None or e.get("class") == cls]


def labels(s, layer):
    return [sw.label for sw in s.legend.group(layer).swatches]


def drawn_labels(sticker):
    return [t.text for t in tagged(sticker.items, "legend-label", Text)]


# --- fit at 5 pt or more (SC-002, FR-013) -------------------------------------------------------

class TestFit:
    @pytest.mark.parametrize("recipe_id", RECIPES)
    def test_both_stickers_fit_at_5_pt_or_more(self, make, recipe_id):
        s = make(recipe_id)
        for st in s.stickers:
            area = st.geometry.safe_box
            assert st.blocks
            for b in st.blocks:
                assert b.size_pt >= 5.0 - EPS, (st.size, b.field, b.size_pt)
                assert b.size_pt <= b.preferred_pt + EPS
                x, y, w, h = b.box
                assert inside((x, y, x + w, y + h), area), (st.size, b.field)
            for t in st.items:
                if isinstance(t, Text):
                    assert t.size_pt >= 5.0 - EPS, (st.size, t.tag, t.text)
                    assert inside(text_extent(t), area), (st.size, t.tag, t.text)
            for c in tagged(st.items, "swatch", Circle):
                assert inside((c.cx - c.r, c.cy - c.r, c.cx + c.r, c.cy + c.r), area)
        # every legend entry of the map is drawn on the large sticker, none on the small one
        assert drawn_labels(s.large) == [sw.label for sw in s.legend]
        assert len(tagged(s.large.items, "swatch", Circle)) == len(s.legend)
        assert not tagged(s.small.items, "swatch") and not s.small.legend

    @pytest.mark.parametrize("recipe_id", RECIPES)
    @pytest.mark.parametrize("paper", PAPER_IDS)
    def test_print_sheet_fits(self, make, recipe_id, paper):
        s = make(recipe_id)
        page = print_sheet(s, paper).page
        W, H = PAPERS[paper].width_mm, PAPERS[paper].height_mm
        texts = [t for t in page.items if isinstance(t, Text)]
        assert texts
        for t in texts:
            assert t.size_pt >= 5.0 - EPS, (t.tag, t.text, t.size_pt)
            l, top, r, b = text_extent(t)
            assert top >= 0 and b <= H and r <= W, (t.tag, t.text)
        # every dataset's full citation and license is on the sheet (FR-007, constitution IV)
        data = norm(" ".join(t.text for t in texts if t.tag == "citation"))
        for c in s.credits:
            for value in (c.dataset, c.version, c.title, c.citation, c.license):
                assert norm(value) in data, (c.dataset, value)
        assert render_sticker_pdf(s, paper).startswith(b"%PDF-")


# --- cut lines within 0.1 mm (SC-001) ----------------------------------------------------------

class TestCutLines:
    @pytest.mark.parametrize("recipe_id", RECIPES)
    @pytest.mark.parametrize("paper", PAPER_IDS)
    def test_page_model(self, make, recipe_id, paper):
        s = make(recipe_id)
        for st in s.stickers:
            cw, ch = CUT[st.size]
            assert abs(st.geometry.cut_mm[0] - cw) <= 0.1 and abs(st.geometry.cut_mm[1] - ch) <= 0.1
        page = print_sheet(s, paper).page
        cuts = {dict(r.data)["sticker"]: r for r in tagged(page.items, "cut-line", Rect)}
        assert set(cuts) == {"small", "large"}
        for size, r in cuts.items():
            cw, ch = CUT[size]
            assert abs(r.w - cw) <= 0.1 and abs(r.h - ch) <= 0.1, size
            assert (r.x, r.y) == CUT_AT[size]              # the same place on Letter and A4

    @pytest.mark.parametrize("recipe_id", RECIPES)
    def test_svg(self, make, recipe_id):
        files = dict(render_sticker_svgs(make(recipe_id)))
        assert tuple(files) == SVG_NAMES
        for name, size in zip(SVG_NAMES, ("small", "large")):
            root = svg_root(files[name])
            W, H = CANVAS[size]
            # true size in millimetres, the viewBox in mm units (two-decimal numbers)
            assert root.get("width").endswith("mm") and root.get("height").endswith("mm")
            assert float(root.get("width")[:-2]) == pytest.approx(W)
            assert float(root.get("height")[:-2]) == pytest.approx(H)
            assert [float(v) for v in root.get("viewBox").split()] == pytest.approx([0, 0, W, H])
            groups = [g for g in root.iter(f"{SVG}g") if g.get("id") == "cut-line"]
            assert len(groups) == 1
            (rect,) = list(groups[0])
            assert rect.tag == f"{SVG}rect" and rect.get("fill") == "none"
            cw, ch = CUT[size]
            assert abs(float(rect.get("width")) - cw) <= 0.1, name
            assert abs(float(rect.get("height")) - ch) <= 0.1, name

    @pytest.mark.parametrize("recipe_id", RECIPES)
    @pytest.mark.parametrize("paper", PAPER_IDS)
    def test_pdf(self, make, recipe_id, paper):
        pdf = render_sticker_pdf(make(recipe_id), paper)
        rects = unpainted_rects(pdf)
        assert len(rects) == 2
        H = PAPERS[paper].height_mm
        for size, (x, y, w, h) in zip(("large", "small"), rects):
            cw, ch = CUT[size]
            assert abs(w / MM - cw) <= 0.1 and abs(h / MM - ch) <= 0.1, size
            cx, cy = CUT_AT[size]
            assert abs(x / MM - cx) <= 0.1 and abs(y / MM - (H - cy - ch)) <= 0.1, size


# --- no image, the disclaimer in each file (SC-004, FR-026) -------------------------------------

class TestDisclaimerNoImage:
    @pytest.mark.parametrize("recipe_id", RECIPES)
    def test_page_models(self, make, recipe_id):
        s = make(recipe_id)
        assert s.disclaimer == DISCLAIMER
        for st in s.stickers:
            assert joined(st.block("disclaimer")) == DISCLAIMER, st.size
            assert all(isinstance(i, (Rect, Circle, Line, Text)) for i in st.items)

    @pytest.mark.parametrize("recipe_id", RECIPES)
    @pytest.mark.parametrize("paper", PAPER_IDS)
    def test_pdf(self, make, recipe_id, paper):
        pdf = render_sticker_pdf(make(recipe_id), paper)
        reader = PdfReader(io.BytesIO(pdf))
        assert len(reader.pages) == 1
        res = reader.pages[0].get("/Resources") or {}
        for name in res.get("/XObject") or {}:
            assert res["/XObject"][name].get_object().get("/Subtype") != "/Image"
        assert re.search(rb"/Subtype\s*/Image", pdf) is None
        assert DISCLAIMER in reader.metadata.subject
        assert DISCLAIMER in norm(reader.pages[0].extract_text())

    @pytest.mark.parametrize("recipe_id", RECIPES)
    def test_svgs(self, make, recipe_id):
        for name, text in render_sticker_svgs(make(recipe_id)):
            assert "<image" not in text and "href" not in text, name
            root = svg_root(text)
            assert root.find(f"{SVG}desc").text == DISCLAIMER
            assert norm(" ".join(svg_texts(root, "disclaimer"))) == DISCLAIMER, name

    @pytest.mark.parametrize("recipe_id", RECIPES)
    def test_json(self, make, recipe_id):
        doc = json.loads(render_sticker_json(make(recipe_id)))
        assert doc["disclaimer"] == DISCLAIMER


# --- sticker titles (FR-004) -------------------------------------------------------------------

class TestTitles:
    @pytest.mark.parametrize("recipe_id", RECIPES)
    def test_no_official_in_sticker_titles(self, make, recipe_id):
        s = make(recipe_id)
        assert "official" not in s.text.title.lower()
        for st in s.stickers:
            assert "official" not in joined(st.block("title")).lower(), st.size
        page = print_sheet(s, "letter").page
        assert "official" not in norm(" ".join(
            t.text for t in tagged(page.items, "sheet-title", Text))).lower()
        for name, text in render_sticker_svgs(s):
            assert "official" not in svg_root(text).find(f"{SVG}title").text.lower(), name
        meta = PdfReader(io.BytesIO(render_sticker_pdf(s))).metadata
        assert "official" not in meta.title.lower()

    @pytest.mark.parametrize("recipe_id", RECIPES)
    def test_texts_from_the_sticker_table(self, make, recipe_id):
        s = make(recipe_id)
        recipe = load_recipe(recipe_id)
        table = recipe.sticker
        assert s.text.line == table.line and s.text.line_source == "sticker table"
        assert s.text.title == (table.title or recipe.title)
        assert s.text.title_source == ("sticker table" if table.title else "recipe title")
        for st in s.stickers:
            assert joined(st.block("title")) == s.text.title
            assert joined(st.block("line")) == s.text.line

    @pytest.mark.parametrize("recipe_id", RECIPES)
    def test_small_sticker_titles_are_balanced(self, make, recipe_id):
        """A title that wraps keeps the greedy wrap's line count, with the break points that
        make its widest line narrowest, so the last line is not a single word (the project
        owner's approval of the texts, 2026-11-24, T042)."""
        s = make(recipe_id)
        block = s.small.block("title")
        assert block.lines == SMALL_TITLE_LINES.get(recipe_id, (s.text.title,))
        size, width = block.size_pt, block.box[2]
        greedy = wrap_words(s.text.title, size, width, True)
        assert len(block.lines) == len(greedy)
        if len(block.lines) > 1:
            assert all(len(ln.split()) > 1 for ln in block.lines)
            widest = max(text_width(ln, size, True) for ln in block.lines)
            assert widest < max(text_width(ln, size, True) for ln in greedy)
            assert widest <= width + EPS
        drawn = [t.text for t in tagged(s.small.items, "title", Text)]
        assert drawn == list(block.lines)
        (small_svg,) = [text for name, text in render_sticker_svgs(s) if name == SVG_NAMES[0]]
        texts = svg_texts(svg_root(small_svg))
        assert all(ln in texts for ln in block.lines)
        # the large sticker's title fits on one line for every bundled map
        assert s.large.block("title").lines == (s.text.title,)


# the small stickers' titles that wrap to two lines, balanced
SMALL_TITLE_LINES = {
    "ocean-el-nino": ("El Niño,", "December 1997"),
    "ocean-la-nina": ("La Niña,", "December 1988"),
    "official-31203": ("World Map,", "kit 31203 design"),
    "official-31203-bathymetry": ("Kit 31203 look,", "from bathymetry"),
}


# --- identical for A-E; same bytes twice (SC-003, FR-006, FR-012) --------------------------------

class TestArrangements:
    @pytest.mark.parametrize("recipe_id", RECIPES)
    def test_sets_identical_in_every_combination(self, make, recipe_id):
        docs = {}
        for c in ARRANGEMENTS:
            s = make(recipe_id, c)
            d = s.to_dict()
            assert s.arrangement == d.pop("arrangement") == c
            docs[c] = d
        assert all(docs[c] == docs["A"] for c in ARRANGEMENTS), recipe_id

    @pytest.mark.parametrize("recipe_id", RECIPES)
    def test_svg_files_byte_identical_in_every_combination(self, make, recipe_id):
        files = {c: render_sticker_svgs(make(recipe_id, c)) for c in ARRANGEMENTS}
        assert all(files[c] == files["A"] for c in ARRANGEMENTS), recipe_id
        assert [n for n, _ in files["A"]] == list(SVG_NAMES)

    @pytest.mark.parametrize("recipe_id", RECIPES)
    @pytest.mark.parametrize("paper", PAPER_IDS)
    def test_print_sheets_differ_only_in_the_arrangement_line(self, make, recipe_id, paper):
        pages = {c: print_sheet(make(recipe_id, c), paper).page for c in ARRANGEMENTS}
        a = pages["A"]
        for c in ARRANGEMENTS[1:]:
            other = pages[c]
            assert len(other.items) == len(a.items)
            differ = [(x, y) for x, y in zip(a.items, other.items) if x != y]
            assert len(differ) == 1, [(x.tag, getattr(x, "text", "")) for x, _ in differ]
            ((x, y),) = differ
            assert x.tag == y.tag == "provenance"
            assert "hung as A" in x.text
            assert x.text.replace("hung as A", f"hung as {c}") == y.text

    @pytest.mark.parametrize("recipe_id", RECIPES)
    @pytest.mark.parametrize("arrangement", ARRANGEMENTS)
    def test_twice_the_same_bytes(self, make, recipe_id, arrangement):
        first, second = make(recipe_id, arrangement), make(recipe_id, arrangement)
        assert first == second
        for paper in PAPER_IDS:
            assert render_sticker_pdf(first, paper) == render_sticker_pdf(second, paper)
        assert render_sticker_svgs(first) == render_sticker_svgs(second)
        assert render_sticker_json(first) == render_sticker_json(second)

    @pytest.mark.parametrize("recipe_id", ["ocean-el-nino", "ocean-la-nina"])
    def test_own_arrangement_recorded(self, make, recipe_id):
        # the ENSO recipes hang as D (feature 010; B before it); their sets record it and equal
        # the A set otherwise
        own, a = make(recipe_id), make(recipe_id, "A")
        assert own.arrangement == "D"
        d_own, d_a = own.to_dict(), a.to_dict()
        d_own.pop("arrangement"), d_a.pop("arrangement")
        assert d_own == d_a


# --- acceptance content (spec US1) -------------------------------------------------------------

def credit_text(s):
    return joined(s.large.block("credit"))


def swatch_circle(sticker, color):
    (c,) = [c for c in tagged(sticker.items, "swatch", Circle) if dict(c.data)["color"] == color]
    return c


class TestOceanSst:
    def test_large_sticker(self, make):                                   # US1-2
        s = make("ocean-sst")
        large = s.large
        assert joined(large.block("title")) == "Ocean temperature"
        assert joined(large.block("site")) == "98138.world"
        assert joined(large.block("line")) == load_recipe("ocean-sst").sticker.line
        ocean = s.legend.group("ocean").swatches
        assert len(ocean) == 9
        assert [sw.part_id for sw in ocean] == ["98138"] * 9
        assert [sw.color for sw in ocean] == list(load_recipe("ocean-sst").ocean.colors)
        for sw in ocean:
            (cls,) = [m for m in sw.meanings if m.kind == "class"]
            assert cls.units == "°C" and "°C" in cls.label and cls.range is not None
        (land,) = s.legend.group("land").swatches
        assert (land.color, land.part_id, land.label) == ("lego_white", "6141", "land")
        (shadow,) = [sw for sw in s.legend if any(m.kind == "shadow" for m in sw.meanings)]
        assert shadow.color == "lego_earth_blue" and shadow.layer == "ocean"
        assert shadow.label.endswith("land shadow")
        assert drawn_labels(large) == [sw.label for sw in s.legend]
        e = load_registry().get("ersst-v5-ltm-1991-2020")
        assert credit_text(s) == f"Data: {e.title}, doi:{e.doi}"
        assert "ERSST v5" in credit_text(s) and "doi:10.1175/JCLI-D-16-0836.1" in credit_text(s)
        assert joined(large.block("disclaimer")) == DISCLAIMER
        assert [b.field for b in large.blocks] == ["title", "site", "line", "legend", "credit",
                                                   "disclaimer"]

    def test_small_sticker(self, make):                                   # US1-3
        s = make("ocean-sst")
        small = s.small
        assert [b.field for b in small.blocks] == ["title", "line", "disclaimer"]
        assert joined(small.block("title")) == "Ocean temperature"
        assert joined(small.block("line")) == load_recipe("ocean-sst").sticker.line
        assert joined(small.block("disclaimer")) == DISCLAIMER
        texts = norm(" ".join(t.text for t in small.items if isinstance(t, Text)))
        assert texts == norm(" ".join([s.text.title, s.text.line, DISCLAIMER]))
        assert "98138.world" not in texts and "Data:" not in texts
        assert not tagged(small.items, "swatch")

    def test_print_sheet(self, make):                                     # US1-1
        s = make("ocean-sst")
        pdf = render_sticker_pdf(s)
        reader = PdfReader(io.BytesIO(pdf))
        assert len(reader.pages) == 1
        box = reader.pages[0].mediabox
        assert abs(float(box.width) / MM - 215.9) < 0.01
        assert abs(float(box.height) / MM - 279.4) < 0.01
        page = print_sheet(s, "letter").page
        bleeds = tagged(page.items, "bleed", Rect)
        black = load_plaque_parts().plaques["large"].tile.color.rgb
        assert sorted(dict(b.data)["sticker"] for b in bleeds) == ["large", "small"]
        assert all(b.fill == black for b in bleeds)
        assert len(tagged(page.items, "cut-mark", Line)) == 16
        assert [t.text for t in tagged(page.items, "print-note", Text)][0] == PRINT_NOTE
        (bar,) = tagged(page.items, "scale-bar", Line)
        assert abs(bar.x2 - bar.x1 - 100.0) <= EPS
        parts = norm(" ".join(t.text for t in tagged(page.items, "part", Text)))
        for plaque in load_plaque_parts().plaques.values():
            for part in plaque.parts:
                assert f"LEGO element {part.color.element_id}" in parts
                assert f"BrickLink {part.numbers.bricklink_item_no}, Black (11)" in parts
                assert f"Rebrickable {part.numbers.rebrickable_part_num}, Black (0)" in parts
        e = load_registry().get("ersst-v5-ltm-1991-2020")
        data = norm(" ".join(t.text for t in tagged(page.items, "citation", Text)))
        assert norm(e.citation) in data and norm(e.license) in data
        text = norm(reader.pages[0].extract_text())
        assert DISCLAIMER in text and PRINT_NOTE in text

    def test_a4_keeps_the_sticker_sizes(self, make):                      # US1-4
        s = make("ocean-sst")
        letter, a4 = print_sheet(s, "letter").page, print_sheet(s, "a4").page
        assert a4.size == PAPERS["a4"]

        def placed(page):
            return [i for i in page.items if dict(i.data).get("sticker")]
        assert placed(letter) == placed(a4)


class TestLandElevation:                                                  # US1-5
    def test_legend(self, make):
        s = make("land-elevation")
        land = s.legend.group("land").swatches
        assert len(land) == 10
        assert [sw.part_id for sw in land] == ["6141"] * 10
        assert land[0].label == "below 150 m" and land[-1].label == "3,000 m and above"
        assert all(m.units == "m" for sw in land for m in sw.meanings)
        assert labels(s, "ocean") == ["offshore", "coast ring", "land shadow"]
        assert drawn_labels(s.large) == labels(s, "land") + labels(s, "ocean")
        assert len(tagged(s.large.items, "swatch-ring", Circle)) == 10   # plates have the ring


class TestRainfall:                                                       # US1-6
    def test_legend(self, make):
        s = make("rainfall")
        for layer in ("land", "ocean"):
            classes = [sw for sw in s.legend.group(layer).swatches
                       if any(m.kind == "class" for m in sw.meanings)]
            assert classes
            assert all(m.units == "mm/yr" for sw in classes for m in sw.meanings
                       if m.kind == "class")
            assert classes[0].label.startswith("below ") and classes[0].label.endswith(" mm/yr")
            assert classes[-1].label.endswith(" mm/yr and above")
        land, ocean = s.legend.group("land").swatches, s.legend.group("ocean").swatches
        ice = [sw for sw in land if sw.color == "lego_white"]
        assert [sw.label for sw in ice] == ["Antarctica; Greenland"]
        sea_ice = [sw for sw in ocean if sw.color == "lego_white"]
        assert [sw.label for sw in sea_ice] == ["sea ice"]
        (shadow,) = [sw for sw in ocean if sw.color == "lego_black"]
        assert shadow.label == "land shadow"
        circle = swatch_circle(s.large, "lego_black")
        black = load_part_colors().get("98138", "lego_black").rgb
        assert circle.fill == tuple(black)
        assert circle.stroke == OUTLINE and circle.stroke_w == OUTLINE_MM   # it shows on Black
        assert "Antarctica; Greenland" in drawn_labels(s.large)

    def test_credits(self, make):
        s = make("rainfall")
        text = credit_text(s)
        assert "GPCP v2.3" in text and "NSIDC" in text
        assert [c.dataset for c in s.credits] == ["gpcp-v23-ltm-1991-2020",
                                                  "nsidc-cdr-v6-seaice-minimum-1991-2020"]


class TestOfficial31203:                                                  # US1-7
    def test_legend_and_credit(self, make):
        s = make("official-31203")
        ocean = s.legend.group("ocean")
        assert ocean.heading == "Ocean: the kit design's colors"
        table = load_part_colors()
        recipe = load_recipe("official-31203")
        assert len(ocean.swatches) == 9
        assert [sw.color for sw in ocean.swatches] == list(recipe.ocean.colors)
        assert [sw.label for sw in ocean.swatches] == [
            table.get("98138", c).lego.name for c in recipe.ocean.colors]
        assert not any(ch.isdigit() for sw in ocean.swatches for ch in sw.label)
        assert "Ocean: the kit design's colors" in [
            t.text for t in tagged(s.large.items, "legend-heading", Text)]
        assert credit_text(s) == f"Data: {load_recipe('official-31203').sticker.credit}"
        assert "design grid" in credit_text(s).lower() and "building instructions" in credit_text(s)
        assert "official" not in credit_text(s).lower()
        # the print sheet keeps the registry's full citation of the design grid
        page = print_sheet(s, "letter").page
        e = load_registry().get("kit31203-design")
        data = norm(" ".join(t.text for t in tagged(page.items, "citation", Text)))
        assert norm(e.citation) in data and norm(e.license) in data


class TestLivingPlanet:
    def test_ice_and_sea_ice(self, make):
        s = make("living-planet")
        land, ocean = s.legend.group("land").swatches, s.legend.group("ocean").swatches
        assert [sw.label for sw in land if sw.color == "lego_white"] == ["ice"]
        assert [sw.label for sw in ocean if sw.color == "lego_white"] == ["sea ice"]
        assert "ice" in drawn_labels(s.large) and "sea ice" in drawn_labels(s.large)
        assert [c.dataset for c in s.credits] == ["mod17a3-npp-mean-2000-2015",
                                                  "etopo2022-surface-10m",
                                                  "modis-aqua-chla-2013-2024"]

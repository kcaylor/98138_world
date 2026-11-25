"""The print sheet as a page model (feature 017, T031; FR-007, FR-010, FR-015; research R2;
contracts/sticker-files.md "Print sheet"; data-model.md PrintSheet).

One portrait page, Letter or A4: both stickers at true size with bleed and cut marks, captions,
the plaque parts, how-to and color notes, every dataset's full citation and license, the
provenance and the build sheets' ``furniture()``. Everything but the sticker content lies outside
the cut lines; a block that does not fit its area raises ``StickerError``.
Not affiliated with or endorsed by The LEGO Group.
"""

import dataclasses

import pytest

from lego_image_processor import __version__
from lego_image_processor.kit.plaque_parts import load_plaque_parts
from lego_image_processor.kit.source import DISCLAIMER
from lego_image_processor.layout.arrangement import parse_arrangement
from lego_image_processor.maps.build import build_map
from lego_image_processor.sheets.compose import PRINT_NOTE, text_width
from lego_image_processor.sheets.model import PAPERS, PT_MM, Circle, Line, Rect, Text
from lego_image_processor.stickers import PrintSheet, StickerError, print_sheet, sticker_set
from lego_image_processor.stickers.credits import Credit
from tests.stickers_support import sticker_recipe

EPS = 1e-6
CAP, DESCENT = 0.718, 0.21
SUBTITLE = ("Two stickers for Black tiles: print on white sticker paper at 100%, cut along the "
            "marks.")
LARGE_AT, SMALL_AT = (19.0, 41.0), (19.0, 118.8)


@pytest.fixture
def build(fixture_registry):
    fixture_registry.place_all()

    def _build(recipe_id, arrangement=None):
        return build_map(sticker_recipe(recipe_id), cache_dir=fixture_registry.cache_dir,
                         compare_official=False,
                         arrangement=parse_arrangement(arrangement) if arrangement else None)
    return _build


@pytest.fixture
def sst(build):
    return sticker_set(build("ocean-sst"))


def tagged(page, tag, kind=None):
    return [i for i in page.items if i.tag == tag and (kind is None or isinstance(i, kind))]


def norm(text):
    return " ".join(text.split())


def flow_text(page, *tags):
    return norm(" ".join(i.text for i in page.items if isinstance(i, Text) and i.tag in tags))


def bbox(it):
    if isinstance(it, Text):
        w = text_width(it.text, it.size_pt, it.bold)
        left = {"left": it.x, "center": it.x - w / 2, "right": it.x - w}[it.align]
        em = it.size_pt * PT_MM
        return left, it.y - CAP * em, left + w, it.y + DESCENT * em
    if isinstance(it, Rect):
        return it.x, it.y, it.x + it.w, it.y + it.h
    if isinstance(it, Circle):
        return it.cx - it.r, it.cy - it.r, it.cx + it.r, it.cy + it.r
    if isinstance(it, Line):
        return min(it.x1, it.x2), min(it.y1, it.y2), max(it.x1, it.x2), max(it.y1, it.y2)
    raise TypeError(it)


def overlaps(a, b):
    return a[0] < b[2] - EPS and b[0] < a[2] - EPS and a[1] < b[3] - EPS and b[1] < a[3] - EPS


@pytest.mark.parametrize("paper", ["letter", "a4"])
class TestPlacement:
    def test_page(self, sst, paper):
        sheet = print_sheet(sst, paper)
        assert isinstance(sheet, PrintSheet)
        assert sheet.paper == PAPERS[paper] == sheet.page.size
        p = sheet.page
        assert (p.kind, p.number, p.total) == ("stickers", 1, 1)
        assert sheet.items == p.items

    def test_cut_lines_at_true_size(self, sst, paper):
        page = print_sheet(sst, paper).page
        cuts = {dict(r.data)["sticker"]: r for r in tagged(page, "cut-line", Rect)}
        assert set(cuts) == {"large", "small"}
        large, small = cuts["large"], cuts["small"]
        assert (large.x, large.y) == LARGE_AT and (small.x, small.y) == SMALL_AT
        assert abs(large.w - 125.8) <= 0.1 and abs(large.h - 61.8) <= 0.1      # SC-001
        assert abs(small.w - 45.8) <= 0.1 and abs(small.h - 45.8) <= 0.1
        for r in (large, small):
            assert r.fill is None and r.stroke is None                     # unpainted (re n)
        assert page.items[-2:] == (large, small)                         # drawn last

    def test_bleed_and_marks(self, sst, paper):
        page = print_sheet(sst, paper).page
        black = load_plaque_parts().plaques["large"].tile.color.rgb
        bleeds = {dict(r.data)["sticker"]: r for r in tagged(page, "bleed", Rect)}
        assert bleeds["large"].fill == bleeds["small"].fill == black
        assert bbox(bleeds["large"]) == pytest.approx((17.0, 39.0, 146.8, 104.8))
        assert bbox(bleeds["small"]) == pytest.approx((17.0, 116.8, 66.8, 166.6))
        marks = tagged(page, "cut-mark", Line)
        assert len(marks) == 16
        by = {"large": [], "small": []}
        for m in marks:
            by[dict(m.data)["sticker"]].append(m)
        assert len(by["large"]) == len(by["small"]) == 8
        lx = [v for m in by["large"] for v in (m.x1, m.x2)]
        ly = [v for m in by["large"] for v in (m.y1, m.y2)]
        assert (min(lx), max(lx), min(ly), max(ly)) == pytest.approx((12.0, 151.8, 34.0, 109.8))
        sy = [v for m in by["small"] for v in (m.y1, m.y2)]
        assert (min(sy), max(sy)) == pytest.approx((111.8, 171.6))
        assert min(sy) - max(ly) == pytest.approx(2.0)           # 2 mm clear of the large marks

    def test_header(self, sst, paper):
        page = print_sheet(sst, paper).page
        title = tagged(page, "sheet-title", Text)
        assert [t.text for t in title] == ["Map stickers: Ocean temperature"]
        assert title[0].bold and title[0].size_pt == 16 and title[0].y == 21.0
        sub = tagged(page, "sheet-subtitle", Text)
        assert norm(" ".join(t.text for t in sub)) == SUBTITLE and sub[0].y == 27.5

    def test_captions_with_tile_sizes(self, sst, paper):
        page = print_sheet(sst, paper).page
        W = PAPERS[paper].width_mm
        text = flow_text(page, "caption")
        assert ("Large sticker 125.8 x 61.8 mm, for a Black tile 8 x 16 (about 127.8 x 63.8 mm)"
                in text)
        assert "Small sticker 45.8 x 45.8 mm, for a Black tile 6 x 6 (about 47.8 x 47.8 mm)" in text
        assert "for the front, the back of the frame or a display" in text.lower()
        for t in tagged(page, "caption", Text):
            l, top, r, b = bbox(t)
            assert r <= W - 12.0 + EPS
            assert l >= 152.0 - EPS or (l >= 77.8 - EPS and top >= 115.0 - EPS)

    def test_plaque_parts_block(self, sst, paper):
        page = print_sheet(sst, paper).page
        W = PAPERS[paper].width_mm
        assert flow_text(page, "parts-heading") == "Parts for a standalone plaque"
        text = flow_text(page, "part")
        table = load_plaque_parts()
        for size in ("small", "large"):
            for part in table.plaques[size].parts:
                c, n = part.color, part.numbers
                line = (f"1 {part.name}, {c.lego.name} - LEGO element {c.element_id}, design "
                        f"{', '.join(n.lego_design_ids)}; BrickLink {n.bricklink_item_no}, "
                        f"{c.bricklink.name} ({c.bricklink.id}); Rebrickable "
                        f"{n.rebrickable_part_num}, {c.rebrickable.name} ({c.rebrickable.id})")
                assert line in text
        assert text.count("1 Tile") == 2 and text.count("1 Plate") == 2
        assert flow_text(page, "printed-note") == "The sticker is printed, not a LEGO part."
        tags = ("parts-heading", "parts-plaque", "part", "printed-note")
        for t in page.items:
            if isinstance(t, Text) and t.tag in tags:
                l, top, r, b = bbox(t)
                assert l >= 77.8 - EPS and r <= W - 12.0 + EPS
                assert top >= 115.0 - EPS and b <= 172.0 + EPS

    def test_notes_data_provenance(self, sst, paper):
        page = print_sheet(sst, paper).page
        H = PAPERS[paper].height_mm
        assert "about 1 mm of tile shows on every side" in flow_text(page, "howto")
        assert flow_text(page, "color-note") == "Printed colors only approximate the LEGO colors."
        data = flow_text(page, "citation")
        for c in sst.credits:
            for value in (c.dataset, c.version, c.title, c.citation, c.license):
                assert norm(value) in data
        prov = flow_text(page, "provenance")
        assert f"Recipe {sst.recipe.id}" in prov and sst.recipe.sha256 in prov
        assert "legend values from the build hung as A" in prov
        assert f"Made with lego-image-processor {__version__}." in prov
        assert "no LEGO artwork, logo or image" in prov
        for t in page.items:
            if isinstance(t, Text) and t.tag in ("notes-heading", "howto", "color-note",
                                                 "citation", "provenance"):
                l, top, r, b = bbox(t)
                assert top >= 178.0 - EPS and b <= H - 24.0 + EPS

    def test_furniture(self, sst, paper):
        page = print_sheet(sst, paper).page
        H = PAPERS[paper].height_mm
        bar = tagged(page, "scale-bar", Line)
        assert len(bar) == 1 and abs(bar[0].x2 - bar[0].x1 - 100.0) <= EPS
        assert [t.text for t in tagged(page, "print-note", Text)][0] == PRINT_NOTE
        assert PRINT_NOTE == "Print at 100% (no fit-to-page)"
        assert [t.text for t in tagged(page, "footer-page", Text)] == ["Page 1 of 1"]
        assert tagged(page, "footer-title", Text)[0].text.startswith("Map stickers: ")
        furniture = [t for t in tagged(page, "disclaimer", Text) if t.y > H - 10]
        assert [t.text for t in furniture] == [DISCLAIMER]

    def test_texts_inside_the_margins(self, sst, paper):
        page = print_sheet(sst, paper).page
        W, H = PAPERS[paper].width_mm, PAPERS[paper].height_mm
        for t in page.items:
            # the build sheets' scale bar labels are centred on its ticks ("0" on the margin)
            if isinstance(t, Text) and t.tag != "scale-label":
                l, top, r, b = bbox(t)
                assert l >= 12.0 - EPS and r <= W - 12.0 + EPS, (t.tag, t.text)
                assert top >= 0 and b <= H, (t.tag, t.text)

    def test_everything_else_outside_the_cut_lines(self, sst, paper):
        """FR-010: only the sticker content lies inside the cut lines."""
        page = print_sheet(sst, paper).page
        content = set(sst.large.content_items(*LARGE_AT)) | set(sst.small.content_items(*SMALL_AT))
        cuts = [bbox(r) for r in tagged(page, "cut-line", Rect)]
        inside = 0
        for it in page.items:
            if it in content:
                inside += 1
                continue
            if it.tag in ("cut-line", "bleed"):
                continue
            for c in cuts:
                assert not overlaps(bbox(it), c), (it.tag, getattr(it, "text", ""))
        assert inside == len(content)                        # every sticker item is on the page

    def test_stickers_drawn_from_their_page_models(self, sst, paper):
        page = print_sheet(sst, paper).page
        items = set(page.items)
        for st, at in ((sst.large, LARGE_AT), (sst.small, SMALL_AT)):
            drawn = st.drawing(*at)
            assert set(drawn) <= items
            # bleed, marks, then the sticker's own content (contracts/sticker-files.md)
            tags = [i.tag for i in drawn]
            assert tags[0] == "bleed" and tags[1:9] == ["cut-mark"] * 8
            assert tags[9] == "sticker-bg"
            assert len(drawn) == len(st.items) + 8


class TestArrangement:
    def test_only_the_provenance_line_depends_on_the_arrangement(self, build):
        a = print_sheet(sticker_set(build("ocean-sst", "A")), "letter").page
        b = print_sheet(sticker_set(build("ocean-sst", "B")), "letter").page
        assert "hung as B" in flow_text(b, "provenance")
        da = [i for i in a.items if i not in set(b.items)]
        db = [i for i in b.items if i not in set(a.items)]
        assert da and len(da) == len(db)
        for x, y in zip(da, db):
            assert x.tag == y.tag == "provenance"
            assert x.text.replace("hung as A", "hung as B") == y.text

    def test_same_set_same_sheet(self, sst):
        assert print_sheet(sst, "letter") == print_sheet(sst, "letter")
        assert print_sheet(sst, "a4") != print_sheet(sst, "letter")


class TestDoesNotFit:
    @pytest.mark.parametrize("paper,label", [("letter", "Letter"), ("a4", "A4")])
    def test_citation_block_too_long(self, sst, paper, label):
        huge = Credit(dataset="huge", version="1", text="Huge, Somebody", title="Huge",
                      doi=None, publisher="Somebody", citation=" ".join(["citation"] * 3000),
                      license="CC0")
        s = dataclasses.replace(sst, credits=sst.credits + (huge,))
        with pytest.raises(StickerError) as exc:
            print_sheet(s, paper)
        msg = str(exc.value)
        assert "data" in msg and label in msg and "does not fit" in msg
        assert exc.value.field == "data"
        assert exc.value.needed_mm > exc.value.available_mm

    def test_unknown_paper(self, sst):
        with pytest.raises(ValueError, match="letter or a4"):
            print_sheet(sst, "legal")

    @pytest.mark.parametrize("recipe_id", ["ocean-sst", "living-planet", "rainfall",
                                           "official-31203", "land-elevation"])
    @pytest.mark.parametrize("paper", ["letter", "a4"])
    def test_bundled_maps_fit(self, build, recipe_id, paper):
        sheet = print_sheet(sticker_set(build(recipe_id)), paper)
        assert all(t.size_pt >= 5.0 for t in sheet.items if isinstance(t, Text))

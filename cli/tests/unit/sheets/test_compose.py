"""Page composition (006 T011, T018): section, overview and legend pages from the page model."""

from collections import Counter

import pytest

from lego_image_processor import __version__
from lego_image_processor.kit.source import DISCLAIMER
from lego_image_processor.parts import ACKNOWLEDGEMENT
from lego_image_processor.sheets import SheetError, build_sheet_set
from lego_image_processor.sheets.model import Circle, Line, Rect, Text

from .layouts import FEW, every_cited_color, full_grid

PITCH = 8.0


def items(page, kind, tag):
    return [i for i in page.items if isinstance(i, kind) and i.tag == tag]


def data(item):
    return dict(item.data)


def texts(page):
    return [i.text for i in page.items if isinstance(i, Text)]


def section_page(sheet_set, label):
    return next(p for p in sheet_set.pages if p.kind == "section" and p.label == label)


@pytest.fixture(scope="module")
def official_set(official_grid):
    return build_sheet_set(official_grid, layout_path="official.json")


@pytest.fixture(scope="module")
def few_set(few_grid):
    return build_sheet_set(few_grid, layout_path="few.json")


# --- section pages (US1) ------------------------------------------------------------------------

def test_page_order_and_count(official_set):
    kinds = [p.kind for p in official_set.pages]
    assert kinds[0] == "overview" and kinds.count("section") == 40
    assert kinds == ["overview"] + ["legend"] * kinds.count("legend") + ["section"] * 40
    labels = [p.label for p in official_set.pages if p.kind == "section"]
    assert labels[:6] == ["A1", "A2", "A3", "A4", "A5", "B1"] and labels[-1] == "H5"
    n = len(official_set.pages)
    assert [p.number for p in official_set.pages] == list(range(1, n + 1))
    assert all(p.total == n for p in official_set.pages)


def test_section_studs_match_layout(few_grid, few_set):
    page = section_page(few_set, "C2")
    studs = items(page, Circle, "stud")
    assert len(studs) == 256
    numbers = {(e.lot.part_id, e.lot.color_key): e for e in few_set.legend}
    by_xy = {(p.x, p.y): p for p in few_grid.positions}
    numbers_text = {(int(data(t)["x"]), int(data(t)["y"])): t.text
                    for t in items(page, Text, "stud-number")}
    for c in studs:
        d = data(c)
        x, y = int(d["x"]), int(d["y"])
        assert 32 <= x <= 47 and 16 <= y <= 31
        entry = numbers[(by_xy[(x, y)].lego_part_id, by_xy[(x, y)].color_id)]
        assert int(d["lot"]) == entry.number and c.fill == entry.rgb
        assert numbers_text[(x, y)] == str(entry.number)
    rings = items(page, Circle, "ring")
    plates = sum(1 for (x, y), p in by_xy.items()
                 if 32 <= x <= 47 and 16 <= y <= 31 and p.part_type == "plate")
    assert len(rings) == plates > 0


def test_true_scale_pitch(few_set):
    studs = items(section_page(few_set, "A1"), Circle, "stud")
    xs = sorted({round(c.cx, 4) for c in studs})
    ys = sorted({round(c.cy, 4) for c in studs})
    assert len(xs) == len(ys) == 16
    assert all(abs((b - a) - PITCH) < 0.05 for a, b in zip(xs, xs[1:]))
    assert all(abs((b - a) - PITCH) < 0.05 for a, b in zip(ys, ys[1:]))
    assert all(abs(c.r * 2 - 7.0) < 0.01 for c in studs)
    # Grid fits inside the page margins.
    size = section_page(few_set, "A1").size
    assert min(xs) - 3.5 >= 12 and max(xs) + 3.5 <= size.width_mm - 12


def test_edge_coordinates_and_header(few_set):
    page = section_page(few_set, "C2")
    coords = {t.text for t in items(page, Text, "col-coord")}
    rows = {t.text for t in items(page, Text, "row-coord")}
    assert coords == {str(x) for x in range(32, 48)} and rows == {str(y) for y in range(16, 32)}
    t = " ".join(texts(page))
    assert "Section C2" in t and "columns 32-47, rows 16-31" in t and "frame 2 of 3" in t


def test_locator_highlights_section(few_set):
    page = section_page(few_set, "C2")
    cells = items(page, Rect, "locator")
    assert len(cells) == 40
    on = [c for c in cells if data(c).get("on") == "1"]
    assert len(on) == 1 and data(on[0])["label"] == "C2"


def test_count_table_sums_to_256(few_grid, few_set):
    page = section_page(few_set, "C2")
    counts = {int(data(t)["lot"]): int(t.text) for t in items(page, Text, "count")}
    assert sum(counts.values()) == 256
    numbers = {(e.lot.part_id, e.lot.color_key): e.number for e in few_set.legend}
    expect = Counter(numbers[(p.lego_part_id, p.color_id)] for p in few_grid.positions
                     if 32 <= p.x <= 47 and 16 <= p.y <= 31)
    assert counts == dict(expect)
    assert "Total 256" in texts(page)
    names = " ".join(t.text for t in items(page, Text, "count-name"))
    assert "plate" in names and "tile" in names


def test_every_page_has_scale_bar_and_footer(official_set):
    for p in official_set.pages:
        bars = items(p, Line, "scale-bar")
        assert len(bars) == 1 and abs((bars[0].x2 - bars[0].x1) - 100.0) < 1e-9
        t = texts(p)
        assert DISCLAIMER in t
        assert f"Page {p.number} of {p.total}" in t
        assert "Print at 100% (no fit-to-page)" in t


def test_all_text_latin1(official_set):
    for p in official_set.pages:
        for t in texts(p):
            t.encode("latin-1")


# --- overview and legend (US2) ------------------------------------------------------------------

def test_overview_map_and_grid(official_grid, official_set):
    page = official_set.pages[0]
    studs = items(page, Circle, "map-stud")
    assert len(studs) == 10240
    xs = sorted({round(c.cx, 4) for c in studs})
    assert len(xs) == 128 and abs((xs[1] - xs[0]) - 1.4) < 1e-6
    rings = items(page, Circle, "map-ring")
    assert len(rings) == official_grid.land_positions
    assert [t.text for t in items(page, Text, "map-col-label")] == list("ABCDEFGH")
    assert [t.text for t in items(page, Text, "map-row-label")] == list("12345")
    frames = items(page, Line, "frame-line")
    x0 = min(xs) - 0.7
    assert sorted(round(l.x1 - x0, 4) for l in frames) == [round(32 * 1.4, 4), round(96 * 1.4, 4)]
    assert len(items(page, Line, "section-line")) == 7 + 4 - 2  # inner lines minus the frame lines


def test_overview_totals_and_provenance_image(official_set):
    t = " ".join(texts(official_set.pages[0]))
    assert "10,240 pieces" in t and "3,062" in t and "7,178" in t
    assert "official.json" in t and "official-31203-design" in t
    assert f"lego-image-processor {__version__}" in t
    assert "LEGO World Map 31203 template: 128 x 80 studs, 40 sections" in t
    assert "without cited IDs" not in t


def test_overview_provenance_recipe():
    meta = {"recipe": {"id": "land-elevation", "title": "Land elevation", "format": "1",
                       "sha256": "c" * 64},
            "layers": [{"class": "land", "dataset": {
                "id": "etopo2022-surface-10m", "version": "v1", "license": "Public domain (NOAA)",
                "citation": "NOAA NCEI. 2022: ETOPO 2022."}}, {"class": "ocean"}],
            "tool_version": "0.1.0"}
    grid = full_grid(FEW, source_image="recipe:land-elevation", map_metadata=meta)
    s = build_sheet_set(grid, layout_path="elev.json", layout_sha256="d" * 64)
    assert s.title == "Land elevation"
    t = " ".join(texts(s.pages[0]))
    assert "land-elevation" in t and "Land elevation" in t
    assert "Public domain (NOAA)" in t and "NOAA NCEI. 2022: ETOPO 2022." in t
    assert "d" * 64 in t


def test_title_defaults_and_override(few_grid):
    assert build_sheet_set(few_grid, layout_path="/tmp/x/few.json").title == "few.json"
    assert build_sheet_set(few_grid, title="My map").title == "My map"
    s = build_sheet_set(few_grid, title="My map")
    assert all("My map" in texts(p) for p in s.pages)


def test_unverified_warning_and_legend(uncited_grid):
    s = build_sheet_set(uncited_grid, layout_path="u.json")
    t = " ".join(texts(s.pages[0]))
    assert "1 lot(s) without cited IDs" in t
    legend = " ".join(" ".join(texts(p)) for p in s.pages if p.kind == "legend")
    assert "no cited IDs" in legend and "Medium Blue" in legend


def test_legend_fields_equal_parts_list(few_set):
    legend = " ".join(" ".join(texts(p)) for p in few_set.pages if p.kind == "legend")
    for e in few_set.legend:
        r = e.lot.ids
        assert f"{r.lego_name} ({r.lego_id})" in legend and r.element_id in legend
        assert f"{r.bricklink_item_no} / {r.bricklink_color_name} ({r.bricklink_color_id})" in legend
        assert f"{r.rebrickable_part_num} / {r.rebrickable_color_name} ({r.rebrickable_color_id})" in legend
        assert f"{e.lot.needed:,}" in legend
    assert "4073 / White (1)" in legend and "6141 / White (15)" in legend and "98138 / " in legend
    assert ACKNOWLEDGEMENT in legend
    swatches = [c for p in few_set.pages if p.kind == "legend" for c in items(p, Circle, "swatch")]
    assert len(swatches) == len(few_set.legend)


def test_legend_paginates_before_sections():
    s = build_sheet_set(full_grid(every_cited_color()), layout_path="many.json")
    kinds = [p.kind for p in s.pages]
    n_legend = kinds.count("legend")
    assert n_legend >= 3  # 90 lots at about 25 per page
    assert kinds == ["overview"] + ["legend"] * n_legend + ["section"] * 40
    swatches = [c for p in s.pages if p.kind == "legend" for c in items(p, Circle, "swatch")]
    assert [int(data(c)["lot"]) for c in swatches] == list(range(1, 91))


# --- subsets and paper (US4) --------------------------------------------------------------------

def test_sections_subset(few_grid):
    s = build_sheet_set(few_grid, sections="C2,B2")
    labels = [p.label for p in s.pages if p.kind == "section"]
    assert labels == ["B2", "C2"]
    assert s.pages[0].kind == "overview" and s.pages[1].kind == "legend"
    assert all(p.total == len(s.pages) for p in s.pages)
    with pytest.raises(SheetError, match="J9"):
        build_sheet_set(few_grid, sections="J9")


def test_a4_keeps_true_scale(few_grid):
    s = build_sheet_set(few_grid, paper="a4", sections="A1")
    page = section_page(s, "A1")
    assert (page.size.width_mm, page.size.height_mm) == (210.0, 297.0)
    xs = sorted({round(c.cx, 4) for c in items(page, Circle, "stud")})
    assert all(abs((b - a) - PITCH) < 0.05 for a, b in zip(xs, xs[1:]))
    bar = items(page, Line, "scale-bar")[0]
    assert abs((bar.x2 - bar.x1) - 100.0) < 1e-9


def test_incomplete_layout_is_rejected():
    from ..parts.layouts import SMALL, make_grid
    with pytest.raises(SheetError, match="10,240"):
        build_sheet_set(make_grid(SMALL))


def test_deterministic(few_grid):
    a = build_sheet_set(few_grid, layout_path="few.json")
    b = build_sheet_set(few_grid, layout_path="few.json")
    assert a.pages == b.pages


def test_more_than_99_lots():
    """Edge case: 3-digit lot numbers stay inside the stud (smaller type); the legend paginates."""
    colors = every_cited_color() + [("tile", f"lego_extra_{i}", f"Extra {i}", str(9100 + i))
                                    for i in range(30)]
    s = build_sheet_set(full_grid(colors), sections="G1")  # G1 holds lots 97-120 (x + y >= 96)
    assert len(s.legend) == 120
    assert [p.kind for p in s.pages].count("legend") >= 5
    numbers = items(section_page(s, "G1"), Text, "stud-number")
    small = {t.size_pt for t in numbers if len(t.text) == 3}
    big = {t.size_pt for t in numbers if len(t.text) <= 2}
    assert small and big and max(small) < min(big)


def test_studs_have_grey_outline(few_set):
    """Edge case: White and Black studs stay visible on white paper."""
    studs = items(section_page(few_set, "A1"), Circle, "stud")
    assert all(c.stroke is not None and c.stroke not in ((255, 255, 255), (0, 0, 0)) and
               c.stroke_w >= 0.2 for c in studs)


# --- a template layout (feature 016 T066; US1-7, FR-015, SC-004; research R16) ------------------

@pytest.fixture
def winkel(confirmed_winkel):
    from ...winkel_layouts import winkel_grid
    grid = winkel_grid(confirmed_winkel)
    return grid, build_sheet_set(grid, layout_path="winkel.json", layout_sha256="e" * 64)


def test_template_set_uses_the_kit_sections_with_the_disclaimer(winkel):
    grid, s = winkel
    kinds = [p.kind for p in s.pages]
    assert kinds == ["overview"] + ["legend"] * kinds.count("legend") + ["section"] * 40
    labels = [p.label for p in s.pages if p.kind == "section"]
    assert labels[0] == "A1" and labels[-1] == "H5" and len(set(labels)) == 40
    assert all(DISCLAIMER in texts(p) for p in s.pages)
    assert all(t.isascii() or t.encode("latin-1") for p in s.pages for t in texts(p))


def test_margin_studs_are_squares_with_lot_numbers(winkel, confirmed_winkel):
    grid, s = winkel
    sq = next(e for e in s.legend if e.lot.part_id == "3070b")
    total = 0
    for page in (p for p in s.pages if p.kind == "section"):
        squares = items(page, Rect, "stud")
        rounds = items(page, Circle, "stud")
        assert len(squares) + len(rounds) == 256
        numbers = {(int(data(t)["x"]), int(data(t)["y"])): t.text for t in items(page, Text, "stud-number")}
        assert len(numbers) == 256
        for r in squares:
            x, y = int(data(r)["x"]), int(data(r)["y"])
            assert confirmed_winkel.class_at(y, x) == "margin"
            assert int(data(r)["lot"]) == sq.number and r.fill == sq.rgb and numbers[(x, y)] == str(sq.number)
            assert abs(r.w - 7.0) < 1e-9 and abs(r.h - 7.0) < 1e-9 and r.stroke is not None
        for c in rounds:
            assert confirmed_winkel.class_at(int(data(c)["y"]), int(data(c)["x"])) != "margin"
        assert not [c for c in items(page, Circle, "ring")
                    if confirmed_winkel.class_at(int(data(c)["y"]), int(data(c)["x"])) != "land"]
        total += len(squares)
        if squares:
            discs = [r for r in items(page, Rect, "count-disc") if int(data(r)["lot"]) == sq.number]
            assert len(discs) == 1
            assert any(t.text.startswith("Black (square tile)") for t in items(page, Text, "count-name"))
    assert total == confirmed_winkel.counts["margin"]


def test_overview_draws_margin_studs_as_small_squares(winkel, confirmed_winkel):
    _, s = winkel
    page = s.pages[0]
    c = confirmed_winkel.counts
    squares = items(page, Rect, "map-stud")
    assert len(squares) == c["margin"] and len(items(page, Circle, "map-stud")) == c["land"] + c["ocean"]
    assert all(abs(r.w - 1.2) < 1e-9 and abs(r.h - 1.2) < 1e-9 for r in squares)
    assert len(items(page, Circle, "map-ring")) == c["land"]


def test_legend_has_a_square_swatch_for_the_square_tile(winkel):
    _, s = winkel
    pages = [p for p in s.pages if p.kind == "legend"]
    squares = [r for p in pages for r in items(p, Rect, "swatch")]
    sq = next(e for e in s.legend if e.lot.part_id == "3070b")
    assert [int(data(r)["lot"]) for r in squares] == [sq.number]
    assert len([c for p in pages for c in items(p, Circle, "swatch")]) == len(s.legend) - 1
    text = " ".join(" ".join(texts(p)) for p in pages)
    assert "tile 1x1 square" in text
    notes = [t.text for p in pages for t in items(p, Text, "legend-note")]
    assert notes and all("square" in n and not n.endswith("...") for n in notes)


def test_overview_text_names_the_template_and_square_tiles(winkel, confirmed_winkel):
    _, s = winkel
    page = s.pages[0]
    c = confirmed_winkel.counts
    totals = " ".join(t.text for t in items(page, Text, "totals"))
    assert (f"10,240 pieces: {c['land']:,} plates 1x1 round (land, part 6141), {c['ocean']:,} tiles 1x1 "
            f"round (ocean, part 98138), {c['margin']:,} tiles 1x1 square (margin, part 3070b);") in totals
    subtitle = items(page, Text, "subtitle")[0].text
    assert "winkel-tripel" in subtitle and "cannot be re-hung" in subtitle and not subtitle.endswith("...")
    arrangement = " ".join(t.text for t in items(page, Text, "arrangement"))
    assert "winkel-tripel" in arrangement and "the frames of a curved map cannot be re-hung" in arrangement
    assert "Every combination uses the same pieces" not in arrangement
    howto = " ".join(t.text for t in items(page, Text, "howto"))
    assert "square tiles (margin)" in howto


def test_provenance_names_the_template_and_its_dataset(winkel):
    grid, s = winkel
    prov = " ".join(t.text for t in items(s.pages[0], Text, "provenance"))
    rec = grid.template
    assert f"Template: {rec['id']} ({rec['title']})" in prov
    assert rec["projection"]["proj"] in prov and rec["source"]["sha256"] in prov
    conf = rec["source"]["confirmation"]
    assert f"confirmed by the {conf['role']} on {conf['date']}" in prov
    ds = rec["dataset"]
    for k in ("id", "version", "title", "license", "citation"):
        assert ds[k] in prov, k
    assert "(more in the parts list JSON)" not in texts(s.pages[0])


def test_kit_sheets_keep_their_text(official_set):
    page = official_set.pages[0]
    prov = [t.text for t in items(page, Text, "provenance")]
    assert not any(t.startswith("Template") for t in prov)
    assert items(page, Text, "subtitle")[0].text == "LEGO World Map 31203 template: 128 x 80 studs, 40 sections"
    assert "Every combination uses the same pieces." in " ".join(t.text for t in items(page, Text, "arrangement"))
    assert "square" not in " ".join(texts(page))
    assert not [r for p in official_set.pages for r in items(p, Rect, "stud")]

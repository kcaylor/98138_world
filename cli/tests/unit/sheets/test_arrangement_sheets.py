"""Build sheets, counts and parts lists in arrangements B and C (feature 007 US4, FR-013-FR-016)."""

import json
from collections import Counter

import pytest

from lego_image_processor.layout.arrangement import arrange_grid, parse_arrangement
from lego_image_processor.parts import build_parts_list
from lego_image_processor.sheets import build_sheet_set, section_counts
from lego_image_processor.sheets.model import Circle, Line, Text
from lego_image_processor.sheets.sections import arranged_sections, section_for

MAP_PITCH = 1.4


def items(page, kind, tag):
    return [i for i in page.items if isinstance(i, kind) and i.tag == tag]


def texts(page):
    return [i.text for i in page.items if isinstance(i, Text)]


@pytest.fixture(scope="module")
def grids(official_grid):
    return {aid: arrange_grid(official_grid, parse_arrangement(aid)) for aid in ("A", "B", "C")}


@pytest.fixture(scope="module")
def sets(grids):
    return {aid: build_sheet_set(g, layout_path=f"{aid}.json") for aid, g in grids.items()}


def test_arranged_sections_b():
    s = {x.label: x for x in arranged_sections(parse_arrangement("B"))}
    assert len(s) == 40
    assert (s["A1"].frame, s["A1"].kit_label, s["A1"].x_range) == (3, "G1", (0, 15))
    assert (s["C3"].frame, s["C3"].kit_label) == (1, "A3")
    assert (s["E5"].frame, s["E5"].kit_label) == (2, "C5")
    assert (s["H2"].frame, s["H2"].kit_label) == (2, "F2")
    kit = {x.label: x for x in arranged_sections(parse_arrangement("A"))}
    assert s["A1"].instruction_page == kit["G1"].instruction_page
    assert [x.label for x in arranged_sections(parse_arrangement("B"))][:6] == ["A1", "A2", "A3", "A4", "A5", "B1"]
    assert [x.order for x in arranged_sections(parse_arrangement("B"))] == list(range(1, 41))


def test_arranged_sections_c():
    s = {x.label: x for x in arranged_sections(parse_arrangement("C"))}
    assert (s["A1"].frame, s["A1"].kit_label) == (2, "C1")
    assert (s["E1"].frame, s["E1"].kit_label) == (3, "G1")
    assert (s["G1"].frame, s["G1"].kit_label) == (1, "A1")


def test_a_sections_unchanged():
    s = arranged_sections(parse_arrangement("A"))
    assert all(x.kit_label == x.label for x in s)
    assert section_for(40, 20, parse_arrangement("B")).kit_label == "A2"


@pytest.mark.parametrize("aid,bounds", [("A", (32, 96)), ("B", (32, 64)), ("C", (64, 96))])
def test_overview_frame_lines(sets, aid, bounds):
    page = sets[aid].pages[0]
    xs = sorted({round(c.cx, 4) for c in items(page, Circle, "map-stud")})
    x0 = min(xs) - MAP_PITCH / 2
    frames = items(page, Line, "frame-line")
    assert sorted(round(l.x1 - x0, 4) for l in frames) == [round(b * MAP_PITCH, 4) for b in bounds]
    assert len(items(page, Line, "section-line")) == 7 + 4 - 2


@pytest.mark.parametrize("aid,names", [
    ("A", ["Frame 1: America", "Frame 2: Europe & Africa", "Frame 3: Asia & Australia"]),
    ("B", ["Frame 3: Asia & Australia", "Frame 1: America", "Frame 2: Europe & Africa"]),
    ("C", ["Frame 2: Europe & Africa", "Frame 3: Asia & Australia", "Frame 1: America"])])
def test_overview_frame_names_in_order(sets, aid, names):
    labels = sorted(items(sets[aid].pages[0], Text, "frame-label"), key=lambda t: t.x)
    assert [t.text for t in labels] == names


def test_overview_states_combination(sets):
    t = " ".join(texts(sets["B"].pages[0]))
    assert "Combination B" in t and "3·1·2" in t and "America in the centre" in t
    assert "LEGO 31203 building instructions, pp. 7-8" in t
    assert "Combination A" in " ".join(texts(sets["A"].pages[0]))


def test_section_page_names_frame_and_kit_section(sets):
    page = next(p for p in sets["B"].pages if p.kind == "section" and p.label == "A1")
    t = " ".join(texts(page))
    assert "frame 3 of 3 (Asia & Australia)" in t
    assert "kit section G1" in t
    loc = items(page, Line, "locator-frame")
    assert len(loc) == 2
    a_page = next(p for p in sets["A"].pages if p.kind == "section" and p.label == "C2")
    assert "frame 2 of 3" in " ".join(texts(a_page))


def test_section_studs_follow_display(sets, grids):
    g = grids["B"]
    page = next(p for p in sets["B"].pages if p.kind == "section" and p.label == "A1")
    studs = [i for i in page.items if isinstance(i, Circle) and i.tag == "stud"]
    xy = {(dict(s.data)["x"], dict(s.data)["y"]) for s in studs if s.data}
    assert ("0", "0") in xy and ("15", "15") in xy and len(xy) == 256


def test_counts_json(grids):
    sc = section_counts(grids["B"])
    d = json.loads(sc.to_json())
    assert d["arrangement"] == "B"
    s0 = d["sections"][0]
    assert (s0["label"], s0["frame"], s0["kit_label"]) == ("A1", 3, "G1")
    totals = Counter()
    for s in d["sections"]:
        for k, v in s["counts"].items():
            totals[int(k)] += v
    assert {e["number"]: e["total"] for e in d["legend"]} == dict(totals)
    # The counts of a section as hung equal the kit section's counts in A.
    a = {s["label"]: s["counts"] for s in json.loads(section_counts(grids["A"]).to_json())["sections"]}
    for s in d["sections"]:
        assert s["counts"] == a[s["kit_label"]]


def test_parts_list_unchanged_with_note(grids):
    a = build_parts_list(grids["A"])
    b = build_parts_list(grids["B"])
    assert [(l.part_id, l.color_key, l.needed) for l in a.lots] == [(l.part_id, l.color_key, l.needed) for l in b.lots]
    blk = b.layout["arrangement"]
    assert blk["id"] == "B" and "same pieces" in blk["note"]

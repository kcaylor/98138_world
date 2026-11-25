"""Per-section counts (006 T009, FR-013, contracts/counts-format.md)."""

import json
from collections import Counter

from lego_image_processor.kit.source import DISCLAIMER
from lego_image_processor.parts import build_parts_list
from lego_image_processor.sheets import section_counts


def test_every_section_totals_256(official_grid):
    sc = section_counts(official_grid)
    assert len(sc.sections) == 40
    assert all(s.total == 256 == sum(s.counts.values()) for s in sc.sections)


def test_per_lot_sums_equal_parts_list(official_grid):
    pl = build_parts_list(official_grid)
    sc = section_counts(official_grid, pl)
    total = Counter()
    for s in sc.sections:
        total.update(s.counts)
    assert sum(total.values()) == 10240
    assert {e.number: e.lot.needed for e in sc.legend} == dict(total)


def test_counts_match_positions(few_grid):
    sc = section_counts(few_grid)
    numbers = {(e.lot.part_id, e.lot.color_key): e.number for e in sc.legend}
    c2 = next(s for s in sc.sections if s.section.label == "C2")
    expect = Counter(numbers[(p.lego_part_id, p.color_id)] for p in few_grid.positions
                     if 32 <= p.x <= 47 and 16 <= p.y <= 31)
    assert c2.counts == dict(expect)


def test_json_shape_and_order(official_grid):
    sc = section_counts(official_grid, layout_path="official.json", layout_sha256="ab" * 32)
    text = sc.to_json()
    d = json.loads(text)
    assert list(d) == ["format_version", "kit", "arrangement", "layout", "legend", "sections", "disclaimer"]
    assert d["format_version"] == "1" and d["kit"] == "31203" and d["disclaimer"] == DISCLAIMER
    assert d["layout"] == {"path": "official.json", "sha256": "ab" * 32,
                           "source_image": "official-31203-design"}
    assert list(d["legend"][0]) == ["number", "part_id", "part_type", "color_key", "name",
                                    "verified", "total"]
    s0 = d["sections"][0]
    assert list(s0) == ["label", "col", "row", "x", "y", "frame", "kit_label", "counts", "total"]
    assert (s0["label"], s0["x"], s0["y"], s0["frame"]) == ("A1", [0, 15], [0, 15], 1)
    assert [s["label"] for s in d["sections"]][:6] == ["A1", "A2", "A3", "A4", "A5", "B1"]
    for s in d["sections"]:
        keys = [int(k) for k in s["counts"]]
        assert keys == sorted(keys) and all(v > 0 for v in s["counts"].values())
    assert "generated" not in text and text.endswith("\n")
    assert sc.to_json() == text


# --- a template layout (feature 016 T066; data-model.md SectionCounts.template) -----------------

def test_square_tiles_are_counted_per_section_and_json_names_the_template(confirmed_winkel):
    from ...winkel_layouts import winkel_grid
    grid = winkel_grid(confirmed_winkel)
    sc = section_counts(grid, layout_path="w.json")
    assert len(sc.sections) == 40 and all(s.total == 256 for s in sc.sections)
    sq = next(e for e in sc.legend if e.lot.part_id == "3070b")
    assert sum(s.counts.get(sq.number, 0) for s in sc.sections) == confirmed_winkel.counts["margin"]
    a1 = next(s for s in sc.sections if s.section.label == "A1")
    assert a1.counts[sq.number] == int(confirmed_winkel.margin[0:16, 0:16].sum())
    d = json.loads(sc.to_json())
    assert list(d) == ["format_version", "kit", "arrangement", "template", "layout", "legend",
                       "sections", "disclaimer"]
    assert d["template"] == {"id": "winkel-tripel", "title": confirmed_winkel.title}
    row = next(r for r in d["legend"] if r["part_id"] == "3070b")
    assert row["part_type"] == "square_tile" and row["total"] == confirmed_winkel.counts["margin"]


def test_kit_counts_have_no_template(official_grid):
    assert "template" not in json.loads(section_counts(official_grid).to_json())


# --- the in-margin plaque (feature 017 T074; contracts/in-margin-plaque.md "Build sheets and counts") --

def test_plaque_lot_is_counted_in_its_section(confirmed_winkel):
    from lego_image_processor.kit.plaque_parts import load_plaque_parts
    from lego_image_processor.maps.margin import place_plaque
    from ...winkel_layouts import winkel_grid
    tile = load_plaque_parts().plaques["small"].tile
    rec = place_plaque(confirmed_winkel, "bottom-left", "option").layout_record()
    sc = section_counts(winkel_grid(confirmed_winkel, plaque=rec), layout_path="p.json")
    (e,) = [e for e in sc.legend if e.lot.part_type == "plaque_tile"]
    holding = [s for s in sc.sections if e.number in s.counts]
    assert [s.section.label for s in holding] == ["A5"] and holding[0].counts[e.number] == 1
    assert holding[0].total == 256 - 36 + 1
    assert all(s.total == 256 for s in sc.sections if s.section.label != "A5")
    sq = next(x for x in sc.legend if x.lot.part_id == "3070b")
    assert sum(s.counts.get(sq.number, 0) for s in sc.sections) == confirmed_winkel.counts["margin"] - 36
    d = json.loads(sc.to_json())
    row = next(r for r in d["legend"] if r["number"] == e.number)
    assert (row["part_id"], row["part_type"], row["color_key"], row["total"]) == \
        (tile.part_id, "plaque_tile", tile.color.key, 1)
    a5 = next(s for s in d["sections"] if s["label"] == "A5")
    assert a5["counts"][str(e.number)] == 1 and a5["total"] == 221
    assert [int(k) for k in a5["counts"]] == sorted(int(k) for k in a5["counts"])


def test_counts_without_a_plaque_have_no_plaque_lot(confirmed_winkel):
    from ...winkel_layouts import winkel_grid
    sc = section_counts(winkel_grid(confirmed_winkel))
    assert not [e for e in sc.legend if e.lot.part_type == "plaque_tile"]

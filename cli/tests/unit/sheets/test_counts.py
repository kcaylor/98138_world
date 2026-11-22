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

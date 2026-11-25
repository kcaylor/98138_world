"""Pacific-centred combinations D and E (feature 010, FR-001-FR-004, FR-006).

Not affiliated with or endorsed by The LEGO Group.
"""

import copy
import json

import pytest

from lego_image_processor.layout import arrangement as arr
from lego_image_processor.layout.arrangement import (
    ArrangementError, arrange_grid, assembly_note, assembly_steps, load_arrangements,
    parse_arrangement)

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."

# The 007 layout records, exactly (A-C must not change).
SRC_78 = {"title": "LEGO 31203 World Map building instructions",
          "url": "https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6372756.pdf",
          "sha256": "b593e2f4befbc227c5b12fec9b58a1bd6141d19b54de5f5336dcc8cc9eb43c4c",
          "pages": [7, 8], "citation": "LEGO 31203 building instructions, pp. 7–8"}
RECORDS_007 = {
    "A": {"id": "A", "name": "europe-africa", "centre": "Europe and Africa", "frame_order": [1, 2, 3],
          "column_shift": 0, "source": SRC_78},
    "B": {"id": "B", "name": "americas", "centre": "America", "frame_order": [3, 1, 2],
          "column_shift": 32, "source": SRC_78},
    "C": {"id": "C", "name": "asia-australia", "centre": "Asia and Australia",
          "frame_order": [2, 3, 1], "column_shift": -32, "source": SRC_78},
}


@pytest.mark.parametrize("aid", ["A", "B", "C"])
def test_a_to_c_records_unchanged(aid):
    a = parse_arrangement(aid)
    assert json.dumps(a.record(), ensure_ascii=False) == json.dumps(RECORDS_007[aid], ensure_ascii=False)
    assert a.in_instructions and not a.is_split


@pytest.mark.parametrize("aid,describe", [
    ("A", "A (europe-africa, frames 1·2·3, Europe and Africa in the centre)"),
    ("B", "B (americas, frames 3·1·2, America in the centre)"),
    ("C", "C (asia-australia, frames 2·3·1, Asia and Australia in the centre)")])
def test_a_to_c_describe_unchanged(aid, describe):
    assert parse_arrangement(aid).describe() == describe


@pytest.mark.parametrize("aid,name,shift,strips,groups,order", [
    ("A", "europe-africa", 0, "ABCDEFGH", ("1", "2", "3"), (1, 2, 3)),
    ("B", "americas", 32, "GHABCDEF", ("3", "1", "2"), (3, 1, 2)),
    ("C", "asia-australia", -32, "CDEFGHAB", ("2", "3", "1"), (2, 3, 1)),
    ("D", "pacific", 64, "EFGHABCD", ("2b", "3", "1", "2a"), (2, 3, 1, 2)),
    ("E", "asia-pacific", 80, "DEFGHABC", ("2b", "3", "1", "2a"), (2, 3, 1, 2))])
def test_strip_model(aid, name, shift, strips, groups, order):
    a = parse_arrangement(aid)
    assert (a.name, a.column_shift, a.strips, a.groups, a.frame_order) == (name, shift, strips, groups, order)
    assert parse_arrangement(name) is a and parse_arrangement(name.upper()) is a
    assert parse_arrangement(aid.lower()) is a
    # display strip i holds kit strip strips[i]
    for i, letter in enumerate(strips):
        assert a.to_kit(16 * i) == 16 * "ABCDEFGH".index(letter)


def test_d_and_e_centres_and_flags():
    d, e = parse_arrangement("D"), parse_arrangement("E")
    assert d.centre == "the Pacific (date line)" and e.centre == "Asia-Pacific (146° E)"
    assert not d.in_instructions and not e.in_instructions
    assert d.is_split and e.is_split
    assert d.order_text == "2b·3·1·2a"
    assert d.describe() == ("D (pacific, frames 2b·3·1·2a, the Pacific (date line) in the centre; "
                            "not in the building instructions)")


@pytest.mark.parametrize("aid,spans,bounds", [
    ("D", [("2b", 2, "EF", 0, 31), ("3", 3, "GH", 32, 63), ("1", 1, "AB", 64, 95), ("2a", 2, "CD", 96, 127)],
     (32, 64, 96)),
    ("E", [("2b", 2, "DEF", 0, 47), ("3", 3, "GH", 48, 79), ("1", 1, "AB", 80, 111), ("2a", 2, "C", 112, 127)],
     (48, 80, 112)),
    ("B", [("3", 3, "GH", 0, 31), ("1", 1, "AB", 32, 63), ("2", 2, "CDEF", 64, 127)], (32, 64))])
def test_group_spans(aid, spans, bounds):
    a = parse_arrangement(aid)
    assert [(g.label, g.frame.number, g.strips, g.start, g.end) for g in a.group_spans()] == spans
    assert a.boundaries() == bounds
    assert a.group_at(bounds[0]).label == spans[1][0]


@pytest.mark.parametrize("aid,make,unpeg", [
    ("A", ["B|C", "F|G"], []),
    ("B", ["H|A", "B|C"], []),
    ("C", ["F|G", "H|A"], []),
    ("D", ["F|G", "H|A", "B|C"], ["D|E"]),
    ("E", ["F|G", "H|A", "B|C"], ["C|D"])])
def test_joints(aid, make, unpeg):
    a = parse_arrangement(aid)
    joints = a.joints()
    assert len(joints) == 7
    assert [f"{j.left}|{j.right}" for j in joints if j.kind == "make"] == make
    assert [f"{l}|{r}" for l, r in a.unpeg()] == unpeg
    assert all(j.x == 16 * (i + 1) for i, j in enumerate(joints))


def test_d_record_and_source():
    r = parse_arrangement("D").record()
    assert r["id"] == "D" and r["name"] == "pacific" and r["column_shift"] == 64
    assert r["frame_order"] == [2, 3, 1, 2] and r["strips"] == "EFGHABCD"
    assert r["groups"] == ["2b", "3", "1", "2a"] and r["in_instructions"] is False
    assert r["source"]["pages"] == [134, 135, 136, 137, 138, 139, 140]
    assert r["source"]["sha256"] == SRC_78["sha256"]
    assert "134" in r["source"]["citation"] and "140" in r["source"]["citation"]


def test_joints_source_is_cited():
    data = load_arrangements()
    js = data.joints_source
    assert js["pages"] == [134, 135, 136, 137, 138, 139, 140]
    assert js["disclaimer"] == DISCLAIMER and js["sha256"] == data.source["sha256"]


def test_peg_budget_from_inventory():
    a = load_arrangements().assembly
    assert a.pegs_per_joint == 15 and a.pegs_used == 201 and a.pegs_supplied == 205


def test_assembly_steps_d():
    text = "\n".join(assembly_steps(parse_arrangement("D")))
    assert "Unpeg frame 2 between strips D and E" in text and "15 connector pegs" in text
    assert "E F G H A B C D" in text and "2b · 3 · 1 · 2a" in text
    assert "F|G, H|A and B|C" in text
    assert "pp. 140-153" in text
    note = assembly_note(parse_arrangement("D"))
    assert "not one of the three combinations" in note.lower() and "134" in note


def test_assembly_steps_e_and_a():
    assert "Unpeg frame 2 between strips C and D" in "\n".join(assembly_steps(parse_arrangement("E")))
    a = "\n".join(assembly_steps(parse_arrangement("A")))
    assert "Unpeg" not in a and "B|C and F|G" in a
    assert "pp. 7-8" in assembly_note(parse_arrangement("A"))


@pytest.mark.parametrize("src,dst", [("A", "D"), ("D", "E"), ("E", "B"), ("C", "D")])
def test_arrange_through_d_e(src, dst):
    from tests.unit.test_arrangement import _grid  # noqa: WPS433 - shared helper

    g = arrange_grid(_grid(), parse_arrangement(src))
    h = arrange_grid(g, parse_arrangement(dst))
    delta = parse_arrangement(dst).column_shift - parse_arrangement(src).column_shift
    for p in g.positions[:300]:
        assert h.get_position((p.x + delta) % 128, p.y).color_id == p.color_id
    back = arrange_grid(h, parse_arrangement(src))
    assert [q.to_dict() for q in back.positions] == [q.to_dict() for q in g.positions]


# --- loader validation ---------------------------------------------------------------------------

def _raw():
    return json.loads(arr.DATA_PATH.read_text(encoding="utf-8"))


def _load(tmp_path, raw):
    p = tmp_path / "arr.json"
    p.write_text(json.dumps(raw), encoding="utf-8")
    arr.load_arrangements.cache_clear()
    try:
        return arr.load_arrangements(str(p))
    finally:
        arr.load_arrangements.cache_clear()


def test_loader_accepts_shipped_copy(tmp_path):
    assert [a.id for a in _load(tmp_path, _raw()).arrangements] == ["A", "B", "C", "D", "E"]


@pytest.mark.parametrize("field,value,match", [
    ("strips", "EFGHABDC", "rotation"),
    ("column_shift", 48, "column_shift"),
    ("groups", ["2a", "3", "1", "2b"], "groups"),
    ("frame_order", [2, 3, 1], "frame order"),
])
def test_loader_rejects_bad_d(tmp_path, field, value, match):
    raw = _raw()
    d = next(a for a in raw["arrangements"] if a["id"] == "D")
    d[field] = value
    with pytest.raises(ArrangementError, match=match):
        _load(tmp_path, raw)


def test_loader_rejects_d_marked_official(tmp_path):
    raw = _raw()
    next(a for a in raw["arrangements"] if a["id"] == "D")["in_instructions"] = True
    with pytest.raises(ArrangementError, match="in_instructions"):
        _load(tmp_path, raw)


def test_loader_rejects_missing_joint_disclaimer(tmp_path):
    raw = copy.deepcopy(_raw())
    del raw["joints_source"]["disclaimer"]
    with pytest.raises(ArrangementError, match="disclaimer"):
        _load(tmp_path, raw)

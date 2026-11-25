"""Parts list (005 T013, T017, T029): layout input, lots, order, JSON, top-up arithmetic."""

import json
from fractions import Fraction

import pytest

from lego_image_processor.parts import (LayoutInputError, OwnedInputs, build_parts_list,
                                        parse_owned_csv, read_layout)
from lego_image_processor.parts.partslist import DISCLAIMER

from .layouts import LAND_ELEVATION, MISMATCH, SMALL, UNCITED, make_grid


def _lot(pl, part, key):
    return next(l for l in pl.lots if (l.part_id, l.color_key) == (part, key))


# --- layout input (T013) ------------------------------------------------------------------------

def test_read_layout_hashes_bytes_and_keeps_map_metadata(tmp_path):
    meta = {"recipe": {"id": "r", "format": "1", "title": "R", "sha256": "ab" * 32},
            "layers": [{"class": "land", "dataset": {"id": "d", "version": "1", "citation": "C",
                                                      "license": "L", "title": "x"}},
                       {"class": "ocean"}]}
    p = tmp_path / "l.json"
    p.write_text(make_grid(SMALL, source_image="recipe:r", map_metadata=meta).to_json(), encoding="utf-8")
    li = read_layout(p)
    import hashlib
    assert li.sha256 == hashlib.sha256(p.read_bytes()).hexdigest()
    pl = build_parts_list(li)
    assert pl.layout["map"] == {"recipe": {"id": "r", "format": "1", "sha256": "ab" * 32},
                                "datasets": [{"id": "d", "version": "1", "citation": "C", "license": "L"}]}
    assert pl.layout["sha256"] == li.sha256 and pl.layout["source_image"] == "recipe:r"


def test_read_layout_errors(tmp_path):
    with pytest.raises(LayoutInputError, match="cannot read"):
        read_layout(tmp_path / "absent.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(LayoutInputError, match="JSON"):
        read_layout(bad)
    d = json.loads(make_grid(SMALL).to_json())
    d["metadata"]["schema_version"] = "1.0"
    old = tmp_path / "old.json"
    old.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(LayoutInputError, match="schema"):
        read_layout(old)
    d = json.loads(make_grid(SMALL).to_json())
    d["positions"][0]["x"] = 128
    out = tmp_path / "out.json"
    out.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(LayoutInputError, match="outside"):
        read_layout(out)
    d = json.loads(make_grid(SMALL).to_json())
    d["positions"][1].update(x=d["positions"][0]["x"], y=d["positions"][0]["y"])
    dup = tmp_path / "dup.json"
    dup.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(LayoutInputError, match="twice"):
        read_layout(dup)


# --- lots, order, totals, JSON (T017) -----------------------------------------------------------

def test_lots_grouped_and_ordered():
    pl = build_parts_list(make_grid(UNCITED + MISMATCH[-1:]))
    order = [(l.part_id, l.color_key) for l in pl.lots]
    assert order == [("6141", "lego_white"), ("6141", "lego_brick_yellow"),
                     ("98138", "lego_bright_red"), ("98138", "lego_medium_azur"),
                     ("6141", "lego_black"), ("6141", "lego_medium_blue")]  # unverified last
    assert [l.needed for l in pl.lots] == [30, 12, 7, 20, 4, 5]
    assert _lot(pl, "6141", "lego_medium_blue").reason == "no cited color for part"
    assert _lot(pl, "6141", "lego_black").reason == "no cited color for part"  # LEGO ID 999
    t = pl.totals()
    assert t == {"lots": 6, "needed": 78, "owned": 0, "to_buy": 78, "lots_to_buy": 6, "spares": 0,
                 "surplus": 0, "verified_lots": 4, "unverified_lots": 2,
                 "leftover": 0}


def test_json_shape_and_determinism():
    pl = build_parts_list(make_grid(UNCITED), layout_path="x.json")
    a, b = pl.to_json(), build_parts_list(make_grid(UNCITED), layout_path="x.json").to_json()
    assert a == b
    d = json.loads(a)
    assert list(d) == ["format_version", "kit", "layout", "owned", "lots", "leftovers", "totals", "unverified",
                       "citations", "acknowledgement", "prices", "disclaimer"]
    assert d["disclaimer"] == DISCLAIMER and "Rebrickable" in d["acknowledgement"]
    assert d["layout"]["map"] is None
    v = d["lots"][0]
    assert list(v) == ["part_id", "part_type", "color_key", "verified", "lego", "bricklink",
                       "rebrickable", "rgb", "needed", "kit_supply", "loose", "owned", "shortfall",
                       "spares", "to_buy", "surplus"]
    assert v["bricklink"] == {"item_type": "P", "item_no": "4073", "color_name": "White", "color_id": 1}
    assert v["rebrickable"] == {"part_num": "6141", "color_name": "White", "color_id": 15}
    u = d["lots"][-1]
    assert u["verified"] is False and u["layout_color"] == {"name": "Medium Blue", "code": "102"}
    assert not {"lego", "bricklink", "rebrickable"} & set(u)
    assert d["owned"]["spares_percent"] == "0"
    ids = [c["id"] for c in d["citations"]]
    assert ids[0] == "kit-31203-instructions" and "rebrickable-terms" in ids
    assert {"bricklink-4073", "rebrickable-6141", "bricklink-98138", "rebrickable-98138"} <= set(ids)
    assert "generated_at" not in a and "2026-11-22T" not in a


# --- top-up arithmetic (T029) -------------------------------------------------------------------

def test_kits_and_shortfall():
    grid = make_grid(LAND_ELEVATION)
    pl = build_parts_list(grid, owned=OwnedInputs(kits=1))
    white, bbg = _lot(pl, "6141", "lego_white"), _lot(pl, "98138", "lego_bright_bluish_green")
    assert (white.kit_supply, white.shortfall, white.surplus) == (3064, 0, 2914)
    assert (bbg.kit_supply, bbg.shortfall, bbg.to_buy) == (1879, 3145, 3145)
    # Bright Green on the plate: the kit's 601 Bright Green pieces are tiles (research R11)
    assert _lot(pl, "6141", "lego_bright_green").kit_supply == 0
    assert pl.totals()["to_buy"] == 6382 and pl.totals()["lots_to_buy"] == 11


def test_owned_missing_and_spares(write_csv):
    grid = make_grid(LAND_ELEVATION)
    loose = parse_owned_csv(write_csv("loose.csv", "Part,Color,Quantity\n98138,3,1000\n"))
    missing = parse_owned_csv(write_csv("missing.csv", "Element,Quantity\n6322819,12\n"))
    pl = build_parts_list(grid, owned=OwnedInputs(kits=1, owned_files=(loose,), missing_files=(missing,),
                                                  spares_percent=Fraction(2)))
    bbg = _lot(pl, "98138", "lego_bright_bluish_green")
    assert (bbg.loose, bbg.owned, bbg.shortfall, bbg.spares, bbg.to_buy) == (1000, 2879, 2145, 43, 2188)
    azur = _lot(pl, "98138", "lego_medium_azur")
    assert (azur.kit_supply, azur.surplus, azur.spares) == (1607 - 12, 1595 - 1436, 0)
    assert _lot(pl, "6141", "lego_white").spares == 0  # no shortfall, no spares


def test_missing_never_below_zero(write_csv):
    missing = parse_owned_csv(write_csv("m.csv", "Part,Color,Quantity\n98138,322,5000\n6141,15,7\n"))
    pl = build_parts_list(make_grid(SMALL), owned=OwnedInputs(kits=0, missing_files=(missing,)))
    assert _lot(pl, "98138", "lego_medium_azur").kit_supply == 0
    pl = build_parts_list(make_grid(SMALL), owned=OwnedInputs(kits=2, missing_files=(missing,)))
    assert _lot(pl, "98138", "lego_medium_azur").kit_supply == 0
    assert _lot(pl, "6141", "lego_white").kit_supply == 2 * 3064 - 7


def test_spares_ceil_exact():
    grid = make_grid([("plate", "lego_brick_yellow", "Brick Yellow", "5", 2145)])
    for pct, expected in ((Fraction(2), 43), (Fraction(1, 10), 3), (Fraction(0), 0), (Fraction(100), 2145)):
        lot = build_parts_list(grid, owned=OwnedInputs(spares_percent=pct)).lots[0]
        assert lot.spares == expected


# --- square tiles on a template layout (feature 016 T061; FR-014, SC-003, US1-6) ----------------

def _winkel(template, **kw):
    from ...winkel_layouts import winkel_grid
    return winkel_grid(template, **kw)


def test_every_part_type_has_a_sheet_label():
    from lego_image_processor.parts.partslist import PART_ORDER, PART_TYPE
    from lego_image_processor.sheets.legend import PART_LABEL
    # feature 017 appends the in-margin plaque's tile 10202 (test_plaque_tile_part_order_type_and_labels)
    assert list(PART_ORDER)[:3] == ["6141", "98138", "3070b"] == list(PART_TYPE)[:3]
    assert PART_TYPE["3070b"] == "square_tile"
    assert set(PART_TYPE.values()) <= set(PART_LABEL)
    assert PART_LABEL["square_tile"] == "tile 1x1 square"


def test_square_tile_lots_follow_plates_and_tiles_with_cited_ids(confirmed_winkel):
    from lego_image_processor.kit.part_colors import load_part_colors
    from lego_image_processor.kit.part_numbers import load_part_numbers
    pl = build_parts_list(_winkel(confirmed_winkel))
    parts = [l.part_id for l in pl.lots]
    assert parts == ["6141", "98138", "98138", "3070b"]
    lot = pl.lots[-1]
    assert (lot.part_type, lot.color_key, lot.verified) == ("square_tile", "lego_black", True)
    assert lot.needed == confirmed_winkel.counts["margin"]
    pn, row = load_part_numbers().get("3070b"), load_part_colors().get("3070b", "lego_black")
    d = lot.to_dict()
    assert d["lego"] == {"name": row.lego.name, "id": row.lego.id, "element_id": row.element_id}
    # BrickLink files the square tile as item 3070 (part_numbers.json), Rebrickable as 3070b
    assert d["bricklink"] == {"item_type": "P", "item_no": pn.bricklink_item_no,
                              "color_name": row.bricklink.name, "color_id": row.bricklink.id}
    assert d["rebrickable"] == {"part_num": pn.rebrickable_part_num, "color_name": row.rebrickable.name,
                                "color_id": row.rebrickable.id}
    assert pn.rebrickable_part_num == "3070b"
    ids = {c["id"] for c in pl.citations}
    assert {p.id for p in pn.citations.values()} <= ids
    assert {c.id for c in row.citations.values()} <= ids


def test_ring_is_a_second_square_tile_lot(confirmed_winkel):
    from ...winkel_layouts import BRIGHT_YELLOW
    pl = build_parts_list(_winkel(confirmed_winkel, ring=BRIGHT_YELLOW))
    sq = [(l.color_key, l.needed) for l in pl.lots if l.part_id == "3070b"]
    c = confirmed_winkel.counts
    # by LEGO color ID: Bright Yellow (24) before Black (26)
    assert sq == [("lego_bright_yellow", c["ring"]), ("lego_black", c["margin"] - c["ring"])]


def test_square_tiles_total_and_one_kit_buys_them_all(confirmed_winkel):
    grid = _winkel(confirmed_winkel)
    full = build_parts_list(grid)
    assert full.totals()["needed"] == 10240 == sum(l.needed for l in full.lots)
    one = build_parts_list(grid, owned=OwnedInputs(kits=1))
    sq = _lot(one, "3070b", "lego_black")
    assert (sq.kit_supply, sq.owned, sq.to_buy) == (0, 0, confirmed_winkel.counts["margin"])
    from lego_image_processor.kit.inventory import load_kit_inventory
    assert load_kit_inventory().supplied_for("3070b", "lego_black") == 0


def test_leftovers_are_kit_elements_only_and_layout_names_the_template(confirmed_winkel, small_grid):
    pl = build_parts_list(_winkel(confirmed_winkel), owned=OwnedInputs(kits=1))
    assert len(pl.leftovers) == 10 and {l.part_id for l in pl.leftovers} == {"6141", "98138"}
    assert pl.layout["template"] == {"id": "winkel-tripel", "title": confirmed_winkel.title}
    d = json.loads(pl.to_json())
    assert list(d["layout"])[-1] == "template" and d["layout"]["template"]["id"] == "winkel-tripel"
    assert "3070b" not in {r["part_id"] for r in d["leftovers"]}
    assert "template" not in build_parts_list(small_grid).layout          # kit layouts unchanged


def test_owned_parts_of_a_layout(confirmed_winkel, small_grid):
    """Owned and missing CSVs are read for the layout's map parts (feature 016 T110): the kit's
    two on a kit layout, plus the square tile 3070b on a layout with square tiles."""
    from lego_image_processor.parts import owned_parts
    assert owned_parts(small_grid) == ("6141", "98138")
    assert owned_parts(make_grid([("plate", "lego_white", "White", "1", 3)])) == ("6141", "98138")
    assert owned_parts(_winkel(confirmed_winkel)) == ("6141", "98138", "3070b")


def test_loose_square_tiles_count_on_a_template_layout(confirmed_winkel, write_csv):
    from lego_image_processor.parts import owned_parts, parse_owned_csv
    grid = _winkel(confirmed_winkel)
    csv = write_csv("w.csv", "Part,Color,Quantity\n3070b,0,40\n3001,15,4\n")
    owned = parse_owned_csv(csv, parts=owned_parts(grid))
    missing = parse_owned_csv(write_csv("m.csv", "Part,Color,Quantity\n3070b,0,5\n"), parts=owned_parts(grid))
    pl = build_parts_list(grid, owned=OwnedInputs(kits=1, owned_files=(owned,), missing_files=(missing,)))
    sq = _lot(pl, "3070b", "lego_black")
    n = confirmed_winkel.counts["margin"]
    # no kit supplies square tiles, so missing ones subtract nothing (supply never below 0)
    assert (sq.kit_supply, sq.loose, sq.owned, sq.to_buy) == (0, 40, 40, n - 40)
    assert pl.owned.ignored_rows == 1


# --- the in-margin plaque tile (feature 017 T069; FR-024, SC-009; contracts/in-margin-plaque.md) -
# The plaque's 36 studs carry no position: its tile is one lot read from ``metadata.plaque``, with
# every ID from plaque_parts.json (never from the part number: a BrickLink item can differ from the
# part ID, as 6141 is item 4073 and 3070b is item 3070).

def _plaque_tile():
    from lego_image_processor.kit.plaque_parts import load_plaque_parts
    return load_plaque_parts().plaques["small"].tile


def _plaque_record(template, corner="bottom-left"):
    from lego_image_processor.maps.margin import place_plaque
    return place_plaque(template, corner).layout_record()


def _plaque_grid(template, corner="bottom-left", **kw):
    return _winkel(template, plaque=_plaque_record(template, corner), **kw)


def test_plaque_tile_part_order_type_and_labels():
    from lego_image_processor.parts.partslist import PART_ORDER, PART_TYPE, PART_TYPE_TEXT
    from lego_image_processor.sheets.legend import PART_LABEL
    tile = _plaque_tile()
    assert list(PART_ORDER) == ["6141", "98138", "3070b", tile.part_id] == list(PART_TYPE)
    assert PART_TYPE[tile.part_id] == "plaque_tile"
    w, h = tile.studs
    assert PART_LABEL["plaque_tile"] == f"tile {w}x{h}" == "tile 6x6" == PART_TYPE_TEXT["plaque_tile"]


def test_plaque_lot_has_the_cited_ids(confirmed_winkel):
    pl = build_parts_list(_plaque_grid(confirmed_winkel))
    tile = _plaque_tile()
    assert [l.part_id for l in pl.lots] == ["6141", "98138", "98138", "3070b", tile.part_id]
    lot = pl.lots[-1]
    assert (lot.part_type, lot.color_key, lot.verified, lot.needed) == ("plaque_tile", tile.color.key, True, 1)
    d = lot.to_dict()
    assert d["lego"] == {"name": tile.color.lego.name, "id": tile.color.lego.id,
                         "element_id": tile.color.element_id}
    assert d["bricklink"] == {"item_type": "P", "item_no": tile.numbers.bricklink_item_no,
                              "color_name": tile.color.bricklink.name, "color_id": tile.color.bricklink.id}
    assert d["rebrickable"] == {"part_num": tile.numbers.rebrickable_part_num,
                                "color_name": tile.color.rebrickable.name,
                                "color_id": tile.color.rebrickable.id}
    assert d["rgb"] == list(tile.color.rgb)
    assert lot.ids.part.lego_design_ids == tile.numbers.lego_design_ids
    # Black: BrickLink 11, Rebrickable 0 (as plaque_parts.json cites them)
    assert (tile.color.bricklink.id, tile.color.rebrickable.id) == (11, 0)
    assert (d["bricklink"]["color_id"], d["rebrickable"]["color_id"]) == (11, 0)


def test_plaque_citations_resolve_from_plaque_parts(confirmed_winkel):
    from lego_image_processor.kit.part_colors import load_part_colors
    from lego_image_processor.kit.part_numbers import load_part_numbers
    from lego_image_processor.kit.plaque_parts import load_plaque_parts
    pl = build_parts_list(_plaque_grid(confirmed_winkel))
    lot = pl.lots[-1]
    by_id = {c["id"]: c for c in pl.citations}
    cids = lot.ids.citation_ids
    assert set(cids) <= set(by_id)                                   # none is dropped
    assert {"bricklink-10202", "rebrickable-elements"} <= set(cids)  # the contract's examples
    shared = {p.id for p in load_part_numbers().pages} | {c.id for c in load_part_colors().citations}
    snaps = {p.id: p for p in load_plaque_parts().snapshots}
    own = [c for c in cids if c not in shared]
    assert "bricklink-10202" in own
    for cid in own:                                                  # resolved from source.snapshots
        assert by_id[cid] == snaps[cid].to_dict()
    assert len(by_id) == len(pl.citations)                           # each once


def test_plaque_replaces_36_square_tiles_and_nothing_else(confirmed_winkel):
    plain = build_parts_list(_winkel(confirmed_winkel), owned=OwnedInputs(kits=1))
    plaque = build_parts_list(_plaque_grid(confirmed_winkel), owned=OwnedInputs(kits=1))
    a = {(l.part_id, l.color_key): l.needed for l in plain.lots}
    b = {(l.part_id, l.color_key): l.needed for l in plaque.lots}
    tile = _plaque_tile()
    cells = tile.studs[0] * tile.studs[1]
    assert b.pop((tile.part_id, tile.color.key)) == 1
    assert b[("3070b", "lego_black")] == a[("3070b", "lego_black")] - cells == confirmed_winkel.counts["margin"] - 36
    assert {k: v for k, v in b.items() if k[0] != "3070b"} == {k: v for k, v in a.items() if k[0] != "3070b"}
    one_stud = sum(l.needed for l in plaque.lots if l.part_type != "plaque_tile")
    assert one_stud == 10204 and plaque.totals()["needed"] == 10205            # SC-009
    assert [l.to_dict() for l in plaque.leftovers] == [l.to_dict() for l in plain.leftovers]
    assert plaque.totals()["leftover"] == plain.totals()["leftover"]


def test_one_kit_buys_the_plaque_tile(confirmed_winkel):
    from lego_image_processor.kit.inventory import load_kit_inventory
    tile = _plaque_tile()
    assert load_kit_inventory().supplied_for(tile.part_id, tile.color.key) == 0
    for kits in (1, 3):
        lot = build_parts_list(_plaque_grid(confirmed_winkel), owned=OwnedInputs(kits=kits)).lots[-1]
        assert (lot.kit_supply, lot.owned, lot.shortfall, lot.to_buy) == (0, 0, 1, 1)


def test_parts_list_json_with_a_plaque(confirmed_winkel):
    pl = build_parts_list(_plaque_grid(confirmed_winkel), layout_path="p.json")
    d = json.loads(pl.to_json())
    row = d["lots"][-1]
    assert (row["part_id"], row["part_type"], row["needed"], row["kit_supply"]) == \
        (_plaque_tile().part_id, "plaque_tile", 1, 0)
    assert list(row) == list(d["lots"][0])
    assert d["totals"]["lots"] == len(d["lots"]) and d["totals"]["unverified_lots"] == 0
    assert d["layout"]["positions"] == 10240                 # the board; 36 of its studs are the plaque
    assert pl.to_json() == build_parts_list(_plaque_grid(confirmed_winkel), layout_path="p.json").to_json()


def test_layouts_without_a_plaque_have_no_plaque_lot(confirmed_winkel, small_grid):
    for grid in (small_grid, _winkel(confirmed_winkel)):
        assert "plaque_tile" not in {l.part_type for l in build_parts_list(grid).lots}


def test_plaque_record_must_name_the_plaque_tile(confirmed_winkel):
    rec = dict(_plaque_record(confirmed_winkel), part_id="3958")     # the plaque plate, not a tile
    with pytest.raises(LayoutInputError, match="metadata.plaque"):
        build_parts_list(_winkel(confirmed_winkel, plaque=rec))


def test_plaque_in_an_uncited_color_is_unverified(confirmed_winkel):
    from lego_image_processor.parts.resolve import REASON_NO_COLOR
    rec = dict(_plaque_record(confirmed_winkel), color="lego_white")
    pl = build_parts_list(_winkel(confirmed_winkel, plaque=rec))
    lot = pl.lots[-1]
    assert (lot.part_type, lot.verified, lot.reason, lot.needed) == ("plaque_tile", False, REASON_NO_COLOR, 1)


def test_owned_csv_reads_the_plaque_tile_only_on_a_plaque_layout(confirmed_winkel, write_csv):
    from lego_image_processor.parts import owned_parts
    tile = _plaque_tile()
    grid = _plaque_grid(confirmed_winkel)
    assert owned_parts(grid) == ("6141", "98138", "3070b", tile.part_id)
    assert owned_parts(_winkel(confirmed_winkel)) == ("6141", "98138", "3070b")
    text = f"Part,Color,Quantity\n{tile.numbers.rebrickable_part_num},{tile.color.rebrickable.id},1\n"
    owned = parse_owned_csv(write_csv("o.csv", text), parts=owned_parts(grid))
    assert owned.quantities == {(tile.part_id, tile.color.key): 1} and owned.ignored_rows == 0
    lot = build_parts_list(grid, owned=OwnedInputs(kits=1, owned_files=(owned,))).lots[-1]
    assert (lot.loose, lot.owned, lot.to_buy, lot.surplus) == (1, 1, 0, 0)
    by_element = parse_owned_csv(write_csv("e.csv", f"Element,Quantity\n{tile.color.element_id},2\n"),
                                 parts=owned_parts(grid))
    assert by_element.quantities == {(tile.part_id, tile.color.key): 2}
    # a layout without the plaque ignores (and counts) the row, as a kit layout does 3070b's
    plain = parse_owned_csv(write_csv("p.csv", text), parts=owned_parts(_winkel(confirmed_winkel)))
    assert plain.quantities == {} and plain.ignored_rows == 1
    from lego_image_processor.parts import OwnedFileError
    with pytest.raises(OwnedFileError, match=f"part {tile.part_id} in Rebrickable color 15 has no cited row"):
        parse_owned_csv(write_csv("w.csv", f"Part,Color,Quantity\n{tile.part_id},15,1\n"),
                        parts=owned_parts(grid))

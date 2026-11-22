"""Part-color maintainer tool (T049, Q4): joins only fully cited rows, from synthetic snapshots."""

import gzip
import hashlib
import json

import pytest

from lego_image_processor.kit.colors import KIT_COLORS_PATH
from lego_image_processor.kit.part_colors import PART_COLORS_PATH, parse_part_colors
from partcolors.build import (SnapshotError, build, color_key, differences, parse_bricklink,
                              parse_ldconfig, read_snapshots)

KIT = json.loads(KIT_COLORS_PATH.read_text(encoding="utf-8"))

ELEMENTS = "element_id,part_num,color_id,design_id\n" + "\n".join(
    [f"{c['element_id']},{'6141' if c['role'] == 'land' else '98138'},{c['rebrickable']['id']},"
     f"{'6141' if c['role'] == 'land' else '35381'}" for c in KIT["colors"]]
    + ["614128,6141,2,6141", "4218588,6141,2,6141", "9000001,6141,2,", "6258990,6141,326,6141",
       "4211525,6141,71,6141", "7000000,6141,41,6141", "3005741,6141,36,30057"])
COLORS = "id,name,rgb,is_trans,num_parts,num_sets,y1,y2\n" + "\n".join(
    [f"{c['rebrickable']['id']},{c['rebrickable']['name']},{''.join(f'{v:02X}' for v in c['rgb'])},False,1,1,2000,2020"
     for c in KIT["colors"]]
    + ["2,Green,237841,False,1,1,1960,2027", "326,Olive Green,9B9A5A,False,1,1,2015,2027",
       "71,Light Bluish Gray,A0A5A9,False,1,1,2003,2027", "41,Trans-Red,C91A09,True,1,1,1960,2027",
       "36,Trans-Green,84B68D,True,1,1,1960,2027"])
LDCONFIG = """0 // LEGOID  28 - Dark Green
0 !COLOUR Green CODE 2 VALUE #237841 EDGE #333333
0 // LEGOID 326 - Spring Yellowish Green
0 !COLOUR Yellowish_Green CODE 326 VALUE #DFEEA5 EDGE #333333
0 // LEGOID 194 - Medium Stone Grey
0 !COLOUR Light_Bluish_Grey CODE 71 VALUE #A0A5A9 EDGE #333333
"""
BL_ROW = ('<TR><TD  ALIGN="RIGHT"><FONT FACE="Tahoma,Arial" SIZE="2">{id}&nbsp;</TD><TD BGCOLOR="000000">'
          '<A HREF="x"></A></TD><TD></TD><TD width="180px"><FONT FACE="Tahoma,Arial" SIZE="2">{name}&nbsp;</TD></TR>')
BRICKLINK = "".join(BL_ROW.format(id=i, name=n) for i, n in ((6, "Green"), (86, "Light Bluish Gray"),
                                                           (155, "Olive Green")))


def _snap():
    return {"rebrickable-elements": ELEMENTS.encode(), "rebrickable-colors": COLORS.encode(),
            "ldraw": LDCONFIG.encode(), "bricklink": BRICKLINK.encode("latin-1")}


def test_parsers():
    ld = parse_ldconfig(LDCONFIG)
    assert ld[2] == {"name": "Green", "lego": (28, "Dark Green")}
    assert parse_bricklink(BRICKLINK) == {"Green": 6, "Light Bluish Gray": 86, "Olive Green": 155}
    assert color_key("Medium Stone Grey") == "lego_medium_stone_grey"


def test_build_keeps_only_fully_cited_rows():
    reviewed = {"6141": (2, 326, 71, 41, 999), "98138": ()}
    r = build(_snap(), KIT, "2026-11-22", reviewed=reviewed)
    plate = {row["key"]: row for row in r.data["parts"]["6141"]}
    assert set(plate) == {"lego_white", "lego_dark_green", "lego_medium_stone_grey"}
    g = plate["lego_dark_green"]
    assert g["lego"] == {"name": "Dark Green", "id": 28}
    assert g["bricklink"] == {"name": "Green", "id": 6}
    assert g["rebrickable"] == {"name": "Green", "id": 2}
    assert g["element_id"] == "614128" and g["element_ids"] == ["614128", "4218588", "9000001"]
    assert g["rgb"] == [35, 120, 65] and g["in_kit"] is False
    reasons = {e["rebrickable_id"]: e["reason"] for e in r.excluded}
    assert set(reasons) == {326, 41, 999}
    assert "LDraw" in reasons[326] and "transparent" in reasons[41]
    assert r.kit_notes == []
    parse_part_colors(r.data)  # the package's rules accept the output


def test_kit_rows_equal_kit_table():
    r = build(_snap(), KIT, "2026-11-22", reviewed={"6141": (), "98138": ()})
    tiles = r.data["parts"]["98138"]
    assert len(tiles) == 9 and all(t["in_kit"] for t in tiles)
    kit = {c["key"]: c for c in KIT["colors"]}
    for t in tiles:
        for f in ("element_id", "lego", "bricklink", "rebrickable", "rgb"):
            assert t[f] == kit[t["key"]][f]


def test_kit_disagreement_is_reported():
    snap = _snap()
    snap["rebrickable-colors"] = snap["rebrickable-colors"].replace(b"FFFFFF", b"F4F4F4")
    r = build(snap, KIT, "2026-11-22", reviewed={"6141": (), "98138": ()})
    assert any("lego_white" in n for n in r.kit_notes)


def test_check_reports_no_differences_on_unchanged_build():
    r1 = build(_snap(), KIT, "2026-11-22")
    r2 = build(_snap(), KIT, "2026-11-23")
    assert differences(r1.data, r2.data) == []
    changed = json.loads(json.dumps(r2.data))
    changed["parts"]["6141"].pop()
    assert differences(r1.data, changed)


def test_snapshot_checksums(tmp_path):
    raw = gzip.compress(b"id,name\n")
    (tmp_path / "x.csv.gz").write_bytes(raw)
    spec = [{"id": "x", "file": "x.csv.gz", "url": "u", "sha256": hashlib.sha256(raw).hexdigest()}]
    assert read_snapshots(tmp_path, spec)["x"] == b"id,name\n"
    spec[0]["sha256"] = "0" * 64
    with pytest.raises(SnapshotError, match="checksum"):
        read_snapshots(tmp_path, spec)
    with pytest.raises(SnapshotError, match="missing"):
        read_snapshots(tmp_path / "nope", spec)


def test_committed_table_lists_part_number_finding():
    data = json.loads(PART_COLORS_PATH.read_text(encoding="utf-8"))
    assert "4073" in data["source"]["part_numbers"]["6141"]
    assert len(data["source"]["snapshots"]) == 4
    assert all(len(s["sha256"]) == 64 for s in data["source"]["snapshots"])

"""Part-number maintainer tool (005 T003; 016 T012): parsers and build on trimmed synthetic page
snippets.

The snippets imitate the structure of the archived BrickLink and Rebrickable part pages; they are
not copies of them (FR-019). Feature 016 adds the 1x1 square tile 3070b, which is not in the kit:
BrickLink files it as item 3070 with 3070b as an alternate, and its LEGO design IDs are the ones
Rebrickable lists (research R10).
"""

import hashlib
import json

import pytest
from click.testing import CliRunner

from lego_image_processor.kit.inventory import INVENTORY_PATH
from partnumbers.build import (PAGES, BuildError, SourceError, build, differences,
                               parse_bricklink_part, parse_rebrickable_part, read_pages)

INVENTORY = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def _bl(title, item, alternates, colors):
    items = "".join(
        f'<div class="pciSelectColorColorItem" data-tab="{tab}"  data-color="{cid}" data-name="{name}" '
        f'data-rgb="#000000"><span>&nbsp;</span>&nbsp;{name}{" (12)" if tab != "All" else ""}</div>'
        for tab in ("All", "Known") for cid, name in colors)
    return (f"<html><head><title>{title} | BrickLink</title></head><body>"
            f'<span style="x">Item No: <span style="font-weight: bold">{item}</span>&nbsp;&nbsp;'
            f'Alternate Item No: <span style="color: #2C6EA5">{alternates}</span></span>'
            f'<div id="_idColorListAll"><div class="pciSelectColorColorItem" data-color="-99" '
            f'data-name="">All Colors</div>{items}</div></body></html>')


def _rb(title, sites):
    rows = "".join(f"<tr><td>{site}</td><td>" + "".join(f'<a href="x">\n  {i}\n</a>' for i in ids)
                   + "</td></tr>" for site, ids in sites)
    return (f"<html><head><title>{title} | Rebrickable - Build with LEGO</title></head><body>"
            f'<h4 class="text-center">External Sites</h4><table class="table">'
            f"<p>This part is known differently at other sites:</p>{rows}</table>"
            f"<table><tr><td>LEGO</td><td>999</td></tr></table></body></html>")


BL_PLATE = _bl("Plate, Round 1 x 1 : Part 4073", "4073", "6141, 15570, 30057",
               [(0, "(Not Applicable)"), (11, "Black"), (1, "White"), (17, "Trans-Red")])
BL_TILE = _bl("Tile, Round 1 x 1 : Part 98138", "98138", "35380, 35381",
              [(0, "(Not Applicable)"), (39, "Dark Turquoise"), (1, "White")])
RB_PLATE = _rb("LEGO PART 6141 Plate Round 1 x 1 with Solid Stud",
               [("LEGO", ["30057", "6141"]), ("BrickLink", ["4073"]), ("LDraw", ["6141", "4073"])])
RB_TILE = _rb("LEGO PART 98138 Tile Round 1 x 1",
              [("LEGO", ["98138", "35380", "35381"]), ("BrickLink", ["98138"])])
BL_SQUARE = _bl("Tile 1 x 1 : Part 3070", "3070", "3070b, 30039, 35403",
                [(0, "(Not Applicable)"), (11, "Black"), (1, "White")])
RB_SQUARE = _rb("LEGO PART 3070b Tile 1 x 1 with Groove",
                [("LEGO", ["3070", "30039", "35403"]), ("BrickLink", ["3070"]), ("LDraw", ["3070b"])])


def _texts(**override):
    t = {"bricklink-4073": BL_PLATE, "bricklink-98138": BL_TILE,
         "rebrickable-6141": RB_PLATE, "rebrickable-98138": RB_TILE,
         "bricklink-3070": BL_SQUARE, "rebrickable-3070b": RB_SQUARE}
    t.update(override)
    return t


def test_parse_bricklink_part():
    p = parse_bricklink_part(BL_PLATE)
    assert p["name"] == "Plate, Round 1 x 1"
    assert p["item_no"] == "4073"
    assert p["alternates"] == ["6141", "15570", "30057"]
    # the "All" tab only, without "(Not Applicable)" and without the counted "Known" tab
    assert p["colors"] == [(11, "Black"), (1, "White"), (17, "Trans-Red")]


def test_parse_rebrickable_part():
    p = parse_rebrickable_part(RB_PLATE)
    assert p["part_num"] == "6141"
    assert p["name"] == "Plate Round 1 x 1 with Solid Stud"
    assert p["external"] == {"LEGO": ["30057", "6141"], "BrickLink": ["4073"], "LDraw": ["6141", "4073"]}


def test_build_part_numbers():
    data = build(_texts(), INVENTORY, "2026-11-22")
    plate, tile = data["parts"]["6141"], data["parts"]["98138"]
    assert plate["bricklink"]["item_no"] == "4073" and plate["rebrickable"]["part_num"] == "6141"
    assert plate["bricklink"]["alternates"][0] == "6141"
    assert plate["bricklink"]["colors"] == ["Black", "White", "Trans-Red"]
    assert plate["lego_design_ids"] == ["6141"]
    assert tile["lego_design_ids"] == ["98138", "35381"]  # part number, then the kit elements' design
    assert tile["bricklink"]["item_no"] == "98138" and tile["rebrickable"]["part_num"] == "98138"
    assert [p["id"] for p in data["source"]["pages"]] == [p["id"] for p in PAGES]
    assert data["source"]["disclaimer"] == "Not affiliated with or endorsed by The LEGO Group."


def test_square_tile_not_in_kit():
    """016 R10: 3070b keeps rules 1-3; the kit-inventory rules are replaced for a non-kit part."""
    data = build(_texts(), INVENTORY, "2026-11-23")
    assert list(data["parts"]) == ["6141", "98138", "3070b"]
    sq = data["parts"]["3070b"]
    assert sq["name"] == "Tile 1 x 1"
    assert sq["bricklink"] == {"item_type": "P", "item_no": "3070", "alternates": ["3070b", "30039", "35403"],
                               "colors": ["Black", "White"], "citation": "bricklink-3070"}
    assert sq["rebrickable"] == {"part_num": "3070b", "name": "Tile 1 x 1 with Groove",
                                 "citation": "rebrickable-3070b"}
    # LEGO design IDs are the ones Rebrickable lists (3070b is LEGO design 3070)
    assert sq["lego_design_ids"] == ["3070", "30039", "35403"]
    # the kit parts are built exactly as without the square tile
    kit_only = build(_texts(), INVENTORY, "2026-11-23", pages=[p for p in PAGES if p["part"] != "3070b"])
    assert {k: data["parts"][k] for k in ("6141", "98138")} == kit_only["parts"]
    assert [p["id"] for p in data["source"]["pages"]][-2:] == ["bricklink-3070", "rebrickable-3070b"]
    assert any("3070b" in r for r in data["source"]["rules"])


def test_square_tile_rules():
    # the project ID must be the BrickLink item number or one of its alternates
    bad_bl = _bl("Tile 1 x 1 : Part 3070", "3070", "30039", [(11, "Black")])
    with pytest.raises(BuildError, match="alternate"):
        build(_texts(**{"bricklink-3070": bad_bl}), INVENTORY, "2026-11-23")
    # Rebrickable's BrickLink cross-reference must name the BrickLink item number
    bad_rb = _rb("LEGO PART 3070b Tile 1 x 1 with Groove", [("LEGO", ["3070"]), ("BrickLink", ["3070b"])])
    with pytest.raises(BuildError, match="BrickLink"):
        build(_texts(**{"rebrickable-3070b": bad_rb}), INVENTORY, "2026-11-23")
    # Rebrickable must list at least one LEGO design ID
    no_lego = _rb("LEGO PART 3070b Tile 1 x 1 with Groove", [("BrickLink", ["3070"])])
    with pytest.raises(BuildError, match="LEGO"):
        build(_texts(**{"rebrickable-3070b": no_lego}), INVENTORY, "2026-11-23")
    # Rebrickable's part number must be the project ID
    other = _rb("LEGO PART 3070a Tile 1 x 1 without Groove", [("LEGO", ["3070"]), ("BrickLink", ["3070"])])
    with pytest.raises(BuildError, match="3070a"):
        build(_texts(**{"rebrickable-3070b": other}), INVENTORY, "2026-11-23")


def test_pinned_square_tile_pages():
    by_id = {p["id"]: p for p in PAGES}
    for pid, url in (("bricklink-3070", "https://www.bricklink.com/v2/catalog/catalogitem.page?P=3070"),
                     ("rebrickable-3070b", "https://rebrickable.com/parts/3070b/")):
        p = by_id[pid]
        assert p["part"] == "3070b" and len(p["sha256"]) == 64
        assert p["url"].startswith("http://web.archive.org/web/") and p["url"].endswith("id_/" + url)


def test_build_rejects_inconsistent_pages():
    # Rebrickable's BrickLink cross-reference must name the BrickLink item number
    bad = _rb("LEGO PART 6141 Plate Round 1 x 1 with Solid Stud", [("LEGO", ["6141"]), ("BrickLink", ["6141"])])
    with pytest.raises(BuildError, match="BrickLink"):
        build(_texts(**{"rebrickable-6141": bad}), INVENTORY, "2026-11-22")
    # the project part number must be the BrickLink item number or one of its alternates
    bad_bl = _bl("Plate, Round 1 x 1 : Part 4073", "4073", "15570", [(1, "White")])
    with pytest.raises(BuildError, match="alternate"):
        build(_texts(**{"bricklink-4073": bad_bl}), INVENTORY, "2026-11-22")
    # a design ID from the kit inventory must be listed by Rebrickable under LEGO
    bad_tile = _rb("LEGO PART 98138 Tile Round 1 x 1", [("LEGO", ["98138"]), ("BrickLink", ["98138"])])
    with pytest.raises(BuildError, match="35381"):
        build(_texts(**{"rebrickable-98138": bad_tile}), INVENTORY, "2026-11-22")


def test_differences_ignore_generation_date():
    a = build(_texts(), INVENTORY, "2026-11-22")
    b = build(_texts(), INVENTORY, "2026-11-23")
    assert differences(a, b) == []
    b["parts"]["6141"]["bricklink"]["item_no"] = "6141"
    assert differences(a, b)


def test_read_pages_checks_sha256(tmp_path):
    body = b"<html>x</html>"
    (tmp_path / "p.html").write_bytes(body)
    spec = [{"id": "p", "file": "p.html", "url": "u", "sha256": hashlib.sha256(body).hexdigest()}]
    assert read_pages(tmp_path, spec) == {"p": "<html>x</html>"}
    spec[0]["sha256"] = "0" * 64
    with pytest.raises(SourceError, match="checksum"):
        read_pages(tmp_path, spec)
    with pytest.raises(SourceError, match="missing"):
        read_pages(tmp_path / "nope", spec)


def test_check_exit_codes(tmp_path, monkeypatch):
    """--check: 0 "no differences", 1 differences, 4 page missing (unchanged by 016)."""
    from partnumbers import __main__ as cli_mod
    from partnumbers.build import to_text

    out = tmp_path / "part_numbers.json"
    out.write_text(to_text(build(_texts(), INVENTORY, "2026-11-23")), encoding="utf-8")
    monkeypatch.setattr(cli_mod, "read_pages", lambda source_dir: _texts())
    args = ["build", "--check", "--no-download", "--source-dir", str(tmp_path), "--output", str(out)]
    ok = CliRunner().invoke(cli_mod.main, args)
    assert ok.exit_code == 0, ok.output
    assert "no differences" in ok.output and "part 3070b: BrickLink P 3070" in ok.output
    changed = json.loads(out.read_text(encoding="utf-8"))
    changed["parts"]["3070b"]["bricklink"]["item_no"] = "3070b"
    out.write_text(to_text(changed), encoding="utf-8")
    assert CliRunner().invoke(cli_mod.main, args).exit_code == 1
    monkeypatch.undo()
    missing = CliRunner().invoke(cli_mod.main, args)
    assert missing.exit_code == 4 and "missing" in missing.output

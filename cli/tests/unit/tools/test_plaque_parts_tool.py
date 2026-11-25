"""Plaque part maintainer tool (feature 017 T013): ``tools/partcolors/plaque.py`` and the
``plaque-parts [--snapshots DIR] [--check]`` command, on the synthetic fixtures in
tests/fixtures/plaque/ (no copy of a catalog page is committed) and small inline snapshots.

Not affiliated with or endorsed by The LEGO Group.
"""

import gzip
import hashlib
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

import partcolors.__main__ as pc_main
from lego_image_processor.kit.inventory import INVENTORY_PATH
from lego_image_processor.kit.part_colors import PART_COLORS_PATH
from lego_image_processor.kit.plaque_parts import load_plaque_parts, parse_plaque_parts
from lego_image_processor.kit.source import DISCLAIMER
from partcolors import plaque
from partcolors.build import TERMS_TEXT, SnapshotError
from partnumbers.build import BuildError

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "plaque"
PARTS = ("10202", "3958", "4974", "92438")
INVENTORY = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
PART_COLORS = json.loads(PART_COLORS_PATH.read_text(encoding="utf-8"))
BLACK = plaque.black_row(PART_COLORS)

ELEMENTS = (FIXTURES / "elements.csv").read_text(encoding="utf-8")
COLORS = ("id,name,rgb,is_trans,num_parts,num_sets,y1,y2\n"
          "-1,[Unknown],0033B2,False,1,1,2000,2000\n"
          "0,Black,05131D,False,1,1,1957,2027\n"
          "1,Blue,0055BF,False,1,1,1950,2027\n")
LDCONFIG = ("0 // LEGOID  26 - Black\n"
            "0 !COLOUR Black CODE 0 VALUE #1B2A34 EDGE #808080\n"
            "0 // LEGOID  23 - Bright Blue\n"
            "0 !COLOUR Blue CODE 1 VALUE #1E5AA8 EDGE #333333\n")
BL_ROW = ('<TR><TD  ALIGN="RIGHT"><FONT FACE="Tahoma,Arial" SIZE="2">{id}&nbsp;</TD><TD BGCOLOR="000000">'
          '<A HREF="x"></A></TD><TD></TD><TD width="180px"><FONT FACE="Tahoma,Arial" SIZE="2">{name}&nbsp;</TD></TR>')
BRICKLINK = "".join(BL_ROW.format(id=i, name=n) for i, n in ((11, "Black"), (7, "Blue")))
TERMS = f"<p>Synthetic terms page for tests. {TERMS_TEXT}</p>"


def _snap(**override):
    s = {"rebrickable-elements": ELEMENTS.encode(), "rebrickable-colors": COLORS.encode(),
         "ldraw": LDCONFIG.encode(), "bricklink": BRICKLINK.encode("latin-1"),
         "rebrickable-terms": TERMS.encode()}
    s.update({k.replace("_", "-"): v for k, v in override.items()})
    return s


def _pages(**override):
    p = {f"bricklink-{part}": (FIXTURES / f"bricklink-{part}.html").read_text(encoding="utf-8")
         for part in PARTS}
    p.update(override)
    return p


def _build(snap=None, pages=None, inventory=INVENTORY, black=BLACK, **kw):
    return plaque.build(snap or _snap(), pages or _pages(), inventory, black, "2026-11-24", **kw)


# --- the join ---------------------------------------------------------------------------------

def test_build_on_fixtures_passes_the_loader():
    data = _build()
    table = parse_plaque_parts(data)
    assert (table.plaques["small"].tile.part_id, table.plaques["small"].plate.part_id) == ("10202", "3958")
    assert (table.plaques["large"].tile.part_id, table.plaques["large"].plate.part_id) == ("4974", "92438")
    assert table.plaques["small"].studs == (6, 6) and table.plaques["large"].studs == (16, 8)
    assert list(data["parts"]) == list(PARTS)
    assert data["parts"]["10202"]["name"] == "Tile 6 x 6 with Bottom Tubes"
    assert data["parts"]["10202"]["bricklink"] == {
        "item_type": "P", "item_no": "10202", "alternates": [], "colors": ["Black", "White"],
        "citation": "bricklink-10202"}
    assert data["parts"]["10202"]["rebrickable"] == {"part_num": "10202", "citation": "rebrickable-elements"}
    assert [s["id"] for s in data["source"]["snapshots"]] == [
        "rebrickable-elements", "rebrickable-colors", "ldraw", "bricklink",
        "bricklink-10202", "bricklink-3958", "bricklink-4974", "bricklink-92438"]
    assert data["source"]["terms"]["text"] == TERMS_TEXT
    assert data["source"]["generator"] == "tools/partcolors plaque-parts"
    assert len(data["source"]["rules"]) == 9


def test_rule2_black_equals_the_part_colors_row():
    """Rule 2: names, IDs and RGB of Black from the snapshots equal part_colors.json's lego_black."""
    row = next(r for rows in PART_COLORS["parts"].values() for r in rows if r["key"] == "lego_black")
    for part in _build()["parts"].values():
        c = part["color"]
        assert c["key"] == "lego_black"
        for f in ("lego", "bricklink", "rebrickable", "rgb"):
            assert c[f] == row[f]
        assert c["citations"] == {"lego": "ldraw", "bricklink": "bricklink",
                                  "rebrickable": "rebrickable-colors", "element": "rebrickable-elements"}


def test_element_choice_lowest_with_design_id_all_kept():
    parts = _build()["parts"]
    assert parts["10202"]["color"]["element_id"] == "6155125"
    assert parts["10202"]["color"]["element_ids"] == ["6155125"]  # the White row is not Black
    # a second Black element with a higher ID is kept, not chosen
    assert parts["3958"]["color"]["element_id"] == "395826"
    assert parts["3958"]["color"]["element_ids"] == ["395826", "9100002"]
    assert parts["4974"]["color"]["element_id"] == "6484420"
    assert parts["4974"]["name"] == "Tile 8 x 16 with Bottom Tubes, Polished Surface"
    # a lower-numbered Black element whose design_id differs is kept, not chosen; rule 4 lists its design
    assert parts["92438"]["color"]["element_id"] == "6094066"
    assert parts["92438"]["color"]["element_ids"] == ["100001", "6094066"]
    assert parts["92438"]["lego_design_ids"] == ["92438", "99999"]
    assert parts["10202"]["lego_design_ids"] == ["10202"]


@pytest.mark.parametrize("rule,case", [
    (1, "no Black element of 10202"),
    (2, "Black RGB differs from part_colors.json"),
    (2, "part_colors.json's lego_black differs from the snapshots"),
    (3, "a Black element of design 10202 filed under another part_num"),
    (4, "the only Black element of 4974 has no design_id"),
    (5, "3958 is neither the BrickLink item number nor an alternate"),
    (6, "BrickLink's page for 4974 does not list Black"),
    (7, "92438 is in the kit inventory"),
    (7, "BrickLink names 10202 a plate"),
    (7, "BrickLink's dimensions for 3958 differ from the plaque"),
    (8, "a page accessed date is not YYYY-MM-DD"),
    (9, "LEGO's name for color 0 gives another color key"),
])
def test_build_rules_fail(rule, case):
    snap, pages, inventory, black, kw = _snap(), _pages(), INVENTORY, BLACK, {}
    if rule == 1:
        snap = _snap(rebrickable_elements=ELEMENTS.replace("6155125,10202,0,10202\n", "").encode())
    elif case.startswith("Black RGB"):
        snap = _snap(rebrickable_colors=COLORS.replace("05131D", "000000").encode())
    elif rule == 2:
        black = json.loads(json.dumps(BLACK))
        black["lego"]["id"] = 99
    elif rule == 3:
        snap = _snap(rebrickable_elements=(ELEMENTS + "9100004,10202b,0,10202\n").encode())
    elif rule == 4:
        snap = _snap(rebrickable_elements=ELEMENTS.replace("6484420,4974,0,4974", "6484420,4974,0,").encode())
    elif rule == 5:
        pages = _pages(**{"bricklink-3958": pages["bricklink-3958"].replace("3958", "3959")})
    elif rule == 6:
        page = pages["bricklink-4974"]
        pages = _pages(**{"bricklink-4974": page.replace('data-color="11" data-name="Black"',
                                                          'data-color="2" data-name="Tan"')})
    elif case.startswith("92438"):
        inventory = json.loads(json.dumps(INVENTORY))
        inventory["elements"][0]["part_ids"] = ["92438"]
    elif case.startswith("BrickLink names"):
        pages = _pages(**{"bricklink-10202": pages["bricklink-10202"].replace("Tile 6 x 6", "Plate 6 x 6")})
    elif rule == 7:
        pages = _pages(**{"bricklink-3958": pages["bricklink-3958"].replace("Plate 6 x 6", "Plate 4 x 6")})
    elif rule == 8:
        specs = [dict(p) for p in plaque.PLAQUE_PAGES]
        specs[1]["accessed"] = "24.11.2026"
        kw = {"plaque_pages": specs}
    elif rule == 9:
        snap = _snap(ldraw=LDCONFIG.replace("26 - Black", "26 - Noir").encode())
    with pytest.raises(BuildError, match=rf"rule {rule}: "):
        _build(snap, pages, inventory, black, **kw)


def test_build_checks_rebrickable_terms():
    with pytest.raises(SnapshotError, match="terms"):
        _build(_snap(rebrickable_terms=b"<p>no terms here</p>"))


def test_differences_ignore_generation_date():
    a = _build()
    b = plaque.build(_snap(), _pages(), INVENTORY, BLACK, "2027-01-01")
    assert plaque.differences(a, b) == []
    b["parts"]["3958"]["color"]["element_id"] = "9100002"
    assert plaque.differences(a, b) == ["parts.3958: changed"]
    assert plaque.differences(a, {}) != []


def test_to_text_is_stable_json():
    data = _build()
    text = plaque.to_text(data)
    assert text.endswith("\n") and json.loads(text) == data
    assert plaque.to_text(json.loads(text)) == text


def test_pinned_pages_are_archived_bricklink_pages():
    assert [p["part"] for p in plaque.PLAQUE_PAGES] == list(PARTS)
    for p in plaque.PLAQUE_PAGES:
        assert p["id"] == f"bricklink-{p['part']}" and p["file"] == f"bricklink-{p['part']}.html"
        assert p["url"].startswith("http://web.archive.org/web/")
        assert p["url"].endswith(f"id_/https://www.bricklink.com/v2/catalog/catalogitem.page?P={p['part']}")
        assert len(p["sha256"]) == 64 and int(p["sha256"], 16) >= 0
        assert "Internet Archive copy of" in p["title"]
    # the committed fixtures are synthetic, not copies of the pinned pages
    pinned = {p["sha256"] for p in plaque.PLAQUE_PAGES}
    for part in PARTS:
        page = FIXTURES / f"bricklink-{part}.html"
        assert hashlib.sha256(page.read_bytes()).hexdigest() not in pinned
        src = json.loads((FIXTURES / f"bricklink-{part}.source.json").read_text(encoding="utf-8"))
        assert src["synthetic"] is True and "not a copy of a catalog page" in src["note"]
        assert src["sha256"] == hashlib.sha256(page.read_bytes()).hexdigest()
        assert src["disclaimer"] == DISCLAIMER
    src = json.loads((FIXTURES / "elements.source.json").read_text(encoding="utf-8"))
    assert src["sha256"] == hashlib.sha256((FIXTURES / "elements.csv").read_bytes()).hexdigest()
    assert src["synthetic"] is True and src["disclaimer"] == DISCLAIMER
    assert ELEMENTS.splitlines()[0] == "element_id,part_num,color_id,design_id"  # the pinned header
    # the Rebrickable snapshots are partcolors' own pins (rebrickable-elements dfc8641d...)
    ids = {s["id"]: s for s in plaque.SNAPSHOTS}
    assert ids["rebrickable-elements"]["sha256"].startswith("dfc8641d")


# --- the command ------------------------------------------------------------------------------

def _gz(b: bytes) -> bytes:
    return gzip.compress(b, mtime=0)


@pytest.fixture()
def cache(tmp_path, monkeypatch):
    """A maintainer cache holding the synthetic snapshots, pinned by their own checksums."""
    root = tmp_path / "cache"
    pc, pn = root / "sources" / "partcolors", root / "sources" / "partnumbers"
    pc.mkdir(parents=True)
    pn.mkdir(parents=True)
    files = {"elements.csv.gz": _gz(ELEMENTS.encode()), "colors.csv.gz": _gz(COLORS.encode()),
             "LDConfig.ldr": LDCONFIG.encode(), "catalogColors.html": BRICKLINK.encode("latin-1"),
             "../partnumbers/rebrickable-downloads.html": TERMS.encode()}
    specs = []
    for s in plaque.SNAPSHOTS:
        b = files[s["file"]]
        (pc / s["file"]).write_bytes(b)
        specs.append({**s, "sha256": hashlib.sha256(b).hexdigest()})
    pages = []
    for p in plaque.PLAQUE_PAGES:
        b = (FIXTURES / p["file"]).read_bytes()
        (pn / p["file"]).write_bytes(b)
        pages.append({**p, "sha256": hashlib.sha256(b).hexdigest()})
    monkeypatch.setattr(plaque, "SNAPSHOTS", tuple(specs))
    monkeypatch.setattr(plaque, "PLAQUE_PAGES", tuple(pages))
    out = tmp_path / "plaque_parts.json"
    monkeypatch.setattr(pc_main, "PLAQUE_PARTS_PATH", out)
    monkeypatch.setenv("LEGO_IMAGE_PROCESSOR_CACHE", str(root))
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    return {"root": root, "partcolors": pc, "partnumbers": pn, "out": out}


def _run(*args):
    return CliRunner().invoke(pc_main.main, ["plaque-parts", *args])


def _last(output):
    return output.strip().splitlines()[-1]


def test_command_writes_then_check_reports_no_differences(cache):
    r = _run()
    assert r.exit_code == 0, r.output
    assert _last(r.output) == DISCLAIMER
    table = load_plaque_parts(cache["out"])
    assert table.plaques["small"].tile.color.element_id == "6155125"
    assert "10202" in r.output and "6155125" in r.output
    r = _run("--check")
    assert r.exit_code == 0, r.output
    assert "no differences" in r.output.splitlines()
    assert _last(r.output) == DISCLAIMER


def test_check_ignores_generated_on(cache):
    assert _run().exit_code == 0
    data = json.loads(cache["out"].read_text(encoding="utf-8"))
    data["source"]["generated_on"] = "2001-01-01"
    cache["out"].write_text(json.dumps(data), encoding="utf-8")
    r = _run("--check")
    assert r.exit_code == 0, r.output
    assert "no differences" in r.output.splitlines()
    assert json.loads(cache["out"].read_text(encoding="utf-8"))["source"]["generated_on"] == "2001-01-01"


def test_check_lists_differences_and_exits_1(cache):
    assert _run().exit_code == 0
    data = json.loads(cache["out"].read_text(encoding="utf-8"))
    data["parts"]["4974"]["name"] = "Tile 8 x 16"
    cache["out"].write_text(json.dumps(data), encoding="utf-8")
    before = cache["out"].read_bytes()
    r = _run("--check")
    assert r.exit_code == 1, r.output
    assert "difference: parts.4974: changed" in r.output.splitlines()
    assert _last(r.output) == DISCLAIMER
    assert cache["out"].read_bytes() == before  # --check writes nothing


def test_changed_snapshot_exits_4(cache):
    page = cache["partnumbers"] / "bricklink-3958.html"
    page.write_bytes(page.read_bytes() + b" ")
    r = _run("--check")
    assert r.exit_code == 4
    assert "checksum mismatch" in r.output and "bricklink-3958" in r.output
    assert _last(r.output) == DISCLAIMER
    (cache["partcolors"] / "LDConfig.ldr").write_bytes(b"changed")
    r = _run()
    assert r.exit_code == 4 and "ldraw" in r.output
    assert not cache["out"].exists()


def test_missing_snapshot_exits_4(cache):
    (cache["partcolors"] / "elements.csv.gz").unlink()
    r = _run("--check")
    assert r.exit_code == 4
    assert "rebrickable-elements missing" in r.output
    assert _last(r.output) == DISCLAIMER


def test_snapshots_come_from_the_cache_never_the_repository(cache, tmp_path, monkeypatch):
    # default: <cache>/sources/partcolors and its sibling partnumbers/ of the configured cache
    assert pc_main.default_snapshot_dir() == cache["root"] / "sources" / "partcolors"
    assert _run().exit_code == 0
    # an empty cache fails, although the repository holds same-named fixture pages
    empty = tmp_path / "empty-cache"
    monkeypatch.setenv("LEGO_IMAGE_PROCESSOR_CACHE", str(empty))
    r = _run("--check")
    assert r.exit_code == 4 and str(empty) in r.output
    repo = Path(__file__).resolve().parents[3]
    assert str(repo) not in r.output


def test_snapshots_option(cache, tmp_path, monkeypatch):
    monkeypatch.setenv("LEGO_IMAGE_PROCESSOR_CACHE", str(tmp_path / "elsewhere"))
    r = _run("--snapshots", str(cache["partcolors"]))
    assert r.exit_code == 0, r.output
    assert cache["out"].is_file()


def test_build_error_exits_5(cache, monkeypatch):
    bad = json.loads(json.dumps(INVENTORY))
    bad["elements"][0]["part_ids"] = ["10202"]
    monkeypatch.setattr(pc_main, "INVENTORY_PATH", cache["root"] / "inventory.json")
    (cache["root"] / "inventory.json").write_text(json.dumps(bad), encoding="utf-8")
    r = _run()
    assert r.exit_code == 5 and "rule 7" in r.output
    assert _last(r.output) == DISCLAIMER

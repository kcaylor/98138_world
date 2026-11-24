"""CLI contract for `parts list`, `parts export` and `kit part-numbers` (005 T020, T025, T032)."""

import json
import xml.etree.ElementTree as ET

import pytest
from click.testing import CliRunner

from lego_image_processor.cli.main import cli
from lego_image_processor.kit import load_official_design
from lego_image_processor.kit.source import DISCLAIMER

from ..unit.parts.layouts import LAND_ELEVATION, SMALL, UNCITED, make_grid


def _last(output: str) -> str:
    return output.rstrip("\n").splitlines()[-1]


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def layouts(tmp_path):
    out = {}
    for name, grid in (("official", load_official_design().to_layout()), ("small", make_grid(SMALL)),
                       ("uncited", make_grid(UNCITED)), ("elev", make_grid(LAND_ELEVATION))):
        p = tmp_path / f"{name}.json"
        p.write_text(grid.to_json(), encoding="utf-8")
        out[name] = p
    return out


# --- parts list ---------------------------------------------------------------------------------

def test_list_table(runner, layouts):
    r = runner.invoke(cli, ["parts", "list", str(layouts["official"])])
    assert r.exit_code == 0, r.output
    assert "4073 / White (1)" in r.output and "98138 / Dark Turquoise (39)" in r.output
    assert "Totals: 10 lots, 10,240 pieces needed" in r.output
    assert ("Prices: none in this file. Estimate them offline with `lego-image-processor parts "
            "estimate LAYOUT` (BrickLink price guide snapshot), or upload the list to BrickLink or "
            "Rebrickable to price it.") in r.output
    assert "Catalog data: Rebrickable" in r.output
    assert _last(r.output) == DISCLAIMER


def test_list_all_columns(runner, layouts):
    r = runner.invoke(cli, ["parts", "list", str(layouts["official"]), "--all-columns"])
    assert r.exit_code == 0 and "6141 / White (15)" in r.output and "614101" in r.output


def test_list_json_stdout_and_file(runner, layouts, tmp_path):
    r = runner.invoke(cli, ["parts", "list", str(layouts["small"]), "--format", "json"])
    assert r.exit_code == 0
    d = json.loads(r.output)
    assert d["disclaimer"] == DISCLAIMER and d["totals"]["needed"] == 69
    out = tmp_path / "pl.json"
    r = runner.invoke(cli, ["parts", "list", str(layouts["small"]), "-o", str(out)])
    assert r.exit_code == 0 and _last(r.output) == DISCLAIMER
    assert json.loads(out.read_text(encoding="utf-8")) == d
    again = tmp_path / "pl2.json"
    runner.invoke(cli, ["parts", "list", str(layouts["small"]), "-o", str(again), "-q"])
    assert again.read_bytes() == out.read_bytes()


def test_list_unverified_warns_and_exits_zero(runner, layouts):
    r = runner.invoke(cli, ["parts", "list", str(layouts["uncited"])])
    assert r.exit_code == 0
    assert "Warning: 1 unverified lot" in r.output and "Medium Blue" in r.output
    assert "no cited color for part" in r.output and _last(r.output) == DISCLAIMER


def test_list_bad_layout_exits_one(runner, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("[]", encoding="utf-8")
    for path in (bad, tmp_path / "absent.json"):
        r = runner.invoke(cli, ["parts", "list", str(path)])
        assert r.exit_code == 1, r.output
        assert "Error:" in r.output and _last(r.output) == DISCLAIMER


def test_list_quiet(runner, layouts):
    r = runner.invoke(cli, ["parts", "list", str(layouts["small"]), "-q"])
    assert r.exit_code == 0 and r.output == ""


def test_list_output_dir_missing(runner, layouts, tmp_path):
    r = runner.invoke(cli, ["parts", "list", str(layouts["small"]), "-o", str(tmp_path / "no" / "x.json")])
    assert r.exit_code == 1 and "does not exist" in r.output


# --- kit part-numbers ---------------------------------------------------------------------------

def test_kit_part_numbers(runner):
    r = runner.invoke(cli, ["kit", "part-numbers"])
    assert r.exit_code == 0
    assert "P 4073" in r.output and "P 98138" in r.output and "SHA-256" in r.output
    assert _last(r.output) == DISCLAIMER
    j = runner.invoke(cli, ["kit", "part-numbers", "--format", "json"])
    d = json.loads(j.output)
    assert d["parts"]["6141"]["bricklink"]["item_no"] == "4073"
    assert d["source"]["disclaimer"] == DISCLAIMER
    assert runner.invoke(cli, ["kit", "part-numbers", "--kit", "10000"]).exit_code == 1


# --- parts export -------------------------------------------------------------------------------

def test_export_needs_a_target(runner, layouts):
    r = runner.invoke(cli, ["parts", "export", str(layouts["small"])])
    assert r.exit_code == 2 and "--bricklink" in r.output


def test_export_writes_both_files(runner, layouts, tmp_path):
    xml_p, csv_p = tmp_path / "o.xml", tmp_path / "o.csv"
    r = runner.invoke(cli, ["parts", "export", str(layouts["official"]), "--bricklink", str(xml_p),
                            "--rebrickable", str(csv_p)])
    assert r.exit_code == 0, r.output
    items = ET.fromstring(xml_p.read_text(encoding="utf-8")).findall("ITEM")
    assert len(items) == 10 and sum(int(i.findtext("MINQTY")) for i in items) == 10240
    assert {i.findtext("ITEMID") for i in items} == {"4073", "98138"}
    lines = csv_p.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "Part,Color,Quantity" and len(lines) == 11
    assert "adds these quantities to items already on the chosen wanted list" in r.output
    assert _last(r.output) == DISCLAIMER
    assert DISCLAIMER not in xml_p.read_text() and DISCLAIMER not in csv_p.read_text()  # Q4


def test_export_condition(runner, layouts, tmp_path):
    p = tmp_path / "u.xml"
    r = runner.invoke(cli, ["parts", "export", str(layouts["small"]), "--bricklink", str(p), "--condition", "used"])
    assert r.exit_code == 0
    assert {i.findtext("CONDITION") for i in ET.fromstring(p.read_text()).findall("ITEM")} == {"U"}
    assert runner.invoke(cli, ["parts", "export", str(layouts["small"]), "--bricklink", str(p),
                               "--condition", "mint"]).exit_code == 2


def test_export_unverified_exit_6_writes_nothing(runner, layouts, tmp_path):
    xml_p, csv_p = tmp_path / "x.xml", tmp_path / "x.csv"
    r = runner.invoke(cli, ["parts", "export", str(layouts["uncited"]), "--bricklink", str(xml_p),
                            "--rebrickable", str(csv_p)])
    assert r.exit_code == 6, r.output
    assert "lego_medium_blue" in r.output and "--allow-partial" in r.output
    assert not xml_p.exists() and not csv_p.exists()
    assert _last(r.output) == DISCLAIMER


def test_export_allow_partial(runner, layouts, tmp_path):
    csv_p = tmp_path / "p.csv"
    r = runner.invoke(cli, ["parts", "export", str(layouts["uncited"]), "--rebrickable", str(csv_p),
                            "--allow-partial"])
    assert r.exit_code == 0, r.output
    assert len(csv_p.read_text().splitlines()) == 5
    assert "Omitted 1 unverified lot" in r.output and "Medium Blue" in r.output


def test_export_nothing_to_buy(runner, layouts, tmp_path):
    p = tmp_path / "none.xml"
    r = runner.invoke(cli, ["parts", "export", str(layouts["official"]), "--kits", "1", "--bricklink", str(p)])
    assert r.exit_code == 0
    assert "Nothing to buy: the owned parts cover this layout." in r.output and not p.exists()
    assert _last(r.output) == DISCLAIMER


def test_export_output_dir_missing(runner, layouts, tmp_path):
    r = runner.invoke(cli, ["parts", "export", str(layouts["small"]), "--bricklink", str(tmp_path / "no" / "x.xml")])
    assert r.exit_code == 1 and "does not exist" in r.output


# --- top-up options on both commands ------------------------------------------------------------

@pytest.mark.parametrize("command", ["list", "export"])
def test_topup_options(runner, layouts, tmp_path, command):
    loose = tmp_path / "loose.csv"
    loose.write_text("Part,Color,Quantity\n98138,3,1000\n", encoding="utf-8")
    missing = tmp_path / "missing.csv"
    missing.write_text("Element,Quantity\n6322819,12\n", encoding="utf-8")
    args = ["parts", command, str(layouts["elev"]), "--kits", "1", "--owned", str(loose),
            "--missing", str(missing), "--spares", "2"]
    if command == "list":
        r = runner.invoke(cli, args + ["--format", "json"])
        assert r.exit_code == 0, r.output
        d = json.loads(r.output)
        bbg = next(l for l in d["lots"] if l["color_key"] == "lego_bright_bluish_green")
        assert (bbg["shortfall"], bbg["spares"], bbg["to_buy"]) == (2145, 43, 2188)
        assert d["owned"]["kits"] == 1 and d["owned"]["spares_percent"] == "2"
        assert [f["path"] for f in d["owned"]["owned_files"]] == [str(loose)]
        assert len(d["owned"]["missing_files"][0]["sha256"]) == 64
    else:
        out = tmp_path / "t.csv"
        r = runner.invoke(cli, args + ["--rebrickable", str(out)])
        assert r.exit_code == 0, r.output
        assert "98138,3,2188" in out.read_text().splitlines()


@pytest.mark.parametrize("extra", [["--kits", "-1"], ["--kits", "x"], ["--spares", "101"], ["--spares", "-1"],
                                   ["--spares", "lots"]])
def test_topup_usage_errors(runner, layouts, extra):
    r = runner.invoke(cli, ["parts", "list", str(layouts["small"])] + extra)
    assert r.exit_code == 2, r.output


def test_bad_owned_file_exits_one(runner, layouts, tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("Part,Color,Quantity\n4073,15,1\n", encoding="utf-8")
    r = runner.invoke(cli, ["parts", "list", str(layouts["small"]), "--owned", str(bad)])
    assert r.exit_code == 1 and f"{bad}:2" in r.output and "Rebrickable part numbers" in r.output


def test_kit_part_colors_acknowledges_rebrickable(runner):
    """005 FR-002 / research R5: Rebrickable's terms ask for acknowledgement."""
    r = runner.invoke(cli, ["kit", "part-colors", "--part", "6141"])
    assert "Catalog data: Rebrickable" in r.output and "Free for personal and commercial use" in r.output
    assert _last(r.output) == DISCLAIMER


# --- leftovers in the box (feature 014) ---------------------------------------------------------

def test_list_leftovers_table_with_one_kit(runner, layouts):
    r = runner.invoke(cli, ["parts", "list", str(layouts["official"]), "--kits", "1"])
    assert r.exit_code == 0, r.output
    assert "Left over in the box (1 kit of 31203):" in r.output
    assert "Left over in the box: 890 pieces" in r.output
    lines = r.output.split("Left over in the box (1 kit of 31203):", 1)[1].splitlines()
    white = next(l for l in lines if l.startswith("plate"))
    assert white.split()[-3:] == ["3,064", "3,062", "2"]
    coral = next(l for l in lines if "Vibrant Coral (353)" in l)
    assert coral.split()[-3:] == ["601", "203", "398"]
    assert _last(r.output) == DISCLAIMER


def test_list_no_leftover_table_without_kits(runner, layouts):
    r = runner.invoke(cli, ["parts", "list", str(layouts["official"])])
    assert r.exit_code == 0 and "Left over in the box" not in r.output


def test_list_leftovers_json(runner, layouts):
    r = runner.invoke(cli, ["parts", "list", str(layouts["small"]), "--kits", "1", "--format", "json"])
    d = json.loads(r.output)
    assert len(d["leftovers"]) == 10 and d["totals"]["leftover"] == 11130 - 30 - 20
    coral = next(x for x in d["leftovers"] if x["color_key"] == "lego_vibrant_coral")
    assert (coral["kit_supply"], coral["used"], coral["leftover"]) == (601, 0, 601)


# --- layouts on the Winkel tripel template (feature 016 T072; contracts/cli.md "Other commands") --

PRICES = __import__("pathlib").Path(__file__).resolve().parents[1] / "fixtures" / "prices"


@pytest.fixture
def winkel_file(confirmed_winkel, tmp_path):
    from ..winkel_layouts import winkel_grid
    p = tmp_path / "winkel.json"
    p.write_text(winkel_grid(confirmed_winkel).to_json(), encoding="utf-8")
    return p


def _item():
    from lego_image_processor.kit.part_numbers import load_part_numbers
    return load_part_numbers().get("3070b").bricklink_item_no


def test_list_winkel_table(runner, winkel_file, confirmed_winkel):
    r = runner.invoke(cli, ["parts", "list", str(winkel_file), "--kits", "1"])
    assert r.exit_code == 0, r.output
    n = confirmed_winkel.counts["margin"]
    assert (f"Template: winkel-tripel ({confirmed_winkel.title}); margin in 1x1 square tiles "
            "(part 3070b), which kit 31203 does not have") in r.output
    rows = [l for l in r.output.splitlines() if l.startswith("square tile")]
    assert len(rows) == 1
    assert "Black (26)" in rows[0] and f"{_item()} / Black (11)" in rows[0]
    assert rows[0].split()[-3:] == [f"{n:,}", "0", f"{n:,}"]           # needed, owned, to buy
    box = r.output.split("Left over in the box (1 kit of 31203):")[1]
    assert "square" not in box
    assert "Totals: 4 lots, 10,240 pieces needed" in r.output
    assert _last(r.output) == DISCLAIMER


def test_list_winkel_json(runner, winkel_file, confirmed_winkel):
    r = runner.invoke(cli, ["parts", "list", str(winkel_file), "--format", "json"])
    assert r.exit_code == 0, r.output
    d = json.loads(r.output)
    assert d["layout"]["template"] == {"id": "winkel-tripel", "title": confirmed_winkel.title}
    sq = [l for l in d["lots"] if l["part_type"] == "square_tile"]
    assert len(sq) == 1 and sq[0]["part_id"] == "3070b" and sq[0]["bricklink"]["item_no"] == _item()
    assert sq[0]["rebrickable"]["part_num"] == "3070b"
    assert list(d)[-1] == "disclaimer"


def test_export_winkel(runner, winkel_file, confirmed_winkel, tmp_path):
    xml, csv = tmp_path / "w.xml", tmp_path / "w.csv"
    r = runner.invoke(cli, ["parts", "export", str(winkel_file), "--bricklink", str(xml),
                            "--rebrickable", str(csv), "--kits", "1"])
    assert r.exit_code == 0, r.output
    n = confirmed_winkel.counts["margin"]
    items = [(i.findtext("ITEMID"), i.findtext("MINQTY")) for i in ET.fromstring(xml.read_text()).findall("ITEM")]
    assert (_item(), str(n)) in items
    assert f"3070b,0,{n}" in csv.read_text().splitlines()
    assert _last(r.output) == DISCLAIMER


def test_estimate_winkel(runner, winkel_file, confirmed_winkel):
    base = ["parts", "estimate", str(winkel_file), "--as-of", "2026-12-05", "--prices"]
    r = runner.invoke(cli, base + [str(PRICES / "bricklink_price_guide.json")])
    assert r.exit_code == 0, r.output
    n = confirmed_winkel.counts["margin"]
    assert f"Template: winkel-tripel ({confirmed_winkel.title})" in r.output
    assert f"  square tile 3070b Black (LEGO 26): not in the price snapshot; {n:,} pieces" in r.output
    assert _last(r.output) == DISCLAIMER
    r = runner.invoke(cli, base + [str(PRICES / "bricklink_price_guide_3070b.json"), "--format", "json"])
    assert r.exit_code == 0, r.output
    d = json.loads(r.output)
    assert d["layout"]["template"]["id"] == "winkel-tripel"
    assert d["estimates"]["full"]["complete"] and d["estimates"]["one_kit"]["complete"]
    assert list(d)[-1] == "disclaimer"


def _square_csv(tmp_path, name, text):
    p = tmp_path / name
    p.write_text("Part,Color,Quantity\n" + text, encoding="utf-8")
    return p


def test_kit_owned_square_tile_rows_ignored(runner, layouts, tmp_path):
    """A kit layout has no square tiles: 3070b rows and its other numbers are ignored and counted,
    as on main (feature 016 T110; SC-001)."""
    owned = _square_csv(tmp_path, "owned.csv", "6141,15,10\n3070b,0,40\n3070,0,3\n112412,0,1\n")
    missing = _square_csv(tmp_path, "missing.csv", "3070b,0,2\n30039,0,1\n")
    args = ["parts", "list", str(layouts["official"]), "--kits", "1", "--owned", str(owned),
            "--missing", str(missing)]
    r = runner.invoke(cli, args)
    assert r.exit_code == 0, r.output
    assert "5 row(s) for other parts ignored" in r.output
    assert not any(line.startswith(("square tile", "Template:")) for line in r.output.splitlines())
    r = runner.invoke(cli, args + ["--format", "json"])
    d = json.loads(r.output)
    assert d["owned"]["ignored_rows"] == 5 and "3070b" not in {l["part_id"] for l in d["lots"]}
    xml = tmp_path / "k.xml"
    r = runner.invoke(cli, ["parts", "export", str(layouts["official"]), "--bricklink", str(xml),
                            "--owned", str(owned)])
    assert r.exit_code == 0, r.output
    assert "3070" not in {i.findtext("ITEMID") for i in ET.fromstring(xml.read_text()).findall("ITEM")}


def test_winkel_owned_square_tiles_counted(runner, winkel_file, confirmed_winkel, tmp_path):
    """On a template layout loose square tiles count as owned 3070b (feature 016 T110, FR-014)."""
    owned = _square_csv(tmp_path, "owned.csv", "3070b,0,40\n3001,15,4\n")
    r = runner.invoke(cli, ["parts", "list", str(winkel_file), "--owned", str(owned), "--format", "json"])
    assert r.exit_code == 0, r.output
    d = json.loads(r.output)
    n = confirmed_winkel.counts["margin"]
    sq = next(l for l in d["lots"] if l["part_id"] == "3070b")
    assert (sq["color_key"], sq["needed"], sq["owned"], sq["to_buy"]) == ("lego_black", n, 40, n - 40)
    assert d["owned"]["ignored_rows"] == 1
    r = runner.invoke(cli, ["parts", "list", str(winkel_file), "--owned", str(owned)])
    assert "1 row(s) for other parts ignored" in r.output
    csv = tmp_path / "w.csv"
    r = runner.invoke(cli, ["parts", "export", str(winkel_file), "--rebrickable", str(csv), "--owned", str(owned)])
    assert r.exit_code == 0, r.output
    assert f"3070b,0,{n - 40}" in csv.read_text().splitlines()


@pytest.mark.parametrize("command", ["list", "export"])
def test_winkel_owned_other_number_of_3070b_is_an_error(runner, winkel_file, tmp_path, command):
    bad = _square_csv(tmp_path, "bad.csv", "3070,0,3\n")
    extra = ["--rebrickable", str(tmp_path / "w.csv")] if command == "export" else []
    r = runner.invoke(cli, ["parts", command, str(winkel_file), "--owned", str(bad)] + extra)
    assert r.exit_code == 1
    assert ("part 3070 is another catalog's number for map part 3070b; this file must use "
            "Rebrickable part numbers (3070b, 6141, 98138)") in r.output
    assert not (tmp_path / "w.csv").exists()
    assert _last(r.output) == DISCLAIMER


def test_kit_list_has_no_template_wording(runner, layouts):
    r = runner.invoke(cli, ["parts", "list", str(layouts["official"]), "--kits", "1"])
    assert r.exit_code == 0
    assert "Template" not in r.output and "square" not in r.output

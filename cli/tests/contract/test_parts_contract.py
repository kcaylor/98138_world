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
    assert "Prices: none are estimated" in r.output and "Catalog data: Rebrickable" in r.output
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

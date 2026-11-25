"""CLI contract for combinations D and E (feature 010 contracts/cli.md).

Not affiliated with or endorsed by The LEGO Group.
"""

import json

import pytest
from click.testing import CliRunner

from lego_image_processor.cli.main import cli

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
D_LINE = ("Arrangement: D (pacific, frames 2b·3·1·2a, the Pacific (date line) in the centre; "
          "not in the building instructions)")


@pytest.fixture
def runner():
    return CliRunner()


def _last(text):
    return text.rstrip("\n").splitlines()[-1]


def _build(runner, path, *args):
    r = runner.invoke(cli, ["map", "build", "official-31203", "-o", str(path), *args])
    assert r.exit_code == 0, r.output
    return r


@pytest.mark.parametrize("value,aid,shift", [("D", "D", 64), ("pacific", "D", 64), ("Pacific", "D", 64),
                                             ("e", "E", 80), ("asia-pacific", "E", 80)])
def test_map_build_d_e(runner, tmp_path, value, aid, shift):
    out = tmp_path / "m.json"
    r = _build(runner, out, "--arrangement", value)
    assert f"Arrangement: {aid} (" in r.output and "not in the building instructions" in r.output
    assert _last(r.output) == DISCLAIMER
    rec = json.loads(out.read_text())["metadata"]["arrangement"]
    assert rec["id"] == aid and rec["column_shift"] == shift and rec["in_instructions"] is False
    assert rec["source"]["pages"] == [134, 135, 136, 137, 138, 139, 140]


def test_map_check_d(runner):
    r = runner.invoke(cli, ["map", "check", "official-31203", "--arrangement", "D"])
    assert r.exit_code == 0, r.output
    assert D_LINE in r.output and _last(r.output) == DISCLAIMER


def test_help_lists_five(runner):
    r = runner.invoke(cli, ["map", "build", "--help"])
    assert "[A|B|C|D|E]" in r.output and "pacific" in r.output and "asia-pacific" in r.output
    assert "not in the building instructions" in " ".join(r.output.split())
    r = runner.invoke(cli, ["layout", "arrange", "--help"])
    assert "[A|B|C|D|E]" in r.output


def test_layout_arrange_round_trip(runner, tmp_path):
    a = tmp_path / "a.json"
    _build(runner, a)
    d, e, back = tmp_path / "d.json", tmp_path / "e.json", tmp_path / "back.json"
    r = runner.invoke(cli, ["layout", "arrange", str(a), "--arrangement", "pacific", "-o", str(d)])
    assert r.exit_code == 0, r.output
    assert "2b Europe & Africa, 3 Asia & Australia, 1 America, 2a Europe & Africa" in r.output
    assert _last(r.output) == DISCLAIMER
    assert runner.invoke(cli, ["layout", "arrange", str(d), "--arrangement", "E", "-o", str(e)]).exit_code == 0
    assert runner.invoke(cli, ["layout", "arrange", str(e), "--arrangement", "A", "-o", str(back)]).exit_code == 0
    pa = json.loads(a.read_text())["positions"]
    pd = {(p["x"], p["y"]): p["color_id"] for p in json.loads(d.read_text())["positions"]}
    assert all(pd[((p["x"] + 64) % 128, p["y"])] == p["color_id"] for p in pa)
    assert json.loads(back.read_text())["positions"] == pa


def test_built_d_equals_arranged_d(runner, tmp_path):
    a, d1, d2 = tmp_path / "a.json", tmp_path / "d1.json", tmp_path / "d2.json"
    _build(runner, a)
    _build(runner, d1, "--arrangement", "D")
    assert runner.invoke(cli, ["layout", "arrange", str(a), "-a", "D", "-o", str(d2)]).exit_code == 0
    assert json.loads(d1.read_text())["positions"] == json.loads(d2.read_text())["positions"]


@pytest.mark.parametrize("aid", ["D", "E"])
def test_downstream_commands_accept(runner, tmp_path, aid):
    m = tmp_path / "m.json"
    _build(runner, m, "--arrangement", aid)
    r = runner.invoke(cli, ["validate", str(m)])
    assert r.exit_code == 0, r.output
    assert f"Arrangement: {aid} (" in r.output
    r = runner.invoke(cli, ["parts", "list", str(m), "--format", "json"])
    assert r.exit_code == 0, r.output
    r = runner.invoke(cli, ["sheets", "counts", str(m), "--format", "json"])
    assert r.exit_code == 0, r.output
    assert json.loads(r.output)["arrangement"] == aid


def test_recipe_key_e(runner, tmp_path):
    src = (__import__("lego_image_processor.maps.recipe", fromlist=["RECIPES_DIR"]))
    text = (src.RECIPES_DIR / "official-31203.toml").read_text(encoding="utf-8")
    text = text.replace('id = "official-31203"', 'id = "official-31203-e"\narrangement = "E"', 1)
    rp = tmp_path / "official-e.toml"
    rp.write_text(text, encoding="utf-8")
    out = tmp_path / "m.json"
    r = runner.invoke(cli, ["map", "build", str(rp), "-o", str(out)])
    assert r.exit_code == 0, r.output
    assert "Arrangement: E (" in r.output and "from the recipe" in r.output
    assert json.loads(out.read_text())["metadata"]["arrangement"]["id"] == "E"

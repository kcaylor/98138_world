"""CLI contract for arrangements (feature 007 contracts/cli.md): `--arrangement` on `map build` and
`map check`, `layout arrange`, `layout IMAGE` unchanged, `validate` names the arrangement."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from lego_image_processor.cli.main import cli

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
IMAGES = Path(__file__).resolve().parents[1] / "fixtures" / "images"


@pytest.fixture
def runner():
    return CliRunner()


def _last(text):
    return text.rstrip("\n").splitlines()[-1]


@pytest.fixture
def official(runner, tmp_path):
    out = tmp_path / "official.json"
    r = runner.invoke(cli, ["map", "build", "official-31203", "-o", str(out), "-q"])
    assert r.exit_code == 0, r.output
    return out


@pytest.mark.parametrize("value,aid", [("B", "B"), ("b", "B"), ("americas", "B"), ("Asia-Australia", "C"),
                                       ("europe-africa", "A")])
def test_map_build_arrangement_values(runner, tmp_path, value, aid):
    out = tmp_path / "m.json"
    r = runner.invoke(cli, ["map", "build", "official-31203", "--arrangement", value, "-o", str(out)])
    assert r.exit_code == 0, r.output
    assert f"Arrangement: {aid} (" in r.output
    assert _last(r.output) == DISCLAIMER
    meta = json.loads(out.read_text())["metadata"]
    assert meta["arrangement"]["id"] == aid
    assert meta["schema_version"] == "2.0"


def test_map_build_default_is_a(runner, official):
    assert json.loads(official.read_text())["metadata"]["arrangement"]["id"] == "A"


def test_map_build_bad_arrangement_exit_2(runner, tmp_path):
    r = runner.invoke(cli, ["map", "build", "official-31203", "--arrangement", "F", "-o", str(tmp_path / "x.json")])
    assert r.exit_code == 2
    assert "A, B, C, D, E, europe-africa, americas, asia-australia, pacific, asia-pacific" in r.output


def test_map_check_arrangement(runner):
    r = runner.invoke(cli, ["map", "check", "official-31203", "--arrangement", "C"])
    assert r.exit_code == 0, r.output
    assert "Arrangement: C (asia-australia, frames 2·3·1, Asia and Australia in the centre)" in r.output
    assert _last(r.output) == DISCLAIMER


def test_map_build_preview_follows_arrangement(runner, tmp_path):
    from PIL import Image

    from lego_image_processor.kit import load_official_design
    from lego_image_processor.maps.preview import color_rgb

    png = tmp_path / "b.png"
    r = runner.invoke(cli, ["map", "build", "official-31203", "-a", "B", "-o", str(tmp_path / "b.json"),
                            "--preview", str(png), "-q"])
    assert r.exit_code == 0, r.output
    img = Image.open(png)
    d = load_official_design()
    rgb = color_rgb()
    for x, y in ((0, 13), (31, 13), (32, 40), (100, 70)):
        key = d.color_at((x - 32) % 128, y)
        part = "6141" if key == "lego_white" else "98138"
        assert img.getpixel((x * 8 + 4, y * 8 + 4)) == rgb[(part, key)]


class TestLayoutArrange:
    def test_arrange_and_back(self, runner, official, tmp_path):
        b = tmp_path / "b.json"
        a = tmp_path / "a.json"
        r = runner.invoke(cli, ["layout", "arrange", str(official), "--arrangement", "B", "-o", str(b)])
        assert r.exit_code == 0, r.output
        assert "from A to B (column shift +32)" in r.output
        assert "3 Asia & Australia, 1 America, 2 Europe & Africa" in r.output
        assert _last(r.output) == DISCLAIMER
        r = runner.invoke(cli, ["layout", "arrange", str(b), "-a", "A", "-o", str(a), "-q"])
        assert r.exit_code == 0 and r.output == ""
        orig = json.loads(official.read_text())
        back = json.loads(a.read_text())
        assert json.dumps(back["positions"]) == json.dumps(orig["positions"])
        assert back["metadata"]["map"] == orig["metadata"]["map"]
        assert back["metadata"]["arrangement"]["id"] == "A"

    def test_b_to_c_shift(self, runner, official, tmp_path):
        b, c = tmp_path / "b.json", tmp_path / "c.json"
        runner.invoke(cli, ["layout", "arrange", str(official), "-a", "B", "-o", str(b), "-q"])
        r = runner.invoke(cli, ["layout", "arrange", str(b), "-a", "C", "-o", str(c)])
        assert r.exit_code == 0
        assert "from B to C (column shift +64)" in r.output

    def test_requires_arrangement(self, runner, official, tmp_path):
        r = runner.invoke(cli, ["layout", "arrange", str(official), "-o", str(tmp_path / "x.json")])
        assert r.exit_code == 2

    def test_missing_file_exit_1(self, runner, tmp_path):
        r = runner.invoke(cli, ["layout", "arrange", str(tmp_path / "nope.json"), "-a", "B",
                                "-o", str(tmp_path / "x.json")])
        assert r.exit_code == 1
        assert _last(r.output) == DISCLAIMER

    def test_unknown_recorded_arrangement_exit_1(self, runner, official, tmp_path):
        data = json.loads(official.read_text())
        data["metadata"]["arrangement"] = {"id": "Q"}
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps(data))
        r = runner.invoke(cli, ["layout", "arrange", str(bad), "-a", "B", "-o", str(tmp_path / "x.json")])
        assert r.exit_code == 1
        assert "unknown arrangement 'Q'" in r.output

    def test_image_layout_unchanged(self, runner, tmp_path):
        out = tmp_path / "img.json"
        r = runner.invoke(cli, ["layout", str(IMAGES / "test_128x80_quantized.png"), "-o", str(out), "-q"])
        assert r.exit_code == 0, r.output
        meta = json.loads(out.read_text())["metadata"]
        assert "arrangement" not in meta
        r = runner.invoke(cli, ["layout", "arrange", str(out), "-a", "C", "-o", str(tmp_path / "c.json"), "-q"])
        assert r.exit_code == 0, r.output

    def test_image_subcommand_name(self, runner, tmp_path):
        out = tmp_path / "img.json"
        r = runner.invoke(cli, ["layout", "image", str(IMAGES / "test_128x80_quantized.png"), "-o", str(out), "-q"])
        assert r.exit_code == 0, r.output

    def test_help_lists_arrange(self, runner):
        r = runner.invoke(cli, ["layout", "--help"])
        assert r.exit_code == 0 and "arrange" in r.output


class TestValidate:
    def test_names_arrangement(self, runner, official, tmp_path):
        b = tmp_path / "b.json"
        runner.invoke(cli, ["layout", "arrange", str(official), "-a", "B", "-o", str(b), "-q"])
        rep = tmp_path / "rep.json"
        r = runner.invoke(cli, ["validate", str(b), "-o", str(rep)])
        assert r.exit_code == 0, r.output
        assert "Arrangement: B (americas" in r.output
        assert "Checking land/sea mask (arrangement B)" in r.output
        assert "FULLY BUILDABLE" in r.output
        assert json.loads(rep.read_text())["arrangement"] == "B"
        assert _last(r.output) == DISCLAIMER

    def test_mask_mismatch(self, runner, official, tmp_path):
        b = tmp_path / "b.json"
        runner.invoke(cli, ["layout", "arrange", str(official), "-a", "B", "-o", str(b), "-q"])
        data = json.loads(b.read_text())
        del data["metadata"]["arrangement"]
        b.write_text(json.dumps(data))
        r = runner.invoke(cli, ["validate", str(b)])
        assert "do not match the kit mask in arrangement A" in r.output
        assert "PARTIALLY BUILDABLE" in r.output


class TestSheetsAndParts:
    def test_sheets_build_and_counts_in_b(self, runner, official, tmp_path):
        b = tmp_path / "b.json"
        runner.invoke(cli, ["layout", "arrange", str(official), "-a", "B", "-o", str(b), "-q"])
        pdf = tmp_path / "b.pdf"
        r = runner.invoke(cli, ["sheets", "build", str(b), "-o", str(pdf), "--sections", "A1"])
        assert r.exit_code == 0, r.output
        assert "Arrangement: B (americas" in r.output
        assert _last(r.output) == DISCLAIMER
        r = runner.invoke(cli, ["sheets", "counts", str(b)])
        assert r.exit_code == 0, r.output
        assert "A1 [G1]" in r.output
        r = runner.invoke(cli, ["parts", "list", str(b)])
        assert r.exit_code == 0, r.output
        assert "Arrangement: B (americas). Every arrangement uses the same pieces" in r.output

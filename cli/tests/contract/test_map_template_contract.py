"""CLI contract for building on a template (T058; contracts/cli.md "map build, map check, map
cells"; FR-004, FR-006, FR-009, FR-011, FR-013, FR-022). Offline, on the dataset fixtures and
``confirmed_winkel``; counts come from the loaded template, never from the contract's examples.
Not affiliated with or endorsed by The LEGO Group.
"""

import json

import pytest
from click.testing import CliRunner

from lego_image_processor.cli.main import cli
from lego_image_processor.maps.recipe import bundled_recipes

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
KIT_NOTE = "margin settings are not used on the kit template"


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def data(fixture_registry):
    return fixture_registry.place_all()


def _last(output):
    return output.rstrip("\n").splitlines()[-1]


def _lines(output):
    return output.splitlines()


def _recipe_file(tmp_path, rid, extra_top="", extra_table=""):
    text = bundled_recipes()[rid].read_text(encoding="utf-8")
    if extra_top:
        text = text.replace("seed = 31203\n", f"seed = 31203\n{extra_top}\n", 1)
    p = tmp_path / f"{rid}.toml"
    p.write_text(text + ("\n" + extra_table if extra_table else ""), encoding="utf-8")
    return p


def _margin_line(t, color="lego_black", ring=None):
    c = t.counts
    tail = f"ring {c['ring']:,} {ring}" if ring else "no ring"
    return f"Margin: {c['margin']:,} square tiles (part 3070b): {color}; {tail}"


class TestOptions:
    @pytest.mark.parametrize("cmd", ["build", "check"])
    def test_help(self, runner, cmd):
        r = runner.invoke(cli, ["map", cmd, "--help"])
        assert r.exit_code == 0
        for opt in ("--template", "--margin-color", "--ring-color"):
            assert opt in r.output


class TestBuildOutput:
    def test_template_and_margin_lines(self, runner, data, confirmed_winkel, tmp_path):
        t = confirmed_winkel
        out, rep, prev = tmp_path / "w.json", tmp_path / "r.json", tmp_path / "w.png"
        r = runner.invoke(cli, ["map", "build", "ocean-sst", "--template", "winkel-tripel", "-o", str(out),
                                "--report", str(rep), "--preview", str(prev)])
        assert r.exit_code == 0, r.output
        lines = _lines(r.output)
        i = next(n for n, line in enumerate(lines) if line.startswith("Arrangement: "))
        assert lines[i + 1] == f"Template: winkel-tripel ({t.title}) - from --template"
        assert lines[i + 2] == _margin_line(t)
        assert lines[i + 3].startswith("Land layer")
        c = t.counts
        assert (f"Layout: {out} (10,240 positions, {c['land']:,} land plates, {c['ocean']:,} ocean tiles, "
                f"{c['margin']:,} margin tiles)") in lines
        assert _last(r.output) == DISCLAIMER
        assert "etopo2022-surface-10m" in r.output  # the template's dataset is cited
        assert json.loads(out.read_text())["metadata"]["template"]["id"] == "winkel-tripel"
        report = json.loads(rep.read_text())
        assert report["template_source"] == "option" and report["margin"]["ring"] is None
        assert prev.exists()

    def test_ring_color(self, runner, data, confirmed_winkel, tmp_path):
        t = confirmed_winkel
        out = tmp_path / "w.json"
        r = runner.invoke(cli, ["map", "build", "ocean-sst", "--template", "winkel-tripel", "-o", str(out),
                                "--ring-color", "lego_bright_yellow"])
        assert r.exit_code == 0, r.output
        assert _margin_line(t, ring="lego_bright_yellow") in _lines(r.output)
        positions = json.loads(out.read_text())["positions"]
        assert sum(p["color_id"] == "lego_bright_yellow" for p in positions) == t.counts["ring"]

    def test_margin_color_and_recipe_ring_off(self, runner, data, confirmed_winkel, tmp_path):
        t = confirmed_winkel
        f = _recipe_file(tmp_path, "ocean-sst", 'template = "winkel-tripel"', '[margin]\nring = "lego_white"\n')
        r = runner.invoke(cli, ["map", "build", str(f), "-o", str(tmp_path / "w.json"),
                                "--margin-color", "lego_dark_stone_grey", "--ring-color", "none"])
        assert r.exit_code == 0, r.output
        assert f"Template: winkel-tripel ({t.title}) - from the recipe" in _lines(r.output)
        assert _margin_line(t, color="lego_dark_stone_grey") in _lines(r.output)

    def test_check(self, runner, data, confirmed_winkel, tmp_path):
        t = confirmed_winkel
        rep = tmp_path / "r.json"
        r = runner.invoke(cli, ["map", "check", "ocean-sst", "--template", "winkel-tripel", "--report", str(rep),
                                "--ring-color", "lego_white"])
        assert r.exit_code == 0, r.output
        lines = _lines(r.output)
        assert f"Template: winkel-tripel ({t.title}) - from --template" in lines
        assert _margin_line(t, ring="lego_white") in lines
        assert json.loads(rep.read_text())["template"]["counts"]["margin"] == t.counts["margin"]
        assert _last(r.output) == DISCLAIMER


class TestKitOutput:
    def test_kit_build_text_has_no_template_lines(self, runner, data, tmp_path):
        out = tmp_path / "k.json"
        r = runner.invoke(cli, ["map", "build", "ocean-sst", "-o", str(out)])
        assert r.exit_code == 0, r.output
        assert not any(line.startswith(("Template:", "Margin:")) for line in _lines(r.output))
        assert KIT_NOTE not in r.output
        assert f"Layout: {out} (10,240 positions, 3,062 land plates, 7,178 ocean tiles)" in _lines(r.output)

    def test_explicit_kit_template_prints_as_today(self, runner, data, confirmed_winkel, tmp_path):
        a = runner.invoke(cli, ["map", "build", "ocean-sst", "-o", str(tmp_path / "k.json")])
        b = runner.invoke(cli, ["map", "build", "ocean-sst", "--template", "kit-31203", "-o", str(tmp_path / "k.json")])
        assert a.exit_code == b.exit_code == 0
        assert a.output == b.output

    @pytest.mark.parametrize("how", ["recipe", "option"])
    def test_margin_on_a_kit_build_prints_a_note(self, runner, data, tmp_path, how):
        if how == "recipe":
            ref, extra = str(_recipe_file(tmp_path, "ocean-sst", extra_table='[margin]\nring = "lego_white"\n')), []
        else:
            ref, extra = "ocean-sst", ["--ring-color", "lego_white"]
        r = runner.invoke(cli, ["map", "build", ref, "-o", str(tmp_path / "k.json")] + extra)
        assert r.exit_code == 0, r.output
        assert KIT_NOTE in r.output
        assert not any(line.startswith(("Template:", "Margin:")) for line in _lines(r.output))
        assert "square_tile" not in (tmp_path / "k.json").read_text()


class TestErrors:
    def test_unknown_option_template_exit_2(self, runner, tmp_path):
        r = runner.invoke(cli, ["map", "build", "ocean-sst", "--template", "mercator", "-o", str(tmp_path / "x.json")])
        assert r.exit_code == 2
        assert "'mercator'" in r.output and "confirmed templates: kit-31203" in r.output

    def test_unknown_recipe_template_exit_1(self, runner, tmp_path):
        f = _recipe_file(tmp_path, "ocean-sst", 'template = "mercator"')
        r = runner.invoke(cli, ["map", "build", str(f), "-o", str(tmp_path / "x.json")])
        assert r.exit_code == 1
        assert "template: unknown template 'mercator'" in r.output and "confirmed templates: kit-31203" in r.output
        assert _last(r.output) == DISCLAIMER

    def test_unconfirmed_template(self, runner, data, unconfirmed_winkel, tmp_path):
        """An unconfirmed copy of the package file (the package file is confirmed)."""
        for cmd in (["map", "build", "ocean-sst", "--template", "winkel-tripel", "-o", str(tmp_path / "x.json")],
                    ["map", "check", "ocean-sst", "--template", "winkel-tripel"]):
            r = runner.invoke(cli, cmd)
            assert r.exit_code == 1
            assert "winkel-tripel" in r.output and "not confirmed by the project owner" in r.output
            assert "confirmed templates: kit-31203" in r.output
            assert _last(r.output) == DISCLAIMER
        assert not (tmp_path / "x.json").exists()

    @pytest.mark.parametrize("args,source", [(["ocean-el-nino"], "from the recipe"),
                                             (["ocean-sst", "--arrangement", "B"], "from --arrangement")])
    def test_arrangement_not_a(self, runner, data, confirmed_winkel, tmp_path, args, source):
        r = runner.invoke(cli, ["map", "build"] + args + ["--template", "winkel-tripel", "-o", str(tmp_path / "x.json")])
        assert r.exit_code == 1
        assert "the frames of a curved map cannot be re-hung" in r.output and source in r.output
        assert _last(r.output) == DISCLAIMER

    def test_enso_with_explicit_a_builds(self, runner, data, confirmed_winkel, tmp_path):
        r = runner.invoke(cli, ["map", "build", "ocean-el-nino", "--template", "winkel-tripel", "--arrangement", "A",
                                "-o", str(tmp_path / "x.json")])
        assert r.exit_code == 0, r.output

    def test_official_design(self, runner, confirmed_winkel, tmp_path):
        r = runner.invoke(cli, ["map", "build", "official-31203", "--template", "winkel-tripel",
                                "-o", str(tmp_path / "x.json")])
        assert r.exit_code == 1
        assert "kit31203-design" in r.output and "official-31203-bathymetry" in r.output
        assert _last(r.output) == DISCLAIMER

    @pytest.mark.parametrize("args,where", [
        (["--margin-color", "lego_vibrant_coral"], "--margin-color"),
        (["--ring-color", "lego_vibrant_coral"], "--ring-color"),
    ])
    def test_margin_color_not_a_square_tile_color(self, runner, confirmed_winkel, tmp_path, args, where):
        r = runner.invoke(cli, ["map", "build", "ocean-sst", "--template", "winkel-tripel",
                                "-o", str(tmp_path / "x.json")] + args)
        assert r.exit_code == 1
        assert where in r.output and "lego_vibrant_coral" in r.output and "part 3070b" in r.output
        assert "lego_black" in r.output and "kit part-colors --part 3070b" in r.output
        assert _last(r.output) == DISCLAIMER

    def test_ring_equal_to_margin(self, runner, confirmed_winkel, tmp_path):
        r = runner.invoke(cli, ["map", "build", "ocean-sst", "--template", "winkel-tripel", "-o", str(tmp_path / "x.json"),
                                "--margin-color", "lego_black", "--ring-color", "lego_black"])
        assert r.exit_code == 1
        assert "--ring-color" in r.output and "differ" in r.output
        # T111: the available 3070b color keys and where to see them (contracts/cli.md errors)
        assert "lego_white" in r.output and "kit part-colors --part 3070b" in r.output
        assert not (tmp_path / "x.json").exists()
        assert _last(r.output) == DISCLAIMER

    def test_recipe_ring_equal_to_margin(self, runner, tmp_path):
        f = _recipe_file(tmp_path, "ocean-sst", extra_table='[margin]\nring = "lego_black"\n')
        r = runner.invoke(cli, ["map", "build", str(f), "-o", str(tmp_path / "x.json")])
        assert r.exit_code == 1
        assert "margin.ring" in r.output and "differ" in r.output
        assert "lego_white" in r.output and "kit part-colors --part 3070b" in r.output
        assert _last(r.output) == DISCLAIMER

    def test_recipe_margin_color(self, runner, tmp_path):
        f = _recipe_file(tmp_path, "ocean-sst", extra_table='[margin]\ncolor = "lego_vibrant_coral"\n')
        r = runner.invoke(cli, ["map", "build", str(f), "-o", str(tmp_path / "x.json")])
        assert r.exit_code == 1
        assert "margin.color" in r.output and "kit part-colors --part 3070b" in r.output
        assert _last(r.output) == DISCLAIMER

    def test_compare_official_on_a_template(self, runner, data, confirmed_winkel, tmp_path):
        r = runner.invoke(cli, ["map", "build", "official-31203-bathymetry", "--template", "winkel-tripel",
                                "--compare-official", "-o", str(tmp_path / "x.json")])
        assert r.exit_code == 1
        assert "kit grid" in r.output and _last(r.output) == DISCLAIMER

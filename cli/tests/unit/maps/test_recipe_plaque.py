"""In-margin plaque: the choice of corner (feature 017 T061; FR-021; research R15 and decision E2;
contracts/cli.md "map build, map check, map cells"; data-model.md InMarginPlaque.corner and
InMarginPlaque.source).

The recipe key ``plaque`` in 016's ``[margin]`` table names a corner; ``--plaque`` on ``map build``,
``map check`` and ``map cells`` wins over it, and ``none`` turns a recipe's plaque off. On the kit
template ``--plaque CORNER`` is an error (exit 1), while a recipe's ``[margin].plaque`` is ignored
with 016's margin note. Offline, on the dataset fixtures and ``confirmed_winkel``.
Not affiliated with or endorsed by The LEGO Group.
"""

import json

import pytest
from click.testing import CliRunner

from lego_image_processor.cli.main import cli
from lego_image_processor.cli.map import KIT_MARGIN_NOTE
from lego_image_processor.maps.margin import (NO_PLAQUE, PLAQUE_CORNERS, MarginError, MarginTreatment,
                                              resolve_margin)
from lego_image_processor.maps.recipe import RecipeError, bundled_recipes, load_recipe, parse_recipe

CORNERS = ("top-left", "top-right", "bottom-left", "bottom-right")
RULE = "must be one of top-left, top-right, bottom-left, bottom-right"
DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
COMMANDS = ("build", "check", "cells")


def _text(rid="ocean-sst", top="", tables=""):
    text = bundled_recipes()[rid].read_text(encoding="utf-8")
    if top:
        text = text.replace("seed = 31203\n", f"seed = 31203\n{top}\n", 1)
    return text + ("\n" + tables if tables else "")


def _recipe(tables="", top=""):
    return parse_recipe(_text(top=top, tables=tables))


def _error(tables):
    with pytest.raises(RecipeError) as e:
        _recipe(tables)
    return e.value


def _args(cmd, out, *extra):
    """``map <cmd> <recipe> [-o out] extra...`` (``map check`` writes no layout)."""
    head = ["map", cmd]
    tail = [] if cmd == "check" else ["-o", str(out)]
    return head, tail, list(extra)


def _invoke(cmd, recipe, out, *extra):
    head, tail, more = _args(cmd, out, *extra)
    return CliRunner().invoke(cli, head + [str(recipe)] + tail + more)


class TestRecipeKey:
    def test_corner_names(self):
        assert PLAQUE_CORNERS == CORNERS and NO_PLAQUE == "none"

    @pytest.mark.parametrize("corner", CORNERS)
    def test_four_corners(self, corner):
        m = _recipe(f'[margin]\nplaque = "{corner}"\n').margin
        assert (m.plaque, m.plaque_source) == (corner, "recipe")
        assert (m.color, m.ring) == ("lego_black", None)  # 016's defaults are kept

    def test_with_margin_colors(self):
        m = _recipe('[margin]\ncolor = "lego_dark_stone_grey"\nring = "lego_bright_yellow"\n'
                    'plaque = "bottom-left"\n').margin
        assert m == MarginTreatment("lego_dark_stone_grey", "lego_bright_yellow", "bottom-left", "recipe")

    def test_margin_without_a_plaque(self):
        m = _recipe('[margin]\ncolor = "lego_black"\n').margin
        assert (m.plaque, m.plaque_source) == (None, None)
        assert m == MarginTreatment("lego_black", None)  # 016's treatment, unchanged

    @pytest.mark.parametrize("value", ['"centre"', '"none"', '"Bottom Left"', "3", "true"])
    def test_unknown_corner(self, value):
        e = _error(f"[margin]\nplaque = {value}\n")
        assert e.path == "margin.plaque" and e.rule == RULE

    def test_unknown_margin_key_lists_plaque(self):
        e = _error('[margin]\nlabel = "World"\n')
        assert e.path == "margin.label" and "color, plaque, ring" in e.rule

    def test_no_bundled_recipe_names_a_corner(self):
        for rid in bundled_recipes():
            m = load_recipe(rid).margin
            assert m is None or m.plaque is None, rid


class TestResolve:
    RECIPE = MarginTreatment("lego_black", None, "top-left", "recipe")

    def test_recipe_corner_is_kept(self):
        assert resolve_margin(self.RECIPE) == self.RECIPE

    def test_option_wins(self):
        got = resolve_margin(self.RECIPE, plaque="bottom-right")
        assert (got.plaque, got.plaque_source) == ("bottom-right", "option")

    def test_option_alone(self):
        assert resolve_margin(None, plaque="bottom-left") == MarginTreatment("lego_black", None, "bottom-left",
                                                                             "option")

    def test_none_turns_a_recipe_plaque_off(self):
        got = resolve_margin(self.RECIPE, plaque="none")
        assert (got.plaque, got.plaque_source) == (None, None)
        assert got == MarginTreatment("lego_black", None)

    def test_colors_still_resolve_per_field(self):
        got = resolve_margin(self.RECIPE, margin_color="lego_white", ring_color="lego_bright_yellow")
        assert got == MarginTreatment("lego_white", "lego_bright_yellow", "top-left", "recipe")

    def test_unknown_corner_from_the_library(self):
        with pytest.raises(MarginError) as e:
            resolve_margin(None, plaque="middle")
        assert e.value.where == "--plaque" and RULE in str(e.value)


@pytest.fixture
def data(fixture_registry):
    return fixture_registry.place_all()


class TestOption:
    @pytest.mark.parametrize("cmd", COMMANDS)
    def test_help(self, cmd):
        r = CliRunner().invoke(cli, ["map", cmd, "--help"])
        assert r.exit_code == 0 and "--plaque" in r.output
        for c in CORNERS:
            assert c in r.output

    @pytest.mark.parametrize("cmd", COMMANDS)
    def test_unknown_corner_exit_2(self, cmd, tmp_path):
        r = _invoke(cmd, "ocean-sst", tmp_path / "x.json", "--plaque", "middle")
        assert r.exit_code == 2
        for c in CORNERS:
            assert c in r.output
        assert not (tmp_path / "x.json").exists()

    @pytest.mark.parametrize("cmd", COMMANDS)
    @pytest.mark.parametrize("template", [None, "kit-31203"])
    def test_corner_on_the_kit_exit_1(self, cmd, template, data, confirmed_winkel, tmp_path):  # E2
        out = tmp_path / "k.json"
        extra = ["--plaque", "bottom-left"] + (["--template", template] if template else [])
        r = _invoke(cmd, "ocean-sst", out, *extra)
        assert r.exit_code == 1, r.output
        assert "the kit template has no margin" in r.output
        assert "--plaque" in r.output and "winkel-tripel" in r.output  # the templates with a margin
        assert r.output.rstrip("\n").splitlines()[-1] == DISCLAIMER
        assert not out.exists()

    @pytest.mark.parametrize("cmd", COMMANDS)
    def test_recipe_corner_on_the_kit_builds_with_016s_note(self, cmd, data, tmp_path):  # E2
        recipe = tmp_path / "ocean-sst.toml"
        recipe.write_text(_text(tables='[margin]\nplaque = "bottom-left"\n'), encoding="utf-8")
        out = tmp_path / "k.json"
        r = _invoke(cmd, recipe, out)
        assert r.exit_code == 0, r.output
        assert KIT_MARGIN_NOTE in r.output.splitlines()
        if cmd == "build":
            d = json.loads(out.read_text())
            assert "plaque" not in d["metadata"] and len(d["positions"]) == 10240
            assert "plaque_tile_count" not in d["statistics"]

    def test_none_on_the_kit_builds(self, data, tmp_path):
        out = tmp_path / "k.json"
        r = _invoke("build", "ocean-sst", out, "--plaque", "none")
        assert r.exit_code == 0, r.output
        assert "plaque" not in json.loads(out.read_text())["metadata"]


class TestOptionOnTheTemplate:
    """The option wins over the recipe, ``none`` turns it off; ``source`` says which (US3-6)."""

    @pytest.fixture
    def recipe(self, tmp_path):
        p = tmp_path / "ocean-sst.toml"
        p.write_text(_text(top='template = "winkel-tripel"', tables='[margin]\nplaque = "top-left"\n'),
                     encoding="utf-8")
        return p

    @pytest.mark.parametrize("extra,want", [
        ((), ("top-left", "recipe")),
        (("--plaque", "bottom-right"), ("bottom-right", "option")),
        (("--plaque", "none"), None),
    ])
    @pytest.mark.parametrize("cmd", ["build", "check"])
    def test_source(self, cmd, extra, want, recipe, data, confirmed_winkel, tmp_path):
        rep = tmp_path / "r.json"
        r = _invoke(cmd, recipe, tmp_path / "w.json", "--report", str(rep), *extra)
        assert r.exit_code == 0, r.output
        plaque = json.loads(rep.read_text())["margin"].get("plaque")
        if want is None:
            assert plaque is None
        else:
            assert (plaque["corner"], plaque["source"]) == want

    def test_option_without_a_recipe_key(self, data, confirmed_winkel, tmp_path):
        rep = tmp_path / "r.json"
        r = _invoke("build", "ocean-sst", tmp_path / "w.json", "--template", "winkel-tripel",
                    "--plaque", "bottom-left", "--report", str(rep))
        assert r.exit_code == 0, r.output
        plaque = json.loads(rep.read_text())["margin"]["plaque"]
        assert (plaque["corner"], plaque["source"]) == ("bottom-left", "option")

    def test_cells_takes_none(self, recipe, data, confirmed_winkel, tmp_path):
        r = _invoke("cells", recipe, tmp_path / "c.json", "--plaque", "none")
        assert r.exit_code == 0, r.output

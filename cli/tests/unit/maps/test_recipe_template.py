"""Recipe keys of feature 016 (T040; contracts/recipe-and-outputs.md "Recipe"; data-model.md
MarginTreatment.color, MarginTreatment.ring): an optional top-level ``template`` and an optional
``[margin]`` table. Both are additive: every bundled recipe parses as before.
Not affiliated with or endorsed by The LEGO Group.
"""

import pytest

from lego_image_processor.maps.margin import DEFAULT_MARGIN_COLOR, MarginTreatment, margin_colors
from lego_image_processor.maps.recipe import (RecipeError, bundled_recipes, load_recipe,
                                              parse_recipe)

BASE = """
format = "1"
id = "bg-map"
title = "Background"
{top}

[land]
role = "background"
colors = ["lego_white"]
weights = [1]

[ocean]
role = "background"
colors = ["lego_medium_azur"]
weights = [1]
{tables}
"""


def _recipe(top="", tables=""):
    return parse_recipe(BASE.format(top=top, tables=tables))


def _error(top="", tables=""):
    with pytest.raises(RecipeError) as e:
        _recipe(top, tables)
    return e.value


class TestTemplateKey:
    def test_absent_is_none(self):
        assert _recipe().template is None

    def test_kit_id(self):
        assert _recipe('template = "kit-31203"').template == "kit-31203"

    def test_unconfirmed_template_parses(self, unconfirmed_winkel):
        # an unconfirmed template parses, but does not build
        assert _recipe('template = "winkel-tripel"').template == "winkel-tripel"

    def test_confirmed_template_parses(self, confirmed_winkel):
        assert _recipe('template = "winkel-tripel"').template == "winkel-tripel"

    def test_unknown_names_confirmed_templates(self, unconfirmed_winkel):
        e = _error('template = "mercator"')
        assert e.path == "template"
        assert "'mercator'" in e.rule and "confirmed templates: kit-31203" in e.rule
        assert "winkel-tripel" not in e.rule  # an unconfirmed template is not listed

    def test_unknown_lists_a_confirmed_winkel(self, confirmed_winkel):
        e = _error('template = "mercator"')
        assert e.path == "template" and "kit-31203, winkel-tripel" in e.rule

    @pytest.mark.parametrize("value", ["1", "true", '["winkel-tripel"]', '""'])
    def test_not_a_string(self, value):
        assert _error(f"template = {value}").path == "template"


class TestMarginTable:
    def test_absent_is_none(self):
        assert _recipe().margin is None

    def test_defaults(self):
        m = _recipe(tables="[margin]\n").margin
        assert m == MarginTreatment(color=DEFAULT_MARGIN_COLOR, ring=None)
        assert DEFAULT_MARGIN_COLOR == "lego_black"

    def test_color_and_ring(self):
        m = _recipe(tables='[margin]\ncolor = "lego_dark_stone_grey"\nring = "lego_bright_yellow"\n').margin
        assert (m.color, m.ring) == ("lego_dark_stone_grey", "lego_bright_yellow")

    def test_unknown_key(self):
        e = _error(tables='[margin]\ncolor = "lego_black"\nlabel = "World"\n')
        assert e.path == "margin.label" and "unknown key" in e.rule and "color, ring" in e.rule

    def test_not_a_table(self):
        assert _error('margin = "lego_black"').path == "margin"

    @pytest.mark.parametrize("key", ["color", "ring"])
    def test_color_not_a_square_tile_color(self, key):
        e = _error(tables=f'[margin]\n{key} = "lego_vibrant_coral"\n')
        assert e.path == f"margin.{key}"
        assert "part 3070b" in e.rule and "kit part-colors --part 3070b" in e.rule
        assert "lego_black" in e.rule and "lego_white" in e.rule  # the available 3070b color keys

    @pytest.mark.parametrize("key", ["color", "ring"])
    def test_color_not_a_string(self, key):
        assert _error(tables=f"[margin]\n{key} = 3\n").path == f"margin.{key}"

    def test_ring_must_differ_from_color(self):
        e = _error(tables='[margin]\nring = "lego_black"\n')
        assert e.path == "margin.ring" and "differ" in e.rule
        # T111: as the not-a-3070b-color error, it lists the available colors (spec Edge Cases)
        assert "part 3070b" in e.rule and "kit part-colors --part 3070b" in e.rule
        for key in margin_colors():
            assert key in e.rule

    def test_margin_with_template(self, confirmed_winkel):
        r = _recipe('template = "winkel-tripel"', '[margin]\nring = "lego_white"\n')
        assert r.template == "winkel-tripel" and r.margin.ring == "lego_white"


@pytest.mark.parametrize("rid", sorted(bundled_recipes()))
def test_bundled_recipes_parse_as_before(rid):
    r = load_recipe(rid)
    assert r.template is None and r.margin is None
    assert r.id == rid

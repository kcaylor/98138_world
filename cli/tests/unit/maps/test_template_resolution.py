"""Template resolution and its errors (T044; FR-004, FR-006, FR-011; research R8;
contracts/cli.md errors table; pattern of test_build_arrangement_source.py).

Resolution: ``template`` argument (``--template``) > recipe ``template`` > ``kit-31203``. The report
records ``template_source`` only for non-kit builds. Not affiliated with or endorsed by The LEGO Group.
"""

import json

import pytest

from lego_image_processor.layout.arrangement import parse_arrangement
from lego_image_processor.maps.build import build_map, check_recipe, resolve_template
from lego_image_processor.maps.classify import MapBuildError
from lego_image_processor.maps.recipe import bundled_recipes, load_recipe, parse_recipe
from lego_image_processor.templates import KIT_TEMPLATE_ID, compatibility, load_template

BG = """
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
"""

ELIGIBLE = {"land-elevation", "living-planet", "ocean-sst", "official-31203-bathymetry", "rainfall"}


def _recipe(top=""):
    return parse_recipe(BG.format(top=top))


def _layout(result):
    d = json.loads(result.layout.to_json())
    d["metadata"].pop("generated_at", None)
    return d


class TestResolve:
    def test_default_is_the_kit(self):
        t, src = resolve_template(_recipe())
        assert (t.id, src) == (KIT_TEMPLATE_ID, "default")

    def test_recipe(self, confirmed_winkel):
        t, src = resolve_template(_recipe('template = "winkel-tripel"'))
        assert (t.id, src) == ("winkel-tripel", "recipe")

    def test_option_wins(self, confirmed_winkel):
        t, src = resolve_template(_recipe('template = "winkel-tripel"'), KIT_TEMPLATE_ID)
        assert (t.id, src) == (KIT_TEMPLATE_ID, "option")
        t, src = resolve_template(_recipe(), "winkel-tripel")
        assert (t.id, src) == ("winkel-tripel", "option")

    def test_template_object(self, confirmed_winkel):
        t, src = resolve_template(_recipe(), confirmed_winkel)
        assert t is confirmed_winkel and src == "option"

    def test_unknown_option(self):
        with pytest.raises(MapBuildError, match=r"unknown template 'mercator'.*confirmed templates: kit-31203"):
            resolve_template(_recipe(), "mercator")


class TestBuildSource:
    def test_option(self, confirmed_winkel):
        r = build_map(_recipe(), template="winkel-tripel")
        assert r.template.id == "winkel-tripel"
        assert r.report["template_source"] == "option" and r.report["template"]["id"] == "winkel-tripel"

    def test_recipe(self, confirmed_winkel):
        r = build_map(_recipe('template = "winkel-tripel"'))
        assert r.report["template_source"] == "recipe"
        assert r.layout.template["id"] == "winkel-tripel"

    def test_kit_reports_have_no_template_keys(self, confirmed_winkel):
        for r in (build_map(_recipe()), build_map(_recipe('template = "winkel-tripel"'), template=KIT_TEMPLATE_ID)):
            assert r.template.id == KIT_TEMPLATE_ID
            assert not {"template", "template_source", "margin"} & set(r.report)
            assert r.layout.template is None

    def test_option_kit_equals_default(self, confirmed_winkel):
        """US1-2, US1-3: --template kit-31203 builds exactly what a recipe without the key builds."""
        a, b = _layout(build_map(_recipe())), _layout(build_map(_recipe('template = "winkel-tripel"'),
                                                                 template=KIT_TEMPLATE_ID))
        assert a["positions"] == b["positions"] and a["statistics"] == b["statistics"]
        for d in (a, b):  # the recipe's own SHA-256 differs (it has the key); nothing else does
            d["metadata"]["map"]["recipe"].pop("sha256")
        assert a == b

    def test_check_recipe(self, confirmed_winkel):
        rep = check_recipe(_recipe(), template="winkel-tripel")
        assert rep["template"]["id"] == "winkel-tripel" and rep["template_source"] == "option"


class TestErrors:
    def test_unconfirmed(self, unconfirmed_winkel):
        """An unconfirmed template cannot be built on (FR-004); the package file is confirmed, so
        this runs on a copy without the confirmation."""
        for kw in ({"template": "winkel-tripel"}, {}):
            recipe = _recipe() if kw else _recipe('template = "winkel-tripel"')
            with pytest.raises(MapBuildError) as e:
                build_map(recipe, **kw)
            msg = str(e.value)
            assert "winkel-tripel" in msg and "not confirmed by the project owner" in msg
            assert "confirmed templates: kit-31203" in msg

    @pytest.mark.parametrize("top,kw,source", [
        ('arrangement = "B"', {}, "from the recipe"),
        ("", {"arrangement": parse_arrangement("C")}, "from --arrangement"),
    ])
    def test_arrangement_not_a(self, confirmed_winkel, top, kw, source):
        with pytest.raises(MapBuildError) as e:
            build_map(_recipe(top), template="winkel-tripel", **kw)
        msg = str(e.value)
        assert "the frames of a curved map cannot be re-hung" in msg and source in msg
        assert "winkel-tripel" in msg

    def test_enso_recipe_names_its_arrangement(self, confirmed_winkel):
        with pytest.raises(MapBuildError, match=r"cannot be re-hung.*arrangement D.*from the recipe"):
            build_map(load_recipe("ocean-el-nino"), template="winkel-tripel")

    def test_kit_design_dataset(self, confirmed_winkel):
        with pytest.raises(MapBuildError) as e:
            build_map(load_recipe("official-31203"), template="winkel-tripel")
        msg = str(e.value)
        assert "kit31203-design" in msg and "official-31203-bathymetry" in msg

    def test_compare_official_on_a_template(self, confirmed_winkel):
        with pytest.raises(MapBuildError, match=r"official .*design.*kit grid"):
            build_map(_recipe(), template="winkel-tripel", compare_official=True)

    def test_kit_builds_any_arrangement(self, confirmed_winkel):
        r = build_map(_recipe('arrangement = "B"'), template=KIT_TEMPLATE_ID)
        assert r.report["arrangement"]["id"] == "B"


class TestAllowed:
    def test_explicit_a_builds_an_enso_recipe(self, confirmed_winkel, fixture_registry):
        fixture_registry.place_all()
        r = build_map(load_recipe("ocean-el-nino"), template="winkel-tripel", arrangement=parse_arrangement("A"))
        assert r.report["arrangement"]["id"] == "A" and r.report["arrangement_source"] == "option"
        assert r.layout.template["id"] == "winkel-tripel"

    def test_bathymetry_comparison_off(self, confirmed_winkel, fixture_registry):
        fixture_registry.place_all()
        r = build_map(load_recipe("official-31203-bathymetry"), template="winkel-tripel")
        assert r.agreement is None and "agreement_with_official" not in r.report

    def test_a_template_build_records_arrangement_a(self, confirmed_winkel):
        r = build_map(_recipe(), template="winkel-tripel", arrangement=parse_arrangement("A"))
        assert r.layout.arrangement["id"] == "A"


class TestCompatibility:
    def test_five_eligible_maps(self, confirmed_winkel):
        """US3-1: of the 8 bundled recipes, exactly the five eligible maps can be built on Winkel."""
        ok = {rid for rid in bundled_recipes() if compatibility(load_recipe(rid), confirmed_winkel) is None}
        assert ok == ELIGIBLE

    def test_reasons(self, confirmed_winkel):
        assert "kit31203-design" in compatibility(load_recipe("official-31203"), confirmed_winkel)
        assert "re-hung" in compatibility(load_recipe("ocean-la-nina"), confirmed_winkel)
        assert compatibility(load_recipe("ocean-la-nina"), confirmed_winkel, parse_arrangement("A")) is None
        assert "re-hung" in compatibility(load_recipe("ocean-sst"), "winkel-tripel", parse_arrangement("B"))

    def test_kit_takes_every_recipe(self):
        assert all(compatibility(load_recipe(rid), KIT_TEMPLATE_ID) is None for rid in bundled_recipes())

    def test_unconfirmed_template(self, unconfirmed_winkel):
        t = load_template("winkel-tripel")
        assert t is unconfirmed_winkel or not t.buildable
        assert "not confirmed by the project owner" in compatibility(load_recipe("ocean-sst"), t)

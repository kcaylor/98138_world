"""Data credits (feature 017, T024): one credit per dataset the map uses, the large sticker's
"Data:" lines and the full citations kept for the print sheet (FR-007; research R9;
data-model.md Credit).

Not affiliated with or endorsed by The LEGO Group.
"""

import pytest

from lego_image_processor.datasets.registry import load_registry
from lego_image_processor.maps.recipe import bundled_recipes, load_recipe
from lego_image_processor.stickers.credits import Credit, credit_lines, credits_for
from tests.stickers_support import fallback_recipe, sticker_recipe

ERSST = "ersst-v5-ltm-1991-2020"


def _entry(dataset_id):
    return load_registry().get(dataset_id)


class TestOnePerDataset:
    @pytest.mark.parametrize("recipe_id", sorted(bundled_recipes()))
    def test_follows_recipe_datasets_in_order(self, recipe_id):
        r = load_recipe(recipe_id)
        got = credits_for(r)
        assert [c.dataset for c in got] == [e.id for e in r.datasets()]
        assert len({c.dataset for c in got}) == len(got)

    def test_living_planet_includes_the_land_from_mask(self):
        got = [c.dataset for c in credits_for(load_recipe("living-planet"))]
        assert got == ["mod17a3-npp-mean-2000-2015", "etopo2022-surface-10m",
                       "modis-aqua-chla-2013-2024"]

    def test_rainfall_override_dataset_and_shared_dataset_once(self):
        got = [c.dataset for c in credits_for(load_recipe("rainfall"))]
        assert got == ["gpcp-v23-ltm-1991-2020", "nsidc-cdr-v6-seaice-minimum-1991-2020"]
        texts = credit_lines(load_recipe("rainfall"), credits_for(load_recipe("rainfall")))
        assert any(t.startswith("GPCP v2.3") for t in texts)
        assert any("NSIDC" in t for t in texts)

    def test_template_dataset_last_and_once(self):
        r = load_recipe("ocean-sst")
        etopo = _entry("etopo2022-surface-10m")
        assert [c.dataset for c in credits_for(r, template_dataset=etopo)] == [ERSST, etopo.id]
        assert [c.dataset for c in credits_for(r, template_dataset=_entry(ERSST))] == [ERSST]


class TestCreditFields:
    def test_doi_text(self):
        (c,) = credits_for(load_recipe("ocean-sst"))
        e = _entry(ERSST)
        assert isinstance(c, Credit)
        assert c.text == f"{e.title}, doi:{e.doi}"
        assert c.text == ("NOAA ERSST v5 monthly long-term mean sea surface temperature, 1991-2020, "
                          "doi:10.1175/JCLI-D-16-0836.1")
        assert (c.dataset, c.version, c.title, c.doi, c.publisher) == (
            e.id, e.version, e.title, e.doi, e.publisher)
        assert (c.citation, c.license, c.acknowledgement) == (e.citation, e.license, e.acknowledgement)

    def test_publisher_text_without_a_doi(self):
        (c,) = credits_for(load_recipe("official-31203"))
        e = _entry("kit31203-design")
        assert not e.doi and c.doi is None
        assert c.text == f"{e.title}, {e.publisher}"

    def test_no_acknowledgement_is_none(self):
        (c,) = credits_for(load_recipe("land-elevation"))
        assert not _entry("etopo2022-surface-10m").acknowledgement and c.acknowledgement is None

    def test_to_dict(self):
        (c,) = credits_for(load_recipe("ocean-sst"))
        d = c.to_dict()
        assert list(d) == ["dataset", "version", "text", "title", "doi", "publisher", "citation",
                           "license", "acknowledgement"]
        (k,) = credits_for(load_recipe("official-31203"))
        d = k.to_dict()
        assert d["doi"] is None and "acknowledgement" not in d

    @pytest.mark.parametrize("recipe_id", sorted(bundled_recipes()))
    def test_every_bundled_credit_is_complete(self, recipe_id):
        for c in credits_for(load_recipe(recipe_id)):
            assert c.title and c.citation and c.license and c.version and c.publisher
            assert c.text.startswith(c.title + ", ")


class TestStickerCreditLine:
    def test_registry_lines_by_default(self):
        r = sticker_recipe("ocean-sst")
        assert r.sticker is not None and r.sticker.credit is None
        cs = credits_for(r)
        assert credit_lines(r, cs) == tuple(c.text for c in cs)

    def test_credit_replaces_only_the_large_sticker_lines(self):
        r = sticker_recipe("official-31203")
        assert r.sticker.credit
        cs = credits_for(r)
        assert credit_lines(r, cs) == (r.sticker.credit,)
        assert "Official" not in " ".join(credit_lines(r, cs))
        # the full credit list stays for the print sheet
        (c,) = cs
        e = _entry("kit31203-design")
        assert (c.dataset, c.title, c.citation, c.license) == (e.id, e.title, e.citation, e.license)

    def test_no_table_uses_the_registry_lines(self):
        r = fallback_recipe("official-31203")                   # the recipe without its table
        assert r.sticker is None
        cs = credits_for(r)
        assert credit_lines(r, cs) == (cs[0].text,)

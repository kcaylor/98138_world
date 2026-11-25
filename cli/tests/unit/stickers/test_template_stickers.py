"""Stickers on a template (feature 017, T055; FR-001, FR-025, SC-002; US3-4; research R14;
data-model.md StickerText resolved line, Credit, StickerSet.template; contracts/sticker-files.md).

Maps are built from the dataset fixtures (``fixture_registry``) on 016's ``confirmed_winkel``
(the package ``winkel-tripel``, confirmed by the project owner on 2026-11-24), for the five
bundled maps ``templates.compatibility`` allows on it. Expected values come from the loaded
template and the registry, never from examples. Kit sets are unchanged (test_compose.py,
test_print_sheet.py and the guards in tests/integration/test_stickers_outputs_unchanged.py).
Not affiliated with or endorsed by The LEGO Group.
"""

import dataclasses
import io
import json

import numpy as np
import pytest
from pypdf import PdfReader

from lego_image_processor.datasets.registry import load_registry
from lego_image_processor.maps.build import build_map
from lego_image_processor.maps.cells import derived_bounds, map_cells
from lego_image_processor.maps.recipe import RANK_METHODS, bundled_recipes, parse_recipe
from lego_image_processor.sheets.compose import template_line
from lego_image_processor.sheets.model import Text
from lego_image_processor.stickers import (KIT_TEMPLATE_ID, StickerError, print_sheet,
                                           render_sticker_json, render_sticker_pdf,
                                           render_sticker_svgs, sticker_set)
from lego_image_processor.stickers.credits import credit_lines, credits_for, template_dataset_entry
from lego_image_processor.stickers.render import svg_metadata
from lego_image_processor.stickers.text import display_step, resolve_text, round_to_step
from lego_image_processor.templates import (PACKAGED_REGISTRY, compatibility, kit_template,
                                            parse_template)
from tests.stickers_support import sticker_recipe

ELIGIBLE = ("land-elevation", "living-planet", "ocean-sst", "official-31203-bathymetry", "rainfall")
SUFFIX = " Winkel tripel projection."
PAPERS = ("letter", "a4")


@pytest.fixture
def build(fixture_registry, confirmed_winkel):
    fixture_registry.place_all()

    def _build(recipe, template=confirmed_winkel):
        if isinstance(recipe, str):
            recipe = sticker_recipe(recipe)
        return build_map(recipe, cache_dir=fixture_registry.cache_dir, compare_official=False,
                         template=template)
    return _build


def norm(text):
    return " ".join(text.split())


def joined(block):
    return " ".join(block.lines)


def flow_text(page, *tags):
    return norm(" ".join(i.text for i in page.items if isinstance(i, Text) and i.tag in tags))


def etopo(tpl):
    """The registry entry of the dataset that decided the template's land and ocean."""
    return load_registry(PACKAGED_REGISTRY).get(tpl.dataset.id)


def kit_line(recipe_id):
    return resolve_text(sticker_recipe(recipe_id)).line


# --- the template's projection title (016 has no accessor; T056 adds one) ----------------------

class TestProjectionTitle:
    def test_winkel(self, confirmed_winkel):
        assert confirmed_winkel.projection_title == "Winkel tripel"
        assert confirmed_winkel.projection["name"] == "winkel-tripel"

    def test_derived_from_the_projection_name_not_a_file_key(self, confirmed_winkel):
        doc = confirmed_winkel.document()
        assert "projection_title" not in doc and "projection_title" not in doc["projection"]
        assert "title" not in doc["projection"]

    def test_kit(self):
        assert kit_template().projection_title == "Equidistant cylindrical"


# --- which maps (FR-001: any recipe that builds on a confirmed template) -----------------------

def test_the_five_maps_016_allows(confirmed_winkel):
    allowed = tuple(sorted(rid for rid, path in bundled_recipes().items()
                           if compatibility(sticker_recipe(rid), confirmed_winkel) is None))
    assert allowed == ELIGIBLE


# --- every Winkel set (FR-025, SC-002) ---------------------------------------------------------

@pytest.mark.parametrize("recipe_id", ELIGIBLE)
class TestWinkelSet:
    def test_line_ends_with_the_projection(self, build, recipe_id):
        s = sticker_set(build(recipe_id))
        base = kit_line(recipe_id)
        assert base.endswith(".") and not base.endswith(SUFFIX)
        assert s.text.line == base + SUFFIX
        assert s.text.line_source == resolve_text(sticker_recipe(recipe_id)).line_source
        assert s.text.title == resolve_text(sticker_recipe(recipe_id)).title
        for st in s.stickers:                          # both stickers carry the full line
            assert joined(st.block("line")) == s.text.line
        assert s.to_dict()["text"]["line"] == s.text.line

    def test_template_record(self, build, recipe_id, confirmed_winkel):
        s = sticker_set(build(recipe_id))
        want = {"id": confirmed_winkel.id, "title": confirmed_winkel.title,
                "projection": confirmed_winkel.projection_title,
                "dataset": confirmed_winkel.dataset.id}
        assert s.template.to_dict() == want
        d = json.loads(render_sticker_json(s))
        assert d["template"] == want and list(d["template"]) == ["id", "title", "projection", "dataset"]
        assert list(d)[:4] == ["format_version", "recipe", "template", "arrangement"]
        assert d["arrangement"] == "A"

    def test_credit_adds_the_template_dataset_once(self, build, recipe_id, confirmed_winkel):
        recipe = sticker_recipe(recipe_id)
        s = sticker_set(build(recipe))
        e = etopo(confirmed_winkel)
        ids = [x.id for x in recipe.datasets()]
        assert [c.dataset for c in s.credits] == ids + ([] if e.id in ids else [e.id])
        assert [c.dataset for c in s.credits].count(e.id) == 1
        (c,) = [c for c in s.credits if c.dataset == e.id]
        assert (c.title, c.doi, c.citation, c.license) == (e.title, e.doi, e.citation, e.license)
        assert s.credit_lines == tuple(x.text for x in s.credits)
        credit = joined(s.large.block("credit"))
        assert credit.startswith("Data: ") and credit.count(c.text) == 1

    def test_print_sheet_names_the_template(self, build, recipe_id, confirmed_winkel):
        s = sticker_set(build(recipe_id))
        line = template_line(confirmed_winkel.layout_record())
        assert line.startswith(f"Template: {confirmed_winkel.id} ({confirmed_winkel.title}), projection ")
        assert confirmed_winkel.file_sha256 in line and "confirmed by the project owner" in line
        for paper in PAPERS:
            page = print_sheet(s, paper).page
            prov = flow_text(page, "provenance")
            assert norm(line) in prov
            assert prov.index(f"Recipe {s.recipe.id}") < prov.index("Template: ")
            assert prov.index("Template: ") < prov.index("Made with lego-image-processor")
            data = flow_text(page, "citation")
            for c in s.credits:
                assert norm(c.citation) in data and norm(c.license) in data

    def test_fits_at_5_pt_or_more_on_letter_and_a4(self, build, recipe_id):
        s = sticker_set(build(recipe_id))
        for st in s.stickers:
            assert min(b.size_pt for b in st.blocks) >= 5.0
        for paper in PAPERS:
            page = print_sheet(s, paper).page
            assert all(t.size_pt >= 5.0 for t in page.items if isinstance(t, Text))
            pdf = render_sticker_pdf(s, paper)
            reader = PdfReader(io.BytesIO(pdf))
            text = norm(reader.pages[0].extract_text())
            assert len(reader.pages) == 1
            assert "Winkel tripel projection." in text and "Template: winkel-tripel" in text

    def test_svgs_carry_the_line_and_the_template(self, build, recipe_id, confirmed_winkel):
        s = sticker_set(build(recipe_id))
        meta = svg_metadata(s)
        assert template_line(confirmed_winkel.layout_record()) in meta
        assert meta.index("Recipe ") < meta.index("Template: ") < meta.index(" Data: ")
        for name, svg in render_sticker_svgs(s):
            assert "Winkel tripel" in svg and "projection." in svg, name
            assert etopo(confirmed_winkel).citation.split()[0] in svg

    def test_same_build_same_set(self, build, recipe_id):
        a, b = sticker_set(build(recipe_id)), sticker_set(build(recipe_id))
        assert a.to_dict() == b.to_dict()
        assert render_sticker_svgs(a) == render_sticker_svgs(b)
        assert render_sticker_pdf(a) == render_sticker_pdf(b)


# --- the legend is the template build's (land, ocean and shadow studs of the board) -----------

@pytest.mark.parametrize("recipe_id", ["official-31203-bathymetry", "ocean-sst"])
def test_rank_legend_from_the_template_studs(build, recipe_id):
    """Rank boundaries come from the template build's own ocean studs (016's ``map_cells`` kinds:
    ``O`` without the shadow ``S`` and the margin ``M``), not from the kit's land mask."""
    result = build(recipe_id)
    layer = next(l for l in result.recipe.layers if l.cls == "ocean")
    assert layer.classification.method in RANK_METHODS
    cells = map_cells(result)
    kinds = np.array(list(cells["cells"])).reshape(cells["height"], cells["width"])
    mask = kinds == "O"
    vals = result.fields["ocean"].values
    ok = mask & np.isfinite(vals)
    b = derived_bounds(vals[ok], result.classes["ocean"][ok], len(layer.colors))
    step = display_step(b[0], b[-1])
    want = [float(round_to_step(v, step)) for v in b]
    group = sticker_set(result).legend.group("ocean")
    ranges = [m.range for sw in group.swatches for m in sw.meanings if m.kind == "class"]
    assert [float(lo) for lo, _ in ranges] + [float(ranges[-1][1])] == want
    shadow = [m for sw in group.swatches for m in sw.meanings if m.kind == "shadow"]
    assert bool(shadow) == bool((kinds == "S").any())


def test_land_layer_reads_the_template_land(build, confirmed_winkel):
    """land-elevation's bins legend lists every class; its land studs are the template's."""
    result = build("land-elevation")
    s = sticker_set(result)
    land = s.legend.group("land")
    layer = next(l for l in result.recipe.layers if l.cls == "land")
    assert sum(len([m for m in sw.meanings if m.kind == "class"]) for sw in land.swatches) == \
        len(layer.colors)
    assert int(np.array(confirmed_winkel.land).sum()) == confirmed_winkel.counts["land"]


# --- texts and credits around the template -----------------------------------------------------

def test_line_without_a_full_stop_gets_one(build):
    text = bundled_recipes()["ocean-sst"].read_text(encoding="utf-8")
    base = kit_line("ocean-sst")
    recipe = parse_recipe(text.replace(f'line = "{base}"', 'line = "Sea surface temperature"'))
    assert recipe.sticker.line == "Sea surface temperature"
    s = sticker_set(build(recipe))
    assert s.text.line == "Sea surface temperature." + SUFFIX
    assert resolve_text(recipe).line == "Sea surface temperature"           # the kit's is as written


def test_sticker_credit_keeps_the_template_dataset(build, confirmed_winkel):
    """A recipe ``[sticker] credit`` replaces the large sticker's data lines; on a template the
    template's dataset is still credited (FR-025)."""
    text = bundled_recipes()["ocean-sst"].read_text(encoding="utf-8")
    recipe = parse_recipe(text + 'credit = "Sea surface temperature from NOAA ERSST v5."\n')
    assert recipe.sticker.credit
    s = sticker_set(build(recipe))
    e = etopo(confirmed_winkel)
    etopo_text = next(c.text for c in s.credits if c.dataset == e.id)
    assert s.credit_lines == (recipe.sticker.credit, etopo_text)
    assert credit_lines(recipe, s.credits, e.id) == s.credit_lines
    assert credit_lines(recipe, s.credits) == (recipe.sticker.credit,)   # the kit's rule
    assert joined(s.large.block("credit")).count(etopo_text) == 1


def test_template_dataset_entry(confirmed_winkel):
    e = template_dataset_entry(confirmed_winkel)
    assert e is not None and e.id == confirmed_winkel.dataset.id
    assert (e.version, e.title, e.citation, e.license, e.doi) == tuple(
        getattr(confirmed_winkel.dataset, k) for k in ("version", "title", "citation", "license", "doi"))
    assert template_dataset_entry(kit_template()) is None
    assert template_dataset_entry(None) is None
    r = sticker_recipe("ocean-sst")
    assert [c.dataset for c in credits_for(r, e)] == ["ersst-v5-ltm-1991-2020", e.id]


# --- only confirmed templates (016 FR-004) ------------------------------------------------------

def test_unconfirmed_template_is_refused(build, confirmed_winkel):
    """``build_map`` already refuses an unconfirmed template; a ``MapResult`` that names one
    anyway gets no sticker set."""
    result = build("ocean-sst")
    doc = confirmed_winkel.document()
    doc["confirmation"] = None
    unconfirmed = parse_template(doc, "winkel-tripel.json")
    assert not unconfirmed.buildable
    with pytest.raises(StickerError, match=r"winkel-tripel is not confirmed by the project owner"):
        sticker_set(dataclasses.replace(result, template=unconfirmed))


# --- kit sets unchanged -------------------------------------------------------------------------

def test_kit_set_has_no_projection_and_no_template_credit(fixture_registry):
    fixture_registry.place_all()
    result = build_map(sticker_recipe("ocean-sst"), cache_dir=fixture_registry.cache_dir,
                       compare_official=False)
    s = sticker_set(result)
    assert result.template.is_kit
    assert s.template.to_dict() == {"id": KIT_TEMPLATE_ID}
    assert s.text.line == kit_line("ocean-sst") and "projection" not in s.text.line
    assert [c.dataset for c in s.credits] == ["ersst-v5-ltm-1991-2020"]
    assert s.credit_lines == credit_lines(result.recipe, s.credits)
    for paper in PAPERS:
        assert "Template:" not in flow_text(print_sheet(s, paper).page, "provenance")
    assert "Template:" not in svg_metadata(s)

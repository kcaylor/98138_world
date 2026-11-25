"""Build sheets of maps built on the Winkel tripel template (feature 016 T066; US1-7, FR-015, SC-004;
data-model.md LegendRow, SectionCounts, SheetProvenance; research R16).

Runs on ``confirmed_winkel`` and the dataset fixtures; counts come from the loaded template.
Not affiliated with or endorsed by The LEGO Group.
"""

import json

import pytest

from lego_image_processor.kit.source import DISCLAIMER
from lego_image_processor.maps.build import build_map
from lego_image_processor.maps.recipe import load_recipe
from lego_image_processor.sheets import build_sheet_set, render_pdf, render_svg, section_counts
from lego_image_processor.sheets.model import Circle, Rect, Text


def _texts(page, tag=None):
    return [i.text for i in page.items if isinstance(i, Text) and (tag is None or i.tag == tag)]


@pytest.fixture
def built(confirmed_winkel, fixture_registry):
    fixture_registry.place_all()

    def build(rid):
        return build_map(load_recipe(rid), template="winkel-tripel").layout
    return build


def test_ocean_sst_sheets(built, confirmed_winkel):  # US1-7
    grid = built("ocean-sst")
    s = build_sheet_set(grid, layout_path="ocean-sst-winkel.json")
    c = confirmed_winkel.counts
    sections = [p for p in s.pages if p.kind == "section"]
    assert len(sections) == 40
    squares = sum(1 for p in sections for i in p.items if isinstance(i, Rect) and i.tag == "stud")
    rounds = sum(1 for p in sections for i in p.items if isinstance(i, Circle) and i.tag == "stud")
    assert (squares, rounds) == (c["margin"], c["land"] + c["ocean"])
    assert all(DISCLAIMER in _texts(p) for p in s.pages)
    # SC-004: the kit's 40 modules; plates and round tiles within one kit's supply
    assert c["land"] <= 3064 and c["ocean"] <= 8066
    overview = s.pages[0]
    prov = " ".join(_texts(overview, "provenance"))
    rec = grid.template
    assert "Template: winkel-tripel" in prov and rec["source"]["sha256"] in prov
    assert "Dataset ersst-v5-ltm-1991-2020" in prov
    for k in ("id", "version", "title", "license", "citation"):
        assert rec["dataset"][k] in prov
    assert "(more in the parts list JSON)" not in _texts(overview)
    pdf = render_pdf(s)
    assert pdf.startswith(b"%PDF") and len(pdf) > 10000
    svg = dict(render_svg(s))
    assert 'class="stud"' in svg["page-10.svg"] and "<rect" in svg["page-10.svg"]


def test_a4_sheets(built):
    s = build_sheet_set(built("ocean-sst"), paper="a4")
    assert [p.kind for p in s.pages].count("section") == 40
    assert "(more in the parts list JSON)" not in _texts(s.pages[0])


def test_template_dataset_listed_once_when_a_layer_reads_it(built):
    # land-elevation reads ETOPO 2022 itself: its dataset line is the one the template points to
    grid = built("land-elevation")
    s = build_sheet_set(grid)
    prov = " ".join(_texts(s.pages[0], "provenance"))
    ds = grid.template["dataset"]
    assert prov.count(ds["citation"]) == 1
    assert f"land and ocean from dataset {ds['id']} {ds['version']} (above)" in prov


def test_section_counts_include_square_tiles(built, confirmed_winkel):
    grid = built("ocean-sst")
    sc = section_counts(grid)
    d = json.loads(sc.to_json())
    assert d["template"] == {"id": "winkel-tripel", "title": confirmed_winkel.title}
    sq = [r["number"] for r in d["legend"] if r["part_type"] == "square_tile"]
    assert len(sq) == 1
    assert sum(s["counts"].get(str(sq[0]), 0) for s in d["sections"]) == confirmed_winkel.counts["margin"]
    assert all(s["total"] == 256 for s in d["sections"])

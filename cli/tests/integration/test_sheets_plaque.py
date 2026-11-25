"""Build sheets and section counts of a map with the in-margin plaque (feature 017 T074; US3-3,
FR-024; contracts/in-margin-plaque.md "Build sheets and counts").

``ocean-sst`` on ``confirmed_winkel`` and the dataset fixtures, with and without the plaque in the
bottom-left corner, read back from layout files as ``sheets build`` reads them. The tile's IDs come
from ``load_plaque_parts()``; counts from the loaded template.
Not affiliated with or endorsed by The LEGO Group.
"""

import json

import pytest

from lego_image_processor.kit.plaque_parts import load_plaque_parts
from lego_image_processor.kit.source import DISCLAIMER
from lego_image_processor.maps.build import build_map
from lego_image_processor.maps.margin import MarginTreatment
from lego_image_processor.maps.recipe import load_recipe
from lego_image_processor.parts import read_layout
from lego_image_processor.sheets import build_sheet_set, render_pdf, render_svg, section_counts
from lego_image_processor.sheets.model import Rect, Text


@pytest.fixture
def layouts(confirmed_winkel, fixture_registry, tmp_path):
    fixture_registry.place_all()
    out = {}
    for name, margin in (("plain", None),
                         ("plaque", MarginTreatment(plaque="bottom-left", plaque_source="option"))):
        result = build_map(load_recipe("ocean-sst"), template="winkel-tripel", margin=margin)
        p = tmp_path / f"{name}.json"
        p.write_text(result.layout.to_json(), encoding="utf-8")
        out[name] = read_layout(p)
    return out


@pytest.fixture
def tile():
    return load_plaque_parts().plaques["small"].tile


def _section(s, label):
    return next(p for p in s.pages if p.kind == "section" and p.label == label)


def test_a5_shows_the_plaque(layouts, tile):
    s = build_sheet_set(layouts["plaque"])
    (e,) = [e for e in s.legend if e.lot.part_type == "plaque_tile"]
    assert e is s.legend[-1] and e.lot.part_id == tile.part_id and e.lot.needed == 1
    page = _section(s, "A5")
    (r,) = [i for i in page.items if isinstance(i, Rect) and i.tag == "plaque"]
    assert r.fill == tuple(tile.color.rgb)
    labels = [i.text for i in page.items if isinstance(i, Text) and i.tag == "plaque-label"]
    assert labels == [f"tile {tile.studs[0]}x{tile.studs[1]} ({tile.part_id})"]
    assert all(DISCLAIMER in [i.text for i in p.items if isinstance(i, Text)] for p in s.pages)
    pdf = render_pdf(s)
    assert pdf.startswith(b"%PDF")
    svg = dict(render_svg(s))
    a5 = svg[f"page-{page.number:02d}.svg"]
    assert 'class="plaque"' in a5 and f"tile 6x6 ({tile.part_id})" in a5


def test_other_section_pages_equal_the_build_without_it(layouts):
    a, b = (build_sheet_set(layouts[k], layout_path="x.json") for k in ("plain", "plaque"))
    assert len(a.pages) == len(b.pages)
    pa = {p.label: p for p in a.pages if p.kind == "section"}
    pb = {p.label: p for p in b.pages if p.kind == "section"}
    assert [k for k in pa if pa[k] != pb[k]] == ["A5"]


def test_overview_totals(layouts, confirmed_winkel, tile):
    s = build_sheet_set(layouts["plaque"])
    totals = " ".join(i.text for i in s.pages[0].items if isinstance(i, Text) and i.tag == "totals")
    assert f"{confirmed_winkel.counts['margin'] - 36:,} tiles 1x1 square (margin, part 3070b), " \
           f"1 tile 6x6 (plaque, part {tile.part_id});" in totals
    assert totals.startswith("10,205 pieces:")
    assert len([i for i in s.pages[0].items if i.tag == "map-plaque"]) == 1


def test_section_counts_list_the_lot(layouts, tile):
    d = json.loads(section_counts(layouts["plaque"]).to_json())
    (row,) = [r for r in d["legend"] if r["part_type"] == "plaque_tile"]
    assert (row["part_id"], row["total"]) == (tile.part_id, 1)
    holding = [s["label"] for s in d["sections"] if str(row["number"]) in s["counts"]]
    assert holding == ["A5"]
    plain = json.loads(section_counts(layouts["plain"]).to_json())
    assert not [r for r in plain["legend"] if r["part_type"] == "plaque_tile"]
    assert all(s["total"] == 256 for s in plain["sections"])

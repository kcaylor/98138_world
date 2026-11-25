"""Parts lists and marketplace files of a map with the in-margin plaque (feature 017 T069; US3-2,
SC-009, FR-024; contracts/in-margin-plaque.md "Parts list JSON and exports").

``ocean-sst`` on ``confirmed_winkel`` and the dataset fixtures, with and without the plaque in the
bottom-left corner, read back from layout files as ``parts list`` reads them. Every ID is taken from
``load_plaque_parts()``; counts come from the loaded template.
Not affiliated with or endorsed by The LEGO Group.
"""

import json
import xml.etree.ElementTree as ET

import pytest

from lego_image_processor.kit.plaque_parts import load_plaque_parts
from lego_image_processor.maps.build import build_map
from lego_image_processor.maps.margin import MarginTreatment
from lego_image_processor.maps.recipe import load_recipe
from lego_image_processor.parts import (OwnedInputs, build_parts_list, read_layout, to_bricklink_xml,
                                        to_rebrickable_csv)


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


def _needed(pl):
    return {(l.part_id, l.color_key): l.needed for l in pl.lots}


def test_one_plaque_lot_after_the_square_tiles(layouts, tile, confirmed_winkel):  # US3-2
    pl = build_parts_list(layouts["plaque"], owned=OwnedInputs(kits=1))
    order = ["6141", "98138", "3070b", tile.part_id]
    assert [l.part_id for l in pl.lots] == sorted((l.part_id for l in pl.lots), key=order.index)
    plaque = [l for l in pl.lots if l.part_type == "plaque_tile"]
    assert len(plaque) == 1
    lot = plaque[0]
    assert lot is pl.lots[-1]
    assert (lot.part_id, lot.color_key, lot.needed, lot.kit_supply, lot.to_buy) == \
        (tile.part_id, tile.color.key, 1, 0, 1)
    assert (lot.ids.element_id, lot.ids.bricklink_item_no, lot.ids.bricklink_color_id,
            lot.ids.rebrickable_part_num, lot.ids.rebrickable_color_id) == \
        (tile.color.element_id, tile.numbers.bricklink_item_no, tile.color.bricklink.id,
         tile.numbers.rebrickable_part_num, tile.color.rebrickable.id)
    assert pl.totals()["unverified_lots"] == 0


def test_36_fewer_square_tiles_and_the_same_plates_and_round_tiles(layouts, tile, confirmed_winkel):
    plain, plaque = (build_parts_list(layouts[k]) for k in ("plain", "plaque"))
    a, b = _needed(plain), _needed(plaque)
    assert b.pop((tile.part_id, tile.color.key)) == 1
    sq = lambda d: sum(v for (p, _), v in d.items() if p == "3070b")  # noqa: E731
    assert sq(a) - sq(b) == 36 == tile.studs[0] * tile.studs[1]
    assert sq(b) == confirmed_winkel.counts["margin"] - 36
    assert {k: v for k, v in a.items() if k[0] != "3070b"} == {k: v for k, v in b.items() if k[0] != "3070b"}
    # SC-009: 10,204 one-stud pieces and one tile
    assert sum(b.values()) == 10204 == len(layouts["plaque"].grid.positions)
    assert plaque.totals()["needed"] == 10205


def test_leftovers_unchanged(layouts):
    a, b = (build_parts_list(layouts[k], owned=OwnedInputs(kits=1)) for k in ("plain", "plaque"))
    assert [l.to_dict() for l in a.leftovers] == [l.to_dict() for l in b.leftovers]
    assert {l.part_id for l in b.leftovers} == {"6141", "98138"}


def test_citations_include_the_plaque_sources(layouts, tile):
    pl = build_parts_list(layouts["plaque"])
    ids = [c["id"] for c in pl.citations]
    assert set(pl.lots[-1].ids.citation_ids) <= set(ids) and len(ids) == len(set(ids))
    assert tile.numbers.citations["bricklink"].id in ids
    plain = [c["id"] for c in build_parts_list(layouts["plain"]).citations]
    assert [c for c in ids if c in plain] == plain       # the plain list's citations, in order, plus the plaque's


def test_exports(layouts, tile, confirmed_winkel):
    pl = build_parts_list(layouts["plaque"], owned=OwnedInputs(kits=1))
    items = ET.fromstring(to_bricklink_xml(pl)).findall("ITEM")
    plaque = [i for i in items if i.findtext("ITEMID") == tile.numbers.bricklink_item_no]
    assert len(plaque) == 1 and items[-1] is plaque[0]
    assert (int(plaque[0].findtext("COLOR")), plaque[0].findtext("MINQTY")) == (tile.color.bricklink.id, "1")
    csv_rows = to_rebrickable_csv(pl).splitlines()
    assert csv_rows[-1] == f"{tile.numbers.rebrickable_part_num},{tile.color.rebrickable.id},1"
    assert sum(int(r.split(",")[2]) for r in csv_rows if r.startswith("3070b,")) == \
        confirmed_winkel.counts["margin"] - 36


def test_json_round_trip(layouts, tile):
    pl = build_parts_list(layouts["plaque"])
    d = json.loads(pl.to_json())
    row = d["lots"][-1]
    assert (row["part_id"], row["part_type"], row["bricklink"]["item_no"], row["rebrickable"]["part_num"]) == \
        (tile.part_id, "plaque_tile", tile.numbers.bricklink_item_no, tile.numbers.rebrickable_part_num)
    assert d["layout"]["template"]["id"] == "winkel-tripel"

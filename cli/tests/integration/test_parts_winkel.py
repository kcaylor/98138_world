"""Parts lists of maps built on the Winkel tripel template (feature 016 T061; US1-6, FR-014, SC-003;
data-model.md PartsListLot, PartsList; research R14).

Runs on ``confirmed_winkel`` and the dataset fixtures; counts come from the loaded template.
Not affiliated with or endorsed by The LEGO Group.
"""

import json

import pytest

from lego_image_processor.kit.part_numbers import load_part_numbers
from lego_image_processor.maps.build import build_map
from lego_image_processor.maps.margin import MarginTreatment
from lego_image_processor.maps.recipe import load_recipe
from lego_image_processor.parts import (OwnedInputs, build_parts_list, read_layout, to_bricklink_xml,
                                        to_rebrickable_csv)


@pytest.fixture
def sst_layout(confirmed_winkel, fixture_registry, tmp_path):
    fixture_registry.place_all()
    result = build_map(load_recipe("ocean-sst"), template="winkel-tripel",
                       margin=MarginTreatment(ring="lego_bright_yellow"))
    p = tmp_path / "ocean-sst-winkel.json"
    p.write_text(result.layout.to_json(), encoding="utf-8")
    return p


def test_complete_and_cited(sst_layout, confirmed_winkel):  # SC-003
    pl = build_parts_list(read_layout(sst_layout))
    t = pl.totals()
    assert t["needed"] == 10240 and t["unverified_lots"] == 0
    assert [l.part_id for l in pl.lots] == sorted((l.part_id for l in pl.lots),
                                                  key=["6141", "98138", "3070b"].index)
    c = confirmed_winkel.counts
    by_part = {p: sum(l.needed for l in pl.lots if l.part_id == p) for p in ("6141", "98138", "3070b")}
    assert by_part == {"6141": c["land"], "98138": c["ocean"], "3070b": c["margin"]}
    sq = {l.color_key: l.needed for l in pl.lots if l.part_id == "3070b"}
    assert sq == {"lego_bright_yellow": c["ring"], "lego_black": c["margin"] - c["ring"]}
    for l in pl.lots:
        assert l.ids is not None and l.ids.element_id and l.ids.bricklink_item_no
        assert l.ids.rebrickable_part_num == l.part_id or l.part_id == "6141"
    assert pl.layout["template"] == {"id": "winkel-tripel", "title": confirmed_winkel.title}


def test_one_kit_top_up_and_leftovers(sst_layout, confirmed_winkel):  # US1-6
    pl = build_parts_list(read_layout(sst_layout), owned=OwnedInputs(kits=1))
    for l in pl.lots:
        if l.part_id == "3070b":
            assert l.kit_supply == 0 and l.to_buy == l.needed
    assert {r.part_id for r in pl.leftovers} == {"6141", "98138"} and len(pl.leftovers) == 10
    used = {(r.part_id, r.color_key): r.used for r in pl.leftovers}
    for l in pl.lots:
        if l.part_id != "3070b" and (l.part_id, l.color_key) in used:
            assert used[(l.part_id, l.color_key)] == l.needed
    d = json.loads(pl.to_json())
    assert d["totals"]["leftover"] == sum(r["leftover"] for r in d["leftovers"])


def test_exports(sst_layout, confirmed_winkel):
    pl = build_parts_list(read_layout(sst_layout))
    item = load_part_numbers().get("3070b").bricklink_item_no
    xml = to_bricklink_xml(pl)
    assert xml.count(f"<ITEMID>{item}</ITEMID>") == 2
    csv_rows = [r for r in to_rebrickable_csv(pl).splitlines() if r.startswith("3070b,")]
    assert len(csv_rows) == 2
    assert sum(int(r.split(",")[2]) for r in csv_rows) == confirmed_winkel.counts["margin"]

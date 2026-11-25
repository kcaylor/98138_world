"""Plaque part data (feature 017 T011): ``kit/plaque_parts.py`` and ``data/plaque_parts.json``.

The loader re-checks rules 3 and 5-9 of contracts/plaque-parts-file.md; each fails on a mutated
copy of the packaged file with ``ValueError("plaque_parts.json: rule N: ...")``.
Not affiliated with or endorsed by The LEGO Group.
"""

import copy
import json

import pytest

from lego_image_processor.kit.inventory import INVENTORY_PATH
from lego_image_processor.kit.part_colors import PartColor
from lego_image_processor.kit.part_numbers import PartNumbers
from lego_image_processor.kit.plaque_parts import (PLAQUE_PARTS_PATH, Plaque, PlaquePart,
                                                   load_plaque_parts, parse_plaque_parts)
from lego_image_processor.kit.source import DISCLAIMER

PLAQUE_PARTS = ("10202", "3958", "4974", "92438")


@pytest.fixture()
def data():
    return json.loads(PLAQUE_PARTS_PATH.read_text(encoding="utf-8"))


def test_packaged_file_loads():
    table = load_plaque_parts()
    assert sorted(table.parts) == sorted(PLAQUE_PARTS)
    assert table.source["disclaimer"] == DISCLAIMER


def test_small_and_large_plaques():
    plaques = load_plaque_parts().plaques
    assert sorted(plaques) == ["large", "small"]
    small, large = plaques["small"], plaques["large"]
    assert isinstance(small, Plaque) and small.size == "small"
    assert (small.tile.part_id, small.plate.part_id, small.studs) == ("10202", "3958", (6, 6))
    assert large.size == "large"
    assert (large.tile.part_id, large.plate.part_id, large.studs) == ("4974", "92438", (16, 8))
    # the smooth (polished) 8 x 16 tile, chosen by the project owner on 2026-11-24 in place of the
    # textured 90498
    assert large.tile.name == "Tile 8 x 16 with Bottom Tubes, Polished Surface"
    for p in (small, large):
        assert p.tile.kind == "tile" and p.plate.kind == "plate"
        assert p.tile.studs == p.plate.studs == p.studs


def test_parts_carry_part_numbers_and_part_colors():
    table = load_plaque_parts()
    expected_elements = {"10202": "6155125", "3958": "395826", "4974": "6484420", "92438": "6094066"}
    for part_id, element_id in expected_elements.items():
        part = table.parts[part_id]
        assert isinstance(part, PlaquePart) and part.part_id == part_id
        assert isinstance(part.numbers, PartNumbers) and isinstance(part.color, PartColor)
        assert part.numbers.part_id == part_id and part.numbers.rebrickable_part_num == part_id
        assert part.numbers.bricklink_item_type == "P"
        assert part_id == part.numbers.bricklink_item_no or part_id in part.numbers.bricklink_alternates
        assert part.numbers.bricklink_colors and "Black" in part.numbers.bricklink_colors
        assert part.name == part.numbers.name and part.name
        assert set(part.numbers.citations) == {"bricklink", "rebrickable"}
        c = part.color
        assert c.key == "lego_black" and c.part_id == part_id and not c.in_kit
        assert c.element_id == element_id and element_id in c.element_ids
        assert (c.lego.name, c.lego.id) == ("Black", 26)
        assert (c.bricklink.name, c.bricklink.id) == ("Black", 11)
        assert (c.rebrickable.name, c.rebrickable.id) == ("Black", 0)
        assert set(c.citations) == {"lego", "bricklink", "rebrickable", "element"}
    assert load_plaque_parts().plaques["small"].tile.color.element_id == "6155125"


def test_no_plaque_part_is_in_the_kit_inventory():
    inv = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    kit_parts = {p for e in inv["elements"] for p in e["part_ids"]} | \
        {e["design_id"] for e in inv["elements"] if e.get("design_id")}
    kit_elements = {e["element_id"] for e in inv["elements"]}
    table = load_plaque_parts()
    for part in table.parts.values():
        assert part.part_id not in kit_parts
        assert not set(part.color.element_ids) & kit_elements


def test_citations_resolve_to_pinned_snapshots():
    table = load_plaque_parts()
    ids = {s.id for s in table.snapshots}
    for part in table.parts.values():
        assert {p.id for p in part.numbers.citations.values()} <= ids
        assert {c.id for c in part.color.citations.values()} <= ids
    assert all(len(s.sha256) == 64 for s in table.snapshots)
    # the four archived BrickLink pages are pinned in the Internet Archive raw (id_) form
    pages = {s.id: s for s in table.snapshots if s.id.startswith("bricklink-")}
    assert sorted(pages) == sorted(f"bricklink-{p}" for p in PLAQUE_PARTS)
    for s in pages.values():
        assert s.url.startswith("http://web.archive.org/web/") and "id_/https://www.bricklink.com/" in s.url


def test_disclaimers(data):
    assert data["source"]["disclaimer"] == DISCLAIMER and data["disclaimer"] == DISCLAIMER


def _mutate(data, path, value):
    d = copy.deepcopy(data)
    node = d
    for k in path[:-1]:
        node = node[k]
    if value is _DELETE:
        del node[path[-1]]
    else:
        node[path[-1]] = value
    return d


_DELETE = object()


@pytest.mark.parametrize("rule,path,value", [
    # 3: Rebrickable part_num equals the part ID
    (3, ("parts", "10202", "rebrickable", "part_num"), "10202b"),
    # 5: the part ID is the BrickLink item number or an alternate
    (5, ("parts", "3958", "bricklink", "item_no"), "3959"),
    # 6: BrickLink's colors list Black (BrickLink id 11)
    (6, ("parts", "4974", "bricklink", "colors"), ["White"]),
    (6, ("parts", "4974", "color", "bricklink", "id"), 12),
    # 7: not in the kit; tile and plate of one plaque share the studs; kind matches the slot
    (7, ("parts", "92438", "studs"), [8, 16]),
    (7, ("parts", "10202", "kind"), "plate"),
    (7, ("plaques", "large", "studs"), [8, 8]),
    # 8: citations resolve; SHA-256s are 64 hex characters; dates are YYYY-MM-DD
    (8, ("parts", "10202", "bricklink", "citation"), "bricklink-9999"),
    (8, ("parts", "3958", "color", "citations", "element"), "elements"),
    (8, ("source", "snapshots", 0, "sha256"), "abc"),
    (8, ("source", "snapshots", 4, "accessed"), "24.11.2026"),
    (8, ("source", "generated_on"), "2026/11/24"),
    # 9: only the color key lego_black; both disclaimers present
    (9, ("parts", "92438", "color", "key"), "lego_white"),
    (9, ("source", "disclaimer"), _DELETE),
    (9, ("disclaimer",), "Not affiliated."),
])
def test_loader_rules_fail_on_mutated_copy(data, rule, path, value):
    with pytest.raises(ValueError, match=rf"^plaque_parts\.json: rule {rule}: "):
        parse_plaque_parts(_mutate(data, path, value))


def test_loader_rule7_rejects_a_kit_part(data, monkeypatch):
    """A plaque part that is in the kit inventory fails rule 7 (a part ID from page 159)."""
    inv = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    kit_part = next(e for e in inv["elements"] if e["role"] == "frame_other")["part_ids"][0]
    d = copy.deepcopy(data)
    row = d["parts"].pop("3958")
    row["rebrickable"]["part_num"] = kit_part
    row["bricklink"]["item_no"] = kit_part
    d["parts"][kit_part] = row
    d["plaques"]["small"]["plate"] = kit_part
    with pytest.raises(ValueError, match=r"^plaque_parts\.json: rule 7: .*kit"):
        parse_plaque_parts(d)


def test_unmutated_copy_parses(data):
    assert sorted(parse_plaque_parts(copy.deepcopy(data)).plaques) == ["large", "small"]

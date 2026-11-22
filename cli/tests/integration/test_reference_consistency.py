"""Cross-file consistency of the shipped kit reference data (data-model.md rules 1-5, FR-023)."""

import json

import pytest

from lego_image_processor.kit import load_kit_colors, load_kit_inventory, load_official_design
from lego_image_processor.kit.colors import DATA_DIR
from lego_image_processor.kit.source import PINNED_SHA256
from lego_image_processor.layout.land_sea_mask import load_land_sea_mask
from lego_image_processor.palette.loader import LegoPalette

FILES = ["kit_colors.json", "kit_31203_inventory.json", "kit_31203_design.json",
         "lego_world_map_land_sea_mask.json", "kit_31203_mask_changes.json"]


@pytest.fixture(scope="module")
def colors():
    return load_kit_colors()


@pytest.fixture(scope="module")
def inventory():
    return load_kit_inventory()


@pytest.fixture(scope="module")
def design():
    return load_official_design()


def test_rule1_color_elements_in_inventory(colors, inventory):
    by_id = {e.element_id: e for e in inventory.elements}
    for c in colors:
        assert c.element_id in by_id, c.key
        e = by_id[c.element_id]
        assert e.color == c.lego.name
        assert e.role == c.role
        assert e.color_key == c.key


def test_rule2_design_counts_within_supply(colors, inventory, design):
    counts = {c.key: c for c in design.counts}
    assert set(counts) == {c.key for c in colors}
    for c in colors:
        used = sum(1 for y in range(80) for x in range(128) if design.color_at(x, y) == c.key)
        assert counts[c.key].used == used
        assert counts[c.key].supplied == inventory.supplied(c.key)
        assert used <= inventory.supplied(c.key), c.key


def test_rule3_mask_equals_design_white_cells(inventory, design):
    mask = load_land_sea_mask()
    white = design.land_positions()
    assert mask.land_count == len(white)
    assert {(x, y) for y in range(80) for x in range(128) if mask.is_land(x, y)} == white
    white_count = next(c for c in design.counts if c.key == "lego_white")
    assert mask.land_count == inventory.land_element().quantity - white_count.spare


def test_rule4_all_files_share_the_pdf_checksum():
    for name in FILES:
        data = json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
        assert data["source"]["sha256"] == PINNED_SHA256, name


def test_rule5_palette_contains_every_kit_color(colors):
    palette = LegoPalette.load_default()
    by_id = {c.id: c for c in palette.colors}
    for c in colors:
        assert c.lego.id in by_id, c.key
    rgbs = [tuple(by_id[c.lego.id].rgb) for c in colors]
    assert len(set(rgbs)) == len(rgbs)


def test_mask_change_record_matches(design):
    rec = json.loads((DATA_DIR / "kit_31203_mask_changes.json").read_text(encoding="utf-8"))
    assert rec["count"] == len(rec["changes"])
    assert len(rec["previous_mask_sha256"]) == 64


def test_cold_loaders_finish_under_100_ms():
    """plan.md Performance Goals: loading inventory, colors and design < 100 ms (T075)."""
    import time

    from lego_image_processor.kit import colors as colors_mod
    from lego_image_processor.kit import design as design_mod
    from lego_image_processor.kit import inventory as inventory_mod
    from lego_image_processor.kit import load_kit_colors, load_kit_inventory, load_official_design

    def clear():
        colors_mod.load_kit_color_table.cache_clear()
        inventory_mod._load.cache_clear()
        design_mod._load.cache_clear()

    clear()
    try:
        start = time.perf_counter()
        load_kit_inventory()
        load_kit_colors()
        load_official_design()
        elapsed_ms = (time.perf_counter() - start) * 1000
    finally:
        clear()
    assert elapsed_ms < 100, f"cold load took {elapsed_ms:.1f} ms"

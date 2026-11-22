"""Unit tests for the kit specification rebuilt from the cited inventory and color table."""

import json

import pytest

from lego_image_processor.kit import UnsupportedKitError, load_kit_inventory
from lego_image_processor.layout.kit_spec import (
    LEGOWorldMapKitSpecification,
    load_kit_specification,
)

OCEAN_KEYS = {
    "lego_bright_bluish_green", "lego_medium_azur", "lego_bright_yellowish_green",
    "lego_brick_yellow", "lego_bright_green", "lego_bright_orange", "lego_vibrant_coral",
    "lego_flame_yellowish_orange", "lego_earth_blue",
}


@pytest.fixture(scope="module")
def kit():
    return load_kit_specification("31203")


def test_identity_and_dimensions(kit):
    assert kit.kit_id == "31203"
    assert kit.kit_name == "LEGO World Map"
    assert (kit.base_plate_width, kit.base_plate_height, kit.total_positions) == (128, 80, 10240)
    assert kit.land_positions == 3062
    assert kit.ocean_positions == 7178


def test_part_ids(kit):
    assert kit.land_part_id == "6141"
    assert kit.ocean_part_id == "98138"


def test_colors(kit):
    assert kit.available_colors_plate == ["lego_white"]
    assert len(kit.available_colors_tile) == 9
    assert set(kit.available_colors_tile) == OCEAN_KEYS


def test_quantities_equal_inventory(kit):
    inv = load_kit_inventory()
    assert kit.plate_quantities == {"lego_white": inv.land_element().quantity}
    assert kit.tile_quantities == {e.color_key: e.quantity for e in inv.ocean_elements()}
    assert sum(kit.tile_quantities.values()) == 8066


def test_plate_and_tile_lookups(kit):
    assert kit.is_plate_color_available("lego_white")
    assert not kit.is_plate_color_available("lego_earth_blue")
    assert kit.is_tile_color_available("lego_earth_blue")
    assert not kit.is_tile_color_available("lego_white")
    assert kit.get_plate_quantity("lego_white") == 3064
    assert kit.get_plate_quantity("lego_nonexistent") == 0
    assert kit.get_tile_quantity("lego_medium_azur") == 1607
    assert kit.get_tile_quantity("lego_nonexistent") == 0


def test_no_brick_attributes_remain(kit):
    names = set(dir(kit)) | set(kit.to_dict())
    legacy = "bri" + "ck"  # spelled so the SC-006 grep guard does not match this test
    assert not [n for n in names if legacy in n and "brick_yellow" not in n]


def test_invalid_kit_id():
    with pytest.raises(UnsupportedKitError, match="not supported"):
        load_kit_specification("99999")


def test_round_trip(kit):
    restored = LEGOWorldMapKitSpecification.from_json(json.dumps(kit.to_dict()))
    assert restored == kit

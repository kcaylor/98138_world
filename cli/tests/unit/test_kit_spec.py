"""Unit tests for LEGOWorldMapKitSpecification class."""

import pytest

from lego_image_processor.layout.kit_spec import (
    LEGOWorldMapKitSpecification,
    load_kit_specification
)


class TestLEGOWorldMapKitSpecification:
    """Tests for LEGOWorldMapKitSpecification class."""

    def test_load_kit_specification(self):
        """Test loading kit specification from file."""
        kit = load_kit_specification("31203")
        assert kit is not None
        assert kit.kit_id == "31203"
        assert kit.kit_name == "LEGO World Map"

    def test_kit_dimensions(self):
        """Test kit has correct dimensions."""
        kit = load_kit_specification("31203")
        assert kit.base_plate_width == 128
        assert kit.base_plate_height == 80
        assert kit.total_positions == 10240
        assert kit.land_positions == 3062
        assert kit.ocean_positions == 7178

    def test_kit_part_ids(self):
        """Test kit has correct part IDs."""
        kit = load_kit_specification("31203")
        assert kit.land_part_id == "3062b"
        assert kit.ocean_part_id == "98138"

    def test_available_colors(self):
        """Test kit has available colors defined."""
        kit = load_kit_specification("31203")
        assert len(kit.available_colors_brick) > 0
        assert len(kit.available_colors_tile) > 0

    def test_is_brick_color_available(self):
        """Test checking brick color availability."""
        kit = load_kit_specification("31203")
        # This assumes lego_white is in the kit
        assert kit.is_brick_color_available("lego_white")
        # A made-up color should not be available
        assert not kit.is_brick_color_available("lego_nonexistent_color")

    def test_is_tile_color_available(self):
        """Test checking tile color availability."""
        kit = load_kit_specification("31203")
        # This assumes lego_white is in the kit
        assert kit.is_tile_color_available("lego_white")
        # A made-up color should not be available
        assert not kit.is_tile_color_available("lego_nonexistent_color")

    def test_get_brick_quantity(self):
        """Test getting brick quantity."""
        kit = load_kit_specification("31203")
        # White bricks should have some quantity
        assert kit.get_brick_quantity("lego_white") > 0
        # Nonexistent color should return 0
        assert kit.get_brick_quantity("lego_nonexistent") == 0

    def test_get_tile_quantity(self):
        """Test getting tile quantity."""
        kit = load_kit_specification("31203")
        # Some tile color should have quantity
        assert kit.get_tile_quantity("lego_medium_blue") > 0
        # Nonexistent color should return 0
        assert kit.get_tile_quantity("lego_nonexistent") == 0

    def test_invalid_kit_id(self):
        """Test loading invalid kit ID raises error."""
        with pytest.raises(ValueError, match="not supported"):
            load_kit_specification("99999")

    def test_to_dict(self):
        """Test converting kit spec to dictionary."""
        kit = load_kit_specification("31203")
        data = kit.to_dict()
        assert data["kit_id"] == "31203"
        assert data["base_plate_width"] == 128
        assert "available_colors_brick" in data
        assert "brick_quantities" in data

    def test_from_json(self):
        """Test creating kit spec from JSON."""
        import json
        kit = load_kit_specification("31203")
        json_str = json.dumps(kit.to_dict())
        restored = LEGOWorldMapKitSpecification.from_json(json_str)
        assert restored.kit_id == kit.kit_id
        assert restored.base_plate_width == kit.base_plate_width

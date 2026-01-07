"""Unit tests for PositionPlacement class."""

import pytest
from lego_image_processor.layout.position import PositionPlacement


class TestPositionPlacement:
    """Tests for PositionPlacement class."""

    def test_create_ocean_tile_position(self):
        """Test creating an ocean tile position."""
        pos = PositionPlacement(
            x=0,
            y=0,
            color_id="lego_blue_medium",
            color_name="Medium Blue",
            lego_color_code="102",
            part_type="tile",
            lego_part_id="98138"
        )
        assert pos.x == 0
        assert pos.y == 0
        assert pos.color_id == "lego_blue_medium"
        assert pos.color_name == "Medium Blue"
        assert pos.lego_color_code == "102"
        assert pos.part_type == "tile"
        assert pos.lego_part_id == "98138"

    def test_create_land_brick_position(self):
        """Test creating a land brick position."""
        pos = PositionPlacement(
            x=45,
            y=25,
            color_id="lego_green",
            color_name="Green",
            lego_color_code="28",
            part_type="brick",
            lego_part_id="3062b"
        )
        assert pos.x == 45
        assert pos.y == 25
        assert pos.color_id == "lego_green"
        assert pos.color_name == "Green"
        assert pos.lego_color_code == "28"
        assert pos.part_type == "brick"
        assert pos.lego_part_id == "3062b"

    def test_invalid_negative_x_coordinate(self):
        """Test that negative x coordinate raises ValueError."""
        with pytest.raises(ValueError, match="x coordinate must be >= 0"):
            PositionPlacement(
                x=-1,
                y=0,
                color_id="lego_blue_medium",
                color_name="Medium Blue",
                lego_color_code="102",
                part_type="tile",
                lego_part_id="98138"
            )

    def test_invalid_negative_y_coordinate(self):
        """Test that negative y coordinate raises ValueError."""
        with pytest.raises(ValueError, match="y coordinate must be >= 0"):
            PositionPlacement(
                x=0,
                y=-1,
                color_id="lego_blue_medium",
                color_name="Medium Blue",
                lego_color_code="102",
                part_type="tile",
                lego_part_id="98138"
            )

    def test_invalid_part_type(self):
        """Test that invalid part_type raises ValueError."""
        with pytest.raises(ValueError, match="part_type must be 'brick' or 'tile'"):
            PositionPlacement(
                x=0,
                y=0,
                color_id="lego_blue_medium",
                color_name="Medium Blue",
                lego_color_code="102",
                part_type="invalid",
                lego_part_id="98138"
            )

    def test_invalid_lego_part_id(self):
        """Test that invalid lego_part_id raises ValueError."""
        with pytest.raises(ValueError, match="lego_part_id must be '3062b' or '98138'"):
            PositionPlacement(
                x=0,
                y=0,
                color_id="lego_blue_medium",
                color_name="Medium Blue",
                lego_color_code="102",
                part_type="tile",
                lego_part_id="invalid"
            )

    def test_part_type_brick_requires_3062b(self):
        """Test that brick part_type must have 3062b part_id."""
        with pytest.raises(ValueError, match="part_type 'brick' must use lego_part_id '3062b'"):
            PositionPlacement(
                x=0,
                y=0,
                color_id="lego_green",
                color_name="Green",
                lego_color_code="28",
                part_type="brick",
                lego_part_id="98138"  # Wrong - bricks use 3062b
            )

    def test_part_type_tile_requires_98138(self):
        """Test that tile part_type must have 98138 part_id."""
        with pytest.raises(ValueError, match="part_type 'tile' must use lego_part_id '98138'"):
            PositionPlacement(
                x=0,
                y=0,
                color_id="lego_blue_medium",
                color_name="Medium Blue",
                lego_color_code="102",
                part_type="tile",
                lego_part_id="3062b"  # Wrong - tiles use 98138
            )

    def test_to_dict(self):
        """Test converting PositionPlacement to dictionary."""
        pos = PositionPlacement(
            x=10,
            y=20,
            color_id="lego_tan",
            color_name="Tan",
            lego_color_code="19",
            part_type="brick",
            lego_part_id="3062b"
        )
        result = pos.to_dict()
        assert result == {
            "x": 10,
            "y": 20,
            "color_id": "lego_tan",
            "color_name": "Tan",
            "lego_color_code": "19",
            "part_type": "brick",
            "lego_part_id": "3062b"
        }

    def test_from_dict(self):
        """Test creating PositionPlacement from dictionary."""
        data = {
            "x": 10,
            "y": 20,
            "color_id": "lego_tan",
            "color_name": "Tan",
            "lego_color_code": "19",
            "part_type": "brick",
            "lego_part_id": "3062b"
        }
        pos = PositionPlacement.from_dict(data)
        assert pos.x == 10
        assert pos.y == 20
        assert pos.color_id == "lego_tan"
        assert pos.color_name == "Tan"
        assert pos.lego_color_code == "19"
        assert pos.part_type == "brick"
        assert pos.lego_part_id == "3062b"

    def test_repr(self):
        """Test string representation."""
        pos = PositionPlacement(
            x=5,
            y=10,
            color_id="lego_green",
            color_name="Green",
            lego_color_code="28",
            part_type="brick",
            lego_part_id="3062b"
        )
        repr_str = repr(pos)
        assert "PositionPlacement" in repr_str
        assert "x=5" in repr_str
        assert "y=10" in repr_str
        assert "brick" in repr_str
        assert "3062b" in repr_str

    def test_equality(self):
        """Test equality comparison."""
        pos1 = PositionPlacement(
            x=0, y=0, color_id="lego_blue", color_name="Blue",
            lego_color_code="23", part_type="tile", lego_part_id="98138"
        )
        pos2 = PositionPlacement(
            x=0, y=0, color_id="lego_blue", color_name="Blue",
            lego_color_code="23", part_type="tile", lego_part_id="98138"
        )
        assert pos1 == pos2

    def test_inequality(self):
        """Test inequality comparison."""
        pos1 = PositionPlacement(
            x=0, y=0, color_id="lego_blue", color_name="Blue",
            lego_color_code="23", part_type="tile", lego_part_id="98138"
        )
        pos2 = PositionPlacement(
            x=1, y=0, color_id="lego_blue", color_name="Blue",
            lego_color_code="23", part_type="tile", lego_part_id="98138"
        )
        assert pos1 != pos2

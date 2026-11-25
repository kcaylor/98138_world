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

    def test_create_land_plate_position(self):
        """Test creating a land plate position."""
        pos = PositionPlacement(
            x=45,
            y=25,
            color_id="lego_green",
            color_name="Green",
            lego_color_code="28",
            part_type="plate",
            lego_part_id="6141"
        )
        assert pos.x == 45
        assert pos.y == 25
        assert pos.color_id == "lego_green"
        assert pos.color_name == "Green"
        assert pos.lego_color_code == "28"
        assert pos.part_type == "plate"
        assert pos.lego_part_id == "6141"

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
        with pytest.raises(ValueError, match="part_type must be 'plate', 'tile' or 'square_tile'"):
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
        with pytest.raises(ValueError, match="lego_part_id must be '6141', '98138' or '3070b'"):
            PositionPlacement(
                x=0,
                y=0,
                color_id="lego_blue_medium",
                color_name="Medium Blue",
                lego_color_code="102",
                part_type="tile",
                lego_part_id="invalid"
            )

    def test_part_type_plate_requires_6141(self):
        """Test that plate part_type must have 6141 part_id."""
        with pytest.raises(ValueError, match="part_type 'plate' must use lego_part_id '6141'"):
            PositionPlacement(
                x=0,
                y=0,
                color_id="lego_green",
                color_name="Green",
                lego_color_code="28",
                part_type="plate",
                lego_part_id="98138"  # Wrong - plates use 6141
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
                lego_part_id="6141"  # Wrong - tiles use 98138
            )

    def test_to_dict(self):
        """Test converting PositionPlacement to dictionary."""
        pos = PositionPlacement(
            x=10,
            y=20,
            color_id="lego_tan",
            color_name="Tan",
            lego_color_code="19",
            part_type="plate",
            lego_part_id="6141"
        )
        result = pos.to_dict()
        assert result == {
            "x": 10,
            "y": 20,
            "color_id": "lego_tan",
            "color_name": "Tan",
            "lego_color_code": "19",
            "part_type": "plate",
            "lego_part_id": "6141"
        }

    def test_from_dict(self):
        """Test creating PositionPlacement from dictionary."""
        data = {
            "x": 10,
            "y": 20,
            "color_id": "lego_tan",
            "color_name": "Tan",
            "lego_color_code": "19",
            "part_type": "plate",
            "lego_part_id": "6141"
        }
        pos = PositionPlacement.from_dict(data)
        assert pos.x == 10
        assert pos.y == 20
        assert pos.color_id == "lego_tan"
        assert pos.color_name == "Tan"
        assert pos.lego_color_code == "19"
        assert pos.part_type == "plate"
        assert pos.lego_part_id == "6141"

    def test_repr(self):
        """Test string representation."""
        pos = PositionPlacement(
            x=5,
            y=10,
            color_id="lego_green",
            color_name="Green",
            lego_color_code="28",
            part_type="plate",
            lego_part_id="6141"
        )
        repr_str = repr(pos)
        assert "PositionPlacement" in repr_str
        assert "x=5" in repr_str
        assert "y=10" in repr_str
        assert "plate" in repr_str
        assert "6141" in repr_str

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


class TestLandPartCorrection:
    """Land is the 1x1 round plate (6141); the old land part is rejected (FR-008)."""

    @pytest.mark.parametrize("part_type,part_id", [
        ("plate", "98138"), ("tile", "6141"), ("plate", "4073"), ("tile", "35381"),
        ("round", "6141"),
    ])
    def test_other_pairings_rejected(self, part_type, part_id):
        with pytest.raises(ValueError):
            PositionPlacement(x=0, y=0, color_id="lego_white", color_name="White",
                              lego_color_code="1", part_type=part_type, lego_part_id=part_id)

    def test_constants(self):
        from lego_image_processor.layout import position
        assert position.LAND_PART_TYPE == "plate"
        assert position.LAND_PART_ID == "6141"
        assert position.OCEAN_PART_TYPE == "tile"
        assert position.OCEAN_PART_ID == "98138"


class TestSquareTile:
    """Feature 016 (T052; FR-009, FR-010; research R11): margin studs of a non-kit template are the
    1x1 square tile, part type ``square_tile``, LEGO part 3070b."""

    def test_constants(self):
        from lego_image_processor.layout import position
        assert position.MARGIN_PART_TYPE == "square_tile"
        assert position.MARGIN_PART_ID == "3070b"
        assert position.PART_ID_FOR_TYPE == {"plate": "6141", "tile": "98138", "square_tile": "3070b"}

    def test_create_and_round_trip(self):
        pos = PositionPlacement(x=0, y=0, color_id="lego_black", color_name="Black", lego_color_code="26",
                                part_type="square_tile", lego_part_id="3070b")
        assert PositionPlacement.from_dict(pos.to_dict()) == pos
        assert pos.to_dict()["part_type"] == "square_tile" and pos.to_dict()["lego_part_id"] == "3070b"

    @pytest.mark.parametrize("part_type,part_id", [("square_tile", "98138"), ("square_tile", "6141"),
                                                   ("tile", "3070b"), ("plate", "3070b"),
                                                   ("square_tile", "3070")])
    def test_pairings_rejected(self, part_type, part_id):
        with pytest.raises(ValueError):
            PositionPlacement(x=0, y=0, color_id="lego_black", color_name="Black", lego_color_code="26",
                              part_type=part_type, lego_part_id=part_id)

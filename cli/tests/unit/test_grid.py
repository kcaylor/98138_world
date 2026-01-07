"""Unit tests for PositionPlacementGrid and LayoutStatistics classes."""

import json
import pytest
from datetime import datetime

from lego_image_processor.layout.position import PositionPlacement
from lego_image_processor.layout.grid import PositionPlacementGrid, LayoutStatistics


class TestLayoutStatistics:
    """Tests for LayoutStatistics class."""

    def test_create_statistics(self):
        """Test creating layout statistics."""
        stats = LayoutStatistics(
            total_tile_count=10240,
            land_brick_count=3062,
            ocean_tile_count=7178,
            unique_colors=12,
            color_frequency={"lego_blue_medium": 2400, "lego_green": 1850},
            color_frequency_by_part_type={
                "brick": {"lego_green": 1500},
                "tile": {"lego_blue_medium": 2400}
            },
            most_common_color={
                "color_id": "lego_blue_medium",
                "color_name": "Medium Blue",
                "count": 2400
            },
            coverage_percentage=100.0
        )
        assert stats.total_tile_count == 10240
        assert stats.land_brick_count == 3062
        assert stats.ocean_tile_count == 7178
        assert stats.unique_colors == 12
        assert stats.coverage_percentage == 100.0

    def test_to_dict(self):
        """Test converting statistics to dictionary."""
        stats = LayoutStatistics(
            total_tile_count=100,
            land_brick_count=30,
            ocean_tile_count=70,
            unique_colors=5,
            color_frequency={"lego_blue": 50, "lego_green": 30},
            color_frequency_by_part_type={
                "brick": {"lego_green": 30},
                "tile": {"lego_blue": 50}
            },
            most_common_color={
                "color_id": "lego_blue",
                "color_name": "Blue",
                "count": 50
            },
            coverage_percentage=100.0
        )
        result = stats.to_dict()
        assert result["total_tile_count"] == 100
        assert result["land_brick_count"] == 30
        assert result["ocean_tile_count"] == 70
        assert result["unique_colors"] == 5
        assert result["coverage_percentage"] == 100.0
        assert "lego_blue" in result["color_frequency"]


class TestPositionPlacementGrid:
    """Tests for PositionPlacementGrid class."""

    @pytest.fixture
    def sample_positions(self):
        """Create sample positions for testing."""
        positions = [
            PositionPlacement(
                x=0, y=0, color_id="lego_blue", color_name="Blue",
                lego_color_code="23", part_type="tile", lego_part_id="98138"
            ),
            PositionPlacement(
                x=1, y=0, color_id="lego_blue", color_name="Blue",
                lego_color_code="23", part_type="tile", lego_part_id="98138"
            ),
            PositionPlacement(
                x=0, y=1, color_id="lego_green", color_name="Green",
                lego_color_code="28", part_type="brick", lego_part_id="3062b"
            ),
            PositionPlacement(
                x=1, y=1, color_id="lego_green", color_name="Green",
                lego_color_code="28", part_type="brick", lego_part_id="3062b"
            ),
        ]
        return positions

    def test_create_grid(self, sample_positions):
        """Test creating a position placement grid."""
        grid = PositionPlacementGrid(
            width=2,
            height=2,
            positions=sample_positions,
            source_image="test.png"
        )
        assert grid.width == 2
        assert grid.height == 2
        assert grid.total_positions == 4
        assert grid.land_positions == 2
        assert grid.ocean_positions == 2
        assert grid.unique_colors == 2
        assert grid.coordinate_system == "top_left_origin"
        assert grid.source_image == "test.png"
        assert grid.schema_version == "1.0"

    def test_get_position(self, sample_positions):
        """Test retrieving a position by coordinates."""
        grid = PositionPlacementGrid(
            width=2, height=2, positions=sample_positions, source_image="test.png"
        )
        pos = grid.get_position(0, 0)
        assert pos is not None
        assert pos.x == 0
        assert pos.y == 0
        assert pos.color_id == "lego_blue"

    def test_get_position_not_found(self, sample_positions):
        """Test retrieving a position that doesn't exist."""
        grid = PositionPlacementGrid(
            width=2, height=2, positions=sample_positions, source_image="test.png"
        )
        pos = grid.get_position(10, 10)
        assert pos is None

    def test_add_position(self):
        """Test adding a position to the grid."""
        grid = PositionPlacementGrid(
            width=2, height=2, positions=[], source_image="test.png"
        )
        pos = PositionPlacement(
            x=0, y=0, color_id="lego_blue", color_name="Blue",
            lego_color_code="23", part_type="tile", lego_part_id="98138"
        )
        grid.add_position(pos)
        assert len(grid.positions) == 1
        assert grid.get_position(0, 0) == pos

    def test_compute_statistics(self, sample_positions):
        """Test computing layout statistics."""
        grid = PositionPlacementGrid(
            width=2, height=2, positions=sample_positions, source_image="test.png"
        )
        stats = grid.compute_statistics()
        assert stats.total_tile_count == 4
        assert stats.land_brick_count == 2
        assert stats.ocean_tile_count == 2
        assert stats.unique_colors == 2
        assert stats.coverage_percentage == 100.0
        assert stats.color_frequency["lego_blue"] == 2
        assert stats.color_frequency["lego_green"] == 2
        assert stats.color_frequency_by_part_type["brick"]["lego_green"] == 2
        assert stats.color_frequency_by_part_type["tile"]["lego_blue"] == 2

    def test_to_json(self, sample_positions):
        """Test serializing grid to JSON string."""
        grid = PositionPlacementGrid(
            width=2, height=2, positions=sample_positions, source_image="test.png"
        )
        json_str = grid.to_json()
        data = json.loads(json_str)

        assert "metadata" in data
        assert "positions" in data
        assert "statistics" in data

        assert data["metadata"]["width"] == 2
        assert data["metadata"]["height"] == 2
        assert data["metadata"]["total_positions"] == 4
        assert data["metadata"]["land_positions"] == 2
        assert data["metadata"]["ocean_positions"] == 2
        assert data["metadata"]["coordinate_system"] == "top_left_origin"
        assert data["metadata"]["schema_version"] == "1.0"

        assert len(data["positions"]) == 4

    def test_to_csv(self, sample_positions):
        """Test serializing grid to CSV string."""
        grid = PositionPlacementGrid(
            width=2, height=2, positions=sample_positions, source_image="test.png"
        )
        csv_str = grid.to_csv()
        lines = [line.strip() for line in csv_str.strip().split("\n")]

        # Check header
        assert lines[0] == "x_position,y_position,color_id,color_name,lego_color_code,part_type,lego_part_id"

        # Check data rows
        assert len(lines) == 5  # Header + 4 positions

    def test_from_json(self, sample_positions):
        """Test round-trip JSON serialization."""
        original_grid = PositionPlacementGrid(
            width=2, height=2, positions=sample_positions, source_image="test.png"
        )
        json_str = original_grid.to_json()

        restored_grid = PositionPlacementGrid.from_json(json_str)

        assert restored_grid.width == original_grid.width
        assert restored_grid.height == original_grid.height
        assert restored_grid.total_positions == original_grid.total_positions
        assert restored_grid.land_positions == original_grid.land_positions
        assert restored_grid.ocean_positions == original_grid.ocean_positions
        assert len(restored_grid.positions) == len(original_grid.positions)

    def test_total_positions_invariant(self, sample_positions):
        """Test that total_positions equals width * height."""
        grid = PositionPlacementGrid(
            width=2, height=2, positions=sample_positions, source_image="test.png"
        )
        assert grid.total_positions == grid.width * grid.height

    def test_land_ocean_sum_invariant(self, sample_positions):
        """Test that land_positions + ocean_positions = total_positions."""
        grid = PositionPlacementGrid(
            width=2, height=2, positions=sample_positions, source_image="test.png"
        )
        assert grid.land_positions + grid.ocean_positions == grid.total_positions

    def test_generated_at_timestamp(self, sample_positions):
        """Test that generated_at is set to current time."""
        from datetime import timedelta
        before = datetime.utcnow() - timedelta(seconds=1)
        grid = PositionPlacementGrid(
            width=2, height=2, positions=sample_positions, source_image="test.png"
        )
        after = datetime.utcnow() + timedelta(seconds=1)

        generated_at = datetime.fromisoformat(grid.generated_at.replace("Z", "+00:00"))
        # Convert to naive datetime for comparison
        generated_at = generated_at.replace(tzinfo=None)

        assert before <= generated_at <= after

    def test_empty_grid(self):
        """Test creating an empty grid."""
        grid = PositionPlacementGrid(
            width=0, height=0, positions=[], source_image="test.png"
        )
        assert grid.total_positions == 0
        assert grid.land_positions == 0
        assert grid.ocean_positions == 0
        assert grid.unique_colors == 0

    def test_positions_list_is_copy(self, sample_positions):
        """Test that positions property returns a copy."""
        grid = PositionPlacementGrid(
            width=2, height=2, positions=sample_positions, source_image="test.png"
        )
        positions = grid.positions
        positions.clear()
        # Original grid should not be affected
        assert len(grid.positions) == 4

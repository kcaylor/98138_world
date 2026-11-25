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
            land_plate_count=3062,
            ocean_tile_count=7178,
            unique_colors=12,
            color_frequency={"lego_blue_medium": 2400, "lego_green": 1850},
            color_frequency_by_part_type={
                "plate": {"lego_green": 1500},
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
        assert stats.land_plate_count == 3062
        assert stats.ocean_tile_count == 7178
        assert stats.unique_colors == 12
        assert stats.coverage_percentage == 100.0

    def test_to_dict(self):
        """Test converting statistics to dictionary."""
        stats = LayoutStatistics(
            total_tile_count=100,
            land_plate_count=30,
            ocean_tile_count=70,
            unique_colors=5,
            color_frequency={"lego_blue": 50, "lego_green": 30},
            color_frequency_by_part_type={
                "plate": {"lego_green": 30},
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
        assert result["land_plate_count"] == 30
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
                lego_color_code="28", part_type="plate", lego_part_id="6141"
            ),
            PositionPlacement(
                x=1, y=1, color_id="lego_green", color_name="Green",
                lego_color_code="28", part_type="plate", lego_part_id="6141"
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
        assert grid.schema_version == "2.0"

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
        assert stats.land_plate_count == 2
        assert stats.ocean_tile_count == 2
        assert stats.unique_colors == 2
        assert stats.coverage_percentage == 100.0
        assert stats.color_frequency["lego_blue"] == 2
        assert stats.color_frequency["lego_green"] == 2
        assert stats.color_frequency_by_part_type["plate"]["lego_green"] == 2
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
        assert data["metadata"]["schema_version"] == "2.0"
        assert data["metadata"]["disclaimer"] == "Not affiliated with or endorsed by The LEGO Group."
        assert "land_plate_count" in data["statistics"]
        assert set(data["statistics"]["color_frequency_by_part_type"]) == {"plate", "tile"}

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


class TestSchemaVersion:
    """Layout format 2.0 and rejection of older layouts (FR-009, US3-4)."""

    @staticmethod
    def _layout_json(version):
        metadata = {"width": 1, "height": 1, "source_image": "x.png",
                    "generated_at": "2026-11-21T00:00:00Z"}
        if version is not None:
            metadata["schema_version"] = version
        return json.dumps({"metadata": metadata, "positions": [
            {"x": 0, "y": 0, "color_id": "lego_earth_blue", "color_name": "Earth Blue",
             "lego_color_code": "140", "part_type": "tile", "lego_part_id": "98138"}]})

    def test_current_version_constant(self):
        from lego_image_processor.layout.grid import CURRENT_SCHEMA_VERSION
        assert CURRENT_SCHEMA_VERSION == "2.0"

    def test_accepts_2_0(self):
        grid = PositionPlacementGrid.from_json(self._layout_json("2.0"))
        assert grid.schema_version == "2.0"

    @pytest.mark.parametrize("version,shown", [("1.0", "1.0"), (None, "(missing)"), ("3.0", "3.0")])
    def test_rejects_other_versions(self, version, shown):
        from lego_image_processor.layout.grid import LayoutSchemaError
        with pytest.raises(LayoutSchemaError) as info:
            PositionPlacementGrid.from_json(self._layout_json(version))
        msg = str(info.value)
        assert f"Layout schema version {shown} is no longer supported" in msg
        assert "6141" in msg
        assert "lego-image-processor layout <image> -o <layout.json>" in msg
        assert isinstance(info.value, ValueError)


class TestMapProvenance:
    """`metadata.map` provenance block (feature 004, Q3): additive, schema stays 2.0."""

    def _grid(self, **kw):
        positions = [PositionPlacement(x=0, y=0, color_id="lego_white", color_name="White",
                                       lego_color_code="1", part_type="plate", lego_part_id="6141")]
        return PositionPlacementGrid(width=1, height=1, positions=positions, source_image="recipe:demo",
                                     generated_at="2026-11-22T00:00:00Z", **kw)

    def test_written_and_preserved(self):
        block = {"recipe": {"id": "demo", "format": "1", "sha256": "0" * 64, "title": "Demo"},
                 "layers": [], "seed": 1, "disclaimer": "Not affiliated with or endorsed by The LEGO Group."}
        g = self._grid(map_metadata=block)
        data = json.loads(g.to_json())
        assert data["metadata"]["map"] == block
        assert data["metadata"]["schema_version"] == "2.0"
        again = PositionPlacementGrid.from_json(g.to_json())
        assert again.map_metadata == block
        assert json.loads(again.to_json())["metadata"]["map"] == block

    def test_absent_by_default(self):
        g = self._grid()
        assert g.map_metadata is None
        assert "map" not in json.loads(g.to_json())["metadata"]
        assert PositionPlacementGrid.from_json(g.to_json()).map_metadata is None


class TestTemplateLayout:
    """Feature 016 (T052; FR-010; research R11; data-model.md Layout (extended)): ``metadata.template``,
    ``metadata.margin_positions``, ``statistics.margin_tile_count`` and
    ``statistics.color_frequency_by_part_type.square_tile`` only for non-kit layouts; a layout without
    ``metadata.template`` reads as the kit."""

    TEMPLATE = {"id": "winkel-tripel", "title": "Winkel tripel on the kit board",
                "parts": {"land": "6141", "ocean": "98138", "margin": "3070b"},
                "counts": {"land": 1, "ocean": 1, "margin": 2, "ring": 2}}

    def _positions(self):
        def p(x, y, part_type, part, color, name, code):
            return PositionPlacement(x=x, y=y, color_id=color, color_name=name, lego_color_code=code,
                                     part_type=part_type, lego_part_id=part)
        return [p(0, 0, "plate", "6141", "lego_white", "White", "1"),
                p(1, 0, "tile", "98138", "lego_medium_azur", "Medium Azur", "322"),
                p(0, 1, "square_tile", "3070b", "lego_black", "Black", "26"),
                p(1, 1, "square_tile", "3070b", "lego_white", "White", "1")]

    def _grid(self, template=None):
        return PositionPlacementGrid(width=2, height=2, positions=self._positions(), source_image="recipe:demo",
                                     generated_at="2026-11-23T00:00:00Z", template=template)

    def test_template_layout(self):
        g = self._grid(self.TEMPLATE)
        assert g.template == self.TEMPLATE
        assert (g.land_positions, g.ocean_positions, g.margin_positions) == (1, 1, 2)
        d = json.loads(g.to_json())
        m = d["metadata"]
        assert m["template"] == self.TEMPLATE and m["margin_positions"] == 2
        assert list(m).index("margin_positions") == list(m).index("ocean_positions") + 1
        s = d["statistics"]
        assert s["margin_tile_count"] == 2
        assert s["color_frequency_by_part_type"]["square_tile"] == {"lego_black": 1, "lego_white": 1}
        assert s["color_frequency_by_part_type"]["plate"] == {"lego_white": 1}
        assert s["total_tile_count"] == 4 and s["color_frequency"]["lego_white"] == 2

    def test_round_trip(self):
        g = self._grid(self.TEMPLATE)
        again = PositionPlacementGrid.from_json(g.to_json())
        assert again.template == self.TEMPLATE
        assert again.to_json() == g.to_json()

    def test_kit_layout_has_no_template_keys(self):
        positions = [q for q in self._positions() if q.part_type != "square_tile"]
        g = PositionPlacementGrid(width=2, height=1, positions=positions, source_image="recipe:demo",
                                  generated_at="2026-11-23T00:00:00Z")
        assert g.template is None
        d = json.loads(g.to_json())
        assert not {"template", "margin_positions"} & set(d["metadata"])
        assert "margin_tile_count" not in d["statistics"]
        assert set(d["statistics"]["color_frequency_by_part_type"]) == {"plate", "tile"}
        assert list(d["statistics"]) == ["total_tile_count", "land_plate_count", "ocean_tile_count",
                                         "unique_colors", "color_frequency", "color_frequency_by_part_type",
                                         "most_common_color", "coverage_percentage"]

    def test_absent_template_reads_as_kit(self):
        g = PositionPlacementGrid.from_json(self._grid().to_json())
        assert g.template is None and g.arrangement is None  # absent = kit template, combination A

    def test_statistics_object(self):
        st = self._grid(self.TEMPLATE).compute_statistics()
        assert st.margin_tile_count == 2
        assert self._grid().compute_statistics().margin_tile_count is None

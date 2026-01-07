"""Integration tests for layout generation pipeline."""

from pathlib import Path

import pytest
from PIL import Image

from lego_image_processor.layout.generator import LayoutGenerator
from lego_image_processor.layout.land_sea_mask import load_land_sea_mask
from lego_image_processor.layout.grid import PositionPlacementGrid
from lego_image_processor.palette.loader import LegoPalette


# Get path to test fixtures
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
IMAGES_DIR = FIXTURES_DIR / "images"


class TestLayoutPipeline:
    """Integration tests for complete layout generation workflow."""

    @pytest.fixture
    def palette(self):
        """Load the default LEGO palette."""
        return LegoPalette.load_default()

    @pytest.fixture
    def land_sea_mask(self):
        """Load the land/sea mask."""
        return load_land_sea_mask()

    @pytest.fixture
    def generator(self, palette, land_sea_mask):
        """Create a LayoutGenerator instance."""
        return LayoutGenerator(palette=palette, land_sea_mask=land_sea_mask)

    @pytest.fixture
    def test_image(self, palette):
        """Create a valid test image."""
        first_color = palette.colors[0]
        return Image.new("RGB", (128, 80), first_color.rgb)

    def test_full_pipeline_generates_correct_position_count(self, generator, test_image):
        """Test that full pipeline generates 10,240 positions."""
        grid = generator.generate(test_image, source_filename="test.png")
        assert len(grid.positions) == 10240

    def test_full_pipeline_correct_land_brick_count(self, generator, test_image):
        """Test that pipeline generates exactly 3,062 land bricks."""
        grid = generator.generate(test_image, source_filename="test.png")

        brick_count = sum(1 for p in grid.positions if p.part_type == "brick")
        assert brick_count == 3062

    def test_full_pipeline_correct_ocean_tile_count(self, generator, test_image):
        """Test that pipeline generates exactly 7,178 ocean tiles."""
        grid = generator.generate(test_image, source_filename="test.png")

        tile_count = sum(1 for p in grid.positions if p.part_type == "tile")
        assert tile_count == 7178

    def test_full_pipeline_correct_part_ids(self, generator, test_image):
        """Test that bricks use 3062b and tiles use 98138."""
        grid = generator.generate(test_image, source_filename="test.png")

        for pos in grid.positions:
            if pos.part_type == "brick":
                assert pos.lego_part_id == "3062b"
            else:
                assert pos.lego_part_id == "98138"

    def test_full_pipeline_valid_coordinates(self, generator, test_image):
        """Test that all positions have valid coordinates."""
        grid = generator.generate(test_image, source_filename="test.png")

        for pos in grid.positions:
            assert 0 <= pos.x < 128
            assert 0 <= pos.y < 80

    def test_full_pipeline_all_coordinates_covered(self, generator, test_image):
        """Test that every coordinate has a position."""
        grid = generator.generate(test_image, source_filename="test.png")

        coords = set((p.x, p.y) for p in grid.positions)
        expected_coords = set((x, y) for y in range(80) for x in range(128))
        assert coords == expected_coords

    def test_full_pipeline_colors_preserved(self, generator, palette):
        """Test that colors from input image are preserved."""
        # Create image with 4 colors in stripes
        colors = [palette.colors[i] for i in range(4)]
        img = Image.new("RGB", (128, 80))
        for y in range(80):
            color = colors[y // 20]
            for x in range(128):
                img.putpixel((x, y), color.rgb)

        grid = generator.generate(img, source_filename="test.png")

        # Verify 4 unique colors
        assert grid.unique_colors == 4

    def test_json_round_trip(self, generator, test_image):
        """Test that JSON serialization and deserialization preserves data."""
        original = generator.generate(test_image, source_filename="test.png")
        json_str = original.to_json()
        restored = PositionPlacementGrid.from_json(json_str)

        assert restored.width == original.width
        assert restored.height == original.height
        assert restored.total_positions == original.total_positions
        assert restored.land_positions == original.land_positions
        assert restored.ocean_positions == original.ocean_positions
        assert len(restored.positions) == len(original.positions)

    def test_csv_output_format(self, generator, test_image):
        """Test that CSV output has correct format."""
        grid = generator.generate(test_image, source_filename="test.png")
        csv = grid.to_csv()
        lines = [line.strip() for line in csv.strip().split("\n")]

        # Header + 10240 positions
        assert len(lines) == 10241

        # Check header
        assert lines[0] == "x_position,y_position,color_id,color_name,lego_color_code,part_type,lego_part_id"

    def test_statistics_computed_correctly(self, generator, palette):
        """Test that statistics are computed correctly."""
        # Create image with 2 colors
        img = Image.new("RGB", (128, 80))
        for y in range(80):
            for x in range(128):
                if x < 64:
                    img.putpixel((x, y), palette.colors[0].rgb)
                else:
                    img.putpixel((x, y), palette.colors[1].rgb)

        grid = generator.generate(img, source_filename="test.png")
        stats = grid.compute_statistics()

        assert stats.total_tile_count == 10240
        assert stats.land_brick_count == 3062
        assert stats.ocean_tile_count == 7178
        assert stats.unique_colors == 2
        assert stats.coverage_percentage == 100.0

    def test_with_real_fixture_image(self, generator):
        """Test with actual fixture image if available."""
        fixture_path = IMAGES_DIR / "test_128x80_quantized.png"
        if not fixture_path.exists():
            pytest.skip("Fixture image not available")

        image = Image.open(fixture_path)
        grid = generator.generate(image, source_filename=fixture_path.name)

        assert grid.total_positions == 10240
        assert grid.land_positions == 3062
        assert grid.ocean_positions == 7178

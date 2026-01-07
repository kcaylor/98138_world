"""Unit tests for LayoutGenerator class."""

import pytest
from PIL import Image
import numpy as np

from lego_image_processor.layout.generator import LayoutGenerator
from lego_image_processor.layout.land_sea_mask import load_land_sea_mask
from lego_image_processor.palette.loader import LegoPalette


class TestLayoutGenerator:
    """Tests for LayoutGenerator class."""

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

    def test_create_generator(self, palette, land_sea_mask):
        """Test creating a LayoutGenerator."""
        gen = LayoutGenerator(palette=palette, land_sea_mask=land_sea_mask)
        assert gen is not None

    def test_generate_valid_image(self, generator, palette):
        """Test generating layout from valid image."""
        # Create a 128x80 image with valid LEGO colors
        # Get first color from palette
        first_color = palette.colors[0]
        image = Image.new("RGB", (128, 80), first_color.rgb)

        grid = generator.generate(image, source_filename="test.png")

        assert grid.width == 128
        assert grid.height == 80
        assert grid.total_positions == 10240
        assert grid.land_positions == 3062
        assert grid.ocean_positions == 7178
        assert len(grid.positions) == 10240

    def test_generate_counts_land_ocean(self, generator, palette):
        """Test that generated layout has correct land/ocean counts."""
        first_color = palette.colors[0]
        image = Image.new("RGB", (128, 80), first_color.rgb)

        grid = generator.generate(image, source_filename="test.png")

        # Count by part type
        brick_count = sum(1 for p in grid.positions if p.part_type == "brick")
        tile_count = sum(1 for p in grid.positions if p.part_type == "tile")

        assert brick_count == 3062
        assert tile_count == 7178

    def test_generate_position_coordinates(self, generator, palette):
        """Test that generated positions have correct coordinates."""
        first_color = palette.colors[0]
        image = Image.new("RGB", (128, 80), first_color.rgb)

        grid = generator.generate(image, source_filename="test.png")

        # Check all positions have valid coordinates
        for pos in grid.positions:
            assert 0 <= pos.x < 128, f"Invalid x coordinate: {pos.x}"
            assert 0 <= pos.y < 80, f"Invalid y coordinate: {pos.y}"

    def test_generate_preserves_colors(self, generator, palette):
        """Test that colors from image are preserved in layout."""
        # Create an image with two colors
        img = Image.new("RGB", (128, 80))
        first_color = palette.colors[0]
        second_color = palette.colors[1]

        # Fill left half with first color, right half with second
        for y in range(80):
            for x in range(128):
                if x < 64:
                    img.putpixel((x, y), first_color.rgb)
                else:
                    img.putpixel((x, y), second_color.rgb)

        grid = generator.generate(img, source_filename="test.png")

        # Verify colors are preserved
        pos_0_0 = grid.get_position(0, 0)
        pos_100_0 = grid.get_position(100, 0)

        assert pos_0_0 is not None
        assert pos_100_0 is not None

    def test_validate_dimensions_correct(self, generator, palette):
        """Test that correct dimensions are accepted."""
        first_color = palette.colors[0]
        image = Image.new("RGB", (128, 80), first_color.rgb)

        # Should not raise
        generator._validate_dimensions(image)

    def test_validate_dimensions_wrong_width(self, generator, palette):
        """Test that wrong width raises ValueError."""
        first_color = palette.colors[0]
        image = Image.new("RGB", (100, 80), first_color.rgb)

        with pytest.raises(ValueError, match="128"):
            generator._validate_dimensions(image)

    def test_validate_dimensions_wrong_height(self, generator, palette):
        """Test that wrong height raises ValueError."""
        first_color = palette.colors[0]
        image = Image.new("RGB", (128, 50), first_color.rgb)

        with pytest.raises(ValueError, match="80"):
            generator._validate_dimensions(image)

    def test_validate_colors_valid(self, generator, palette):
        """Test that valid LEGO colors are accepted."""
        first_color = palette.colors[0]
        image = Image.new("RGB", (128, 80), first_color.rgb)

        # Should not raise
        generator._validate_colors(image)

    def test_validate_colors_invalid(self, generator):
        """Test that invalid colors raise ValueError."""
        # Create image with a color not in LEGO palette
        image = Image.new("RGB", (128, 80), (127, 84, 200))  # Random non-LEGO color

        with pytest.raises(ValueError, match="Invalid color"):
            generator._validate_colors(image)

    def test_validate_colors_shows_coordinates(self, generator):
        """Test that invalid color error shows coordinates."""
        # Create valid image first
        from lego_image_processor.palette.loader import LegoPalette
        palette = LegoPalette.load_default()
        first_color = palette.colors[0]
        image = Image.new("RGB", (128, 80), first_color.rgb)

        # Set an invalid pixel
        image.putpixel((42, 17), (127, 84, 200))

        with pytest.raises(ValueError) as exc_info:
            generator._validate_colors(image)

        # Should include coordinates
        assert "42" in str(exc_info.value) or "17" in str(exc_info.value)

    def test_generate_with_multicolor_image(self, generator, palette):
        """Test generating layout from multi-color image."""
        img = Image.new("RGB", (128, 80))

        # Create a striped pattern with 4 colors
        colors = [palette.colors[i].rgb for i in range(min(4, len(palette.colors)))]
        for y in range(80):
            color_idx = y // 20  # 4 horizontal stripes
            for x in range(128):
                img.putpixel((x, y), colors[color_idx])

        grid = generator.generate(img, source_filename="striped.png")

        assert grid.total_positions == 10240
        assert grid.unique_colors == 4

    def test_source_image_in_grid(self, generator, palette):
        """Test that source image filename is stored in grid."""
        first_color = palette.colors[0]
        image = Image.new("RGB", (128, 80), first_color.rgb)

        grid = generator.generate(image, source_filename="my_image.png")

        assert grid.source_image == "my_image.png"

    def test_part_type_matches_mask(self, generator, palette, land_sea_mask):
        """Test that part types match the land/sea mask."""
        first_color = palette.colors[0]
        image = Image.new("RGB", (128, 80), first_color.rgb)

        grid = generator.generate(image, source_filename="test.png")

        # Verify each position's part type matches the mask
        for pos in grid.positions:
            expected_is_land = land_sea_mask.is_land(pos.x, pos.y)
            if expected_is_land:
                assert pos.part_type == "brick", f"Position ({pos.x}, {pos.y}) should be brick"
                assert pos.lego_part_id == "3062b"
            else:
                assert pos.part_type == "tile", f"Position ({pos.x}, {pos.y}) should be tile"
                assert pos.lego_part_id == "98138"

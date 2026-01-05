"""Unit tests for color statistics."""

import pytest
import numpy as np
from PIL import Image
from collections import Counter

from lego_image_processor.analysis.color_stats import (
    ColorStatistics,
    analyze_image
)
from lego_image_processor.palette.loader import LegoPalette


class TestColorStatistics:
    """Tests for ColorStatistics dataclass."""

    def test_create_statistics(self):
        """Test creating ColorStatistics instance."""
        stats = ColorStatistics(
            total_pixels=1000,
            unique_colors=10,
            color_counts=Counter({(255, 0, 0): 500, (0, 255, 0): 500}),
            lego_colors_found=2,
            lego_coverage_percent=100.0
        )
        assert stats.total_pixels == 1000
        assert stats.unique_colors == 10
        assert stats.lego_colors_found == 2

    def test_get_top_colors(self):
        """Test getting top colors."""
        counts = Counter({
            (255, 0, 0): 500,
            (0, 255, 0): 300,
            (0, 0, 255): 200
        })
        stats = ColorStatistics(
            total_pixels=1000,
            unique_colors=3,
            color_counts=counts,
            lego_colors_found=0,
            lego_coverage_percent=0.0
        )

        top = stats.get_top_colors(2)
        assert len(top) == 2
        assert top[0] == ((255, 0, 0), 500)
        assert top[1] == ((0, 255, 0), 300)

    def test_is_fully_lego(self):
        """Test is_fully_lego method."""
        # Fully LEGO
        stats = ColorStatistics(
            total_pixels=1000,
            unique_colors=5,
            color_counts=Counter(),
            lego_colors_found=5,
            lego_coverage_percent=100.0
        )
        assert stats.is_fully_lego()

        # Not fully LEGO
        stats = ColorStatistics(
            total_pixels=1000,
            unique_colors=5,
            color_counts=Counter(),
            lego_colors_found=3,
            lego_coverage_percent=60.0
        )
        assert not stats.is_fully_lego()


class TestAnalyzeImage:
    """Tests for analyze_image function."""

    @pytest.fixture
    def palette(self):
        """Load default palette."""
        return LegoPalette.load_default()

    @pytest.fixture
    def solid_color_image(self, palette):
        """Create image with single LEGO color."""
        # Use actual LEGO white color
        white = palette.get_by_name("White")
        return Image.new("RGB", (100, 100), color=white.rgb)

    @pytest.fixture
    def non_lego_image(self):
        """Create image with non-LEGO colors."""
        # Use a color unlikely to be in palette
        return Image.new("RGB", (100, 100), color=(123, 45, 67))

    def test_analyze_solid_color(self, solid_color_image, palette):
        """Test analyzing solid color image."""
        stats = analyze_image(solid_color_image, palette)
        assert stats.total_pixels == 10000
        assert stats.unique_colors == 1
        assert stats.lego_colors_found == 1
        assert stats.lego_coverage_percent == 100.0

    def test_analyze_non_lego_image(self, non_lego_image, palette):
        """Test analyzing image with non-LEGO colors."""
        stats = analyze_image(non_lego_image, palette)
        assert stats.lego_colors_found == 0
        assert stats.lego_coverage_percent == 0.0

    def test_analyze_multicolor_image(self, palette):
        """Test analyzing image with multiple colors."""
        img = Image.new("RGB", (20, 20))
        pixels = img.load()

        # Fill with gradient
        for y in range(20):
            for x in range(20):
                pixels[x, y] = (x * 12, y * 12, 128)

        stats = analyze_image(img, palette)
        assert stats.total_pixels == 400
        assert stats.unique_colors > 1

    def test_analyze_rgba_image(self, palette):
        """Test analyzing RGBA image."""
        img = Image.new("RGBA", (50, 50), color=(255, 255, 255, 255))
        stats = analyze_image(img, palette)
        assert stats.total_pixels == 2500

    def test_analyze_grayscale_image(self, palette):
        """Test analyzing grayscale image."""
        img = Image.new("L", (50, 50), color=128)
        stats = analyze_image(img, palette)
        assert stats.total_pixels == 2500

    def test_analyze_with_default_palette(self):
        """Test analyzing with default palette (None)."""
        img = Image.new("RGB", (10, 10), color=(255, 255, 255))
        stats = analyze_image(img)  # No palette specified
        assert stats is not None
        assert stats.total_pixels == 100

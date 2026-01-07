"""Unit tests for color quantizer."""

import pytest
import numpy as np
from PIL import Image

from lego_image_processor.core.color_quantizer import (
    delta_e_2000,
    ColorQuantizer,
    QuantizationResult
)
from lego_image_processor.palette.loader import LegoPalette
from lego_image_processor.palette.converter import rgb_to_lab


class TestDeltaE2000:
    """Tests for Delta E 2000 color difference."""

    def test_identical_colors(self):
        """Test that identical colors have zero difference."""
        lab1 = np.array([[50, 0, 0]], dtype=np.float64)
        lab2 = np.array([[50, 0, 0]], dtype=np.float64)
        delta_e = delta_e_2000(lab1, lab2)
        np.testing.assert_almost_equal(delta_e[0], 0, decimal=5)

    def test_different_lightness(self):
        """Test colors with different lightness."""
        lab1 = np.array([[0, 0, 0]], dtype=np.float64)  # Black
        lab2 = np.array([[100, 0, 0]], dtype=np.float64)  # White
        delta_e = delta_e_2000(lab1, lab2)
        assert delta_e[0] > 50  # Should be very different

    def test_symmetry(self):
        """Test that delta E is symmetric."""
        lab1 = np.array([[50, 20, 30]], dtype=np.float64)
        lab2 = np.array([[60, -10, 40]], dtype=np.float64)
        de_1_to_2 = delta_e_2000(lab1, lab2)
        de_2_to_1 = delta_e_2000(lab2, lab1)
        np.testing.assert_almost_equal(de_1_to_2, de_2_to_1, decimal=5)

    def test_non_negative(self):
        """Test that delta E is always non-negative."""
        np.random.seed(42)
        for _ in range(100):
            lab1 = np.random.uniform(-128, 128, (1, 3))
            lab1[0, 0] = np.random.uniform(0, 100)  # L in valid range
            lab2 = np.random.uniform(-128, 128, (1, 3))
            lab2[0, 0] = np.random.uniform(0, 100)
            delta_e = delta_e_2000(lab1, lab2)
            assert delta_e[0] >= 0

    def test_batch_processing(self):
        """Test computing delta E for multiple color pairs."""
        lab1 = np.array([[50, 0, 0]], dtype=np.float64)
        lab2 = np.array([
            [50, 0, 0],
            [60, 0, 0],
            [70, 0, 0]
        ], dtype=np.float64)
        delta_e = delta_e_2000(lab1, lab2)
        assert len(delta_e) == 3
        assert delta_e[0] < delta_e[1] < delta_e[2]


class TestColorQuantizer:
    """Tests for ColorQuantizer class."""

    @pytest.fixture
    def quantizer(self):
        """Create a quantizer with default palette."""
        return ColorQuantizer()

    @pytest.fixture
    def simple_image(self):
        """Create a simple test image."""
        # 10x10 red image
        return Image.new("RGB", (10, 10), color=(255, 0, 0))

    def test_init_with_default_palette(self, quantizer):
        """Test quantizer initialization with default palette."""
        assert quantizer.palette is not None
        assert len(quantizer.palette) > 0

    def test_init_with_custom_palette(self):
        """Test quantizer initialization with custom palette."""
        palette = LegoPalette.load_default()
        quantizer = ColorQuantizer(palette)
        assert quantizer.palette is palette

    def test_find_closest_color(self, quantizer):
        """Test finding closest LEGO color."""
        # Pure white should map to LEGO white
        closest = quantizer.find_closest_color((255, 255, 255))
        assert closest.name == "White"

        # Pure black should map to LEGO black
        closest = quantizer.find_closest_color((0, 0, 0))
        assert closest.name == "Black"

    def test_find_closest_color_red(self, quantizer):
        """Test finding closest color to pure red."""
        closest = quantizer.find_closest_color((255, 0, 0))
        # Should match Bright Red or similar
        assert closest is not None
        assert closest.rgb[0] > closest.rgb[1]  # More red than green

    def test_quantize_returns_result(self, quantizer, simple_image):
        """Test that quantize returns a QuantizationResult."""
        result = quantizer.quantize(simple_image)
        assert isinstance(result, QuantizationResult)

    def test_quantize_preserves_dimensions(self, quantizer, simple_image):
        """Test that quantized image has same dimensions."""
        result = quantizer.quantize(simple_image)
        assert result.image.size == simple_image.size

    def test_quantize_produces_lego_colors(self, quantizer, simple_image):
        """Test that output contains only LEGO palette colors."""
        result = quantizer.quantize(simple_image)

        # Get all unique colors in output
        img_array = np.array(result.image)
        unique_colors = set(map(tuple, img_array.reshape(-1, 3)))

        # All colors should be in palette
        palette_colors = set(c.rgb for c in quantizer.palette.colors)
        for color in unique_colors:
            assert color in palette_colors, f"Color {color} not in palette"

    def test_quantize_tracks_color_mapping(self, quantizer, simple_image):
        """Test that color mapping is tracked."""
        result = quantizer.quantize(simple_image)
        assert len(result.color_mapping) > 0
        assert result.original_colors >= 1
        assert result.mapped_colors >= 1

    def test_quantize_rgba_image(self, quantizer):
        """Test quantizing RGBA image."""
        img = Image.new("RGBA", (10, 10), color=(255, 0, 0, 255))
        result = quantizer.quantize(img)
        assert result.image.mode == "RGB"

    def test_quantize_grayscale_image(self, quantizer):
        """Test quantizing grayscale image."""
        img = Image.new("L", (10, 10), color=128)
        result = quantizer.quantize(img)
        assert result.image.mode == "RGB"

    def test_quantize_multicolor_image(self, quantizer):
        """Test quantizing image with multiple colors."""
        img = Image.new("RGB", (20, 20))
        pixels = img.load()

        # Create a gradient
        for y in range(20):
            for x in range(20):
                pixels[x, y] = (x * 12, y * 12, 128)

        result = quantizer.quantize(img)
        assert result.original_colors > 1
        assert result.mapped_colors >= 1


class TestQuantizationResult:
    """Tests for QuantizationResult dataclass."""

    def test_create_result(self):
        """Test creating a QuantizationResult."""
        img = Image.new("RGB", (10, 10))
        result = QuantizationResult(
            image=img,
            color_mapping={},
            original_colors=5,
            mapped_colors=3
        )
        assert result.image is img
        assert result.original_colors == 5
        assert result.mapped_colors == 3

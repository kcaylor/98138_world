"""Integration tests for the full quantization pipeline."""

import pytest
import numpy as np
from PIL import Image
import tempfile
from pathlib import Path

from lego_image_processor.core.color_quantizer import ColorQuantizer
from lego_image_processor.core.image_loader import load_image
from lego_image_processor.core.image_writer import save_image
from lego_image_processor.palette.loader import LegoPalette
from lego_image_processor.analysis.color_stats import analyze_image


class TestFullPipeline:
    """Integration tests for complete image processing pipeline."""

    @pytest.fixture
    def palette(self):
        """Load the default LEGO palette."""
        return LegoPalette.load_default()

    @pytest.fixture
    def quantizer(self, palette):
        """Create a color quantizer."""
        return ColorQuantizer(palette)

    @pytest.fixture
    def test_image(self):
        """Create a test image with various colors."""
        img = Image.new("RGB", (100, 100))
        pixels = img.load()

        # Create quadrants with different colors
        for y in range(100):
            for x in range(100):
                if x < 50 and y < 50:
                    pixels[x, y] = (255, 0, 0)  # Red
                elif x >= 50 and y < 50:
                    pixels[x, y] = (0, 255, 0)  # Green
                elif x < 50 and y >= 50:
                    pixels[x, y] = (0, 0, 255)  # Blue
                else:
                    pixels[x, y] = (255, 255, 0)  # Yellow

        return img

    def test_load_quantize_save_pipeline(self, quantizer, test_image):
        """Test full pipeline: load -> quantize -> save -> verify."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save test image
            input_path = Path(temp_dir) / "input.png"
            test_image.save(input_path)

            # Load
            loaded_image = load_image(input_path)
            assert loaded_image.size == (100, 100)

            # Quantize
            result = quantizer.quantize(loaded_image)
            assert result.image.size == (100, 100)

            # Save
            output_path = Path(temp_dir) / "output.png"
            save_image(result.image, output_path)
            assert output_path.exists()

            # Verify output
            final_image = load_image(output_path)
            stats = analyze_image(final_image)

            # All colors should be LEGO colors
            assert stats.lego_coverage_percent == 100.0

    def test_quantized_output_contains_only_lego_colors(self, quantizer, palette):
        """Test that quantized images only contain LEGO colors."""
        # Create image with random colors
        np.random.seed(42)
        random_pixels = np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8)
        img = Image.fromarray(random_pixels, mode="RGB")

        # Quantize
        result = quantizer.quantize(img)

        # Verify all output colors are in palette
        output_array = np.array(result.image)
        unique_colors = set(map(tuple, output_array.reshape(-1, 3)))
        palette_colors = set(c.rgb for c in palette.colors)

        for color in unique_colors:
            assert color in palette_colors

    def test_color_mapping_accuracy(self, quantizer):
        """Test that color mapping is recorded accurately."""
        # Create simple image
        img = Image.new("RGB", (10, 10), color=(200, 50, 50))
        result = quantizer.quantize(img)

        # Check mapping
        assert (200, 50, 50) in result.color_mapping
        mapped_color = result.color_mapping[(200, 50, 50)]

        # Verify the mapped color is in the output
        output_array = np.array(result.image)
        assert np.all(output_array[0, 0] == list(mapped_color.rgb))

    def test_large_image_processing(self, quantizer):
        """Test processing of larger images."""
        # Create 1024x1024 image
        np.random.seed(42)
        large_pixels = np.random.randint(0, 256, (1024, 1024, 3), dtype=np.uint8)
        img = Image.fromarray(large_pixels, mode="RGB")

        # Should complete without error
        result = quantizer.quantize(img)
        assert result.image.size == (1024, 1024)

        # Verify output
        stats = analyze_image(result.image)
        assert stats.lego_coverage_percent == 100.0

    def test_preserves_image_dimensions(self, quantizer):
        """Test that various image dimensions are preserved."""
        dimensions = [(1, 1), (10, 20), (100, 50), (200, 200)]

        for width, height in dimensions:
            img = Image.new("RGB", (width, height), color=(128, 128, 128))
            result = quantizer.quantize(img)
            assert result.image.size == (width, height)

    def test_stats_after_quantization(self, quantizer, palette):
        """Test that stats reflect LEGO colors after quantization."""
        # Create image with non-LEGO colors
        img = Image.new("RGB", (50, 50), color=(123, 45, 67))

        # Before quantization - should have no LEGO colors
        before_stats = analyze_image(img, palette)
        assert before_stats.lego_coverage_percent == 0.0

        # After quantization - should be 100% LEGO
        result = quantizer.quantize(img)
        after_stats = analyze_image(result.image, palette)
        assert after_stats.lego_coverage_percent == 100.0


class TestDifferentImageFormats:
    """Test processing different image formats."""

    @pytest.fixture
    def quantizer(self):
        """Create a color quantizer."""
        return ColorQuantizer()

    def test_process_rgba_image(self, quantizer):
        """Test processing RGBA image."""
        img = Image.new("RGBA", (50, 50), color=(255, 0, 0, 128))
        result = quantizer.quantize(img)
        assert result.image.mode == "RGB"

    def test_process_grayscale_image(self, quantizer):
        """Test processing grayscale image."""
        img = Image.new("L", (50, 50), color=128)
        result = quantizer.quantize(img)
        assert result.image.mode == "RGB"

    def test_process_palette_image(self, quantizer):
        """Test processing palette-mode image."""
        img = Image.new("P", (50, 50))
        result = quantizer.quantize(img)
        assert result.image.mode == "RGB"

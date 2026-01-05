"""Unit tests for image writer."""

import pytest
from pathlib import Path
from PIL import Image
import tempfile
import os

from lego_image_processor.core.image_writer import (
    save_image,
    get_output_path,
    ImageWriteError
)


class TestSaveImage:
    """Tests for save_image function."""

    @pytest.fixture
    def sample_image(self):
        """Create a sample RGB image."""
        return Image.new("RGB", (100, 100), color=(255, 0, 0))

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as d:
            yield Path(d)

    def test_save_png(self, sample_image, temp_dir):
        """Test saving PNG image."""
        output_path = temp_dir / "output.png"
        save_image(sample_image, output_path)
        assert output_path.exists()

        # Verify it can be loaded back
        loaded = Image.open(output_path)
        assert loaded.size == (100, 100)

    def test_save_jpeg(self, sample_image, temp_dir):
        """Test saving JPEG image."""
        output_path = temp_dir / "output.jpg"
        save_image(sample_image, output_path)
        assert output_path.exists()

    def test_save_jpeg_quality(self, sample_image, temp_dir):
        """Test saving JPEG with quality parameter."""
        high_quality = temp_dir / "high.jpg"
        low_quality = temp_dir / "low.jpg"

        save_image(sample_image, high_quality, quality=95)
        save_image(sample_image, low_quality, quality=10)

        assert high_quality.exists()
        assert low_quality.exists()
        # Higher quality should result in larger file
        assert high_quality.stat().st_size > low_quality.stat().st_size

    def test_save_creates_directories(self, sample_image, temp_dir):
        """Test that save creates parent directories."""
        output_path = temp_dir / "nested" / "dir" / "output.png"
        save_image(sample_image, output_path)
        assert output_path.exists()

    def test_save_rgba_as_jpeg(self, temp_dir):
        """Test saving RGBA image as JPEG (should convert)."""
        rgba_image = Image.new("RGBA", (100, 100), color=(255, 0, 0, 255))
        output_path = temp_dir / "output.jpg"
        save_image(rgba_image, output_path)

        # JPEG doesn't support alpha, should be converted
        loaded = Image.open(output_path)
        assert loaded.mode == "RGB"

    def test_save_with_string_path(self, sample_image, temp_dir):
        """Test saving with string path."""
        output_path = str(temp_dir / "output.png")
        save_image(sample_image, output_path)
        assert Path(output_path).exists()


class TestGetOutputPath:
    """Tests for get_output_path function."""

    def test_explicit_output(self):
        """Test with explicit output path."""
        result = get_output_path("input.png", "/custom/output.png")
        assert result == Path("/custom/output.png")

    def test_default_suffix(self):
        """Test default suffix."""
        result = get_output_path("/path/to/input.png")
        assert result == Path("/path/to/input_lego.png")

    def test_custom_suffix(self):
        """Test custom suffix."""
        result = get_output_path("/path/to/input.png", suffix="_processed")
        assert result == Path("/path/to/input_processed.png")

    def test_preserves_extension(self):
        """Test that extension is preserved."""
        result = get_output_path("/path/to/photo.jpg")
        assert result.suffix == ".jpg"

        result = get_output_path("/path/to/image.tiff")
        assert result.suffix == ".tiff"

    def test_path_object_input(self):
        """Test with Path object input."""
        result = get_output_path(Path("/path/to/input.png"))
        assert result == Path("/path/to/input_lego.png")

    def test_relative_path(self):
        """Test with relative path."""
        result = get_output_path("images/photo.png")
        assert result == Path("images/photo_lego.png")

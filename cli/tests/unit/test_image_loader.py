"""Unit tests for image loader."""

import pytest
from pathlib import Path
from PIL import Image
import tempfile
import os

from lego_image_processor.core.image_loader import (
    load_image,
    is_supported_format,
    get_image_info,
    ImageLoadError,
    SUPPORTED_FORMATS
)


class TestLoadImage:
    """Tests for load_image function."""

    @pytest.fixture
    def temp_png(self):
        """Create a temporary PNG file."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new("RGB", (100, 100), color=(255, 0, 0))
            img.save(f.name)
            yield Path(f.name)
        os.unlink(f.name)

    @pytest.fixture
    def temp_jpg(self):
        """Create a temporary JPEG file."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            img = Image.new("RGB", (100, 100), color=(0, 255, 0))
            img.save(f.name, "JPEG")
            yield Path(f.name)
        os.unlink(f.name)

    def test_load_png(self, temp_png):
        """Test loading PNG image."""
        img = load_image(temp_png)
        assert isinstance(img, Image.Image)
        assert img.size == (100, 100)

    def test_load_jpg(self, temp_jpg):
        """Test loading JPEG image."""
        img = load_image(temp_jpg)
        assert isinstance(img, Image.Image)
        assert img.size == (100, 100)

    def test_load_nonexistent_file(self):
        """Test loading non-existent file."""
        with pytest.raises(ImageLoadError) as exc_info:
            load_image("/nonexistent/path/image.png")
        assert "File not found" in str(exc_info.value)

    def test_load_unsupported_format(self, tmp_path):
        """Test loading unsupported format."""
        unsupported_file = tmp_path / "file.xyz"
        unsupported_file.write_text("not an image")
        with pytest.raises(ImageLoadError) as exc_info:
            load_image(unsupported_file)
        assert "Unsupported format" in str(exc_info.value)

    def test_load_with_string_path(self, temp_png):
        """Test loading with string path."""
        img = load_image(str(temp_png))
        assert isinstance(img, Image.Image)


class TestIsSupportedFormat:
    """Tests for is_supported_format function."""

    def test_png_supported(self):
        """Test that PNG is supported."""
        assert is_supported_format("image.png")
        assert is_supported_format("image.PNG")

    def test_jpeg_supported(self):
        """Test that JPEG is supported."""
        assert is_supported_format("image.jpg")
        assert is_supported_format("image.jpeg")
        assert is_supported_format("image.JPEG")

    def test_tiff_supported(self):
        """Test that TIFF is supported."""
        assert is_supported_format("image.tiff")
        assert is_supported_format("image.tif")

    def test_bmp_supported(self):
        """Test that BMP is supported."""
        assert is_supported_format("image.bmp")

    def test_unsupported_format(self):
        """Test unsupported format detection."""
        assert not is_supported_format("image.xyz")
        assert not is_supported_format("image.pdf")
        assert not is_supported_format("image.svg")

    def test_path_object(self):
        """Test with Path object."""
        assert is_supported_format(Path("image.png"))


class TestGetImageInfo:
    """Tests for get_image_info function."""

    def test_get_info_rgb(self):
        """Test getting info for RGB image."""
        img = Image.new("RGB", (100, 200))
        info = get_image_info(img)
        assert info["width"] == 100
        assert info["height"] == 200
        assert info["mode"] == "RGB"
        assert info["pixels"] == 20000

    def test_get_info_rgba(self):
        """Test getting info for RGBA image."""
        img = Image.new("RGBA", (50, 50))
        info = get_image_info(img)
        assert info["mode"] == "RGBA"
        assert info["pixels"] == 2500

    def test_get_info_grayscale(self):
        """Test getting info for grayscale image."""
        img = Image.new("L", (10, 10))
        info = get_image_info(img)
        assert info["mode"] == "L"


class TestSupportedFormats:
    """Tests for SUPPORTED_FORMATS constant."""

    def test_contains_common_formats(self):
        """Test that common formats are supported."""
        assert ".png" in SUPPORTED_FORMATS
        assert ".jpg" in SUPPORTED_FORMATS
        assert ".jpeg" in SUPPORTED_FORMATS
        assert ".tiff" in SUPPORTED_FORMATS
        assert ".tif" in SUPPORTED_FORMATS
        assert ".bmp" in SUPPORTED_FORMATS

    def test_formats_are_lowercase(self):
        """Test that all formats are lowercase."""
        for fmt in SUPPORTED_FORMATS:
            assert fmt == fmt.lower()
            assert fmt.startswith(".")

"""Unit tests for palette loader."""

import pytest
from pathlib import Path

from lego_image_processor.palette.loader import LegoColor, LegoPalette


class TestLegoColor:
    """Tests for LegoColor dataclass."""

    def test_create_lego_color(self):
        """Test creating a LegoColor instance."""
        color = LegoColor(id=1, name="White", rgb=(255, 255, 255), hex="#FFFFFF")
        assert color.id == 1
        assert color.name == "White"
        assert color.rgb == (255, 255, 255)
        assert color.hex == "#FFFFFF"

    def test_lego_color_is_frozen(self):
        """Test that LegoColor is immutable."""
        color = LegoColor(id=1, name="White", rgb=(255, 255, 255), hex="#FFFFFF")
        with pytest.raises(AttributeError):
            color.name = "Black"

    def test_from_dict(self):
        """Test creating LegoColor from dictionary."""
        data = {"id": 26, "name": "Black", "rgb": [27, 42, 52], "hex": "#1B2A34"}
        color = LegoColor.from_dict(data)
        assert color.id == 26
        assert color.name == "Black"
        assert color.rgb == (27, 42, 52)
        assert color.hex == "#1B2A34"


class TestLegoPalette:
    """Tests for LegoPalette class."""

    def test_load_default_palette(self):
        """Test loading the default LEGO palette."""
        palette = LegoPalette.load_default()
        assert len(palette) > 0
        assert all(isinstance(c, LegoColor) for c in palette.colors)

    def test_palette_contains_basic_colors(self):
        """Test that palette contains basic LEGO colors."""
        palette = LegoPalette.load_default()

        # Check for white
        white = palette.get_by_name("White")
        assert white is not None
        assert white.rgb == (255, 255, 255)

        # Check for black
        black = palette.get_by_name("Black")
        assert black is not None

    def test_get_by_id(self):
        """Test getting color by ID."""
        palette = LegoPalette.load_default()
        color = palette.get_by_id(1)  # White
        assert color is not None
        assert color.name == "White"

    def test_get_by_id_not_found(self):
        """Test getting non-existent color by ID."""
        palette = LegoPalette.load_default()
        assert palette.get_by_id(99999) is None

    def test_get_by_name_case_insensitive(self):
        """Test that color lookup is case-insensitive."""
        palette = LegoPalette.load_default()
        assert palette.get_by_name("WHITE") is not None
        assert palette.get_by_name("white") is not None
        assert palette.get_by_name("White") is not None

    def test_get_rgb_array(self):
        """Test getting all RGB values as array."""
        palette = LegoPalette.load_default()
        rgb_array = palette.get_rgb_array()
        assert len(rgb_array) == len(palette)
        assert all(len(rgb) == 3 for rgb in rgb_array)
        assert all(all(0 <= c <= 255 for c in rgb) for rgb in rgb_array)

    def test_palette_iteration(self):
        """Test iterating over palette colors."""
        palette = LegoPalette.load_default()
        colors = list(palette)
        assert len(colors) == len(palette)
        assert all(isinstance(c, LegoColor) for c in colors)

    def test_palette_length(self):
        """Test palette length."""
        palette = LegoPalette.load_default()
        assert len(palette) >= 40  # At least 40 colors in official palette

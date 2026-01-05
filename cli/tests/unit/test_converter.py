"""Unit tests for color space converter."""

import pytest
import numpy as np

from lego_image_processor.palette.converter import (
    rgb_to_xyz,
    xyz_to_lab,
    rgb_to_lab,
    lab_to_xyz,
    xyz_to_rgb,
    lab_to_rgb
)


class TestRgbToXyz:
    """Tests for RGB to XYZ conversion."""

    def test_black(self):
        """Test converting black."""
        rgb = np.array([[0, 0, 0]], dtype=np.float64)
        xyz = rgb_to_xyz(rgb)
        np.testing.assert_array_almost_equal(xyz[0], [0, 0, 0], decimal=2)

    def test_white(self):
        """Test converting white."""
        rgb = np.array([[255, 255, 255]], dtype=np.float64)
        xyz = rgb_to_xyz(rgb)
        # White should be close to D65 reference white
        assert xyz[0, 0] > 90  # X
        assert xyz[0, 1] > 90  # Y
        assert xyz[0, 2] > 90  # Z

    def test_red(self):
        """Test converting pure red."""
        rgb = np.array([[255, 0, 0]], dtype=np.float64)
        xyz = rgb_to_xyz(rgb)
        assert xyz[0, 0] > xyz[0, 1]  # X should be higher for red
        assert xyz[0, 0] > xyz[0, 2]

    def test_batch_processing(self):
        """Test converting multiple colors at once."""
        rgb = np.array([
            [255, 255, 255],
            [0, 0, 0],
            [255, 0, 0]
        ], dtype=np.float64)
        xyz = rgb_to_xyz(rgb)
        assert xyz.shape == (3, 3)


class TestXyzToLab:
    """Tests for XYZ to LAB conversion."""

    def test_white(self):
        """Test converting white reference point."""
        # D65 white in XYZ
        xyz = np.array([[95.047, 100.0, 108.883]], dtype=np.float64)
        lab = xyz_to_lab(xyz)
        # Should be L*=100, a*=0, b*=0
        assert lab[0, 0] > 99  # L close to 100
        np.testing.assert_array_almost_equal(lab[0, 1:], [0, 0], decimal=1)

    def test_black(self):
        """Test converting black."""
        xyz = np.array([[0, 0, 0]], dtype=np.float64)
        lab = xyz_to_lab(xyz)
        assert lab[0, 0] < 1  # L close to 0


class TestRgbToLab:
    """Tests for RGB to LAB conversion."""

    def test_white(self):
        """Test converting white."""
        rgb = np.array([[255, 255, 255]], dtype=np.float64)
        lab = rgb_to_lab(rgb)
        assert lab[0, 0] > 99  # L close to 100

    def test_black(self):
        """Test converting black."""
        rgb = np.array([[0, 0, 0]], dtype=np.float64)
        lab = rgb_to_lab(rgb)
        assert lab[0, 0] < 1  # L close to 0

    def test_pure_red(self):
        """Test converting pure red."""
        rgb = np.array([[255, 0, 0]], dtype=np.float64)
        lab = rgb_to_lab(rgb)
        assert lab[0, 1] > 0  # a* positive (red)

    def test_pure_green(self):
        """Test converting pure green."""
        rgb = np.array([[0, 255, 0]], dtype=np.float64)
        lab = rgb_to_lab(rgb)
        assert lab[0, 1] < 0  # a* negative (green)

    def test_pure_blue(self):
        """Test converting pure blue."""
        rgb = np.array([[0, 0, 255]], dtype=np.float64)
        lab = rgb_to_lab(rgb)
        assert lab[0, 2] < 0  # b* negative (blue)

    def test_pure_yellow(self):
        """Test converting pure yellow."""
        rgb = np.array([[255, 255, 0]], dtype=np.float64)
        lab = rgb_to_lab(rgb)
        assert lab[0, 2] > 0  # b* positive (yellow)


class TestLabToRgb:
    """Tests for LAB to RGB roundtrip."""

    def test_roundtrip_basic_colors(self):
        """Test that RGB -> LAB -> RGB preserves colors."""
        colors = np.array([
            [255, 255, 255],  # White
            [0, 0, 0],        # Black
            [255, 0, 0],      # Red
            [0, 255, 0],      # Green
            [0, 0, 255],      # Blue
            [128, 128, 128],  # Gray
        ], dtype=np.float64)

        lab = rgb_to_lab(colors)
        rgb_back = lab_to_rgb(lab)

        np.testing.assert_array_almost_equal(colors, rgb_back, decimal=0)

    def test_roundtrip_random_colors(self):
        """Test roundtrip with random colors."""
        np.random.seed(42)
        colors = np.random.randint(0, 256, size=(100, 3)).astype(np.float64)

        lab = rgb_to_lab(colors)
        rgb_back = lab_to_rgb(lab)

        # Allow for small rounding errors
        np.testing.assert_array_almost_equal(colors, rgb_back, decimal=0)

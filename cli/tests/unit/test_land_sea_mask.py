"""Unit tests for LandSeaMask class and loader function."""

import pytest

from lego_image_processor.layout.land_sea_mask import LandSeaMask, load_land_sea_mask


class TestLandSeaMask:
    """Tests for LandSeaMask class."""

    def test_load_land_sea_mask(self):
        """Test loading land/sea mask from fixture."""
        mask = load_land_sea_mask()
        assert mask is not None
        assert isinstance(mask, LandSeaMask)

    def test_mask_dimensions(self):
        """Test mask has correct dimensions."""
        mask = load_land_sea_mask()
        assert mask.width == 128
        assert mask.height == 80
        assert mask.total_positions == 10240

    def test_land_ocean_counts(self):
        """Test correct land and ocean counts."""
        mask = load_land_sea_mask()
        assert mask.land_count == 3062
        assert mask.ocean_count == 7178
        assert mask.land_count + mask.ocean_count == mask.total_positions

    def test_land_ocean_percentages(self):
        """Test land and ocean percentages."""
        mask = load_land_sea_mask()
        assert 29.0 <= mask.land_percentage <= 30.0  # ~29.9%
        assert 70.0 <= mask.ocean_percentage <= 71.0  # ~70.1%

    def test_is_land_ocean_position(self):
        """Test querying land positions at known coordinates."""
        mask = load_land_sea_mask()

        # Position (0, 0) should be ocean (top-left is ocean in world map)
        assert mask.is_land(0, 0) == False

        # Check some positions are classified
        land_found = False
        ocean_found = False
        for y in range(80):
            for x in range(128):
                if mask.is_land(x, y):
                    land_found = True
                else:
                    ocean_found = True
                if land_found and ocean_found:
                    break
            if land_found and ocean_found:
                break

        assert land_found, "No land positions found"
        assert ocean_found, "No ocean positions found"

    def test_get_part_type_land(self):
        """Test get_part_type returns 'brick' for land positions."""
        mask = load_land_sea_mask()

        # Find a land position
        for y in range(80):
            for x in range(128):
                if mask.is_land(x, y):
                    assert mask.get_part_type(x, y) == "brick"
                    return
        pytest.fail("No land position found")

    def test_get_part_type_ocean(self):
        """Test get_part_type returns 'tile' for ocean positions."""
        mask = load_land_sea_mask()

        # Find an ocean position
        for y in range(80):
            for x in range(128):
                if not mask.is_land(x, y):
                    assert mask.get_part_type(x, y) == "tile"
                    return
        pytest.fail("No ocean position found")

    def test_get_lego_part_id_land(self):
        """Test get_lego_part_id returns '3062b' for land positions."""
        mask = load_land_sea_mask()

        # Find a land position
        for y in range(80):
            for x in range(128):
                if mask.is_land(x, y):
                    assert mask.get_lego_part_id(x, y) == "3062b"
                    return
        pytest.fail("No land position found")

    def test_get_lego_part_id_ocean(self):
        """Test get_lego_part_id returns '98138' for ocean positions."""
        mask = load_land_sea_mask()

        # Find an ocean position
        for y in range(80):
            for x in range(128):
                if not mask.is_land(x, y):
                    assert mask.get_lego_part_id(x, y) == "98138"
                    return
        pytest.fail("No ocean position found")

    def test_mask_is_cached(self):
        """Test that mask loading uses cache."""
        mask1 = load_land_sea_mask()
        mask2 = load_land_sea_mask()
        # Should return the same cached instance
        assert mask1 is mask2

    def test_invalid_coordinates(self):
        """Test accessing invalid coordinates raises error."""
        mask = load_land_sea_mask()

        with pytest.raises(IndexError):
            mask.is_land(200, 0)  # x out of range

        with pytest.raises(IndexError):
            mask.is_land(0, 100)  # y out of range

        with pytest.raises(IndexError):
            mask.is_land(-1, 0)  # negative x

        with pytest.raises(IndexError):
            mask.is_land(0, -1)  # negative y

    def test_boundary_coordinates(self):
        """Test mask boundaries work correctly."""
        mask = load_land_sea_mask()

        # Test corners and edges
        # Top-left
        mask.is_land(0, 0)
        # Top-right
        mask.is_land(127, 0)
        # Bottom-left
        mask.is_land(0, 79)
        # Bottom-right
        mask.is_land(127, 79)

    def test_count_matches_data(self):
        """Test that counted land positions matches reported land_count."""
        mask = load_land_sea_mask()

        counted_land = 0
        counted_ocean = 0
        for y in range(80):
            for x in range(128):
                if mask.is_land(x, y):
                    counted_land += 1
                else:
                    counted_ocean += 1

        assert counted_land == mask.land_count
        assert counted_ocean == mask.ocean_count

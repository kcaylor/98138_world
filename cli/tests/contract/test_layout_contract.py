"""Contract tests for layout CLI command."""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest


# Get path to test fixtures
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
IMAGES_DIR = FIXTURES_DIR / "images"


class TestLayoutContract:
    """Contract tests for layout command input/output."""

    def test_valid_input_produces_json_output(self):
        """Test that valid input produces valid JSON output with exit code 0."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = f.name

        try:
            result = subprocess.run(
                ["lego-image-processor", "layout",
                 str(IMAGES_DIR / "test_128x80_quantized.png"),
                 "-o", output_path, "-q"],
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, f"Command failed: {result.stderr}"

            # Verify output is valid JSON
            with open(output_path) as f:
                data = json.load(f)

            assert "metadata" in data
            assert "positions" in data
            assert data["metadata"]["total_positions"] == 10240
            assert data["metadata"]["land_positions"] == 3062
            assert data["metadata"]["ocean_positions"] == 7178
            assert len(data["positions"]) == 10240
        finally:
            os.unlink(output_path)

    def test_valid_input_produces_csv_output(self):
        """Test that valid input produces valid CSV output."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            output_path = f.name

        try:
            result = subprocess.run(
                ["lego-image-processor", "layout",
                 str(IMAGES_DIR / "test_128x80_quantized.png"),
                 "-o", output_path, "-f", "csv", "-q"],
                capture_output=True,
                text=True
            )

            assert result.returncode == 0, f"Command failed: {result.stderr}"

            # Verify output is valid CSV
            with open(output_path) as f:
                lines = f.readlines()

            # Header + 10240 positions
            assert len(lines) == 10241, f"Expected 10241 lines, got {len(lines)}"

            # Check header
            header = lines[0].strip()
            assert "x_position" in header
            assert "y_position" in header
            assert "color_id" in header
            assert "part_type" in header
        finally:
            os.unlink(output_path)

    def test_missing_file_produces_error(self):
        """Test that missing file produces error with exit code 1."""
        result = subprocess.run(
            ["lego-image-processor", "layout",
             "nonexistent.png", "-o", "output.json", "-q"],
            capture_output=True,
            text=True
        )

        assert result.returncode != 0
        # Error message should be present
        assert "Error" in result.stderr or "error" in result.stderr.lower() or result.returncode == 2

    def test_wrong_dimensions_produces_error(self):
        """Test that wrong dimensions produce error with resize suggestion."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = f.name

        try:
            result = subprocess.run(
                ["lego-image-processor", "layout",
                 str(IMAGES_DIR / "test_wrong_size.png"),
                 "-o", output_path, "-q"],
                capture_output=True,
                text=True
            )

            assert result.returncode != 0
            # Should mention expected dimensions
            assert "128" in result.stderr or "80" in result.stderr
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_invalid_colors_produces_error(self):
        """Test that invalid colors produce error with re-quantize suggestion."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = f.name

        try:
            result = subprocess.run(
                ["lego-image-processor", "layout",
                 str(IMAGES_DIR / "test_invalid_colors.png"),
                 "-o", output_path, "-q"],
                capture_output=True,
                text=True
            )

            assert result.returncode != 0
            # Should mention invalid color
            assert "Invalid color" in result.stderr or "color" in result.stderr.lower()
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_output_matches_schema(self):
        """Test that JSON output matches expected schema structure."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = f.name

        try:
            result = subprocess.run(
                ["lego-image-processor", "layout",
                 str(IMAGES_DIR / "test_128x80_quantized.png"),
                 "-o", output_path, "-q"],
                capture_output=True,
                text=True
            )

            assert result.returncode == 0

            with open(output_path) as f:
                data = json.load(f)

            # Check metadata fields
            metadata = data["metadata"]
            assert "width" in metadata
            assert "height" in metadata
            assert "total_positions" in metadata
            assert "land_positions" in metadata
            assert "ocean_positions" in metadata
            assert "unique_colors" in metadata
            assert "generated_at" in metadata
            assert "source_image" in metadata
            assert "schema_version" in metadata
            assert "coordinate_system" in metadata

            # Check position fields
            pos = data["positions"][0]
            assert "x" in pos
            assert "y" in pos
            assert "color_id" in pos
            assert "color_name" in pos
            assert "lego_color_code" in pos
            assert "part_type" in pos
            assert "lego_part_id" in pos

            # Check statistics
            assert "statistics" in data
            stats = data["statistics"]
            assert "total_tile_count" in stats
            assert "land_brick_count" in stats
            assert "ocean_tile_count" in stats
        finally:
            os.unlink(output_path)

    def test_positions_have_valid_part_types(self):
        """Test that all positions have valid part types."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = f.name

        try:
            result = subprocess.run(
                ["lego-image-processor", "layout",
                 str(IMAGES_DIR / "test_128x80_quantized.png"),
                 "-o", output_path, "-q"],
                capture_output=True,
                text=True
            )

            assert result.returncode == 0

            with open(output_path) as f:
                data = json.load(f)

            for pos in data["positions"]:
                assert pos["part_type"] in ["brick", "tile"]
                if pos["part_type"] == "brick":
                    assert pos["lego_part_id"] == "3062b"
                else:
                    assert pos["lego_part_id"] == "98138"
        finally:
            os.unlink(output_path)

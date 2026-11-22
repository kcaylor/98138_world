"""Contract tests for layout CLI command."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


# Get path to test fixtures
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
IMAGES_DIR = FIXTURES_DIR / "images"

# Prefer the entry point installed alongside the running interpreter, so the
# tests work without an activated virtualenv; fall back to PATH.
_VENV_CLI = Path(sys.executable).parent / "lego-image-processor"
CLI = str(_VENV_CLI) if _VENV_CLI.exists() else (shutil.which("lego-image-processor") or "lego-image-processor")


class TestLayoutContract:
    """Contract tests for layout command input/output."""

    def test_valid_input_produces_json_output(self):
        """Test that valid input produces valid JSON output with exit code 0."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = f.name

        try:
            result = subprocess.run(
                [CLI, "layout",
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
                [CLI, "layout",
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
            [CLI, "layout",
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
                [CLI, "layout",
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
                [CLI, "layout",
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
                [CLI, "layout",
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
            assert "land_plate_count" in stats
            assert stats["land_plate_count"] == 3062
            assert set(stats["color_frequency_by_part_type"]) == {"plate", "tile"}
            assert metadata["schema_version"] == "2.0"
            assert metadata["disclaimer"] == "Not affiliated with or endorsed by The LEGO Group."
            assert "ocean_tile_count" in stats
        finally:
            os.unlink(output_path)

    def test_positions_have_valid_part_types(self):
        """Test that all positions have valid part types."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = f.name

        try:
            result = subprocess.run(
                [CLI, "layout",
                 str(IMAGES_DIR / "test_128x80_quantized.png"),
                 "-o", output_path, "-q"],
                capture_output=True,
                text=True
            )

            assert result.returncode == 0

            with open(output_path) as f:
                data = json.load(f)

            for pos in data["positions"]:
                assert pos["part_type"] in ["plate", "tile"]
                if pos["part_type"] == "plate":
                    assert pos["lego_part_id"] == "6141"
                else:
                    assert pos["lego_part_id"] == "98138"
        finally:
            os.unlink(output_path)


class TestLayoutSchema2Contract:
    """Schema 2.0 output and human summary (contracts/cli.md `layout`, US1-4)."""

    def test_summary_lines_and_disclaimer(self, tmp_path):
        out = tmp_path / "l.json"
        result = subprocess.run(
            [CLI, "layout", str(IMAGES_DIR / "test_128x80_quantized.png"), "-o", str(out)],
            capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert "Land plates (6141): 3,062 (29.9%)" in result.stdout
        assert "Ocean tiles (98138): 7,178 (70.1%)" in result.stdout
        assert result.stdout.strip().splitlines()[-1] == "Not affiliated with or endorsed by The LEGO Group."

    def test_csv_land_rows_use_plate_6141(self, tmp_path):
        out = tmp_path / "l.csv"
        result = subprocess.run(
            [CLI, "layout", str(IMAGES_DIR / "test_128x80_quantized.png"), "-o", str(out),
             "-f", "csv", "-q"], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        rows = out.read_text().strip().splitlines()[1:]
        land = [r for r in rows if r.endswith(",plate,6141")]
        ocean = [r for r in rows if r.endswith(",tile,98138")]
        assert len(land) == 3062
        assert len(ocean) == 7178

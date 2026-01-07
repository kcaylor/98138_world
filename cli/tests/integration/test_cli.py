"""Integration tests for CLI commands."""

import pytest
import tempfile
import os
from pathlib import Path
from PIL import Image
from click.testing import CliRunner

from lego_image_processor.cli.main import cli


class TestQuantizeCommand:
    """Integration tests for quantize command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_image(self):
        """Create a temporary test image."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new("RGB", (100, 100), color=(200, 50, 50))
            img.save(f.name)
            yield Path(f.name)
        os.unlink(f.name)

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as d:
            yield Path(d)

    def test_quantize_basic(self, runner, temp_image, temp_dir):
        """Test basic quantize command."""
        output_path = temp_dir / "output.png"
        result = runner.invoke(cli, [
            "quantize", str(temp_image), "-o", str(output_path)
        ])

        assert result.exit_code == 0, f"CLI error: {result.output}"
        assert output_path.exists()

        # Verify output is valid image
        img = Image.open(output_path)
        assert img.size == (100, 100)

    def test_quantize_default_output(self, runner, temp_image):
        """Test quantize with default output path."""
        result = runner.invoke(cli, ["quantize", str(temp_image)])

        assert result.exit_code == 0

        # Default output should be input_lego.png
        expected_output = temp_image.parent / f"{temp_image.stem}_lego.png"
        assert expected_output.exists()
        os.unlink(expected_output)

    def test_quantize_verbose(self, runner, temp_image, temp_dir):
        """Test quantize with verbose output."""
        output_path = temp_dir / "output.png"
        result = runner.invoke(cli, [
            "quantize", str(temp_image), "-o", str(output_path), "-v"
        ])

        assert result.exit_code == 0
        assert "Loading image" in result.output
        assert "Image size" in result.output

    def test_quantize_nonexistent_file(self, runner):
        """Test quantize with non-existent file."""
        result = runner.invoke(cli, ["quantize", "/nonexistent/file.png"])
        assert result.exit_code != 0

    def test_quantize_jpeg_quality(self, runner, temp_image, temp_dir):
        """Test quantize with JPEG quality option."""
        output_path = temp_dir / "output.jpg"
        result = runner.invoke(cli, [
            "quantize", str(temp_image),
            "-o", str(output_path),
            "-q", "50"
        ])

        assert result.exit_code == 0
        assert output_path.exists()


class TestStatsCommand:
    """Integration tests for stats command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_image(self):
        """Create a temporary test image."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new("RGB", (50, 50), color=(255, 255, 255))
            img.save(f.name)
            yield Path(f.name)
        os.unlink(f.name)

    def test_stats_basic(self, runner, temp_image):
        """Test basic stats command."""
        result = runner.invoke(cli, ["stats", str(temp_image)])

        assert result.exit_code == 0
        assert "File:" in result.output
        assert "Size:" in result.output
        assert "50x50" in result.output

    def test_stats_json(self, runner, temp_image):
        """Test stats with JSON output."""
        result = runner.invoke(cli, ["stats", str(temp_image), "--json"])

        assert result.exit_code == 0

        import json
        data = json.loads(result.output)
        assert data["width"] == 50
        assert data["height"] == 50
        assert "total_pixels" in data

    def test_stats_top_colors(self, runner, temp_image):
        """Test stats with top N colors."""
        result = runner.invoke(cli, ["stats", str(temp_image), "-n", "5"])

        assert result.exit_code == 0
        assert "Top 5 colors" in result.output

    def test_stats_nonexistent_file(self, runner):
        """Test stats with non-existent file."""
        result = runner.invoke(cli, ["stats", "/nonexistent/file.png"])
        assert result.exit_code != 0


class TestMainCli:
    """Tests for main CLI group."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_help(self, runner):
        """Test --help flag."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "LEGO Image Processor" in result.output
        assert "quantize" in result.output
        assert "stats" in result.output

    def test_version(self, runner):
        """Test --version flag."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_quantize_help(self, runner):
        """Test quantize --help."""
        result = runner.invoke(cli, ["quantize", "--help"])
        assert result.exit_code == 0
        assert "Quantize an image" in result.output

    def test_stats_help(self, runner):
        """Test stats --help."""
        result = runner.invoke(cli, ["stats", "--help"])
        assert result.exit_code == 0
        assert "color statistics" in result.output

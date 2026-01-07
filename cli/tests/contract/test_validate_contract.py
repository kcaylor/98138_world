"""Contract tests for validate command output format."""

import json
import pytest
from pathlib import Path
from click.testing import CliRunner

from lego_image_processor.cli.main import cli


class TestValidateContractOutput:
    """Tests that validate command output matches expected contract."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def layout_file(self):
        """Path to test layout file."""
        return Path(__file__).parent.parent / "fixtures" / "layouts" / "expected_test_128x80.json"

    def test_validate_json_output_schema(self, runner, layout_file, tmp_path):
        """Test that validation report JSON matches expected schema."""
        output_file = tmp_path / "report.json"

        result = runner.invoke(cli, [
            "validate",
            str(layout_file),
            "-o", str(output_file)
        ])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert output_file.exists()

        with open(output_file, "r", encoding="utf-8") as f:
            report = json.load(f)

        # Check required top-level fields
        assert "buildable" in report
        assert "buildability_score" in report
        assert "violations" in report
        assert "validated_at" in report
        assert "kit_id" in report
        assert "layout_file" in report

        # Check field types
        assert isinstance(report["buildable"], bool)
        assert isinstance(report["buildability_score"], (int, float))
        assert isinstance(report["violations"], list)
        assert isinstance(report["validated_at"], str)
        assert isinstance(report["kit_id"], str)
        assert isinstance(report["layout_file"], str)

        # Check score range
        assert 0.0 <= report["buildability_score"] <= 1.0

        # Check timestamp format (ISO 8601)
        assert "T" in report["validated_at"]

    def test_validate_violation_schema(self, runner, layout_file, tmp_path):
        """Test that violation objects match expected schema."""
        output_file = tmp_path / "report.json"

        result = runner.invoke(cli, [
            "validate",
            str(layout_file),
            "-o", str(output_file)
        ])

        assert result.exit_code == 0

        with open(output_file, "r", encoding="utf-8") as f:
            report = json.load(f)

        for violation in report["violations"]:
            # All violations must have these fields
            assert "type" in violation
            assert violation["type"] in ["color_unavailable", "quantity_exceeded"]
            assert "part_type" in violation
            assert violation["part_type"] in ["brick", "tile"]
            assert "part_id" in violation
            assert "color_id" in violation
            assert "color_name" in violation
            assert "positions_required" in violation

            if violation["type"] == "color_unavailable":
                # May have suggested_alternative
                if "suggested_alternative" in violation and violation["suggested_alternative"]:
                    alt = violation["suggested_alternative"]
                    assert "color_id" in alt
                    assert "color_name" in alt
                    assert "color_distance" in alt

            elif violation["type"] == "quantity_exceeded":
                assert "kit_quantity" in violation
                assert "shortfall" in violation

    def test_validate_cli_output_format(self, runner, layout_file):
        """Test that CLI output has expected format."""
        result = runner.invoke(cli, ["validate", str(layout_file)])

        assert result.exit_code == 0

        # Check key sections appear in output
        assert "Loading layout:" in result.output
        assert "Total positions:" in result.output
        assert "Land bricks:" in result.output
        assert "Ocean tiles:" in result.output
        assert "Loading kit specification:" in result.output
        assert "Validating layout against kit..." in result.output
        assert "Validation complete!" in result.output
        assert "Buildability:" in result.output

    def test_validate_kit_option(self, runner, layout_file, tmp_path):
        """Test that --kit option is reflected in report."""
        output_file = tmp_path / "report.json"

        result = runner.invoke(cli, [
            "validate",
            str(layout_file),
            "--kit", "31203",
            "-o", str(output_file)
        ])

        assert result.exit_code == 0

        with open(output_file, "r", encoding="utf-8") as f:
            report = json.load(f)

        assert report["kit_id"] == "31203"

    def test_validate_handles_missing_file(self, runner, tmp_path):
        """Test that validate handles missing file gracefully."""
        result = runner.invoke(cli, ["validate", str(tmp_path / "nonexistent.json")])

        assert result.exit_code != 0

    def test_validate_handles_invalid_json(self, runner, tmp_path):
        """Test that validate handles invalid JSON gracefully."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{ invalid json }", encoding="utf-8")

        result = runner.invoke(cli, ["validate", str(invalid_file)])

        assert result.exit_code != 0


class TestValidateReportConsistency:
    """Tests for validation report consistency."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def layout_file(self):
        """Path to test layout file."""
        return Path(__file__).parent.parent / "fixtures" / "layouts" / "expected_test_128x80.json"

    def test_buildable_implies_no_blocking_violations(self, runner, layout_file, tmp_path):
        """Test that buildable=true implies no critical violations."""
        output_file = tmp_path / "report.json"

        result = runner.invoke(cli, [
            "validate",
            str(layout_file),
            "-o", str(output_file)
        ])

        assert result.exit_code == 0

        with open(output_file, "r", encoding="utf-8") as f:
            report = json.load(f)

        if report["buildable"]:
            # If buildable, score should be 1.0
            assert report["buildability_score"] == 1.0
            # No violations should exist
            assert len(report["violations"]) == 0

    def test_violations_imply_not_fully_buildable(self, runner, layout_file, tmp_path):
        """Test that violations reduce buildability."""
        output_file = tmp_path / "report.json"

        result = runner.invoke(cli, [
            "validate",
            str(layout_file),
            "-o", str(output_file)
        ])

        assert result.exit_code == 0

        with open(output_file, "r", encoding="utf-8") as f:
            report = json.load(f)

        if len(report["violations"]) > 0:
            # Should not be fully buildable
            assert not report["buildable"]
            # Score should be less than 1.0
            assert report["buildability_score"] < 1.0

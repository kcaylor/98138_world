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
            assert violation["part_type"] in ["plate", "tile"]
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
        assert "Land plates:" in result.output
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


# --- US3 (feature 003): validate against the real kit (T062, contracts/cli.md `validate`) -------

import re

from lego_image_processor.layout.grid import DISCLAIMER, PositionPlacementGrid
from lego_image_processor.layout.position import PositionPlacement

FIXTURES = Path(__file__).parent.parent / "fixtures" / "layouts"


def _write_layout(path, specs):
    """specs: list of (color_id, color_name, code, part_type, count)."""
    positions = []
    for color_id, name, code, part_type, count in specs:
        for _ in range(count):
            positions.append(PositionPlacement(
                x=len(positions), y=0, color_id=color_id, color_name=name, lego_color_code=code,
                part_type=part_type, lego_part_id="6141" if part_type == "plate" else "98138"))
    grid = PositionPlacementGrid(width=len(positions), height=1, positions=positions,
                                 source_image="t.png")
    path.write_text(grid.to_json(), encoding="utf-8")
    return path


class TestValidateRealKitContract:

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def violating_layout(self, tmp_path):
        return _write_layout(tmp_path / "bad.json", [
            ("lego_white", "White", "1", "plate", 2),
            ("lego_bright_blue", "Bright Blue", "23", "tile", 5),
            ("lego_earth_blue", "Earth Blue", "140", "tile", 400),
        ])

    def test_legacy_schema_rejected_with_regenerate_message(self, runner):
        result = runner.invoke(cli, ["validate", str(FIXTURES / "legacy_v1_layout.json")])
        assert result.exit_code == 1
        assert ("Error: Layout schema version 1.0 is no longer supported (land is now part 6141, "
                "a 1x1 round plate). Regenerate it with: lego-image-processor layout <image> "
                "-o <layout.json>") in result.output

    def test_kit_summary_lines(self, runner, violating_layout):
        result = runner.invoke(cli, ["validate", str(violating_layout)])
        assert result.exit_code == 0, result.output
        assert "  Land plates: 2" in result.output
        assert "  Ocean tiles: 405" in result.output
        assert "  Plate colors: 1" in result.output
        assert "  Tile colors: 9" in result.output
        assert "  Inventory: 32 lines, cited from instructions page 159" in result.output

    def test_color_detail_line_uses_delta_e00(self, runner, violating_layout):
        result = runner.invoke(cli, ["validate", str(violating_layout)])
        out = result.output
        assert "Color Unavailable: Bright Blue (lego_bright_blue)" in out
        assert "Part type: tile (98138)" in out
        assert "Positions required: 5" in out
        assert re.search(r"Suggested alternative: [A-Z][A-Za-z ]+ \(ΔE00 \d+\.\d\)", out), out

    def test_quantity_detail_lines(self, runner, violating_layout):
        out = runner.invoke(cli, ["validate", str(violating_layout)]).output
        assert "Quantity Exceeded: Earth Blue (lego_earth_blue)" in out
        assert "Required: 400, Available: 393" in out
        assert "Shortfall: 7" in out

    def test_report_json_has_disclaimer_and_part_types(self, runner, violating_layout, tmp_path):
        report_path = tmp_path / "report.json"
        result = runner.invoke(cli, ["validate", str(violating_layout), "-o", str(report_path)])
        assert result.exit_code == 0
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["disclaimer"] == DISCLAIMER
        assert {v["part_type"] for v in report["violations"]} == {"tile"}
        assert {v["part_id"] for v in report["violations"]} == {"98138"}

    @pytest.mark.parametrize("name", ["violating", "buildable"])
    def test_disclaimer_is_last_line(self, runner, violating_layout, tmp_path, name):
        path = violating_layout if name == "violating" else _write_layout(
            tmp_path / "ok.json", [("lego_white", "White", "1", "plate", 3)])
        result = runner.invoke(cli, ["validate", str(path)])
        assert result.exit_code == 0
        assert result.output.rstrip("\n").splitlines()[-1] == DISCLAIMER


# --- a layout on a non-kit template (feature 016 T068; contracts/cli.md `validate`) --------------

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."


@pytest.fixture
def winkel_file(confirmed_winkel, tmp_path):
    from ..winkel_layouts import winkel_grid
    p = tmp_path / "winkel.json"
    p.write_text(winkel_grid(confirmed_winkel).to_json(), encoding="utf-8")
    return p


def test_validate_winkel_layout(winkel_file, confirmed_winkel, tmp_path):
    out = tmp_path / "report.json"
    r = CliRunner().invoke(cli, ["validate", str(winkel_file), "-o", str(out)])
    assert r.exit_code == 0, r.output
    c = confirmed_winkel.counts
    assert f"  Margin square tiles: {c['margin']:,}" in r.output
    assert f"  Template: winkel-tripel ({confirmed_winkel.title}); arrangement A only" in r.output
    assert "Checking template classes (winkel-tripel)..." in r.output
    assert "✓ Plates on land, tiles on ocean and square tiles on the margin" in r.output
    assert "1 square tile colors unavailable in kit (no kit has part 3070b)" in r.output
    assert "Part type: square_tile (3070b)" in r.output
    assert r.output.rstrip("\n").splitlines()[-1] == DISCLAIMER
    report = json.loads(out.read_text())
    assert report["template"] == {"id": "winkel-tripel", "title": confirmed_winkel.title}
    sq = [v for v in report["violations"] if v["part_type"] == "square_tile"]
    assert [(v["type"], v["part_id"], v["positions_required"]) for v in sq] == \
        [("color_unavailable", "3070b", c["margin"])]
    assert "suggested_alternative" not in sq[0]


def test_validate_unknown_template_exit_1(winkel_file, tmp_path):
    d = json.loads(winkel_file.read_text())
    d["metadata"]["template"]["id"] = "no-such-template"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(d), encoding="utf-8")
    r = CliRunner().invoke(cli, ["validate", str(bad)])
    assert r.exit_code == 1 and "no-such-template" in r.output


def test_validate_kit_layout_has_no_template_lines():
    layout = Path(__file__).parent.parent / "fixtures" / "layouts" / "expected_test_128x80.json"
    r = CliRunner().invoke(cli, ["validate", str(layout)])
    assert r.exit_code == 0, r.output
    assert "Template" not in r.output and "square" not in r.output and "Margin" not in r.output
    assert "Checking land/sea mask (arrangement A)..." in r.output


# --- a layout with the in-margin plaque (feature 017 T065; contracts/in-margin-plaque.md) --------

@pytest.fixture
def plaque_file(confirmed_winkel, tmp_path):
    from lego_image_processor.maps.margin import place_plaque
    from ..winkel_layouts import winkel_grid
    p = tmp_path / "plaque.json"
    rec = place_plaque(confirmed_winkel, "bottom-left", "option").layout_record()
    p.write_text(winkel_grid(confirmed_winkel, plaque=rec).to_json(), encoding="utf-8")
    return p


def test_validate_accepts_the_plaque_studs(plaque_file, confirmed_winkel, tmp_path):
    out = tmp_path / "report.json"
    r = CliRunner().invoke(cli, ["validate", str(plaque_file), "-o", str(out)])
    assert r.exit_code == 0, r.output
    assert "✓ Plates on land, tiles on ocean and square tiles on the margin" in r.output
    report = json.loads(out.read_text())
    assert not [v for v in report["violations"] if v["type"] == "mask_mismatch"]
    (sq,) = [v for v in report["violations"] if v["part_type"] == "square_tile"]
    assert sq["positions_required"] == confirmed_winkel.counts["margin"] - 36
    assert r.output.rstrip("\n").splitlines()[-1] == DISCLAIMER


def test_validate_reports_the_plaque_tile_beyond_the_kit(plaque_file, confirmed_winkel, tmp_path):
    """T082: the plaque's tile is reported as 016 reports the square tiles (no kit has it), and its
    36 studs are not counted as buildable with the kit."""
    out = tmp_path / "report.json"
    r = CliRunner().invoke(cli, ["validate", str(plaque_file), "-o", str(out)])
    assert r.exit_code == 0, r.output
    report = json.loads(out.read_text())
    (pl,) = [v for v in report["violations"] if v["part_type"] == "plaque_tile"]
    assert pl == {"type": "color_unavailable", "part_type": "plaque_tile", "part_id": "10202",
                  "color_id": "lego_black", "color_name": "Black", "positions_required": 36}
    lost = sum(v.get("shortfall", v["positions_required"]) for v in report["violations"])
    assert report["buildability_score"] == round((10240 - lost) / 10240, 4)
    assert "  Checking the plaque tile...\n    ✗ tile 6x6 (part 10202) unavailable in kit (no kit has part 10202)\n" \
        in r.output
    assert ("  Color Unavailable: Black (lego_black)\n    Part type: plaque_tile (10202)\n"
            "    Positions required: 36 (studs under one tile 6x6)\n") in r.output
    assert f"  Buildability: {(10240 - lost) / 10240 * 100:.1f}% (PARTIALLY BUILDABLE)" in r.output
    assert f"  Violations: {len(report['violations'])}" in r.output


def test_validate_without_a_plaque_has_no_plaque_lines(confirmed_winkel, tmp_path):
    from ..winkel_layouts import winkel_grid
    p = tmp_path / "w.json"
    p.write_text(winkel_grid(confirmed_winkel).to_json(), encoding="utf-8")
    r = CliRunner().invoke(cli, ["validate", str(p)])
    assert r.exit_code == 0, r.output
    assert "plaque" not in r.output.split("\n", 1)[1].lower()  # the first line names the file


def test_validate_refuses_another_absent_position(plaque_file, confirmed_winkel, tmp_path):
    d = json.loads(plaque_file.read_text())
    gone = next(p for p in d["positions"] if p["part_type"] == "tile")
    d["positions"].remove(gone)
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(d), encoding="utf-8")
    out = tmp_path / "report.json"
    r = CliRunner().invoke(cli, ["validate", str(bad), "-o", str(out)])
    assert r.exit_code == 0, r.output
    assert "1 positions do not match template winkel-tripel" in r.output
    (mm,) = [v for v in json.loads(out.read_text())["violations"] if v["type"] == "mask_mismatch"]
    assert mm["examples"] == [{"x": gone["x"], "y": gone["y"], "part_type": None, "expected": "tile"}]

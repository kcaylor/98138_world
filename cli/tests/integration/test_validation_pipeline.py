"""Integration tests for end-to-end validation pipeline."""

import json
import pytest
from pathlib import Path
from PIL import Image
from click.testing import CliRunner

from lego_image_processor.cli.main import cli
from lego_image_processor.palette.loader import LegoPalette
from lego_image_processor.layout.generator import LayoutGenerator
from lego_image_processor.layout.land_sea_mask import load_land_sea_mask
from lego_image_processor.layout.kit_spec import load_kit_specification
from lego_image_processor.layout.validator import LayoutValidator


class TestValidationPipelineIntegration:
    """End-to-end tests for image → layout → validation pipeline."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def palette(self):
        """Load the default LEGO palette."""
        return LegoPalette.load_default()

    @pytest.fixture
    def kit_spec(self):
        """Load the kit specification."""
        return load_kit_specification("31203")

    @pytest.fixture
    def land_sea_mask(self):
        """Load the land/sea mask."""
        return load_land_sea_mask()

    def test_full_pipeline_with_valid_colors(self, palette, kit_spec, land_sea_mask, tmp_path):
        """Test full pipeline with colors that are all in the kit."""
        # Create image using only kit-available colors
        # Earth Blue is one of the 9 kit tile colors
        earth_blue = palette.get_by_name("Earth Blue")
        image = Image.new("RGB", (128, 80), earth_blue.rgb)

        # Generate layout
        generator = LayoutGenerator(palette=palette, land_sea_mask=land_sea_mask)
        layout = generator.generate(image, source_filename="test.png")

        # Validate layout
        validator = LayoutValidator(kit_spec=kit_spec, palette=palette)
        report = validator.validate(layout, layout_file="test.json")

        # Check results
        assert report.kit_id == "31203"
        assert report.validated_at is not None
        # Note: may have quantity violations depending on color distribution

    def test_full_pipeline_cli(self, runner, palette, tmp_path):
        """Test full pipeline through CLI commands."""
        # Create a quantized test image
        first_color = palette.colors[0]
        image = Image.new("RGB", (128, 80), first_color.rgb)
        image_path = tmp_path / "test_image.png"
        image.save(image_path)

        # Generate layout using CLI
        layout_path = tmp_path / "layout.json"
        result = runner.invoke(cli, [
            "layout",
            str(image_path),
            "-o", str(layout_path),
            "-f", "json"
        ])
        assert result.exit_code == 0, f"Layout generation failed: {result.output}"
        assert layout_path.exists()

        # Validate layout using CLI
        report_path = tmp_path / "report.json"
        result = runner.invoke(cli, [
            "validate",
            str(layout_path),
            "-o", str(report_path)
        ])
        assert result.exit_code == 0, f"Validation failed: {result.output}"
        assert report_path.exists()

        # Verify report structure
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)

        assert "buildable" in report
        assert "buildability_score" in report
        assert "violations" in report

    def test_pipeline_with_unavailable_plate_color(self, palette, kit_spec, land_sea_mask, tmp_path):
        """Test pipeline detects unavailable plate colors."""
        # Black is not a kit color for the land plate (only White is)
        black = palette.get_by_name("Black")
        image = Image.new("RGB", (128, 80), black.rgb)

        # Generate layout
        generator = LayoutGenerator(palette=palette, land_sea_mask=land_sea_mask)
        layout = generator.generate(image, source_filename="test.png")

        # Validate layout
        validator = LayoutValidator(kit_spec=kit_spec, palette=palette)
        report = validator.validate(layout, layout_file="test.json")

        # Should have violations for black plates on land
        plate_violations = [v for v in report.violations
                          if v.part_type == "plate" and v.type == "color_unavailable"]

        # If there are land positions, should have violations
        if layout.land_positions > 0:
            assert len(plate_violations) > 0, "Should detect black plate as unavailable"

    def test_pipeline_with_quantity_exceeded(self, palette, kit_spec, land_sea_mask, tmp_path):
        """Test pipeline detects quantity exceeded violations."""
        # Earth Blue is a kit tile color with 393 tiles; 7,178 ocean positions need more
        earth_blue = palette.get_by_name("Earth Blue")
        image = Image.new("RGB", (128, 80), earth_blue.rgb)

        # Generate layout
        generator = LayoutGenerator(palette=palette, land_sea_mask=land_sea_mask)
        layout = generator.generate(image, source_filename="test.png")

        # Validate layout
        validator = LayoutValidator(kit_spec=kit_spec, palette=palette)
        report = validator.validate(layout, layout_file="test.json")

        # Should have quantity exceeded violations
        quantity_violations = [v for v in report.violations if v.type == "quantity_exceeded"]

        # 7,178 ocean positions in Earth Blue exceed the 393 supplied
        assert len(quantity_violations) > 0, "Should detect quantity exceeded"
        tile_exceeded = [v for v in quantity_violations if v.part_type == "tile"]
        assert tile_exceeded[0].kit_quantity == 393
        assert tile_exceeded[0].shortfall == 7178 - 393
        assert not report.buildable

    def test_pipeline_preserves_position_count(self, palette, land_sea_mask, kit_spec, tmp_path):
        """Test that validation counts match layout positions."""
        # Use White which has good availability
        white = palette.get_by_name("White")
        image = Image.new("RGB", (128, 80), white.rgb)

        # Generate layout
        generator = LayoutGenerator(palette=palette, land_sea_mask=land_sea_mask)
        layout = generator.generate(image, source_filename="test.png")

        # Validate layout
        validator = LayoutValidator(kit_spec=kit_spec, palette=palette)
        report = validator.validate(layout, layout_file="test.json")

        # Total positions should be 128 * 80 = 10,240
        assert layout.total_positions == 10240

        # Violations should reference correct position counts
        for v in report.violations:
            if v.type == "quantity_exceeded":
                assert v.positions_required > 0
                assert v.kit_quantity >= 0
                assert v.shortfall == v.positions_required - v.kit_quantity


class TestValidationPipelineEdgeCases:
    """Edge case tests for validation pipeline."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def palette(self):
        """Load the default LEGO palette."""
        return LegoPalette.load_default()

    @pytest.fixture
    def kit_spec(self):
        """Load the kit specification."""
        return load_kit_specification("31203")

    @pytest.fixture
    def land_sea_mask(self):
        """Load the land/sea mask."""
        return load_land_sea_mask()

    def test_validation_with_mixed_colors(self, palette, kit_spec, land_sea_mask):
        """Test validation with multiple colors in layout."""
        # Create image with checkerboard pattern
        image = Image.new("RGB", (128, 80))

        white = palette.get_by_name("White")
        blue = palette.get_by_name("Bright Blue")

        for y in range(80):
            for x in range(128):
                color = white.rgb if (x + y) % 2 == 0 else blue.rgb
                image.putpixel((x, y), color)

        # Generate layout
        generator = LayoutGenerator(palette=palette, land_sea_mask=land_sea_mask)
        layout = generator.generate(image, source_filename="test.png")

        # Should have both colors
        stats = layout.compute_statistics()
        assert stats.unique_colors >= 2

        # Validate
        validator = LayoutValidator(kit_spec=kit_spec, palette=palette)
        report = validator.validate(layout, layout_file="test.json")

        assert isinstance(report.buildability_score, float)
        assert 0.0 <= report.buildability_score <= 1.0

    def test_validation_report_json_roundtrip(self, palette, kit_spec, land_sea_mask, tmp_path):
        """Test that validation report can be serialized and loaded."""
        white = palette.get_by_name("White")
        image = Image.new("RGB", (128, 80), white.rgb)

        generator = LayoutGenerator(palette=palette, land_sea_mask=land_sea_mask)
        layout = generator.generate(image, source_filename="test.png")

        validator = LayoutValidator(kit_spec=kit_spec, palette=palette)
        report = validator.validate(layout, layout_file="test.json")

        # Serialize to JSON
        json_str = report.to_json()

        # Parse JSON
        data = json.loads(json_str)

        # Verify structure
        assert data["kit_id"] == report.kit_id
        assert data["buildable"] == report.buildable
        assert data["buildability_score"] == pytest.approx(report.buildability_score, rel=0.01)
        assert len(data["violations"]) == len(report.violations)

    def test_cli_validate_output_file_created(self, runner, tmp_path):
        """Test that CLI creates output file when specified."""
        # Create a simple layout file
        layout_file = Path(__file__).parent.parent / "fixtures" / "layouts" / "expected_test_128x80.json"
        output_file = tmp_path / "validation_report.json"

        result = runner.invoke(cli, [
            "validate",
            str(layout_file),
            "-o", str(output_file)
        ])

        assert result.exit_code == 0
        assert output_file.exists()

        # Verify it's valid JSON
        with open(output_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "buildable" in data


# --- US3 (feature 003): the official design validates against the real kit (T063, SC-005) -----

import dataclasses

from lego_image_processor.kit import load_official_design
from lego_image_processor.layout.grid import PositionPlacementGrid


def _official_layout():
    return load_official_design().to_layout()


def _with_changes(layout, changes):
    """changes: {(x, y): (color_id, color_name, code)}"""
    positions = []
    for p in layout.positions:
        if (p.x, p.y) in changes:
            cid, name, code = changes[(p.x, p.y)]
            p = dataclasses.replace(p, color_id=cid, color_name=name, lego_color_code=code)
        positions.append(p)
    return PositionPlacementGrid(width=layout.width, height=layout.height, positions=positions,
                                 source_image=layout.source_image)


def _validate_file(layout, tmp_path, name="layout.json"):
    path = tmp_path / name
    path.write_text(layout.to_json(), encoding="utf-8")
    loaded = PositionPlacementGrid.from_json(path.read_text(encoding="utf-8"))
    validator = LayoutValidator(kit_spec=load_kit_specification("31203"),
                                palette=LegoPalette.load_default())
    return validator.validate(loaded, layout_file=str(path))


def _ocean_cells(layout, exclude_color):
    return [(p.x, p.y) for p in layout.positions
            if p.part_type == "tile" and p.color_id != exclude_color]


class TestOfficialDesignValidation:

    def test_official_design_is_fully_buildable(self, tmp_path):
        report = _validate_file(_official_layout(), tmp_path)
        assert report.violations == []
        assert report.buildable
        assert report.buildability_score == 1.0

    def test_official_design_through_cli(self, tmp_path):
        path = tmp_path / "official.json"
        path.write_text(_official_layout().to_json(), encoding="utf-8")
        result = CliRunner().invoke(cli, ["validate", str(path)])
        assert result.exit_code == 0, result.output
        assert "100.0% (FULLY BUILDABLE)" in result.output
        assert "Violations: 0" in result.output

    def test_one_non_kit_ocean_cell_reports_exactly_that(self, tmp_path):
        layout = _official_layout()
        cell = _ocean_cells(layout, "lego_bright_blue")[0]
        report = _validate_file(
            _with_changes(layout, {cell: ("lego_bright_blue", "Bright Blue", "23")}), tmp_path)
        (v,) = report.violations
        assert v.type == "color_unavailable"
        assert (v.color_id, v.part_type, v.part_id, v.positions_required) == (
            "lego_bright_blue", "tile", "98138", 1)
        assert v.suggested_alternative.color_id != "lego_white"

    def test_extra_earth_blue_cells_report_exactly_that(self, tmp_path):
        layout = _official_layout()
        # The design uses 392 of 393 Earth Blue tiles, so two extra cells exceed the supply.
        cells = [c for c in _ocean_cells(layout, "lego_earth_blue")
                 if layout.get_position(*c).color_id == "lego_bright_yellowish_green"][:2]
        report = _validate_file(
            _with_changes(layout, {c: ("lego_earth_blue", "Earth Blue", "140") for c in cells}),
            tmp_path)
        (v,) = report.violations
        assert v.type == "quantity_exceeded"
        assert (v.color_id, v.positions_required, v.kit_quantity, v.shortfall) == (
            "lego_earth_blue", 394, 393, 1)


def test_to_layout_shape():
    layout = _official_layout()
    assert layout.schema_version == "2.0"
    assert layout.source_image == "official-31203-design"
    assert (layout.width, layout.height, layout.total_positions) == (128, 80, 10240)
    assert layout.land_positions == 3062 and layout.ocean_positions == 7178
    p = layout.get_position(0, 0)
    assert p.color_id == load_official_design().color_at(0, 0)

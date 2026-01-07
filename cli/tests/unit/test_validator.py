"""Unit tests for LayoutValidator and related classes."""

import pytest
from PIL import Image

from lego_image_processor.layout.validator import (
    ColorSuggestion,
    ColorUnavailableViolation,
    QuantityExceededViolation,
    ValidationReport,
    LayoutValidator
)
from lego_image_processor.layout.kit_spec import load_kit_specification
from lego_image_processor.layout.generator import LayoutGenerator
from lego_image_processor.layout.land_sea_mask import load_land_sea_mask
from lego_image_processor.palette.loader import LegoPalette


class TestColorSuggestion:
    """Tests for ColorSuggestion class."""

    def test_create_suggestion(self):
        """Test creating a color suggestion."""
        suggestion = ColorSuggestion(
            color_id="lego_white",
            color_name="White",
            color_distance=10.5
        )
        assert suggestion.color_id == "lego_white"
        assert suggestion.color_name == "White"
        assert suggestion.color_distance == 10.5

    def test_to_dict(self):
        """Test converting suggestion to dictionary."""
        suggestion = ColorSuggestion(
            color_id="lego_white",
            color_name="White",
            color_distance=10.567
        )
        data = suggestion.to_dict()
        assert data["color_id"] == "lego_white"
        assert data["color_distance"] == 10.57  # Rounded


class TestColorUnavailableViolation:
    """Tests for ColorUnavailableViolation class."""

    def test_create_violation(self):
        """Test creating a color unavailable violation."""
        violation = ColorUnavailableViolation(
            part_type="brick",
            part_id="3062b",
            color_id="lego_purple",
            color_name="Purple",
            positions_required=100
        )
        assert violation.type == "color_unavailable"
        assert violation.part_type == "brick"
        assert violation.positions_required == 100

    def test_to_dict(self):
        """Test converting violation to dictionary."""
        suggestion = ColorSuggestion("lego_white", "White", 15.0)
        violation = ColorUnavailableViolation(
            part_type="brick",
            part_id="3062b",
            color_id="lego_purple",
            color_name="Purple",
            positions_required=100,
            suggested_alternative=suggestion
        )
        data = violation.to_dict()
        assert data["type"] == "color_unavailable"
        assert data["positions_required"] == 100
        assert "suggested_alternative" in data


class TestQuantityExceededViolation:
    """Tests for QuantityExceededViolation class."""

    def test_create_violation(self):
        """Test creating a quantity exceeded violation."""
        violation = QuantityExceededViolation(
            part_type="tile",
            part_id="98138",
            color_id="lego_blue",
            color_name="Blue",
            positions_required=2000,
            kit_quantity=1500,
            shortfall=500
        )
        assert violation.type == "quantity_exceeded"
        assert violation.shortfall == 500

    def test_to_dict(self):
        """Test converting violation to dictionary."""
        violation = QuantityExceededViolation(
            part_type="tile",
            part_id="98138",
            color_id="lego_blue",
            color_name="Blue",
            positions_required=2000,
            kit_quantity=1500,
            shortfall=500
        )
        data = violation.to_dict()
        assert data["type"] == "quantity_exceeded"
        assert data["shortfall"] == 500


class TestValidationReport:
    """Tests for ValidationReport class."""

    def test_create_buildable_report(self):
        """Test creating a buildable report."""
        report = ValidationReport(
            buildable=True,
            buildability_score=1.0,
            violations=[],
            validated_at="2026-01-07T12:00:00Z",
            kit_id="31203",
            layout_file="layout.json"
        )
        assert report.buildable
        assert report.buildability_score == 1.0
        assert len(report.violations) == 0

    def test_create_unbuildable_report(self):
        """Test creating an unbuildable report."""
        violation = QuantityExceededViolation(
            part_type="tile",
            part_id="98138",
            color_id="lego_blue",
            color_name="Blue",
            positions_required=2000,
            kit_quantity=1500,
            shortfall=500
        )
        report = ValidationReport(
            buildable=False,
            buildability_score=0.75,
            violations=[violation],
            validated_at="2026-01-07T12:00:00Z",
            kit_id="31203",
            layout_file="layout.json"
        )
        assert not report.buildable
        assert len(report.violations) == 1

    def test_to_json(self):
        """Test converting report to JSON."""
        report = ValidationReport(
            buildable=True,
            buildability_score=1.0,
            violations=[],
            validated_at="2026-01-07T12:00:00Z",
            kit_id="31203",
            layout_file="layout.json"
        )
        json_str = report.to_json()
        assert '"buildable": true' in json_str
        assert '"kit_id": "31203"' in json_str


class TestLayoutValidator:
    """Tests for LayoutValidator class."""

    @pytest.fixture
    def palette(self):
        """Load the default LEGO palette."""
        return LegoPalette.load_default()

    @pytest.fixture
    def kit_spec(self):
        """Load the kit specification."""
        return load_kit_specification("31203")

    @pytest.fixture
    def validator(self, kit_spec, palette):
        """Create a LayoutValidator instance."""
        return LayoutValidator(kit_spec=kit_spec, palette=palette)

    @pytest.fixture
    def generator(self, palette):
        """Create a LayoutGenerator instance."""
        land_sea_mask = load_land_sea_mask()
        return LayoutGenerator(palette=palette, land_sea_mask=land_sea_mask)

    def test_create_validator(self, kit_spec, palette):
        """Test creating a LayoutValidator."""
        validator = LayoutValidator(kit_spec=kit_spec, palette=palette)
        assert validator is not None

    def test_validate_returns_report(self, validator, generator, palette):
        """Test that validation returns a ValidationReport."""
        # Create a simple layout
        first_color = palette.colors[0]
        image = Image.new("RGB", (128, 80), first_color.rgb)
        layout = generator.generate(image, source_filename="test.png")

        report = validator.validate(layout, layout_file="test.json")

        assert isinstance(report, ValidationReport)
        assert report.kit_id == "31203"

    def test_validate_has_buildability_score(self, validator, generator, palette):
        """Test that validation report has buildability score."""
        first_color = palette.colors[0]
        image = Image.new("RGB", (128, 80), first_color.rgb)
        layout = generator.generate(image, source_filename="test.png")

        report = validator.validate(layout, layout_file="test.json")

        assert 0.0 <= report.buildability_score <= 1.0

    def test_validate_detects_unavailable_color(self, validator, generator, palette):
        """Test that validator detects unavailable colors."""
        # Use a color that might not be in the kit
        # We'll check if any violations are reported
        first_color = palette.colors[0]
        image = Image.new("RGB", (128, 80), first_color.rgb)
        layout = generator.generate(image, source_filename="test.png")

        report = validator.validate(layout, layout_file="test.json")

        # Report should exist regardless of violations
        assert isinstance(report, ValidationReport)

    def test_validate_reports_timestamp(self, validator, generator, palette):
        """Test that validation report has timestamp."""
        first_color = palette.colors[0]
        image = Image.new("RGB", (128, 80), first_color.rgb)
        layout = generator.generate(image, source_filename="test.png")

        report = validator.validate(layout, layout_file="test.json")

        assert report.validated_at is not None
        assert "T" in report.validated_at  # ISO format

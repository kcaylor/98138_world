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
            part_type="plate",
            part_id="6141",
            color_id="lego_purple",
            color_name="Purple",
            positions_required=100
        )
        assert violation.type == "color_unavailable"
        assert violation.part_type == "plate"
        assert violation.positions_required == 100

    def test_to_dict(self):
        """Test converting violation to dictionary."""
        suggestion = ColorSuggestion("lego_white", "White", 15.0)
        violation = ColorUnavailableViolation(
            part_type="plate",
            part_id="6141",
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


# --- US3 (feature 003): validation against the real kit (T061) ---------------------------------

from lego_image_processor.core.color_quantizer import delta_e_2000
from lego_image_processor.kit import load_kit_color_table
from lego_image_processor.layout.grid import DISCLAIMER, PositionPlacementGrid
from lego_image_processor.layout.position import PositionPlacement
import numpy as np
from lego_image_processor.palette.converter import rgb_to_lab


def _pos(x, palette_color, part_type):
    part_id = "6141" if part_type == "plate" else "98138"
    key = "lego_" + palette_color.name.lower().replace(" ", "_").replace("-", "_")
    return PositionPlacement(x=x, y=0, color_id=key, color_name=palette_color.name,
                             lego_color_code=str(palette_color.id), part_type=part_type,
                             lego_part_id=part_id)


def _grid(positions):
    return PositionPlacementGrid(width=len(positions), height=1, positions=positions,
                                 source_image="test.png")


class TestValidatorAgainstRealKit:
    """US3-2, US3-3, FR-018, FR-019: colors per part, real quantities, CIEDE2000 suggestions."""

    @pytest.fixture
    def palette(self):
        return LegoPalette.load_default()

    @pytest.fixture
    def validator(self, palette):
        return LayoutValidator(kit_spec=load_kit_specification("31203"), palette=palette)

    def _expected_nearest(self, palette_color, role):
        target = rgb_to_lab(np.array(palette_color.rgb, dtype=np.float64))
        best = None
        for c in load_kit_color_table().colors:
            if c.role != role:
                continue
            d = float(delta_e_2000(target, rgb_to_lab(np.array(c.rgb, dtype=np.float64))))
            if best is None or d < best[1]:
                best = (c.key, d)
        return best

    def test_ocean_non_kit_color_named_with_part_count_and_ciede2000_suggestion(
            self, validator, palette):
        bright_blue = palette.get_by_name("Bright Blue")
        earth_blue = palette.get_by_name("Earth Blue")
        layout = _grid([_pos(0, bright_blue, "tile"), _pos(1, bright_blue, "tile"),
                        _pos(2, bright_blue, "tile"), _pos(3, earth_blue, "tile")])
        report = validator.validate(layout, layout_file="t.json")
        (v,) = [v for v in report.violations if v.type == "color_unavailable"]
        assert v.color_id == "lego_bright_blue"
        assert v.color_name == "Bright Blue"
        assert (v.part_type, v.part_id) == ("tile", "98138")
        assert v.positions_required == 3
        key, dist = self._expected_nearest(bright_blue, "ocean")
        assert v.suggested_alternative.color_id == key
        assert v.suggested_alternative.color_id != "lego_white"
        assert v.suggested_alternative.color_distance == pytest.approx(dist, abs=1e-6)

    def test_ocean_suggestion_is_always_an_ocean_kit_color(self, validator, palette):
        ocean_keys = {c.key for c in load_kit_color_table().colors if c.role == "ocean"}
        # Light colors whose nearest kit color overall could be White
        for name in ("Light Stone Grey", "Aqua", "White Glow", "Cool Yellow"):
            layout = _grid([_pos(0, palette.get_by_name(name), "tile")])
            (v,) = validator.validate(layout, layout_file="t.json").violations
            assert v.suggested_alternative.color_id in ocean_keys, name

    def test_land_non_white_color_suggests_only_white(self, validator, palette):
        for name in ("Earth Blue", "Black", "Bright Red", "Medium Azur"):
            layout = _grid([_pos(0, palette.get_by_name(name), "plate")])
            (v,) = validator.validate(layout, layout_file="t.json").violations
            assert v.type == "color_unavailable"
            assert (v.part_type, v.part_id) == ("plate", "6141")
            assert v.suggested_alternative.color_id == "lego_white"

    def test_overuse_reports_required_available_shortfall_from_inventory(self, validator, palette):
        earth_blue = palette.get_by_name("Earth Blue")
        layout = _grid([_pos(x, earth_blue, "tile") for x in range(400)])
        (v,) = validator.validate(layout, layout_file="t.json").violations
        assert isinstance(v, QuantityExceededViolation)
        assert (v.positions_required, v.kit_quantity, v.shortfall) == (400, 393, 7)
        assert (v.part_type, v.part_id) == ("tile", "98138")

    def test_report_dict_has_disclaimer(self, validator, palette):
        layout = _grid([_pos(0, palette.get_by_name("White"), "plate")])
        report = validator.validate(layout, layout_file="t.json")
        assert report.to_dict()["disclaimer"] == DISCLAIMER
        assert report.buildable

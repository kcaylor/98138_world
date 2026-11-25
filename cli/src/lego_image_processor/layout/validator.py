"""Layout validator for LEGO World Map kit compliance.

Colors and quantities are checked against one kit 31203. A layout on a non-kit template (feature
016, ``metadata.template``) is checked against its own template's classes instead of the kit's
land/sea mask, and its margin's 1x1 square tiles (part 3070b) are reported as unavailable in the
kit with no suggestion, since no kit has them (FR-016, research R17). Kit layouts validate as before.

Feature 017 (FR-024; contracts/in-margin-plaque.md): a layout may lack exactly the studs its
``metadata.plaque`` records, and those must be margin studs of its template. On a non-kit template
any other absent position (``part_type`` None in the example), a piece under the plaque (expected
``plaque_tile``) or a plaque on a stud that is not a margin stud (``part_type`` ``plaque_tile``) is a
mask mismatch; on the kit, whose layouts have no margin, every stud a recorded plaque covers is one.
Like the square tiles, the plaque's tile (part 10202) is in no kit: a recorded plaque is reported as
``color_unavailable`` (part type ``plaque_tile``, one position per covered stud, no suggestion), so
its studs do not count as buildable with the kit (T082).
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

import numpy as np

from .grid import DISCLAIMER, PositionPlacementGrid
from .kit_spec import LEGOWorldMapKitSpecification
from .position import LAND_PART_TYPE, MARGIN_PART_ID, MARGIN_PART_TYPE, OCEAN_PART_TYPE

PLAQUE_PART_TYPE = "plaque_tile"  # feature 017: the in-margin plaque's tile in mask examples
from ..core.color_quantizer import delta_e_2000
from ..kit import load_kit_color_table
from ..palette.converter import rgb_to_lab
from ..palette.loader import LegoPalette


@dataclass
class ColorSuggestion:
    """Suggested alternative color for unavailable colors.

    Attributes:
        color_id: Suggested color ID
        color_name: Human-readable name
        color_distance: CIEDE2000 (Delta E 00) distance from the required color
    """

    color_id: str
    color_name: str
    color_distance: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "color_id": self.color_id,
            "color_name": self.color_name,
            "color_distance": round(self.color_distance, 2)
        }


class Violation(ABC):
    """Abstract base class for validation violations."""

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert violation to dictionary."""
        pass


@dataclass
class ColorUnavailableViolation(Violation):
    """Color required by layout is not available in kit for part type.

    Attributes:
        type: Always "color_unavailable"
        part_type: Affected part type ("plate", "tile", or "square_tile" on a non-kit template;
            "plaque_tile" for an in-margin plaque, feature 017)
        part_id: LEGO part ID ("6141", "98138", "3070b" or "10202")
        color_id: Required color not in kit
        color_name: Human-readable color name
        positions_required: Number of positions needing this color (for the plaque tile, the
            studs it covers)
        suggested_alternative: Nearest available color in kit (None for square tiles and the
            plaque tile: the kit has none)
    """

    part_type: str
    part_id: str
    color_id: str
    color_name: str
    positions_required: int
    suggested_alternative: Optional[ColorSuggestion] = None

    @property
    def type(self) -> str:
        return "color_unavailable"

    def to_dict(self) -> Dict[str, Any]:
        """Convert violation to dictionary."""
        result = {
            "type": self.type,
            "part_type": self.part_type,
            "part_id": self.part_id,
            "color_id": self.color_id,
            "color_name": self.color_name,
            "positions_required": self.positions_required
        }
        if self.suggested_alternative:
            result["suggested_alternative"] = self.suggested_alternative.to_dict()
        return result


@dataclass
class QuantityExceededViolation(Violation):
    """Layout requires more parts of color/type than kit provides.

    Attributes:
        type: Always "quantity_exceeded"
        part_type: Affected part type ("plate" or "tile")
        part_id: LEGO part ID ("6141" or "98138")
        color_id: Color with insufficient quantity
        color_name: Human-readable color name
        positions_required: Number of positions needed
        kit_quantity: Number available in kit
        shortfall: positions_required - kit_quantity
    """

    part_type: str
    part_id: str
    color_id: str
    color_name: str
    positions_required: int
    kit_quantity: int
    shortfall: int

    @property
    def type(self) -> str:
        return "quantity_exceeded"

    def to_dict(self) -> Dict[str, Any]:
        """Convert violation to dictionary."""
        return {
            "type": self.type,
            "part_type": self.part_type,
            "part_id": self.part_id,
            "color_id": self.color_id,
            "color_name": self.color_name,
            "positions_required": self.positions_required,
            "kit_quantity": self.kit_quantity,
            "shortfall": self.shortfall
        }


@dataclass
class MaskMismatchViolation(Violation):
    """Positions whose part (plate on land, tile on ocean) does not match the kit's land/sea mask
    in the layout's arrangement (feature 007), or, for a layout on a non-kit template, the part
    of the template's class at that stud (feature 016: plate on land, tile on ocean, square tile
    on the margin).

    Attributes:
        arrangement: Arrangement id the mask was checked in (A, B or C)
        positions_required: Number of mismatched positions
        examples: Up to 10 mismatches as {x, y, part_type, expected}
        template: The non-kit template id checked against; None for the kit mask (not written)
    """

    arrangement: str
    positions_required: int
    examples: List[Dict[str, Any]] = field(default_factory=list)
    template: Optional[str] = None

    @property
    def type(self) -> str:
        return "mask_mismatch"

    def to_dict(self) -> Dict[str, Any]:
        out = {"type": self.type, "arrangement": self.arrangement}
        if self.template is not None:
            out["template"] = self.template
        out.update(positions_required=self.positions_required, examples=list(self.examples))
        return out


@dataclass
class ValidationReport:
    """Result of validating layout against kit specifications.

    Attributes:
        buildable: Overall buildability flag (True if no violations)
        buildability_score: Percentage buildable (0.0-1.0)
        violations: List of compatibility issues
        validated_at: Validation timestamp
        kit_id: Kit validated against
        layout_file: Validated layout file path
    """

    buildable: bool
    buildability_score: float
    violations: List[Violation]
    validated_at: str
    kit_id: str
    layout_file: str
    arrangement: str = "A"
    template: Optional[Dict[str, Any]] = None  # feature 016: {id, title}; None (not written) on the kit

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        out = {
            "buildable": self.buildable,
            "buildability_score": round(self.buildability_score, 4),
            "violations": [v.to_dict() for v in self.violations],
            "validated_at": self.validated_at,
            "kit_id": self.kit_id,
            "layout_file": self.layout_file,
            "arrangement": self.arrangement,
        }
        if self.template is not None:
            out["template"] = dict(self.template)
        out["disclaimer"] = DISCLAIMER
        return out

    def to_json(self, indent: int = 2) -> str:
        """Convert report to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class LayoutValidator:
    """Validate layouts against LEGO World Map kit specifications.

    Checks color availability and quantities for both plate (land) and tile (ocean) parts.
    """

    def __init__(self, kit_spec: LEGOWorldMapKitSpecification, palette: LegoPalette):
        """Initialize layout validator.

        Args:
            kit_spec: Kit specification for validation
            palette: LEGO color palette for color lookup and distance calculation
        """
        self._kit_spec = kit_spec
        self._palette = palette

        # Build color lookup
        self._color_by_id = {}
        for color in palette.colors:
            color_id = self._make_color_id(color.name)
            self._color_by_id[color_id] = color

        # Kit colors (cited names and RGB) for suggestions
        self._kit_colors = {
            c.key: (c.lego.name, tuple(c.rgb)) for c in load_kit_color_table().colors
        }

    def validate(self, layout: PositionPlacementGrid, layout_file: str) -> ValidationReport:
        """Validate layout against kit specifications.

        Args:
            layout: Position placement layout to validate
            layout_file: Path to layout file (for report)

        Returns:
            ValidationReport with buildability status and violations
        """
        violations = []
        total_violation_positions = 0

        # Count colors by part type
        plate_colors = Counter()
        tile_colors = Counter()
        square_colors = Counter()  # feature 016: a non-kit template's margin
        color_names = {}

        for pos in layout.positions:
            color_names[pos.color_id] = pos.color_name
            if pos.part_type == LAND_PART_TYPE:
                plate_colors[pos.color_id] += 1
            elif pos.part_type == MARGIN_PART_TYPE:
                square_colors[pos.color_id] += 1
            else:
                tile_colors[pos.color_id] += 1

        # Validate plate (land) colors
        for color_id, count in plate_colors.items():
            color_name = color_names.get(color_id, color_id)

            # Check if color is available
            if not self._kit_spec.is_plate_color_available(color_id):
                suggestion = self._find_nearest_color(
                    color_id, self._kit_spec.available_colors_plate
                )
                violations.append(ColorUnavailableViolation(
                    part_type=LAND_PART_TYPE,
                    part_id=self._kit_spec.land_part_id,
                    color_id=color_id,
                    color_name=color_name,
                    positions_required=count,
                    suggested_alternative=suggestion
                ))
                total_violation_positions += count
            else:
                # Check quantity
                available = self._kit_spec.get_plate_quantity(color_id)
                if count > available:
                    violations.append(QuantityExceededViolation(
                        part_type=LAND_PART_TYPE,
                        part_id=self._kit_spec.land_part_id,
                        color_id=color_id,
                        color_name=color_name,
                        positions_required=count,
                        kit_quantity=available,
                        shortfall=count - available
                    ))
                    total_violation_positions += (count - available)

        # Validate tile (ocean) colors
        for color_id, count in tile_colors.items():
            color_name = color_names.get(color_id, color_id)

            # Check if color is available
            if not self._kit_spec.is_tile_color_available(color_id):
                suggestion = self._find_nearest_color(
                    color_id, self._kit_spec.available_colors_tile
                )
                violations.append(ColorUnavailableViolation(
                    part_type=OCEAN_PART_TYPE,
                    part_id=self._kit_spec.ocean_part_id,
                    color_id=color_id,
                    color_name=color_name,
                    positions_required=count,
                    suggested_alternative=suggestion
                ))
                total_violation_positions += count
            else:
                # Check quantity
                available = self._kit_spec.get_tile_quantity(color_id)
                if count > available:
                    violations.append(QuantityExceededViolation(
                        part_type=OCEAN_PART_TYPE,
                        part_id=self._kit_spec.ocean_part_id,
                        color_id=color_id,
                        color_name=color_name,
                        positions_required=count,
                        kit_quantity=available,
                        shortfall=count - available
                    ))
                    total_violation_positions += (count - available)

        # Square tiles (feature 016): no kit 31203 supplies part 3070b, so every color of it is
        # unavailable, with no suggestion (a template map always needs pieces beyond the kit).
        for color_id, count in square_colors.items():
            violations.append(ColorUnavailableViolation(
                part_type=MARGIN_PART_TYPE,
                part_id=MARGIN_PART_ID,
                color_id=color_id,
                color_name=color_names.get(color_id, color_id),
                positions_required=count,
            ))
            total_violation_positions += count

        # The in-margin plaque's tile (feature 017, T082): no kit has it either, so, as for the square
        # tiles, it is unavailable with no suggestion and the studs it covers are not buildable.
        plaque = self._plaque_unavailable(layout)
        if plaque is not None:
            violations.append(plaque)
            total_violation_positions += plaque.positions_required

        # Land/sea mask in the layout's arrangement (feature 007), or the layout's own template
        from .arrangement import arrangement_of

        arrangement = arrangement_of(layout)
        template = self._template(layout)
        if template is None:
            mismatch = self._mask_mismatch(layout, arrangement)
        else:
            mismatch = self._template_mismatch(layout, template, arrangement)
        if mismatch is not None:
            violations.append(mismatch)
            total_violation_positions += mismatch.positions_required

        # Calculate buildability score
        total_positions = layout.total_positions
        buildable_positions = total_positions - total_violation_positions
        buildability_score = buildable_positions / total_positions if total_positions > 0 else 0.0

        return ValidationReport(
            buildable=len(violations) == 0,
            buildability_score=buildability_score,
            violations=violations,
            validated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            kit_id=self._kit_spec.kit_id,
            layout_file=layout_file,
            arrangement=arrangement.id,
            template=None if template is None else {"id": template.id, "title": template.title},
        )

    @staticmethod
    def _plaque_unavailable(layout: PositionPlacementGrid) -> Optional[ColorUnavailableViolation]:
        """The recorded plaque's tile as ``color_unavailable`` (part type ``plaque_tile``), one
        position per stud it covers; None without a plaque (feature 017, T082)."""
        rec = getattr(layout, "plaque", None)
        if rec is None:
            return None
        from ..maps.margin import plaque_tile

        tile = plaque_tile()
        color_id = str(rec.get("color", tile.color.key))
        part_id = str(rec.get("part_id", tile.part_id))
        name = tile.color.lego.name if (part_id, color_id) == (tile.part_id, tile.color.key) else color_id
        return ColorUnavailableViolation(part_type=PLAQUE_PART_TYPE, part_id=part_id, color_id=color_id,
                                         color_name=name, positions_required=len(layout.plaque_positions))

    @staticmethod
    def _template(layout: PositionPlacementGrid):
        """The non-kit template a layout records (``metadata.template``), or None for the kit.

        Raises ``UnknownTemplateError`` (a ``ValueError``) for a template id this version does not
        know."""
        rec = getattr(layout, "template", None)
        if not rec:
            return None
        from ..templates import KIT_TEMPLATE_ID, load_template

        tid = rec.get("id") if isinstance(rec, dict) else None
        if tid == KIT_TEMPLATE_ID:
            return None
        return load_template(tid)

    @staticmethod
    def _template_mismatch(layout: PositionPlacementGrid, template, arrangement) -> Optional["MaskMismatchViolation"]:
        """Positions whose part type is not the part of the template's class at that stud; then
        (feature 017) studs without a position that the layout's plaque does not cover, and plaque
        studs that are not margin studs."""
        expected_type = {"land": LAND_PART_TYPE, "ocean": OCEAN_PART_TYPE, "margin": MARGIN_PART_TYPE}
        covered = getattr(layout, "plaque_positions", frozenset())
        bad = []
        for p in layout.positions:
            if not (0 <= p.x < template.width and 0 <= p.y < template.height):
                continue
            expected = expected_type[template.class_at(p.y, p.x)]
            if (p.x, p.y) in covered and expected == MARGIN_PART_TYPE:  # a piece under the plaque
                bad.append({"x": p.x, "y": p.y, "part_type": p.part_type, "expected": PLAQUE_PART_TYPE})
            elif p.part_type != expected:
                bad.append({"x": p.x, "y": p.y, "part_type": p.part_type, "expected": expected})
        present = {(p.x, p.y) for p in layout.positions}
        for y in range(template.height):
            for x in range(template.width):
                expected = expected_type[template.class_at(y, x)]
                if (x, y) in covered:
                    if expected != MARGIN_PART_TYPE:  # the plaque must lie on margin studs
                        bad.append({"x": x, "y": y, "part_type": PLAQUE_PART_TYPE, "expected": expected})
                elif (x, y) not in present:
                    bad.append({"x": x, "y": y, "part_type": None, "expected": expected})
        if not bad:
            return None
        return MaskMismatchViolation(arrangement=arrangement.id, positions_required=len(bad),
                                     examples=bad[:10], template=template.id)

    @staticmethod
    def _mask_mismatch(layout: PositionPlacementGrid, arrangement) -> Optional["MaskMismatchViolation"]:
        """Positions off the kit mask shifted to ``arrangement``; None when all match."""
        from .land_sea_mask import load_land_sea_mask

        mask = load_land_sea_mask()
        if (layout.width, layout.height) != (mask.width, mask.height):
            return None
        covered = getattr(layout, "plaque_positions", frozenset())  # feature 017: the kit has no margin
        bad = []
        for p in layout.positions:
            if not (0 <= p.x < mask.width and 0 <= p.y < mask.height) or (p.x, p.y) in covered:
                continue
            expected = LAND_PART_TYPE if mask.is_land(arrangement.to_kit(p.x), p.y) else OCEAN_PART_TYPE
            if p.part_type != expected:
                bad.append({"x": p.x, "y": p.y, "part_type": p.part_type, "expected": expected})
        for (x, y) in sorted(covered, key=lambda s: (s[1], s[0])):
            if 0 <= x < mask.width and 0 <= y < mask.height:
                expected = LAND_PART_TYPE if mask.is_land(arrangement.to_kit(x), y) else OCEAN_PART_TYPE
                bad.append({"x": x, "y": y, "part_type": PLAQUE_PART_TYPE, "expected": expected})
        if not bad:
            return None
        return MaskMismatchViolation(arrangement=arrangement.id, positions_required=len(bad),
                                     examples=bad[:10])

    def _find_nearest_color(
        self,
        target_color_id: str,
        available_colors: List[str]
    ) -> Optional[ColorSuggestion]:
        """Nearest kit color of the affected part by CIEDE2000.

        The target's RGB comes from the palette (the colors quantized images use); candidates are
        the part's kit colors with their cited RGB from ``kit_colors.json``. Only colors in
        ``available_colors`` (the part's kit colors) are considered.

        Returns:
            ColorSuggestion with the distance as Delta E 00, or None if the target is unknown
        """
        target_color = self._color_by_id.get(target_color_id)
        if not target_color:
            return None
        target_lab = rgb_to_lab(np.array(target_color.rgb, dtype=np.float64))

        best_suggestion = None
        best_distance = float("inf")
        for color_id in available_colors:
            candidate = self._kit_colors.get(color_id)
            if candidate is None:
                continue
            name, rgb = candidate
            distance = float(delta_e_2000(target_lab, rgb_to_lab(np.array(rgb, dtype=np.float64))))
            if distance < best_distance:
                best_distance = distance
                best_suggestion = ColorSuggestion(
                    color_id=color_id, color_name=name, color_distance=distance
                )
        return best_suggestion

    @staticmethod
    def _make_color_id(color_name: str) -> str:
        """Convert color name to color_id format."""
        normalized = color_name.lower().replace(" ", "_").replace("-", "_")
        return f"lego_{normalized}"

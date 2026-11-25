"""Position placement grid and statistics for LEGO World Map layouts.

Feature 017 (FR-023; contracts/in-margin-plaque.md "Layout JSON"): a layout on a non-kit template
may record an in-margin plaque in ``metadata.plaque`` (``{part_id, color, corner, studs: {row, col,
height, width}, cells}``, written only when one is placed). Its studs carry no position, so the
margin counts are the square tiles present; ``statistics.plaque_tile_count`` is 1 and the coverage
counts the plaque's studs as covered. Layouts without it read and write as before.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import StringIO
from typing import Dict, FrozenSet, List, Any, Optional, Tuple

from .position import LAND_PART_TYPE, MARGIN_PART_TYPE, OCEAN_PART_TYPE, PositionPlacement

CURRENT_SCHEMA_VERSION = "2.0"
DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
_PLAQUE_STUD_KEYS = ("row", "col", "height", "width")


def plaque_positions(record: Optional[Dict[str, Any]]) -> FrozenSet[Tuple[int, int]]:
    """The studs ``(x, y)`` a ``metadata.plaque`` record covers (feature 017); empty for None.
    Raises ``ValueError`` naming ``metadata.plaque`` for a malformed record."""
    if record is None:
        return frozenset()
    studs = record.get("studs") if isinstance(record, dict) else None
    if not (isinstance(studs, dict) and all(
            isinstance(studs.get(k), int) and not isinstance(studs.get(k), bool) for k in _PLAQUE_STUD_KEYS)
            and studs["row"] >= 0 and studs["col"] >= 0 and studs["height"] > 0 and studs["width"] > 0):
        raise ValueError("metadata.plaque: studs must be {row, col, height, width}, non-negative integers "
                         "(height and width positive)")
    r, c, h, w = (studs[k] for k in _PLAQUE_STUD_KEYS)
    return frozenset((x, y) for y in range(r, r + h) for x in range(c, c + w))


class LayoutSchemaError(ValueError):
    """Raised when a layout file was written with an unsupported schema version."""

    def __init__(self, found):
        shown = found if found else "(missing)"
        self.found = found
        super().__init__(
            f"Layout schema version {shown} is no longer supported "
            f"(land is now part 6141, a 1x1 round plate). "
            f"Regenerate it with: lego-image-processor layout <image> -o <layout.json>"
        )


@dataclass
class LayoutStatistics:
    """Summary statistics about a generated layout.

    Provides quick overview of composition and part requirements without
    parsing the full position array.

    Attributes:
        total_tile_count: Total positions (e.g., 10,240)
        land_plate_count: Round plates for land (e.g., 3,062)
        ocean_tile_count: Flat tiles for ocean (e.g., 7,178)
        unique_colors: Count of distinct colors used
        color_frequency: Map of color_id to position count
        color_frequency_by_part_type: Color frequency split by part type
        most_common_color: Color with highest frequency
        coverage_percentage: Percentage of grid filled (100.0 for valid layouts)
        margin_tile_count: Square tiles of a non-kit template's margin (feature 016); None (and
            not written) for kit layouts
        plaque_tile_count: The in-margin plaque's tile (feature 017): 1 when the layout records a
            plaque; None (and not written) otherwise
    """

    total_tile_count: int
    land_plate_count: int
    ocean_tile_count: int
    unique_colors: int
    color_frequency: Dict[str, int]
    color_frequency_by_part_type: Dict[str, Dict[str, int]]
    most_common_color: Dict[str, Any]
    coverage_percentage: float
    margin_tile_count: Optional[int] = None
    plaque_tile_count: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert statistics to dictionary.

        Returns:
            Dictionary with all statistics.
        """
        out = {
            "total_tile_count": self.total_tile_count,
            "land_plate_count": self.land_plate_count,
            "ocean_tile_count": self.ocean_tile_count,
            "unique_colors": self.unique_colors,
            "color_frequency": self.color_frequency,
            "color_frequency_by_part_type": self.color_frequency_by_part_type,
            "most_common_color": self.most_common_color,
            "coverage_percentage": self.coverage_percentage
        }
        if self.margin_tile_count is None and self.plaque_tile_count is None:
            return out
        # feature 016, non-kit layouts only: the margin count follows the ocean count;
        # feature 017: the plaque's tile follows it
        keys = list(out)
        after = "ocean_tile_count"
        if self.margin_tile_count is not None:
            keys.insert(keys.index(after) + 1, "margin_tile_count")
            out["margin_tile_count"] = self.margin_tile_count
            after = "margin_tile_count"
        if self.plaque_tile_count is not None:
            keys.insert(keys.index(after) + 1, "plaque_tile_count")
            out["plaque_tile_count"] = self.plaque_tile_count
        return {k: out[k] for k in keys}


class PositionPlacementGrid:
    """Complete LEGO World Map building plan.

    Represents a grid of position placements matching the official kit 31203
    structure (128x80 grid, 10,240 positions: 3,062 land plates + 7,178 ocean tiles).

    Attributes:
        width: Grid width in studs (standard: 128)
        height: Grid height in studs (standard: 80)
        total_positions: Total positions (width x height)
        land_positions: Count of land positions (round plates)
        ocean_positions: Count of ocean positions (flat tiles)
        unique_colors: Count of distinct colors used
        coordinate_system: Always "top_left_origin"
        generated_at: ISO 8601 timestamp when layout was generated
        source_image: Input quantized image filename
        schema_version: Schema version (current: "2.0")
        positions: List of all position placements
    """

    def __init__(
        self,
        width: int,
        height: int,
        positions: List[PositionPlacement],
        source_image: str,
        generated_at: Optional[str] = None,
        schema_version: str = CURRENT_SCHEMA_VERSION,
        map_metadata: Optional[Dict[str, Any]] = None,
        arrangement: Optional[Dict[str, Any]] = None,
        template: Optional[Dict[str, Any]] = None,
        plaque: Optional[Dict[str, Any]] = None,
    ):
        """Initialize position placement grid.

        Args:
            width: Grid width in studs
            height: Grid height in studs
            positions: List of position placements
            source_image: Input quantized image filename
            generated_at: Optional ISO 8601 timestamp (defaults to now)
            schema_version: Schema version
            map_metadata: Optional map provenance written as ``metadata.map`` (feature 004)
            arrangement: Optional ``metadata.arrangement`` record (feature 007); None means A
            template: Optional ``metadata.template`` record (feature 016); None means the kit
                template, and no template, margin or square-tile keys are written
            plaque: Optional ``metadata.plaque`` record (feature 017): the in-margin plaque, whose
                studs carry no position; None means no plaque, and no plaque keys are written
        """
        self._width = width
        self._height = height
        self._positions = list(positions)  # Make a copy
        self._source_image = source_image
        self._schema_version = schema_version
        self._coordinate_system = "top_left_origin"
        self._map_metadata = map_metadata
        self._arrangement = arrangement
        self._template = template
        self._plaque = plaque
        self._plaque_positions = plaque_positions(plaque)

        if generated_at is None:
            self._generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            self._generated_at = generated_at

        # Build position lookup for fast access
        self._position_map: Dict[tuple, PositionPlacement] = {}
        for pos in self._positions:
            self._position_map[(pos.x, pos.y)] = pos

        # Compute derived values
        self._compute_counts()

    def _compute_counts(self) -> None:
        """Compute land/ocean/color counts from positions."""
        self._land_positions = sum(1 for p in self._positions if p.part_type == LAND_PART_TYPE)
        self._ocean_positions = sum(1 for p in self._positions if p.part_type == OCEAN_PART_TYPE)
        self._margin_positions = sum(1 for p in self._positions if p.part_type == MARGIN_PART_TYPE)
        self._unique_colors = len(set(p.color_id for p in self._positions)) if self._positions else 0

    @property
    def width(self) -> int:
        """Grid width in studs."""
        return self._width

    @property
    def height(self) -> int:
        """Grid height in studs."""
        return self._height

    @property
    def total_positions(self) -> int:
        """Total number of positions (width x height)."""
        return self._width * self._height

    @property
    def land_positions(self) -> int:
        """Count of land positions (round plates)."""
        return self._land_positions

    @property
    def ocean_positions(self) -> int:
        """Count of ocean positions (flat tiles)."""
        return self._ocean_positions

    @property
    def margin_positions(self) -> int:
        """Count of margin positions (1x1 square tiles, part 3070b; 0 on the kit template)."""
        return self._margin_positions

    @property
    def unique_colors(self) -> int:
        """Count of distinct colors used."""
        return self._unique_colors

    @property
    def coordinate_system(self) -> str:
        """Coordinate system origin (always top-left)."""
        return self._coordinate_system

    @property
    def generated_at(self) -> str:
        """ISO 8601 timestamp when layout was generated."""
        return self._generated_at

    @property
    def source_image(self) -> str:
        """Input quantized image filename."""
        return self._source_image

    @property
    def schema_version(self) -> str:
        """Schema version."""
        return self._schema_version

    @property
    def map_metadata(self) -> Optional[Dict[str, Any]]:
        """Map provenance (``metadata.map``) for recipe builds; None for image layouts."""
        return self._map_metadata

    @property
    def arrangement(self) -> Optional[Dict[str, Any]]:
        """The ``metadata.arrangement`` record (feature 007); None for combination A by default."""
        return self._arrangement

    @property
    def template(self) -> Optional[Dict[str, Any]]:
        """The ``metadata.template`` record (feature 016); None for the kit template."""
        return self._template

    @property
    def plaque(self) -> Optional[Dict[str, Any]]:
        """The ``metadata.plaque`` record (feature 017); None without an in-margin plaque."""
        return self._plaque

    @property
    def plaque_positions(self) -> FrozenSet[Tuple[int, int]]:
        """The studs ``(x, y)`` the in-margin plaque covers (feature 017); empty without one."""
        return self._plaque_positions

    @property
    def positions(self) -> List[PositionPlacement]:
        """List of all position placements (copy)."""
        return list(self._positions)

    def add_position(self, position: PositionPlacement) -> None:
        """Add a position to the grid.

        Args:
            position: Position placement to add
        """
        self._positions.append(position)
        self._position_map[(position.x, position.y)] = position
        self._compute_counts()

    def get_position(self, x: int, y: int) -> Optional[PositionPlacement]:
        """Get position placement at coordinates.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            PositionPlacement at (x, y) or None if not found
        """
        return self._position_map.get((x, y))

    def compute_statistics(self) -> LayoutStatistics:
        """Compute layout statistics.

        Returns:
            LayoutStatistics with composition information
        """
        on_template = self._template is not None  # feature 016: margin counts for non-kit layouts only
        plaque_tiles = 1 if self._plaque is not None else None  # feature 017
        if not self._positions:
            by_type = {LAND_PART_TYPE: {}, OCEAN_PART_TYPE: {}}
            if on_template:
                by_type[MARGIN_PART_TYPE] = {}
            return LayoutStatistics(
                total_tile_count=0,
                land_plate_count=0,
                ocean_tile_count=0,
                unique_colors=0,
                color_frequency={},
                color_frequency_by_part_type=by_type,
                most_common_color={},
                coverage_percentage=0.0,
                margin_tile_count=0 if on_template else None,
                plaque_tile_count=plaque_tiles
            )

        # Count colors
        color_counter = Counter(p.color_id for p in self._positions)
        color_frequency = dict(color_counter)

        # Count colors by part type
        plate_colors = Counter(p.color_id for p in self._positions if p.part_type == LAND_PART_TYPE)
        tile_colors = Counter(p.color_id for p in self._positions if p.part_type == OCEAN_PART_TYPE)

        # Find most common color
        most_common = color_counter.most_common(1)[0]
        most_common_pos = next(p for p in self._positions if p.color_id == most_common[0])
        most_common_color = {
            "color_id": most_common[0],
            "color_name": most_common_pos.color_name,
            "count": most_common[1]
        }

        # Calculate coverage
        expected_positions = self._width * self._height
        # feature 017: the in-margin plaque covers its studs
        covered = len(self._positions) + len(self._plaque_positions - set(self._position_map))
        coverage = (covered / expected_positions * 100.0) if expected_positions > 0 else 0.0

        by_type = {
            LAND_PART_TYPE: dict(plate_colors),
            OCEAN_PART_TYPE: dict(tile_colors)
        }
        if on_template:
            by_type[MARGIN_PART_TYPE] = dict(Counter(p.color_id for p in self._positions
                                                     if p.part_type == MARGIN_PART_TYPE))

        return LayoutStatistics(
            total_tile_count=len(self._positions),
            land_plate_count=self._land_positions,
            ocean_tile_count=self._ocean_positions,
            unique_colors=self._unique_colors,
            color_frequency=color_frequency,
            color_frequency_by_part_type=by_type,
            most_common_color=most_common_color,
            coverage_percentage=coverage,
            margin_tile_count=self._margin_positions if on_template else None,
            plaque_tile_count=plaque_tiles
        )

    def to_json(self, indent: int = 2) -> str:
        """Serialize grid to JSON string.

        Args:
            indent: JSON indentation level

        Returns:
            JSON string representation
        """
        data = {
            "metadata": {
                "width": self._width,
                "height": self._height,
                "total_positions": self.total_positions,
                "land_positions": self._land_positions,
                "ocean_positions": self._ocean_positions,
                "unique_colors": self._unique_colors,
                "generated_at": self._generated_at,
                "source_image": self._source_image,
                "schema_version": self._schema_version,
                "coordinate_system": self._coordinate_system,
                "disclaimer": DISCLAIMER
            },
            "positions": [p.to_dict() for p in self._positions],
            "statistics": self.compute_statistics().to_dict()
        }
        if self._template is not None:  # feature 016: the margin count follows the ocean count
            meta = data["metadata"]
            keys = list(meta)
            keys.insert(keys.index("ocean_positions") + 1, "margin_positions")
            meta["margin_positions"] = self._margin_positions
            data["metadata"] = {k: meta[k] for k in keys}
        if self._map_metadata is not None:
            data["metadata"]["map"] = self._map_metadata
        if self._arrangement is not None:
            data["metadata"]["arrangement"] = self._arrangement
        if self._template is not None:
            data["metadata"]["template"] = self._template
        if self._plaque is not None:  # feature 017: only when an in-margin plaque is placed
            data["metadata"]["plaque"] = self._plaque
        return json.dumps(data, indent=indent)

    def to_csv(self) -> str:
        """Serialize grid to CSV string.

        Returns:
            CSV string representation
        """
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            "x_position", "y_position", "color_id", "color_name",
            "lego_color_code", "part_type", "lego_part_id"
        ])

        # Write positions
        for pos in self._positions:
            writer.writerow([
                pos.x, pos.y, pos.color_id, pos.color_name,
                pos.lego_color_code, pos.part_type, pos.lego_part_id
            ])

        return output.getvalue()

    @classmethod
    def from_json(cls, json_str: str) -> PositionPlacementGrid:
        """Create grid from JSON string.

        Args:
            json_str: JSON string representation

        Returns:
            New PositionPlacementGrid instance

        Raises:
            LayoutSchemaError: if the schema version is missing or not the current one
        """
        data = json.loads(json_str)
        metadata = data["metadata"]
        version = metadata.get("schema_version")
        if version != CURRENT_SCHEMA_VERSION:
            raise LayoutSchemaError(version)

        positions = [
            PositionPlacement.from_dict(p)
            for p in data["positions"]
        ]

        return cls(
            width=metadata["width"],
            height=metadata["height"],
            positions=positions,
            source_image=metadata["source_image"],
            generated_at=metadata["generated_at"],
            schema_version=metadata["schema_version"],
            map_metadata=metadata.get("map"),
            arrangement=metadata.get("arrangement"),
            template=metadata.get("template"),
            plaque=metadata.get("plaque"),
        )

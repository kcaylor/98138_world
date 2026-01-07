"""Position placement grid and statistics for LEGO World Map layouts."""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import StringIO
from typing import Dict, List, Any, Optional

from .position import PositionPlacement


@dataclass
class LayoutStatistics:
    """Summary statistics about a generated layout.

    Provides quick overview of composition and part requirements without
    parsing the full position array.

    Attributes:
        total_tile_count: Total positions (e.g., 10,240)
        land_brick_count: Round bricks for land (e.g., 3,062)
        ocean_tile_count: Flat tiles for ocean (e.g., 7,178)
        unique_colors: Count of distinct colors used
        color_frequency: Map of color_id to position count
        color_frequency_by_part_type: Color frequency split by part type
        most_common_color: Color with highest frequency
        coverage_percentage: Percentage of grid filled (100.0 for valid layouts)
    """

    total_tile_count: int
    land_brick_count: int
    ocean_tile_count: int
    unique_colors: int
    color_frequency: Dict[str, int]
    color_frequency_by_part_type: Dict[str, Dict[str, int]]
    most_common_color: Dict[str, Any]
    coverage_percentage: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert statistics to dictionary.

        Returns:
            Dictionary with all statistics.
        """
        return {
            "total_tile_count": self.total_tile_count,
            "land_brick_count": self.land_brick_count,
            "ocean_tile_count": self.ocean_tile_count,
            "unique_colors": self.unique_colors,
            "color_frequency": self.color_frequency,
            "color_frequency_by_part_type": self.color_frequency_by_part_type,
            "most_common_color": self.most_common_color,
            "coverage_percentage": self.coverage_percentage
        }


class PositionPlacementGrid:
    """Complete LEGO World Map building plan.

    Represents a grid of position placements matching the official kit 31203
    structure (128x80 grid, 10,240 positions: 3,062 land bricks + 7,178 ocean tiles).

    Attributes:
        width: Grid width in studs (standard: 128)
        height: Grid height in studs (standard: 80)
        total_positions: Total positions (width x height)
        land_positions: Count of land positions (round bricks)
        ocean_positions: Count of ocean positions (flat tiles)
        unique_colors: Count of distinct colors used
        coordinate_system: Always "top_left_origin"
        generated_at: ISO 8601 timestamp when layout was generated
        source_image: Input quantized image filename
        schema_version: Schema version (current: "1.0")
        positions: List of all position placements
    """

    def __init__(
        self,
        width: int,
        height: int,
        positions: List[PositionPlacement],
        source_image: str,
        generated_at: Optional[str] = None,
        schema_version: str = "1.0"
    ):
        """Initialize position placement grid.

        Args:
            width: Grid width in studs
            height: Grid height in studs
            positions: List of position placements
            source_image: Input quantized image filename
            generated_at: Optional ISO 8601 timestamp (defaults to now)
            schema_version: Schema version
        """
        self._width = width
        self._height = height
        self._positions = list(positions)  # Make a copy
        self._source_image = source_image
        self._schema_version = schema_version
        self._coordinate_system = "top_left_origin"

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
        self._land_positions = sum(1 for p in self._positions if p.part_type == "brick")
        self._ocean_positions = sum(1 for p in self._positions if p.part_type == "tile")
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
        """Count of land positions (round bricks)."""
        return self._land_positions

    @property
    def ocean_positions(self) -> int:
        """Count of ocean positions (flat tiles)."""
        return self._ocean_positions

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
        if not self._positions:
            return LayoutStatistics(
                total_tile_count=0,
                land_brick_count=0,
                ocean_tile_count=0,
                unique_colors=0,
                color_frequency={},
                color_frequency_by_part_type={"brick": {}, "tile": {}},
                most_common_color={},
                coverage_percentage=0.0
            )

        # Count colors
        color_counter = Counter(p.color_id for p in self._positions)
        color_frequency = dict(color_counter)

        # Count colors by part type
        brick_colors = Counter(p.color_id for p in self._positions if p.part_type == "brick")
        tile_colors = Counter(p.color_id for p in self._positions if p.part_type == "tile")

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
        coverage = (len(self._positions) / expected_positions * 100.0) if expected_positions > 0 else 0.0

        return LayoutStatistics(
            total_tile_count=len(self._positions),
            land_brick_count=self._land_positions,
            ocean_tile_count=self._ocean_positions,
            unique_colors=self._unique_colors,
            color_frequency=color_frequency,
            color_frequency_by_part_type={
                "brick": dict(brick_colors),
                "tile": dict(tile_colors)
            },
            most_common_color=most_common_color,
            coverage_percentage=coverage
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
                "coordinate_system": self._coordinate_system
            },
            "positions": [p.to_dict() for p in self._positions],
            "statistics": self.compute_statistics().to_dict()
        }
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
        """
        data = json.loads(json_str)
        metadata = data["metadata"]

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
            schema_version=metadata["schema_version"]
        )

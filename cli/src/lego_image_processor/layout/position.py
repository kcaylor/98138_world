"""Position placement class for LEGO World Map layouts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class PositionPlacement:
    """Represents a single LEGO part placement at a specific grid position.

    Land positions use round bricks (LEGO part 3062b) that stand taller.
    Ocean positions use flat tiles (LEGO part 98138) that sit flush with base plate.

    Attributes:
        x: X coordinate (0-based, increases rightward, range: 0-127)
        y: Y coordinate (0-based, increases downward, range: 0-79)
        color_id: LEGO color identifier (e.g., "lego_blue_medium")
        color_name: Human-readable color name (e.g., "Medium Blue")
        lego_color_code: Official LEGO color code (e.g., "102")
        part_type: Part type - "brick" for land, "tile" for ocean
        lego_part_id: LEGO part number - "3062b" for bricks, "98138" for tiles
    """

    x: int
    y: int
    color_id: str
    color_name: str
    lego_color_code: str
    part_type: str
    lego_part_id: str

    def __post_init__(self) -> None:
        """Validate position placement attributes."""
        # Validate coordinates
        if self.x < 0:
            raise ValueError(f"x coordinate must be >= 0, got {self.x}")
        if self.y < 0:
            raise ValueError(f"y coordinate must be >= 0, got {self.y}")

        # Validate part_type
        if self.part_type not in ("brick", "tile"):
            raise ValueError(f"part_type must be 'brick' or 'tile', got '{self.part_type}'")

        # Validate lego_part_id
        if self.lego_part_id not in ("3062b", "98138"):
            raise ValueError(f"lego_part_id must be '3062b' or '98138', got '{self.lego_part_id}'")

        # Validate invariant: part_type and lego_part_id must match
        if self.part_type == "brick" and self.lego_part_id != "3062b":
            raise ValueError(f"part_type 'brick' must use lego_part_id '3062b', got '{self.lego_part_id}'")
        if self.part_type == "tile" and self.lego_part_id != "98138":
            raise ValueError(f"part_type 'tile' must use lego_part_id '98138', got '{self.lego_part_id}'")

    def to_dict(self) -> Dict[str, Any]:
        """Convert position placement to dictionary.

        Returns:
            Dictionary with all position attributes.
        """
        return {
            "x": self.x,
            "y": self.y,
            "color_id": self.color_id,
            "color_name": self.color_name,
            "lego_color_code": self.lego_color_code,
            "part_type": self.part_type,
            "lego_part_id": self.lego_part_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PositionPlacement:
        """Create position placement from dictionary.

        Args:
            data: Dictionary with position attributes.

        Returns:
            New PositionPlacement instance.
        """
        return cls(
            x=data["x"],
            y=data["y"],
            color_id=data["color_id"],
            color_name=data["color_name"],
            lego_color_code=data["lego_color_code"],
            part_type=data["part_type"],
            lego_part_id=data["lego_part_id"]
        )

    def __repr__(self) -> str:
        """Return string representation of position placement."""
        return (
            f"PositionPlacement(x={self.x}, y={self.y}, "
            f"color_id='{self.color_id}', part_type='{self.part_type}', "
            f"lego_part_id='{self.lego_part_id}')"
        )

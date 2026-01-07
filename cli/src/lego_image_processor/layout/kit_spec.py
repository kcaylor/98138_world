"""Kit specification for LEGO World Map validation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any


# Default kit configuration path
KIT_DATA_PATH = Path(__file__).parent.parent / "data" / "lego_world_map_kit.json"


@dataclass
class LEGOWorldMapKitSpecification:
    """Reference data for official LEGO World Map kit 31203.

    Contains constant structure (dimensions, part types) and variable
    components (available colors, quantities) for validation.

    Attributes:
        kit_id: Official LEGO kit ID (e.g., "31203")
        kit_name: Official kit name
        base_plate_width: Total width in studs (128)
        base_plate_height: Total height in studs (80)
        total_positions: Total positions (10,240)
        land_positions: Land positions (3,062)
        ocean_positions: Ocean positions (7,178)
        land_part_id: LEGO part for land ("3062b")
        ocean_part_id: LEGO part for ocean ("98138")
        available_colors_brick: Colors available for round bricks
        available_colors_tile: Colors available for flat tiles
        brick_quantities: Quantity of each brick color in kit
        tile_quantities: Quantity of each tile color in kit
    """

    # Constant structure
    kit_id: str
    kit_name: str
    base_plate_width: int
    base_plate_height: int
    total_positions: int
    land_positions: int
    ocean_positions: int
    land_part_id: str
    ocean_part_id: str

    # Variable components
    available_colors_brick: List[str] = field(default_factory=list)
    available_colors_tile: List[str] = field(default_factory=list)
    brick_quantities: Dict[str, int] = field(default_factory=dict)
    tile_quantities: Dict[str, int] = field(default_factory=dict)

    def is_brick_color_available(self, color_id: str) -> bool:
        """Check if color is available for round bricks.

        Args:
            color_id: LEGO color identifier

        Returns:
            True if color is available for bricks
        """
        return color_id in self.available_colors_brick

    def is_tile_color_available(self, color_id: str) -> bool:
        """Check if color is available for flat tiles.

        Args:
            color_id: LEGO color identifier

        Returns:
            True if color is available for tiles
        """
        return color_id in self.available_colors_tile

    def get_brick_quantity(self, color_id: str) -> int:
        """Get available quantity of brick color.

        Args:
            color_id: LEGO color identifier

        Returns:
            Available quantity, 0 if color not in kit
        """
        return self.brick_quantities.get(color_id, 0)

    def get_tile_quantity(self, color_id: str) -> int:
        """Get available quantity of tile color.

        Args:
            color_id: LEGO color identifier

        Returns:
            Available quantity, 0 if color not in kit
        """
        return self.tile_quantities.get(color_id, 0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert kit specification to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "kit_id": self.kit_id,
            "kit_name": self.kit_name,
            "base_plate_width": self.base_plate_width,
            "base_plate_height": self.base_plate_height,
            "total_positions": self.total_positions,
            "land_positions": self.land_positions,
            "ocean_positions": self.ocean_positions,
            "land_part_id": self.land_part_id,
            "ocean_part_id": self.ocean_part_id,
            "available_colors_brick": self.available_colors_brick,
            "available_colors_tile": self.available_colors_tile,
            "brick_quantities": self.brick_quantities,
            "tile_quantities": self.tile_quantities
        }

    @classmethod
    def from_json(cls, json_str: str) -> LEGOWorldMapKitSpecification:
        """Create kit specification from JSON string.

        Args:
            json_str: JSON string

        Returns:
            New kit specification instance
        """
        data = json.loads(json_str)
        return cls(
            kit_id=data["kit_id"],
            kit_name=data["kit_name"],
            base_plate_width=data["base_plate_width"],
            base_plate_height=data["base_plate_height"],
            total_positions=data["total_positions"],
            land_positions=data["land_positions"],
            ocean_positions=data["ocean_positions"],
            land_part_id=data["land_part_id"],
            ocean_part_id=data["ocean_part_id"],
            available_colors_brick=data.get("available_colors_brick", []),
            available_colors_tile=data.get("available_colors_tile", []),
            brick_quantities=data.get("brick_quantities", {}),
            tile_quantities=data.get("tile_quantities", {})
        )


def load_kit_specification(kit_id: str = "31203") -> LEGOWorldMapKitSpecification:
    """Load kit specification from configuration file.

    Args:
        kit_id: Kit ID to load (currently only "31203" supported)

    Returns:
        LEGOWorldMapKitSpecification instance

    Raises:
        FileNotFoundError: If kit configuration file not found
        ValueError: If kit_id not supported
    """
    if kit_id != "31203":
        raise ValueError(
            f"Kit ID '{kit_id}' not supported. "
            f"Currently only '31203' (LEGO World Map) is supported."
        )

    if not KIT_DATA_PATH.exists():
        raise FileNotFoundError(f"Kit configuration file not found: {KIT_DATA_PATH}")

    with open(KIT_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    return LEGOWorldMapKitSpecification(
        kit_id=data["kit_id"],
        kit_name=data["kit_name"],
        base_plate_width=data["base_plate_width"],
        base_plate_height=data["base_plate_height"],
        total_positions=data["total_positions"],
        land_positions=data["land_positions"],
        ocean_positions=data["ocean_positions"],
        land_part_id=data["land_part_id"],
        ocean_part_id=data["ocean_part_id"],
        available_colors_brick=data.get("available_colors_brick", []),
        available_colors_tile=data.get("available_colors_tile", []),
        brick_quantities=data.get("brick_quantities", {}),
        tile_quantities=data.get("tile_quantities", {})
    )

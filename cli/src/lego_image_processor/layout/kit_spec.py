"""Kit specification for LEGO World Map validation, built from cited reference data.

Colors come from ``data/kit_colors.json``, quantities from ``data/kit_31203_inventory.json``
(instructions page 159) and position counts from the land/sea mask. No quantities are stored here.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..kit.inventory import check_kit_id, load_kit_inventory
from .position import LAND_PART_ID, OCEAN_PART_ID


@dataclass
class LEGOWorldMapKitSpecification:
    """Reference data for LEGO World Map kit 31203 used by the validator.

    Attributes:
        land_part_id: land part, the 1x1 round plate ("6141")
        ocean_part_id: ocean part, the 1x1 round tile ("98138")
        available_colors_plate: kit color keys for the land plate (1)
        available_colors_tile: kit color keys for the ocean tile (9)
        plate_quantities / tile_quantities: supplied pieces per color key (from the inventory)
    """

    kit_id: str
    kit_name: str
    base_plate_width: int
    base_plate_height: int
    total_positions: int
    land_positions: int
    ocean_positions: int
    land_part_id: str
    ocean_part_id: str
    available_colors_plate: List[str] = field(default_factory=list)
    available_colors_tile: List[str] = field(default_factory=list)
    plate_quantities: Dict[str, int] = field(default_factory=dict)
    tile_quantities: Dict[str, int] = field(default_factory=dict)
    inventory_lines: int = 0
    inventory_page: int = 0

    def is_plate_color_available(self, color_id: str) -> bool:
        return color_id in self.available_colors_plate

    def is_tile_color_available(self, color_id: str) -> bool:
        return color_id in self.available_colors_tile

    def get_plate_quantity(self, color_id: str) -> int:
        return self.plate_quantities.get(color_id, 0)

    def get_tile_quantity(self, color_id: str) -> int:
        return self.tile_quantities.get(color_id, 0)

    def to_dict(self) -> Dict[str, Any]:
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
            "available_colors_plate": list(self.available_colors_plate),
            "available_colors_tile": list(self.available_colors_tile),
            "plate_quantities": dict(self.plate_quantities),
            "tile_quantities": dict(self.tile_quantities),
            "inventory_lines": self.inventory_lines,
            "inventory_page": self.inventory_page,
        }

    @classmethod
    def from_json(cls, json_str: str) -> LEGOWorldMapKitSpecification:
        data = json.loads(json_str)
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})


def load_kit_specification(kit_id: str = "31203") -> LEGOWorldMapKitSpecification:
    """Build the kit specification from the inventory, color table and land/sea mask.

    Raises:
        UnsupportedKitError (a ValueError): for any kit other than 31203
    """
    check_kit_id(kit_id)
    from .land_sea_mask import load_land_sea_mask

    inventory = load_kit_inventory(kit_id)
    mask = load_land_sea_mask()
    land = inventory.land_element()
    ocean = inventory.ocean_elements()
    return LEGOWorldMapKitSpecification(
        kit_id=kit_id,
        kit_name="LEGO World Map",
        base_plate_width=mask.width,
        base_plate_height=mask.height,
        total_positions=mask.total_positions,
        land_positions=mask.land_count,
        ocean_positions=mask.ocean_count,
        land_part_id=LAND_PART_ID,
        ocean_part_id=OCEAN_PART_ID,
        available_colors_plate=[land.color_key],
        available_colors_tile=[e.color_key for e in ocean],
        plate_quantities={land.color_key: land.quantity},
        tile_quantities={e.color_key: e.quantity for e in ocean},
        inventory_lines=inventory.totals["lines"],
        inventory_page=inventory.elements[0].source_page,
    )

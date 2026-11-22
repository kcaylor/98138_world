"""Synthetic layouts for the parts tests (005 T002).

Layouts are built in memory: positions are placed row by row on the 128x80 grid with the chosen
color counts (they need not follow the kit mask; the parts list only counts positions).
"""

from typing import Iterable, Tuple

from lego_image_processor.layout.grid import PositionPlacementGrid
from lego_image_processor.layout.position import PositionPlacement

# (part_type, color key, color name, LEGO code, count)
Spec = Tuple[str, str, str, str, int]


def make_grid(specs: Iterable[Spec], source_image="synthetic.png", map_metadata=None) -> PositionPlacementGrid:
    positions, i = [], 0
    for part_type, key, name, code, n in specs:
        part = "6141" if part_type == "plate" else "98138"
        for _ in range(n):
            positions.append(PositionPlacement(x=i % 128, y=i // 128, color_id=key, color_name=name,
                                               lego_color_code=str(code), part_type=part_type,
                                               lego_part_id=part))
            i += 1
    return PositionPlacementGrid(width=128, height=80, positions=positions, source_image=source_image,
                                 generated_at="2026-11-22T00:00:00Z", map_metadata=map_metadata)


# The land-elevation counts measured on the real-data build (005 research R6).
LAND_ELEVATION = [
    ("plate", "lego_white", "White", "1", 150),
    ("plate", "lego_dark_green", "Dark Green", "28", 506),
    ("plate", "lego_bright_green", "Bright Green", "37", 528),
    ("plate", "lego_bright_yellowish_green", "Bright Yellowish Green", "119", 515),
    ("plate", "lego_brick_yellow", "Brick Yellow", "5", 350),
    ("plate", "lego_sand_yellow", "Sand Yellow", "138", 231),
    ("plate", "lego_medium_nougat", "Medium Nougat", "312", 311),
    ("plate", "lego_reddish_brown", "Reddish Brown", "192", 158),
    ("plate", "lego_dark_brown", "Dark Brown", "308", 128),
    ("plate", "lego_medium_stone_grey", "Medium Stone Grey", "194", 185),
    ("tile", "lego_bright_bluish_green", "Bright Bluish Green", "107", 5024),
    ("tile", "lego_medium_azur", "Medium Azur", "322", 1436),
    ("tile", "lego_earth_blue", "Earth Blue", "140", 718),
]

SMALL = [
    ("plate", "lego_white", "White", "1", 30),
    ("plate", "lego_brick_yellow", "Brick Yellow", "5", 12),
    ("tile", "lego_medium_azur", "Medium Azur", "322", 20),
    ("tile", "lego_bright_red", "Bright Red", "21", 7),
]
# Medium Blue is not on BrickLink's page for item 4073, so it has no cited plate row (rule 5).
UNCITED = SMALL + [("plate", "lego_medium_blue", "Medium Blue", "102", 5)]
MISMATCH = SMALL + [("plate", "lego_black", "Black", "999", 4)]

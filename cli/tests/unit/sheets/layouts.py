"""Full 128x80 synthetic layouts for the build-sheet tests (006).

Build sheets need every one of the 10,240 positions. These helpers fill the grid by cycling a list
of colors so each section gets a known, reproducible mix.
"""

from typing import List, Sequence, Tuple

from lego_image_processor.kit.part_colors import load_part_colors
from lego_image_processor.layout.grid import PositionPlacementGrid
from lego_image_processor.layout.position import PositionPlacement

# (part_type, color key, color name, LEGO code)
Color = Tuple[str, str, str, str]

PART = {"plate": "6141", "tile": "98138"}


def full_grid(colors: Sequence[Color], source_image="synthetic.png", map_metadata=None,
              stride: int = 1) -> PositionPlacementGrid:
    """Every position filled; color index = ((x // stride) + y) mod len(colors)."""
    positions = []
    for y in range(80):
        for x in range(128):
            part_type, key, name, code = colors[((x // stride) + y) % len(colors)]
            positions.append(PositionPlacement(x=x, y=y, color_id=key, color_name=name,
                                               lego_color_code=str(code), part_type=part_type,
                                               lego_part_id=PART[part_type]))
    return PositionPlacementGrid(width=128, height=80, positions=positions, source_image=source_image,
                                 generated_at="2026-11-22T00:00:00Z", map_metadata=map_metadata)


FEW: List[Color] = [
    ("plate", "lego_white", "White", "1"),
    ("plate", "lego_brick_yellow", "Brick Yellow", "5"),
    ("tile", "lego_medium_azur", "Medium Azur", "322"),
    ("tile", "lego_earth_blue", "Earth Blue", "140"),
    ("tile", "lego_bright_green", "Bright Green", "37"),
    ("plate", "lego_bright_green", "Bright Green", "37"),
]

# Medium Blue has no cited plate row (005 rule 5), so it is an unverified lot.
WITH_UNCITED: List[Color] = FEW + [("plate", "lego_medium_blue", "Medium Blue", "102")]


def every_cited_color() -> List[Color]:
    """All 84 cited part-color rows (44 plate, 40 tile) plus six uncited plates: 90 lots."""
    out: List[Color] = []
    table = load_part_colors()
    for part_id, part_type in (("6141", "plate"), ("98138", "tile")):
        for row in table.for_part(part_id):
            out.append((part_type, row.key, row.lego.name, str(row.lego.id)))
    for i in range(6):
        out.append(("plate", f"lego_uncited_{i}", f"Uncited {i}", str(9000 + i)))
    return out

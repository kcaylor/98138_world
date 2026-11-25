"""Synthetic layouts on a non-kit template for the feature 016 parts, sheets and validation tests.

``winkel_grid(template)`` fills every stud of a loaded template (``confirmed_winkel`` or
``synthetic_template``) by its class: land a plate color, ocean a tile color, margin the square
tile in Black (and, with ``ring``, the template's ring studs in a second square-tile color), and
records ``metadata.template`` as a template build does. With ``plaque`` (feature 017: a
``metadata.plaque`` record, e.g. ``place_plaque(...).layout_record()``) the plaque's studs carry no
position and the record is written, as a build with ``--plaque`` does. No dataset is read, so the
tests are fast; the integration tests build real recipes on the fixtures instead.
Not affiliated with or endorsed by The LEGO Group.
"""

from typing import Optional, Tuple

from lego_image_processor.layout.grid import PositionPlacementGrid
from lego_image_processor.layout.position import PART_ID_FOR_TYPE, PositionPlacement

# (color key, color name, LEGO code)
Color = Tuple[str, str, str]

WHITE: Color = ("lego_white", "White", "1")
MEDIUM_AZUR: Color = ("lego_medium_azur", "Medium Azur", "322")
EARTH_BLUE: Color = ("lego_earth_blue", "Earth Blue", "140")
BLACK: Color = ("lego_black", "Black", "26")
BRIGHT_YELLOW: Color = ("lego_bright_yellow", "Bright Yellow", "24")
TYPE_FOR_CLASS = {"land": "plate", "ocean": "tile", "margin": "square_tile"}


def winkel_grid(template, land: Color = WHITE, ocean: Tuple[Color, ...] = (MEDIUM_AZUR, EARTH_BLUE),
                margin: Color = BLACK, ring: Optional[Color] = None,
                map_metadata=None, plaque=None) -> PositionPlacementGrid:
    """Every stud of ``template`` by class; ocean colors alternate by column. ``plaque`` (a
    ``metadata.plaque`` record) leaves its studs out."""
    ring_mask = template.ring
    covered = set()
    if plaque is not None:
        s = plaque["studs"]
        covered = {(x, y) for y in range(s["row"], s["row"] + s["height"])
                   for x in range(s["col"], s["col"] + s["width"])}
    positions = []
    for y in range(template.height):
        for x in range(template.width):
            if (x, y) in covered:
                continue
            cls = template.class_at(y, x)
            if cls == "land":
                key, name, code = land
            elif cls == "ocean":
                key, name, code = ocean[x % len(ocean)]
            else:
                key, name, code = ring if ring is not None and ring_mask[y, x] else margin
            part_type = TYPE_FOR_CLASS[cls]
            positions.append(PositionPlacement(x=x, y=y, color_id=key, color_name=name,
                                               lego_color_code=code, part_type=part_type,
                                               lego_part_id=PART_ID_FOR_TYPE[part_type]))
    return PositionPlacementGrid(width=template.width, height=template.height, positions=positions,
                                 source_image="recipe:synthetic-winkel",
                                 generated_at="2026-11-23T00:00:00Z", map_metadata=map_metadata,
                                 template=template.layout_record(), plaque=plaque)

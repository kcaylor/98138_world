"""Kit 31203 reference data: inventory, color table and the official design.

All loaders read package data only (no network, no API keys).
Not affiliated with or endorsed by The LEGO Group.
"""

from .colors import CatalogColor, KitColor, KitColorTable, load_kit_color_table, load_kit_colors
from .design import ColorCount, DesignGrid, Section, load_official_design
from .inventory import KitElement, KitInventory, UnsupportedKitError, load_kit_inventory
from .part_colors import PartColor, PartColorTable, colors_for_part, load_part_colors
from .part_numbers import PartNumberTable, PartNumbers, PinnedPage, load_part_numbers
from .plaque_parts import Plaque, PlaquePart, PlaquePartTable, load_plaque_parts
from .source import DISCLAIMER, Citation, SourceDocument

__all__ = [
    "SourceDocument", "Citation", "DISCLAIMER",
    "CatalogColor", "KitColor", "KitColorTable", "load_kit_colors", "load_kit_color_table",
    "KitElement", "KitInventory", "load_kit_inventory",
    "Section", "DesignGrid", "ColorCount", "load_official_design",
    "UnsupportedKitError",
    "PartColor", "PartColorTable", "load_part_colors", "colors_for_part",
    "PartNumbers", "PartNumberTable", "PinnedPage", "load_part_numbers",
    "Plaque", "PlaquePart", "PlaquePartTable", "load_plaque_parts",
]

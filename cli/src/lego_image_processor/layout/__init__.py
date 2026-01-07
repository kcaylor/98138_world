"""LEGO World Map layout generation module."""

from .position import PositionPlacement

__all__ = [
    "PositionPlacement",
]

# Lazy imports to avoid circular dependencies
def __getattr__(name):
    if name == "PositionPlacementGrid":
        from .grid import PositionPlacementGrid
        return PositionPlacementGrid
    elif name == "LayoutStatistics":
        from .grid import LayoutStatistics
        return LayoutStatistics
    elif name == "LandSeaMask":
        from .land_sea_mask import LandSeaMask
        return LandSeaMask
    elif name == "load_land_sea_mask":
        from .land_sea_mask import load_land_sea_mask
        return load_land_sea_mask
    elif name == "LayoutGenerator":
        from .generator import LayoutGenerator
        return LayoutGenerator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

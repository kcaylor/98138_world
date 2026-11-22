"""Land/sea mask for LEGO World Map layouts."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional, Set, Tuple

from .position import LAND_PART_ID, LAND_PART_TYPE, OCEAN_PART_ID, OCEAN_PART_TYPE


# Land/sea mask shipped with the package (runtime reference data)
MASK_PATH = Path(__file__).parent.parent / "data" / "lego_world_map_land_sea_mask.json"


class LandSeaMask:
    """Binary classification of grid positions into land (plates) or ocean (tiles).

    Derived from the official design of kit 31203 (white positions are land), which the
    maintainer tool extracts from the pinned instructions PDF. This classification is constant
    across all custom maps - only colors vary.

    Attributes:
        width: Mask width in positions (128)
        height: Mask height in positions (80)
        total_positions: Total positions (10,240)
        land_count: Land positions (3,062)
        ocean_count: Ocean positions (7,178)
        land_percentage: Land percentage (~29.9%)
        ocean_percentage: Ocean percentage (~70.1%)
        source: Extraction source reference
        extracted_date: Extraction date
    """

    def __init__(
        self,
        width: int,
        height: int,
        land_positions: Set[Tuple[int, int]],
        source: str,
        extracted_date: str,
        derived_from: Optional[str] = None,
    ):
        """Initialize land/sea mask.

        Args:
            width: Mask width in positions
            height: Mask height in positions
            land_positions: Set of (x, y) coordinates that are land
            source: Extraction source reference (URL of the pinned instructions PDF)
            extracted_date: Extraction date (YYYY-MM-DD)
            derived_from: Design file the mask was derived from, if any
        """
        self._width = width
        self._height = height
        self._land_positions = land_positions
        self._source = source
        self._extracted_date = extracted_date
        self._derived_from = derived_from

        # Compute counts
        self._land_count = len(land_positions)
        self._total_positions = width * height
        self._ocean_count = self._total_positions - self._land_count

    @property
    def width(self) -> int:
        """Mask width in positions."""
        return self._width

    @property
    def height(self) -> int:
        """Mask height in positions."""
        return self._height

    @property
    def total_positions(self) -> int:
        """Total positions."""
        return self._total_positions

    @property
    def land_count(self) -> int:
        """Land positions count."""
        return self._land_count

    @property
    def ocean_count(self) -> int:
        """Ocean positions count."""
        return self._ocean_count

    @property
    def land_percentage(self) -> float:
        """Land percentage."""
        if self._total_positions == 0:
            return 0.0
        return (self._land_count / self._total_positions) * 100.0

    @property
    def ocean_percentage(self) -> float:
        """Ocean percentage."""
        if self._total_positions == 0:
            return 0.0
        return (self._ocean_count / self._total_positions) * 100.0

    @property
    def source(self) -> str:
        """Extraction source reference."""
        return self._source

    @property
    def extracted_date(self) -> str:
        """Extraction date."""
        return self._extracted_date

    @property
    def derived_from(self) -> Optional[str]:
        """Design file the mask was derived from (``kit_31203_design.json``)."""
        return self._derived_from

    def is_land(self, x: int, y: int) -> bool:
        """Check if position (x, y) is land.

        Args:
            x: X coordinate (0-127)
            y: Y coordinate (0-79)

        Returns:
            True if position is land, False if ocean

        Raises:
            IndexError: If coordinates are out of bounds
        """
        if x < 0 or x >= self._width:
            raise IndexError(f"x coordinate {x} out of range [0, {self._width})")
        if y < 0 or y >= self._height:
            raise IndexError(f"y coordinate {y} out of range [0, {self._height})")

        return (x, y) in self._land_positions

    def get_part_type(self, x: int, y: int) -> str:
        """Get part type for position.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            'plate' for land, 'tile' for ocean
        """
        return LAND_PART_TYPE if self.is_land(x, y) else OCEAN_PART_TYPE

    def get_lego_part_id(self, x: int, y: int) -> str:
        """Get LEGO part ID for position.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            '6141' for land (1x1 round plate), '98138' for ocean (1x1 round tile)
        """
        return LAND_PART_ID if self.is_land(x, y) else OCEAN_PART_ID


@lru_cache(maxsize=1)
def load_land_sea_mask(mask_path: str = None) -> LandSeaMask:
    """Load the land/sea mask bundled with the package.

    Uses @lru_cache to avoid reloading the file on repeated calls.

    Args:
        mask_path: Optional custom path to mask file (for testing)

    Returns:
        LandSeaMask instance

    Raises:
        FileNotFoundError: If mask file not found
        ValueError: If mask has invalid structure
    """
    path = Path(mask_path) if mask_path else MASK_PATH

    if not path.exists():
        raise FileNotFoundError(f"Land/sea mask file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Parse dimensions
    dimensions = data.get("dimensions", {})
    width = dimensions.get("width", 128)
    height = dimensions.get("height", 80)

    # Parse land coordinates
    land_coordinates = data.get("land_coordinates", [])
    land_positions = set()
    for coord in land_coordinates:
        if isinstance(coord, list) and len(coord) == 2:
            x, y = coord
            land_positions.add((x, y))

    # Validate counts
    expected_land = data.get("land_positions", 3062)
    if len(land_positions) != expected_land:
        raise ValueError(
            f"Land position count mismatch: expected {expected_land}, "
            f"got {len(land_positions)}"
        )

    # Provenance: a ``source`` block (url, generated_on, ...). The old free-text form is still
    # accepted for the date during the transition (contracts/data-files.md).
    raw_source = data.get("source")
    if isinstance(raw_source, dict):
        source = raw_source.get("url", "")
        extracted_date = raw_source.get("generated_on", "")
    else:
        source = raw_source or "LEGO World Map kit 31203 instruction manual"
        extracted_date = data.get("extracted_date", data.get("extraction_date", ""))

    return LandSeaMask(
        width=width,
        height=height,
        land_positions=land_positions,
        source=source,
        extracted_date=extracted_date,
        derived_from=data.get("derived_from"),
    )

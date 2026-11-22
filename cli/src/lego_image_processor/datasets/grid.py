"""A gridded field read from a dataset, normalised for reprojection (data-model.md SourceGrid).

Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np


@dataclass
class SourceGrid:
    """``values[i, j]`` at ``lat[i]``, ``lon[j]``; NaN is missing.

    ``lat`` is ascending; ``lon`` is in -180..180 and ascending. ``land`` marks source cells that
    count as land (None: the source does not say). ``on_kit_grid`` grids are already 80x128 kit
    cells (row 0 at the top) and skip reprojection; ``categories`` names integer category codes.
    """

    values: np.ndarray
    lat: np.ndarray
    lon: np.ndarray
    land: Optional[np.ndarray] = None
    units: str = ""
    categories: Optional[List[str]] = None
    on_kit_grid: bool = False

    def __post_init__(self) -> None:
        if not self.on_kit_grid and self.values.shape != (len(self.lat), len(self.lon)):
            raise ValueError(f"values shape {self.values.shape} does not match lat/lon "
                             f"({len(self.lat)}, {len(self.lon)})")


def normalise(values: np.ndarray, lat: np.ndarray, lon: np.ndarray):
    """Sort latitude ascending and wrap longitude to -180..180 ascending (edge cases in spec)."""
    values = np.asarray(values, dtype=float)
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    if lat.size > 1 and lat[0] > lat[-1]:
        lat = lat[::-1]
        values = values[::-1, :]
    wrapped = ((lon + 180.0) % 360.0) - 180.0
    order = np.argsort(wrapped, kind="stable")
    return values[:, order], lat, wrapped[order]

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
    counts: Optional[np.ndarray] = None   # feature 012: valid steps per pixel (climatology-mean)
    steps: Optional[int] = None           # feature 012: steps on the reduced axis
    missing: Optional[np.ndarray] = None  # feature 012: class pixels whose value was filled in

    def __post_init__(self) -> None:
        if not self.on_kit_grid and self.values.shape != (len(self.lat), len(self.lon)):
            raise ValueError(f"values shape {self.values.shape} does not match lat/lon "
                             f"({len(self.lat)}, {len(self.lon)})")


def extend_latitudes(grid: "SourceGrid", south: float, north: float) -> "SourceGrid":
    """Pad a regular grid with missing rows at its own spacing so it reaches ``south``..``north``
    (cell centres stay inside the range). Used before a land mask from another dataset is applied,
    so land outside the file's coverage exists as land with no value (feature 012, R4)."""
    lat = np.asarray(grid.lat, dtype=float)
    if lat.size < 2:
        return grid
    d = float(np.median(np.diff(lat)))
    if d <= 0:
        return grid
    below = int(np.floor((lat[0] - south) / d + 1e-9))
    above = int(np.floor((north - lat[-1]) / d + 1e-9))
    below, above = max(below, 0), max(above, 0)
    if not below and not above:
        return grid
    new_lat = np.concatenate([lat[0] - d * np.arange(below, 0, -1), lat, lat[-1] + d * np.arange(1, above + 1)])

    def pad(a, value):
        if a is None:
            return None
        return np.pad(a, ((below, above), (0, 0)), constant_values=value)

    return SourceGrid(values=pad(grid.values, np.nan), lat=new_lat, lon=grid.lon,
                      land=pad(grid.land, False), units=grid.units, categories=grid.categories,
                      counts=pad(grid.counts, 0), steps=grid.steps, missing=pad(grid.missing, False))


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

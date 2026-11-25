"""Override rules of a data layer (feature 013, specs/013-rainfall/contracts/recipe-and-datasets.md).

Computed in kit coordinates (combination A), like the other per-cell work. Each override takes the
layer's cells not yet taken (by the shadow, a no-data rule or an earlier override):

- region: the cell centre is strictly inside the bounds and outside every ``exclude`` box;
- dataset: the mean of the dataset's valid values in the cell is at least ``min_value``, or the
  cell has no valid value and its centre lies poleward of ``unobserved_lat``.

Feature 016 (FR-008, spec Edge Cases): on a non-kit template the "cell centre" is each stud's own
stored location (``reproject.cell_centres``) and the dataset is binned into studs by the template's
forward formula (``reproject.cell_means``), so the same place gets the same rule on every template.
Margin studs have no location and are never in a layer's mask.

Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from typing import List, Sequence

import numpy as np

from .projection import KitProjection
from .recipe import Override, Region
from .reproject import cell_centres, cell_means


def _inside(region: Region, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    out = np.ones(lat.shape, dtype=bool)
    if region.lat_min is not None:
        out &= lat > region.lat_min
    if region.lat_max is not None:
        out &= lat < region.lat_max
    if region.lon_min is not None:
        out &= lon > region.lon_min
    if region.lon_max is not None:
        out &= lon < region.lon_max
    return out


def override_cells(overrides: Sequence[Override], mask: np.ndarray, taken: np.ndarray,
                   projection: KitProjection, cls: str, cache_dir=None) -> List[np.ndarray]:
    """One boolean 80 x 128 array per override (kit coordinates); they do not overlap."""
    from ..datasets.cache import resolve
    from ..datasets.readers import read_dataset

    mask = np.asarray(mask, dtype=bool)
    free = mask & ~np.asarray(taken, dtype=bool)
    lat, lon = cell_centres(projection)
    free &= np.isfinite(lat) & np.isfinite(lon)  # feature 016: a template's margin studs (no location)
    out = []
    for o in overrides:
        if o.region is not None:
            cells = _inside(o.region, lat, lon)
            for ex in o.exclude:
                cells &= ~_inside(ex, lat, lon)
        else:
            entry = o.dataset
            grid = read_dataset(entry, resolve(entry, cache_dir), o.variable, cache_dir=cache_dir)
            if grid.on_kit_grid:  # pragma: no cover - recipe validation rejects kit-design
                raise ValueError(f"override {o.name}: dataset {entry.id} is not a gridded field")
            mean, n = cell_means(grid, projection, cls)
            with np.errstate(invalid="ignore"):
                cells = (n > 0) & (mean >= o.min_value)
            if o.unobserved_lat is not None:
                cells |= (n == 0) & (np.abs(lat) > o.unobserved_lat)
        cells &= free
        free &= ~cells
        out.append(cells)
    return out

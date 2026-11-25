"""No-data rules of a data layer (feature 012, contracts/recipe-and-datasets.md).

Two steps, both in kit coordinates (combination A), like the rest of the per-cell work:

1. ``apply_value``: class source pixels with no value take ``no_data.value`` (after the layer's
   transform); the pixels that had no value are remembered in ``grid.missing``.
2. ``no_data_cells``: the kit cells of the layer that take ``no_data.color`` instead of a class:
   ``unobserved`` (no valid source value, poleward of ``min_lat``; or poleward of ``sparse_lat``
   with fewer than ``min_steps`` valid steps in the cell's best source pixel) or ``share`` (the
   share of the cell's class pixels that had no value and lie poleward of ``min_lat`` exceeds
   ``min_share``; cells with no class pixel take the nearest cell's share, as values do).

Feature 016 (FR-008, spec Edge Cases): on a non-kit template the latitudes are each stud's own
stored location and source pixels are binned by the template's forward formula
(``reproject.source_cells``), so the same place gets the same rule on every template.

Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np

from ..datasets.grid import SourceGrid
from .projection import KitProjection
from .recipe import NoData
from .reproject import LayerField, _is_template, reproject_layer, source_cells


def class_pixels(grid: SourceGrid, cls: str) -> np.ndarray:
    """Source pixels of the layer's class (all pixels when the source does not say)."""
    if grid.land is None:
        return np.ones(grid.values.shape, dtype=bool)
    return grid.land if cls == "land" else ~grid.land


def transformed_value(value: float, transform: str) -> float:
    if transform == "negate":
        return -value
    if transform == "log10":
        return math.log10(value) if value > 0 else float("nan")
    return value


def apply_value(grid: SourceGrid, no_data: Optional[NoData], cls: str, transform: str = "none") -> SourceGrid:
    """Record missing class pixels in ``grid.missing`` and fill them with ``no_data.value``."""
    if grid.on_kit_grid:
        return grid
    cp = class_pixels(grid, cls)
    grid.missing = cp & ~np.isfinite(grid.values)
    if no_data is not None and no_data.value is not None:
        grid.values = np.where(grid.missing, transformed_value(no_data.value, transform), grid.values)
    return grid


def cell_latitudes(projection: KitProjection) -> np.ndarray:
    """|latitude| of each kit cell centre (80 x 128); on a template, of each stud's location (NaN
    on margin studs, which belong to no layer)."""
    if _is_template(projection):
        return projection.abs_lat()
    lat = np.array([abs(projection.cell_center(r, 0)[0]) for r in range(projection.height)])
    return np.repeat(lat[:, None], projection.width, axis=1)


def cell_max(grid: SourceGrid, values: np.ndarray, where: np.ndarray, projection: KitProjection) -> np.ndarray:
    """Per kit cell, the largest of ``values`` over the source pixels in ``where`` (0 if none)."""
    H, W = projection.height, projection.width
    if _is_template(projection):  # feature 016: pixels binned into studs by the forward formula
        cell = source_cells(grid, projection)
        ok = (cell >= 0) & where
        out = np.zeros(H * W)
        np.maximum.at(out, cell[ok], values[ok].astype(float))
        return out.reshape(H, W)
    rows = projection.rows_for_lat(grid.lat)
    cols = projection.cols_for_lon(grid.lon)
    cell = rows[:, None] * W + cols[None, :]
    ok = (rows[:, None] >= 0) & where
    out = np.zeros(H * W)
    np.maximum.at(out, cell[ok], values[ok].astype(float))
    return out.reshape(H, W)


def no_data_cells(no_data: Optional[NoData], grid: SourceGrid, fld: LayerField, mask: np.ndarray,
                  projection: KitProjection, cls: str) -> np.ndarray:
    """Kit cells (in ``mask``) that take ``no_data.color``; all False without a rule."""
    mask = np.asarray(mask, dtype=bool)
    if no_data is None or grid.on_kit_grid:
        return np.zeros(mask.shape, dtype=bool)
    lats = cell_latitudes(projection)
    if no_data.rule == "unobserved":
        out = mask & fld.filled & (lats > no_data.min_lat)
        if no_data.sparse_lat is not None:
            if grid.counts is None:
                raise ValueError("no_data.min_steps needs valid-step counts (reduce = climatology-mean)")
            best = cell_max(grid, grid.counts, class_pixels(grid, cls), projection)
            out |= mask & (lats > no_data.sparse_lat) & (best < no_data.min_steps)
        return out
    # share: indicator of "had no value and lies poleward of min_lat" over the class pixels
    missing = grid.missing if grid.missing is not None else class_pixels(grid, cls) & ~np.isfinite(grid.values)
    polar = (np.abs(grid.lat) > no_data.min_lat)[:, None]
    cp = class_pixels(grid, cls)
    ind = np.where(cp, (missing & polar).astype(float), np.nan)
    share = reproject_layer(SourceGrid(values=ind, lat=grid.lat, lon=grid.lon, land=grid.land),
                            projection, mask, cls)
    return mask & (share.values > no_data.min_share)

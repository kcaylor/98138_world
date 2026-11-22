"""Reprojection of a source grid onto the kit grid, one layer class at a time (FR-014).

Each kit cell's value is the plain mean of the valid source values of the layer's own class whose
centers fall in the cell (no area weighting; spec Clarifications). Cells with no such value take
the value of the nearest valid cell and are flagged. For categorical data the most frequent
category is used instead of the mean. Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from ..datasets.grid import SourceGrid
from .projection import KitProjection


@dataclass
class LayerField:
    values: np.ndarray          # 80x128, NaN outside the layer
    samples: np.ndarray         # source values per cell
    filled: np.ndarray          # cells filled from the nearest valid cell
    variance_lost: Optional[float] = None  # mean within-cell variance / total variance
    total_variance: Optional[float] = None

    @property
    def filled_count(self) -> int:
        return int(self.filled.sum())


def _nearest_fill(values: np.ndarray, have: np.ndarray, mask: np.ndarray) -> np.ndarray:
    from scipy import ndimage

    if not have.any():
        raise ValueError("the layer has no source values at all")
    _, (ri, ci) = ndimage.distance_transform_edt(~have, return_indices=True)
    out = values.copy()
    need = mask & ~have
    out[need] = values[ri[need], ci[need]]
    return out


def reproject_layer(grid: SourceGrid, projection: KitProjection, mask: np.ndarray, cls: str,
                    categorical: bool = False) -> LayerField:
    """Values for the kit cells in ``mask`` (the layer's cells) from ``grid``."""
    mask = np.asarray(mask, dtype=bool)
    H, W = projection.height, projection.width
    if grid.on_kit_grid:
        v = np.where(mask, grid.values, np.nan)
        return LayerField(values=v, samples=mask.astype(int), filled=np.zeros((H, W), bool))
    rows = projection.rows_for_lat(grid.lat)
    cols = projection.cols_for_lon(grid.lon)
    cell = rows[:, None] * W + cols[None, :]
    ok = (rows[:, None] >= 0) & np.isfinite(grid.values)
    if grid.land is not None:
        ok &= grid.land if cls == "land" else ~grid.land
    c = cell[ok]
    x = grid.values[ok]
    inside = mask.ravel()[c]
    c, x = c[inside], x[inside]
    n = np.bincount(c, minlength=H * W).astype(float)
    have = (n > 0).reshape(H, W)
    if categorical:
        cats, inv = np.unique(x, return_inverse=True)
        tab = np.zeros((H * W, len(cats)))
        np.add.at(tab, (c, inv), 1)
        mode = np.where(n > 0, cats[np.argmax(tab, axis=1)] if len(cats) else np.nan, np.nan)
        values = mode.reshape(H, W)
        var_lost = total = None
    else:
        s = np.bincount(c, weights=x, minlength=H * W)
        with np.errstate(invalid="ignore", divide="ignore"):
            mean = s / n
        values = mean.reshape(H, W)
        if x.size > 1:
            dev = x - mean[c]
            within = float((dev * dev).sum() / x.size)
            total = float(x.var())
            var_lost = within / total if total > 0 else 0.0
        else:
            var_lost = total = None
    values = np.where(mask, values, np.nan)
    filled = mask & ~have
    if filled.any():
        values = _nearest_fill(values, have & mask, mask)
    return LayerField(values=np.where(mask, values, np.nan), samples=n.reshape(H, W).astype(int),
                      filled=filled, variance_lost=var_lost, total_variance=total)

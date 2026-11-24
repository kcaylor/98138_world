"""Reprojection of a source grid onto the kit grid, one layer class at a time (FR-014).

Each kit cell's value is the plain mean of the valid source values of the layer's own class whose
centers fall in the cell (no area weighting; spec Clarifications). Cells with no such value take
the value of the nearest valid cell and are flagged. For categorical data the most frequent
category is used instead of the mean.

Feature 013: ``sampling = "bilinear"`` interpolates a regular grid at each kit cell centre instead
(periodic in longitude, latitude clamped to the outermost rows); points grids (one latitude and
longitude per value) are binned like pixels.

Feature 016 (research R6): on a non-kit template the projection is a
``templates.geometry.TemplateProjection`` and ``source_cells`` bins each source location into the
stud that contains it by the template's forward formula, in chunks of ``TEMPLATE_CHUNK`` points;
locations off the board or on a margin stud are dropped (-1). ``cell_centres`` are the template's
stored stud locations (NaN on margin studs, which ``bilinear`` skips). Everything after the
lookup is shared with the kit, whose branch is unchanged. Not affiliated with or endorsed by The
LEGO Group.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from ..datasets.grid import SourceGrid
from ..templates.geometry import TemplateProjection
from .projection import KitProjection

TEMPLATE_CHUNK = 1_000_000  # feature 016: points per forward-projection step (bounds memory)


def _is_template(projection) -> bool:
    """A non-kit template's stud lookup (feature 016); the kit's is a ``KitProjection``."""
    return isinstance(projection, TemplateProjection)


def template_source_cells(grid: SourceGrid, projection: TemplateProjection) -> np.ndarray:
    """Flat stud index of every source value on a template (shape of ``grid.values``); -1 off the
    board, at an invalid location or on a margin stud. At most ``TEMPLATE_CHUNK`` locations are
    projected at a time (a row of a regular grid is never split)."""
    chunk = max(1, int(TEMPLATE_CHUNK))
    lat = np.asarray(grid.lat, dtype=float)
    lon = np.asarray(grid.lon, dtype=float)
    if grid.points:
        flat_lat, flat_lon = lat.ravel(), lon.ravel()
        out = np.empty(flat_lat.size, dtype=np.int64)
        for i in range(0, flat_lat.size, chunk):
            out[i:i + chunk] = projection.cells_for(flat_lat[i:i + chunk], flat_lon[i:i + chunk])
        return out.reshape(lat.shape)
    out = np.empty((lat.size, lon.size), dtype=np.int64)
    rows = max(1, chunk // max(lon.size, 1))
    for i in range(0, lat.size, rows):
        out[i:i + rows] = projection.cells_for(lat[i:i + rows, None], lon[None, :])
    return out


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


def source_cells(grid: SourceGrid, projection: KitProjection) -> np.ndarray:
    """Flat kit-cell index of every source value (shape of ``grid.values``); -1 outside the grid.
    On a template (feature 016): ``template_source_cells``."""
    if _is_template(projection):
        return template_source_cells(grid, projection)
    W = projection.width
    rows = projection.rows_for_lat(grid.lat)
    cols = projection.cols_for_lon(grid.lon)
    if grid.points:
        return np.where(rows >= 0, rows * W + cols, -1)
    return np.where(rows[:, None] >= 0, rows[:, None] * W + cols[None, :], -1)


def class_ok(grid: SourceGrid, cls: Optional[str]) -> np.ndarray:
    """Finite source values of the layer's class (all classes when the source does not say)."""
    ok = np.isfinite(grid.values)
    if grid.land is not None and cls is not None:
        ok &= grid.land if cls == "land" else ~grid.land
    return ok


def cell_means(grid: SourceGrid, projection: KitProjection, cls: Optional[str] = None):
    """``(mean, n)`` per kit cell (80 x 128) of the valid source values of ``cls``; ``mean`` is NaN
    where ``n == 0`` (feature 013: dataset overrides)."""
    H, W = projection.height, projection.width
    cell = source_cells(grid, projection)
    ok = (cell >= 0) & class_ok(grid, cls)
    c, x = cell[ok], grid.values[ok]
    n = np.bincount(c, minlength=H * W).astype(float)
    s = np.bincount(c, weights=x, minlength=H * W)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(n > 0, s / np.maximum(n, 1), np.nan)
    return mean.reshape(H, W), n.reshape(H, W).astype(int)


def cell_centres(projection: KitProjection):
    """Latitude and longitude (-180..180) of every kit cell centre (80 x 128). On a template
    (feature 016): the stored stud locations, NaN on margin studs."""
    if _is_template(projection):
        return projection.locations()
    H, W = projection.height, projection.width
    lat = np.array([projection.cell_center(r, 0)[0] for r in range(H)])
    lon = np.array([projection.cell_center(0, c)[1] for c in range(W)])
    return np.repeat(lat[:, None], W, axis=1), np.repeat(lon[None, :], H, axis=0)


def _even(axis: np.ndarray) -> Optional[float]:
    d = np.diff(axis)
    if d.size == 0 or not np.all(d > 0):
        return None
    step = float(np.mean(d))
    return step if np.allclose(d, step, rtol=1e-4, atol=1e-6) else None


def bilinear(grid: SourceGrid, projection: KitProjection, cls: Optional[str] = None):
    """``(values, have)``: bilinear interpolation at each kit cell centre (feature 013, research R6).

    Rows: ``fy = (lat - lat[0]) / dlat`` clamped to the outermost rows; columns periodic in
    longitude. Corners without a valid value of the layer's class are dropped and the remaining
    weights renormalised; ``have`` is False where no corner has a value."""
    if grid.points or grid.on_kit_grid:
        raise ValueError("bilinear sampling needs a regular latitude/longitude grid")
    lat, lon = np.asarray(grid.lat, dtype=float), np.asarray(grid.lon, dtype=float)
    dlat, dlon = _even(lat), _even(lon)
    if dlat is None or dlon is None or lat.size < 2:
        raise ValueError("bilinear sampling needs evenly spaced latitudes and longitudes")
    if abs(dlon * lon.size - 360.0) > 1e-6 * 360:
        raise ValueError("bilinear sampling needs a global longitude axis (periodic)")
    clat, clon = cell_centres(projection)
    on = np.isfinite(clat) & np.isfinite(clon)  # feature 016: a template's margin studs are skipped
    if not on.all():
        clat, clon = np.where(on, clat, 0.0), np.where(on, clon, 0.0)
    ny, nx = lat.size, lon.size
    fy = np.clip((clat - lat[0]) / dlat, 0, ny - 1)
    y0 = np.clip(np.floor(fy).astype(int), 0, ny - 2)
    ty = fy - y0
    fx = (clon - lon[0]) / dlon
    x0 = np.floor(fx).astype(int)
    tx = fx - x0
    x0m, x1m = x0 % nx, (x0 + 1) % nx
    ok = class_ok(grid, cls)
    v = np.where(ok, grid.values, 0.0)
    total = np.zeros(clat.shape)
    weight = np.zeros(clat.shape)
    for yy, xx, w in ((y0, x0m, (1 - ty) * (1 - tx)), (y0, x1m, (1 - ty) * tx),
                      (y0 + 1, x0m, ty * (1 - tx)), (y0 + 1, x1m, ty * tx)):
        good = ok[yy, xx]
        total += np.where(good, w * v[yy, xx], 0.0)
        weight += np.where(good, w, 0.0)
    have = (weight > 0) & on
    with np.errstate(invalid="ignore", divide="ignore"):
        values = np.where(have, total / np.where(have, weight, 1.0), np.nan)
    return values, have


def reproject_layer(grid: SourceGrid, projection: KitProjection, mask: np.ndarray, cls: str,
                    categorical: bool = False, sampling: str = "mean") -> LayerField:
    """Values for the kit cells in ``mask`` (the layer's cells) from ``grid``. On a template
    (feature 016) ``mask`` holds on-globe studs only, so margin studs never take data."""
    mask = np.asarray(mask, dtype=bool)
    H, W = projection.height, projection.width
    if grid.on_kit_grid and _is_template(projection):
        raise ValueError("the source is already on the kit grid (the official design); it cannot be "
                         "sampled on another template")
    if grid.on_kit_grid:
        v = np.where(mask, grid.values, np.nan)
        return LayerField(values=v, samples=mask.astype(int), filled=np.zeros((H, W), bool))
    cell = source_cells(grid, projection)
    ok = (cell >= 0) & class_ok(grid, cls)
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
    if sampling == "bilinear":  # feature 013: same samples and variance, interpolated values
        if categorical:
            raise ValueError("bilinear sampling needs ordered (not categorical) data")
        values, have = bilinear(grid, projection, cls)
    elif sampling != "mean":
        raise ValueError(f"unknown sampling {sampling!r}")
    values = np.where(mask, values, np.nan)
    filled = mask & ~have
    if filled.any():
        values = _nearest_fill(values, have & mask, mask)
    return LayerField(values=np.where(mask, values, np.nan), samples=n.reshape(H, W).astype(int),
                      filled=filled, variance_lost=var_lost, total_variance=total)

"""Fit the kit grid's projection to the kit's land/sea mask (feature 004, research R2).

Land fraction of an elevation grid (land = z > 0) is binned into kit cells; a cell is predicted
land when the fraction is >= 0.5 and compared with the kit mask. The left-edge longitude is
fitted from the column profile of land (correlation), then per model the equator row and the
scale (rows per unit of the model's y) by a coarse-to-fine grid search (step 0.5, then 0.1).
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np

WIDTH, HEIGHT = 128, 80
MODELS = {
    "equirectangular": lambda phi: np.radians(phi),
    "miller": lambda phi: 1.25 * np.log(np.tan(np.pi / 4 + 0.4 * np.radians(phi))),
    "mercator": lambda phi: np.log(np.tan(np.pi / 4 + np.radians(np.clip(phi, -85, 85)) / 2)),
}


def column_index(lon: np.ndarray, lon0: float) -> np.ndarray:
    return np.floor(((lon - lon0) % 360.0) / (360.0 / WIDTH)).astype(int).clip(0, WIDTH - 1)


def land_by_column(land: np.ndarray, lon: np.ndarray, lon0: float) -> np.ndarray:
    """(nlat, 128) land fraction of each latitude row within each kit column."""
    col = column_index(lon, lon0)
    counts = np.bincount(col, minlength=WIDTH).astype(float)
    sums = np.zeros((land.shape[0], WIDTH))
    for j in range(WIDTH):
        sel = col == j
        if sel.any():
            sums[:, j] = land[:, sel].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return sums / counts[None, :]


def fit_left_edge(land, lat, lon, kit, lons=np.arange(-180.0, -150.0, 0.1)) -> Tuple[float, float]:
    band = (lat > -60) & (lat < 75)
    prof_data = land[band].mean(axis=0)
    prof_kit = kit[5:66].mean(axis=0)
    best = (-2.0, None)
    for lon0 in lons:
        col = column_index(lon, lon0)
        p = np.bincount(col, prof_data, WIDTH) / np.maximum(np.bincount(col, minlength=WIDTH), 1)
        r = float(np.corrcoef(p, prof_kit)[0, 1])
        if r > best[0] + 1e-12:
            best = (r, round(float(lon0), 2))
    return best[1], best[0]


def _agreement(L, P, kit, y0, s):
    row = np.floor(y0 - s * P).astype(int)
    ok = np.flatnonzero((row >= 0) & (row < HEIGHT))
    if ok.size == 0:
        return -1.0
    r = row[ok]
    order = np.argsort(r, kind="stable")
    r, idx = r[order], ok[order]
    starts = np.flatnonzero(np.r_[True, np.diff(r) != 0])
    if len(starts) != HEIGHT:
        return -1.0  # some kit row gets no data
    sums = np.add.reduceat(np.nan_to_num(L[idx]), starts, axis=0)
    n = np.diff(np.r_[starts, len(r)])
    frac = sums / n[:, None]
    return float(((frac >= 0.5 - 1e-9) == kit[r[starts]]).mean())  # tolerance: summation order


def fit_rows(L, lat, kit, model: str, y0_range=(36.0, 48.0), s_range=(14.0, 34.0)) -> Tuple[float, float, float]:
    P = MODELS[model](lat)
    best = (-1.0, None, None)
    for y0 in np.arange(y0_range[0], y0_range[1] + 1e-9, 0.5):
        for s in np.arange(s_range[0], s_range[1] + 1e-9, 0.5):
            a = _agreement(L, P, kit, y0, s)
            if a > best[0]:
                best = (a, y0, s)
    a0, y0c, sc = best
    for y0 in np.arange(y0c - 0.5, y0c + 0.5 + 1e-9, 0.1):
        for s in np.arange(sc - 0.5, sc + 0.5 + 1e-9, 0.1):
            a = _agreement(L, P, kit, y0, s)
            if a > best[0] + 1e-12:
                best = (a, y0, s)
    a, y0, s = best
    return round(a, 3), round(float(y0), 1), round(float(s), 1)


def fit(z: np.ndarray, lat: np.ndarray, lon: np.ndarray, kit: np.ndarray, *,
        lons=np.arange(-180.0, -150.0, 0.1), y0_range=(36.0, 48.0), s_range=(14.0, 34.0)) -> Dict:
    """Fit every model; ``kit`` is the 80x128 boolean land mask. Returns the projection fields."""
    land = np.where(np.isfinite(z), z > 0, False).astype(float)
    lon0, r = fit_left_edge(land, lat, lon, kit, lons)
    L = land_by_column(land, lon, lon0)
    results = {m: fit_rows(L, lat, kit, m, y0_range, s_range) for m in MODELS}
    a, y0, s = results["equirectangular"]
    return {"model": "equirectangular", "width": WIDTH, "height": HEIGHT, "left_edge_lon": lon0,
            "deg_per_col": 360.0 / WIDTH, "equator_row": y0, "rows_per_radian": s,
            "agreement": {m: v[0] for m, v in results.items()},
            "fits": {m: {"equator_row": v[1], "scale": v[2], "agreement": v[0]} for m, v in results.items()},
            "column_correlation": round(r, 3)}

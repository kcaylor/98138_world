"""Rasterise a projection onto a board of studs and classify each stud.

Each stud is supersampled ``ss × ss``. Every subsample is inverse-projected to (lat, lon) and kept
only if a forward round trip returns to the same point (this rejects points outside the
projection's outline, where many inverses still return a value). A stud is on the globe when at
least half of its subsamples are; an on-globe stud is land when at least half of its on-globe
subsamples have elevation > 0, otherwise ocean. Everything else is margin (off the globe).

pyproj is imported only when a projected (non-kit) board is rasterised, so the pure helpers here
can be tested without it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

from lego_image_processor.maps.projection import PROJECTION_PATH
# Board helpers moved to the package in feature 016 (templates/board.py); re-exported here.
from lego_image_processor.templates.board import MODULE, largest_rectangle, module_stats, rim_cells  # noqa: F401

EARTH_RADIUS_KM = 6371.0


def kit_projection() -> dict:
    return json.loads(PROJECTION_PATH.read_text(encoding="utf-8"))


def kit_centre_lon(kit: Optional[dict] = None) -> float:
    """The kit's central meridian as hung in combination A (11.1° E)."""
    kit = kit or kit_projection()
    return round(kit["left_edge_lon"] + 180.0, 6)


class Elevation:
    """Nearest-neighbour lookup into a regular lat/lon grid (ETOPO 2022, 10′)."""

    def __init__(self, values: np.ndarray, lat: np.ndarray, lon: np.ndarray):
        self.z, self.lat, self.lon = values, lat, lon
        self.dlat, self.dlon = lat[1] - lat[0], lon[1] - lon[0]

    def at(self, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
        i = np.clip(np.rint((lat - self.lat[0]) / self.dlat).astype(int), 0, len(self.lat) - 1)
        j = np.rint((((lon + 180) % 360) - 180 - self.lon[0]) / self.dlon).astype(int) % len(self.lon)
        return self.z[i, j]


class Proj:
    """A projection on the unit sphere, with a round-trip-checked inverse.

    ``spec`` is a PROJ string without ``+R``; ``None`` means the kit's own fitted grid.
    ``clip`` optionally limits latitudes (south, north), for cylindrical projections that would
    otherwise run to the poles or to infinity.
    """

    def __init__(self, name: str, spec: Optional[str], family: str, clip: Optional[Tuple[float, float]] = None):
        self.name, self.spec, self.family, self.clip = name, spec, family, clip
        if spec:
            from pyproj import Transformer

            self.fwd = Transformer.from_crs("+proj=longlat +R=1 +no_defs", spec + " +R=1", always_xy=True)
        self.extent = self._extent()

    def forward(self, lon, lat):
        x, y = self.fwd.transform(lon, lat, errcheck=False)
        return np.asarray(x), np.asarray(y)

    def inverse(self, x, y):
        lon, lat = self.fwd.transform(x, y, direction="INVERSE", errcheck=False)
        lon, lat = np.asarray(lon), np.asarray(lat)
        ok = np.isfinite(lon) & np.isfinite(lat)
        x2, y2 = self.forward(np.where(ok, lon, 0), np.where(ok, lat, 0))
        scale = max(self.extent[1] - self.extent[0], self.extent[3] - self.extent[2])
        with np.errstate(invalid="ignore"):
            ok &= (np.abs(x2 - x) < 1e-6 * scale) & (np.abs(y2 - y) < 1e-6 * scale)
            if self.clip:
                ok &= (lat >= self.clip[0]) & (lat <= self.clip[1])
        return lat, lon, ok

    def _extent(self):
        if not self.spec:
            return (0.0, 128.0, 0.0, 80.0)
        lat = np.linspace(-90, 90, 721)
        lon = np.linspace(-180, 180, 1441)
        lo, la = np.meshgrid(lon, lat)
        if self.clip:
            la = np.clip(la, *self.clip)
        x, y = self.forward(lo.ravel(), la.ravel())
        f = np.isfinite(x) & np.isfinite(y) & (np.abs(x) < 1e3) & (np.abs(y) < 1e3)
        return (x[f].min(), x[f].max(), y[f].min(), y[f].max())

    @property
    def aspect(self) -> float:
        x0, x1, y0, y1 = self.extent
        return (x1 - x0) / (y1 - y0)


@dataclass
class Raster:
    cover: np.ndarray      # share of subsamples on the globe, per stud
    landfrac: np.ndarray   # share of on-globe subsamples with z > 0
    depth: np.ndarray      # mean z of on-globe ocean subsamples (m, <= 0)
    area_km2: np.ndarray   # ground area represented by each stud (NaN off the globe)
    scale: Optional[float]  # board studs per projected unit (None for the kit grid)


def _kit_inverse(kit: dict, xs, ys):
    lat = np.degrees((kit["equator_row"] - ys) / kit["rows_per_radian"])
    lon = kit["left_edge_lon"] + xs * kit["deg_per_col"]
    ok = (lat <= 90) & (lat >= -90)
    return lat, lon, ok


def rasterise(p: Proj, elev: Elevation, W: int, H: int, ss: int = 4, fit: str = "contain",
              kit: Optional[dict] = None) -> Raster:
    off = (np.arange(ss) + 0.5) / ss
    cols = (np.arange(W)[:, None] + off[None, :]).ravel()
    rows = (np.arange(H)[:, None] + off[None, :]).ravel()
    s = None
    if p.spec is None:
        kit = kit or kit_projection()
        if (W, H) != (128, 80):
            raise ValueError("the kit grid is 128×80")
        xs, ys = np.meshgrid(cols, rows)
        lat, lon, ok = _kit_inverse(kit, xs, ys)
    else:
        x0, x1, y0, y1 = p.extent
        pick = min if fit == "contain" else max
        s = pick(W / (x1 - x0), H / (y1 - y0))
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        xs, ys = np.meshgrid((cols - W / 2) / s + cx, (H / 2 - rows) / s + cy)
        lat, lon, ok = p.inverse(xs.ravel(), ys.ravel())
        lat, lon, ok = lat.reshape(xs.shape), lon.reshape(xs.shape), ok.reshape(xs.shape)
    z = np.where(ok, elev.at(np.where(ok, lat, 0), np.where(ok, lon, 0)), np.nan)

    def block(a):
        return a.reshape(H, ss, W, ss).swapaxes(1, 2).reshape(H, W, ss * ss)

    okb, zb = block(ok), block(z)
    cover = okb.mean(axis=2)
    with np.errstate(invalid="ignore"):
        landfrac = np.nansum(zb > 0, axis=2) / np.maximum(okb.sum(axis=2), 1)
        depth = np.nanmean(np.where(zb <= 0, zb, np.nan), axis=2)

    if s is not None:
        # Ground area per stud from the numerical Jacobian of the inverse at the stud centre.
        cc, rr = np.arange(W) + 0.5, np.arange(H) + 0.5
        CX, RY = np.meshgrid((cc - W / 2) / s + cx, (H / 2 - rr) / s + cy)
        e = 0.05 / s
        la, lo, k0 = p.inverse(CX.ravel(), RY.ravel())
        la1, lo1, k1 = p.inverse(CX.ravel() + e, RY.ravel())
        la2, lo2, k2 = p.inverse(CX.ravel(), RY.ravel() + e)
        dlo1 = ((lo1 - lo + 540) % 360) - 180
        dlo2 = ((lo2 - lo + 540) % 360) - 180
        c = np.cos(np.radians(la))
        jac = np.abs(np.radians(dlo1) * c * np.radians(la2 - la)
                     - np.radians(dlo2) * c * np.radians(la1 - la)) / (e * s) ** 2
        area = np.where(k0 & k1 & k2, jac * EARTH_RADIUS_KM ** 2, np.nan).reshape(H, W)
    else:
        rr = np.arange(H) + 0.5
        la = np.degrees((kit["equator_row"] - rr) / kit["rows_per_radian"])
        km2 = (np.radians(kit["deg_per_col"]) * np.cos(np.radians(la)) / kit["rows_per_radian"]
               * EARTH_RADIUS_KM ** 2)
        area = np.repeat(km2[:, None], W, axis=1)
        area[np.abs(la) > 90] = np.nan
    return Raster(cover, landfrac, depth, area, s)


def classify(cover: np.ndarray, landfrac: np.ndarray, threshold: float = 0.5):
    """Return (on_globe, land, ocean) boolean arrays."""
    on = cover >= threshold
    land = on & (landfrac >= threshold)
    return on, land, on & ~land

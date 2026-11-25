"""Forward Winkel tripel on the unit sphere, in numpy (research R1).

Winkel tripel is the mean of the equirectangular projection with standard parallel φ1 and Aitoff's
projection (Winkel 1921; Snyder 1993, *Flattening the Earth*; PROJ ``wintri``). With
λ the longitude from the central meridian λ0 and α = arccos(cos φ cos(λ/2)):

    x = ½ (λ cos φ1 + 2 cos φ sin(λ/2) · α / sin α)
    y = ½ (φ + sin φ · α / sin α)

Longitudes are wrapped and latitudes checked as PROJ does (``adjlon`` with a 1e-12 overshoot;
latitudes beyond ±90° by more than 1e-12 are invalid and give NaN). The forward step needs no
pyproj: the run time bins data into studs with it. The inverse has no closed form; the maintainer
tool computes stud locations with pyproj and the template file stores them, with 24 check points
that the loader recomputes here (|Δ| < 1e-9).

The extent is exact: x = ±(π/2)(1 + cos φ1), y = ±π/2 (research R2). The outline is the image of
the edge meridian λ = ±π: x = ±(π/2)(cos φ + cos φ1), y = ½((π/2) sin φ + φ); the poles are lines
|x| ≤ (π/2) cos φ1. Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np

NAME = "winkel-tripel"
LAT_1 = 50.4598   # degrees; arccos(2/π), Winkel's own choice (PROJ's default is 0)
LON_0 = 11.1      # degrees east; the centre of the kit board as hung in combination A
CHUNK = 1_000_000  # points per vectorised step (bounds memory for 1080 x 2160 source grids)
CITATION = ("Winkel, O. (1921), Neue Gradnetzkombinationen, Petermanns Geographische Mitteilungen 67; "
            "Snyder, J. P. (1993), Flattening the Earth: Two Thousand Years of Map Projections, "
            "University of Chicago Press, pp. 231-232; PROJ, Winkel Tripel (wintri), "
            "https://proj.org/en/stable/operations/projections/wintri.html")

_EPS_LON = 1e-12  # PROJ adjlon: longitudes within pi + 1e-12 are left alone
_EPS_LAT = 1e-12  # PROJ: latitudes beyond pi/2 by more than this are an error

# The 24 (lon, lat) check points a template file records with pyproj's x, y (contracts/
# template-file.md): the centre, the antimeridian edge, the poles, the standard parallels, and a
# spread of places on every continent and both sides of the antimeridian.
CHECK_POINTS: Tuple[Tuple[float, float], ...] = (
    (11.1, 0.0), (-168.9, 0.0), (-168.9, 45.0), (-168.9, -45.0), (-168.9, 90.0), (-168.9, -90.0),
    (11.1, 90.0), (11.1, -90.0), (11.1, 50.4598), (11.1, -50.4598),
    (0.0, 51.5), (-74.0, 40.7), (151.2, -33.9), (18.4, -33.9), (139.7, 35.7), (-58.4, -34.6),
    (37.6, 55.8), (-150.0, 61.2), (100.0, -89.0), (-45.0, 89.5), (179.9, 10.0), (-179.9, -10.0),
    (-170.0, 70.0), (-100.0, -75.0),
)


def proj_string(lat_1: float = LAT_1, lon_0: float = LON_0) -> str:
    """The PROJ definition, e.g. ``+proj=wintri +lat_1=50.4598 +lon_0=11.1 +R=1``."""
    return f"+proj=wintri +lat_1={lat_1:.10g} +lon_0={lon_0:.10g} +R=1"


def _adjlon(lam: np.ndarray) -> np.ndarray:
    w = lam + math.pi
    w = w - 2 * math.pi * np.floor(w / (2 * math.pi))
    return np.where(np.abs(lam) < math.pi + _EPS_LON, lam, w - math.pi)


def forward_radians(lam: np.ndarray, phi: np.ndarray, cosphi1: float) -> Tuple[np.ndarray, np.ndarray]:
    """The formula itself: λ from the central meridian and φ in radians, no wrapping or checks."""
    c = 0.5 * lam
    cphi = np.cos(phi)
    d = np.arccos(np.clip(cphi * np.cos(c), -1.0, 1.0))
    sd = np.sin(d)
    with np.errstate(invalid="ignore", divide="ignore"):
        k = np.where(d != 0.0, d / np.where(d != 0.0, sd, 1.0), 1.0)
    x = 0.5 * (2.0 * k * cphi * np.sin(c) + lam * cosphi1)
    y = 0.5 * (k * np.sin(phi) + phi)
    return x, y


def forward(lon, lat, lat_1: float = LAT_1, lon_0: float = LON_0) -> Tuple[np.ndarray, np.ndarray]:
    """Projected (x, y) on the unit sphere of longitudes and latitudes in degrees (broadcast,
    vectorised in chunks of ``CHUNK`` points). Invalid input (|lat| > 90°, not finite) gives NaN."""
    lon, lat = np.broadcast_arrays(np.asarray(lon, dtype=float), np.asarray(lat, dtype=float))
    shape = lon.shape
    lon, lat = lon.ravel(), lat.ravel()
    x = np.empty(lon.size)
    y = np.empty(lon.size)
    cosphi1 = math.cos(math.radians(lat_1))
    lam0 = math.radians(lon_0)
    for i in range(0, lon.size, CHUNK):
        lo, la = lon[i:i + CHUNK], lat[i:i + CHUNK]
        phi = np.radians(la)
        with np.errstate(invalid="ignore"):
            bad = ~(np.isfinite(lo) & np.isfinite(phi)) | (np.abs(phi) - math.pi / 2 > _EPS_LAT)
        phi = np.clip(np.where(bad, 0.0, phi), -math.pi / 2, math.pi / 2)
        lam = _adjlon(np.where(bad, 0.0, np.radians(lo)) - lam0)
        xx, yy = forward_radians(lam, phi, cosphi1)
        x[i:i + CHUNK] = np.where(bad, np.nan, xx)
        y[i:i + CHUNK] = np.where(bad, np.nan, yy)
    return x.reshape(shape), y.reshape(shape)


def extent(lat_1: float = LAT_1) -> Tuple[float, float, float, float]:
    """The exact extent (x0, x1, y0, y1): x = ±(π/2)(1 + cos φ1), y = ±π/2."""
    half = (math.pi / 2) * (1.0 + math.cos(math.radians(lat_1)))
    return (-half, half, -math.pi / 2, math.pi / 2)


def fit(width: int, height: int, lat_1: float = LAT_1, mode: str = "contain") -> Dict[str, object]:
    """The board fit (``projection.fit``): the exact extent scaled to fit inside the board
    (``contain``), in studs per projected unit, centred."""
    if mode != "contain":
        raise ValueError(f"fit mode must be 'contain', not {mode!r}")
    x0, x1, y0, y1 = extent(lat_1)
    scale = min(width / (x1 - x0), height / (y1 - y0))
    return {"mode": "contain", "extent": [x0, x1, y0, y1], "scale": scale,
            "centre": [(x0 + x1) / 2, (y0 + y1) / 2]}


def edge_x(y, lat_1: float = LAT_1) -> np.ndarray:
    """Half-width of the outline at height ``y``: |x| of the edge meridian there (NaN beyond ±π/2)."""
    y = np.asarray(y, dtype=float)
    ay = np.abs(y)
    valid = ay <= math.pi / 2
    target = np.where(valid, ay, 0.0)
    phi = target.copy()
    for _ in range(50):  # Newton on y(φ) = ½((π/2) sin φ + φ), increasing on [0, π/2]
        step = (0.5 * ((math.pi / 2) * np.sin(phi) + phi) - target) / (0.5 * ((math.pi / 2) * np.cos(phi) + 1.0))
        phi = np.clip(phi - step, 0.0, math.pi / 2)
        if np.all(np.abs(step) < 1e-16):
            break
    half = (math.pi / 2) * (np.cos(phi) + math.cos(math.radians(lat_1)))
    return np.where(valid, half, np.nan)


def outline_contains(x, y, lat_1: float = LAT_1, tol: float = 0.0) -> np.ndarray:
    """Whether points (x, y) lie inside the projection's outline (boundary included, within
    ``tol``)."""
    x, y = np.broadcast_arrays(np.asarray(x, dtype=float), np.asarray(y, dtype=float))
    with np.errstate(invalid="ignore"):
        inside_y = np.abs(y) <= math.pi / 2 + tol
        half = edge_x(np.clip(y, -math.pi / 2, math.pi / 2), lat_1)
        return inside_y & (np.abs(x) <= half + tol)


def check_points(lat_1: float = LAT_1, lon_0: float = LON_0) -> List[List[float]]:
    """``[[lon, lat, x, y], …]`` for ``CHECK_POINTS`` from this formula (the maintainer tool
    records pyproj's x, y; the loader compares them with these)."""
    lon = np.array([p[0] for p in CHECK_POINTS])
    lat = np.array([p[1] for p in CHECK_POINTS])
    x, y = forward(lon, lat, lat_1, lon_0)
    return [[float(a), float(b), float(c), float(d)] for a, b, c, d in zip(lon, lat, x, y)]

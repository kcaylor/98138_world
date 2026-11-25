"""Stud geometry of a non-kit template (data-model.md TemplateProjection.cells_for, .locations,
.abs_lat; research R6).

A template's projection maps a location to projected (x, y) with its forward formula
(``templates/winkel.py``); the fit (``projection.fit``: extent, studs per unit ``scale``, centre)
places that on the board::

    col_x = (x - centre_x) * scale + width / 2
    row_y = height / 2 - (y - centre_y) * scale

and the stud is ``(floor(row_y), floor(col_x))``. Values within 1e-9 of the board's edges are
counted on the edge stud. Margin studs never take data, so ``cells_for`` gives -1 on them as off
the board. Stud locations are the ones the template file stores (no inverse at run time).

``TemplateProjection`` offers what ``maps/projection.py`` ``KitProjection`` offers to the map
code: ``height``, ``width``, the stud of a location (``cells_for``) and stud locations.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from typing import Callable, Dict, Mapping, Tuple

import numpy as np

from . import winkel

EDGE_TOLERANCE = 1e-9

Forward = Callable[..., Tuple[np.ndarray, np.ndarray]]
FORWARD: Dict[str, Forward] = {winkel.NAME: winkel.forward}


def to_board(x, y, fit: Mapping, width: int, height: int) -> Tuple[np.ndarray, np.ndarray]:
    """Board coordinates (col_x, row_y), in studs from the top-left corner, of projected (x, y)."""
    cx, cy = fit["centre"]
    s = fit["scale"]
    return (np.asarray(x, dtype=float) - cx) * s + width / 2, height / 2 - (np.asarray(y, dtype=float) - cy) * s


def from_board(col_x, row_y, fit: Mapping, width: int, height: int) -> Tuple[np.ndarray, np.ndarray]:
    """Projected (x, y) of board coordinates (col_x, row_y); the inverse of ``to_board``."""
    cx, cy = fit["centre"]
    s = fit["scale"]
    return (np.asarray(col_x, dtype=float) - width / 2) / s + cx, (height / 2 - np.asarray(row_y, dtype=float)) / s + cy


def _index(v: np.ndarray, n: int) -> np.ndarray:
    """``floor(v)`` as an int index; within ``EDGE_TOLERANCE`` of 0 or ``n`` it stays on the
    board; elsewhere outside 0..n-1 (or not finite) it is -1."""
    with np.errstate(invalid="ignore"):
        ok = np.isfinite(v) & (v > -EDGE_TOLERANCE) & (v < n + EDGE_TOLERANCE)
        i = np.floor(np.where(ok, v, 0.0)).astype(int)
    i = np.clip(i, 0, n - 1)
    return np.where(ok, i, -1)


class TemplateProjection:
    """Stud lookups of a non-kit template: forward formula + fit + stored stud locations."""

    def __init__(self, *, name: str, lat_1: float, lon_0: float, fit: Mapping, width: int, height: int,
                 on_globe: np.ndarray, lat: np.ndarray, lon: np.ndarray):
        if name not in FORWARD:
            raise ValueError(f"no forward formula for projection {name!r}; known: {', '.join(FORWARD)}")
        self.name, self.lat_1, self.lon_0 = name, float(lat_1), float(lon_0)
        self.fit = {"mode": fit["mode"], "extent": list(fit["extent"]), "scale": float(fit["scale"]),
                    "centre": list(fit["centre"])}
        self.width, self.height = int(width), int(height)
        self._on = np.array(on_globe, dtype=bool)
        self._lat = np.where(self._on, np.asarray(lat, dtype=float), np.nan)
        self._lon = np.where(self._on, np.asarray(lon, dtype=float), np.nan)
        for a in (self._on, self._lat, self._lon):
            a.setflags(write=False)
        self._forward = FORWARD[name]

    def __repr__(self) -> str:
        return f"TemplateProjection({self.name!r}, {self.width}x{self.height})"

    def board_xy(self, lat, lon) -> Tuple[np.ndarray, np.ndarray]:
        """Board coordinates (col_x, row_y) of locations (degrees, broadcast); NaN where invalid."""
        x, y = self._forward(lon, lat, self.lat_1, self.lon_0)
        return to_board(x, y, self.fit, self.width, self.height)

    def cells_for(self, lat, lon) -> np.ndarray:
        """Flat stud index (row * width + col) of each location (broadcast shape); -1 off the
        board, for invalid locations, or on a margin stud."""
        col_x, row_y = self.board_xy(lat, lon)
        r, c = _index(row_y, self.height), _index(col_x, self.width)
        ok = (r >= 0) & (c >= 0)
        flat = np.where(ok, r * self.width + c, 0)
        ok &= self._on.ravel()[flat]
        return np.where(ok, flat, -1)

    def locations(self) -> Tuple[np.ndarray, np.ndarray]:
        """Latitude and longitude (degrees) of every stud (height x width); NaN on margin studs."""
        return self._lat.copy(), self._lon.copy()

    def abs_lat(self) -> np.ndarray:
        """|latitude| of every stud location (NaN on margin studs)."""
        return np.abs(self._lat)

    @property
    def on_globe(self) -> np.ndarray:
        return self._on

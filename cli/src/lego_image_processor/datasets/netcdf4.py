"""netCDF-4/HDF5 reader (feature 013, specs/013-rainfall/contracts/recipe-and-datasets.md).

Read with h5py, which returns stored values; CF decoding is done here: ``_FillValue``,
``missing_value``, ``valid_range``/``valid_min``/``valid_max`` (compared on stored values), the
netCDF default fill floor, then ``scale_factor`` and ``add_offset``. Leading axes of size 1 (e.g.
``time=1, lev=1`` in ERSST v5 per-month files) are dropped; ``annual-mean`` and
``climatology-mean`` work as for netCDF-3.

Coordinates: 1-D ``lat``/``latitude`` and ``lon``/``longitude`` (a regular grid, normalised like
the other readers), or 1-D projected ``x``/``y`` with a CF ``polar_stereographic`` grid mapping
(NSIDC sea ice), whose latitude and longitude are computed per pixel (Snyder 1987, ellipsoidal
inverse); the result is then a points grid.

Several files (a multi-file registry entry) are combined by ``read_netcdf4_files``: with
``climatology-mean`` each pixel is the mean of its valid values over the files on the same grid.

Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .grid import SourceGrid, normalise

_HDF5_SIGNATURE = b"\x89HDF\r\n\x1a\n"
_NETCDF3_SIGNATURES = (b"CDF\x01", b"CDF\x02")
_USER_BLOCK_OFFSETS = (0, 512, 1024, 2048)
_MISSING_FLOOR = -1e30
_LAT_NAMES = ("lat", "latitude")
_LON_NAMES = ("lon", "longitude")
REDUCES = ("annual-mean", "climatology-mean")


def check_netcdf4_signature(path) -> None:
    """An HDF5 file (netCDF-4); netCDF-3 files are named plainly (route by ``format``)."""
    with open(path, "rb") as fh:
        head = fh.read(2048 + 8)
    if head[:4] in _NETCDF3_SIGNATURES:
        raise ValueError(f"{path}: a netCDF-3 classic file, not netCDF-4/HDF5; declare format netcdf3")
    if not any(head[o:o + 8] == _HDF5_SIGNATURE for o in _USER_BLOCK_OFFSETS):
        raise ValueError(f"{path}: not a netCDF-4/HDF5 file")


def _attr(obj, name: str):
    v = obj.attrs.get(name)
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    if isinstance(v, np.ndarray) and v.dtype.kind in "SO" and v.size == 1:
        x = v.ravel()[0]
        return x.decode("utf-8", "replace") if isinstance(x, bytes) else x
    return v


def _number(obj, name: str) -> Optional[float]:
    v = obj.attrs.get(name)
    if v is None:
        return None
    a = np.asarray(v).ravel()
    if a.size == 0 or a.dtype.kind not in "biuf":
        return None
    return float(a[0])


def decode(raw: np.ndarray, var) -> np.ndarray:
    """Stored values -> physical values with NaN for missing (CF conventions)."""
    stored = np.asarray(raw)
    out = stored.astype(float)
    bad = ~np.isfinite(out)
    for name in ("_FillValue", "missing_value"):
        v = var.attrs.get(name)
        if v is None:
            continue
        for mv in np.asarray(v).ravel():
            try:
                mv = float(mv)
            except (TypeError, ValueError):
                continue
            if np.isfinite(mv):
                bad |= np.isclose(out, mv, rtol=1e-6, atol=0.0)
    vr = var.attrs.get("valid_range")
    lo = hi = None
    if vr is not None and np.asarray(vr).size == 2:
        lo, hi = (float(x) for x in np.asarray(vr).ravel())
    lo = _number(var, "valid_min") if _number(var, "valid_min") is not None else lo
    hi = _number(var, "valid_max") if _number(var, "valid_max") is not None else hi
    if lo is not None:
        bad |= out < lo
    if hi is not None:
        bad |= out > hi
    bad |= out < _MISSING_FLOOR
    out = np.where(bad, np.nan, out)
    scale, offset = _number(var, "scale_factor"), _number(var, "add_offset")
    if scale is not None:
        out = out * scale
    if offset is not None:
        out = out + offset
    return out


# ---------------------------------------------------------------- polar stereographic (CF)

def polar_stereographic_latlon(x: np.ndarray, y: np.ndarray, gm: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
    """Latitude and longitude (degrees, longitude in -180..180) of projected ``x``, ``y`` (metres)
    for a CF ``polar_stereographic`` grid mapping; ellipsoidal inverse after Snyder (1987),
    *Map Projections - A Working Manual*, USGS PP 1395, eqs. 21-38, 7-9, 3-5 (south aspect by
    sign reversal). ``gm`` holds the mapping's attributes."""
    def get(*names, default=None):
        for n in names:
            if gm.get(n) is not None:
                return float(np.asarray(gm[n]).ravel()[0])
        return default

    lat0 = get("latitude_of_projection_origin")
    if lat0 is None or abs(abs(lat0) - 90.0) > 1e-9:
        raise ValueError("polar_stereographic needs latitude_of_projection_origin = 90 or -90")
    a = get("semi_major_axis", "earth_radius")
    if a is None:
        raise ValueError("polar_stereographic needs semi_major_axis (or earth_radius)")
    invf = get("inverse_flattening")
    b = get("semi_minor_axis")
    if invf:
        f = 1.0 / invf
    elif b is not None:
        f = 1.0 - b / a
    else:
        f = 0.0
    e2 = 2 * f - f * f
    e = math.sqrt(e2)
    s = 1.0 if lat0 > 0 else -1.0
    lon0 = get("straight_vertical_longitude_from_pole", "longitude_of_projection_origin", default=0.0)
    fe, fn = get("false_easting", default=0.0), get("false_northing", default=0.0)
    xs = s * (np.asarray(x, dtype=float) - fe)
    ys = s * (np.asarray(y, dtype=float) - fn)
    rho = np.hypot(xs, ys)
    lat_ts = get("standard_parallel")
    if lat_ts is not None:
        phic = math.radians(s * lat_ts)
        if abs(phic - math.pi / 2) < 1e-12:
            k = 2 * a / math.sqrt((1 + e) ** (1 + e) * (1 - e) ** (1 - e))
        else:
            tc = math.tan(math.pi / 4 - phic / 2) / ((1 - e * math.sin(phic)) / (1 + e * math.sin(phic))) ** (e / 2)
            mc = math.cos(phic) / math.sqrt(1 - e2 * math.sin(phic) ** 2)
            k = a * mc / tc
    else:
        k0 = get("scale_factor_at_projection_origin", default=1.0)
        k = 2 * a * k0 / math.sqrt((1 + e) ** (1 + e) * (1 - e) ** (1 - e))
    t = rho / k
    chi = np.pi / 2 - 2 * np.arctan(t)
    phi = (chi + (e2 / 2 + 5 * e2 ** 2 / 24 + e2 ** 3 / 12 + 13 * e2 ** 4 / 360) * np.sin(2 * chi)
           + (7 * e2 ** 2 / 48 + 29 * e2 ** 3 / 240 + 811 * e2 ** 4 / 11520) * np.sin(4 * chi)
           + (7 * e2 ** 3 / 120 + 81 * e2 ** 4 / 1120) * np.sin(6 * chi)
           + (4279 * e2 ** 4 / 161280) * np.sin(8 * chi))
    lam = math.radians(s * lon0) + np.arctan2(xs, -ys)
    lat = s * np.degrees(phi)
    lon = s * np.degrees(lam)
    return lat, ((lon + 180.0) % 360.0) - 180.0


# ---------------------------------------------------------------- one file

def _find(f, names) -> Optional[str]:
    for n in names:
        if n in f and getattr(f[n], "ndim", None) == 1:
            return n
    return None


def _coordinates(f, var, path) -> Dict[str, Any]:
    """``{"kind": "regular", lat, lon}`` or ``{"kind": "points", lat2d, lon2d, key}``."""
    la, lo = _find(f, _LAT_NAMES), _find(f, _LON_NAMES)
    if la and lo:
        return {"kind": "regular", "lat": np.array(f[la][()], dtype=float),
                "lon": np.array(f[lo][()], dtype=float)}
    gm_name = _attr(var, "grid_mapping")
    if gm_name and gm_name in f and "x" in f and "y" in f:
        gm = {k: _attr(f[gm_name], k) for k in f[gm_name].attrs}
        if gm.get("grid_mapping_name") != "polar_stereographic":
            raise ValueError(f"{path}: grid_mapping {gm.get('grid_mapping_name')!r} is not supported "
                             "(polar_stereographic only)")
        x = np.array(f["x"][()], dtype=float)
        y = np.array(f["y"][()], dtype=float)
        X, Y = np.meshgrid(x, y)
        lat, lon = polar_stereographic_latlon(X, Y, gm)
        key = ("ps", x.tobytes(), y.tobytes(), tuple(sorted((k, str(v)) for k, v in gm.items()
                                                           if k not in ("crs_wkt", "spatial_ref"))))
        return {"kind": "points", "lat2d": lat, "lon2d": lon, "key": key}
    raise ValueError(f"{path}: no latitude/longitude coordinates (looked for {', '.join(_LAT_NAMES)} and "
                     f"{', '.join(_LON_NAMES)}, or x/y with a polar_stereographic grid_mapping)")


def _leading_error(path, variable, lead) -> str:
    axes = ", ".join(f"dim{i}={s}" for i, s in enumerate(lead))
    return f"{path}: {variable} has leading axes {axes}; declare a reduce rule"


def _read_steps(path, variable: str, reduce: Optional[str]):
    """``(total, counts, n_steps, field_or_None, coords, units)`` for one file. ``total``/``counts``
    are filled for ``climatology-mean``; ``field`` (2-D) otherwise."""
    import h5py

    check_netcdf4_signature(path)
    if reduce is not None and reduce not in REDUCES:
        raise ValueError(f"unknown reduce {reduce!r}")
    with h5py.File(str(path), "r") as f:
        if variable not in f or not isinstance(f[variable], h5py.Dataset):
            names = sorted(k for k in f if isinstance(f[k], h5py.Dataset))
            raise ValueError(f"{path}: variable {variable!r} not found ({names})")
        var = f[variable]
        shape = tuple(var.shape)
        if len(shape) < 2:
            raise ValueError(f"{path}: {variable} must have latitude and longitude axes")
        units = _attr(var, "units") or ""
        if not isinstance(units, str):
            units = str(units)
        coords = _coordinates(f, var, path)
        lead = shape[:-2]
        keep = [i for i, n in enumerate(lead) if n != 1]
        if reduce == "climatology-mean":
            if len(keep) > 1:
                raise ValueError(_leading_error(path, variable, lead))
            n_steps = lead[keep[0]] if keep else 1
            total = np.zeros(shape[-2:])
            counts = np.zeros(shape[-2:], dtype=np.int64)
            for t in range(n_steps):
                idx = tuple((t if i in keep else 0) for i in range(len(lead)))
                step = decode(var[idx], var)
                ok = np.isfinite(step)
                total += np.where(ok, step, 0.0)
                counts += ok
            return total, counts, n_steps, None, coords, units
        field = decode(var[()], var).reshape(tuple(lead[i] for i in keep) + shape[-2:])
        if reduce == "annual-mean":
            n = field.shape[0] if field.ndim == 3 else (1 if field.ndim == 2 else None)
            if n != 12:
                if n is None:
                    raise ValueError(_leading_error(path, variable, lead))
                raise ValueError(f"{path}: annual-mean needs 12 months, found {n}")
            field = field.mean(axis=0)  # NaN wherever any month is missing
        elif field.ndim != 2:
            raise ValueError(_leading_error(path, variable, lead))
        return None, None, 1, field, coords, units


def _grid(values, coords, counts=None, steps=None, units="") -> SourceGrid:
    if coords["kind"] == "points":
        return SourceGrid(values=np.asarray(values, dtype=float).ravel(),
                          lat=coords["lat2d"].ravel(), lon=coords["lon2d"].ravel(), units=units,
                          counts=None if counts is None else np.asarray(counts).ravel(),
                          steps=steps, points=True)
    c = None
    if counts is not None:
        c, _, _ = normalise(np.asarray(counts, dtype=float), coords["lat"], coords["lon"])
        c = c.astype(np.int64)
    v, lat, lon = normalise(values, coords["lat"], coords["lon"])
    return SourceGrid(values=v, lat=lat, lon=lon, units=units, counts=c, steps=steps)


def read_netcdf4(path, variable: str, reduce: Optional[str] = None) -> SourceGrid:
    """Read a ``(..., lat, lon)`` (or ``(..., y, x)`` polar-stereographic) variable."""
    total, counts, n, field, coords, units = _read_steps(path, variable, reduce)
    if reduce == "climatology-mean":
        with np.errstate(invalid="ignore", divide="ignore"):
            values = np.where(counts > 0, total / np.maximum(counts, 1), np.nan)
        return _grid(values, coords, counts=counts, steps=int(n), units=units)
    return _grid(field, coords, units=units)


def read_netcdf4_files(paths: Sequence[Path], variable: str, reduce: Optional[str] = None) -> SourceGrid:
    """Several files of one variable. ``climatology-mean``: per pixel, the mean of the valid values
    over every step of every file on the same grid (``counts``, ``steps`` = files); grids that
    differ are joined as points. Without a reduce rule each file must be 2-D and the files are
    joined as points (or returned as is when there is one)."""
    paths = list(paths)
    if not paths:
        raise ValueError("no files to read")
    if len(paths) == 1:
        return read_netcdf4(paths[0], variable, reduce)
    groups: List[Dict[str, Any]] = []

    def group_for(coords):
        key = coords["key"] if coords["kind"] == "points" else (
            "ll", coords["lat"].tobytes(), coords["lon"].tobytes())
        for g in groups:
            if g["key"] == key:
                return g
        g = {"key": key, "coords": coords, "total": None, "counts": None, "files": 0, "fields": []}
        groups.append(g)
        return g

    units = ""
    for p in paths:
        if reduce == "climatology-mean":
            total, counts, _, _, coords, u = _read_steps(p, variable, reduce)
            g = group_for(coords)
            g["total"] = total if g["total"] is None else g["total"] + total
            g["counts"] = counts if g["counts"] is None else g["counts"] + counts
        else:
            _, _, _, field, coords, u = _read_steps(p, variable, reduce)
            g = group_for(coords)
            g["fields"].append(field)
        g["files"] += 1
        units = units or u
    grids = []
    for g in groups:
        if reduce == "climatology-mean":
            with np.errstate(invalid="ignore", divide="ignore"):
                values = np.where(g["counts"] > 0, g["total"] / np.maximum(g["counts"], 1), np.nan)
            grids.append(_grid(values, g["coords"], counts=g["counts"], steps=g["files"], units=units))
        else:
            for fld in g["fields"]:
                grids.append(_grid(fld, g["coords"], units=units))
    if len(grids) == 1:
        return grids[0]
    return join_points(grids, steps=len(paths) if reduce == "climatology-mean" else None)


def join_points(grids: Sequence[SourceGrid], steps: Optional[int] = None) -> SourceGrid:
    """Concatenate grids (regular or points) into one points grid."""
    vals, lats, lons, counts = [], [], [], []
    with_counts = all(g.counts is not None for g in grids)
    for g in grids:
        if g.points:
            vals.append(g.values), lats.append(g.lat), lons.append(g.lon)
            if with_counts:
                counts.append(np.asarray(g.counts).ravel())
        else:
            LON, LAT = np.meshgrid(g.lon, g.lat)
            vals.append(g.values.ravel()), lats.append(LAT.ravel()), lons.append(LON.ravel())
            if with_counts:
                counts.append(np.asarray(g.counts).ravel())
    return SourceGrid(values=np.concatenate(vals), lat=np.concatenate(lats), lon=np.concatenate(lons),
                      units=grids[0].units, counts=np.concatenate(counts) if with_counts else None,
                      steps=steps, points=True)

"""Readers for the registry's file formats (004 research R5; netCDF-4 needs h5py, feature 013).

- ``dods``: DAP2 binary (OPeNDAP ``.dods``): DDS text, ``Data:\\n``, then XDR arrays.
- ``netcdf3``: netCDF-3 classic via ``scipy.io.netcdf_file`` (size-1 leading axes dropped;
  netCDF-4/HDF5 files rejected by signature).
- ``npy``: a NumPy array plus a cell-registered extent (rows south to north).
- ``kit-design``: the packaged official design grid (categorical, already on the kit grid).
- ``geotiff`` (feature 012): a strip GeoTIFF, block-averaged while reading (``geotiff.py``).
- ``netcdf4`` (feature 013): netCDF-4/HDF5 via h5py (``netcdf4.py``), one file or a multi-file entry.

Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from .grid import SourceGrid, normalise
from .registry import DatasetEntry

_DODS_MARK = b"\nData:\n"
_DODS_TYPES = {"Float32": (">f4", 4), "Float64": (">f8", 8), "Int32": (">i4", 4),
               "Int16": (">i4", 4), "UInt16": (">u4", 4), "Byte": ("B", 1)}
_MISSING_FLOOR = -1e30  # netCDF default fills (e.g. -9.96921e36) are below this


def read_dods(path, variable: str, fill: Optional[float] = None) -> SourceGrid:
    """Read a DAP2 ``Grid`` response with one 2-D array and its ``lat``/``lon`` maps."""
    data = Path(path).read_bytes()
    i = data.find(_DODS_MARK)
    if i < 0 or not data.lstrip().startswith(b"Dataset"):
        raise ValueError(f"{path}: not a DODS (DAP2 binary) response")
    dds = data[:i].decode("ascii", "replace")
    decls = re.findall(r"(\w+)\s+(\w+)((?:\[\s*\w+\s*=\s*\d+\s*\])+);", dds)
    if not decls:
        raise ValueError(f"{path}: DODS header lists no arrays")
    pos = i + len(_DODS_MARK)
    arrays: Dict[str, np.ndarray] = {}
    for typ, name, dims in decls:
        shape = tuple(int(n) for n in re.findall(r"=\s*(\d+)", dims))
        if typ not in _DODS_TYPES:
            raise ValueError(f"{path}: unsupported DODS type {typ}")
        dt, width = _DODS_TYPES[typ]
        n = int.from_bytes(data[pos:pos + 4], "big")
        if n != int(np.prod(shape)):
            raise ValueError(f"{path}: DODS array {name} has {n} values, expected {np.prod(shape)}")
        pos += 8
        raw = np.frombuffer(data[pos:pos + n * width], dtype=dt)
        if raw.size != n:
            raise ValueError(f"{path}: DODS array {name} is truncated")
        pos += n * width
        arrays[name] = raw.reshape(shape)
    if variable not in arrays:
        raise ValueError(f"{path}: variable {variable!r} not in DODS response ({sorted(arrays)})")
    values = arrays[variable].astype(float)
    if fill is not None:
        values = np.where(values == fill, np.nan, values)
    values, lat, lon = normalise(values, arrays["lat"], arrays["lon"])
    return SourceGrid(values=values, lat=lat, lon=lon)


def _attr(var, name):
    v = getattr(var, name, None)
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    return v


_NETCDF3_SIGNATURES = (b"CDF\x01", b"CDF\x02")
_HDF5_SIGNATURE = b"\x89HDF"


def _check_netcdf3_signature(path) -> None:
    """netCDF-3 classic or 64-bit offset only; name netCDF-4/HDF5 files plainly (009 R2)."""
    with open(path, "rb") as fh:
        head = fh.read(4)
    if head in _NETCDF3_SIGNATURES:
        return
    if head == _HDF5_SIGNATURE:
        raise ValueError(f"{path}: not a netCDF-3 classic file (netCDF-4/HDF5 signature); "
                         "this reader reads netCDF-3 only")
    raise ValueError(f"{path}: not a netCDF-3 classic file")


_LAT_NAMES = ("lat", "latitude")
_LON_NAMES = ("lon", "longitude")


def _coord(f, names, path, what):
    for n in names:
        if n in f.variables:
            return np.array(f.variables[n][:], dtype=float)
    raise ValueError(f"{path}: no {what} coordinate variable (looked for {', '.join(names)})")


def _clean(raw: np.ndarray, var) -> np.ndarray:
    """Missing values to NaN, then scale and offset (CF packing)."""
    for name in ("missing_value", "_FillValue"):
        mv = _attr(var, name)
        if mv is not None:
            mv = float(np.asarray(mv).ravel()[0])
            if np.isfinite(mv):
                raw = np.where(np.isclose(raw, mv, rtol=1e-6), np.nan, raw)
    raw = np.where(raw < _MISSING_FLOOR, np.nan, raw)
    scale, offset = _attr(var, "scale_factor"), _attr(var, "add_offset")
    if scale is not None:
        raw = raw * float(scale)
    if offset is not None:
        raw = raw + float(offset)
    return raw


def read_netcdf3(path, variable: str, reduce: Optional[str] = None) -> SourceGrid:
    """Read a ``(..., lat, lon)`` variable.

    Coordinates may be named ``lat``/``lon`` or ``latitude``/``longitude`` (ERDDAP; feature 012).
    Leading axes of size 1 (e.g. ``time=1, lev=1`` in the ERSST per-month files) are dropped.
    ``reduce="annual-mean"`` averages a 12-step leading axis where all months are valid;
    ``reduce="climatology-mean"`` (feature 012) averages every valid step of one leading axis,
    reading one step at a time, and returns ``counts`` (valid steps per pixel) and ``steps``.
    ``reduce="monthly-max"`` (feature 015, the sea-ice rule) takes the warmest of the 12 months,
    NaN only where every month is missing. Any other leading axis larger than 1 is an error naming
    the dimensions.
    """
    from scipy.io import netcdf_file

    _check_netcdf3_signature(path)
    counts = steps = None
    with netcdf_file(str(path), "r", mmap=(reduce == "climatology-mean")) as f:
        if variable not in f.variables:
            raise ValueError(f"{path}: variable {variable!r} not found ({sorted(f.variables)})")
        var = f.variables[variable]
        dims = tuple(var.dimensions)
        shape = tuple(var.shape)
        units = _attr(var, "units") or ""
        lat = _coord(f, _LAT_NAMES, path, "latitude")
        lon = _coord(f, _LON_NAMES, path, "longitude")
        if len(shape) < 2:
            raise ValueError(f"{path}: {variable} must have latitude and longitude axes")
        lead = shape[:-2]
        names = dims[:-2] if len(dims) == len(shape) else tuple(f"dim{i}" for i in range(len(lead)))
        keep = [i for i, n in enumerate(lead) if n != 1]
        try:
            if reduce == "climatology-mean":
                if len(keep) > 1:
                    raise ValueError(_leading_error(path, variable, names, lead))
                n_steps = lead[keep[0]] if keep else 1
                total = np.zeros(shape[-2:])
                counts = np.zeros(shape[-2:], dtype=np.int64)
                for t in range(n_steps):
                    idx = tuple((t if i in keep else 0) for i in range(len(lead)))
                    step = _clean(np.array(var[idx], dtype=float), var)
                    ok = np.isfinite(step)
                    total += np.where(ok, step, 0.0)
                    counts += ok
                    del step
                with np.errstate(invalid="ignore", divide="ignore"):
                    values = np.where(counts > 0, total / np.maximum(counts, 1), np.nan)
                steps = int(n_steps)
            else:
                raw = _clean(np.array(var[:], dtype=float), var)
                field = raw.reshape(tuple(lead[i] for i in keep) + raw.shape[-2:])
                if reduce in ("annual-mean", "monthly-max"):
                    n = field.shape[0] if field.ndim == 3 else (1 if field.ndim == 2 else None)
                    if n != 12:
                        if n is None:
                            raise ValueError(_leading_error(path, variable, names, lead))
                        raise ValueError(f"{path}: {reduce} needs 12 months, found {n}")
                    if reduce == "annual-mean":
                        values = field.mean(axis=0)  # NaN wherever any month is missing
                    else:
                        valid = np.isfinite(field).any(axis=0)
                        values = np.where(
                            valid, np.max(np.where(np.isfinite(field), field, -np.inf), axis=0),
                            np.nan)
                elif field.ndim == 2:
                    values = field
                else:
                    raise ValueError(_leading_error(path, variable, names, lead))
        finally:
            var = None  # no reference to mapped data may outlive the file
    if counts is not None:
        c, _, _ = normalise(counts.astype(float), lat, lon)
        counts = c.astype(np.int64)
    values, lat, lon = normalise(values, lat, lon)
    return SourceGrid(values=values, lat=lat, lon=lon, units=units, counts=counts, steps=steps)


def netcdf3_content_sha256(path, variable: str) -> str:
    """SHA-256 over the stored data of ``variable`` and its dimension coordinates (feature 012,
    research R2): for each, in order, ``name``, NUL, dtype, NUL, shape, NUL, then the raw stored
    (big-endian) bytes. Attributes, including ERDDAP's per-request ``history``, are excluded."""
    import hashlib

    from scipy.io import netcdf_file

    _check_netcdf3_signature(path)
    h = hashlib.sha256()
    with netcdf_file(str(path), "r", mmap=True) as f:
        if variable not in f.variables:
            raise ValueError(f"{path}: variable {variable!r} not found ({sorted(f.variables)})")
        names = [variable] + [d for d in f.variables[variable].dimensions if d in f.variables]
        for name in names:
            var = f.variables[name]
            arr = var.data
            h.update(name.encode() + b"\0" + arr.dtype.str.encode() + b"\0" +
                     repr(tuple(arr.shape)).encode() + b"\0")
            if arr.ndim and arr.shape[0] > 1:
                for i in range(arr.shape[0]):  # one step at a time (bounded memory)
                    h.update(np.ascontiguousarray(arr[i]).tobytes())
            else:
                h.update(np.ascontiguousarray(arr).tobytes())
            del arr, var
    return h.hexdigest()


def _leading_error(path, variable, names, lead) -> str:
    axes = ", ".join(f"{n}={s}" for n, s in zip(names, lead))
    return f"{path}: {variable} has leading axes {axes}; declare a reduce rule"


def read_npy(path, grid: Dict[str, Any]) -> SourceGrid:
    """A 2-D array with a cell-registered extent ``grid = {lat: [s, n], lon: [w, e]}``; row 0 is
    the southern row. ``grid.fill`` marks missing values."""
    for key in ("lat", "lon"):
        if not (isinstance(grid.get(key), (list, tuple)) and len(grid[key]) == 2):
            raise ValueError(f"{path}: .npy data needs grid {key} = [min, max]")
    a = np.load(str(path), allow_pickle=False)
    if a.ndim != 2:
        raise ValueError(f"{path}: .npy data must be 2-D, found {a.ndim}-D")
    values = a.astype(float)
    if grid.get("fill") is not None:
        values = np.where(a == grid["fill"], np.nan, values)
    s, n = (float(v) for v in grid["lat"])
    w, e = (float(v) for v in grid["lon"])
    ny, nx = a.shape
    lat = s + (np.arange(ny) + 0.5) * (n - s) / ny
    lon = w + (np.arange(nx) + 0.5) * (e - w) / nx
    values, lat, lon = normalise(values, lat, lon)
    return SourceGrid(values=values, lat=lat, lon=lon)


def read_kit_design() -> SourceGrid:
    """The official design as category codes on the kit grid (FR-012; no download)."""
    from ..kit import load_official_design

    d = load_official_design()
    codes = {k: i for i, k in enumerate(d.palette)}
    values = np.array([[codes[d.color_at(x, y)] for x in range(d.width)] for y in range(d.height)],
                      dtype=float)
    return SourceGrid(values=values, lat=np.array([]), lon=np.array([]), units="category",
                      categories=list(d.palette), on_kit_grid=True)


def _land_from_mask(g: SourceGrid, rule: Dict[str, Any], cache_dir=None) -> SourceGrid:
    """Land where the nearest cell of another dataset's variable is above ``split_at``
    (``class_rule.land_from``, feature 012, research R4). The grid is first extended to the mask's
    latitude range, so land outside the file's own coverage is land with no value."""
    from .cache import resolve
    from .grid import extend_latitudes
    from .registry import get_entry

    entry = get_entry(rule["dataset"])
    mask_grid = read_dataset(entry, resolve(entry, cache_dir), rule["variable"])
    if mask_grid.on_kit_grid or mask_grid.points:
        raise ValueError(f"land_from dataset {entry.id} is not a gridded field")
    g = extend_latitudes(g, float(mask_grid.lat[0]), float(mask_grid.lat[-1]))
    ri = _nearest_index(mask_grid.lat, g.lat)
    ci = _nearest_index(mask_grid.lon, g.lon, period=360.0)
    mv = mask_grid.values[np.ix_(ri, ci)]
    g.land = np.where(np.isfinite(mv), mv > float(rule["split_at"]), False)
    return g


def _nearest_index(axis: np.ndarray, x: np.ndarray, period: Optional[float] = None) -> np.ndarray:
    """Index of the nearest ``axis`` value (ascending) for each ``x``; wraps when ``period``."""
    axis = np.asarray(axis, dtype=float)
    i = np.clip(np.searchsorted(axis, x), 1, len(axis) - 1)
    left, right = axis[i - 1], axis[i]
    idx = np.where(np.abs(x - left) <= np.abs(right - x), i - 1, i)
    if period is not None and len(axis) > 1:
        # beyond either end the first or last cell may be nearer across the date line
        d_first = np.abs(((x - axis[0]) + period / 2) % period - period / 2)
        d_last = np.abs(((x - axis[-1]) + period / 2) % period - period / 2)
        d_idx = np.abs(x - axis[idx])
        idx = np.where(d_first < d_idx, 0, idx)
        idx = np.where((d_last < d_idx) & (d_last < d_first), len(axis) - 1, idx)
    return idx


TRANSFORMS = ("none", "negate", "log10")


def read_dataset(entry: DatasetEntry, path, variable: str, transform: str = "none",
                 cache_dir=None) -> SourceGrid:
    """Read ``variable`` of ``entry`` from ``path`` and apply the entry's land/ocean rule.

    The class rule is applied to the raw values, before ``transform`` (e.g. depth = -elevation;
    ``log10``, feature 012: values <= 0 become missing). ``cache_dir`` locates a ``land_from``
    mask dataset.
    """
    spec = entry.variables.get(variable, {}) if entry.variables else {}
    if entry.format == "kit-design":
        return read_kit_design()
    if entry.format == "dods":
        g = read_dods(path, variable, fill=entry.grid.get("fill"))
    elif entry.format == "netcdf3":
        g = read_netcdf3(path, variable, reduce=spec.get("reduce"))
    elif entry.format == "netcdf4":  # feature 013 (h5py); a multi-file entry's path is its directory
        from .netcdf4 import read_netcdf4, read_netcdf4_files

        if entry.files:
            g = read_netcdf4_files([Path(path) / f.name for f in entry.files], variable,
                                   reduce=spec.get("reduce"))
        else:
            g = read_netcdf4(path, variable, reduce=spec.get("reduce"))
    elif entry.format == "npy":
        g = read_npy(path, entry.grid)
    elif entry.format == "geotiff":
        from .geotiff import read_geotiff

        g = read_geotiff(path, block=int(entry.grid.get("block", 1)),
                         **{k: spec[k] for k in ("scale_factor", "add_offset", "valid_min", "valid_max",
                                                 "fill") if k in spec})
    else:  # pragma: no cover - registry validation rejects other formats
        raise ValueError(f"unsupported format {entry.format}")
    rule = entry.class_rule or {}
    if "split_at" in rule:
        g.land = np.where(np.isfinite(g.values), g.values > float(rule["split_at"]), False)
    elif rule.get("missing_is_land"):
        g.land = ~np.isfinite(g.values)
    elif "land_from" in rule:
        g = _land_from_mask(g, rule["land_from"], cache_dir)
    if transform == "negate":
        g.values = -g.values
    elif transform == "log10":
        with np.errstate(invalid="ignore", divide="ignore"):
            g.values = np.where(g.values > 0, np.log10(np.where(g.values > 0, g.values, 1.0)), np.nan)
    elif transform != "none":
        raise ValueError(f"unknown transform {transform!r}")
    if spec.get("units") and not g.units:
        g.units = spec["units"]
    return g

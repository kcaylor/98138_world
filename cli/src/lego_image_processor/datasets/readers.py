"""Readers for the registry's file formats, with no new dependencies (research R5).

- ``dods``: DAP2 binary (OPeNDAP ``.dods``): DDS text, ``Data:\\n``, then XDR arrays.
- ``netcdf3``: netCDF-3 classic via ``scipy.io.netcdf_file`` (size-1 leading axes dropped;
  netCDF-4/HDF5 files rejected by signature).
- ``npy``: a NumPy array plus a cell-registered extent (rows south to north).
- ``kit-design``: the packaged official design grid (categorical, already on the kit grid).

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


def read_netcdf3(path, variable: str, reduce: Optional[str] = None) -> SourceGrid:
    """Read a ``(..., lat, lon)`` variable.

    Leading axes of size 1 (e.g. ``time=1, lev=1`` in the ERSST per-month files) are dropped.
    ``reduce="annual-mean"`` averages a 12-step leading axis where all months are valid;
    ``reduce="monthly-max"`` (feature 012, the sea-ice rule) takes the warmest of the 12 months,
    NaN only where every month is missing; any other leading axis larger than 1 is an error
    naming the dimensions.
    """
    from scipy.io import netcdf_file

    _check_netcdf3_signature(path)
    with netcdf_file(str(path), "r", mmap=False) as f:
        if variable not in f.variables:
            raise ValueError(f"{path}: variable {variable!r} not found ({sorted(f.variables)})")
        var = f.variables[variable]
        dims = tuple(var.dimensions)
        raw = np.array(var[:], dtype=float)
        for name in ("missing_value", "_FillValue"):
            mv = _attr(var, name)
            if mv is not None:
                raw = np.where(np.isclose(raw, float(np.asarray(mv).ravel()[0]), rtol=1e-6), np.nan, raw)
        raw = np.where(raw < _MISSING_FLOOR, np.nan, raw)
        scale, offset = _attr(var, "scale_factor"), _attr(var, "add_offset")
        if scale is not None:
            raw = raw * float(scale)
        if offset is not None:
            raw = raw + float(offset)
        units = _attr(var, "units") or ""
        lat = np.array(f.variables["lat"][:], dtype=float)
        lon = np.array(f.variables["lon"][:], dtype=float)
    if raw.ndim < 2:
        raise ValueError(f"{path}: {variable} must have latitude and longitude axes")
    lead = raw.shape[:-2]
    names = dims[:-2] if len(dims) == raw.ndim else tuple(f"dim{i}" for i in range(len(lead)))
    keep = [i for i, n in enumerate(lead) if n != 1]
    field = raw.reshape(tuple(lead[i] for i in keep) + raw.shape[-2:])
    if reduce in ("annual-mean", "monthly-max"):
        steps = field.shape[0] if field.ndim == 3 else (1 if field.ndim == 2 else None)
        if steps != 12:
            if steps is None:
                raise ValueError(_leading_error(path, variable, names, lead))
            raise ValueError(f"{path}: {reduce} needs 12 months, found {steps}")
        if reduce == "annual-mean":
            values = field.mean(axis=0)  # NaN wherever any month is missing
        else:
            valid = np.isfinite(field).any(axis=0)
            values = np.where(valid, np.max(np.where(np.isfinite(field), field, -np.inf), axis=0),
                              np.nan)
    elif field.ndim == 2:
        values = field
    else:
        raise ValueError(_leading_error(path, variable, names, lead))
    values, lat, lon = normalise(values, lat, lon)
    return SourceGrid(values=values, lat=lat, lon=lon, units=units)


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


def read_dataset(entry: DatasetEntry, path, variable: str, transform: str = "none") -> SourceGrid:
    """Read ``variable`` of ``entry`` from ``path`` and apply the entry's land/ocean rule.

    The class rule is applied to the raw values, before ``transform`` (e.g. depth = -elevation).
    """
    spec = entry.variables.get(variable, {}) if entry.variables else {}
    if entry.format == "kit-design":
        return read_kit_design()
    if entry.format == "dods":
        g = read_dods(path, variable, fill=entry.grid.get("fill"))
    elif entry.format == "netcdf3":
        g = read_netcdf3(path, variable, reduce=spec.get("reduce"))
    elif entry.format == "npy":
        g = read_npy(path, entry.grid)
    else:  # pragma: no cover - registry validation rejects other formats
        raise ValueError(f"unsupported format {entry.format}")
    rule = entry.class_rule or {}
    if "split_at" in rule:
        g.land = np.where(np.isfinite(g.values), g.values > float(rule["split_at"]), False)
    elif rule.get("missing_is_land"):
        g.land = ~np.isfinite(g.values)
    if transform == "negate":
        g.values = -g.values
    if spec.get("units") and not g.units:
        g.units = spec["units"]
    return g

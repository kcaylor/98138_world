"""Write the small derived dataset fixtures used by the feature 004 tests (research R11).

Reads the verified cached ETOPO 2022 and ERSST v5 files and writes, into
``tests/fixtures/datasets/``:

- ``etopo2022_1deg.npy``: int16 means of 6x6 blocks of the 10-arc-minute subset (1 degree,
  180 x 360, rows south to north, metres);
- ``ersst_v5_annual_2deg.nc``: netCDF-3 annual mean SST (89 x 180, degC; missing over land/ice);
- ``ersst_v5_YYYYMM_ssta.nc`` (feature 009): the ERSST v5 per-month ``ssta`` on the full 2 degree
  grid, keeping the source's ``(time=1, lev=1, lat, lon)`` structure, packed as int16 with
  ``scale_factor 0.01`` and ``_FillValue -999``;
- ``<name>.source.json`` beside each: dataset id, source SHA-256, method, license, generator.

Usage (from ``cli/``): ``PYTHONPATH=tools python -m fixtures004.make_fixtures [--cache-dir DIR]
[--only DATASET_ID ...]``.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from lego_image_processor.datasets import get_entry, read_dataset, resolve, sha256_file
from lego_image_processor.kit.source import DISCLAIMER

OUT = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "datasets"
GENERATOR = "tools/fixtures004/make_fixtures.py"


def _source(name, entry, method, extra=None):
    d = {"fixture": name, "dataset": entry.id, "version": entry.version,
         "source_sha256": entry.sha256, "source_url": entry.url, "method": method,
         "license": entry.license, "citation": entry.citation, "doi": entry.doi,
         "generator": GENERATOR, "disclaimer": DISCLAIMER}
    d.update(extra or {})
    return d


def make_etopo(cache_dir, out: Path) -> Path:
    e = get_entry("etopo2022-surface-10m")
    g = read_dataset(e, resolve(e, cache_dir), "z")
    v = g.values  # 1080 x 2160, lat ascending, lon -180..180
    blocks = v.reshape(180, 6, 360, 6)
    with np.errstate(invalid="ignore"):
        mean = np.nanmean(blocks, axis=(1, 3))
    arr = np.round(mean).astype(np.int16)
    p = out / "etopo2022_1deg.npy"
    np.save(p, arr)
    meta = _source(p.name, e, "nanmean of 6x6 blocks of the 10-arc-minute DODS subset, rounded to int16 "
                              "metres; rows south to north, cell-registered 1 degree, lat [-90, 90], "
                              "lon [-180, 180]",
                   {"grid": {"lat": [-90, 90], "lon": [-180, 180]}, "units": "m", "sha256": sha256_file(p)})
    (out / "etopo2022_1deg.source.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return p


def make_ersst(cache_dir, out: Path) -> Path:
    from scipy.io import netcdf_file

    e = get_entry("ersst-v5-ltm-1991-2020")
    src = resolve(e, cache_dir)
    with netcdf_file(str(src), "r", mmap=False) as f:
        lat = np.array(f.variables["lat"][:], dtype=np.float32)
        lon = np.array(f.variables["lon"][:], dtype=np.float32)
        raw = np.array(f.variables["sst"][:], dtype=np.float64)
    raw = np.where(raw < -1e30, np.nan, raw)
    annual = raw.mean(axis=0)
    missing = np.float32(-9.96921e36)
    p = out / "ersst_v5_annual_2deg.nc"
    f = netcdf_file(str(p), "w")
    f.title = "Annual mean of NOAA ERSST v5 1991-2020 monthly long-term means (test fixture)"
    f.createDimension("lat", len(lat))
    f.createDimension("lon", len(lon))
    vlat = f.createVariable("lat", "f4", ("lat",))
    vlat[:] = lat
    vlon = f.createVariable("lon", "f4", ("lon",))
    vlon[:] = lon
    v = f.createVariable("sst", "f4", ("lat", "lon"))
    v.units = "degC"
    v.missing_value = missing
    v[:] = np.where(np.isfinite(annual), annual, missing).astype(np.float32)
    f.close()
    meta = _source(p.name, e, "mean of the 12 monthly long-term means where all 12 are valid; written as "
                              "netCDF-3 sst(lat, lon) with the source's lat/lon and missing value",
                   {"units": "degC", "sha256": sha256_file(p)})
    (out / "ersst_v5_annual_2deg.source.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return p


ERSST_MONTHS = ("ersst-v5-1997-12", "ersst-v5-1988-12")
_PACK_FILL = -999
_PACK_SCALE = 0.01


def make_ersst_month(dataset_id: str, cache_dir, out: Path) -> Path:
    """Pack one ERSST v5 per-month file's ``ssta`` as int16 (0.01 degC), same dims and coords."""
    from scipy.io import netcdf_file

    e = get_entry(dataset_id)
    src = resolve(e, cache_dir)
    with netcdf_file(str(src), "r", mmap=False) as f:
        dims = {name: f.dimensions[name] for name in f.variables["ssta"].dimensions}
        coords = {name: (np.array(f.variables[name][:], dtype=np.float32),
                         {k: v for k, v in f.variables[name]._attributes.items()})
                  for name in dims if name in f.variables}
        var = f.variables["ssta"]
        raw = np.array(var[:], dtype=np.float64)
        fill = getattr(var, "_FillValue", None)
    if fill is not None:
        raw = np.where(np.isclose(raw, float(fill)), np.nan, raw)
    raw = np.where(raw < -1e30, np.nan, raw)
    packed = np.where(np.isfinite(raw), np.round(np.nan_to_num(raw) / _PACK_SCALE), _PACK_FILL)
    stamp = dataset_id.split("-")[-2] + dataset_id.split("-")[-1]
    p = out / f"ersst_v5_{stamp}_ssta.nc"
    f = netcdf_file(str(p), "w")
    f.title = f"NOAA ERSST v5 ssta, {stamp[:4]}-{stamp[4:]}, packed to 0.01 degC (test fixture)"
    for name, size in dims.items():
        f.createDimension(name, size)
    for name, (values, attrs) in coords.items():
        cv = f.createVariable(name, "f4", (name,))
        for k, val in attrs.items():
            if k not in ("_FillValue", "scale_factor", "add_offset"):
                setattr(cv, k, val)
        cv[:] = values
    v = f.createVariable("ssta", "i2", tuple(dims))
    v._FillValue = np.int16(_PACK_FILL)
    v.scale_factor = np.float32(_PACK_SCALE)
    v.add_offset = np.float32(0.0)
    v.units = "degree_C"
    v[:] = packed.astype(np.int16)
    f.close()
    meta = _source(p.name, e, "ssta of the per-month file, dims and coordinates kept (time=1, lev=1, "
                              "lat, lon), sst dropped; packed as int16 with scale_factor 0.01, "
                              "add_offset 0 and _FillValue -999 (round to 0.01 degC)",
                   {"units": "degree_C", "sha256": sha256_file(p)})
    (out / f"ersst_v5_{stamp}_ssta.source.json").write_text(json.dumps(meta, indent=2) + "\n",
                                                             encoding="utf-8")
    return p


MAKERS = {
    "etopo2022-surface-10m": make_etopo,
    "ersst-v5-ltm-1991-2020": make_ersst,
    **{i: (lambda cache_dir, out, _i=i: make_ersst_month(_i, cache_dir, out)) for i in ERSST_MONTHS},
}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache-dir", default=None)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--only", action="append", choices=sorted(MAKERS), metavar="DATASET_ID",
                    help="write only this dataset's fixture (repeatable; default: all)")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for dataset_id in a.only or list(MAKERS):
        p = MAKERS[dataset_id](a.cache_dir, out)
        print(f"wrote {p} ({p.stat().st_size:,} bytes)")
    print(DISCLAIMER)


if __name__ == "__main__":
    main()

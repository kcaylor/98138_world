"""Write the small derived dataset fixtures used by the feature 004 tests (research R11).

Reads the verified cached ETOPO 2022 and ERSST v5 files and writes, into
``tests/fixtures/datasets/``:

- ``etopo2022_1deg.npy``: int16 means of 6x6 blocks of the 10-arc-minute subset (1 degree,
  180 x 360, rows south to north, metres);
- ``ersst_v5_annual_2deg.nc``: netCDF-3 annual mean SST (89 x 180, degC; missing over land/ice);
- ``<name>.source.json`` beside each: dataset id, source SHA-256, method, license, generator.

Usage (from ``cli/``): ``PYTHONPATH=tools python -m fixtures004.make_fixtures [--cache-dir DIR]``.
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


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache-dir", default=None)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for p in (make_etopo(a.cache_dir, out), make_ersst(a.cache_dir, out)):
        print(f"wrote {p} ({p.stat().st_size:,} bytes)")
    print(DISCLAIMER)


if __name__ == "__main__":
    main()

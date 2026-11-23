"""Write the small derived dataset fixtures used by the feature 004 tests (research R11).

Reads the verified cached ETOPO 2022 and ERSST v5 files and writes, into
``tests/fixtures/datasets/``:

- ``etopo2022_1deg.npy``: int16 means of 6x6 blocks of the 10-arc-minute subset (1 degree,
  180 x 360, rows south to north, metres);
- ``ersst_v5_annual_2deg.nc``: netCDF-3 annual mean SST (89 x 180, degC; missing over land/ice);
- ``ersst_v5_YYYYMM_ssta.nc`` (feature 009): the ERSST v5 per-month ``ssta`` on the full 2 degree
  grid, keeping the source's ``(time=1, lev=1, lat, lon)`` structure, packed as int16 with
  ``scale_factor 0.01`` and ``_FillValue -999``;
- ``mod17a3_npp_1deg.tif`` (feature 012): MOD17A3 NPP block means (1 degree) as a uint16 LZW strip
  GeoTIFF; ``modis_chla_4deg_6mo.nc``: six months of MODIS-Aqua chlorophyll-a at 4 degrees;
- ``gpcp_v23_ltm_10deg.nc`` (feature 013): GPCP v2.3 12-month long-term mean precipitation at
  every 4th cell (10 degrees, 18 x 36), netCDF-4 (h5py) as PSL writes it;
  ``nsidc_cdr_v6_<hemisphere>_<yyyymm>_4x.nc``: four NSIDC CDR v6 minimum-month files (1991 and
  2020, north and south) at every 4th pixel (100 km), x/y and the CF crs kept;
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


def write_geotiff(path: Path, codes: np.ndarray, west: float, north: float, step: float) -> None:
    """A uint16 LZW strip GeoTIFF (WGS84 degrees) written with Pillow (feature 012 fixtures/tests)."""
    from PIL import Image, TiffImagePlugin

    ifd = TiffImagePlugin.ImageFileDirectory_v2()
    ifd[33550] = (float(step), float(step), 0.0)
    ifd.tagtype[33550] = 12
    ifd[33922] = (0.0, 0.0, 0.0, float(west), float(north), 0.0)
    ifd.tagtype[33922] = 12
    im = Image.fromarray(np.ascontiguousarray(codes.astype("<u2")), mode="I;16")
    im.save(str(path), compression="tiff_lzw", tiffinfo=ifd)


def make_npp(cache_dir, out: Path) -> Path:
    """MOD17A3 NPP: 120 x 120 block means of the valid raw codes (1 degree), fill 65535 (012, R6)."""
    from lego_image_processor.datasets.geotiff import read_geotiff, read_layout

    e = get_entry("mod17a3-npp-mean-2000-2015")
    src = resolve(e, cache_dir)
    spec = e.variables["npp"]
    g = read_geotiff(src, block=120, valid_max=spec["valid_max"], fill=spec["fill"])
    lay = read_layout(src)
    codes = np.where(np.isfinite(g.values), np.round(np.nan_to_num(g.values)), spec["fill"])[::-1]
    p = out / "mod17a3_npp_1deg.tif"
    write_geotiff(p, codes, lay.lon0, lay.lat0, lay.dlon * 120)
    meta = _source(p.name, e, "means of the valid raw codes (<= 65499) in 120 x 120 pixel blocks of the "
                              "30 arc-second GeoTIFF (1 degree, 360 x 140, 80N to 60S), rounded; 65535 where "
                              "a block has no valid pixel; written as a uint16 LZW strip GeoTIFF with "
                              "ModelTiepoint and ModelPixelScale; values x 0.1 = g C m-2 yr-1",
                   {"units": "g C m-2 yr-1 (x 10)", "sha256": sha256_file(p)})
    (out / "mod17a3_npp_1deg.source.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return p


CHLA_MONTHS = ("2023-01", "2023-03", "2023-05", "2023-07", "2023-09", "2023-11")


def make_chla(cache_dir, out: Path) -> Path:
    """MODIS-Aqua chl-a: six months of 2023 at every 8th row and column (4 degrees), float32, NaN
    fill, ``chlor_a(time, latitude, longitude)`` as ERDDAP writes it (012, R6)."""
    from datetime import datetime, timezone

    from scipy.io import netcdf_file

    e = get_entry("modis-aqua-chla-2013-2024")
    src = resolve(e, cache_dir)
    with netcdf_file(str(src), "r", mmap=False) as f:
        t = np.array(f.variables["time"][:], dtype=np.float64)
        stamps = [datetime.fromtimestamp(x, tz=timezone.utc).strftime("%Y-%m") for x in t]
        idx = [stamps.index(m) for m in CHLA_MONTHS]
        lat = np.array(f.variables["latitude"][::8], dtype=np.float64)
        lon = np.array(f.variables["longitude"][::8], dtype=np.float64)
        chl = np.array(f.variables["chlor_a"][idx, ::8, ::8], dtype=np.float32)
        tsel = t[idx]
        attrs = {k: v for k, v in f.variables["chlor_a"]._attributes.items() if k in ("units", "long_name")}
    p = out / "modis_chla_4deg_6mo.nc"
    f = netcdf_file(str(p), "w")
    f.title = "MODIS-Aqua chlorophyll-a R2022.0, six months of 2023, every 8th pixel (test fixture)"
    for name, n in (("time", len(tsel)), ("latitude", len(lat)), ("longitude", len(lon))):
        f.createDimension(name, n)
    vt = f.createVariable("time", "f8", ("time",))
    vt.units = "seconds since 1970-01-01T00:00:00Z"
    vt[:] = tsel
    vla = f.createVariable("latitude", "f8", ("latitude",))
    vla[:] = lat
    vlo = f.createVariable("longitude", "f8", ("longitude",))
    vlo[:] = lon
    v = f.createVariable("chlor_a", "f4", ("time", "latitude", "longitude"))
    for k, val in attrs.items():
        setattr(v, k, val)
    v._FillValue = np.float32(np.nan)
    v[:] = chl
    f.close()
    from lego_image_processor.datasets.cache import content_sha256

    meta = _source(p.name, e, "chlor_a of the pinned request for 2023-01, -03, -05, -07, -09 and -11 at "
                              "every 8th latitude and longitude (4 degrees, 45 x 90), float32 with NaN "
                              "fill; dims (time, latitude, longitude) and coordinates as ERDDAP writes them",
                   {"units": "mg m-3", "sha256": sha256_file(p), "content_sha256": content_sha256(e, p),
                    "source_content_sha256": e.content_sha256})
    (out / "modis_chla_4deg_6mo.source.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return p


GPCP_STRIDE = 4
NSIDC_STRIDE = 4
NSIDC_FIXTURE_FILES = ("sic_psn25_199109_F08_v06r00.nc", "sic_psn25_202009_F17_v06r00.nc",
                       "sic_pss25_199102_F08_v06r00.nc", "sic_pss25_202002_F17_v06r00.nc")


def _h5_attrs(obj, keep=None):
    return {k: v for k, v in obj.attrs.items()
            if k not in ("DIMENSION_LIST", "REFERENCE_LIST", "CLASS", "NAME", "_Netcdf4Dimid",
                         "_Netcdf4Coordinates") and (keep is None or k in keep)}


def make_gpcp(cache_dir, out: Path) -> Path:
    """GPCP v2.3 LTM: every 4th latitude and longitude of the 12 months (10 degrees), float32,
    attributes as in the source (feature 013, research R7)."""
    import h5py

    from fixtures004.nc4 import write_netcdf4

    e = get_entry("gpcp-v23-ltm-1991-2020")
    src = resolve(e, cache_dir)
    k = GPCP_STRIDE
    with h5py.File(str(src), "r") as f:
        lat = np.array(f["lat"][k // 2::k], dtype=np.float32)
        lon = np.array(f["lon"][k // 2::k], dtype=np.float32)
        time = np.array(f["time"][()], dtype=np.float64)
        precip = np.array(f["precip"][:, k // 2::k, k // 2::k], dtype=np.float32)
        pattrs = _h5_attrs(f["precip"], ("units", "long_name", "missing_value", "valid_range",
                                         "add_offset", "scale_factor"))
        lattrs, oattrs = _h5_attrs(f["lat"], ("units",)), _h5_attrs(f["lon"], ("units",))
        tattrs = _h5_attrs(f["time"], ("units",))
    p = out / "gpcp_v23_ltm_10deg.nc"
    write_netcdf4(p, {"lat": lat, "lon": lon, "time": time},
                  {"precip": (("time", "lat", "lon"), precip, pattrs)},
                  attrs={"title": "GPCP v2.3 LTM 1991-2020, every 4th cell (test fixture)",
                         "disclaimer": DISCLAIMER}, compress=False)
    import h5py as _h5
    with _h5.File(str(p), "r+") as f:
        for name, a in (("lat", lattrs), ("lon", oattrs), ("time", tattrs)):
            for kk, v in a.items():
                f[name].attrs[kk] = v
    meta = _source(p.name, e, f"precip(12, lat, lon) at every {k}th latitude and longitude starting at index "
                              f"{k // 2} (10 degrees, {len(lat)} x {len(lon)}), float32, source attributes "
                              "kept; netCDF-4 written with h5py (tools/fixtures004/nc4.py)",
                   {"units": "mm/day", "sha256": sha256_file(p)})
    (out / "gpcp_v23_ltm_10deg.source.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return p


def nsidc_fixture_name(source_name: str) -> str:
    """``sic_psn25_199109_F08_v06r00.nc`` -> ``nsidc_cdr_v6_n_199109_4x.nc``."""
    parts = source_name.split("_")
    return f"nsidc_cdr_v6_{'n' if parts[1].startswith('psn') else 's'}_{parts[2]}_{NSIDC_STRIDE}x.nc"


def make_nsidc(cache_dir, out: Path) -> Path:
    """Four NSIDC CDR v6 minimum-month files at every 4th pixel: ``cdr_seaice_conc_monthly``
    (uint8, scale 0.01, fill 255), x, y, time and the CF crs as in the source (feature 013, R7)."""
    import h5py

    from fixtures004.nc4 import write_netcdf4
    from lego_image_processor.datasets.cache import file_paths

    e = get_entry("nsidc-cdr-v6-seaice-minimum-1991-2020")
    resolve(e, cache_dir)
    by_name = {f.name: (f, path) for f, path in file_paths(e, cache_dir)}
    k = NSIDC_STRIDE
    last = None
    for name in NSIDC_FIXTURE_FILES:
        pin, src = by_name[name]
        with h5py.File(str(src), "r") as f:
            x = np.array(f["x"][k // 2::k], dtype=np.float64)
            y = np.array(f["y"][k // 2::k], dtype=np.float64)
            t = np.array(f["time"][()], dtype=np.int64)
            v = f["cdr_seaice_conc_monthly"]
            conc = np.array(v[:, k // 2::k, k // 2::k], dtype=np.uint8)
            vattrs = _h5_attrs(v, ("_FillValue", "units", "valid_range", "add_offset", "scale_factor",
                                   "grid_mapping", "standard_name", "long_name"))
            crs = _h5_attrs(f["crs"])
            gattrs = {kk: f.attrs[kk] for kk in ("title", "license", "product_version") if kk in f.attrs}
        p = out / nsidc_fixture_name(name)
        write_netcdf4(p, {"time": t, "y": y, "x": x},
                      {"cdr_seaice_conc_monthly": (("time", "y", "x"), conc, vattrs)},
                      attrs={**gattrs, "comment": f"test fixture: every {k}th pixel of {name}",
                             "disclaimer": DISCLAIMER},
                      scalars={"crs": crs})
        meta = _source(p.name, e, f"cdr_seaice_conc_monthly of {name} at every {k}th x and y starting at "
                                  f"index {k // 2} (100 km, {len(y)} x {len(x)}), uint8 as stored; x, y, "
                                  "time and the CF polar_stereographic crs kept; netCDF-4 written with h5py",
                       {"source_file": name, "source_sha256": pin.sha256, "source_url": pin.url,
                        "units": "1", "sha256": sha256_file(p)})
        (out / f"{p.stem}.source.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        last = p
    return last


MAKERS = {
    "gpcp-v23-ltm-1991-2020": make_gpcp,
    "nsidc-cdr-v6-seaice-minimum-1991-2020": make_nsidc,
    "mod17a3-npp-mean-2000-2015": make_npp,
    "modis-aqua-chla-2013-2024": make_chla,
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

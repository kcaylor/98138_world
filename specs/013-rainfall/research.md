# Research: Rainfall map (013)

Not affiliated with or endorsed by The LEGO Group.

## Prototype summary (read-only, outside the repository)

`proto-rain/NOTES.md` ("Approved design: round 3A"), `SOURCES.md`, `scripts/rain.py`, `rain2.py`,
`rain3.py`, `round3/3A-darkblue.png`, `round3/stats3.json`. GPCP v2.3 LTM 1991–2020
(`precip.mon.ltm.1991-2020.nc`, 677,810 bytes, SHA-256 `e72475e6…6281c`, netCDF-4) converted
locally to netCDF-3 for the prototype (not pinned: owner decision 1). Bilinear sampling
(`rain2.py`), ice sheets (`rain.py`: Antarctica = land with centre latitude < -60; Greenland =
land with lat > 59, -75 < lon < -10, excluding lon > -26 and lat < 67), sea ice from the
living-planet chlorophyll rule (`rain2.py`), round-3 ocean colors (`rain3.py`, variant 3A).
Prototype counts (stats3.json): land White 711, Lime 588, Sand Green 416, Bright Green 380, Dark
Tan 355, Green 352, Tan 260; ocean Dark Azure 2,032, Blue 1,800, Medium Azure 993, White 738,
Bright Light Blue 656, Dark Blue 567, Black 392; 8,143 pieces beyond one kit. Decoding the PNG
(cell centres, nearest part color, max RGB distance 11) reproduces these counts exactly; that
grid is the acceptance reference.

## R1. netCDF-4 reader

h5py (BSD-3-Clause) reads HDF5 directly; no netCDF-C library. h5py 3.16.0 (2026-03-06) has
CPython 3.11 wheels for macOS (x86_64, arm64), manylinux_2_28 (x86_64, aarch64) and musllinux;
the Docker builder (python:3.11-slim, Debian bookworm, glibc 2.36) uses the manylinux wheel. It
needs only numpy ≥ 1.21.2 (project pins numpy ^1.24). Pinned `h5py = "^3.16.0"` in
`pyproject.toml` and `h5py==3.16.0` in `web/requirements-build.txt`.

h5py returns stored values: CF decoding (fill, missing, valid range, packing) is done by the
reader, mirroring `_clean` for netCDF-3. GPCP: `precip(12, 72, 144)` float32, `missing_value`
-9.96921e36, `valid_range` [0, 100], scale 1, offset 0; lat descending. ERSST v5 per-month
files: `ssta(time=1, lev=1, lat, lon)`; the reader drops the size-1 axes; a test converts the
committed netCDF-3 ERSST fixtures to netCDF-4 with h5py and compares. NSIDC: `uint8`, `_FillValue`
255, `valid_range` [0, 100], scale 0.01 (flags 251–254 fall outside the valid range).

Routing: by the registry `format` (`netcdf4`); `read_netcdf3` still rejects an HDF5 signature
(feature 009 behaviour), and `read_netcdf4` rejects netCDF-3 signatures by name.

## R2. Sea-ice source and rule

Candidates (checked 2026-11-22):

- NSIDC-0192 (Sea Ice Trends and Climatologies) and NSIDC-0051: climatologies, but Earthdata
  login (credentials) — rejected (reserved decision avoided).
- NOAA@NSIDC public HTTPS (`noaadata.apps.nsidc.org`, no login): G02135 Sea Ice Index (monthly
  concentration GeoTIFFs per month and year; median extent only as polylines) and G02202 CDR V6
  (per-month netCDF-4 files, 25 km polar stereographic; per-year daily aggregates of 70–100 MB;
  a whole-record monthly aggregate `sic_psn25_197811-202610_v06r00.nc`, 119 MB, whose name and
  bytes change every month — not pinnable).
- PolarWatch/CoastWatch ERDDAP no longer serve the G02202 monthly datasets (404).

Chosen: G02202 V6 per-month files for each hemisphere's minimum month (September north, February
south), 1991–2020 (matches the GPCP normal): 60 files, 17,826,152 bytes in total, versioned
v06r00, each pinned by SHA-256; all 60 matched NSIDC's published MD5 manifests (`checksums/`).

Rule exploration (the whole-record aggregates downloaded once to scratch, not pinned), against the
prototype's sea-ice cells (ocean, not shadow, White; 738 cells, 689 north / 49 south):

| rule (cell mean of 1991–2020 climatology) | cells | agree (of 6,786) |
|---|---|---|
| annual mean ≥ 0.5 | 1,433 | 6,087 |
| minimum month ≥ 0.15 | 1,060 | 6,436 |
| minimum month ≥ 0.7, + no pixel poleward of 60° | 753 | 6,711 |
| Sep / Feb ≥ 0.6, + no pixel poleward of 60° | 806 | 6,692 |
| **Sep / Feb ≥ 0.7, + no pixel poleward of 60°** | **759** | **6,705** |
| Sep / Feb ≥ 0.8, + no pixel poleward of 60° | 720 | 6,694 |

The prototype's rule (never or rarely observed by MODIS) marks ice that survives the summer, so
seasonal-ice rules (annual mean, 15% extent) overshoot (Hudson Bay, Okhotsk, Weddell pack). The
stated-month rule is nearly as close as the 12-month minimum and needs 60 files instead of 720.
"No pixel" cells (173 poleward of 60°, of which the prototype has 168 as ice) are kit ocean cells
whose NSIDC pixels are all land, coast or ice shelf (e.g. the Ross and Ronne shelves); treating
them as ice mirrors living-planet's `unobserved` rule.

## R3. Polar stereographic coordinates

Snyder (1987), Map Projections — A Working Manual, USGS PP 1395, pp. 160–162 (ellipsoidal polar
stereographic, inverse with a standard parallel; south aspect by sign reversal). With the files'
CF `crs` (Hughes 1980 ellipsoid, a = 6,378,273 m, 1/f = 298.27941112; north lat_ts 70, lon_0 -45;
south lat_ts -70, lon_0 0) the computed grids match NSIDC's ancillary latitude/longitude
(`G02202-ancillary-ps{n,s}25-v06r00.nc`) to 3.0e-10° in latitude and 6e-14° in longitude.
Unit tests use reference points from those files.

## R4. Multi-file entries

A registry `files` list keeps one entry (one id, one citation, one row in `dataset list`) for the
60 files; the alternative, 60 entries plus a composite, would put 60 rows into every citation
list. Cache directory = the entry's version directory. Provenance carries a checksum over the
file manifest so a layout records exactly which files it used.

## R5. Overrides

The ice sheets are a region rule (no dataset), sea ice a dataset rule. One `override` table type
covers both and other uses (e.g. a lake, a glacier mask). Bounds are on kit cell centres in kit
coordinates (arrangement A), like the other per-cell work; overrides are rolled with the classes.

## R6. Bilinear sampling

As `rain2.py`: cell centres from `KitProjection.cell_center`; `fy = (lat - lat0) / dlat`, clamped to
[0, n-1]; `y0 = clip(floor(fy), 0, n-2)`; `fx = (lon - lon0) / dlon`, periodic. GPCP has no
missing values, so no corner is dropped and no cell is filled.

## R7. Fixtures

`gpcp_v23_ltm_10deg.nc` (netCDF-4, 12 × 18 × 36, every 4th GPCP cell), and two NSIDC files per
hemisphere (1991 and 2020) at every 4th pixel (x/y kept, crs copied), all written by
`tools/fixtures004/make_fixtures.py` with h5py (`tools/fixtures004/nc4.py`, no stored times, so
regeneration is byte-identical). 513,576 bytes in all; budget raised from 450 kB to 540 kB.

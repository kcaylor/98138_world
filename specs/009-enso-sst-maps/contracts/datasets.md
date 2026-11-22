# Contract: registry entries and reader (009)

## `data/datasets.json` — two new rows (appended after `ersst-v5-ltm-1991-2020`)

```json
{
  "id": "ersst-v5-1997-12",
  "version": "v5-1997-12",
  "kind": "download",
  "title": "NOAA ERSST v5 sea surface temperature anomaly, December 1997 (strong El Niño)",
  "publisher": "NOAA National Centers for Environmental Information (NCEI)",
  "url": "https://www.ncei.noaa.gov/pub/data/cmb/ersst/v5/netcdf/ersst.v5.199712.nc",
  "size": 134832,
  "sha256": "9f96dbe3aadf8b261e607a8337de02425c65e67803929c592bf1271b2c4e9ebe",
  "format": "netcdf3",
  "filename": "ersst.v5.199712.nc",
  "variables": {
    "ssta": {"units": "degC",
             "description": "sea surface temperature anomaly against the 1971-2000 climatology (the file's climatology attribute)"}
  },
  "grid": {"registration": "node", "resolution_deg": 2.0, "lat": [-88, 88], "lon": [0, 358]},
  "class_rule": {"missing_is_land": true},
  "license": "Public domain (U.S. Government work, NOAA NCEI); the file's license attribute reads 'No constraints on data access or use'",
  "citation": "Huang, B., P. W. Thorne, V. F. Banzon, T. Boyer, G. Chepurin, J. H. Lawrimore, M. J. Menne, T. M. Smith, R. S. Vose, and H.-M. Zhang, 2017: Extended Reconstructed Sea Surface Temperature, Version 5 (ERSSTv5): Upgrades, Validations, and Intercomparisons. J. Climate, 30, 8179-8205. Dataset: Huang, B., et al., 2017: NOAA Extended Reconstructed Sea Surface Temperature (ERSST), Version 5. NOAA National Centers for Environmental Information, doi:10.7289/V5T72FNM.",
  "doi": "10.1175/JCLI-D-16-0836.1",
  "notes": "netCDF-3 classic (per-month NCEI files before 2010; later months are netCDF-4), ssta(time=1, lev=1, lat=89, lon=180) float32, _FillValue -999 over land and missing cells. date_modified 2017-06-30T12:18:00Z. Dataset DOI: 10.7289/V5T72FNM. Niño 3.4 mean anomaly +2.28 °C."
}
```

`ersst-v5-1988-12` is identical except: `version` `v5-1988-12`; `title` "NOAA ERSST v5 sea surface
temperature anomaly, December 1988 (strong La Niña)"; `url` `…/ersst.v5.198812.nc`; `filename`
`ersst.v5.198812.nc`; `sha256`
`f6d21ff447213c6abd32ee32bb1a4a26b5d847a5abb3dee33baed3f250bb14db`; notes end "Niño 3.4 mean
anomaly −1.97 °C."

Registry format, `registry_version` "1" and validation rules (`datasets/registry.py`
`parse_entry`) are unchanged. `dataset list`, `dataset fetch <id>`, `dataset fetch --recipe <id>`,
`dataset verify` work on the new rows with no code change.

## Fetch and cache (unchanged behaviour, FR-004)

- `dataset fetch ersst-v5-1997-12` / `map build ocean-el-nino --fetch`: the only network use;
  streams, checks size then SHA-256, exit 4 on mismatch (`ChecksumMismatchError`), part file
  removed.
- `map build ocean-el-nino` without `--fetch` and no cache: exit 3, `Dataset ersst-v5-1997-12 is not
  cached. Fetch it with: lego-image-processor dataset fetch ersst-v5-1997-12 (or rerun map build
  with --fetch)`; no network access.

## Reader `read_netcdf3(path, variable, reduce=None)`

| Input | Result |
|---|---|
| signature `CDF\x01`/`CDF\x02` | read |
| signature `\x89HDF` | `ValueError: <path>: not a netCDF-3 classic file (netCDF-4/HDF5 signature); this reader reads netCDF-3 only` |
| other signature | `ValueError: <path>: not a netCDF-3 classic file` |
| `ssta(time=1, lev=1, lat, lon)` | 2-D field (size-1 leading axes dropped) |
| `(lat, lon)`, `(1, lat, lon)` | as before |
| `(12, lat, lon)` + `reduce="annual-mean"` | as before (NaN where any month missing) |
| `(time=2, lev=1, lat, lon)`, no reduce | `ValueError: <path>: ssta has leading axes time=2, lev=1; declare a reduce rule` |
| `_FillValue` −999 (float or packed int16) | NaN before scale/offset |
| `scale_factor`, `add_offset` | applied after fill masking |

In `map build`/`map check`, a reader `ValueError` becomes `Cannot build <recipe>: <cls>: cannot read
<dataset id>: <message>` with exit 1 (via `MapBuildError`).

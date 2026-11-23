# Contract: recipe keys and registry fields added by feature 013

All additions are optional; recipes and registry rows without them behave exactly as before.
Not affiliated with or endorsed by The LEGO Group.

## Registry (`data/datasets.json`)

### `format = "netcdf4"`

netCDF-4/HDF5 files, read with h5py (`datasets/netcdf4.py`). Variable spec keys as for netCDF-3
(`units`, `description`, `reduce`). `reduce` may be `annual-mean` or `climatology-mean`.
`content_sha256` stays netCDF-3 only.

Decoding, in order: values equal to `_FillValue` or `missing_value`, outside `valid_range` /
`valid_min` / `valid_max` (compared on stored values), or below -1e30 become missing; then
`scale_factor` and `add_offset`. Leading axes of size 1 are dropped.

Coordinates: 1-D `lat`/`latitude` and `lon`/`longitude` at the root (a regular grid), else 1-D
`x` and `y` with the variable's `grid_mapping` naming a CF `polar_stereographic` variable
(`latitude_of_projection_origin` ±90, `standard_parallel`, `straight_vertical_longitude_from_pole`,
`semi_major_axis`, `inverse_flattening` or `semi_minor_axis`, `false_easting`/`false_northing`):
latitude/longitude are computed per pixel and the result is a **points** grid. Anything else is an
error naming the variable.

### `files` (multi-file download entries)

```json
"files": [{"url": "https://…/a.nc", "size": 123, "sha256": "…"}, …]
```

- At least 2 items; each `url` https (or `http_only` rules as for `url`), `size` > 0, `sha256` 64
  hex; file names (URL basenames) unique.
- The entry has no `sha256`/`content_sha256`; `size` is the total of the files; `url` is an
  informational https base (directory) URL; `filename` is not used.
- Cache: `<root>/datasets/<id>/<version>/<basename>` per file. Cached = every file present with
  its size. `resolve` returns the directory after verifying every file (size and SHA-256).
  `fetch` downloads missing or invalid files only.
- Reading: every file is read; with `reduce = "climatology-mean"` each pixel is the mean of its
  valid values over the files on the same grid (`counts` = valid files, `steps` = files); grids
  of different shapes or coordinates are concatenated as points.
- Provenance adds `files` (count) and `files_sha256`: SHA-256 of the lines
  `"<sha256>  <basename>\n"` in list order.

## Recipe (format "1")

### `sampling` (data layers)

`"mean"` (default; the cell mean with nearest fill, unchanged) or `"bilinear"`. Bilinear is not
allowed with `method = "categorical"` and needs a regular grid with even spacing (checked when
building). Reported in the layer provenance only when not `"mean"`.

### `[[<layer>.override]]` (data layers, repeatable)

| key | rule |
|---|---|
| `name` | required, non-empty string, unique within the layer |
| `color` | required, a color of the layer's part |
| `lat_min`, `lat_max`, `lon_min`, `lon_max` | region bounds, degrees (cell centre strictly inside: `lat > lat_min`, `lat < lat_max`, …); longitude in -180..180 |
| `exclude` | list of tables with the same four bounds; a cell inside any is left out |
| `dataset`, `variable` | dataset rule: a registry id and its variable |
| `min_value` | dataset rule: the cell's value (mean of the dataset's valid points/pixels in the cell) ≥ `min_value` |
| `unobserved_lat` | dataset rule, optional: cells with no valid point and \|centre latitude\| > this |

An override is a region (at least one bound, no dataset keys) or a dataset rule (`dataset`,
`variable`, `min_value`; no bounds). Cells: the layer's cells not already taken by the shadow,
`no_data` or an earlier override. Override cells take `color` and are left out of the
classification; one kit's supply of that color is reduced by their count. The report layer and
the layout metadata layer gain `overrides: [{name, kind ("region" | "dataset"), color, cells}]`.
A dataset override's dataset is one of the recipe's datasets (fetched, cited).

### `[<layer>.legend]` (data layers)

`units` (non-empty string) and `factor` (number > 0). The report layer gains
`legend: {units, factor}`; the CLI legend prints `0.5 to 1 (182.5 to 365 mm/yr)`.

## Recipe `rainfall`

Land `gpcp-v23-ltm-1991-2020` `precip`, bilinear, bins `[0, 0.5, 1, 1.5, 2.5, 4, 1000]`, six
colors; overrides Antarctica (`lat_max = -60`) and Greenland (`lat_min = 59`, `lon_min = -75`,
`lon_max = -10`, `exclude = [{lat_max = 67, lon_min = -26}]`), White. Ocean same variable,
bilinear, bins `[0, 0.75, 1.5, 3, 5, 1000]`, five colors; override sea ice
(`nsidc-cdr-v6-seaice-minimum-1991-2020`, `cdr_seaice_conc_monthly`, `min_value = 0.7`,
`unobserved_lat = 60`), White. Legend `mm/yr`, factor 365 on both. `[shadow] color = "lego_black"`.

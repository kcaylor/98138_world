# Contract: data files (004)

## `data/kit_31203_projection.json`

```json
{
  "kit": "31203",
  "model": "equirectangular",
  "width": 128, "height": 80,
  "left_edge_lon": -168.9, "deg_per_col": 2.8125,
  "equator_row": 42.2, "rows_per_radian": 26.3,
  "agreement": {"equirectangular": 0.942, "miller": 0.909, "mercator": 0.870},
  "source": {
    "method": "land fraction >= 0.5 per cell vs kit mask; lon from column profile, rows by grid search",
    "mask": "lego_world_map_land_sea_mask.json",
    "dataset": {"id": "etopo2022-surface-10m", "sha256": "575c7a0c..."},
    "generator": "tools/kit31203 fit-projection",
    "generated_on": "YYYY-MM-DD",
    "disclaimer": "Not affiliated with or endorsed by The LEGO Group."
  }
}
```
Values are fitted at implement time by `fit-projection`; research R2 numbers are expected.

## `data/datasets.json`

```json
{
  "registry_version": "1",
  "datasets": [
    {"id": "etopo2022-surface-10m", "version": "2022-v1-60s-stride10", "kind": "download",
     "title": "ETOPO 2022 surface elevation, 10 arc-minute subset of the 60 arc-second grid",
     "publisher": "NOAA National Centers for Environmental Information",
     "url": "https://www.ngdc.noaa.gov/thredds/dodsC/global/ETOPO2022/60s/60s_surface_elev_netcdf/ETOPO_2022_v1_60s_N90W180_surface.nc.dods?z%5B0:10:10799%5D%5B0:10:21599%5D",
     "size": 9357398,
     "sha256": "575c7a0c84f18b41430a723f26475fa41b1d787c94fa641f0d0705291e3991fd",
     "format": "dods", "filename": "etopo2022_surface_10m.dods",
     "variables": {"z": {"units": "m", "description": "surface elevation (EGM2008), positive up"}},
     "class_rule": {"split_at": 0.0},
     "license": "Public domain (U.S. Government work, NOAA NCEI)",
     "citation": "NOAA National Centers for Environmental Information. 2022: ETOPO 2022 15 Arc-Second Global Relief Model.",
     "doi": "10.25921/fd45-gt74", "notes": "..."},
    {"id": "ersst-v5-ltm-1991-2020", "version": "v5-ltm-1991-2020", "kind": "download",
     "url": "https://downloads.psl.noaa.gov/Datasets/noaa.ersst.v5/sst.mon.ltm.1991-2020.nc",
     "size": 1160004,
     "sha256": "b4f20ecfbf5e4c9276ff9e72adbf6205663e9efd64a3b1e74a0fcd2b3c72e99f",
     "format": "netcdf3", "filename": "sst.mon.ltm.1991-2020.nc",
     "variables": {"sst": {"units": "degC", "reduce": "annual-mean"}},
     "class_rule": {"missing_is_land": true},
     "license": "Public domain (NOAA)",
     "acknowledgement": "NOAA ERSST V5 data provided by the NOAA PSL, Boulder, Colorado, USA, from their website at https://psl.noaa.gov",
     "citation": "Huang, B., et al., 2017: Extended Reconstructed Sea Surface Temperature, Version 5 (ERSSTv5). J. Climate, 30, 8179-8205.",
     "doi": "10.1175/JCLI-D-16-0836.1"},
    {"id": "kit31203-design", "version": "003", "kind": "packaged", "format": "kit-design",
     "title": "Official LEGO 31203 design grid", "class_rule": {"kit_mask": true},
     "license": "Facts extracted from the official building instructions (see kit_31203_design.json source)",
     "citation": "LEGO 31203 World Map building instructions (pinned PDF, see source block)"}
  ],
  "disclaimer": "Not affiliated with or endorsed by The LEGO Group."
}
```

Rules: ids unique; `download` entries need https `url`, `size`, `sha256`, `filename`; `license`
and `citation` required for all.

## `data/part_colors.json` (Q4)

Same `source` + `citations` structure as `kit_colors.json` (citation ids resolve), plus the
snapshot checksums of the catalog files used:

```json
{"source": {"title": "...", "snapshots": [{"id": "rebrickable-elements", "url": "...", "sha256": "...", "accessed": "YYYY-MM-DD"}], "citations": [...], "disclaimer": "..."},
 "parts": {"6141": [{"key": "lego_bright_green", "element_id": "...", "lego": {"name": "...", "id": 37},
                     "bricklink": {"name": "...", "id": 36}, "rebrickable": {"name": "Bright Green", "id": 10},
                     "rgb": [75, 159, 74], "in_kit": false, "citations": {...}}],
           "98138": [...]}}
```
Kit colors must match `kit_colors.json` exactly (key, IDs, element ID).

## Layout `metadata.map` (Q3)

Additive key inside `metadata` of a schema 2.0 layout; `schema_version` stays `"2.0"`;
`source_image` = `recipe:<id>`.

```json
"map": {
  "recipe": {"id": "ocean-sst", "format": "1", "title": "...", "sha256": "..."},
  "layers": [
    {"class": "land", "role": "background", "colors": ["lego_white"]},
    {"class": "ocean", "role": "data", "variable": "sst", "classification": "rank-to-supply",
     "dataset": {"id": "ersst-v5-ltm-1991-2020", "version": "...", "sha256": "...",
                 "license": "...", "citation": "...", "doi": "..."}}],
  "seed": 31203, "tool_version": "0.x", "disclaimer": "Not affiliated with or endorsed by The LEGO Group."
}
```

## Suitability report JSON

`{"recipe_id", "layers": [...], "thresholds": {"variance_lost": 0.5, "filled_share": 0.05,
"min_delta_e00": 5.0}, "citations": [...], "generated_at", "disclaimer"}` (fields per
data-model.md).

## Test fixtures (`cli/tests/fixtures/datasets/`)

Derived, small, public-domain sources only, each with `<name>.source.json` (dataset id, sha256 of
the source file, method, license, generator).

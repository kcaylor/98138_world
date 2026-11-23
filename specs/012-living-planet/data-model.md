# Data model: Living planet map (012)

## DatasetEntry (registry row; extended)

| Field | Rule |
|---|---|
| `format` | adds `"geotiff"` (strip GeoTIFF, one band) |
| `grid.block` | geotiff only; integer ≥ 1 (default 1); output cell = mean of valid pixels in a block |
| `variables.<v>.scale_factor`, `add_offset`, `valid_min`, `valid_max`, `fill` | numbers (geotiff decoding) |
| `variables.<v>.reduce` | adds `"climatology-mean"` (netcdf3 only) |
| `http_only` | non-empty reason; allowed only with an `http://` URL; requires `sha256` |
| `content_sha256` | 64 hex; netcdf3 only; download entries have exactly one of `sha256`, `content_sha256` |
| `class_rule.land_from` | `{dataset, variable, split_at}`; `dataset` is another registry id, itself a plain grid |

Derived: `mask_dataset_id` (the `land_from` dataset), `splits_land` (class rule present, not
`kit_mask`). `provenance()` adds `content_sha256` when set.

## SourceGrid (extended)

| Field | Meaning |
|---|---|
| `counts` | valid steps per pixel (`climatology-mean`), int, same shape as `values` |
| `steps` | number of steps on the reduced axis |
| `missing` | class pixels that had no value before `no_data.value` was applied |

`extend_latitudes(grid, south, north)` pads a regular grid with missing rows (land False, counts 0).

## Recipe: Layer.no_data → NoData

| Field | Rule |
|---|---|
| `color` | required; a color of the layer's part |
| `rule` | `unobserved` or `share` |
| `min_lat` | required; 0–90 |
| `value` | optional; needs `dataset.splits_land`; > 0 with `log10` |
| `min_share` | `share` only, required, 0 ≤ x < 1 |
| `sparse_lat`, `min_steps` | `unobserved` only, together; `min_lat ≤ sparse_lat ≤ 90`, integer ≥ 1; needs `climatology-mean` |

`Layer.transform` adds `log10`; with `bins`, `Classification.bounds` hold log10 of the recipe's
bounds (which must be > 0).

## Build outputs

- Class `NO_DATA_CLASS = -2` in `MapResult.classes[cls]` for no-data cells.
- Report layer: `no_data` (`NoData.provenance(cells)`), `transform` (log10 only), `class_bounds`
  and `median_by_color` in data units for log10, `cells` = classified cells, supply rows count the
  no-data color.
- Layout `metadata.map.layers[i]`: `no_data`, `land_from` (when the dataset has one).

Not affiliated with or endorsed by The LEGO Group.

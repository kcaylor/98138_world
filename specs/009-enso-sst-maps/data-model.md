# Data Model: ENSO SST Anomaly Maps (009)

Existing entities (`DatasetEntry`, `Recipe`, `Layer`, `Classification`, `Arrangement`, layer
report) are extended; no new persistent format. Not affiliated with or endorsed by The LEGO Group.

## DatasetEntry (registry row, `data/datasets.json`) — two new rows

| Field | `ersst-v5-1997-12` | `ersst-v5-1988-12` | Rule |
|---|---|---|---|
| `id` | `ersst-v5-1997-12` | `ersst-v5-1988-12` | `^[a-z0-9][a-z0-9.-]{0,63}$`, unique |
| `version` | `v5-1997-12` | `v5-1988-12` | non-empty; cache path `datasets/<id>/<version>/<filename>` |
| `kind` | `download` | `download` | download entries need url, size, sha256, filename |
| `url` | NCEI `.../ersst.v5.199712.nc` | `.../ersst.v5.198812.nc` | https |
| `size` | 134832 | 134832 | positive int, checked before SHA-256 |
| `sha256` | `9f96dbe3…2c4e9ebe` | `f6d21ff4…50bb14db` | 64 lowercase hex (full values in research R4) |
| `format` | `netcdf3` | `netcdf3` | reader checks the netCDF-3 signature |
| `variables` | `{"ssta": {"units": "degC", "description": …}}` | same | no `reduce` (singleton axes are dropped) |
| `class_rule` | `{"missing_is_land": true}` | same | NaN after fill = land (FR-001) |
| `grid` | node, 2°, lat [−88, 88], lon [0, 358] | same | informational |
| `license`, `citation`, `doi`, `publisher`, `title`, `notes` | see contracts/datasets.md | | citation carries the dataset DOI (R4) |

Relationship: referenced by exactly one recipe each (`ocean-el-nino` → 1997-12, `ocean-la-nina` →
1988-12). The 2026–27 swap adds a third entry and changes `ocean-el-nino`'s `dataset` and title.

## SourceGrid read rule (reader behaviour, `datasets/readers.py`)

- Input variable shape `(d0, …, dk, lat, lon)`; axes `d0..dk` of size 1 are dropped (FR-002).
- After dropping: 2-D → field; 3-D → existing `reduce` rule (`annual-mean` with 12 steps) or error;
  otherwise error naming the dimensions and sizes.
- `_FillValue`/`missing_value` (−999 here) and values below −1e30 → NaN, before scale/offset
  (FR-003). `scale_factor`/`add_offset` applied (the fixtures use 0.01 / 0).
- File signature must be `CDF\x01` or `CDF\x02`; `\x89HDF` → "not a netCDF-3 classic file
  (netCDF-4/HDF5 signature)".
- Read errors reach the CLI as `MapBuildError` (exit 1).

## Recipe (`maps/recipe.py`) — new optional field

| Field | Type | Rule |
|---|---|---|
| `arrangement` | `Optional[Arrangement]` | top-level TOML key; absent → None (built as A unless overridden); string accepted by `parse_arrangement` (A/B/C any case, `europe-africa`, `americas`, `asia-australia`); anything else → `RecipeError` at path `arrangement` listing the valid values. Format stays "1". Included in the recipe SHA-256 (raw bytes) like every key. |

## ArrangementResolution (`maps/build.py`, not persisted in the layout)

`resolve_arrangement(recipe, arrangement=None) -> (Arrangement, source)`

| Input | Result | `source` |
|---|---|---|
| `arrangement` given (CLI `--arrangement`, library argument) | that arrangement | `option` |
| none given, `recipe.arrangement` set | recipe's | `recipe` |
| neither | A | `default` |

Written to the report as `arrangement` (the existing record) and `arrangement_source`; the layout's
`metadata.arrangement` is unchanged (SC-006).

## Shared legend (ENSO recipes' ocean layer)

| Field | Value | Rule |
|---|---|---|
| `colors` | 9 kit colors, `ocean-sst` order (research R1) | identical list in both recipes (SC-003); all part 98138 kit colors (SC-005) |
| `classification.method` | `bins` | |
| `classification.bounds` | `[-9, -1.5, -0.5, -0.25, -0.1, 0.1, 0.3, 0.5, 1.0, 9]` | n+1 = 10, strictly increasing; identical in both recipes; zero lies in class 4 (Bright Yellowish Green), the middle of 9 (FR-006) |
| `texture` | absent (`none`) | no `blend` (FR-008) |
| class membership | `[b_i, b_{i+1})`, end classes open (values < −1.5 → class 0, ≥ +1.0 → class 8) | `classify.py` searchsorted on inner bounds |

## Report (`maps/build.py`, `maps/suitability.py`)

| Field / function | Type | Meaning |
|---|---|---|
| report `arrangement_source` | `recipe` \| `option` \| `default` | new, additive (FR-012; escalated for sign-off) |
| layer `supply` (existing) | rows `key, used, supplied, within, in_kit` | `used` includes the shadow for the ocean layer |
| layer `class_bounds` (existing) | list | rendered as °C ranges in output (FR-015) |
| `extra_tiles(supply_rows)` | function → int | Σ `max(0, used − supplied)`; non-kit colors count in full; not stored |
| legend units | from the recipe layer's registry variable `units` | `degC` → `°C`; not stored |

Validation: `extra_tiles(ocean supply)` equals `parts list --kits 1` `to_buy` for part 98138 with
no spares/owned/missing inputs (FR-016, SC-004); it is 0 for the land layer of both maps.

## Fixture (test data, `cli/tests/fixtures/datasets/`)

| Field | Value |
|---|---|
| files | `ersst_v5_199712_ssta.nc`, `ersst_v5_198812_ssta.nc` + `.source.json` each |
| structure | netCDF-3 classic; dims `time=1, lev=1, lat=89, lon=180`; coords `time, lev, lat, lon`; `ssta` int16, `scale_factor 0.01`, `add_offset 0`, `_FillValue -999`, `units degree_C` |
| `.source.json` | fixture, dataset, version, source_sha256, source_url, method, license, citation, doi, generator, disclaimer, units, sha256 |
| budget | all fixtures < 300,000 bytes (`test_no_large_data.py`) |

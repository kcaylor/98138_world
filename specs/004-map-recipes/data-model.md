# Data Model: Map Recipes and Canonical Datasets (004)

Python dataclasses (frozen unless noted). File shapes are in `contracts/`.

## Recipe

| Field | Type | Rules |
|---|---|---|
| `format` | str | `"1"`; any other value is rejected naming the supported version |
| `id` | str | `^[a-z0-9][a-z0-9-]{1,63}$`; unique among bundled recipes |
| `title`, `description` | str | title required |
| `seed` | int | default 31203; used by every texture in the recipe |
| `land`, `ocean` | Layer | both required |
| `sha256` | str | of the recipe file bytes (computed, not written in the file) |
| `path` | Path | where it was read from |

## Layer

| Field | Type | Rules |
|---|---|---|
| `cls` | `"land"` \| `"ocean"` | from the table name |
| `role` | `"data"` \| `"background"` | required |
| `part_id` | str | derived: land `6141`, ocean `98138` (never in the file) |
| `dataset` | DatasetRef | data role only |
| `variable` | str | data role; must exist in the dataset entry |
| `transform` | `"none"` \| `"negate"` | data role; default none |
| `classification` | Classification | data role |
| `colors` | tuple[str] | ordered color keys; each available for `part_id` (PartColorTable) |
| `weights` | tuple[float] | background only; same length as colors, > 0 |
| `texture` | Texture | optional; default none |

Data role: `len(colors)` = number of classes. Background role: no dataset/classification.

## Classification

| method | parameters | rules |
|---|---|---|
| `bins` | `bounds`: n+1 floats | strictly increasing; n = len(colors) |
| `quantile` | — | equal counts |
| `rank` | `shares`: n positive numbers | normalised; largest-remainder rounding |
| `rank-to-supply` | — | shares = one kit's supply per color; every color must be a kit color of the part; fails if cells > total supply |
| `categorical` | `categories`: map source category → color key | every source category present must be mapped |

Ordered methods: value order → class order (ties broken row-major).

## Texture

| kind | parameters | rules |
|---|---|---|
| `none` | — | |
| `blend` | `width` 0–0.5 (fraction of a class) | data layers; moves ≤ 1 class; rank methods swap in pairs |
| `mix` | `cluster` ≥ 0 (studs, Gaussian sigma) | background layers; exact counts by weight |

## DatasetEntry (registry)

| Field | Type | Rules |
|---|---|---|
| `id`, `version`, `title`, `publisher` | str | id unique |
| `kind` | `"download"` \| `"packaged"` \| `"local"` | packaged = shipped (the official design grid); local = from a recipe (Q6) |
| `url` | str | download only; https |
| `size` | int | exact bytes (download) |
| `sha256` | str | 64 lowercase hex |
| `format` | `"dods"` \| `"netcdf3"` \| `"npy"` \| `"kit-design"` | |
| `filename` | str | cache file name |
| `variables` | map name → {units, description, reduce} | `reduce`: `annual-mean` for 12-month climatologies |
| `class_rule` | `{"split_at": 0.0}` \| `{"missing_is_land": true}` \| `{"kit_mask": true}` | which source values are land vs ocean |
| `license`, `citation`, `doi`, `acknowledgement`, `notes` | str | license and citation required |

## CachedDataset

`entry`, `path` (`<root>/datasets/<id>/<version>/<filename>`), `verified` (bool). State:
absent → (fetch) `.part` → (size + SHA-256 ok) cached → (each use) re-verified; mismatch at any
step → deleted, error with expected/actual.

## SourceGrid

`values` (2-D float, NaN = missing), `lat` (1-D, ascending after normalisation), `lon` (1-D,
normalised to −180..180 and sorted), `land` (2-D bool or None), `units`, `entry`.

## KitProjection (`data/kit_31203_projection.json`)

`model` (`"equirectangular"`), `left_edge_lon` (−168.9), `deg_per_col` (2.8125), `equator_row`
(42.2), `rows_per_radian` (26.3), `width` 128, `height` 80, `agreement` {model → fraction},
`source` (method, datasets used, date, tool, disclaimer). Rule: row = floor(equator_row −
rows_per_radian × radians(lat)); col = floor(((lon − left_edge_lon) mod 360) / deg_per_col).

## LayerField (computed)

`values` (80×128, NaN outside the layer's class), `samples` (count per cell), `filled` (bool mask
of nearest-filled cells), `within_var`, `total_var`.

## PartColor (`data/part_colors.json`)

`key`, `part_id` (`6141` | `98138`), `element_id`, `lego` {name, id}, `bricklink` {name, id},
`rebrickable` {name, id}, `rgb`, `in_kit` (bool), `citations` {field → citation id}. Rules as
`kit_colors.json`: no null IDs, no "estimate/placeholder" notes, unique (part, key); kit colors
must agree with `kit_colors.json`.

## SuitabilityReport

`recipe_id`, `layers[]` {cls, role, variance_lost, filled_share, class_counts, class_bounds,
min_neighbour_delta_e00 (pair), supply[] {key, used, supplied, within}, warnings[]}, `thresholds`,
`citations[]`, `disclaimer`.

## MapProvenance (layout `metadata.map`)

`recipe` {id, format, sha256, title}, `layers[]` {cls, role, dataset {id, version, sha256,
citation, license, doi}, variable, classification method}, `seed`, `tool_version`, `disclaimer`.

## MapResult

`layout` (PositionPlacementGrid with provenance), `report` (SuitabilityReport), `classes`
(80×128 int class index per cell, for tests), `agreement` (optional, vs official design).

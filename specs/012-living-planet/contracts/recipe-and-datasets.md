# Contract: recipe and registry additions (feature 012)

Additive to `specs/004-map-recipes/contracts/recipe-format.md` and `data-files.md`. Recipe format
stays `"1"`; files that do not use the new keys parse and build exactly as before.

## Recipe: data layer keys

```toml
[ocean]
role = "data"
dataset = "modis-aqua-chla-2013-2024"
variable = "chlor_a"
transform = "log10"        # "none" | "negate" | "log10" (new): values <= 0 become missing
colors = ["lego_bright_blue", "lego_dark_azur", "lego_medium_azur",
          "lego_bright_bluish_green", "lego_earth_green"]

[ocean.classification]
method = "bins"
# With transform = "log10", bounds are in the variable's units (here mg m-3), all > 0, and are
# compared on log10; reports and the legend show them in the variable's units.
bounds = [0.001, 0.08, 0.15, 0.3, 1.0, 1000]

[ocean.no_data]            # optional, data layers only
color = "lego_white"       # required: a color of the layer's part (need not be in `colors`)
rule = "unobserved"        # "unobserved" | "share"
min_lat = 60               # required, 0..90 (degrees, absolute latitude)
sparse_lat = 70            # unobserved only, optional, with min_steps; >= min_lat
min_steps = 12             # unobserved only; integer >= 1; needs reduce = "climatology-mean"

[land.no_data]
value = 0                  # optional: class pixels with no value take this value
                           # (needs a dataset whose class rule splits land and ocean)
color = "lego_white"
rule = "share"
min_lat = 55
min_share = 0.5            # share only, required, 0 <= x < 1
```

Rules (errors name the key path):

- `no_data` on a background layer, unknown keys, `rule` outside the list, missing `color` /
  `min_lat`, `min_share` with `unobserved`, `sparse_lat`/`min_steps` with `share`, only one of
  `sparse_lat`/`min_steps`, a `color` not available for the part: `RecipeError`.
- `value` with a dataset that has no land/ocean split: `RecipeError` at `<layer>.no_data.value`.
- `min_steps` with a dataset variable whose `reduce` is not `climatology-mean`:
  `RecipeError` at `<layer>.no_data.min_steps`.
- `transform = "log10"` with bins and a bound <= 0: `RecipeError` at
  `<layer>.classification.bounds[i]`.

Semantics, per kit cell of the layer (after the land shadow, which wins):

- `unobserved`: the cell has no valid source value of the layer's class (it would be nearest-filled)
  and |cell-centre latitude| > `min_lat`; or |cell-centre latitude| > `sparse_lat` and the largest
  valid-step count among the source pixels in the cell is below `min_steps`.
- `share`: among the cell's source pixels of the layer's class, the share that had no value (before
  `value` is applied) and whose own latitude is poleward of `min_lat` exceeds `min_share`.
- No-data cells take `color`, are left out of the classification and its texture, and count in the
  layer's supply rows. Remaining cells with no value are nearest-filled as before.
- Layout `metadata.map.layers[i].no_data` and report `layers[i].no_data`:
  `{"rule", "color", "cells", "min_lat", ...parameters, "value"?}`.

## Registry (`data/datasets.json`)

- `format`: adds `"geotiff"`. `grid.block` (integer >= 1, default 1): block-mean on read.
  Variable spec keys for geotiff: `scale_factor`, `add_offset`, `valid_min`, `valid_max`, `fill`.
- Variable `reduce`: adds `"climatology-mean"` (netCDF-3): mean over valid steps of the leading
  axis; the grid carries `counts` and `steps`.
- netCDF-3 coordinates: `lat`/`lon` or `latitude`/`longitude`.
- `url`: `https://` required, unless `http_only` is a non-empty reason; such entries need `sha256`.
- `content_sha256` (download, netcdf3 only): replaces `sha256`; SHA-256 over the variable and its
  dimension coordinates as stored (name, NUL, dtype, NUL, shape, NUL, bytes, in order). `size` is
  still required and checked. Exactly one of `sha256` / `content_sha256` for download entries.
- `class_rule.land_from = {"dataset": <registry id>, "variable": <name>, "split_at": <number>}`:
  land where the nearest cell of that dataset's variable is > `split_at`. The mask dataset is part of
  every recipe that uses the entry (fetched with `--fetch`, cited in outputs).

## CLI output (`map build` / `map check`)

After a layer heading, when the layer has a no-data rule:
`  No data (<rule>): N cells of <color> (<parameters>), assigned before classification`.

Not affiliated with or endorsed by The LEGO Group.

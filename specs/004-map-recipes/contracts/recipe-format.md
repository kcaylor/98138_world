# Contract: recipe file (format 1, TOML, Q1)

A recipe is a UTF-8 TOML file. Unknown keys are errors. Errors name the key path
(e.g. `ocean.classification.bounds`) and the rule.

```toml
# Not affiliated with or endorsed by The LEGO Group.
format = "1"
id = "ocean-sst"
title = "Ocean temperature"
description = "Annual mean sea surface temperature, 1991-2020, on the kit's nine tile colors."
seed = 31203

[land]
role = "background"
colors = ["lego_white"]
weights = [1]

[ocean]
role = "data"
dataset = "ersst-v5-ltm-1991-2020"      # registry id, or a [ocean.local] table (Q6)
variable = "sst"
transform = "none"                       # "none" | "negate"
colors = ["lego_earth_blue", "lego_medium_azur", "lego_bright_bluish_green", "lego_bright_green",
          "lego_bright_yellowish_green", "lego_brick_yellow", "lego_flame_yellowish_orange",
          "lego_bright_orange", "lego_vibrant_coral"]   # cold -> warm

[ocean.classification]
method = "rank-to-supply"                # bins | quantile | rank | rank-to-supply | categorical
# bounds = [-2, 2, 6, 10, 14, 18, 22, 25, 28, 32]   (bins: len(colors)+1, increasing)
# shares = [392, 724, ...]                           (rank: len(colors) positive numbers)
# [ocean.classification.categories]                  (categorical: source value -> color key)

[ocean.texture]
kind = "blend"                           # none | blend (data) | mix (background)
width = 0.25                             # blend: fraction of a class, 0-0.5
# cluster = 2.0                          # mix: Gaussian sigma in studs, >= 0
```

## Rules

| Key | Rule |
|---|---|
| `format` | must be `"1"` |
| `id` | `^[a-z0-9][a-z0-9-]{1,63}$` |
| `land`, `ocean` | both present; `role` = `data` \| `background` |
| `colors` | non-empty; each key available for the layer's part (land 6141, ocean 98138) in the kit table or `part_colors.json` |
| background | `weights` same length as `colors`, all > 0; no `dataset`/`classification`; texture `none` or `mix` |
| data | `dataset`, `variable`, `classification` required; texture `none` or `blend` |
| `rank-to-supply` | every color must be a kit color of the part |
| `local` (Q6) | `[<layer>.local]` with `path`, `format` (`netcdf3`\|`npy`\|`dods`), `sha256`, `variable`, `citation`, `license`, and for `npy` `lat`/`lon` ranges; relative paths resolve against the recipe file |

## Bundled recipes

| id | Land | Ocean |
|---|---|---|
| `official-31203` | background White | data: `kit31203-design`, `categorical` (each design key → itself), no texture |
| `official-31203-bathymetry` | background White | data: `etopo2022-surface-10m` `z`, `negate`, `rank` with the official counts, colors in median-depth order (research R1), `blend` 0.25 |
| `ocean-sst` | background White | data: `ersst-v5-ltm-1991-2020` `sst`, `rank-to-supply`, cold → warm, `blend` 0.25 |
| `land-elevation` | data: `etopo2022-surface-10m` `z`, `bins` (m: 0, 200, 500, 1000, 1500, 2000, 3000, 4000, …) over plate colors green → brown → gray → white (research R9; final list fixed at implement by the suitability check) | background: kit tile colors (e.g. Medium Azur, Bright Bluish Green, Earth Blue), `mix` cluster 2, weights within one kit's supply |

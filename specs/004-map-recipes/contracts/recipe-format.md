# Contract: recipe file (format 1, TOML, Q1)

Feature 012 adds `transform = "log10"` and the optional `[<layer>.no_data]` table (format stays
"1"): see `specs/012-living-planet/contracts/recipe-and-datasets.md`.

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
kind = "blend"                           # none | blend (data) | mix | halo (background)
width = 0.25                             # blend: fraction of a class, 0-0.5
# cluster = 2.0                          # mix: Gaussian sigma in studs, >= 0

[shadow]                                 # optional (amendment 2026-11-22); these are the defaults
enabled = true
color = "lego_earth_blue"                # a 98138 tile color
direction = "east"                       # only "east"
```

A background ocean with a coastal halo (amendment 2026-11-22):

```toml
[ocean]
role = "background"
colors = ["lego_bright_bluish_green", "lego_medium_azur"]   # offshore base, coast ring; no weights

[ocean.texture]
kind = "halo"
inner = 1.5     # Euclidean distance from land (studs): ring color
outer = 3.0     # inner < d <= outer: ring color on an even Poisson-disk subset (seeded)
spacing = 2.0   # minimum spacing of that subset; beyond outer: base color
```

## Rules

| Key | Rule |
|---|---|
| `format` | must be `"1"` |
| `id` | `^[a-z0-9][a-z0-9-]{1,63}$` |
| `land`, `ocean` | both present; `role` = `data` \| `background` |
| `colors` | non-empty; each key available for the layer's part (land 6141, ocean 98138) in the kit table or `part_colors.json` |
| background | `weights` same length as `colors`, all > 0; no `dataset`/`classification`; texture `none`, `mix` or `halo` |
| `halo` | ocean background only; exactly two colors (base, ring); no `weights`; `inner` > 0, `outer` >= `inner`, `spacing` > 0 |
| `shadow` | optional top-level table; keys `enabled` (bool), `color` (98138 tile color), `direction` (`east`); unknown keys are errors |
| data | `dataset`, `variable`, `classification` required; texture `none` or `blend` |
| `rank-to-supply` | every color must be a kit color of the part |
| `local` (Q6) | `[<layer>.local]` with `path`, `format` (`netcdf3`\|`npy`\|`dods`), `sha256`, `variable`, `citation`, `license`, and for `npy` `lat`/`lon` ranges; relative paths resolve against the recipe file |

## Bundled recipes

| id | Land | Ocean |
|---|---|---|
| `official-31203` | background White | data: `kit31203-design`, `categorical` (each design key → itself), no texture; `[shadow] enabled = false` (the design grid already holds it) |
| `official-31203-bathymetry` | background White | shadow Earth Blue; data: `etopo2022-surface-10m` `z`, `negate`, `rank` with the official counts of the eight non-shadow colors, colors in median-depth order (research R1), `blend` 0.25 |
| `ocean-sst` | background White | shadow Earth Blue; data: `ersst-v5-ltm-1991-2020` `sst`, `rank-to-supply` (supply net of the shadow), cold → warm, `blend` 0.25 |
| `land-elevation` | data: `etopo2022-surface-10m` `z`, `bins` (m: 0, 200, 500, 1000, 1500, 2000, 3000, 4000, …) over plate colors green → brown → gray → white (research R9; final list fixed at implement by the suitability check) | background: Bright Bluish Green base with a Medium Azur `halo` (inner 1.5, outer 3.0, spacing 2.0) and the Earth Blue shadow (amendment 2026-11-22, replacing the owner's earlier 70/20/10 `mix`; it needs more Bright Bluish Green tiles than one kit holds, reported as beyond-kit) |

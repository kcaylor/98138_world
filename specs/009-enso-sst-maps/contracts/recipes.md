# Contract: bundled recipes `ocean-el-nino` and `ocean-la-nina` (009)

Files: `cli/src/lego_image_processor/maps/recipes/ocean-el-nino.toml` and `ocean-la-nina.toml`.
The `[ocean]` `colors` and `[ocean.classification]` blocks MUST be byte-identical between the two
files (SC-003 is tested on the parsed values).

## `ocean-el-nino.toml`

```toml
# Sea surface temperature anomaly in December 1997, a strong El Niño (NOAA ERSST v5 ssta, against
# the 1971-2000 climatology), hung as combination B (3·1·2) so the Pacific is whole. One fixed
# legend in °C, shared with ocean-la-nina, so the two boards compare tile for tile:
#   Earth Blue below -1.5 | Bright Bluish Green -1.5 to -0.5 | Medium Azur -0.5 to -0.25 |
#   Bright Green -0.25 to -0.1 | Bright Yellowish Green -0.1 to +0.1 | Brick Yellow +0.1 to +0.3 |
#   Flame Yellowish Orange +0.3 to +0.5 | Bright Orange +0.5 to +1.0 | Vibrant Coral +1.0 and above
# The outer bounds -9 and +9 only close the list (bins needs one more bound than colors); the end
# classes are open. Bounds chosen to keep tiles beyond one kit to a minimum (specs/009-enso-sst-maps
# research R1): about 1,114 extra ocean tiles; see `parts list <layout> --kits 1`.
# The land shadow (on by default) takes 390 Earth Blue tiles in combination B.
# Not affiliated with or endorsed by The LEGO Group.
format = "1"
id = "ocean-el-nino"
title = "El Niño, December 1997"
description = "Sea surface temperature anomaly in December 1997 (strong El Niño), °C against 1971-2000, Pacific-centred (B)."
seed = 31203
arrangement = "B"

[land]
role = "background"
colors = ["lego_white"]
weights = [1]

[ocean]
role = "data"
dataset = "ersst-v5-1997-12"
variable = "ssta"
colors = [   # cold -> warm; anomaly classes in °C, see bounds
  "lego_earth_blue", "lego_bright_bluish_green", "lego_medium_azur", "lego_bright_green",
  "lego_bright_yellowish_green", "lego_brick_yellow", "lego_flame_yellowish_orange",
  "lego_bright_orange", "lego_vibrant_coral",
]

[ocean.classification]
method = "bins"
bounds = [-9, -1.5, -0.5, -0.25, -0.1, 0.1, 0.3, 0.5, 1.0, 9]
```

No `[ocean.texture]` (none; FR-008). No `[shadow]` table (defaults: on, Earth Blue, east; FR-005).

## `ocean-la-nina.toml`

Identical except:

- header comment: "December 1988, a strong La Niña"; "about 1,155 extra ocean tiles";
- `id = "ocean-la-nina"`;
- `title = "La Niña, December 1988"`;
- `description = "Sea surface temperature anomaly in December 1988 (strong La Niña), °C against 1971-2000, Pacific-centred (B)."`;
- `dataset = "ersst-v5-1988-12"`.

## Expected build results (real data, arrangement B)

| | `ocean-el-nino` | `ocean-la-nina` |
|---|---|---|
| ocean data cells / shadow | 6,788 / 390 | 6,788 / 390 |
| filled from neighbours | 237 (3.5 %) | 237 (3.5 %) |
| extra tiles beyond one kit | 1,114 | 1,155 |
| SC-004 bound | ≤ 1,200 | ≤ 1,200 |
| Niño 3.4 cells in the expected classes (SC-002) | 68/68 ≥ +0.5 | 68/68 ≤ −0.5 |
| expected warnings | `over_supply` (Earth Blue, Bright Green, Bright Yellowish Green, Bright Orange) | `over_supply` (Earth Blue, Bright Green, Bright Yellowish Green, Brick Yellow, Bright Orange) |

Fixture results differ slightly (values packed to 0.01 °C): 1,126 and 1,159 extra tiles.

## Swap to 2026–27 (follow-up, not in this feature)

Add a dataset entry for the new month (needs a netCDF-4 reader), change `dataset`, `title`,
`description` and the header comment of `ocean-el-nino.toml`; `id`, `arrangement`, `colors` and
`bounds` stay.

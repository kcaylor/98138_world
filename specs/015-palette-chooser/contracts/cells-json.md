# Contract: `cells.json` (format "1")

Written by `map_cells(result)` / `map cells` / the prebuild. Compact JSON, UTF-8.

| Field | Type | Notes |
|---|---|---|
| `format_version` | `"1"` | |
| `recipe` | `{id, title, sha256}` | |
| `arrangement` | `"A"｜"B"｜"C"` | board as hung |
| `width`, `height` | 128, 80 | index = row × 128 + column |
| `cells` | string(10240) | `L`, `O`, `S` (shadow) |
| `layers.<cls>.role` | `data`｜`background` | |
| `.part_id` | `"6141"`｜`"98138"` | |
| `.method` | `bins`, `rank`, `rank-to-supply`, `quantile`, `categorical`, `background` | |
| `.texture` | `none`, `blend`, `mix`, `halo` | |
| `.colors` | key[] | recipe colors per class |
| `.classes` | int[10240] | built class, −1 outside the layer |
| `.cells` | int | layer cells |
| `.editable_classes` | bool | |
| `.values` | (number｜null)[10240] or null | data layers except categorical; rounded to `decimals` |
| `.units`, `.decimals`, `.range` | | data layers |
| `.bounds`, `.bounds_source` | number[n+1], `recipe`｜`built classes` | outer bounds close the list |
| `.no_value`, `.no_value_ice` | int[], int | cells filled from the nearest value |
| `.categories` / `.class_labels` | key[] / string[] | categorical / background |
| `shadow` | `{enabled, color, cells}` | |
| `ice` | `{land: int[], sea: int[], color: "lego_white", source}` | as hung |
| `palette.<part>` | `[{key, lego{name,id}, bricklink{name,id}, rgb, in_kit, lightness}]` | light → dark |
| `note`, `disclaimer` | string | preview-only note; LEGO disclaimer |

Default rendering: `S` → `shadow.color`; else `layers[L→land, O→ocean].colors[classes[i]]`; it
equals `layout.json` (SC-001, tested).

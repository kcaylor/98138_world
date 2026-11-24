# Contract: recipe keys and output additions

Every addition is optional or appears only for non-kit outputs; recipes, layouts and files
without them behave and read exactly as before. Not affiliated with or endorsed by The LEGO Group.

## Recipe (format "1")

```toml
template = "winkel-tripel"        # optional; absent = kit-31203

[margin]                          # optional; used only on non-kit templates
color = "lego_black"              # 3070b color; default lego_black
ring = "lego_bright_yellow"       # optional 3070b color for the outline ring; must differ from color
```

Rules: `template` must name a known template (recipe error otherwise); a recipe naming an
unconfirmed template parses but does not build. Unknown keys in `[margin]` are errors (the
`_check_keys` rule). A margin or ring color that is not a cited 3070b color is an error that lists
the available 3070b color keys and points to `kit part-colors --part 3070b`. Margin labels are not
part of this feature (feature 017, map stickers).

## Layout JSON (schema 2.0) — non-kit layouts only

```json
"metadata": {
  "…": "as today",
  "margin_positions": 1996,
  "template": {"id": "winkel-tripel", "title": "…",
               "projection": {"name": "winkel-tripel", "proj": "+proj=wintri +lat_1=50.4598 +lon_0=11.1 +R=1"},
               "board": {"modules": [8, 5], "width": 128, "height": 80},
               "parts": {"land": "6141", "ocean": "98138", "margin": "3070b"},
               "counts": {"land": 2553, "ocean": 5691, "margin": 1996, "ring": 288},
               "dataset": {"id": "etopo2022-surface-10m", "version": "2022-v1-60s-stride10",
                           "title": "…", "publisher": "NOAA National Centers for Environmental Information",
                           "license": "Public domain (U.S. Government work, NOAA NCEI)",
                           "citation": "…", "doi": "10.25921/fd45-gt74"},
               "source": {"file": "templates/winkel-tripel.json", "sha256": "…",
                          "layout_sha256": "…",
                          "confirmation": {"role": "project owner", "date": "…"}}},
  "map": {"…": "as today", "margin": {"part_id": "3070b", "color": "lego_black", "ring": null,
          "cells": {"margin": 1996, "ring": 0}}}
}
```

Margin positions: `"part_type": "square_tile"`, `"lego_part_id": "3070b"`.
`statistics.margin_tile_count` and `statistics.color_frequency_by_part_type.square_tile` are
added. Counts shown are example exact-fit values (research R2); outputs carry the loaded
template's counts, and tests take them from the template, not from this example.
`template.dataset` is the template's dataset provenance (data-model.md TemplateDataset), copied
from the registry entry `etopo2022-surface-10m` that decided land and ocean. `source.sha256` is
the template file's SHA-256 and `source.layout_sha256` its layout digest (contracts/template-file.md).

## Suitability report (non-kit only)

`template` (id, title, counts, `dataset`), `template_source`, and `margin` (as
`metadata.map.margin`). `citations` gains the template's dataset entry after the recipe's datasets
(once, even when a layer reads the same dataset). Layer reports and thresholds are unchanged;
their cell counts are the template's.

## `cells.json` (format "1") — non-kit only

| Field | Addition |
|---|---|
| `cells` | may contain `M` (margin) |
| `template` | `{id, title, dataset: {id, version, citation, license}}` |
| `margin` | `{part_id: "3070b", color, ring: {color, cells: int[]} \| null}` |
| `palette["3070b"]` | cited square-tile colors, light → dark, with L* |
| `ice` | from `data/templates/<id>-ice.json` (its `source.template_layout_sha256` must equal the template's layout digest) |

Default rendering: `M` → ring color if in `ring.cells`, else `margin.color`; it equals
`layout.json` (tested as for kit variants).

## Parts list JSON and exports

- Lots of part `3070b` with `part_type: "square_tile"`, cited LEGO, BrickLink (`item_no` 3070, from
  `part_numbers.json`; BrickLink lists 3070b as an alternate of item 3070)
  and Rebrickable (`part_num` 3070b) IDs; `kit_supply` 0.
- `layout.template` `{id, title}` for non-kit layouts. `leftovers` unchanged (kit elements only).
- BrickLink XML: `<ITEMID>3070</ITEMID>` items (the `part_numbers.json` BrickLink item); Rebrickable
  CSV: `3070b,<color>,<qty>` rows.

## Price snapshot (`bricklink_price_guide.json`)

`lots[].part_id` may be `3070b`; lots are sorted by part (6141, 98138, 3070b), then LEGO color
ID. Default lot set (`recipes`) adds each bundled recipe's margin colors. Lot IDs are
`<part_id>:<LEGO color id>`. The lot pattern (`_LOT_RE`, today `^(\d+):(\d+)$`) is widened to
accept a part ID with a letter suffix (`3070b:26`), and the part must be in `PART_ORDER`.
Estimates of a Winkel layout stay `complete: false`, with the square-tile colors as `unpriced`
lines, until the snapshot has 3070b rows.

## Section counts JSON (`sheets counts`)

`template` `{id, title}` for non-kit layouts; legend rows may have `part_type: "square_tile"`
with the label "tile 1x1 square".

## Build sheets (non-kit only)

The provenance section adds a line for the template: id, projection, file SHA-256,
confirmation, and its dataset (id, version, title, license, citation). The subtitle and
arrangement sentence name the template and say the frames cannot be re-hung.

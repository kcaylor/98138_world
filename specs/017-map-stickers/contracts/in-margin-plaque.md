# Contract: plaque in a Winkel margin corner (US3, after feature 016)

Additions to 016's contracts (`specs/016-map-templates/contracts/recipe-and-outputs.md`,
`cli.md`). Everything appears only when a plaque is placed; layouts and outputs without one read
and print exactly as 016 defines them. Not affiliated with or endorsed by The LEGO Group.

## Placement

| Corner | Rows | Columns | Module |
|---|---|---|---|
| `top-left` | 1–6 | 1–6 | A1 |
| `top-right` | 1–6 | 121–126 | H1 |
| `bottom-left` | 73–78 | 1–6 | A5 |
| `bottom-right` | 73–78 | 121–126 | H5 |

Checks, in order (exit 1 on failure, contracts/cli.md): the template is not the kit; all 36
studs are margin studs inside the corner's clear block (016 `counts.corners`); they lie in one
16×16 module; no ring stud is within one stud (Chebyshev distance ≤ 1) of the tile. The offset
is shown to the owner on a preview before it is final.

## Layout JSON (schema 2.0), only when placed

```json
"metadata": {"…": "016's non-kit metadata",
  "plaque": {"part_id": "10202", "color": "lego_black", "corner": "bottom-left",
             "studs": {"row": 73, "col": 1, "height": 6, "width": 6}, "cells": 36}}
```

The 36 covered positions are absent (10,204 positions). `statistics.margin_tile_count` counts
the square tiles left; `statistics.plaque_tile_count` is 1. `validate` accepts the layout when
the absent positions are exactly the plaque's studs and those are template margin studs. As 016
reports the square tiles, it reports the tile as `color_unavailable` (`part_type` `plaque_tile`,
`part_id` `10202`, `positions_required` 36, the studs it covers; no suggestion), so the
buildability score counts those studs as not buildable with the kit (80.5% for `ocean-sst` on
Winkel, with or without a plaque; agent decision at T082, 2026-11-25).
Counts: `metadata.margin_positions` and `metadata.map.margin.cells.margin` count the margin
positions present in the layout (1,960 on the Winkel template with a plaque); the template's own
counts in `metadata.template` stay as the template file records them (1,996); and
`metadata.plaque.studs` is 36, so margin positions + plaque studs = template margin studs
(agent decision, 2026-11-23).

## Report

`margin.plaque`: `{corner, source: "option"|"recipe", studs, part_id}`.

## Preview

The plaque is one rectangle in the tile's cited Black over its 6 × 6 studs.

## Parts list JSON and exports

- One lot: `part_id` `10202`, `part_type` `plaque_tile`, `needed` 1, `kit_supply` 0, IDs from
  `plaque_parts.json` (LEGO element 6155125, design 10202; the BrickLink item `bricklink.item_no`
  read from the pinned page, which can differ from the part ID as 6141 is item 4073, and Black
  11; Rebrickable 10202 / Black 0). Lot order 6141, 98138, 3070b, 10202.
- The parts list's `citations` include the lot's sources from `plaque_parts.json`
  `source.snapshots` (its BrickLink page and `rebrickable-elements`); none is dropped.
- The 3070b lots hold 36 fewer tiles than the same build without the plaque.
- `leftovers` unchanged (kit map elements only).
- BrickLink XML: `<ITEMID>` = the tile's `bricklink.item_no`, color 11, `<MINQTY>1</MINQTY>`;
  Rebrickable CSV: `<rebrickable part_num>,0,1` (`10202,0,1`).

## Price estimate

Lot `10202:26`. Without a snapshot row: `complete: false`, the lot `unpriced` with a reason.
`recipe_lots()` adds the lot only for recipes that name a corner.

## Build sheets and counts

- Section page: one Black rectangle, outlined (0.4 mm), over the 6 × 6 studs, labelled
  "tile 6x6 (10202)" and its lot number; the section's count table lists the lot with 1.
- Legend: a row for the lot with a square swatch and the label "tile 6x6"
  (`sheets/legend.py` `PART_LABEL["plaque_tile"]`).
- Overview map: the rectangle; totals line adds "1 tile 6x6 (plaque, part 10202)".
- `sheets counts` JSON: the lot in its section's counts.
- `sheets build` and `sheets counts` accept a layout that lacks exactly the studs recorded in
  `metadata.plaque` (today they require all 10,240 positions); a layout missing any other
  position is still refused with today's message.

## `cells.json`

`cells` uses `P` for plaque studs; block `plaque`: `{part_id, color, rgb, corner, cells: int[]}`.
`palette.js` is not changed by this feature: no site variant has a plaque (spec FR-020), so the
chooser never receives `P` cells. A future site variant with a plaque would need it to draw `P`
in `plaque.rgb` and leave it out of class counts, recoloring and ice.

## Stickers on a template (FR-025)

Both stickers' line ends with "<projection> projection." ("Winkel tripel projection."); the
large sticker's credit adds the template's dataset (ETOPO 2022) once.

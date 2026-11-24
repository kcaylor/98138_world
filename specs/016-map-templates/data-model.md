# Data model: Map templates (016)

Field-level formats are in `contracts/`. Not affiliated with or endorsed by The LEGO Group.

## Template (`templates/__init__.py`; file `data/templates/<id>.json`)

- `id` (`kit-31203`, `winkel-tripel`), `title`, `description`.
- `projection`: name, PROJ string, φ1 and λ0, citation; `fit` (exact extent, studs per unit,
  centre); `check_points` (24 × lon, lat, x, y from pyproj).
- `board`: modules across and down (8 × 5), module size 16, width 128, height 80, pitch 8.0 mm.
- `classes`: 80 × 128 of `L` land, `O` ocean, `M` margin (after corrections).
- `locations`: latitude and longitude of every on-globe stud (null on margin studs).
- `parts`: `{land: "6141", ocean: "98138", margin: "3070b"}`.
- `frame`: kit 31203 frame, arrangements allowed `["A"]`.
- `counts`: land, ocean, margin, ring, modules (full, partial, empty), corner blocks.
- `source`: generator, generated_on, dataset (id, version, URL, SHA-256, citation, license: the
  registry entry `etopo2022-surface-10m`), method and thresholds, software versions, disclaimer.
- `corrections`: list of TemplateCorrection. `confirmation`: Confirmation or null.
- Derived at load: `on_globe`, `land`, `ocean`, `margin` masks; `ring` (margin studs with an
  on-globe 4-neighbour); corner free regions (margin minus ring, per board quadrant);
  `layout_sha256` (TemplateLayoutDigest); `dataset` (TemplateDataset).
- Validation: board is whole modules and 128 × 80; classes only `L`/`O`/`M`; recorded counts
  equal derived counts; a location exactly where the class is `L` or `O`; parts as above;
  check points agree with `templates/winkel.py` to 1e-9; disclaimer present.
- The kit template is built in code from the kit's files: classes from the land/sea mask (no
  `M`), locations from `kit_31203_projection.json`, arrangements A, B, C; it is always buildable.

## TemplateLayoutDigest (`templates/digest.py`)

`layout_sha256`: the SHA-256 of the canonical JSON (UTF-8, keys sorted, no whitespace,
`separators=(",", ":")`) of the object

`{"id", "board", "parts", "projection": {"name", "proj", "lat_1", "lon_0", "fit"}, "classes",
"locations"}`

taken from the template file. It identifies the layout, not the file. It leaves out `title`,
`description`, `check_points`, `counts` (derived), `source`, `corrections`, `confirmation` and
`disclaimer`. Corrections count only through their effect on `classes`. So writing or changing
the confirmation, or adding a test confirmation to a copy, leaves the digest unchanged. Any change
to a class, a location, the fit, the board or the parts changes it. The kit template's digest is
computed the same way from its in-code classes and locations. Ice files record it
(Template ice regions.template_layout_sha256).

## TemplateDataset (non-kit only)

The provenance of the data that decided land and ocean: `{id, version, title, publisher, license,
citation, doi}` from the dataset registry entry named by the template file's `source.dataset.id`
(`etopo2022-surface-10m`). Its `version`, `sha256`, `citation` and `license` must equal the
template file's `source.dataset`. Written into non-kit layouts, reports, sheets and `cells.json`
(below); never into kit outputs.

## TemplateCorrection

`row`, `col`, `class` (`land` | `ocean` | `margin`), `reason` (text). Applied in list order
after generation. Invalid: out of the board, same class as generated (stale), or
`margin → land/ocean` on a stud without on-globe samples.

## Confirmation

`{role: "project owner", date: "YYYY-MM-DD"}`. No personal name. Null until the owner confirms;
cleared by the tool when classes or locations change.

## Template lifecycle

```
generated (candidate + review sheet, outside the repo)
  → committed, unconfirmed (confirmation null: CLI refuses to build; tests use a copy)
  → reviewed (corrections recorded)
  → confirmed (role + date: buildable; web builds its variants)
  → regenerated with changes → unconfirmed again
```

## TemplateProjection (`templates/geometry.py`, run time)

`height`, `width`; `cells_for(lat, lon)` → flat stud index (−1 off the board or on margin);
`locations()` → two 80 × 128 arrays (NaN on margin); `abs_lat()`. Used by `maps/reproject.py`,
`maps/nodata.py` and `maps/overrides.py` in place of `KitProjection` for non-kit builds.
`maps/ice.py` does not use it at build time; it only loads a template's ice file for `map cells`.

## Template ice regions (`data/templates/<id>-ice.json`)

As `data/kit_31203_ice.json` (feature 015), plus:

- `template_id`: the template's id.
- `source.template_layout_sha256`: the template's TemplateLayoutDigest when the file was made.
  `load_template_ice` refuses a file whose value differs from the loaded template's
  `layout_sha256`.
- `land_ice.cells`, `sea_ice.cells`: board indices (row × 128 + column). Land ice only on `L`,
  sea ice only on `O`.

Not used by map builds; read by `map cells`.

## MarginTreatment (`maps/margin.py`)

`color` (3070b color key, default `lego_black`), `ring` (3070b color key or none; ≠ color). Comes
from the recipe `[margin]` table, overridden per field by `--margin-color` and `--ring-color`.
Ignored on the kit template. A color that is not a cited 3070b color is an error. The error lists
the available 3070b color keys and points to `kit part-colors --part 3070b`. Margin labels are
not part of this feature (feature 017, map stickers).

## Layout (extended; schema 2.0 unchanged)

- Positions may have `part_type: "square_tile"`, `lego_part_id: "3070b"` (margin studs).
- Non-kit only:
  - `metadata.template`: id, title, projection, board, parts, counts, `dataset` (TemplateDataset),
    and `source` with the file SHA-256, `layout_sha256` and the confirmation.
  - `metadata.margin_positions`, `metadata.map.margin`.
  - `statistics.margin_tile_count`, `statistics.color_frequency_by_part_type.square_tile`.
- `metadata.arrangement` is A for non-kit layouts. No `metadata.template` = kit template.

## SuitabilityReport (non-kit additions)

`template` (id, title, counts, `dataset`: TemplateDataset), `template_source` (`option` |
`recipe` | `default`), `margin` (as `metadata.map.margin`). `citations` gains the TemplateDataset
entry after the recipe's datasets; it is added once even when a layer reads the same dataset.

## Part 3070b (`part_colors.json`, `part_numbers.json`)

Rows as for 6141 and 98138, all `in_kit: false`; citations to the pinned snapshots plus the pinned
BrickLink page for item 3070 (BrickLink's number for 3070b) and the Rebrickable page for 3070b.
`kit_supply` 0 (`kit/inventory.py` `supplied_for`).

## PartsListLot (`parts/partslist.py`)

- `part_id`: `6141` | `98138` | `3070b`.
- `part_type`: `plate` | `tile` | `square_tile`.
- Order: lots sorted by part (6141, 98138, 3070b), then as today.
- IDs: LEGO element and design IDs, BrickLink `item_no` (3070 for the square tile, from
  `part_numbers.json`; BrickLink lists 3070b as an alternate of item 3070) and
  Rebrickable `part_num` (3070b), each cited.
- `kit_supply`: 0 for 3070b, so `--kits N` buys every square tile.

`sheets/legend.py` `PART_LABEL` has an entry for every `part_type` (`square_tile`: "tile 1x1
square").

## PartsList (parts list JSON)

- `layout.template`: `{id, title}`, for non-kit layouts only.
- `leftovers`: unchanged; kit elements only, so the square tile adds no row.
- `totals`: as today, and they include the square tiles.

## ExportRow (BrickLink XML, Rebrickable CSV)

- BrickLink: `<ITEM>` with `<ITEMID>3070</ITEMID>` (the `part_numbers.json` BrickLink item) and the
  cited BrickLink color ID.
- Rebrickable: a `3070b,<Rebrickable color id>,<qty>` row.

## PriceLot (`prices/lots.py`)

- `id`: `"<part_id>:<LEGO color id>"`, with `part_id` in `PART_ORDER` (6141, 98138, 3070b).
  The lot pattern accepts a part ID with a letter suffix (`3070b:26`).
- Order: by `PART_ORDER` (6141, 98138, 3070b), then LEGO color ID.
- `recipe_lots()` adds each bundled recipe's margin colors.

## Estimate (`prices/estimate.py`)

- `complete`: false while any line is unpriced.
- `lines[].basis`: `unpriced`, with a `reason`, for every 3070b color the snapshot has no row for.
- Kit estimates are unchanged.

## LegendRow (`sheets counts` JSON `legend[]`, sheet legend)

- `part_type`: may be `square_tile`.
- `label`: "tile 1x1 square" (`PART_LABEL`), shown with a square swatch.

## SectionCounts (`sheets counts` JSON)

`template`: `{id, title}`, for non-kit layouts only. Per-section counts include square tiles.

## SheetProvenance (sheet text, non-kit only)

`template`: a provenance line naming the template, its projection, the file SHA-256, the
confirmation, and the TemplateDataset (id, version, title, license, citation). The subtitle and
arrangement sentence name the template and say the frames cannot be re-hung.

## Map cells (`cells.json`, format "1", additive)

Non-kit only:

- `cells` may contain `M`.
- `template`: `{id, title, dataset}`, where `dataset` is TemplateDataset (id, version, citation,
  license).
- `margin`: `{part_id, color, ring: {color, cells} | null}`.
- `palette["3070b"]`.
- `ice`: from the template's ice file.

## Manifest (web, format "1", additive)

- `templates`: `[{id, title, projection, board, counts, rehang: false, description, source}]`.
- `maps[].template_variants.<template-id>`: a variant entry (as `variants.<C>`) plus `template`.
- `part_labels`: the labels of the parts the site's variants use. A kit-only site lists exactly
  6141 and 98138 as today; 3070b appears only when a template variant exists.

## ReviewFlag (maintainer, outside the repo; the review sheet's flags JSON)

- `row`, `col`: the stud.
- `class`: the generated class, `land` | `ocean` | `margin`.
- `land_share`: the share of on-globe subsamples above 0 m, from 0 to 1.
- `reason`: `"land share 40-60%"` | `"water not connected to the ocean"`.
- `group_size`: for the second reason, the number of studs in the unconnected group.

The review sheet PNG shows classes, the ring, module lines, section names A1–H5, the flagged
studs and the disclaimer.

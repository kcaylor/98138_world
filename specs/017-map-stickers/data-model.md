# Data model: Map stickers (017)

Field-level formats are in `contracts/`. Lengths are millimetres, text sizes points. Not
affiliated with or endorsed by The LEGO Group.

## StickerText (`maps/recipe.py`; recipe `[sticker]` table)

- `title`: optional string; `line`: required string (when the table is present);
  `credit`: optional string (replaces the large sticker's "Data:" lines only; research R9);
  `no_data`: optional `{land?: str, ocean?: str}`.
- Validation: known keys only; strings non-empty, one line (no newline or tab); a `no_data` key
  names a layer that has a `no_data` rule. Latin-1 is checked only when a PDF is written.
- `Recipe.sticker`: a StickerText or None (table absent). Nothing but `stickers/` reads it.
- Resolved text (`stickers/text.py`): `title` = table title or `Recipe.title`; `line` = table
  line or `Recipe.description` (empty: `StickerError`); on a non-kit template the line gains
  " <projection> projection." (FR-025). Each resolved field records its source
  (`sticker table`, `recipe title`, `recipe description`).

## Swatch (`stickers/legend.py`; one legend entry)

- `layer` (`land` | `ocean`), `part_id` (`6141` | `98138`), `color` (color key), `rgb` (cited
  sRGB from `part_colors.json`), `lego_name` (cited LEGO color name).
- `meanings`: list of Meaning, in recipe order; two or more when the color is used twice.
- Order: per layer, the layer's colors, then its no-data color, its overrides, then (ocean) the
  land shadow; the land group before the ocean group.

## Meaning

- `kind`: `class` | `background` | `category` | `no_data` | `override` | `shadow`.
- `label`: display text ("below 150 m", "11 to 16 °C", "offshore", "Earth Blue", "ice",
  "Greenland", "land shadow").
- `class` only: `range` `[lo, hi]` (numbers as displayed; `null` for an open end), `units`,
  `source` (`recipe bins` | `built classes`), `step` (rank layers: the display step).
- Rules: bins labels from the recipe bounds (outer bounds never shown, `log10` back in data
  units, the `[legend]` unit when present); rank labels from `maps/cells.py` `derived_bounds`
  rounded to `step` = 10^(floor(log10(max − min)) − 1), half away from zero; equal bounds show
  one value. Scale classes are listed even with no studs; no-data, override and shadow meanings
  only when they cover a stud.

## Credit (`stickers/credits.py`)

- `dataset` (id), `version`, `text` ("<title>, doi:<doi>" or "<title>, <publisher>"), `title`,
  `doi`, `publisher`, `citation`, `license`, `acknowledgement` (optional).
- From `Recipe.datasets()` in order, then (non-kit) the template's dataset; each dataset once.

## PlaquePart (`kit/plaque_parts.py`; `data/plaque_parts.json`)

- `part_id` (`10202`, `3958`, `4974`, `92438`), `kind` (`tile` | `plate`), `studs` (`[w, h]`),
  `name` (BrickLink item name), `numbers` (a `kit.part_numbers.PartNumbers`: LEGO design IDs,
  BrickLink item type `P`, item number, alternates, colors; Rebrickable part number),
  `color` (a `kit.part_colors.PartColor` for `lego_black`: element ID, LEGO/BrickLink/Rebrickable
  names and IDs, RGB, citations).
- Validation: Black only; element ID digits; citations resolve to the file's pinned sources;
  Rebrickable part number equals the part ID; the part ID is the BrickLink item number or an
  alternate (the item number is read from the pinned page and can differ from the part ID, as
  6141 is BrickLink item 4073; outputs and tests use `numbers` and never assume they are equal); BrickLink colors list Black; none of the parts is in the kit inventory; disclaimer.

## Plaque (`kit/plaque_parts.py`)

- `size`: `small` | `large`; `tile` (PlaquePart, a tile), `plate` (PlaquePart, a plate of the
  same studs), `studs` (`[6, 6]` | `[16, 8]`, width × height as the sticker is read).
- `small`: tile 10202 on plate 3958; `large`: tile 4974 on plate 92438 (the smooth tile, chosen
  by the project owner on 2026-11-24 in place of the textured 90498).
- Parts listed for a standalone plaque: 1 tile and 1 plate; for an in-margin plaque: the tile.

## StickerGeometry (`stickers/geometry.py`)

- `tile_mm` = studs × 8.0 − 0.2; `cut_mm` = tile − 2 × 1.0; `bleed_mm` 2.0; marks: gap 1.0,
  length 4.0, width 0.25; `safe_mm` 2.5 inside the cut; `canvas_mm` = cut + 14.
- Small: tile 47.8 × 47.8, cut 45.8 × 45.8, canvas 59.8 × 59.8. Large: tile 127.8 × 63.8, cut
  125.8 × 61.8, canvas 139.8 × 75.8.

## TextBlock

- `field` (`title`, `line`, `site`, `legend`, `credit`, `disclaimer`), `lines` (wrapped text),
  `size_pt` (chosen), `preferred_pt`, `min_pt` (5), `bold`, `align`, `box` (x, y, w, h in the
  sticker's cut coordinates).
- Fit rule: wrap within `max_lines`, then shrink by 0.25 pt to `min_pt`; failure raises
  `StickerError(sticker, field, needed_mm, available_mm)`.

## Sticker (`stickers/compose.py`)

- `size` (`small` | `large`), `plaque` (Plaque), `geometry`, `blocks` (TextBlocks in reading
  order), `legend` (large only: Swatches with their placed circles and labels), `items`
  (`sheets/model.py` items in the sticker's own coordinates: background, bleed, content; marks
  and the cut line are added by the print sheet and the SVG writer).
- Small: blocks title, line, disclaimer. Large: title, site ("98138.world"), line, legend,
  credit, disclaimer.

## StickerSet (`stickers/compose.py`; JSON summary: contracts/sticker-files.md)

- `recipe` (id, title, sha256), `template` (`{id: "kit-31203"}`; after 016 the template's id,
  title, projection and dataset), `arrangement` (the build's, as the legend values' source),
  `text` (resolved title and line with sources), `small`, `large` (Stickers), `legend`
  (Swatches), `credits` (Credits), `plaques` (small, large), `notes` (printed-not-a-part,
  colors-approximate), `tool_version`, `disclaimer`.
- Deterministic: no timestamps; the same `MapResult` content gives the same set, files and
  bytes. Sets made from A, B and C builds of a bundled map are equal except `arrangement`, which
  records the build the legend values come from (SC-003): `to_dict()` without `arrangement` and
  both SVG files are identical. The print sheet prints "legend values from the build hung as
  <C>", so its PDF bytes are identical only within one arrangement.

## PrintSheet (`stickers/compose.py`)

- `paper` (`letter` | `a4`, `sheets/model.py` `PAPERS`), one `Page` (kind `stickers`): title,
  subtitle, both stickers at the positions of research R2 with bleed and marks, captions, the
  plaque parts block, how-to and color notes, every Credit's full citation and license, recipe
  id and SHA-256, tool version, the sheets' furniture (scale bar, print note, footer,
  disclaimer). Each block must fit its area (else `StickerError`).

## Sticker files

- PDF: one page per print sheet; title "Map stickers: <title>", author "98138.world", subject
  with the disclaimer; the cut lines as unpainted paths.
- SVG: `sticker-small.svg`, `sticker-large.svg`; mm units; `<g id="cut-line">`; `<desc>` with
  the disclaimer; `<metadata>` (not drawn) with each Credit's id, version, title, citation,
  license and acknowledgement, the recipe id and SHA-256 and the tool version, nothing that
  depends on the arrangement, so the SVG set carries the citations as the print sheet does
  (constitution IV); text with `textLength`.

## Manifest additions (web, format "1")

- `maps[].stickers.<template-id>`: `files` (kinds `stickers-letter`, `stickers-a4`,
  `sticker-small`, `sticker-large`, each path, bytes, sha256, media_type, description,
  filename), `title`, `line`, `alt` (`small`, `large`), `legend` (label and color name per
  swatch), `plaques`, `notes`. Kit id `kit-31203`; after 016 one entry per template variant.
- `total_bytes` counts every listed file, sticker files included: the one existing manifest value
  that changes (spec FR-018).

## InMarginPlaque (US3, after 016; contracts/in-margin-plaque.md)

- `corner` (`top-left` | `top-right` | `bottom-left` | `bottom-right`), `source` (`option` |
  `recipe`), `part_id` `10202`, `color` `lego_black`, `studs` `{row, col, height: 6, width: 6}`,
  `cells` 36.
- From `--plaque` (wins; `none` turns it off) or the recipe's `[margin].plaque`; part of 016's
  MarginTreatment. Only on a non-kit template; `--plaque CORNER` on the kit is an error, the
  recipe key on the kit is ignored with 016's margin note (research R15, E2).
- Placement: one stud in from both board edges of the corner; must be inside the corner's clear
  block, one 16×16 module, and more than one stud from any ring stud.
- Layout `metadata.plaque` (only when placed); the 36 positions are absent (10,204 positions).
- Parts-list lot: part `10202`, type `plaque_tile`, label "tile 6x6", needed 1, kit supply 0,
  IDs and citations from `plaque_parts.json` (the parts list's `citations` include them); price
  lot `10202:26`.
- `cells.json`: `P` cells and a `plaque` block. `palette.js` is not changed: no site variant has
  a plaque.

## State: sticker texts of the bundled recipes

```
drafted (research R6) → owner approves or edits (blocking task) → appended to the eight recipes
  → recipe checksums change (G1, G2 prove nothing else does) → 016 golden regenerated by
    whichever feature merges second, only after its harness run on the af3ce57 recipe bytes
    matches the committed golden exactly
```

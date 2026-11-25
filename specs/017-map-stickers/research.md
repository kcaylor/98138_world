# Research: Map stickers (017)

Planning evidence and decisions. Numbers marked "measured" come from scratch runs on 2026-11-23
of the code at af3ce57 (this branch) against the cached, pinned datasets and against the test
fixtures in `cli/tests/fixtures/datasets/`; text widths are ReportLab's Helvetica metrics
(`reportlab.pdfbase.pdfmetrics.stringWidth`). The scratch scripts stayed outside the repository.
Not affiliated with or endorsed by The LEGO Group.

Each item is tagged **decided** (logged under the run policy). E1 and E2 were raised as
escalations during planning and then decided by the agent (2026-11-23); the owner can still
reverse them before implementation.

## R1. True-size geometry (decided)

- Stud pitch 8.0 mm: LDraw file format specification ("1 brick width/depth = 20 LDU",
  "1 LDU = 0.4 mm", stated there as approximations), already the build sheets' pitch
  (feature 006 R4, `sheets/compose.py` `PITCH`).
- Tile outer size = studs × 8.0 mm − 0.2 mm (FR-009): 6×6 tile 47.8 mm square, 8×16 tile
  127.8 × 63.8 mm. LDraw gives no clearance; the LUGNET FAQ "What are the dimensions of LEGO
  brick?" (https://www.lugnet.com/~330/FAQ/Build/dimensions) gives a measured pitch of 7.986 mm
  and "a small gap" between bricks. The 0.1 mm per side is the conventional figure; with the
  measured pitch the 6×6 tile is about 47.7 mm. The 1 mm inset absorbs either value (0.95 mm
  instead of 1.0 mm per side), so the plan keeps the spec's nominal formula and the print sheet
  says "about" for tile sizes.
- Cut size (the sticker) = tile − 2 × 1.0 mm inset: **small 45.8 × 45.8 mm**, **large
  125.8 × 61.8 mm, landscape** (16 studs wide, 8 high).
- Bleed 2.0 mm of background past each cut line. Cut marks outside the bleed: a 1.0 mm gap, then
  a 4.0 mm mark, 0.25 mm wide, on the extension of each cut edge at each corner (8 marks per
  sticker). So one sticker with its marks needs cut + 14 mm: small 59.8 mm square, large
  139.8 × 75.8 mm.
- Text safe area 2.5 mm inside the cut line on every side: small 40.8 × 40.8 mm, large
  120.8 × 56.8 mm. The disclaimer at 5 pt is 40.5 mm wide (measured) and fits one line of the
  small sticker; a 1 mm cutting error still leaves 1.5 mm.
- Constants live in `stickers/geometry.py` with the citations in its docstring (the
  `sheets/compose.py` pattern for `PITCH`); the plaque sizes in studs come from
  `data/plaque_parts.json` (R10).
- Alternatives rejected: sizing the sticker to the full tile (any cutting error shows sticker
  edge over the tile edge); 0.5 mm inset (too tight for hand cutting).

## R2. Print sheet page layout, Letter and A4 (decided)

One portrait page, 12 mm margins, the build sheets' furniture (`sheets/compose.py`
`furniture()`: 100 mm scale bar, "Print at 100% (no fit-to-page)", footer title, "Page 1 of 1",
disclaimer) at the bottom. Positions in mm from the top-left corner, the same on both papers:

| Block | Place |
|---|---|
| Title "Map stickers: <sticker title>" (16 pt bold), subtitle (8.5 pt) | baselines 21.0 and 27.5 |
| Large sticker: cut line at x 19.0, y 41.0 (125.8 × 61.8); bleed and marks to x 12.0–151.8, y 34.0–109.8 | top |
| Caption beside it: size, tile, "for the front, the back of the frame or a display" | x 152 to the right margin (Letter 52 mm, A4 46 mm) |
| Small sticker: cut line at x 19.0, y 118.8 (45.8 square); marks from y 111.8 to 171.6 | below the large one, its marks 2 mm clear of the large sticker's |
| Parts for a standalone plaque (both sizes), "The sticker is printed, not a LEGO part." | x 77.8 to the right margin (Letter 126 mm, A4 120 mm), y 115–172 |
| How to make it, the color note, each dataset's full citation and license, recipe id and SHA-256, tool version | y 178 to 24 mm above the bottom edge (Letter 77 mm, A4 95 mm) |

Letter is the binding paper. A test lays out every bundled map (and, after 016, every template
variant) on both papers and fails if a block runs past its area; a block that does not fit stops
the command (`StickerError`) instead of being cut, because the citations and licenses must
appear (constitution IV). Measured: the longest citation set (living planet, three datasets) is
about 12 lines at 7 pt across 191.9 mm (about 40 mm), within 77 mm.

## R3. Sticker layout and text fitting (decided)

- Small sticker (FR-003): title (bold, preferred 11 pt, up to 3 lines), sticker line (7 pt, up
  to 5 lines), both centred and the pair centred vertically above the disclaimer (5 pt, up to 2
  lines, at the bottom of the safe area). Nothing else.
- Large sticker (FR-002): title (bold, 14 pt, up to 2 lines) on the left and "98138.world"
  (bold, 7 pt) right-aligned on the title's first baseline; the line (7 pt, up to 2 lines);
  the legend (6 pt labels, 2.8 mm round swatches, row pitch 3.4 mm at 6 pt); the data credit
  (5.5 pt, one dataset per line, wrapped); the disclaimer (5.5 pt) at the bottom.
- Fitting (FR-013): every block starts at its preferred size; text wraps at spaces within the
  block's line limit; if it still does not fit, the size drops in 0.25 pt steps; the minimum is
  5 pt. Bottom blocks are placed from the bottom up, top blocks from the top down, and the legend
  takes what is left, shrinking first. A word wider than the block at 5 pt, or a stack that does
  not fit at 5 pt, raises `StickerError` naming the sticker, the field (`title`, `line`,
  `legend: ocean`, `credit`, `disclaimer`) and the space needed and available in mm.
  The build sheets' `wrap()`/`fit()` truncate with "..."; stickers never truncate, so they get
  their own wrapper (it reuses `sheets/compose.py` `text_width`).
- Measured at the preferred sizes (drafts of R6): small-sticker titles take 1–2 lines, lines
  2–3; large-sticker lines take 1 line (rainfall 115.7 mm of 120.8); the widest legend label is
  26.4 mm ("850 g C m-2 yr-1 and above", 6 pt); the most legend rows in one group are 10
  (land elevation, two columns); the widest credit is 118.2 mm at 5 pt (MODIS-Aqua chlorophyll),
  130.1 mm at 5.5 pt, so it wraps to two lines. Vertical budget of the large sticker: top
  blocks about 12.6 mm, bottom blocks up to about 15.3 mm, leaving about 33.9 mm for the legend
  (a heading row and 9 rows). By this estimate every bundled map fits at the preferred sizes;
  the test of R2 checks it on both papers (SC-002).
- No slack factor: PDF viewers substitute Helvetica with metric-compatible fonts and SVG text
  carries `textLength` (R4), so the Helvetica widths hold.

## R4. Rendering, fonts and colors (decided)

- Page model: stickers and the print sheet are built from `sheets/model.py` items (`Rect`,
  `Circle`, `Line`, `Text`) in millimetres, so tests read text, sizes and swatches without
  rendering (as for the build sheets).
- PDF: `sheets/render_pdf.py` gains a shared item-drawing function (moved out of
  `render_pdf()` unchanged); `stickers/render.py` uses it with ReportLab `invariant=1` and
  `pageCompression=1`, so the same input gives the same bytes (FR-012). Build-sheet PDFs stay
  byte-identical (R13 guard).
- Fonts: the PDF standard fonts Helvetica and Helvetica-Bold, not embedded, Latin-1 (FR-013;
  feature 006 R3). Any field outside Latin-1 stops a PDF run with "use --format svg". SVG text
  names `Helvetica, Arial, sans-serif` (the sheets' `FONT`) and carries
  `textLength="<Helvetica width>" lengthAdjust="spacingAndGlyphs"`, so a substitute font keeps
  every line's measured width and nothing spills past the safe area. No font file is shipped or
  embedded; embedding one (for outlines or non-Latin-1 PDFs) would need a font license and a new
  dependency, which this plan does not take.
- SVG: one file per sticker (`sticker-small.svg`, `sticker-large.svg`), `width`/`height` in mm
  and `viewBox` in mm (cut + 14 mm), white paper, the bleed, the marks, the sticker content, and
  last a group `<g id="cut-line">` holding one `<rect>` of the cut size, `fill="none"`,
  `stroke="#ff00ff"`, `stroke-width="0.1"` (a hairline "cut contour" that print shops and
  cutting software can select); `<title>` and `<desc>` (the disclaimer); and `<metadata>` (not
  drawn) with the recipe id and SHA-256, each dataset's id, version, title, full citation and
  license, and the tool version, so the SVG set carries the citations as the print sheet does
  (constitution IV; spec Clarifications), with nothing that depends on the arrangement. Written by
  `stickers/render.py` with the sheets' number format (two decimals, fixed attribute order, `\n`)
  and the item serialiser moved out of `sheets/render_svg.py` `page_svg()` unchanged. Sheet SVGs
  stay byte-identical.
- PDF cut line: an unpainted path (`re n`) of the cut size, so it is in the file (SC-001) but not
  printed; the bleed and the marks are printed.
- Colors: swatches in the part color's cited sRGB from `part_colors.json` (kit colors equal
  `kit_colors.json`); the background and bleed in the cited sRGB of the label tile's Black
  (`lego_black`, Rebrickable/LDraw RGB 5, 19, 29, from `plaque_parts.json`), so the print matches
  the tile as closely as the swatches match their parts; text White; every swatch has a 0.15 mm
  light outline (RGB 210, 210, 210) so Black swatches show (FR-008); land (plate) swatches carry
  the build sheets' inner ring. No image, logo, wordmark or LEGO label artwork (FR-008, SC-004).
- Alternatives rejected: pure black background (looks unlike the tile); text converted to
  outlines (needs a font file); a PNG preview for the web (needs a rasteriser with a font; SVG
  in `<img>` is enough, R12).

## R5. The recipe sticker table (decided)

```toml
[sticker]                                  # optional, anywhere in the file
title = "World Map, kit 31203 design"      # optional; default: the recipe's title
line = "White land and ..."                # required in the table
no_data = { land = "ice", ocean = "sea ice" }   # optional; per layer with a no_data rule
```

- Parser (`maps/recipe.py`): `sticker` joins `_TOP_KEYS`; `_sticker()` checks keys with
  `_check_keys`; `line` and `title` are non-empty single-line strings (no newline or tab);
  `no_data` keys are `land`/`ocean` and the layer must have a `no_data` rule (error
  `sticker.no_data.land: the land layer has no no_data rule`). Latin-1 is not a parse rule (SVG
  takes any text); the PDF path checks it. `Recipe.sticker` is a `StickerText` or None.
- Fallback (FR-004): title from the table, else the recipe title; line from the table, else the
  recipe description; no-data label from the table, else "no data". A recipe with neither a
  line nor a description stops the sticker command with "add a [sticker] line".
- Additive: recipes without the table parse and build exactly as before; nothing in a layout,
  report, parts list, cells file or sheet reads `Recipe.sticker`.
- Checksums: `Recipe.sha256` is the SHA-256 of the file's bytes, so each bundled recipe's
  checksum changes when its table is added, and with it every output that records it (layout
  `metadata.map.recipe.sha256`, report `recipe_sha256`, `cells.json` `recipe.sha256`, the layout
  file's own SHA-256 inside parts lists and sheets, the web manifest). No stud, part, color or
  count changes (SC-006; R13 proves it). No committed test on main pins a recipe checksum
  (searched `cli/tests`, `web/tests`); feature 016's kit golden does (R13).
- The table is appended at the end of each bundled file, after one comment line, so the bytes
  before it are exactly the af3ce57 file (R13 uses that).

## R6. Draft sticker texts for the owner (owner approval stop)

The eight bundled recipes get these tables only after the owner approves or edits them (a
blocking task). Text is Latin-1 (° and ñ are; en dashes are not, so years use "-"). Titles
without "Official" (FR-004). Widths at the preferred sizes are in R3.

| Recipe | Sticker title | Sticker line | No-data labels |
|---|---|---|---|
| `official-31203` | World Map, kit 31203 design | White land and the kit's ocean pattern in nine tile colors, cell for cell from its building instructions. | – |
| `official-31203-bathymetry` | Kit 31203 look, from bathymetry | Ocean depth (ETOPO 2022) ranked into the kit's nine tile colors in the kit design's proportions, on white land. | – |
| `ocean-sst` | (recipe title) Ocean temperature | Annual mean sea surface temperature, 1991-2020, cold to warm on the kit's nine tile colors. | – |
| `land-elevation` | (recipe title) Land elevation | Height of the land in metres, from lowland green through tan and brown to grey and ice-sheet white. | – |
| `ocean-el-nino` | (recipe title) El Niño, December 1997 | Sea surface temperature anomaly of a strong El Niño, in °C against the 1971-2000 average. | – |
| `ocean-la-nina` | (recipe title) La Niña, December 1988 | Sea surface temperature anomaly of a strong La Niña, in °C against the 1971-2000 average. | – |
| `living-planet` | (recipe title) Living planet | Plant productivity on land (2000-2015) and ocean chlorophyll at sea (2013-2024), with ice in white. | land "ice", ocean "sea ice" |
| `rainfall` | (recipe title) Rainfall | Annual mean precipitation, 1991-2020, from desert tan to rainforest green on land and pale to deep blue at sea. | – (its White cells are overrides with names) |

At the stop the agent also writes a sample print sheet of every bundled map (real cached data,
outside the repository) so the owner sees the whole sticker, including the legend labels and the
data credits (R7, R9).

Credit override (R9): `official-31203` also gets `credit = "Design grid from the LEGO 31203
building instructions, extracted by 98138.world."` for the large sticker; every other recipe uses
the registry credit lines.

## R7. The legend from the built map (decided)

- Input: a `MapResult` (`maps/build.py`): the recipe, `classes` per layer (class index, −2
  no-data, −10 − i override i), `fields` per data layer, the arrangement. `stickers/legend.py`
  never reads, reprojects or classifies data. Rank boundaries come from the helper that
  `map_cells` already uses: `maps/cells.py` `_derived_bounds` is split into a public
  `derived_bounds(values, classes, n)` returning unrounded floats and the existing rounding, so
  `cells.json` stays byte-identical; units come from a public `variable_units(layer)` (the
  `_UNITS` mapping without the `log10` prefix).
- One swatch per (part, color), in the recipe's order: the layer's colors, then its no-data
  color, then its overrides, then (ocean group) the land shadow. A color met again adds its
  meaning to the earlier swatch ("-2 °C; land shadow"; "Antarctica; Greenland"). Every scale
  class is listed even with no studs; a no-data, override or shadow entry appears only when it
  covers at least one stud (the shadow is on in every bundled recipe but `official-31203`).
- Labels:
  - bins: first class "below b1 u", last "bn u and above", others "a to b u"; outer bounds never
    printed; `log10` layers in data units (10^b printed with up to 6 significant digits, so
    0.08, 0.15, 0.3, 1); a layer with `[legend]` in the second unit only (rainfall:
    "below 182.5 mm/yr", exact recipe bounds × 365).
  - rank (`rank`, `rank-to-supply`, `quantile`): "lo to hi u" from the derived bounds, outer
    bounds included (they are the built data's minimum and maximum), rounded to the display step
    (R8); equal rounded bounds print one value ("-2 °C").
  - categorical (`official-31203`): the LEGO color name of each swatch (cited), no values; the
    group heading says "Ocean: the kit design's colors".
  - background: the roles `map_cells` uses (`_BACKGROUND_LABELS`): "land", "offshore",
    "coast ring", or "background n".
  - no data: the sticker table's label or "no data"; overrides: their `name`; shadow: "land
    shadow".
- Numbers: hyphen-minus, comma thousands separator ("3,000 m"), no trailing zeros, a space before
  the unit, "°C" for `degC`, other units as the registry spells them ("g C m-2 yr-1", "mg m-3").
- Measured legends (real data, A): official-31203 1 + 9 swatches; bathymetry 1 + 9 (8 depth
  classes "0 to 800 m" … "4,600 to 6,200 m" and the Earth Blue shadow); ocean-sst 1 + 9 ("-2 °C;
  land shadow", "-2 to 0 °C", "0 to 11 °C", … "28 to 30 °C"); land elevation 10 + 3; each ENSO
  map 1 + 9 ("below -1.5 °C; land shadow" … "1 °C and above"); living planet 7 + 7; rainfall
  7 + 7 (White "Antarctica; Greenland", White "sea ice", Black "land shadow").

## R8. One sticker set per map: A, B and C (decided)

- What varies with the combination: only the land shadow's cell count (392, 390, 389 in A, B,
  C) and therefore the supply left for rank classes. Bins bounds, titles, lines, credits, parts
  and categorical colors do not depend on it.
- Measured rank bounds (inner and outer, before rounding):

| Map | Data | A | B | C |
|---|---|---|---|---|
| ocean-sst | real = fixture (ERSST is 2°) | −1.8, −1.8, 0.01, 10.97, 15.8, 22.22, 25.4, 27.14, 28.26, 29.76 | … 11.01, 15.83, 22.22, 25.41, 27.14, 28.27 … | … 11.01, 15.83, 22.22, 25.41, 27.14, 28.26 … |
| bathymetry | real ETOPO 10′ | 1, 801, 2297, 2623, 2904, 3628, 4319, 4574, 6169 | 1, 799, 2295, 2620, 2902, 3627, 4319, 4574, 6169 | 1, 799, 2295, 2619, 2902, 3627, 4319, 4574, 6169 |
| bathymetry | fixture ETOPO 1° | 0, 784, 2296, 2610, 2877, 3562, 4320, 4572, 6170 | 0, 780, 2292, 2608, 2875, 3561, 4320, 4571, 6170 | 0, 780, 2287, 2607, 2875, 3561, 4320, 4571, 6170 |

- Display step: two significant digits of the layer's built range, step =
  10^(floor(log10(max − min)) − 1), rounding half away from zero (`decimal.ROUND_HALF_UP`):
  ocean-sst 1 °C, bathymetry 100 m. At that step A, B and C give identical legends for all
  eight maps on real data and on the fixtures (measured). The spec's "10 m" is not enough on the
  fixtures (2,296 → 2,300 in A but 2,292 → 2,290 in B), so the plan uses 100 m; it still meets
  FR-006.
- The CLI builds in the recipe's own arrangement (A, or B for the ENSO maps; no
  `--arrangement` option); the web makes one set per map from the variant built in the recipe's
  default combination. A test builds every bundled map in A, B and C from the fixtures and
  requires identical sticker sets (SC-003): `to_dict()` without `arrangement`, and both SVG
  files byte for byte. The JSON summary's `arrangement` and the print sheet's line "legend
  values from the build hung as <C>" record the build, so JSON and PDF bytes are compared only
  within one arrangement (two runs give the same bytes, FR-012). Quickstart step 4 repeats it on
  real data.

## R9. Data credit and citations (decided)

- Large sticker (FR-007): one line per dataset of `Recipe.datasets()` (layer datasets, a
  `land_from` mask dataset, override datasets) and, on a template, the template's dataset (once):
  "<registry title>, doi:<doi>", or "<registry title>, <publisher>" without a DOI. The block is
  headed "Data:". Widest line 118.2 mm at 5 pt (R3).
- Print sheet: each dataset's id, version, title, full citation and license, as the build
  sheets' provenance lines do (`sheets/compose.py`), plus the acknowledgement when the registry
  has one. This is where the small sticker's map meets constitution IV.
- `official-31203` reads the packaged design grid, whose registry title and publisher give
  "Official LEGO 31203 World Map design grid, Extracted by this project (feature 003)". It is
  factual, but it says "Official" and names a project feature. Changing the registry title would
  change kit outputs, so the plan does not. Decision (agent, close call, 2026-11-23): an optional
  `sticker.credit` line (contracts/recipe-sticker.md) replaces the large sticker's "Data:" lines
  only; the print sheet keeps every registry citation. `official-31203` sets one, drafted in R6
  for the owner's approval, for example "Design grid from the LEGO 31203 building instructions,
  extracted by 98138.world", following the owner's decision to drop "Official".

## R10. Plaque parts and their cited IDs (decided)

- Parts (spec): small = tile 6×6 10202 on plate 6×6 3958; large = tile 8×16 4974 on plate 8×16
  92438; Black only. The project owner chose the smooth tile 4974 "Tile 8 x 16 with Bottom Tubes,
  Polished Surface" on 2026-11-24, in place of the textured 90498 (element 4603646).
- Pinned Rebrickable `elements.csv` (SHA-256 `dfc8641d…`, already pinned in
  `tools/partcolors/build.py`; verified on a cached copy): Rebrickable color 0 (Black) has
  exactly one element per part: 10202 → 6155125, 3958 → 395826, 4974 → 6484420,
  92438 → 6094066; `design_id` equals the part number for each. None of the four is in
  `data/kit_31203_inventory.json`.
- BrickLink: the Internet Archive holds catalog pages for all four items (availability API,
  2026-11-23; CDX API for P=4974, 2026-11-24): P=10202 (2025-09-03), P=3958 (2026-09-12),
  P=4974 (2026-04-17, the latest copy), P=92438 (2026-09-12). They are pinned by SHA-256 like `bricklink-4073` (feature 005) and parsed with
  `partnumbers.build.parse_bricklink_part` for the item name, item number, alternates and
  colors (Black must be listed with BrickLink id 11).
- Rebrickable part pages: no archived copy of part 10202; copies of the others are from 2019 and
  2024. So the Rebrickable part number and LEGO design ID come from the pinned `elements.csv`
  (`part_num`, `design_id`), not from part pages; LEGO, BrickLink and Rebrickable color names and
  IDs and the RGB come from the snapshots `partcolors` already pins (Rebrickable colors, LDraw
  `LDConfig.ldr`, BrickLink color guide), with its join rules 1–5.
- Where: a new package file `cli/src/lego_image_processor/data/plaque_parts.json` (format in
  `contracts/plaque-parts-file.md`), written and checked by
  `PYTHONPATH=tools python -m partcolors plaque-parts [--check]`, read by
  `kit/plaque_parts.py` `load_plaque_parts()`. The loader returns the same `PartNumbers` and
  `PartColor` objects as the map parts, so `parts.resolve.ResolvedColor` and the exports work for
  the in-margin tile (R15).
- Why not rows in `part_colors.json`/`part_numbers.json` (FR-014 says "the packaged part data"):
  those loaders accept exactly the map parts, and every reader of `part_colors.json` that loops
  over parts would change a kit output: `maps/cells.py` `part_palette()` (every `cells.json`),
  `parts/owned.py` (loose-parts CSV matching), `kit part-colors`. Feature 016 is also changing
  those files and tools for part 3070b. A separate file, made by the same maintainer tool with
  `--check`, changes no existing output and merges with 016 without conflicts in generated data.
  Close call, logged.
- How makers see them (FR-015): the print sheet, the command's text and JSON output, and the map
  page list each plaque's tile and plate: quantity 1, name, LEGO element and design ID,
  BrickLink item and color (id), Rebrickable part and color (id), with "The sticker is printed,
  not a LEGO part." No price estimate and no marketplace export for standalone plaques (spec).
- Network: fetching the four archived BrickLink pages is a one-time maintainer step (as in
  feature 005); tests use small synthetic HTML pages in the structure the parser reads, never a
  copy of a catalog page. If a pinned copy turns out unusable, the
  owner is asked for another pinned source (owner step).

## R11. Library and command line (decided; one escalation)

- Library (`stickers/`): `sticker_set(result, *, template=None) -> StickerSet` (content and the
  two stickers' page items), `print_sheet(sticker_set, paper) -> Page`,
  `render_sticker_pdf(sticker_set, paper) -> bytes`, `render_sticker_svgs(sticker_set)` →
  `[(file name, text)]`, `StickerSet.to_dict()` (the JSON summary), `StickerError`
  (`ValueError`).
- `map stickers RECIPE -o OUT [--format pdf|svg|json] [--paper letter|a4] [--cache-dir DIR]`
  (and `--template ID` after 016): builds like `map cells` (`build_map(...,
  compare_official=False)`, the recipe's own arrangement), never downloads, composes everything
  in memory, then writes: PDF to the file OUT; SVG to the directory OUT (two files; it removes
  only its own two names); JSON to the file OUT. It prints the recipe, where the legend values
  come from, the title and line with their sources, both stickers' sizes and smallest text size,
  the plaque parts, the files written, the color note, the citations, and the disclaimer last.
  Errors exit like `map cells` (dataset not cached: the `DatasetNotCachedError` exit and message
  naming `dataset fetch`; recipe error 1; `StickerError` and non-Latin-1 PDF text 1), write
  nothing, and end with the disclaimer.
- **Decided (agent, E1)**: FR-015 requires "the command's text and JSON output", but FR-016's
  signature has `--format pdf|svg` only. Decision: add `json` to `--format` (the summary that
  the web prebuild also lists; the `parts list --format json` pattern). Alternative: write
  `stickers.json` beside the two SVG files. The plan assumes the recommendation; switching is a
  small change to one command.

## R12. Web (P2) (decided)

- Prebuild (`web/src/web98138/prebuild.py`): per map, one sticker set from the `MapResult` of the
  recipe's default combination (`build_variant` hands it back as `_result` for that combination;
  if that combination is not being built, one extra `build_map` in it). Files under
  `maps/<map>/stickers/kit-31203/`: `stickers-letter.pdf`, `stickers-a4.pdf`,
  `sticker-small.svg`, `sticker-large.svg`, made with `render_sticker_pdf` and
  `render_sticker_svgs`. `kit-31203` is 016's kit template id (a constant in `stickers/` until
  016 merges).
- Manifest (format "1", additive): `maps[].stickers.<template-id>` with `files` (kind → path,
  bytes, sha256, media_type, description, filename), `title`, `line`, `alt` texts, `legend`
  (label and color name per swatch), `plaques` (parts with IDs) and `notes`. Variant entries are
  unchanged. `total_bytes` counts every listed file, stickers included (it is the site's size;
  nothing else reads it). Download names: `98138-world_<map>_<kind>.<ext>`, and after 016
  `98138-world_<map>_<template-id>_<kind>.<ext>`.
- Catalog (`catalog.py`): sticker kinds (`stickers-letter`, `stickers-a4`, `sticker-small`,
  `sticker-large`) are checked like variant files (inside the root, present, size); the block is
  optional, so an older manifest still serves.
- Routes (`app.py`), registered before the combination routes: `GET
  /maps/{map}/stickers/{template}/{name}.svg` (inline `image/svg+xml`, for `<img>`) and `GET
  /maps/{map}/stickers/{template}/download/{kind}` (attachment). Unknown map, template or kind:
  404. CSP unchanged (`img-src 'self'`); the SVGs contain no script.
- Map page (`templates/map.html`): a "Stickers" panel after the parts: both stickers as `<img>`
  in `<figure>`s with alt text (title and line) and a caption with size and tile; a native
  `<details>` with the large sticker's full text (legend labels, credit); the standalone plaque
  parts with IDs; the notes ("printed colors only approximate the LEGO colors", "the sticker is
  printed, not a LEGO part"); the four downloads. Identical for A, B and C; no JavaScript.
- The service never imports `lego_image_processor`; `web/requirements*.txt` gain nothing.
- Sizes (estimate): a one-page vector PDF of about 10 kB and SVGs of about 10–15 kB, so about
  50 kB per map, 0.4 MB for 8 maps (+5 Winkel sets after 016), within SC-008's 2 MB.

## R13. Guarding the other outputs, and feature 016 (decided)

- G1, recipe prefix: a test pins the af3ce57 SHA-256 of each bundled recipe and requires the
  file's bytes before the sticker block to hash to it (so the only change to a recipe is the
  appended table):

  | Recipe | af3ce57 SHA-256 |
  |---|---|
  | land-elevation | 659b67ad222c6fae15e514ba35d6e256297055b82588c4e3dabd3546bbf9c2e5 |
  | living-planet | cf7a805b65f751299545181a025cd3096a6a2466508e3e8cbe7575c8babf0dfc |
  | ocean-el-nino | 0095a9da442d29b04dde0b9df467efc812c9a6ea952e165c1b44d91c7d5f98cd |
  | ocean-la-nina | 973535a1c1487ed071c0b70a9a4bf1f55196bd50614ffed50bebeeb3ff3eeec8 |
  | ocean-sst | d7aaececf7f444b37f7cbca3a92ff8aedef735b770f58be2b87e3b1d9a0d6ddb |
  | official-31203-bathymetry | f7412b1c05148e7ca253913fc940a18d835ddec1c1f7eeaaee664ee13fd9b97e |
  | official-31203 | e08f4d1747cab16a58d45c8dbb94dfe0725cf7f0ad558cb26e10f7f9aba764f7 |
  | rainfall | 0fdc586705803f3ff6522d30e999a317dd7fb8cfa2d83b039c57d0921b7cfa5a |

- G2, only the checksum: for every bundled recipe, built from the fixtures in A, the outputs
  from the prefix bytes and from the full file are equal after replacing the recipe SHA-256 and
  the layout file's SHA-256 with placeholders: layout JSON, report (fixed `generated_at`),
  preview pixels, parts lists (full and `--kits 1`), BrickLink XML, Rebrickable CSV, estimate on
  the synthetic price fixture, section counts, `cells.json`, sheets SVG text (SC-006).
- G3, kit golden: before any code change, digests of every kit output of the eight bundled
  recipes in A, B and C, built from the prefix bytes (016's `kit_outputs` approach: layout,
  report with a fixed `generated_at`, preview pixels and PNG bytes, parts lists full and
  `--kits 1`, BrickLink XML, Rebrickable CSV, estimate on the synthetic price fixture, section
  counts, `cells.json`), plus the sheets PDF Letter bytes and SVG pages for `ocean-sst` and
  `land-elevation` in A (the outputs the renderer refactor touches), are committed as
  `cli/tests/fixtures/golden/stickers_017_guard.json` (+ `.source.json` naming af3ce57);
  `tests/integration/test_stickers_outputs_unchanged.py` rebuilds and compares.
- G4, `part_palette()` and part data: canonical-JSON digests of the 6141 and 98138 blocks of
  `part_colors.json` and `part_numbers.json` and of the citation entries they reference equal
  their af3ce57 values (plaque parts are in their own file). Whole-file checksums are not pinned,
  because feature 016 appends 3070b rows and keeps those blocks byte-identical (016's golden
  digests them the same way), so G4 stays valid after 016 merges. A test asserts `cells.json`
  palettes list only 6141 and 98138.
- Feature 016: its kit golden (`cli/tests/fixtures/golden/kit_outputs.json` and the web digest
  list, research R9 of 016) records recipe checksums through layouts, reports, `cells.json`, the
  manifest and sheet PDFs. Whichever of 016 and 017 merges second regenerates those digests with
  `PYTHONPATH=tools python -m maptemplates kit-golden --fixtures`, after G1 and G2 pass, and says
  so in its pull request. Before rewriting, it proves that only recipe checksums differ: 016's
  harness run on the af3ce57 recipe bytes (the prefixes) must reproduce the committed golden
  exactly, and the web golden's normalised pages, with recipe checksums replaced by
  placeholders, may differ only by the Stickers panel, the about paragraph and the manifest's
  `stickers` blocks and `total_bytes`. If 017 is second, it also rebases US3's code on 016's final code. The
  merge order does not change 017's own guards.

## R14. Templates after feature 016 (decided)

- `map stickers --template ID` (016's `--template` option and resolution) builds on the
  template; `sticker_set` reads `MapResult.template`. On a non-kit template both stickers' line
  ends with "<projection name> projection." ("Winkel tripel projection.") and the large
  sticker's credit adds the template's dataset (ETOPO 2022, once) (FR-025); the print sheet adds
  016's template provenance line. The projection name comes from 016's template data
  (`templates[].projection` "Winkel tripel" in 016's manifest contract); if 016's library has no
  accessor for it, 017 adds `Template.projection_title`.
- Web (FR-020): each template variant gets `maps[].stickers.<template-id>` and the template page
  shows it; its layout files stay as 016 builds them (no plaque).
- Measured: the Winkel suffix adds 26 characters; every drafted line still fits the small
  sticker at 7 pt in 4 lines.

## R15. In-margin plaque (US3, after 016; decided, one escalation)

Planned against 016's contracts (`specs/016-map-templates/contracts/`, data-model.md), not its
code in progress; the US3 tasks start by re-reading 016's merged contracts.

- Where: one Black tile 6×6 (10202) per board, in a corner chosen by `--plaque
  top-left|top-right|bottom-left|bottom-right|none` on `map build`, `map check` and `map cells`
  (the same three commands that take 016's margin options) or by a recipe key. Option wins;
  `none` turns a recipe's plaque off (FR-021).
- Recipe key: `plaque = "<corner>"` in 016's `[margin]` table (it is margin content).
- **Decided (agent, E2)**: FR-021 says a plaque on the kit template stops the build; 016's contract
  says `[margin]` settings on a kit build are ignored with a note. Decision: `--plaque CORNER`
  with the kit template is an error (exit 1); a recipe's `[margin].plaque` on a kit build is
  ignored with 016's note, so a recipe that names a corner still builds on the kit.
- Offset: the tile sits one stud in from both board edges of its corner: top-left rows 1–6,
  columns 1–6; top-right rows 1–6, columns 121–126; bottom-left rows 73–78, columns 1–6;
  bottom-right rows 73–78, columns 121–126. That lies inside the corner module (A1, H1, A5, H5)
  and, with 016's exact fit, inside each corner's 14 × 14 clear block (016 R2, R20). The build
  checks, in order: template has a margin (else E2's error); the 36 studs are margin studs inside
  016's corner block (`counts.corners`); they lie in one 16×16 module; no ring stud is within
  one stud (Chebyshev distance ≤ 1) of the tile. A failure stops with the space needed (6 × 6
  plus one stud) and available (the block's size). The owner sees a Winkel preview with plaques
  in all four corners before the offset is final (owner step).
- Layout: `metadata.plaque` `{part_id: "10202", color: "lego_black", corner, studs: {row, col,
  height: 6, width: 6}, cells: 36}` only when placed; the 36 positions are absent, so the layout
  has 10,204 positions (SC-009); `statistics.margin_tile_count` counts the square tiles left.
  Layouts without it read as before (FR-023).
- Preview: one filled rectangle of the tile's cited Black over its 6 × 6 studs (pitch × 6 minus
  the stud gap). Sheets: the section page draws one outlined Black rectangle labelled
  "tile 6x6 (10202)" with its lot number, counted in the section's table and the legend; the
  overview map draws the rectangle; the totals line adds "1 tile 6x6 (plaque, part 10202)".
  `sheets counts` counts it in its section.
- Parts list: one lot, part 10202, part type `plaque_tile` (label "tile 6x6"), quantity 1, cited
  IDs from `plaque_parts.json`, `kit_supply` 0, so the one-kit top-up buys it; 36 fewer square
  tiles; exports carry the tile's BrickLink item (`bricklink.item_no` from `plaque_parts.json`,
  which can differ from the part ID, as 6141 is item 4073) in color 11 and Rebrickable 10202
  color 0; `parts/partslist.py` `_citations()` also resolves the lot's citation ids from
  `plaque_parts.json` (today it reads only the part_numbers pages and part_colors citations and
  would drop them); leftovers unchanged (kit map elements only, feature 014). Lot order 6141,
  98138, 3070b, 10202.
- Prices: lot `10202:26`; `recipe_lots()` adds it only for recipes that name a corner (none of
  the bundled ones), so the committed snapshot's lot set does not change; without a row the
  estimate is incomplete with that lot unpriced (feature 011). `all_cited_lots()` keeps looping
  only over the part_colors parts (`PartColorTable.for_part("10202")` would raise), so
  `--all-colors` is unchanged. Refreshing needs the owner's BrickLink credentials (owner step);
  because `--lot` writes a `named` snapshot of only the listed lots, the owner lists every
  `recipe_lots()` lot plus `10202:26`.
- Sheets: `build_sheet_set` accepts a layout that lacks exactly the recorded plaque studs (it
  requires all 10,240 positions today).
- `map cells`: plaque studs are `P` in `cells` and a `plaque` block `{part_id, color, rgb,
  cells}`. `palette.js` is not changed: no site variant has a plaque, so the chooser never sees
  `P` cells.
  `validate`: accepts a recorded plaque when exactly its studs are absent and they are margin
  studs of the template; anything else is a mask error.
- Web: none of the site's variants has a plaque (spec).
- Constitution 3.0.0 Principle I: "maps vary only the colors in each class and the content of
  the margin" and margin cells "hold labels or a background"; the plaque is margin content (a
  label), and the margin class's part stays 3070b. Pass, noted as a close call in plan.md.

## R16. Performance (decided)

Building the map dominates (0.1 s for ocean-sst, 4 s for living planet, measured); legend,
layout and rendering of one set are small vector pages, well under SC-007's 5 s. The web
prebuild adds one sticker set per map, not per combination.

## R17. Documentation (decided)

`cli/README.md` (map stickers, the sticker table, plaque parts, printing notes), `README.md`,
`docs/vision.md` (017 row: built), `web/README.md`, the recipe format contract note, and the
CLAUDE.md / AGENTS.md project paragraph, in the implement phase.

Sources consulted on the web during planning: [LDraw file format](https://www.ldraw.org/article/218.html),
[LUGNET FAQ: dimensions](https://www.lugnet.com/~330/FAQ/Build/dimensions), Internet Archive
availability API for the BrickLink and Rebrickable part pages named in R10.

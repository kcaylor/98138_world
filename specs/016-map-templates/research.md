# Research: Map templates (016)

Planning evidence and decisions. Numbers marked "measured" come from a scratch run on 2026-11-23
of `cli/tools/projection_study` code with pyproj 3.7.2 (PROJ 9.5.1) against the cached, pinned
`etopo2022-surface-10m` file; the scratch scripts stayed outside the repository.
Not affiliated with or endorsed by The LEGO Group.

Each item is tagged **decided** (logged under the run policy). R2 and R13 were raised as
escalations during planning and decided by the agent as close calls; the owner can still reverse
either before implementation.

## R1. Run time without pyproj (decided)

- Today the kit path bins every source pixel into the kit cell that contains it
  (`maps/reproject.py` `source_cells`: `rows_for_lat`, `cols_for_lon` of
  `maps/projection.py`); `sampling = "bilinear"` interpolates at each cell centre
  (`cell_centres`); no-data, overrides and ice use cell centres (`maps/nodata.py`
  `cell_latitudes`, `maps/overrides.py`, `maps/ice.py`). So a template must answer two questions:
  which stud contains a location (forward), and where each stud is (inverse).
- Forward Winkel tripel is closed form (the mean of the equirectangular projection at standard
  parallel φ1 and Aitoff; Snyder, *Flattening the Earth*, 1993; PROJ `wintri`). A numpy version of
  six lines matched pyproj on 200,000 random points to 1.8e-15 (measured), including the
  antimeridian edges.
- The inverse has no closed form. The maintainer tool computes each stud's location with pyproj
  and the template data file stores it (R4).
- Decision: `lego_image_processor/templates/winkel.py` implements the forward formula in numpy.
  The template file stores the fit (scale, centre) and every on-globe stud's latitude and
  longitude, plus 24 pyproj check points that the loader verifies against the numpy formula
  (|Δ| < 1e-9). pyproj goes only into the `maintainer` Poetry group. `map build`, the web image and
  `web/requirements-build.txt` gain no dependency.
- Alternatives rejected: pyproj at run time (a new runtime and web build dependency, ~30 MB of
  PROJ data); a Newton inverse at run time (more code to validate, and the stored locations make
  it unnecessary); a lat/lon→stud lookup table (megabytes, and inexact).

## R2. Fitting Winkel tripel to the board (decided; agent, close call)

- The study fits the projection to the board from an extent sampled on a 0.25° lat/lon grid
  (`projection_study/raster.py` `Proj._extent`). With the central meridian at 11.1° E the
  antimeridian (168.9° W) is not on that grid, so the sampled width is 0.07 % short and the
  centre is off by 0.0004 units. That fit gives the spec's numbers: 2,554 land, 5,706 ocean,
  1,980 margin, ring 286, corner blocks 15 × 13.
- The exact extent is published: x = ±(π/2)(1 + cos φ1), y = ±π/2 (aspect 1.6366). With it
  (measured): **2,553 land, 5,691 ocean, 1,996 margin, ring 288, corner blocks 14 × 14**,
  modules 18 / 22 / 0, ground area p90/p10 1.91, and a land/ocean/margin mask that is exactly
  symmetric left–right and top–bottom in its on-globe outline. Leftovers with one kit become 511
  White plates and at least 2,375 tiles (spec: 510 and 2,360).
- Decision (agent, 2026-11-23): the exact extent ("a published projection definition", Principle I).
  The sampled extent is an artefact of the study's grid, not a property of the projection, and the
  owner reviews and confirms the generated layout anyway (US2). Acceptance
  then uses the confirmed template's counts, as US1-1 and SC-002 already allow. The spec's figures
  in Context, US1-1 and Assumptions become approximate. Alternative: reproduce the study's
  sampled fit exactly (the spec's numbers, but an arbitrary sampling artefact in the data file).

## R3. Where template data lives (decided)

- `cli/src/lego_image_processor/data/templates/winkel-tripel.json`: the template (format in
  `contracts/template-file.md`). `data/templates/winkel-tripel-ice.json`: its ice regions, the
  same format as `data/kit_31203_ice.json` plus `template_id`. Both are package data with a
  `source` block and the disclaimer (Principle I, constitution "Technical Constraints").
- The kit template `kit-31203` is built in code from the files it already has
  (`lego_world_map_land_sea_mask.json`, `kit_31203_projection.json`,
  `kit_31203_arrangements.json`, `kit_31203_inventory.json`, `kit_31203_ice.json`). It needs no
  new file and no confirmation record: it is the reference (Principle I). Nothing it reads changes.
- Classes are stored as 80 strings of 128 characters (`L`, `O`, `M`), one board row per line, so
  the file reads as a picture and diffs by row. Locations are two 80 × 128 arrays (`lat`, `lon`,
  4 decimals, null on margin studs), one board row per line. Expected size about 170 kB.
- Ring, module counts and corner blocks are derived at load time from the classes and checked
  against the counts the file records.
- Only one margin part exists: 3070b (`MARGIN_PART_ID`). The loader requires land 6141, ocean
  98138, margin 3070b, a board of whole 16 × 16 modules, and, for now, 8 × 5 modules (parts lists,
  sheets and frames are 128 × 80).

## R4. Generating and checking a template (decided)

- New maintainer tool `cli/tools/maptemplates` (`PYTHONPATH=tools python -m maptemplates …`),
  built on `projection_study.raster` (`Proj`, `rasterise`, `classify`). It sets the exact extent
  from `templates/winkel.py` (R2) instead of the sampled one.
- Method (FR-017, the study's): 4 × 4 subsamples per stud, each inverse-projected and kept only
  if the forward round trip returns within 1e-6 of the board scale; on the globe when ≥ 50 % of
  subsamples are; land when ≥ 50 % of on-globe subsamples have ETOPO elevation > 0 m.
- Stud location: the inverse of the stud centre; for the 12 on-globe studs whose centre falls
  just outside the outline (measured), the spherical mean of their on-globe subsamples.
- The file records the projection (PROJ string `+proj=wintri +lat_1=50.4598 +lon_0=11.1 +R=1`,
  φ1, λ0, citation), the fit, the board, the dataset (id, version, URL, SHA-256, citation,
  license), the method and thresholds, pyproj and PROJ versions, the generation date, corrections
  and confirmation.
- `build --check` regenerates from the cached dataset, applies the committed corrections and
  compares classes, locations, fit, check points, counts and source (except `generated_on`);
  it prints "no differences" and exits 0, else lists the differences and exits 1 (the
  `kit31203 fit-projection --check` and `partcolors build --check` pattern).
- pyproj pin: `pyproj = ">=3.7,<3.8"` in `[tool.poetry.group.maintainer.dependencies]` (MIT).
  pyproj 3.8 requires Python ≥ 3.12 and the project supports 3.11; Winkel tripel needs no PROJ
  9.6 feature (only the study's Spilhaus did). `projection_study/README.md` is updated to match.
- Tool tests run offline without pyproj: the pure parts (corrections, document writer,
  differences, flags) use a small numpy plate-carrée projection object; the one end-to-end
  Winkel test is skipped when pyproj is not installed.

## R5. Review, corrections and confirmation (decided)

- `maptemplates generate` writes the candidate and a review sheet (PNG) plus a flags list (JSON)
  to `<cache>/templates/` by default, outside the repository (FR-017). The sheet shows every stud
  by class, the outline ring, module lines and section names A1–H5, and highlights flagged studs.
- Flags (measured): 194 studs with a land share between 40 % and 60 %; 97 water studs in 20
  groups not connected (4-neighbour) to the main ocean, the largest of 33 studs (the Caspian Sea).
- Corrections are recorded in the template file as `{row, col, class, reason}` (FR-018; the
  `tools/kit31203/overrides.json` pattern). `margin → land/ocean` is allowed only for a stud with
  at least one on-globe subsample (it needs a location); a correction that sets the class the
  generator already gives is an error (stale).
- Confirmation is `{"role": "project owner", "date": "YYYY-MM-DD"}`, no personal name (spec
  Clarifications). The tool writes it only with `write --confirmed-on DATE`, run after the owner
  says so; any change to classes or locations clears it. The loader refuses to build on a
  template whose confirmation is null (FR-004).
- Lifecycle: candidate (outside the repo) → committed, unconfirmed (tests use a temporary copy
  with a test confirmation) → corrections → confirmed. The owner's review is a blocking step in
  the tasks: the agent generates the sheet, stops, and asks.

## R6. Sampling data on a template (decided)

- `TemplateProjection` (`templates/geometry.py`) offers what the kit projection offers to the
  map code: `height`, `width`, the flat stud index of source locations (forward projection,
  `floor` to a stud; −1 off the board or on a margin stud), stud locations and |latitude|.
- `maps/reproject.py`, `maps/nodata.py` and `maps/overrides.py` gain a template branch selected
  by the projection's type. The kit branch keeps its arithmetic line for line (R9). Map builds
  never read `maps/ice.py`. It gains only a loader for a template's ice file, used by `map cells`
  (R18).
- `mean` sampling: forward binning, as for the kit. Measured with the exact fit: every on-globe
  stud receives at least 106 ETOPO 10′ pixels; with a 2° grid (ERSST) 52 of 8,244 on-globe studs
  get no node and take the nearest value, as kit cells do (reported as `filled`).
- `bilinear` sampling: interpolation at the stored stud locations (margin studs are skipped).
- Points grids (NSIDC) bin by forward projection of each point. Source grids are at most
  1080 × 2160 here; the forward step runs in chunks of 10⁶ points to bound memory.
- A recipe whose layer reads a dataset whose registry entry has `format = "kit-design"`
  (`kit31203-design`, used by `official-31203`) cannot be sampled on another template (R8).
  `templates.compatibility()` tests `entry.format == "kit-design"`; the registry has no other flag
  for it. The `on_kit_grid` attribute exists only on a decoded `SourceGrid`.

## R7. Neighbourhood rules on a template (decided)

- Shadow: `shadow_mask(land) & ocean`, so a land stud whose eastern neighbour is margin casts no
  shadow (spec Edge Cases). On the kit `ocean = ~land`, so the result is the same.
- Halo, `mix` and `blend` already act only inside their layer's mask; margin studs are never in a
  mask, so they never take a layer color. Nearest fill uses only layer studs as sources.
- The Winkel outline is convex, so the straight-line neighbourhoods (Euclidean distance for the
  halo, nearest fill) never reach across the margin to a far part of the globe. There is no wrap
  at the left and right edges, as on the kit since feature 007.

## R8. Building on a template (decided)

- Resolution (FR-006): `--template` > recipe `template` > `kit-31203`; the report records
  `template_source` (`option`, `recipe`, `default`) only for non-kit builds (the feature 009
  `arrangement_source` pattern).
- Errors (FR-011, Edge Cases), all exit 1 with the disclaimer last: unknown template in a recipe
  (recipe error naming the confirmed templates); unknown `--template` (Click usage error, exit 2,
  like `--arrangement`); unconfirmed template; resolved arrangement other than A; a layer reading
  a `format = "kit-design"` dataset (suggests `official-31203-bathymetry`).
- An explicit `--arrangement A` with `--template winkel-tripel` builds an ENSO recipe (the option
  wins over the recipe's `B`, feature 009). The web does not offer those variants (spec US3).
- `compare_official` (automatic for `official-31203*` ids) is off on non-kit templates; an
  explicit `--compare-official` there is an error (the official design is on the kit grid).
- `[margin]` settings on a kit build are ignored, with one stdout line saying so.

## R9. Kit outputs byte-for-byte unchanged (decided)

- Code: every change is a branch taken only when the template is not the kit; the kit path keeps
  its arithmetic, key order and text. New JSON keys (`metadata.template`, `template`,
  `margin_positions`, `square_tile` counts, `template_source`, cells `M`, `margin`, palette part
  3070b) are written only for non-kit outputs. `maps/cells.py` `part_palette()` lists only the
  template's parts (6141 and 98138 for the kit), so the new 3070b rows never reach kit
  `cells.json`.
- Golden test, written first: before any production change, a harness
  (`maptemplates kit-golden`) builds all 8 bundled recipes × A, B, C on the kit from the dataset
  fixtures with a fixed layout `generated_at`. It writes digests of:
  - layout JSON and report JSON (fixed `generated_at`);
  - preview pixels and PNG bytes;
  - parts lists (full, `--kits 1`), BrickLink XML and Rebrickable CSV (both);
  - `parts estimate` JSON and text on the synthetic fixture snapshot
    (`cli/tests/fixtures/prices/bricklink_price_guide.json`, fixed `--as-of`);
  - section counts JSON and `cells.json`;
  - the `map build` and `map check` text output, with temporary paths replaced by a placeholder;
  - sheets as SVG text (Letter, every variant) and PDF bytes (Letter, A only). PNGs are also compared as decoded pixels and
  sheets as SVG text, so an encoder upgrade shows up as a byte change, not a content change. The
  digests are committed as `cli/tests/fixtures/golden/kit_outputs.json` (+ `.source.json` naming
  commit `af3ce57` and the library versions); `tests/integration/test_kit_outputs_unchanged.py`
  rebuilds and compares. `kit-golden --fixtures` points a temporary registry at
  `cli/tests/fixtures/datasets/` exactly as `tests/conftest.py` does (that helper moves to a
  module both import), so the tool and the test build the same thing.
- Web golden: the web test session builds the small site (official-31203, ocean-sst,
  ocean-el-nino). A committed digest list, made before the web changes, covers every kit
  variant's timestamp-free files byte for byte (previews, exports, `cells.json`). Its layout,
  parts lists (`parts.json`, `parts-1kit.json`) and manifest entry are compared after removing
  `generated_at` and every checksum that derives from the layout: `layout_sha256` inside the
  parts lists, and the `sha256` and `bytes` of each manifest file entry whose file embeds the
  layout checksum or a timestamp (layout, parts lists, sheets). The CLI golden covers the PDFs.
  The list also holds the top-level manifest `part_labels` of the kit-only site, and the rendered
  HTML of each kit map page with content-versioned asset tokens normalised.
- Real data: `maptemplates kit-golden --cache-dir …` run on a checkout of `main` and on the branch
  with the cached real datasets must give identical files (quickstart step 10). This covers the
  large datasets the fixtures stand in for.
- `part_colors.json` and `part_numbers.json`: the existing 6141 and 98138 blocks and citations
  must stay identical (a unit test compares them with digests the Phase 0 golden recorded from
  commit `af3ce57`); new rows,
  snapshots and citations are appended.

## R10. Part 3070b reference data (decided)

- `tools/partcolors` adds part 3070b with the same five join rules: the pinned Rebrickable
  elements and colors snapshots, LDraw `LDConfig.ldr` and the BrickLink color guide already
  pinned, plus a new pinned archived BrickLink catalog page for item 3070b (rule 5). All 3070b
  rows have `in_kit: false`; the "kit colors missing" rule applies to kit parts only.
- `tools/partnumbers` adds 3070b from pinned archived BrickLink and Rebrickable pages for 3070b.
  For a part that is not in the kit, the two kit-inventory rules (BrickLink item in the
  inventory's part IDs; design IDs from the inventory) are replaced by: BrickLink item equals the
  project ID or lists it as an alternate, and LEGO design IDs are those Rebrickable lists (3070b
  is LEGO design 3070, so "design IDs include the part ID" is a kit-part rule).
- Fetching the two archived pages needs the network once (maintainer, like feature 005). Risk:
  if the Internet Archive has no copy, the owner is asked for another pinned source.

## R11. Layout format additions (decided)

- Positions: a third part type `square_tile` with `lego_part_id` `3070b`
  (`layout/position.py` `PART_ID_FOR_TYPE`). The stud's class follows from its part (one part per
  class, Principle I); `metadata.template.parts` maps classes to parts, so FR-010 needs no
  per-position class field.
- `metadata.template` (only non-kit): id, title, projection name and PROJ string, board, parts,
  counts, `dataset` (the template's dataset provenance: id, version, title, publisher, license,
  citation, doi from the registry entry `etopo2022-surface-10m`), and `source` (file name,
  SHA-256 of the template file, `layout_sha256`, confirmation). The report's `citations`, the
  sheets' provenance and `cells.json` carry the same dataset for template builds, because ETOPO
  2022 decided land and ocean (Principle IV); kit outputs are unchanged.
  `metadata.margin_positions` and `statistics.margin_tile_count` and the `square_tile` key of
  `color_frequency_by_part_type` appear only for non-kit layouts. `metadata.arrangement` is A,
  as written today. Layouts without `metadata.template` read as the kit (Clarifications).
- `metadata.map.margin`: part, margin color, ring color, cells per role (margin, ring).

## R12. Margin treatment (decided)

- Recipe: top-level `template = "<id>"` and a `[margin]` table with `color` (default
  `lego_black`) and an optional `ring` (a color key). CLI: `--template`, `--margin-color` and
  `--ring-color` (`none` turns a recipe ring off) on `map build`, `map check` and `map cells`.
  Options win over the recipe.
- Colors must be cited colors of 3070b; margin and ring must differ. Errors name the option or
  key path, list the available 3070b color keys, and point to `kit part-colors --part 3070b`
  (spec Edge Cases).
- Ring: margin studs with an on-globe 4-neighbour (`rim_cells` of the study, moved to
  `templates/board.py`; `projection_study/raster.py` imports it from there).

## R13. Previews (decided; agent, close call)

- Every preview today draws one square per stud (`maps/preview.py`; the web caption says "One
  square per stud"). FR-012 asks for rounds on land and ocean and squares on the margin. Drawing
  rounds on kit previews would change every kit preview, which SC-001 forbids.
- Decision (agent, 2026-11-23): shapes only for non-kit layouts, which meets FR-012 and SC-001
  together. `write_preview` draws, at 4× and downsampled,
  each on-globe stud as a round (diameter 0.95 of the pitch) on Black (the kit's base color) and
  each margin stud as a full square; kit previews stay byte-for-byte the same. The palette
  chooser draws the same shapes for template variants. Alternative: round studs on kit previews
  too, as a separate owner-approved change to kit outputs.
- Note (agent, 2026-11-23: main 6038d9c): the owner made that change on main. Commit 6038d9c
  ("Round studs on black for map previews; thumbnails stay square", spec 008 amended) draws every
  map preview as round studs on black: `write_preview(..., style="round" | "square",
  background=(0, 0, 0))`, diameter 0.9 of the pitch, 8× supersampled, `map build --preview-style`;
  the web thumbnails stay square and the palette chooser canvas draws rounds. So the "kit previews
  unchanged" half of this decision is moot: 016 now follows main's style for template previews,
  and kit previews match main byte for byte. One code path draws every stud: in the round style a
  template's margin studs (part type `square_tile`) get full coverage, so they are squares in the
  margin or ring color, and land and ocean studs are main's rounds on main's background (pure
  black, not the cited Black of the margin tiles); `style="square"` draws every stud square, the
  template's too. The 0.95 diameter, 4× supersampling and Black background above are replaced.
  The kit golden was re-based on 6038d9c from an unmodified checkout (only the previews changed;
  run-state.md).
- Note (owner, 2026-11-24: margin shade): match pure black. In previews, margin studs whose color
  is LEGO Black are drawn in the preview's background color (pure black by default, as main
  6038d9c draws the gaps between rounds), so a Black margin blends into the background instead of
  showing the cited Black RGB (5, 19, 29) a shade lighter; other margin colors and the outline
  ring keep their cited colors (a Black ring around a margin of another color stays cited Black).
  `write_preview` applies it in both styles, with the `background` it is given (so the square web
  thumbnails agree); the palette chooser canvas (`palette.js` `drawStuds`) leaves Black margin
  cells as its black background. Only the drawing changes: layouts, parts lists, exports, sheets
  and `cells.json` still name and use LEGO Black's cited color. Kit layouts have no margin, so kit
  previews are unchanged (SC-001).

## R14. Parts lists, exports and leftovers (decided)

- Lots: part order 6141, 98138, 3070b (`parts/partslist.py` `PART_ORDER`, `PART_TYPE`); 3070b
  lots resolve through `part_colors.json` and `part_numbers.json` like the others, so exports
  carry BrickLink item 3070b and Rebrickable 3070b with cited color IDs.
- Kit supply of 3070b is 0 (`kit/inventory.py` `supplied_for`), so the one-kit top-up buys every
  square tile (US1-6). Leftovers iterate kit elements only, unchanged (spec Assumptions).
- The parts list `layout` block gains `template` (id, title) for non-kit layouts.

## R15. Price estimates (decided)

- `prices/lots.py`: part 3070b in `PART_ORDER`/`PART_TYPE`; `--lot` accepts `3070b:26`. The
  lot pattern `_LOT_RE` is `^(\d+):(\d+)$` today and must be widened to `^(\d+[a-z]?):(\d+)$`;
  `parse_lot` keeps rejecting parts not in `PART_ORDER`. `recipe_lots()` adds each bundled recipe's margin
  colors (default Black, so one new lot) so the next `parts prices fetch` covers Winkel builds.
  `prices/snapshot.py` accepts 3070b lots, sorted after 98138.
- No snapshot is committed yet (`Dockerfile` builds `--no-prices`). Refreshing needs the owner's
  BrickLink credentials from environment variables; this feature never calls BrickLink. Until a
  refreshed snapshot exists, a Winkel estimate is marked incomplete with the square tile colors
  unpriced (011 behaviour); kit estimates are unchanged.
- Tests: the existing synthetic fixture stays byte-identical (its Winkel estimates are
  incomplete); `tools/fixtures011` writes a second synthetic fixture with a 3070b Black lot for
  the complete path.

## R16. Build sheets and sections (decided)

- A Winkel board uses the kit's 40 sections and three frames unchanged, hung as A (SC-004);
  margin studs sit inside those sections (every module touches the globe: 18 full, 22 partial,
  0 empty). No section or frame data is added.
- Section pages draw margin studs as squares (`Rect`) with their lot numbers; the overview map
  draws small squares; the legend uses a square swatch and the label "tile 1x1 square"; the
  totals line adds "N tiles 1x1 square (margin, part 3070b)"; the subtitle and the arrangement
  sentence name the template and say the frames cannot be re-hung. Kit pages keep their text.
- `sheets counts` JSON gains `template` for non-kit layouts.
- The provenance section adds a line for the template (id, projection, file SHA-256,
  confirmation) and its dataset (id, version, title, license, citation).
- `sheets/legend.py` `PART_LABEL` gains `square_tile` in the same change that adds the part type
  to `parts/partslist.py` `PART_TYPE`. The web prebuild's `_part_labels()` maps every
  `PART_TYPE` through `PART_LABEL`, so a part type without a label raises `KeyError`. From that
  change on, `_part_labels()` lists only the parts the site's variants use, so a kit-only
  manifest keeps exactly the 6141 and 98138 labels (web golden).

## R17. Layout validation (decided, FR-016)

- For a layout with `metadata.template`, the mask check compares each position's part with the
  template's class part (`mask_mismatch` with `template` set) instead of the kit mask.
- Colors and quantities are still checked against one kit 31203 (what `validate` reports), so
  square tiles appear as `color_unavailable` for part 3070b with no suggestion: a Winkel map
  always needs pieces beyond the kit. Kit layouts validate exactly as before.

## R18. Ice regions and the palette chooser on templates (decided)

- `maptemplates ice-mask winkel-tripel [--check]` derives the template's ice regions with the
  kit's rules (`maps/ice.py`: land ice in Antarctica and the Greenland box; sea ice from the
  ERSST v5 1991–2020 warmest month ≤ −1.5 °C, or no value poleward of 60°) using the template's
  locations and forward binning; it needs no pyproj (FR-020b).
- The ice file records the template's layout digest (`source.template_layout_sha256`;
  contracts/template-file.md), not the file's SHA-256. The digest leaves out the confirmation
  and the correction records, which count only through `classes`. So the file made from the
  committed, unconfirmed template stays valid after the owner confirms, and so does a test copy
  with a test confirmation. It is regenerated only when corrections change classes (or a
  regeneration changes locations); `ice-mask --check` tells.
- `map cells` on a template: `cells` uses `M` for margin studs; new blocks `template` and
  `margin` (colors and the ring cells); `palette` adds part 3070b; `ice` comes from
  the template's ice file (FR-020a). `static/palette.js` keeps `M` studs in their margin colors,
  leaves them out of class counts and ice, and draws rounds and squares for template variants.

## R19. Web (P2) (decided)

- Eligibility comes from the library (`templates.compatibility(recipe, template)`): the five maps
  `official-31203-bathymetry`, `ocean-sst`, `land-elevation`, `living-planet`, `rainfall` are
  eligible; `official-31203` (kit-grid dataset) and `ocean-el-nino`/`ocean-la-nina` (arrangement
  B) are not (spec US3-1, tested).
- The prebuild builds template variants only for confirmed templates, at
  `maps/<map>/<template-id>/`, with the same files as kit variants. Manifest additions are
  additive and keep `format_version` "1": a top-level `templates` list and
  `maps[].template_variants.<template-id>`; `maps[].variants` stays exactly A, B, C. Kit variant
  files and entries are unchanged (R9).
- Routes: `/maps/<map>/<template-id>` and its `preview.png`, `thumb.png`, `cells.json` and
  `download/<kind>`; unknown ids are 404. The map page offers "Winkel tripel" beside A, B and C,
  says the frames cannot be re-hung, and works without JavaScript.
- Size and time: 24 → 29 variants, about +20 % build time and output size.

## R20. Corner labels (moved to feature 017)

- The owner decided on 2026-11-23 that labels are not built from square tiles. They become a
  printed sticker on a black tile in feature 017 (map stickers), which can also place a plaque in
  a Winkel margin corner after 016 ships. 016 has no label font, placement or label options.
- Room in the margin, kept as input for 017's corner plaque (measured): with the exact fit (R2),
  each corner's free region (the margin minus the outline ring, per board quadrant) has a largest
  clear block of 14 × 14 studs (15 × 13 with the study's sampled fit), and the widest band of 5
  rows in a corner is 27 studs. The template file records the corner blocks (`counts.corners`),
  and `template show` prints them.

## R21. CLI-first exposure (decided)

- New group `template`: `template list` (id, title, status confirmed/unconfirmed, counts),
  `template show ID [--format json]` (projection, board, counts, ring, corners, source,
  confirmation), `template locate ID LAT LON` and `template locate ID --stud ROW COL` (FR-005:
  the stud for a location and the location of a stud).
- `kit part-colors --part` accepts 3070b. `layout arrange` on a non-kit layout stops with the
  re-hang error (FR-011).

## R22. Documentation (decided)

`README.md` line 3 (constitution follow-up), `cli/README.md` (template commands and options),
`docs/vision.md` (016 built), `web/README.md`, `docs/deploy.md` (template variants need a
confirmed template), `cli/tools/projection_study/README.md` (pyproj pin), and the CLAUDE.md /
AGENTS.md project paragraph (in the implement phase).

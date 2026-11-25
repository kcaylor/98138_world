# Run state: 017-map-stickers

Source: prompt (owner, 2026-11-23: stickers instead of brick labels; four scoping answers)
Phase: done (converge round 1: T092 appended and implemented; every task done but the owner's T091)
Status: done; owner steps open: T091 price refresh, commit of the work since merge 0150441, push/PR, deploy
Updated: 2026-11-25

Worktree: ../98138_world-017 (branch 017-map-stickers, from main af3ce57,
fast-forwarded to main 6038d9c on 2026-11-23: round studs on black for all map previews); 017 committed
on its branch (e4142bb guard golden, 3257c9d feature); the local branch 016-map-templates (f33b464)
merged into it on 2026-11-24 (T053, T054), merge commit 0150441 by the coordinator, which also holds
016's kit goldens as T054 regenerated them; nothing pushed. Everything since the merge, Phase 5
(T055-T082), Phase 6 (T083-T090) and converge round 1 (T092, docs/runbook.md), is uncommitted in the worktree (76 tracked files modified, 9
new files), waiting for the owner's go-ahead to commit (run policy "commit: no").
Scope of this run (owner): draft the spec; stop after clarify for review.
Owner said "plan for 017" (2026-11-23): run plan, tasks and analyze; stop before implement.

## Owner steps still open
- T091: refresh the BrickLink price snapshot with every default lot plus `--lot 10202:26` (the
  owner's credentials; tasks.md has the command); best together with 016's T109. Until then no
  snapshot is packaged, so `parts estimate` needs `--prices FILE` and the web prebuild
  `--no-prices` (or `--prices`).
- Commit the uncommitted Phase 5 and Phase 6 work on the branch, then push and open the pull
  request (it must say that 017, merging second, regenerated 016's kit goldens: T054, research R13).
- Deploy (`fly`), after the merge to main: the owner's step, not planned here.
- T042 and T081 are done (texts approved 2026-11-24; plaque offset confirmed 2026-11-25).

## Open questions
- none

## Decisions
- converge round 1 (agent, 2026-11-25): every FR (001-026), SC (001-010), the 23 acceptance
  scenarios, the edge cases and the six contracts assessed against the code with targeted runs on
  cached real data (session scratchpad 017/converge/): sticker sets of all eight maps identical for
  A, B and C (to_dict without arrangement, both SVGs) and their legends as the spec sets out;
  PDF, SVG and JSON content, metadata, fonts, no image; byte-identical outputs across two
  PYTHONHASHSEED values; the error table (not cached exit 3, nothing written; non-Latin-1;
  too-long line; OUT a file); `partcolors plaque-parts --check` and `partcolors build --check` "no
  differences"; the wheel ships data/plaque_parts.json and stickers/; Winkel stickers; the
  plaque through build, report, validate, parts list and exports, estimate (incomplete without a
  10202 row, complete with the plaque fixture), sheets, counts and `map cells`, and its kit and
  corner errors. Findings: one LOW partial (docs/runbook.md had no stickers or `--plaque` step),
  appended as Phase 8 T092 and implemented (new step 11, old 11-12 renumbered 12-13; the stickers
  panel in the local web section; a print-and-cut check; a troubleshooting line; every command
  run on cached data). Reported, no task: the web suite has no socket guard of its own (pre-existing
  since 008, offline by construction; SC-010); a plaque layout's parts list names Rebrickable
  colors.csv twice in its sources (part_colors.json cites it as `rebrickable-colors-snapshot`,
  plaque_parts.json as `rebrickable-colors`, as contracts/plaque-parts-file.md sets; merging them
  needs a contract change). Full suites after T092: CLI 3192 passed, 1 skipped; web 296 passed;
  guards G1-G4 and 016's kit goldens pass unchanged (git diff of both golden directories empty).
  Next: a second converge round should find nothing; then the owner commits, opens the pull
  request and runs T091
- T090 (agent, 2026-11-25): implement is complete but for the owner's T091; next phase converge.
  Who regenerated 016's kit goldens: 017, at T054 (cli/tests/fixtures/golden/kit_outputs.json and
  web/tests/fixtures/kit_variants_golden.json, in merge commit 0150441); neither golden nor 017's
  guard golden changed after it (git diff against HEAD is empty for both fixture directories)
- T089 (agent, 2026-11-25): full suites with the CLI socket guard on (cli/tests/conftest.py): CLI
  3192 passed, 1 skipped in 150 s (T001 baseline 1551 passed, 1 skipped; T079 checkpoint 3182/1;
  +10 from T082 and T087); web 296 passed in 82 s (T001 baseline 134; unchanged since T079). Guards
  (test_stickers_outputs_unchanged.py, G1-G4) and 016's kit goldens (CLI
  test_kit_outputs_unchanged.py, web test_kit_golden.py) pass unchanged. The web suite has no
  socket guard of its own (as on main since 008); it builds its site from the CLI's dataset
  fixtures and never fetches. Logs: session scratchpad 017/t082/t089-cli.txt, t089-web.txt
- T088 (agent, 2026-11-25): quickstart steps 1-12 walked on real cached data: steps 2-7 38/38
  (T044's script on the current tree, 017/t082/t088-steps-2-7.txt); step 8 against 6038d9c's
  outputs from T044: ocean-sst layout, report, parts lists, estimate, counts, cells, sheets PDF
  (42 pages) and SVG differ only in the recipe SHA-256 and its derived checksums, preview, XML and
  CSV identical (t088-step8-ocean-sst.txt); step 9: full prebuild `--no-prices` (29 variants, 13
  sticker sets: 8 kit, 5 Winkel; 345 kB of sticker files) and the service (TestClient): A, B, C
  panels identical, the Winkel pages show their own set and note, every sticker image and download
  200, unknown set or kind 404 (s09-s10-web.txt); steps 10-12 as T082. Docs fixed in quickstart.md:
  step 8 compares with 6038d9c (af3ce57's previews predate the round studs); step 11's `parts
  estimate` needs `--prices FILE` (no packaged snapshot before T091; the two fixtures named) and
  `validate` "passes" now reads "no mask mismatch; square tiles and the plaque tile beyond the kit
  (80.5%)"; step 12's misfit needs a template copy (every packaged Winkel corner fits). No
  behaviour mismatch found
- T087 (agent, 2026-11-25): FR-026 audit, tests added to tests/contract/test_disclaimer.py: the
  plaque parts file's two disclaimers; the Winkel sticker set (output, JSON, both stickers, SVG
  `<desc>`, PDF subject and page); every output of a plaque layout (`map build|check|cells
  --plaque`, `parts list|export|estimate`, `sheets build|counts`, `validate`, the SVG section page
  with "tile 6x6 (10202)"); no endorsement wording ("official", "endorse", "sponsor",
  "authoriz/s", "partner", "approved by") in any sticker text of official-31203, ocean-sst and
  ocean-sst on Winkel, nor on the two ocean-sst print sheets. Covered elsewhere and listed in the
  test's comment: `partcolors plaque-parts` output (test_plaque_parts_tool.py), all bundled sets
  and "no Official in a sticker title" (test_stickers_bundled.py), plaque errors
  (test_map_plaque_contract.py), the Stickers panel, about paragraph and footer
  (web/tests/test_stickers_page.py). Noted, not changed: official-31203's print sheet "Data"
  block cites its dataset by the registry title "Official LEGO 31203 World Map design grid" (004's
  datasets.json, as every output of that map does; plan decision "print sheet keeps registry
  citations"); its stickers do not
- T083-T086 (agent, 2026-11-25): docs in the existing style: cli/README.md (Features bullet;
  section "Map stickers": command, print sheet and printing at 100% on white sticker paper,
  cutting, 1 mm inset, legend, credit, fitting and Latin-1, the `[sticker]` table, plaque parts
  table with cited IDs and `partcolors plaque-parts --check`, `--template`, plaque in a margin
  corner with `--plaque`, `[margin].plaque`, the corner table, outputs and estimate; Python library
  lines; the maintainer-tools list); specs/004-map-recipes/contracts/recipe-format.md (017 note
  beside 012's and 013's); README.md (stickers for every map, the corner plaque, `cli/` list);
  web/README.md (sticker files, manifest `maps[].stickers.<template-id>` incl. `credit` and
  template sets, file names, routes, the panel); docs/vision.md (016's merge brought a 017
  "planned" row: updated to "built", no row added); CLAUDE.md and AGENTS.md (the same 017
  paragraph after 016's; Layout: `stickers/` and `kit/` plaque_parts.py; nothing removed; the
  paragraph names the large plaque as the smooth tile 4974). Also the contract
  contracts/in-margin-plaque.md "Layout JSON" (T082's validate rule) and `validate --help`
- T082 (agent, 2026-11-25): the offset stays as built (T081), so no placement change. Real data
  (cached; session scratchpad 017/t082/, script run_t082.py, results.txt): 139 of 139 checks.
  Step 10: `map stickers ocean-sst --template winkel-tripel` PDF and JSON: both lines end
  "Winkel tripel projection.", the large credit adds ETOPO 2022, no title says Official; the
  prebuild writes `stickers.winkel-tripel` for each of the 5 Winkel variants (credit lines with
  ETOPO 2022 once, also for living-planet, whose recipe already reads it). Step 11, each corner
  (top-left A1, top-right H1, bottom-left A5, bottom-right H5): `metadata.plaque` with the
  contract's rows and columns, 10,204 positions, exactly the 36 studs absent, every other position
  equal to the build without `--plaque`, margin 1,960 and plaque 1 in the statistics; `parts list
  --kits 1` one 10202 lot (needed 1, kit_supply 0, BrickLink 10202 / 11, Rebrickable 10202 / 0,
  last), 1,996 -> 1,960 square tiles, leftovers unchanged; `parts export` XML 10202 color 11 MINQTY
  1, CSV `10202,0,1`; `parts estimate` incomplete with 016's 3070b fixture (the --lot 10202:26
  hint), complete with the plaque fixture, and without `--prices` exit 1 (no packaged snapshot);
  `sheets build` puts the plaque in its section, the section SVG has the outlined "tile 6x6
  (10202)", `sheets counts` names the section; `validate` no mask mismatch; `map cells --plaque`
  36 P and 1,960 M with the plaque block. Step 12: `--plaque` on the kit exit 1 "the kit template
  has no margin", no file; unknown corner exit 2; a copied recipe with `template` and `[margin]
  plaque = "top-right"` places it "from the recipe", `--plaque none` gives 10,240 positions and no
  `metadata.plaque`, `--plaque bottom-left` wins, `--template kit-31203` ignores it with 016's
  note; a misfit (template copy with an ocean stud at row 75, column 7, as the contract test)
  exit 1 with the space needed and available (s12-misfit.txt). Buildability (the open item from
  T079): 016 counts its margin square tiles as not buildable with the kit (`color_unavailable`
  for 3070b, positions added to the score's violations; 016 research R17), so the plaque is made
  consistent, test first (test_validator.py `test_the_plaque_tile_is_not_buildable_with_the_kit`,
  `test_no_plaque_violation_without_a_plaque`; test_validate_contract.py two tests): a recorded
  plaque is `color_unavailable` with `part_type` `plaque_tile`, `part_id` 10202, `color_id`
  `lego_black`, `color_name` Black (from plaque_parts.json), `positions_required` 36 (the studs
  it covers, the score's unit), no suggestion; the score drops from 80.9% to 80.5% on a plaque
  layout, equal to the same map without a plaque. `validate` prints "Checking the plaque tile..."
  / "✗ tile 6x6 (part 10202) unavailable in kit (no kit has part 10202)" after the square-tile
  check and "Positions required: 36 (studs under one tile 6x6)"; `maps.margin.plaque_label`
  shared with `plaque_text`. On a kit layout a recorded plaque is also a mask mismatch, so its
  studs count twice there, as 016's square tiles on a kit layout do. Layouts without a plaque
  validate as before (tests)
- T081: in-margin plaque offset confirmed as built, one stud in from both board edges (rows 1-6 or
  73-78, columns 1-6 or 121-126), by the project owner, 2026-11-25 (user)
- implement T074-T079 (in-margin plaque: sheets, counts, cells, CLI wording; agent, 2026-11-24):
  Sheets: `build_sheet_set` accepts a layout lacking exactly `metadata.plaque`'s studs (a piece under
  the plaque: "layout has N position(s) under the plaque recorded in metadata.plaque"; any other
  absent position: today's message, plus " but the 36 studs under the plaque recorded in
  metadata.plaque" on a plaque layout); the plaque must lie in one section
  (`sheets.counts.plaque_section`, else "metadata.plaque: rows ..., columns ... are not inside one
  section (16 x 16 base)", exit 1 from `sheets build` and `sheets counts`). Section page: one Rect
  (tag `plaque`) in the lot's cited Black, outline grey 0.4 mm, 6 pitches minus the stud gap (47 mm,
  as the preview), lot number 16 pt bold and "tile 6x6 (10202)" (`PART_LABEL` + part id) 9 pt inside;
  no 1x1 studs there; count table row "Black (tile 6x6)" 1 with a square swatch (A5 total 221).
  Legend: square swatch (`disc` squares the plaque tile; `is_square` stays the 3070b test). Overview:
  one Rect (tag `map-plaque`, stud gap 0.2 mm, no stroke); totals "10,205 pieces: ..., 1,960 tiles 1x1
  square (margin, part 3070b), 1 tile 6x6 (plaque, part 10202);" and the how-to adds "the plaque tile as
  one outlined rectangle". `count_sections` counts the plaque lot once in its section (`sheets counts`
  JSON lists it); `SheetSet.plaque` (a `PlaqueMark`) carries entry and section. cells.json: `P` over
  `M`, block `plaque` `{part_id, color, rgb, corner, cells}` right after `margin` (rgb the tile's cited
  Black (5, 19, 29) from plaque_parts.json); palette unchanged; files without a plaque unchanged.
  CLI wording: `maps.margin.plaque_text(record)` "tile 6x6 (part 10202), Black, bottom-left, rows
  73-78, columns 1-6" (label and color from plaque_parts.json; the report's record has no color, so
  the tile's Black); 016's `Margin:` line counts the report's `margin.cells` margin + ring (1,960 with
  a plaque, the template's count without), then `Plaque: ... - from --plaque|from the recipe`;
  `Layout: ... (10,204 positions, ..., 1,960 margin tiles, 1 plaque tile)` (len(positions) only with
  a plaque). `parts list`/`parts estimate` header "10,204 positions and 1 tile 6x6 (plaque, part
  10202)" and Template line "...margin in 1x1 square tiles (part 3070b) and the plaque tile 6x6 (part
  10202), which kit 31203 does not have" (`parts.partslist.positions_text`, `template_text`,
  `plaque_lot_text`; JSON unchanged: `layout.positions` stays the board's 10,240); `parts export` adds
  "Plaque tile in the files: 1 tile 6x6 (plaque, part 10202); BrickLink 10202 / Black (11);
  Rebrickable 10202 / Black (0)"; `sheets build` Lots line ends ", 1 tile 6x6 (plaque, part 10202) in
  section A5"; `sheets counts` prints "Plaque: <plaque_text>; counted in section A5"; `validate`
  prints "Total positions: 10,204" and "Plaque: <plaque_text> (36 studs without a 1x1 piece)" for a
  plaque layout, and mask examples say "no piece" (absent stud) and "the plaque tile" instead of
  None/plaque_tile (other part types as before). `--lot` help adds "or 10202:26 (the in-margin
  plaque's tile 6x6)", `--all-colors` help "not the plaque tile 10202 (fetch it with --lot)". Estimate
  hint reworded to 011's "Hint: fetch ... with: <command>" form: "fetch the plaque tile with:
  lego-image-processor parts prices fetch --lot 10202:26, plus a --lot for every other lot the
  snapshot should hold (a --lot fetch writes only the lots it names; --all-colors does not fetch the
  plaque tile)"; the JSON note is the same sentence capitalised (was "Fetch the plaque tile: ...").
  Output without a plaque is unchanged (tests). Noted, not changed: `validate`'s buildability score
  divides by the board's 10,240 and counts the plaque's 36 studs as buildable with the kit (80.9% on
  bl.json), though the plaque tile is not in the kit. Real data (session scratchpad 017/plaque/,
  rebuilt with this code): map-build.txt, sheets-build.txt, sheet-A5-07.png, sheet-overview-01.png,
  sheet-legend-02.png, sheets-counts.txt, bl-counts.json (lot 12 in A5, total 221), bl-cells.json
  (36 P, 1,960 M), validate.txt, parts-*.txt. Checkpoint: CLI 3182 passed, 1 skipped; web 296 passed;
  guards (test_stickers_outputs_unchanged.py) and 016's kit goldens (CLI and web) pass unchanged, no
  golden file touched (agent)
- implement T069-T073 (in-margin plaque: parts, exports, prices; agent, 2026-11-24): the plaque
  lot is read from `metadata.plaque` (its studs carry no position): `partslist._plaque_lot`, needed
  1, `kit_supply` 0 (`supplied_for` is 0 for any non-kit part), sorted by `PART_ORDER` 6141, 98138,
  3070b, 10202 (`PART_TYPE["10202"] = "plaque_tile"`, `PART_TYPE_TEXT` and `sheets.legend.PART_LABEL`
  "tile 6x6"); IDs from `parts.resolve.resolve_plaque_tile` (plaque_parts.json's `PartNumbers` and
  `PartColor`, so the same `ResolvedColor`; a record in another color is an unverified lot with
  "no cited color for part"); `check_grid` refuses a `metadata.plaque` whose part is not the plaque
  tile (exit 1, "metadata.plaque: part '3958' is not the in-margin plaque tile (10202)").
  `_citations()` resolves each id from the part_numbers pages, then the part_colors citations, then
  plaque_parts.json `source.snapshots` (read only when an id is not found earlier), so kit lists keep
  their bytes and `bricklink-10202` and `rebrickable-colors` are added (the human `Sources:` list
  then shows "Rebrickable colors.csv (catalog download)" twice, once per id: same file, two ids;
  left as is, none dropped). Owned and missing CSVs: `owned_parts` adds 10202 when the layout
  records a plaque (016's rule: only parts the layout uses), and `parse_owned_text` reads its
  Rebrickable part and color and its element from plaque_parts.json; elsewhere a 10202 row is
  ignored and counted. Prices: `prices.lots` `PART_ORDER`/`PART_TYPE` add 10202, `PART_NAMES`
  "6141, 98138, 3070b or 10202" (the snapshot's part and order errors list it too); `lot_ref`,
  `lot_ref_by_lego_id` and so `parse_lot`/`named_lots` and the snapshot loader read the plaque tile
  from plaque_parts.json; `recipe_lots()` adds `10202:26` when `margin.plaque` is set (no bundled
  recipe: still 26 lots); `all_cited_lots()` loops only over `PartColorTable.parts` (unchanged).
  Estimates: `--all-colors` does not fetch the plaque tile, so a missing plaque lot gets its own note
  and table hint ("--all-colors does not fetch the plaque tile; fetch it with --lot 10202:26,
  together with a --lot for every other lot the snapshot should hold (--lot writes only the lots it
  names)", `wording.plaque_lot_hint`) and the --all-colors hint appears only for other missing lots.
  T071: tests/fixtures/prices/bricklink_price_guide_plaque.json (+ .source.json) = 016's 3070b
  fixture plus a synthetic 10202 Black row (SHA-256 2ca51cc0...); the two existing fixtures are
  byte-identical (checked before and after). Tests amended for 017: the exact `PART_ORDER` lists of
  016's test_partslist.py and test_lots.py check their first three parts (the new tests check all
  four). Left for T079: CLI wording (`parts list`/`estimate` "Template:" lines and `--lot` help
  still name only 3070b; `validate` still prints `None` as an absent stud's part type). Real data
  (session scratchpad 017/plaque/bl.json): `parts list` 12 lots, last "tile 6x6 Black (26) 10202 /
  Black (11) 1", 1,960 square tiles, 10,205 pieces; `parts export` XML `<ITEMID>10202</ITEMID>`
  color 11 `<MINQTY>1</MINQTY>`, CSV `10202,0,1`; `parts estimate` complete with the plaque fixture,
  with 016's 3070b fixture incomplete with only the tile unpriced. Checkpoint: CLI 3137 passed, 1
  skipped; web 296 passed; guards G1-G4 and 016's kit goldens (CLI and web) pass unchanged, no golden
  file touched (agent)
- implement T055-T058 (stickers on a template, agent, 2026-11-24): `Template.projection_title`
  in src/templates/__init__.py from `PROJECTION_TITLES` keyed by `projection["name"]`
  (`winkel.TITLE` "Winkel tripel"; the kit's `KIT_PROJECTION` "Equidistant cylindrical"), not a
  key of the template file (no template output changes); the web's `TEMPLATES` became the id
  tuple `("winkel-tripel",)` and the manifest's `templates[].projection` is
  `tpl.projection_title` (same text). `resolve_text(recipe, template)` appends " <projection>
  projection." after a full stop it adds when the line has none (`with_projection`); sources
  unchanged. `credits.template_dataset_entry(template)` looks the template's dataset id up in the
  packaged registry (`templates.PACKAGED_REGISTRY`, which 016 checks the template file against);
  `credit_lines(recipe, credits, template_dataset)`: on a template a `[sticker] credit` is
  followed by the template dataset's line (FR-025; no bundled recipe has both). `StickerSet`
  gains `credit_lines` (not in the JSON), which the prebuild's manifest `credit` uses. The legend
  reads the template's land and ocean studs and its ocean-only shadow (`legend._masks`, as
  `build_map`/`map_cells`); with the kit's mask, bathymetry's rank bounds on Winkel differed
  (test). JSON `template` on a non-kit template: `{id, title, projection: "Winkel tripel",
  dataset: "<dataset id>"}` (the full citation is in `credits`). The print sheet's Provenance and
  the SVG `<metadata>` add 016's `template_line(template.layout_record())` after the recipe
  (kit sets byte-identical: G1-G4 and 016's kit goldens pass). The T053 interim guard is gone;
  `sticker_set` refuses only a `MapResult` on an unconfirmed template (016 FR-004; `build_map`
  never makes one). `map stickers --template ID` (016's `TemplateType`, `TEMPLATE_HELP`; no margin
  options): after the `Recipe:` line 016's `template_lines` (Template, Margin), and on a template
  the legend line ends "the frames of a curved map cannot be re-hung." (016's `REHANG_RULE`)
  instead of "the stickers are the same for A, B and C." Real data (cached): the five Winkel sets
  fit on Letter and A4 (smallest text 5 pt, as the kit sets) (agent)
- implement T059-T060 (template sticker sets on the site, agent, 2026-11-24): `build_map_stickers(
  recipe, result, out, template=None)` makes the kit set as before or, with a template, the set
  of that template variant's `MapResult` into maps/<map>/stickers/<template-id>/ with file names
  `98138-world_<map>_<template-id>_<kind>.<ext>`; `build_site` adds it right after each template
  variant (one echo line per set), so `maps[].stickers` is the kit set, then one per template
  variant. `check_stickers(root, m, template_ids)` accepts the kit id and the manifest's listed
  templates (error names both). map.html: on a template page the panel's note reads "These are
  the Winkel tripel version's stickers: …" instead of "The stickers are the same for every
  combination." (kit pages unchanged). web/tests/kit_golden.py: `row_digests` digests a map row's
  `stickers` through `kit_stickers` (template variants' sets removed, each required once, no
  other non-kit set), so the kit golden passes without rewriting; tests that strip a site to
  kit-only (test_catalog, test_routes) also drop the template sticker sets (agent)
- implement T061-T068 (in-margin plaque: choice, placement, layout, report, validation, preview;
  agent, 2026-11-24): `MarginTreatment` gains `plaque` (a corner) and `plaque_source` (`option` |
  `recipe`), both defaulted, so 016's treatments compare as before; recipe `[margin].plaque`
  (`_MARGIN_KEYS` adds `plaque`, so the unknown-key rule lists "color, plaque, ring": 016's
  test_recipe_template.py assertion amended); `resolve_margin(..., plaque=)` (a corner wins with
  source `option`, `none` clears); `--plaque` (Click choice `PLAQUE_CORNERS` + `none`) joins 016's
  `template_options`, so `map build`, `map check` and `map cells` take it. Placement in
  src/maps/margin.py: `plaque_tile()` (plaque_parts small tile; IDs and size read there),
  `plaque_studs`, `plaque_misfit` (block, margin and ring overridable, so the module and ring checks
  are tested on their own: neither can fail on the 128 x 80 board with 016's exact-fit corner
  blocks), `place_plaque`, `plaque_for`, frozen `InMarginPlaque` (`layout_record`, `report_record`,
  `mask`, `positions`) and `PlaqueError(MarginError)` (`where` `--plaque` or `margin.plaque`), which
  `build_map` turns into `MapBuildError` (exit 1, "Cannot build <id>: --plaque: the kit template has
  no margin, so the plaque tile 6x6 (part 10202) cannot go in its <corner> corner; templates with a
  margin: winkel-tripel (choose one with --template)"). The kit check runs right after the template
  is resolved, before any data are read; a recipe corner on the kit is ignored and 016's
  `echo_template` note prints, as for any `[margin]` (also for `--plaque none` on the kit, as 016
  does for `--ring-color none`). `margin_cells` leaves the plaque out, so `metadata.map.margin.cells`
  and the report's `margin.cells` drop by 36; the report's `margin` is a copy with `plaque` `{corner,
  source, studs, part_id}` (`studs` the `{row, col, height, width}` block, as in `metadata.plaque`;
  `metadata.map.margin` gets no `plaque` key). `MapResult.plaque`. Layout: `PositionPlacementGrid(
  plaque=)`, `metadata.plaque` written last (after `template`), `plaque_positions`;
  `statistics.plaque_tile_count` 1 right after `margin_tile_count`. Decided: `metadata.total_positions`
  stays width x height (10,240, the board; `layout.total_positions` is the board everywhere) while
  the positions and `statistics.total_tile_count` are 10,204; `coverage_percentage` counts the
  plaque's studs as covered (100.0). Validator: on a template every board stud is checked: an absent
  stud not under the plaque is a mask mismatch with `part_type` null, a piece under the plaque
  expects `plaque_tile`, a plaque stud off the margin has `part_type` `plaque_tile`; on the kit only a
  recorded plaque's studs are mismatches, so kit layouts validate as before (a template layout that
  lacks a position without a plaque is now a mask error; 016 accepted it silently). Preview: one
  rectangle in the tile's cited Black (plaque_parts.json, (5, 19, 29)), in the round style 6 pitches
  minus the stud gap (inset 0.4 px each side at 8 px per stud, anti-aliased), in the square style
  filling the cells; `write_preview` refuses a layout lacking any position other than its plaque's
  studs (with or without a plaque; every map build is complete). Real data (cached):
  `map build ocean-sst --template winkel-tripel --plaque bottom-left` (session scratchpad
  017/plaque/bl.json, bl.png, bl-report.json): 10,204 positions, 1,960 margin tiles, plaque at rows
  73-78, columns 1-6. Left for T078/T079: the `Plaque:` line; the `Layout:` line still reads
  "10,240 positions, ..., 1,960 margin tiles"; 016's `Margin:` line reads the template's counts and
  still says 1,996 square tiles with a plaque (use the report's `margin.cells`, equal without one);
  `validate` prints `None` as the part type of an absent stud in its example lines. `map cells`
  with a plaque still marks its studs `M` until T077. Checkpoint: CLI 3106 passed, 1 skipped; web 294
  passed; guards G1-G4 and 016's kit goldens pass unchanged, no golden file touched (agent)
- T053/T054 checkpoint (merged tree, uncommitted, 2026-11-24): CLI 2932 passed, 1 skipped (016
  alone 2216/1, 017 alone 2265/1); web 269 passed (016 alone 209, 017 alone 193); guards G1-G4
  pass unchanged, guard golden untouched; no unmerged path and no conflict marker; constitution
  3.0.0 on the merged tree (agent)
- T053 (merge 016 into 017, agent, 2026-11-24): 7 conflicts resolved keeping both features; where
  they overlap 016's code is kept (catalog `_check_files`/`all_variants`, prebuild `_all_variants`
  and template loop, app `map_page`), and 017 adds its sticker parts beside it: recipe `_TOP_KEYS`
  holds `template`, `margin` and `sticker` (Recipe fields: 016's `template`, `margin`, then
  `sticker`); the prebuild builds each map's kit sticker set after its kit variants, then 016's
  template variants (which now pop `_result` too); map rows end `variants`, `template_variants`,
  `stickers`; `total_bytes` adds sticker files to every variant's files. A template page looks up
  its own template's sticker set (none until T060), so it shows no panel rather than the kit
  set. Interim guard until T056: `sticker_set` raises `StickerError` for a non-kit template
  ("sticker sets are made on the kit template kit-31203 only; <recipe> is built on <template>"),
  since the kit legend applied to a Winkel board would be wrong; tests
  `TestTemplateBuildBeforeT056` (test_compose.py) and `test_template_page_shows_no_kit_set`
  (test_stickers_page.py), to be replaced by T055/T059. Tests amended for 016's additions: Recipe
  fields (test_recipe_sticker.py), map-row key order (test_prebuild.py), `total_bytes` with
  template variants (test_stickers.py) and with sticker files (016's test_templates.py), the
  kit-id test (test_stickers.py). Auto-merged files checked (cli/map.py, maps/cells.py,
  test_disclaimer.py, map.html, about.html, style.css, test_palette.py, test_prebuild.py,
  test_routes.py, partcolors __main__.py, both conftests): no other semantic conflict; 016's
  `part_palette(parts=KIT_PARTS)` keeps G4's kit palette. 016's f33b464 (timestamp-free build
  comparison) came with the merge. pyproj 3.7.2 (maintainer-only) installed in cli/.venv from the
  uv cache for 016's tests; no runtime or web dependency added
- T054 (016's kit goldens regenerated, agent, 2026-11-24; scripts and outputs in the session
  scratchpad 017/t054/): (1) with G1-G4 green, 016's harness (`maptemplates.golden.kit_golden`,
  fixtures) on the merged tree with the eight bundled recipes replaced by their `prefix_bytes`
  (af3ce57 SHA-256, checked) gave a document byte-identical to the committed
  cli/tests/fixtures/golden/kit_outputs.json (0 differences); (2) web: the three session sites
  built by 016's branch code (git archive of f33b464) reproduced the committed web golden exactly
  (0 differences); the merged tree's sites (bundled recipes with their sticker tables), with
  recipe checksums and the checksums derived from them as placeholders, differ from them only by
  one Stickers panel on each of the 15 kit map pages, the about paragraph (3 sites), each map
  row's `stickers` block (5 maps) and `total_bytes` (3 manifests); previews, thumbnails, BrickLink
  and Rebrickable files identical; layouts, parts lists and cells.json differ only in the recipe
  checksum; palette.js, kit_golden.py and the harness are 016's unchanged. (3) Then regenerated:
  cli kit_outputs.json (`PYTHONPATH=tools .venv/bin/python -m maptemplates kit-golden --fixtures
  --out tests/fixtures/golden/kit_outputs.json`; 248 of 568 digests changed: map-build.txt,
  layout, report, map-cells.txt, cells, parts lists, estimate, counts, sheets SVG in all 24 and
  the 8 sheets PDFs; SHA-256 46709d5e..., was 8a865bb3...) with its .source.json (`regenerated`
  names the merge, the approved sticker tables and the proof; `code.commit` stays 6038d9c, the
  code whose kit outputs it holds); web kit_variants_golden.json with 016's writer
  (`kit_golden.golden_document` + `to_text`) on the same three sites built by the merged tree with
  `templates=[]` (kit-only, as main's: the session sites' Winkel variants would put
  `template_variants`, which embed build timestamps, and the 3070b label into the file): map rows
  change in `recipe` and gain `stickers`; per variant the layout, parts lists, cells, manifest
  entry and page digests change. 016's rule "only from an unmodified main checkout" is superseded
  for this regeneration by T054's proof procedure (docstrings of test_kit_outputs_unchanged.py and
  test_kit_golden.py say so). 017's guard golden untouched; G3 passes unchanged
- plaque parts: large plaque tile 4974 "Tile 8 x 16 with Bottom Tubes, Polished Surface" (smooth,
  Black element 6484420, in the pinned elements snapshot) replaces 90498 (textured); plate 92438
  and all sizes unchanged. Small plaque and in-margin plaque keep 10202 (matte, widely available);
  smooth 7798 noted for later (user, 2026-11-24)
- T042: sticker texts approved by the project owner, 2026-11-24, as the research R6 drafts with
  two changes: official-31203-bathymetry line without "nine" ("Ocean depth (ETOPO 2022) ranked
  into the kit's tile colors in the kit design's proportions, on white land."), and two-line
  sticker titles balanced so the second line is not a single word (user)
- implement, following the owner's T042 approval: sticker titles that wrap are balanced in
  src/stickers/text.py (`balanced_wrap`, `BALANCED_FIELDS = ("title",)`, used by
  `TextSpec.wrap`): the greedy wrap's line count, break points at spaces that make the widest
  line narrowest (then the next widest), every line within the width; sizes and shrinking (R3)
  unchanged. A plain min-max split gives "World Map, kit / 31203 design" (26.5 mm widest line
  against 30.0 mm), not the owner's example "World Map, / kit 31203 design", so a title also
  does not break between a word and the number after it ("kit 31203", "December 1997") unless no
  split with that line count fits otherwise. Small stickers: "El Niño, / December 1997", "La
  Niña, / December 1988", "World Map, / kit 31203 design", "Kit 31203 look, / from bathymetry";
  every large title stays on one line (agent)
- implement T043: the eight bundled recipes end with one line `# Map stickers (feature 017):
  sticker texts approved by the project owner, 2026-11-24` and their `[sticker]` table (keys in
  the order title, line, credit, no_data; TOML basic strings, UTF-8), directly after the af3ce57
  final newline; no other byte changed (G1). New recipe SHA-256 (first 12 hex): land-elevation
  89b792348fd2, living-planet 0a3f0cd36a92, ocean-el-nino 52265301d13b, ocean-la-nina
  62ea37adb037, ocean-sst 95111dd87f94, official-31203 d46d321e9190, official-31203-bathymetry
  8f2580b9bfef, rainfall aed69799723b (T054 needs them for 016's golden). Drafts deleted
  (draft_tables.toml and its .source.json, the draft branch of `sticker_recipe`, the T021 test,
  `TestDraftTexts`); `tests/stickers_support.py` gains `fallback_recipe(id)` (the bytes before the
  comment line), which the four fallback tests that assumed a bundled recipe without a table now
  use (test_text, test_compose, test_credits, test_legend); the contract test "a recipe file"
  copies the bundled ocean-sst (agent)
- implement T044 (real cached data, 2026-11-24; scripts and results in the session scratchpad
  017/t044/): quickstart steps 2-7, 38 of 38 checks pass (Letter and A4 sheets with both cut
  lines within 0.1 mm, SVG canvases, cut-line groups, `<desc>` disclaimer and `<metadata>`
  citations, JSON summary; A, B and C sets identical for all eight maps and two runs
  byte-identical; the step 5 legends; errors: empty cache exit 3 naming the dataset and `dataset
  fetch`, nothing written or downloaded, "Δ temperature" PDF exit 1 with "use --format svg" and
  SVG fine, a too-long line exit 1 with the field and the space; plaque parts with cited IDs,
  `partcolors plaque-parts --check` "no differences"). Step 8 against `git archive 6038d9c cli`:
  ocean-sst layout, report, parts lists (full and --kits 1), estimate (synthetic price fixture),
  section counts, sheets PDF (42 pages: metadata and content streams) and SVG, cells.json differ
  only in the recipe SHA-256 and the layout SHA-256 derived from it (and the build time);
  preview PNG, BrickLink XML, Rebrickable CSV and 41 of 42 sheet SVG pages byte-identical. Suites:
  CLI 2265 passed, 1 skipped; web 193 passed; guards G1-G4 22 passed, golden unchanged. Sample
  sheets with the approved texts: 017/samples-approved/ (Letter PDFs, 200 dpi page PNGs,
  all-stickers.png, texts.md) (agent)
- T053: owner go-ahead to commit 017's work on its branch (guard golden first, then the feature)
  and merge the local 016-map-templates branch into 017, then build Phase 5; no push (user,
  2026-11-24)
- plaque parts: owner asked to look for a smooth Black part instead of 90498 "Tile 8 x 16 with
  Bottom Tubes, Textured Surface" (user, 2026-11-24)
- implement T048: the manifest block adds `credit` (the large sticker's "Data:" lines,
  `credit_lines`) next to contracts/web.md's keys, because the page's "What the large sticker
  says" must show the data credit and the service cannot compute it; `alt` is "<Small|Large>
  sticker: <title>. <line>" (R12: title and line); `legend` rows `{label, color: LEGO name,
  part}`; `plaques` are the JSON summary's entries, large first as on the print sheet; SVG
  descriptions carry the cut size ("Small sticker (SVG, 45.8 x 45.8 mm)") (agent)
- implement T049: the catalog requires all four sticker kinds (unknown or missing kind is a
  `CatalogError`) and checks the texts and lists the page reads (title, line, alt.small/large,
  notes, legend, credit, plaques); `STICKER_TEMPLATES = ("kit-31203",)` until 016 (agent)
- implement T050: sticker `<img>`s carry no width/height (the SVGs' mm size gives both the same
  scale); the panel sits after the Lots, outside the palette section, and lists the plaque parts
  as a table like the Lots (agent)
- implement T047: the existing test_palette.py `test_downloads_and_parts_unchanged_by_chooser`
  counted every "/download/" link on the page; amended additively: it now also asserts the four
  sticker download links and subtracts them from the same count (agent)
- implement T040: the SC-007 test builds every bundled fixture map with its sticker text, times
  the full set (sticker_set, PDF Letter and A4, both SVGs, JSON) and asserts < 5 s on the
  slowest build and on every other map; the existing 30 s build test is unchanged (agent)
- implement T039: A/B/C print sheets are compared item by item: exactly one item differs, the
  provenance text, and only by "hung as <C>"; the ENSO sets in their own B equal the A set but
  for `arrangement` (agent)
- implement T033: shared helpers `sheets.render_pdf.draw_items(c, items, height_mm)` and
  `sheets.render_svg.item_svg(item, text_length=None)` (+ public `svg_number`); `textLength` and
  `lengthAdjust` go after `text-anchor`/`font-weight`, before `fill`; sheets output unchanged (G3)
  (agent)
- implement T035: `render_sticker_json(set)` is the JSON writer (`ensure_ascii=False`, indent 2,
  trailing newline as the CLI's other JSON files); SVG `<title>` "<Small|Large> sticker: <title>
  (98138.world)"; `<metadata>` = "Recipe <id> (SHA-256 <hex>). Data: <each citation as on the print
  sheet> Made with lego-image-processor <version>." (`compose.citation_text`, made public); the
  cut line keeps `data-sticker`; a non-Latin-1 PDF field is checked in the order title, line,
  `legend: <layer>`, credit, `data: <dataset>`, then any page text by tag (agent)
- implement T038: `--paper` defaults to None (letter) so a note prints only when it is given with
  svg or json ("Note: --paper applies to PDF output only; not used with --format <fmt>.", before
  the `Stickers:` line); `--format svg` with OUT a file is refused before the build; files lines:
  pdf `Stickers: OUT (Letter, 1 page, N bytes)`, svg both paths with sizes, json `Stickers: OUT
  (JSON summary, N bytes)`; citations printed from the set's credits in `echo_citations` form (same
  datasets as the report's citations for every bundled map) (agent)
- implement T030-T032: large-sticker legend: each group (Land, Ocean) starts a new column with
  its heading; its swatches spread evenly over as few columns as the height allows (row pitch
  3.4 mm and swatch 2.8 mm fixed); labels one line each; label size 6 pt down to 5 pt until the
  columns fit the width; when the legend does not fit at 5 pt the title, line, credit and
  disclaimer drop a quarter point at a time, and at their minimums the error names
  `legend: <layer>` with the width (or height) needed and available; "98138.world" stays 7 pt
  bold on the title's first baseline (the title moves down if it is smaller) (agent)
- implement T030: the "Data:" block is one paragraph per credit line, the first prefixed
  "Data: " (`TextSpec.paragraphs`, all at one size); the legend's TextBlock lists the headings
  and labels in reading order (JSON `blocks`) (agent)
- implement T032: JSON `stickers.<size>.plaque` is the size key of its `plaques[]` entry;
  `plaques[].parts[].citations` is the list of citation ids (resolved in plaque_parts.json),
  the `ResolvedColor.citation_ids` pattern; `sticker_set(result)` has no `template` argument
  until 016 (T056 adds it); `KIT_TEMPLATE_ID = "kit-31203"` equals 016's
  `templates.KIT_TEMPLATE_ID` (agent)
- implement T031/T032: print sheet: the small sticker's caption heads the parts column (x 77.8,
  y 115; R2 gives it no place of its own); plaque part line "1 <BrickLink name>, <LEGO color> -
  LEGO element <id>, design <ids>; BrickLink <item no>, Black (11); Rebrickable <part>, Black (0)"
  from `compose.part_line` (the CLI, T038, should reuse it); headings "How to make it", "Data",
  "Provenance"; every flow shrinks by 0.25 pt to 5 pt and the error names the block (`header`,
  `large sticker`, `small sticker`, `plaque parts`, `notes`, `data`, `provenance`) and the
  paper; the two cut lines are the page's last items; bleed, marks and cut lines carry
  `data-sticker` (agent)
- implement T023: text line pitch 1.3 em (the build sheets' Flow), baseline = cap height
  centred in the pitch; `fit_stack` shrinks every block of a stack together by 0.25 pt (each
  first at its own `fit_block` size, none below 5 pt) and its error names the fields joined with
  " + "; a fit error prints needed rounded up and available rounded down to 0.1 mm; numbers
  without a step keep 6 significant digits; `display_step` of a one-value range uses that value's
  magnitude (1 for 0) (agent)
- implement T025: `doi` and `acknowledgement` are None (JSON null; acknowledgement omitted) when
  the registry has none; `credits_for(recipe, template_dataset=None)` already takes the 016
  template dataset (appended once) (agent)
- implement T027: `[<layer>.legend]` units and `log10` apply to rank layers too (none bundled);
  a one-class bins layer prints its outer bounds; the group heading is "Land"/"Ocean", and
  "Ocean: the kit design's colors" only for a categorical layer on a `kit-design` dataset; group
  headings are not in the JSON `legend` (the swatch `layer` carries the group) (agent)
- implement T017: an unknown key in `[sticker.no_data]` reads `sticker.no_data.<key>: unknown key
  (allowed: land, ocean)` (`_check_keys` style; the contract's one message lists the `[sticker]`
  keys); `sticker` or `sticker.no_data` that is not a table: `<path>: must be a table` (the
  parser's existing rule); single-line = non-blank, no tab, `str.splitlines() == [s]` (so CR,
  form feed, U+2028 and a trailing newline are rejected); the label is checked before the layer's
  no_data rule (agent)
- implement T019: `variable_units` returns "" for a layer without a dataset (background) (agent)
- implement T020/T021: the draft block is `# Map stickers (feature 017): draft (research R6)` and
  `[sticker]` with keys in the order title, line, credit, no_data (inline, land before ocean);
  the T021 draft test and the draft tests in test_recipe_sticker.py `TestDraftTexts` go with the
  drafts at T043 (agent)
- implement T014: a failing plaque rule stops the build (`BuildError`, exit 5, partnumbers' code)
  instead of excluding the row, since each plaque needs both parts; rule 3 in the tool = no Black
  element of the part's LEGO design is filed under another Rebrickable part_num; rule 4 design IDs
  sorted with the part ID first, at least one; rule 7 also checks BrickLink's item name (Tile/Plate
  and dimensions) against the slot and studs; the loader's rule 6 also requires Black = BrickLink
  11 (agent)
- implement T014: `--snapshots DIR` is the partcolors snapshot directory (default
  `<cache>/sources/partcolors`), pages from its sibling `partnumbers/`, as `partcolors build` pins
  them; no `--output` flag (contract), tests patch the output path; Rebrickable's terms page is
  read and checked as in partcolors and recorded in `source.terms`, not in `source.snapshots`
  (contract example) (agent)
- implement: guard helpers use only library functions (no CliRunner); the layout path recorded
  in parts lists, estimates, counts and sheets is `<recipe>/<combination>/layout.json` and the
  price fixture is loaded by file name, so no local path reaches an output. All 292 digests the
  guard golden shares with 016's CLI-made kit golden are equal (cross-check) (agent)
- implement: G3 also pins the golden's own SHA-256 (from its .source.json), so a regenerated
  golden fails; G2 also asserts no checkout or temporary path in any output; G4 holds on 016's
  part data too (checked read-only against the 016 worktree) (agent)
- implement: owner go-ahead "Implement 017" (user, 2026-11-24)
- implement: scratch samples in the session scratchpad (017/) instead of ~/017-sticker-samples; guard golden from 6038d9c code (recipes byte-identical to af3ce57) (agent)
- analyze: 0 CRITICAL, 3 HIGH (I1 A/B/C byte identity vs recorded arrangement; I2 part-data
  guard vs 016's 3070b rows; C1 SVG citations), 15 MEDIUM/LOW; all fixed in tasks and design
  files (91 tasks, T042a added, T051 folded); plaque read as margin content under Principle I
  3.0.0 ("the content of the margin", "hold labels or a background") (agent)
- analyze: branch fast-forwarded to main 6038d9c before any implementation, so the Phase 0
  guards will capture current main (agent)
- tasks: tasks.md written, 91 tasks; owner stops T009 (BrickLink source, only if needed), T042
  (approve the eight sticker texts and the official-31203 credit), T081 (approve the corner
  offset), T091 (price refresh); US3 gated on 016 merging (T053) (agent)
- tasks: spec FR-016, FR-021 and the 100 m step aligned with the planning decisions; data-model
  gains `credit`; layout margin counts exclude plaque studs (1,960), template counts stay 1,996
  (agent)
- plan: plan.md, research.md (R1-R17), data-model.md, six contracts, quickstart.md written; no
  constitution violations (agent)
- plan: E1 `--format json`; E2 `--plaque` on the kit is an error, recipe `[margin].plaque` on a
  kit build ignored with 016's note (agent: existing patterns)
- plan: optional `sticker.credit` replaces the large sticker's data lines for `official-31203`
  (no "Official"); print sheet keeps registry citations (agent, close call)
- plan: plaque parts in their own `data/plaque_parts.json` so kit outputs and 016's 3070b rows are
  untouched; bathymetry display step 100 m (agent)
- clarify: the sticker line comes from an optional recipe sticker table (line, optional title,
  optional no-data labels), falling back to title and description; the eight bundled recipes get
  one, with lines drafted in planning for the owner's approval (an owner stop in tasks); their
  recorded recipe checksums change in every output, so feature 016's kit golden is regenerated
  for whichever feature merges second (user, 2026-11-23)
- clarify: bundled sticker titles drop "Official"; recipe titles and web pages unchanged (user,
  2026-11-23)
- specify: new feature 017 separate from 016; 016 drops its brick-built corner labels (user).
- specify: two plaques from one design, small (such as 6×6) and large (such as 8×16); a black
  tile, on a black plate when standalone; planning confirms the parts (user).
- specify: content: title, one-line description, color legend, data credit, 98138.world and the
  disclaimer on the large sticker; title, description and disclaimer on the small one (user).
- specify: optional in-margin plaque on a Winkel board, corner picked by the recipe, after 016
  ships (user).
- specify: stories US1 P1 CLI stickers for every map, US2 P2 web downloads, US3 P3 in-margin
  plaque, which depends on 016 and constitution 3.0.0 (agent: owner said "after 016 ships"; CLI
  first, constitution VI).
- clarify: one sticker set per map and template, identical for A, B and C. Only rank-derived
  legend values vary (shadow 392/390/389 studs; ocean-sst 10.97 vs 11.01 °C, bathymetry 801 vs
  799 m); legend values come from the recipe's own arrangement, rounded to a step at which A, B
  and C agree, with a test (agent: measured with map_cells on cached data).
- clarify: legend labels from the build: bins ranges with open end classes, rank boundaries as
  map_cells derives them, the recipe's second legend unit, log10 layers in data units, background
  roles, override names, "land shadow", categorical colors without values; every class listed;
  one swatch per color with all its meanings (agent: classify.py, cells.py, recipes, 013, 015).
- clarify: data credit = registry title and DOI (publisher without DOI) per dataset, including
  land_from, override and template datasets; full citation and license on the print sheet, which
  is how the small sticker meets constitution IV (agent: datasets.json; widest line 118 mm at 5 pt).
  Close call: the small sticker itself carries no credit, as the owner set.
- clarify: plaque parts tile 6×6 10202, plate 6×6 3958, tile 8×16 90498, plate 8×16 92438, Black
  only; each has one Black element in the pinned Rebrickable elements snapshot (dfc8641d…):
  6155125, 395826, 4603646, 6094066; none in kit 31203; planning adds cited IDs with 016 R10's
  method (agent: snapshot and inventory).
- clarify: makers learn plaque parts from the print sheet, the command's text and JSON output and
  the map page, with cited IDs; no price estimate or export for standalone plaques (agent:
  constitution V; feature 005).
- clarify: in-margin plaque = one Black 6×6 tile lot replacing 36 square tiles; top-up buys it;
  leftovers unchanged (kit map elements only, 014); estimate prices it or marks it unpriced (011)
  (agent).
- clarify: print sheet like the build sheets: Letter default or A4, "Print at 100% (no
  fit-to-page)", scale bar, deterministic PDF and SVG, PDF standard Helvetica (Latin-1), no images;
  both stickers on one page; about 1 mm inset from the tile and 2 mm bleed (agent: sheets/).
- clarify: minimum text 5 pt; the disclaimer is 40.5 mm wide at 5 pt and fits the small sticker
  (agent: font metrics).
- clarify: command `map stickers RECIPE -o OUT` builds from a recipe like `map cells`, never
  downloads; no `--arrangement` option (agent: rank bounds need the build; cli/map.py).
- clarify: in-margin plaque corners top-left, top-right, bottom-left, bottom-right; recipe key and
  `--plaque` option (option wins, `none` turns it off); tile inside the clear block and one 16×16
  module, at least one stud from the ring; error on the kit template or a misfit; exact offset set
  in planning and shown to the owner on a preview (agent: 016 R12, R20; sections are separate
  modules).
- clarify: layout records the plaque only when placed (agent: 016 metadata.template pattern).
- clarify: the site's Winkel variants carry no in-margin plaque; the site offers each variant's
  stickers (agent: the plaque is optional and bundled recipes name no corner). Close call.
- clarify: Winkel stickers end the line with "Winkel tripel projection" and credit ETOPO 2022
  (agent: 016 R11).

## After the 016 merge (T053, T054; 2026-11-24)

016's merged contracts (specs/016-map-templates/contracts/), data-model.md and code, compared with
what 017's tasks assumed (T055-T082 amended in tasks.md, "Amended at T053"):

- `MapResult.template` exists, but a kit build carries the kit `Template` (`is_kit` True), never
  None; the non-kit test is `result.template is not None and not result.template.is_kit` (016's
  own pattern in `map_cells` and `cli.map.template_lines`). `MapResult.margin` holds the resolved
  `MarginTreatment` (None on the kit).
- The template's projection title: 016's library has none. `Template.projection["name"]` is the
  slug `winkel-tripel`, `Template.title` is "Winkel tripel on the kit board"; "Winkel tripel" is
  only in the web package (`web98138.TEMPLATES`, manifest `templates[].projection`). So T056 adds
  `Template.projection_title` in code, not as a key of the confirmed template file.
- The template's dataset: `Template.dataset` is a `TemplateDataset` (id, version, title,
  publisher, license, citation, doi), not the `DatasetEntry` that 017's `credits_for(recipe,
  template_dataset)` takes; T056 looks up the registry entry by its id. The non-kit report's
  `citations` already list it once after the recipe's datasets.
- `counts.corners` is as assumed: `Template.counts["corners"]` = `{corner: {row, col, height,
  width}}`, 0-based board coordinates, 017's corner names; the packaged Winkel has 14 x 14 blocks
  at (0, 0), (0, 114), (66, 0), (66, 114). 017's plaque rows and columns (1-6, 73-78, 121-126) are
  0-based like 016's (`template locate --stud`: "rows 0-79") and lie inside them.
- `[margin]` and `MarginTreatment`: `_margin()` with `_MARGIN_KEYS = {"color", "ring"}` in
  maps/recipe.py; frozen `MarginTreatment(color, ring)` with `provenance(cells)`,
  `resolve_margin` and `margin_cells(tpl, treatment)` in maps/margin.py; the CLI's
  `resolve_margin_options`, `echo_template` and `KIT_MARGIN_NOTE` in cli/map.py. A recipe
  `[margin]` with only `plaque` makes `recipe.margin` non-None, so 016's kit note prints (E2 holds).
  `metadata.map.margin.cells` comes from `margin_cells` (the template mask): the plaque studs must
  be taken out there (T064/T066).
- `confirmed_winkel`: the owner confirmed the packaged `winkel-tripel.json` on 2026-11-24, so the
  fixture yields the package file as is; 016's synthetic template is the separate fixture
  `synthetic_template`; `unconfirmed_winkel` tests the refusal. The web session (autouse
  `confirmed_template_dir`) gives ocean-sst, living-planet and rainfall a Winkel variant.
- `PART_LABEL` (sheets/legend.py: plate, tile, square_tile) and the prebuild's `_part_labels()`
  (`PART_LABEL[t]` for each `parts.partslist.PART_TYPE` part a variant's lots or leftovers use,
  template variants included) are as assumed: T070's `plaque_tile` label is still required.
- `metadata.margin_positions` and `statistics.margin_tile_count` count the positions whose
  `part_type` is `square_tile` (layout/grid.py), so they become 1,960 by themselves when the
  plaque's 36 positions are absent; `metadata.template.counts` is the file's (1,996).
- `templates.KIT_TEMPLATE_ID` is "kit-31203", as assumed. 017's constant in stickers/compose.py now
  imports it (re-exported by `lego_image_processor.stickers`); the web prebuild uses it; the
  service, which never imports the library, spells it as `catalog.KIT_TEMPLATE_ID`, and
  web/tests/test_stickers.py checks the three are equal.
- Options: 016's `template_options` (src/cli/options.py) bundles `--template` (`TemplateType`,
  unknown id exit 2), `--margin-color` and `--ring-color` on `map build`, `map check` and `map
  cells`; `map stickers` needs `--template` alone (T058). 016's Template line is
  `Template: <id> (<title>) - from --template|from the recipe`, then `Margin: ...` (T057).
- Web: template variants are served at `/maps/<map>/<template-id>` by the same `map_page`
  (`MapEntry.variant`, `template_ids`); `build_variant` gains `template=`; the manifest gains
  `templates` and `maps[].template_variants`, and `total_bytes` sums both kinds of variant (017
  adds the sticker files).

## Blocked tasks
- none

## Deferred findings
- docs/runbook.md had no `map stickers` or `--plaque` step: done in converge round 1 (T092)
- the web suite has no socket guard of its own (since 008); it is offline by construction (low)

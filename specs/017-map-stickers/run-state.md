# Run state: 017-map-stickers

Source: prompt (owner, 2026-11-23: stickers instead of brick labels; four scoping answers)
Phase: implement
Status: running
Updated: 2026-11-24

Worktree: ../98138_world-017 (branch 017-map-stickers, from main af3ce57,
fast-forwarded to main 6038d9c on 2026-11-23: round studs on black for all map previews); 017 committed
on its branch (e4142bb guard golden, 3257c9d feature); the local branch 016-map-templates (f33b464)
merged into it on 2026-11-24 (T053, T054), merge commit by the coordinator; nothing pushed.
Scope of this run (owner): draft the spec; stop after clarify for review.
Owner said "plan for 017" (2026-11-23): run plan, tasks and analyze; stop before implement.

## Open questions
- none

## Decisions
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
- none

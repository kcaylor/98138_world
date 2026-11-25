---
description: "Task list for feature 017: map stickers"
---

# Tasks: Map stickers (017)

**Input**: spec.md (Clarifications incl. the "planning" session), plan.md ("Phases (for tasks.md)"),
research.md (R1–R17; E1, E2 and the `sticker.credit` override decided), data-model.md, contracts/
(recipe-sticker.md, cli.md, sticker-files.md, plaque-parts-file.md, web.md, in-margin-plaque.md),
quickstart.md, run-state.md

**Count**: 91 tasks (T001–T091 with T042a; T051 was folded into T045 and T047 after analyze, and
its ID is not reused).

**Tests**: required (constitution VII). Each implementation task follows the failing test task it
must pass; the two refactors (T019, T033) are held by the Phase 0 guards and the existing tests,
which pass before and after. All tests run offline (SC-010): the socket guard in
`cli/tests/conftest.py` stays on.

**Environment**: Poetry is not installed; the run uses uv venvs (T001). CLI commands run from
`cli/` with `.venv/bin/pytest`, `.venv/bin/lego-image-processor` and, for maintainer tools,
`PYTHONPATH=tools .venv/bin/python -m <tool>`. Web tests run from `web/` with `.venv/bin/pytest`.

**Paths**: under `cli/` unless stated; `src/` = `cli/src/lego_image_processor/`; `tools/` =
`cli/tools/`; paths starting `web/` are in the web package; `~/017-sticker-samples/` is a scratch
directory outside the repository.

**Guard rule (FR-017, SC-006)**: Phase 0 writes digests of every kit output of the eight bundled
recipes from unchanged code (016's `kit_outputs` approach), and pins the af3ce57 recipe checksums
and the map parts' blocks of the part data (research R13 G1–G4). Every later checkpoint
reruns `tests/integration/test_stickers_outputs_unchanged.py`. A changed guard digest is a bug in
the new code; the guard golden is never regenerated in this feature. (Re-based once, from an
unmodified main 6f300dc, with the owner's approval of 2026-11-25: see the note at the end.)

**Owner stops**: tasks marked **OWNER** are not done by the agent: T009 (another pinned BrickLink
source, only if T008 finds an unusable copy), T042 (approve or edit the eight sticker texts,
blocking only T042a–T044), T081 (review the in-margin plaque offset on Winkel previews, blocking
only T082), T091 (price snapshot refresh with the owner's BrickLink credentials; blocks nothing).
T053 is an agent task that needs the owner's go-ahead: bringing 016 into this worktree needs a
commit or stash of 017's uncommitted work, and the run policy allows no commit without the owner.
E1 (`--format json`), E2 (a recipe `[margin].plaque` on a kit build is ignored) and the
`sticker.credit` override are agent decisions the owner can still reverse; T042 shows them to the
owner with the texts. Deploying (`fly`) is the owner's step and is not planned here.

**Draft texts until T042**: the eight bundled recipes get their `[sticker]` tables only after the
owner approves (T043). Until then, tests that need final text (fit of every bundled sticker, A/B/C
identity, no "Official" in sticker titles, the official-31203 credit) use fixture recipes: the
bundled bytes with the research R6 draft table appended (T020). Everything else uses the fallback
(recipe title and description), which is itself a tested path.

**Merge order with 016 (research R13)**: whichever of 016 and 017 merges second regenerates 016's
kit golden files (`cli/tests/fixtures/golden/kit_outputs.json` and
`web/tests/fixtures/kit_variants_golden.json`) after G1 and G2 pass, and says so in its pull
request. In this plan 017 is second (T053–T054); if 017's US1–US2 merge first instead, 016 does it.

**Story order**: US1 (P1, CLI stickers for every map) → US2 (P2, web downloads) → US3 (P3,
in-margin plaque), which starts with the 016 gate (T053). US2's acceptance scenario 4 (template
sticker sets, FR-020) also needs 016 and runs after the gate (T059–T060).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US3 (spec.md user stories); setup, foundational and polish tasks carry none

---

## Phase 0: Setup and guards (before any production change)

**Purpose**: a working environment and proof that nothing but the recorded recipe checksum
changes (research R13).

- [x] T001 Create the venvs (Poetry is not installed): `cd cli && uv venv --python 3.11 && uv pip install -e . pytest pytest-cov pytest-benchmark pypdf` (pypdf is the existing dev dependency the PDF tests read with) and the web venv exactly as in CLAUDE.md. Note whether `node` is on PATH (palette.js tests skip without it). Record the baseline: `cd cli && .venv/bin/pytest -q` and `cd web && .venv/bin/pytest -q`; write the pass/skip counts into specs/017-map-stickers/run-state.md
- [x] T002 Guard helper tests/integration/stickers_guard.py (plain module, only library functions present at af3ce57, so it also runs against an af3ce57 export):
  - `prefix_bytes(path)`: the recipe file's bytes before the line that starts `# Map stickers (feature 017):`, or the whole file when there is none (research R5).
  - `kit_outputs(recipe_bytes, recipe_path, cache_dir, prices)`: the G2 output set for one recipe built in A from the dataset fixtures: layout JSON, report JSON (fixed `generated_at`), preview pixels, parts lists (full and `--kits 1`), BrickLink XML, Rebrickable CSV, `parts estimate` JSON on tests/fixtures/prices/bricklink_price_guide.json (fixed as-of date), section counts JSON, cells.json, sheets SVG page text; each with the recipe SHA-256 and the layout file's SHA-256 replaced by placeholders.
  - `guard_digests(cache_dir)`, every build from `prefix_bytes`, so the digests keep the af3ce57 recipe checksums (016's `kit_outputs` approach): for the eight bundled recipes in A, B and C, the layout JSON, report JSON (fixed `generated_at`), preview pixels and PNG bytes, parts lists (full and `--kits 1`), BrickLink XML, Rebrickable CSV, `parts estimate` JSON on the synthetic price fixture (fixed as-of date), section counts JSON and cells.json; and, in A for `ocean-sst` and `land-elevation`, the sheets PDF (Letter) bytes and each sheets SVG page (the outputs T033's refactor touches).
  - `map_part_blocks()`: canonical-JSON digests of the 6141 and 98138 blocks of src/data/part_colors.json and src/data/part_numbers.json and of the citation entries those blocks reference (016's method, so 016's added 3070b rows do not touch them).
- [x] T003 G1 in tests/integration/test_stickers_outputs_unchanged.py: pin the af3ce57 SHA-256 of each bundled recipe (research R13 table) and require `prefix_bytes` of src/maps/recipes/<id>.toml to hash to it; passes now
- [x] T004 G3 `test_guard_golden` in tests/integration/test_stickers_outputs_unchanged.py: rebuild `guard_digests` with the `fixture_registry` fixture and compare with cli/tests/fixtures/golden/stickers_017_guard.json, naming the recipe and output that differ; with `STICKERS_017_GUARD_WRITE=1` (and only then) it writes the file instead of comparing
- [x] T005 With no change under cli/src or web/src, write the guard golden: `cd cli && STICKERS_017_GUARD_WRITE=1 .venv/bin/pytest tests/integration/test_stickers_outputs_unchanged.py -k guard_golden`, plus cli/tests/fixtures/golden/stickers_017_guard.source.json (commit af3ce57, Python, ReportLab, Pillow and numpy versions, how it was made, disclaimer). These two files are the branch's first change: commit them first when commits are allowed. Then `test_guard_golden` passes without the variable, twice in a row
- [x] T006 G2 `test_outputs_differ_only_in_recipe_checksum` in tests/integration/test_stickers_outputs_unchanged.py, parametrised over the eight bundled recipes: `kit_outputs` from `prefix_bytes` equals `kit_outputs` from the full file (SC-006, FR-017). It passes trivially now and becomes meaningful in T021 (draft tables) and T043 (approved tables)
- [x] T007 G4 in tests/integration/test_stickers_outputs_unchanged.py: `map_part_blocks()` equals af3ce57 digests pinned in the test (the plaque parts live in their own file, research R10; whole-file checksums are not pinned, because feature 016 appends 3070b rows), and every `map_cells` palette lists only parts 6141 and 98138

**Checkpoint**: the guard file passes; `git diff --stat -- cli/src web/src` is empty.

---

## Phase 1: Foundational — plaque part data (FR-014, SC-005)

**Goal**: the four Black plaque parts with cited LEGO, BrickLink and Rebrickable IDs in
`data/plaque_parts.json`, made and checked by the `partcolors` tool (research R10;
contracts/plaque-parts-file.md). Blocks the print sheet's parts block (T031), the CLI (T036) and
US3's tile lot (T069).

**Independent test**: `PYTHONPATH=tools .venv/bin/python -m partcolors plaque-parts --check` prints
"no differences"; `load_plaque_parts().plaques["small"].tile.color.element_id == "6155125"`; G4
passes.

- [x] T008 Pin the four archived BrickLink catalog pages (network once, maintainer step, as feature 005 did for `bricklink-4073`): find the Internet Archive copies of P=10202, P=3958, P=4974 and P=92438 (research R10 dates), save them to `<cache>/sources/partnumbers/bricklink-<part>.html`, and pin id, URL (`id_` form), file, SHA-256 and access date in `PLAQUE_PAGES` in the new tools/partcolors/plaque.py (kept out of tools/partnumbers/build.py `PAGES`, which feature 016 also edits). Check that each parses with `partnumbers.build.parse_bricklink_part`, names the part as item number or alternate and lists Black (BrickLink 11), and that the cached pinned `elements.csv` (SHA-256 `dfc8641d…`) gives 6155125, 395826, 6484420 and 6094066. If a copy is unusable, stop at T009 (the large tile is the smooth 4974, chosen by the project owner on 2026-11-24 in place of the textured 90498; its page, the copy of 2026-04-17, was pinned the same day)
- [x] T009 (not needed: T008 found all four archived copies usable, 2026-11-24) **OWNER (not the agent; only if T008 finds an unusable copy)**: supply another source for the missing BrickLink page that the agent can pin by URL and SHA-256 in tools/partcolors/plaque.py `PLAQUE_PAGES`. T014–T015 wait for it; Phase 2 proceeds
- [x] T010 [P] Fixtures cli/tests/fixtures/plaque/: a synthetic `elements.csv` excerpt with the pinned file's header (the four Black rows, a non-Black row, a second Black element with a higher ID, an element whose `design_id` differs) and synthetic BrickLink pages for the four items in the structure `parse_bricklink_part` reads (as tests/unit/tools/test_partnumbers.py builds them); each with a `.source.json` (generator, date, "synthetic, not a copy of a catalog page", disclaimer). No catalog page copy is committed
- [x] T011 [P] Tests tests/unit/test_plaque_parts.py: `load_plaque_parts()` returns `plaques["small"]` (tile 10202 on plate 3958, studs [6, 6]) and `plaques["large"]` (tile 4974 on plate 92438, studs [16, 8]; the smooth tile, chosen by the project owner on 2026-11-24 in place of the textured 90498); parts carry `kit.part_numbers.PartNumbers` and `kit.part_colors.PartColor` objects; the packaged file loads; each loader rule of contracts/plaque-parts-file.md (3, 5–9) fails on a mutated copy with `ValueError("plaque_parts.json: <rule>")`; no part is in src/data/kit_31203_inventory.json
- [x] T012 Implement src/kit/plaque_parts.py (`load_plaque_parts`, `Plaque`, `PlaquePart`; data-model.md PlaquePart.part_id, PlaquePart.kind, PlaquePart.studs, PlaquePart.name, PlaquePart.numbers, PlaquePart.color and the PlaquePart validation list; Plaque.size, Plaque.tile, Plaque.plate, Plaque.studs)
- [x] T013 Tests tests/unit/tools/test_plaque_parts_tool.py on the T010 fixtures: build rules 1–9 (one failing case each), rule 2 equality with the `lego_black` row of src/data/part_colors.json, element choice (lowest ID with `design_id` = part, all kept), snapshots read from the cache directory and never the repository, `--check` exit 0 "no differences", 1 with the differences listed, 4 on a missing or changed snapshot (`SnapshotError`); `generated_on` ignored by `--check`; disclaimer last
- [x] T014 Implement tools/partcolors/plaque.py (`build`, `differences`, `to_text`, reusing the partcolors snapshot readers and join rules 1–5 and `partnumbers.build.read_pages`/`parse_bricklink_part`) and the `plaque-parts [--snapshots DIR] [--check]` command in tools/partcolors/__main__.py; the result must pass `load_plaque_parts`' rules (data-model.md PlaquePart validation)
- [x] T015 Generate src/data/plaque_parts.json with `PYTHONPATH=tools .venv/bin/python -m partcolors plaque-parts`, then `--check` → "no differences" (quickstart step 7). tests/contract/test_disclaimer.py `test_every_data_file_source_has_disclaimer` covers the new file; G4 still passes

**Checkpoint**: suite green; guards unchanged.

---

## Phase 2: Foundational — recipe sticker table, shared helpers, draft texts

**Goal**: the optional `[sticker]` table (FR-004; research R5; contracts/recipe-sticker.md), the
public rank-bound and unit helpers the legend needs (research R7), and the draft-text fixtures
that stand in for the approved texts until T043.

**Independent test**: every bundled recipe parses exactly as before with `sticker is None`; a copy
with the R6 draft table parses and its kit outputs equal the original's but for the checksum (T021).

- [x] T016 [P] Tests tests/unit/maps/test_recipe_sticker.py: `title`, `line`, `credit` and `no_data.land`/`.ocean` parse; every error of the contracts/recipe-sticker.md table with its exact message and key path (unknown key, `line` missing, empty or multi-line string, `no_data` for a layer without a `[<layer>.no_data]` rule); the table may appear anywhere in the file; text outside Latin-1 parses; `Recipe.sha256` changes with the table's bytes; the eight bundled recipes parse to the same `Recipe` as before with `sticker is None`
- [x] T017 Implement in src/maps/recipe.py: `StickerText`, `sticker` in `_TOP_KEYS`, `_sticker()` with `_check_keys`, `Recipe.sticker` (default None) (data-model.md StickerText.title, StickerText.line, StickerText.no_data and its validation; `credit` from contracts/recipe-sticker.md `sticker.credit`, which data-model.md StickerText does not list). Nothing outside src/stickers/ reads it
- [x] T018 [P] Tests tests/unit/maps/test_cells_helpers.py: public `derived_bounds(values, classes, n)` returns the unrounded rank boundaries, and the existing rounding of them equals the bounds in today's cells.json for `ocean-sst` and `official-31203-bathymetry` (fixtures); `variable_units(layer)` gives "°C" for `degC` and the registry spelling otherwise, without the `log10` prefix
- [x] T019 Implement in src/maps/cells.py: split `_derived_bounds` into `derived_bounds` and the rounding, and make `variable_units` public from `_units`/`_UNITS`; cells.json stays byte-identical (G3, T004)
- [x] T020 [P] Draft texts: cli/tests/fixtures/stickers/draft_tables.toml (+ `.source.json`) with the research R6 drafts per recipe id (title where R6 sets one, line, `no_data` for living-planet, and the official-31203 `credit`); helper cli/tests/stickers_support.py with `sticker_recipe(recipe_id)`: the bundled recipe when its file already has a `[sticker]` table, otherwise the bundled bytes followed directly (no blank line) by `# Map stickers (feature 017): draft (research R6)` and the draft table, parsed with the bundled path
- [x] T021 Extend G2 (T006) in tests/integration/test_stickers_outputs_unchanged.py to the drafts: for each bundled recipe, `kit_outputs` of `prefix_bytes` equals `kit_outputs` of the draft bytes from T020, and `prefix_bytes` of the draft bytes hashes to the pinned af3ce57 value (FR-017 and SC-006 shown before the owner's approval)

**Checkpoint**: suite green; guards unchanged.

---

## Phase 3: User Story 1 — Print the stickers for a map from the command line (Priority: P1) 🎯 MVP

**Goal**: `map stickers RECIPE -o OUT [--format pdf|svg|json] [--paper letter|a4] [--cache-dir
DIR]` and the library `stickers.sticker_set` make one sticker set for any bundled or custom recipe
on the kit template (FR-001 – FR-017, FR-026).

**Independent test**: from the dataset fixtures, make the sticker sets of `ocean-sst`,
`land-elevation`, `rainfall` and `official-31203`; check each sticker's size, text, legend and
disclaimer in the page model, render PDF and SVG, and compare the sets built in A, B and C.

### Content: text, credits, legend

- [x] T022 [P] [US1] Tests tests/unit/stickers/test_text.py (with tests/unit/stickers/__init__.py):
  - Resolution: title from the table, else the recipe title; line from the table, else the description; each with its source (`sticker table`, `recipe title`, `recipe description`); neither line nor description → `StickerError` "add a [sticker] line".
  - Numbers (research R7): hyphen-minus, comma thousands separator, no trailing zeros, a space before the unit, "°C" for `degC`; display step 10^(floor(log10(max − min)) − 1), half away from zero (`ROUND_HALF_UP`): ocean-sst 1 °C, bathymetry 100 m (research R8).
  - Fitting (research R3, FR-013): start at the preferred size, wrap at spaces within the block's line limit, then shrink in 0.25 pt steps to 5 pt; never truncate (no "..."); a word wider than the block at 5 pt or a stack that does not fit raises `StickerError` naming the sticker, the field and the space needed and available in mm; widths from `sheets.compose.text_width`.
- [x] T023 [US1] Create src/stickers/__init__.py (`StickerError`, a `ValueError`; exports grow with later tasks) and implement src/stickers/text.py (data-model.md StickerText resolved title and line with their sources; TextBlock.field, TextBlock.lines, TextBlock.size_pt, TextBlock.preferred_pt, TextBlock.min_pt, TextBlock.bold, TextBlock.align, TextBlock.box and the TextBlock fit rule)
- [x] T024 [P] [US1] Tests tests/unit/stickers/test_credits.py: one credit per dataset of `Recipe.datasets()` in order, including a `land_from` mask dataset (living-planet) and override datasets (rainfall: GPCP v2.3 and the NSIDC record), each once; text "<registry title>, doi:<doi>" or "<registry title>, <publisher>"; a `sticker.credit` replaces only the large sticker's "Data:" lines while the full credit list (citation, license, acknowledgement) is kept for the print sheet (research R9)
- [x] T025 [US1] Implement src/stickers/credits.py (data-model.md Credit.dataset, Credit.version, Credit.text, Credit.title, Credit.doi, Credit.publisher, Credit.citation, Credit.license, Credit.acknowledgement)
- [x] T026 [P] [US1] Tests tests/unit/stickers/test_legend.py on fixture builds (`fixture_registry`), per research R7 and spec Clarifications:
  - Bins: open end classes, outer bounds never printed (land-elevation "below 150 m" … "3,000 m and above", 10 land swatches); `log10` back in data units (living-planet); the `[legend]` second unit only (rainfall "below 182.5 mm/yr").
  - Rank: labels from `derived_bounds` at the display step, outer bounds included; equal rounded bounds print one value (ocean-sst "-2 °C; land shadow").
  - Categorical (official-31203): the nine LEGO color names without values, group heading "Ocean: the kit design's colors".
  - Background roles "land", "offshore", "coast ring"; override names; no-data label from the table or "no data"; the shadow "land shadow".
  - Order: land group then ocean group; per layer its colors, then no-data, overrides, then (ocean) the shadow; a color met again adds its meaning to the earlier swatch ("Antarctica; Greenland"); every scale class listed even with no studs; no-data, override and shadow entries only when they cover a stud.
  - Swatch `rgb` is the part color's cited sRGB from src/data/part_colors.json; legends of `ocean-sst` and `official-31203-bathymetry` built in A, B and C are identical (FR-006).
- [x] T027 [US1] Implement src/stickers/legend.py from a `MapResult` only (no data reading or classification; data-model.md Swatch.layer, Swatch.part_id, Swatch.color, Swatch.rgb, Swatch.lego_name, Swatch.meanings and the Swatch order; Meaning.kind, Meaning.label, Meaning.range, Meaning.units, Meaning.source, Meaning.step and the Meaning rules)

### Layout: geometry, stickers, print sheet (page model, no rendering)

- [x] T028 [P] [US1] Tests tests/unit/stickers/test_geometry.py: tile = studs × 8.0 − 0.2, cut = tile − 2 × 1.0, bleed 2.0, marks (gap 1.0, length 4.0, width 0.25, 8 per sticker), safe area 2.5, canvas = cut + 14; small 47.8 / 45.8 / 59.8 mm, large 127.8 × 63.8 / 125.8 × 61.8 / 139.8 × 75.8 mm; plaque studs read from src/data/plaque_parts.json (FR-009)
- [x] T029 [US1] Implement src/stickers/geometry.py with the LDraw and LUGNET citations in its docstring (research R1; data-model.md StickerGeometry.tile_mm, StickerGeometry.cut_mm, StickerGeometry.bleed_mm, the StickerGeometry marks, StickerGeometry.safe_mm, StickerGeometry.canvas_mm)
- [x] T030 [P] [US1] Tests tests/unit/stickers/test_compose.py (page model, built from fixture maps; contracts/sticker-files.md "Sticker content"):
  - Small sticker: title, line and disclaimer only (FR-003). Large: title, "98138.world", line, legend, "Data:" credit, disclaimer (FR-002).
  - Background and bleed in the cited sRGB of `lego_black` from src/data/plaque_parts.json; text White; swatches Ø 2.8 mm in cited sRGB with a 0.15 mm outline RGB 210, 210, 210 (the Black shadow shows, FR-008); plate swatches with the inner ring; item tags and `data-layer`/`data-color`/`data-part`.
  - Every text item inside the safe area; cut lines within 0.1 mm of their sizes (SC-001); preferred sizes of research R3; a legend that does not fit (a custom recipe with long override names) and a title or line too long at 5 pt raise `StickerError` naming the layer or field and the space needed and available.
  - `sticker_set(result)` twice gives equal sets and `to_dict()` (no timestamps).
- [x] T031 [P] [US1] Tests tests/unit/stickers/test_print_sheet.py: `print_sheet(set, "letter"|"a4")` places the blocks of research R2 and contracts/sticker-files.md "Print sheet" (large cut line at (19.0, 41.0), small at (19.0, 118.8), bleed, 8 cut marks each, captions with tile sizes, header "Two stickers for Black tiles: print on white sticker paper at 100%, cut along the marks."); the plaque parts block per plaque (1 tile and 1 plate with LEGO element and design, BrickLink item and color, Rebrickable part and color) and "The sticker is printed, not a LEGO part."; how-to and "Printed colors only approximate the LEGO colors."; each dataset's id, version, title, citation and license (FR-007); recipe id and SHA-256, "legend values from the build hung as <C>" (the sheet's only text that depends on the arrangement), tool version; the sheets' `furniture()` (100 mm scale bar, "Print at 100% (no fit-to-page)", footer, "Page 1 of 1", disclaimer); everything but the sticker content outside the cut lines (FR-010); a citation block too long for its area raises `StickerError` naming the block and paper
- [x] T032 [US1] Implement src/stickers/compose.py (`sticker_set`, `StickerSet`, `Sticker`, `print_sheet`, `StickerSet.to_dict`) and export them from src/stickers/__init__.py; the template is `{id: "kit-31203"}` from a constant until 016 merges (data-model.md Sticker.size, Sticker.plaque, Sticker.geometry, Sticker.blocks, Sticker.legend, Sticker.items; StickerSet.recipe, StickerSet.template, StickerSet.arrangement, StickerSet.text, StickerSet.small, StickerSet.large, StickerSet.legend, StickerSet.credits, StickerSet.plaques, StickerSet.notes, StickerSet.tool_version, StickerSet.disclaimer and its determinism rule; PrintSheet.paper, PrintSheet page)

### Renderers

- [x] T033 [US1] Refactor, output unchanged (research R4): move the per-item drawing out of src/sheets/render_pdf.py `render_pdf()` into a shared function, and the per-item serialiser out of src/sheets/render_svg.py `page_svg()` into a shared function with an optional `text_length` that sheets never pass. Held by G3 (T004) and tests/unit/sheets/test_render_pdf.py and test_render_svg.py, which pass before and after
- [x] T034 [P] [US1] Tests tests/unit/stickers/test_render.py (contracts/sticker-files.md):
  - PDF: one page, Letter 215.9 × 279.4 or A4 210 × 297; metadata title "Map stickers: <title>", author "98138.world", subject with the disclaimer, creator with the tool version; Helvetica and Helvetica-Bold, not embedded; no image XObject (SC-004); each cut line an unpainted `re n` path within 0.1 mm of its size (SC-001); same input, same bytes (FR-012); a field outside Latin-1 stops with the field and "use --format svg" (FR-013).
  - SVG: `sticker-small.svg` and `sticker-large.svg`; `width`/`height` in mm and `viewBox` equal to the canvas; white paper, bleed, marks, content, then `<g id="cut-line">` with one `<rect>` of the cut size, `fill="none"`, `stroke="#ff00ff"`, `stroke-width="0.10"`; `<title>` and `<desc>` with the disclaimer (FR-011); a `<metadata>` element outside the drawing holding each dataset's id, version, title, full citation and license (and acknowledgement), the recipe id and SHA-256 and the tool version, so the SVG set carries the citations as the print sheet does (constitution IV; spec Clarifications), and nothing that depends on the arrangement; every `<text>` carries `textLength` equal to its Helvetica width and `lengthAdjust="spacingAndGlyphs"`; no `<image>`; Unicode text allowed; same input, same text.
  - JSON: `to_dict()` field order and content of the "JSON summary" table (format "1", template `{id: "kit-31203"}`, plaques with cited IDs, notes, disclaimer), written with `ensure_ascii=False`, indent 2.
- [x] T035 [US1] Implement src/stickers/render.py (`render_sticker_pdf` with ReportLab `invariant=1`, `pageCompression=1`; `render_sticker_svgs` with the `<metadata>` citations block; the JSON writer), using the T033 helpers; export from src/stickers/__init__.py (data-model.md "Sticker files": PDF and SVG)

### Command line

- [x] T036 [P] [US1] Contract tests tests/contract/test_map_stickers_contract.py (contracts/cli.md "map stickers"):
  - Options and defaults; `--format pdf` writes the file OUT, `svg` creates the directory OUT and replaces only its two names (OUT a file → exit 1), `json` writes the summary; `--paper a4`; `--paper` with svg or json prints a note.
  - Output text in the contract's order: recipe, legend source, title and line with sources, both stickers' sizes and text sizes, each plaque's tile and plate with cited LEGO, BrickLink and Rebrickable IDs in Black, the expected values read from `load_plaque_parts()` and never assumed equal to the part number, and "the sticker is printed, not a LEGO part" (FR-015, US1-10), files written, the color note, citations, the disclaimer last.
  - Every row of the error table with its exit code: unknown recipe 1; dataset not cached 3 naming the dataset and `dataset fetch ID`, with no download (socket guard) and nothing written (US1-9); checksum mismatch 4; "add a [sticker] line" 1; text that does not fit 1; a print-sheet block that does not fit 1; non-Latin-1 PDF 1 with "use --format svg"; cannot write 1; the disclaimer last on every error.
  - FR-017: after a run the directory holds only OUT; no layout, parts list, sheet, cells file or report is written.
- [x] T037 [P] [US1] Extend tests/contract/test_disclaimer.py (FR-026): `map stickers` text output and errors, the JSON summary's `disclaimer`, both SVGs' `<desc>`, the PDF subject and both stickers' disclaimer text
- [x] T038 [US1] Implement `map stickers` in src/cli/map.py: build like `map cells` (`build_map(..., compare_official=False)` in the recipe's own arrangement, cache only), compose in memory, write only on success, print the contract's output (research R11; E1 `--format json`)

### Every bundled map

- [x] T039 [P] [US1] Integration tests tests/integration/test_stickers_bundled.py, for the eight bundled maps from the fixtures through `sticker_recipe` (T020):
  - Fit at 5 pt or more on Letter and A4 (SC-002); cut lines within 0.1 mm in the page model, SVG and PDF (SC-001); no image and the disclaimer in each file (SC-004); no "Official" in any sticker title (FR-004).
  - Sets built in A, B and C are identical (SC-003, FR-006): `to_dict()` without its `arrangement` field, and both SVG files byte for byte. The print sheet names the build's arrangement ("legend values from the build hung as <C>"), so its PDF bytes are compared only within one arrangement, and the A, B and C sheets' page models differ only in that line. Making a set twice in the same arrangement gives identical PDF, SVG and JSON bytes (FR-012).
  - Acceptance content: ocean-sst title "Ocean temperature", nine ocean swatches with °C ranges, White land, the shadow on the Earth Blue swatch, ERSST v5 title and DOI (US1-2, US1-3); land-elevation (US1-5); rainfall mm/yr classes, "Antarctica; Greenland", "sea ice", Black "land shadow" with its outline, GPCP v2.3 and NSIDC credits (US1-6); official-31203 nine colors by name and the `credit` line (US1-7); living-planet "ice" and "sea ice".
- [x] T040 [P] [US1] Performance test in tests/integration/test_map_performance.py: composing and rendering a full sticker set (PDF Letter and A4, both SVGs, JSON) adds less than 5 s to the build of the slowest fixture map (SC-007)

### Owner stop: the eight sticker texts

- [x] T041 [US1] Sample print sheets from real data, outside the repository: check `lego-image-processor dataset list` shows the pinned datasets cached (fetch a missing one with `dataset fetch ID`, network, outside the tests); write each bundled recipe with its R6 draft table appended to ~/017-sticker-samples/recipes/<id>.toml; run `map stickers <file> -o ~/017-sticker-samples/<id>.pdf` and `--format svg -o ~/017-sticker-samples/<id>-svg`. Write ~/017-sticker-samples/texts.md listing per map the sticker title, line, no-data labels, the official-31203 credit, the legend labels, the credits and the smallest text size chosen. Record the path in specs/017-map-stickers/run-state.md
- [x] T042 (approved by the project owner, 2026-11-24 (run-state.md)) [US1] **OWNER STOP (not the agent)**: the agent sends the owner the T041 samples and text list, plus E1, E2 and the `sticker.credit` decision for awareness, and asks for approval or edits per recipe (Latin-1, one line, no "Official" in titles). The approval is recorded in specs/017-map-stickers/run-state.md as role "project owner" and the date, with the approved texts. Blocks only T042a–T044; Phase 4 proceeds on the fallback texts
- [x] T042a [US1] Tests in tests/unit/maps/test_recipe_sticker.py, written before T043 and failing until it lands: every bundled recipe file has a `[sticker]` table after one `# Map stickers (feature 017):` comment line at its end; its `title` and `description` keys equal af3ce57's; no sticker title contains "Official"; official-31203 sets `credit`; the texts equal the approved ones recorded in run-state.md (T042)
- [x] T043 [US1] Append the approved tables to the eight files in src/maps/recipes/: directly after each file's final newline (no blank line), one comment line `# Map stickers (feature 017): ...` and the `[sticker]` table; no other byte changes; recipe `title` and `description` unchanged (contracts/recipe-sticker.md "Bundled recipes"; data-model.md "State: sticker texts"). Then delete cli/tests/fixtures/stickers/draft_tables.toml and the draft branch of `sticker_recipe`; T042a, G1, G2, G3 and T039 pass. If an edited text fails to fit, report the field and sizes to the owner (back to T042)
- [x] T044 [US1] Real-data checks (quickstart steps 2–8): print sheets of ocean-sst on Letter and A4, SVG and JSON; A, B and C sets of every bundled map identical (`to_dict()` without `arrangement`, SVG bytes) and two runs in one arrangement byte-identical (step 4); the step 6 errors; plaque parts in the output; step 8 against af3ce57 in a scratch directory (`git archive af3ce57 cli` extracted outside the repository): layouts, parts lists, exports, sheets and cells.json of ocean-sst differ only in the recipe SHA-256 and its derived checksums. Record results in run-state.md

**Checkpoint (MVP)**: `map stickers <recipe> -o stickers.pdf` works for all eight maps with the
approved texts; guards unchanged; CLI suite green.

---

## Phase 4: User Story 2 — Download the stickers from the web site (Priority: P2)

**Goal**: the prebuild writes each map's sticker set once with the library; map pages show both
stickers, the plaque parts and four downloads, without JavaScript (FR-018, FR-019, FR-026;
research R12; contracts/web.md).

**Independent test**: an offline prebuild with the fixtures lists `maps[].stickers.kit-31203` per
map with sizes and checksums; each map page shows and links them; every variant file is unchanged
by the sticker step.

- [x] T045 [P] [US2] Tests web/tests/test_stickers.py (prebuild and manifest), on the session site and the living-planet and rainfall sites:
  - `maps[].stickers["kit-31203"]` once per map, never per combination: four files (`stickers-letter`, `stickers-a4`, `sticker-small`, `sticker-large`) under maps/<map>/stickers/kit-31203/ with path, bytes, SHA-256, media type, description and filename `98138-world_<map>_<kind>.<ext>` that match the files on disk; `title`, `line`, `alt`, `legend`, `plaques`, `notes` as contracts/web.md (US2-1).
  - The files equal `render_sticker_pdf`/`render_sticker_svgs` of `sticker_set` for the recipe's default combination (A, or B for ocean-el-nino).
  - `total_bytes` counts them; each map's four files total at most 150 kB, so 13 sets stay under 2 MB (SC-008).
  - A second small prebuild with the sticker step patched out gives identical variant entries and identical variant files (FR-018 "additions only"; `total_bytes` is the one top-level value that changes).
  - Amend web/tests/test_prebuild.py where it enumerates manifest keys, additively; no existing assertion is dropped (folded from T051).
- [x] T046 [P] [US2] Tests web/tests/test_catalog.py: `stickers` is optional (an older manifest still serves); keys must be `kit-31203` (later, a listed template id); kinds must be the four sticker kinds; each file inside the root, present and of the recorded size, else `CatalogError`
- [x] T047 [P] [US2] Tests web/tests/test_stickers_page.py (routes and page):
  - `GET /maps/<map>/stickers/kit-31203/sticker-small.svg` and `sticker-large.svg`: 200 `image/svg+xml`, inline, cacheable, ETag; `GET …/download/<kind>`: attachment with the manifest filename; unknown map, template, file or kind: 404; CSP unchanged.
  - Map page "Stickers for a plaque" panel identical for A, B and C: both `<img>` in `<figure>`s with the manifest alt texts and captions, the `<details>` "What the large sticker says", the standalone plaque parts with IDs, "Printed colors only approximate the LEGO colors.", "The sticker is printed, not a LEGO part.", four downloads with sizes (US2-2).
  - With scripts removed the panel, images and downloads still work (US2-3); the footer disclaimer; the about page's sticker paragraph; the sticker images sit outside the palette chooser, which never recolors them.
  - Amend web/tests/test_routes.py where it enumerates page content or downloads, additively; no existing assertion is dropped (folded from T051).
- [x] T048 [US2] Implement in web/src/web98138/prebuild.py: make `build_variant` hand back the variant's `MapResult` (research R12 assumes it; the af3ce57 code does not), make one sticker set per map from the recipe's default combination (one extra `build_map` only if that combination is not built), write the four files and the manifest block, count them in `total_bytes` (data-model.md "Manifest additions": maps[].stickers.<template-id>, total_bytes)
- [x] T049 [US2] Implement the optional `stickers` block and the sticker kinds in web/src/web98138/catalog.py
- [x] T050 [US2] Implement the routes in web/src/web98138/app.py (registered before the combination routes), the Stickers panel in web/src/web98138/templates/map.html, the paragraph in web/src/web98138/templates/about.html and the sticker figures in web/src/web98138/static/style.css; no script, no new dependency, the service still never imports `lego_image_processor`

T051 was folded into T045 and T047 (analyze, 2026-11-23); its ID is not reused.

- [x] T052 [US2] Real-data local check (quickstart step 9; no `fly` command): `python -m web98138.prebuild --out <scratch>/site --no-prices` and the same at af3ce57 (or with the sticker step patched out); serve with uvicorn; check /maps/ocean-sst/A, /B and /C with and without JavaScript; record the output growth (under 2 MB, SC-008) and the wall time in run-state.md

**Checkpoint**: web suite green; CLI guards unchanged.

---

## Phase 5: User Story 3 — A plaque in a Winkel margin corner (Priority: P3), and the 016-dependent part of US2

**Goal**: after feature 016 merges: stickers on templates (FR-001, FR-025), template sticker sets
on the site (FR-020, US2-4), and the optional in-margin plaque (FR-021 – FR-024; research R14,
R15; contracts/in-margin-plaque.md).

**Independent test**: with 016's confirmed fixture template, build `ocean-sst` with the plaque in
the bottom-left corner: it covers 36 margin studs inside the corner's clear block, no land or
ocean stud changes, the parts list has one Black 6×6 tile and 36 fewer square tiles, and the
sheets and preview show it.

### Gate

- [x] T053 [US3] **GATE: rebase or merge 016 (owner go-ahead needed).** Feature 016 is merged into `main`; bring it into this branch (rebase onto the new `main` or merge it). This needs a commit or stash of 017's uncommitted work, so it waits for the owner's go-ahead (run policy "commit: no"). After the merge, G4 (T007) stays valid unchanged: it digests only the 6141 and 98138 blocks and their citations, which 016 leaves byte-identical while appending 3070b rows; G1–G3 must also pass unchanged. Keep 016's code in files both features touch (cli/tests/conftest.py, tools/partcolors/__main__.py, src/maps/cells.py `part_palette`, src/sheets/render_*.py, web/src/web98138/prebuild.py, docs/vision.md). Re-read the merged specs/016-map-templates/contracts/ and data-model.md, and record in specs/017-map-stickers/run-state.md every difference from 017's assumptions (`MapResult.template`, the template's projection title, `counts.corners`, `[margin]` and `MarginTreatment`, `confirmed_winkel`, `PART_LABEL`, `_part_labels()`, `metadata.margin_positions`); amend T055–T082 before starting them. Replace 017's `kit-31203` constant with 016's `templates.KIT_TEMPLATE_ID`. Constitution is now 3.0.0. No task below starts before this one
- [x] T054 [US3] Regenerate 016's kit golden (017 merges second; research R13). Run it right after T053, before any US3 code (T061–T079) is in place, and rerun it whenever later work touches a kit output. Before rewriting anything, prove that only recipe checksums differ:
  - With G1 and G2 green, run 016's harness on the eight recipes' `prefix_bytes` copies (a temporary recipes directory holding the af3ce57 bytes, so every recorded recipe checksum is af3ce57's): its digests must equal the committed cli/tests/fixtures/golden/kit_outputs.json exactly. Any difference is a bug, not a reason to regenerate.
  - For the web golden, diff the normalised kit pages and manifest entries with the recipe checksums (and the checksums derived from them) replaced by placeholders: the only remaining differences are the Stickers panel on kit map pages, the about paragraph and the manifest's `stickers` blocks and `total_bytes`. palette.js is not changed by this feature (T076–T077), so it is not in the allowed diff.
  - Only then regenerate cli/tests/fixtures/golden/kit_outputs.json with `PYTHONPATH=tools .venv/bin/python -m maptemplates kit-golden --fixtures --out tests/fixtures/golden/kit_outputs.json` (update its `.source.json`) and web/tests/fixtures/kit_variants_golden.json with 016's writer in web/tests/kit_golden.py. 017's own guard golden is not regenerated and passes unchanged. Record it in run-state.md for the pull request; rerun this task if T043 lands later

### Stickers on a template (FR-001, FR-025; US3-4)

- [x] T055 [P] [US3] Tests tests/unit/stickers/test_template_stickers.py on 016's `confirmed_winkel` fixture with the dataset fixtures, for the five maps `templates.compatibility` allows: both stickers' line ends with " Winkel tripel projection."; the large credit adds ETOPO 2022 once (also for official-31203-bathymetry, which already reads it); the print sheet adds 016's template provenance line; JSON `template` is `{id, title, projection, dataset}`; every set fits at 5 pt or more on Letter and A4 (SC-002); kit sets are unchanged (T039 still passes) *Amended at T053 (016 merged):* `confirmed_winkel` yields the packaged `winkel-tripel` as is (the owner confirmed it on 2026-11-24); 016's synthetic template is the separate fixture `synthetic_template`. Kit builds carry the kit `Template` in `MapResult.template` (never None): test the non-kit case with `result.template.is_kit`. The provenance line is `sheets.compose.template_line(template.layout_record())`. Replace the interim T053 test class `TestTemplateBuildBeforeT056` in tests/unit/stickers/test_compose.py (a non-kit build raises `StickerError`)
- [x] T056 [US3] Implement in src/stickers/text.py, src/stickers/credits.py and src/stickers/compose.py, reading `MapResult.template`; add `Template.projection_title` in src/templates/__init__.py only if 016 has no accessor for it (research R14; data-model.md StickerSet.template, StickerText resolved line, Credit order with the template's dataset) *Amended at T053:* 016 has no accessor for the short projection name: `Template.projection["name"]` is the slug `winkel-tripel`, `Template.title` is "Winkel tripel on the kit board", and "Winkel tripel" exists only in the web package (`web98138.TEMPLATES`, the manifest's `templates[].projection`), which the library must not import; so add `Template.projection_title` in code (keyed by the projection name), not as a new key of the confirmed template file (its SHA-256 is recorded in every Winkel output). `Template.dataset` is a `TemplateDataset` (id, version, title, publisher, license, citation, doi), not a `DatasetEntry`: look up the registry entry by `template.dataset.id` for `credits_for(recipe, template_dataset)`; the report's `citations` already add it once after the recipe's datasets. Remove the interim guard at the top of `sticker_set` (StickerError for a non-kit template, added at T053)
- [x] T057 [P] [US3] Contract tests in tests/contract/test_map_stickers_contract.py: `map stickers ocean-sst --template winkel-tripel` and a recipe `template` key; the `Template:` line after the `Recipe:` line (016's wording); an unknown `--template` exits 2 listing the confirmed templates; kit output unchanged *Amended at T053:* 016's wording is `cli.map.template_lines(result)`: `Template: winkel-tripel (Winkel tripel on the kit board) - from --template` (or `- from the recipe`), then a `Margin: … square tiles (part 3070b): …` line; `map build` prints them after its `Arrangement:` line. An unknown `--template` is `TemplateType`'s usage error (exit 2, "confirmed templates: …"); an unknown recipe `template` exits 1 with key path `template`
- [x] T058 [US3] Implement `--template` on `map stickers` in src/cli/map.py with 016's option in src/cli/options.py *Amended at T053:* 016's options are `TemplateType` and `TEMPLATE_HELP` in src/cli/options.py; its `template_options` decorator also adds `--margin-color` and `--ring-color`, which do not change stickers, so `map stickers` takes `--template` alone (`click.option("--template", "template_id", type=TemplateType(), …)`) and passes it to `build_map(..., template=...)`; arrangement A only on a non-kit template (016 refuses others)

### Template sticker sets on the site (FR-020; US2-4)

- [x] T059 [P] [US2] Tests in web/tests/test_stickers.py and web/tests/test_stickers_page.py on 016's session site with the Winkel variant of ocean-sst: `maps[].stickers["winkel-tripel"]` with four files under maps/ocean-sst/stickers/winkel-tripel/ and filenames `98138-world_ocean-sst_winkel-tripel_<kind>.<ext>`; the Winkel page shows the Winkel set and kit pages the kit set; the catalog accepts only listed template ids; the Winkel variant's layout has no `metadata.plaque` and its files are unchanged by the sticker step (FR-020) *Amended at T053:* 016's session sites have Winkel variants of ocean-sst (small site), living-planet and rainfall (`confirmed_template_dir`, autouse). Since T053 a template page already looks up its own template's set (`app.map_page` passes `sticker_template=<template-id>`), so it shows no panel; replace the interim web test `test_template_page_shows_no_kit_set` (tests/test_stickers_page.py). The kit sticker filenames carry no template id (`98138-world_<map>_<stem>.<ext>`)
- [x] T060 [US2] Implement in web/src/web98138/prebuild.py, web/src/web98138/catalog.py, web/src/web98138/app.py and web/src/web98138/templates/map.html (data-model.md "Manifest additions": one entry per template variant) *Amended at T053:* `build_variant` returns `_result` for template variants too (the template loop pops it); build each template set from that `MapResult` into `maps/<map>/stickers/<template-id>/`. `catalog.STICKER_TEMPLATES` is `(KIT_TEMPLATE_ID,)` (the service spells `kit-31203`, checked against `templates.KIT_TEMPLATE_ID` by test_stickers.py); make `check_stickers` accept the kit id and the manifest's `templates[].id`. The web kit golden (T054) now also compares each map row's `stickers` digest: a `stickers["winkel-tripel"]` entry changes it on maps with a template variant, so extend kit_golden.py's template allowance (compare `stickers` without the template ids, as 016 allows the nav item and the 3070b label) instead of rewriting the golden

### In-margin plaque: choice and placement (FR-021, FR-022)

- [x] T061 [P] [US3] Tests tests/unit/maps/test_recipe_plaque.py: `[margin].plaque` accepts the four corners, an unknown one is `margin.plaque: must be one of top-left, top-right, bottom-left, bottom-right`; `--plaque` on `map build`, `map check` and `map cells` (Click choice, unknown corner exit 2); the option wins, `none` turns a recipe's plaque off, `source` is `option` or `recipe`; E2: `--plaque CORNER` on the kit exits 1 "the kit template has no margin" naming the templates with one, while a recipe `[margin].plaque` on a kit build prints 016's margin note, builds and places nothing; no bundled recipe names a corner *Amended at T053:* `map build`, `map check` and `map cells` all take 016's `@template_options` (src/cli/options.py); 016's note is `cli.map.KIT_MARGIN_NOTE`, printed by `echo_template(result, margin)` when the recipe or an option sets a margin on a kit build (a recipe `[margin]` with only `plaque` makes `recipe.margin` non-None, so the note prints)
- [x] T062 [US3] Implement in src/maps/recipe.py (016's `[margin]` parser), src/cli/options.py (the `--plaque` option) and src/cli/map.py (attach it to `map build`, `map check` and `map cells`, resolve option over recipe, the kit error and exit codes) (data-model.md InMarginPlaque.corner, InMarginPlaque.source) *Amended at T053:* 016's parser is `_margin()` with `_MARGIN_KEYS = {"color", "ring"}` in src/maps/recipe.py; `MarginTreatment(color, ring)` (frozen) with `provenance(cells)`, `resolve_margin(recipe.margin, margin_color, ring_color)` and `margin_cells(tpl, treatment)` are in src/maps/margin.py; the CLI resolves them in `cli.map.resolve_margin_options`
- [x] T063 [P] [US3] Tests tests/unit/maps/test_plaque.py on `confirmed_winkel` and 016's synthetic fixture template, taking each clear block from the loaded template's `counts.corners`, not hard-coded: *Amended at T053:* "016's synthetic fixture template" is the CLI fixture `synthetic_template`. `Template.counts["corners"]` is `{corner: {row, col, height, width}}` in 0-based board coordinates with 017's corner names; the packaged Winkel has 14 x 14 blocks at (0, 0), (0, 114), (66, 0) and (66, 114). The contract's rows and columns (1-6, 73-78, 121-126) are 0-based, as 016's (`template locate --stud`, "rows 0-79")
  - The placement table of contracts/in-margin-plaque.md for each corner (one stud in from both board edges; modules A1, H1, A5, H5).
  - The checks in order: not the kit; all 36 studs margin studs inside the corner's clear block; one 16×16 module; no ring stud within Chebyshev distance 1. A misfit (a temporary template copy with a smaller corner block) stops with "needs 6 x 6 studs plus one stud from the outline ring" and the block's size.
  - The plaque never covers ring studs; with `--margin-color lego_white` it stays Black; it works with `--ring-color`.
- [x] T064 [US3] Implement plaque placement in src/maps/margin.py as part of 016's margin treatment (data-model.md InMarginPlaque.corner, InMarginPlaque.part_id, InMarginPlaque.color, InMarginPlaque.studs, InMarginPlaque.cells and the InMarginPlaque placement rule) *Amended at T053:* `metadata.map.margin.cells` and the report's `margin.cells` come from `margin_cells(tpl, treatment)` (the template's margin mask), so the plaque's 36 studs must be taken out there

### In-margin plaque: layout, report, validation, preview (FR-023, FR-024)

- [x] T065 [P] [US3] Tests:
  - tests/unit/test_grid.py: `metadata.plaque` `{part_id: "10202", color: "lego_black", corner, studs, cells: 36}` only when placed; the 36 positions absent (10,204 positions); `statistics.margin_tile_count` counts the square tiles left and `statistics.plaque_tile_count` is 1; `metadata.margin_positions` and `metadata.map.margin.cells.margin` count the margin positions present (1,960 with a plaque on the exact-fit Winkel template; taken from the loaded template's counts minus 36, not hard-coded) while `metadata.template.counts` keeps the template's own (contracts/in-margin-plaque.md "Counts"); layouts without a plaque read and write as before.
  - tests/unit/test_validator.py and tests/contract/test_validate_contract.py: `validate` accepts a layout whose absent positions are exactly the plaque's studs and template margin studs; anything else is a mask error.
  - tests/integration/test_map_plaque.py: `ocean-sst --template winkel-tripel --plaque bottom-left`: land, ocean and the other margin positions equal the build without the plaque (US3-1, SC-009); the report's `margin.plaque` is `{corner, source, studs, part_id}`; a recipe naming a corner built with `--plaque none` has no plaque (US3-6).
- [x] T066 [US3] Implement in src/layout/grid.py, src/layout/validator.py and src/maps/build.py (data-model.md InMarginPlaque layout `metadata.plaque` and absent positions) *Amended at T053:* `metadata.margin_positions` and `statistics.margin_tile_count` are counted from the positions with `part_type` `square_tile` (src/layout/grid.py), so they drop to 1,960 by themselves when the plaque studs are absent; `metadata.template.counts` is `Template.layout_record()` (the file's counts)
- [x] T067 [P] [US3] Tests tests/unit/maps/test_preview.py: the plaque is one filled rectangle in the tile's cited Black over its 6 × 6 studs (pixel probes on a stud, between studs and just outside); previews without a plaque unchanged
- [x] T068 [US3] Implement in src/maps/preview.py `write_preview`; a layout may lack exactly the recorded plaque studs, and no other position

### In-margin plaque: parts, exports, prices (FR-024; US3-2)

- [x] T069 [P] [US3] Tests tests/unit/parts/test_partslist.py, tests/unit/parts/test_export.py and tests/integration/test_parts_plaque.py:
  - One lot: part 10202, type `plaque_tile`, label "tile 6x6", needed 1, `kit_supply` 0 so `--kits 1` buys it; lot order 6141, 98138, 3070b, 10202. Every ID is asserted against `load_plaque_parts()`, never hard-coded from the part number: LEGO element and design IDs, the BrickLink item from `bricklink.item_no` (a BrickLink item can differ from the part ID: 6141 is item 4073, and 016's 3070b is item 3070) and Black (11), the Rebrickable part and Black (0).
  - The parts list's `citations` include every citation id of the 10202 lot (its BrickLink page, e.g. `bricklink-10202`, and `rebrickable-elements`), resolved from plaque_parts.json `source.snapshots`; none is dropped.
  - The 3070b lots hold 36 fewer tiles; the 6141 and 98138 lots equal the build without the plaque; 10,204 one-stud pieces and one tile (SC-009); `leftovers` unchanged.
  - BrickLink XML: one item with `<ITEMID>` = the plaque tile's `bricklink.item_no`, color 11, `<MINQTY>1</MINQTY>`; Rebrickable CSV: the tile's Rebrickable part, color 0, quantity 1.
  - src/sheets/legend.py `PART_LABEL` has `plaque_tile`; the web prebuild's `part_labels` for a site without a plaque is unchanged.
- [x] T070 [US3] Implement in src/parts/partslist.py (`PART_ORDER`, `PART_TYPE`, and `_citations()`, which today looks citation ids up only in the part_numbers pages and part_colors citations and would silently drop the plaque's: also resolve them from plaque_parts.json `source.snapshots`), src/parts/export.py, src/parts/resolve.py (the tile's `ResolvedColor` from plaque_parts.json) and src/kit/inventory.py (supply 0), and in the same task `PART_LABEL["plaque_tile"] = "tile 6x6"` in src/sheets/legend.py, so the prebuild's `_part_labels()` never meets a part type without a label (016 research R16; data-model.md InMarginPlaque parts-list lot)
- [x] T071 [P] [US3] Extend tools/fixtures011/make_price_fixture.py to write tests/fixtures/prices/bricklink_price_guide_plaque.json (+ `.source.json`): 016's 3070b fixture (tests/fixtures/prices/bricklink_price_guide_3070b.json, kit and square-tile lots) plus a 10202 Black row, so a Winkel estimate with the plaque can be complete; the existing price fixtures stay byte-identical
- [x] T072 [P] [US3] Tests tests/unit/prices/test_lots.py, tests/unit/prices/test_snapshot.py, tests/unit/prices/test_estimate.py and tests/integration/test_prices_estimate.py: `parse_lot("10202:26")`; part order 6141, 98138, 3070b, 10202; `recipe_lots()` adds `10202:26` only for a recipe naming a corner, so the bundled lot set and the committed snapshot's lots are unchanged; a plaque layout's estimate with the existing fixture is `complete: false` with the lot `unpriced` and a reason, and complete with the T071 fixture; other estimates unaffected; `all_cited_lots()` (`--all-colors`) does not raise and is unchanged: it loops only over the parts `PartColorTable` holds (today it loops over `PART_ORDER` and `PartColorTable.for_part` would raise `KeyError` for 10202); `parse_lot("10202:26")` checks the color against plaque_parts.json; a `named` snapshot holding every `recipe_lots()` lot plus `10202:26` is complete for `parts estimate` and for the web prebuild's `load_prices`, for builds with and without a plaque (needed by T091)
- [x] T073 [US3] Implement in src/prices/lots.py (`PART_ORDER`, `parse_lot`, `recipe_lots`, `all_cited_lots` limited to the part_colors parts), src/prices/snapshot.py and, if needed, src/prices/estimate.py (data-model.md InMarginPlaque price lot `10202:26`)

### In-margin plaque: sheets, counts, cells, CLI (FR-024; US3-3, US3-5)

- [x] T074 [P] [US3] Tests tests/unit/sheets/test_compose.py, tests/unit/sheets/test_legend.py, tests/unit/sheets/test_counts.py and tests/integration/test_sheets_plaque.py: the section page (A5 for bottom-left) draws one Black `Rect` outlined 0.4 mm over the 6 × 6 studs, labelled "tile 6x6 (10202)" with its lot number, and no 1×1 studs there; the section's count table lists the lot with 1; a legend row with a square swatch "tile 6x6"; the overview draws the rectangle; the totals line adds "1 tile 6x6 (plaque, part 10202)"; `sheets counts` JSON lists the lot in its section; sheets without a plaque unchanged; a layout missing a position that is not a recorded plaque stud is still refused
- [x] T075 [US3] Implement in src/sheets/compose.py, src/sheets/legend.py and src/sheets/counts.py. `build_sheet_set` today refuses any layout with fewer than 10,240 positions (`len(grid.positions) != FULL_POSITIONS`); relax it so exactly the studs recorded in `metadata.plaque` may be absent, and nothing else (a layout missing any other position still fails with today's message)
- [x] T076 [P] [US3] Tests tests/integration/test_map_cells.py and tests/contract/test_map_cells_contract.py: `map cells … --plaque bottom-left` writes `P` for plaque studs and a `plaque` block `{part_id, color, rgb, corner, cells}`, and its default rendering equals the layout; cells.json without a plaque unchanged. palette.js is not changed: no site variant has a plaque (spec, FR-020), so the chooser never receives `P` cells; a future site variant with a plaque would need it
- [x] T077 [US3] Implement in src/maps/cells.py, and pass the resolved plaque from `map cells` in src/cli/map.py (the option itself is T062) (data-model.md InMarginPlaque cells.json)
- [x] T078 [P] [US3] Contract tests tests/contract/test_map_plaque_contract.py: `map build`/`map check --plaque` print, after 016's `Margin:` line, `Plaque: tile 6x6 (part 10202), Black, bottom-left, rows 73-78, columns 1-6 - from --plaque` (or `from the recipe`), and the `Layout:` line counts 10,204 pieces and 1 plaque tile; every row of the contracts/cli.md `--plaque` error table with its exit code (US3-5); `parts list`, `parts export`, `parts estimate`, `sheets build`, `sheets counts` and `validate` accept a plaque layout and name the tile; disclaimer last; output without a plaque unchanged
- [x] T079 [US3] Implement the wording in src/cli/map.py, src/cli/parts.py, src/cli/prices.py, src/cli/sheets.py and src/cli/validate.py

### Owner stop: the corner offset

- [x] T080 [US3] Previews for the owner, outside the repository, on the confirmed Winkel template with real data: `map build ocean-sst --template winkel-tripel --plaque <corner> -o ~/017-sticker-samples/plaque-<corner>.json --preview ~/017-sticker-samples/plaque-<corner>.png` for the four corners, the corner section pages (A1, H1, A5, H5) from `sheets build`, and the Winkel sticker print sheet from `map stickers ocean-sst --template winkel-tripel` *Amended at T053:* write the samples under the session scratchpad `017/` (implement brief), not `~/017-sticker-samples/`
- [x] T081 [US3] **OWNER STOP (not the agent)** (confirmed as built by the project owner, 2026-11-25; run-state.md): the agent sends the T080 previews with the offsets of contracts/in-margin-plaque.md (one stud in from both board edges) and asks the owner to confirm them or give other rows and columns. Recorded in run-state.md as role "project owner" and the date. Blocks only T082
- [x] T082 [US3] Apply the answer: if the offset changes, update the placement in src/maps/margin.py and its tests (T063, T078) and record the decision; then real-data checks of quickstart steps 10–12 (Winkel stickers, the plaque in a corner through parts, estimate, sheets, `validate` and `map cells`, the plaque errors). Record results in run-state.md

**Checkpoint**: CLI and web suites green, including 016's regenerated kit golden and 017's guards.

---

## Phase 6: Docs and final checks

- [x] T083 [P] cli/README.md: `map stickers` (formats, papers, printing on white sticker paper at 100%, cutting, the 1 mm inset), the `[sticker]` table, the plaque parts, `PYTHONPATH=tools python -m partcolors plaque-parts --check`, and after 016 `--template` on `map stickers`, `--plaque` and `[margin].plaque`; add the `[sticker]` note to specs/004-map-recipes/contracts/recipe-format.md, as features 012 and 013 did (research R17)
- [x] T084 [P] README.md (stickers for every map) and web/README.md (sticker files, the manifest `stickers` block, the routes)
- [x] T085 [P] docs/vision.md: a 017 row "built" (two plaques from one design, stickers from the built map, print sheet and SVG, web downloads, in-margin plaque on Winkel); if 016's merge brought a 017 row, update it rather than add one
- [x] T086 CLAUDE.md and AGENTS.md: the same feature 017 paragraph in both (`stickers/` and `map stickers`, the `[sticker]` table with `credit`, `data/plaque_parts.json` and `partcolors plaque-parts --check`, the web `maps[].stickers` block and routes, `--plaque` and `metadata.plaque` after 016, the guard golden); add `stickers/` to the Layout list and `kit/plaque_parts.py` where the kit package is described; remove nothing else
- [x] T087 FR-026 audit, extending tests/contract/test_disclaimer.py where needed: the disclaimer on both stickers, the print sheet, the SVG `<desc>`, the PDF subject, the JSON summary, `map stickers` and `partcolors plaque-parts` output, src/data/plaque_parts.json, the Stickers panel and footer; no new text implies endorsement and no sticker title says "Official"
- [x] T088 Walk quickstart.md steps 1–12 (10–12 after Phase 5) and fix any mismatch between the docs and the behaviour
- [x] T089 Full test runs with the socket guard on (SC-010): `cd cli && .venv/bin/pytest` and `cd web && .venv/bin/pytest`; record the counts against T001 in run-state.md
- [x] T090 Update specs/017-map-stickers/run-state.md: phase, decisions taken during implementation, owner tasks still open (T091; T042 or T081 if pending), who regenerated 016's kit golden (T054, or "016 does it" if 017's US1–US2 merged first), and that deploying is the owner's step

---

## Phase 7: Owner steps (not the agent; do not block the agent's completion)

- [ ] T091 **OWNER (not the agent)**: with the four `BRICKLINK_*` environment variables set (never written or logged), from `cli/`, fetch a snapshot that holds every default lot and the plaque tile. `--lot` makes a `named` snapshot of only the listed lots, so `--lot 10202:26` alone would replace the kit snapshot with one lot; list them all instead: `.venv/bin/lego-image-processor parts prices fetch -o src/lego_image_processor/data/bricklink_price_guide.json $(.venv/bin/python -c "from lego_image_processor.prices.lots import recipe_lots; print(' '.join('--lot ' + l.spec for l in recipe_lots()))") --lot 10202:26`. Review and commit it; plaque estimates then become complete, and the snapshot's `lot_set.kind` is `named` instead of `recipes`. Best done together with 016's own refresh (its T109). Needs T073 and its `named`-snapshot test

---

## Dependencies and execution order

- **Phase 0 first**: no production change before T004 and T005 pass. Then Phase 1 → 2 → 3 (US1)
  → 4 (US2) → 5 (after 016) → 6.
- **Phase 1** (plaque data) blocks T028 (plaque studs), T030–T032 (Black background, parts
  block), T036 (CLI parts lines) and T069–T070. T009 (owner, only if needed) blocks T014–T015
  only; Phase 2 runs meanwhile.
- **Phase 2** blocks US1: T017 before T022–T023 and T039; T019 before T026–T027; T020–T021
  before T039 and T041.
- **Within US1**: T023 → T025 → T027 → T029 → T032 (each consumes the previous module);
  T033 before T035; T035 before T038; T038 before T039–T041. T042 (owner) blocks only
  T042a–T044; T042a is written before T043 and fails until it lands.
- **US2** needs T032 and T035 (library), not T042: before approval it shows the fallback texts.
- **Phase 5** starts with T053 (016 merged; needs the owner's go-ahead for the commit or stash)
  and T054, which runs before any US3 code (T061–T079) and again whenever later work touches a
  kit output; T055–T058 and T059–T060 need T053; the plaque tasks T061–T079 need T054 and T015;
  T071 needs 016's 3070b price fixture; T080 needs T079; T081 (owner) blocks only T082.
- **Merge order**: if 017's US1–US2 are to merge before 016, Phase 5 becomes follow-up work and
  016 regenerates its kit golden; otherwise T054 does it here.
- **T091** (owner) needs T073 and blocks nothing.

Test → implementation pairs: T003–T007 guard every later task; T011→T012; T013→T014→T015;
T016→T017; T018→T019; T022→T023; T024→T025; T026→T027; T028→T029; T030, T031→T032;
T034→T035; T036, T037→T038; T042a→T043; T045→T048; T046→T049; T047→T050; T055→T056; T057→T058;
T059→T060; T061→T062; T063→T064; T065→T066; T067→T068; T069→T070; T071, T072→T073;
T074→T075; T076→T077; T078→T079. T033 and T019 are refactors held by the guards.

## Parallel opportunities

- Phase 0: T002 first; then T003–T007 in order (one test file).
- Phase 1: T010 and T011 together; T013 after T010.
- Phase 2: T016, T018, T020 together.
- US1: T022, T024, T026, T028 together (four test files); T030 and T031 together; T034, T036,
  T037 together after T032; T039 and T040 together after T038.
- US2: T045, T046, T047 together; T048, T049, T050 touch different files and can run together
  after their tests.
- Phase 5: after T054, T055, T057, T059, T061, T063 together; later T065, T067, T069, T071,
  T072, T074, T076, T078 together, each implementation after its test.
- Phase 6: T083, T084, T085 together.

Example (US1, after Phase 2):

```text
T022 tests/unit/stickers/test_text.py     T024 tests/unit/stickers/test_credits.py
T026 tests/unit/stickers/test_legend.py   T028 tests/unit/stickers/test_geometry.py
```

Example (US2): `T045 web/tests/test_stickers.py`, `T046 web/tests/test_catalog.py`,
`T047 web/tests/test_stickers_page.py`, then T048–T050.

## Implementation strategy

1. **Guards first** (Phase 0): every later change is measured against unchanged outputs.
2. **MVP = US1** (T001–T044): `map stickers` makes print sheets, SVGs and JSON for all eight maps
   with the approved texts. Before the owner's T042, T001–T040 already give a working command
   (fallback texts in the bundled recipes, drafts in tests).
3. **US2** (T045–T052): the site offers every map's stickers.
4. **After 016** (T053–T082): template stickers, template sets on the site, the in-margin plaque.
5. **Finish**: Phase 6; the owner runs T091 and deploys.

## Coverage

| Requirement | Tasks |
|---|---|
| FR-001 a set for any recipe that builds; any confirmed template | T032, T038, T039, T055, T056 |
| FR-002 large sticker content | T030, T032, T039 |
| FR-003 small sticker content only | T030, T032, T039 |
| FR-004 sticker table (incl. `credit`), fallback, bundled tables, no "Official" | T016, T017, T020, T022, T023, T039, T041, T042, T042a, T043 |
| FR-005 legend from the built map; merged meanings | T018, T019, T026, T027 |
| FR-006 one set per map, identical for A, B, C | T026, T039, T044 |
| FR-007 credits; full citation and license on the sheet (and in the SVG `<metadata>`) | T024, T025, T031, T034, T035 |
| FR-008 cited sRGB swatches with outline; no logo or image | T030, T032, T034 |
| FR-009 sticker sizes | T028, T029 |
| FR-010 print sheet content | T031, T032 |
| FR-011 SVG per sticker, cut line element | T034, T035 |
| FR-012 same input, same bytes | T030, T034, T039, T044 |
| FR-013 fonts, wrap then shrink, 5 pt minimum | T022, T023, T034, T036 |
| FR-014 plaque parts with cited IDs, `--check` | T008–T015 |
| FR-015 plaque parts on sheet, CLI text and JSON, map page | T031, T034, T036, T038, T045, T047 |
| FR-016 library and `map stickers` command | T032, T035, T036, T038, T057, T058 |
| FR-017 no other output changes | T002–T006, T021, T036, T043, T044 |
| FR-018 prebuild writes sets once per map, manifest additions (`total_bytes` counts them) | T045, T048, T049 |
| FR-019 map page, no JS, service serves files only | T047, T050 |
| FR-020 template variants get their own sets, no plaque | T059, T060 |
| FR-021 `--plaque` and recipe key; kit error | T061, T062, T078, T079 |
| FR-022 placement inside the clear block and one module | T063, T064, T080–T082 |
| FR-023 layout records the plaque only when placed | T065, T066 |
| FR-024 preview, sheets, parts (with citations), top-up, leftovers, prices, cells, validate | T065–T079, T091 |
| FR-025 template projection in the line, template dataset credited | T055–T058 |
| FR-026 disclaimer, no endorsement | T030, T034, T036, T037, T047, T087 |
| SC-001 cut lines within 0.1 mm | T028, T030, T034, T039 |
| SC-002 every bundled map fits at 5 pt or more | T030, T031, T039, T043, T055 |
| SC-003 A/B/C identical (`to_dict()` without `arrangement`, SVG bytes); twice identical bytes | T026, T039, T044 |
| SC-004 disclaimer, no image | T034, T037, T039, T087 |
| SC-005 cited IDs in Black | T011, T013, T015, T036 |
| SC-006 other outputs differ only in recipe checksum | T002–T007, T021, T043, T044, T054 |
| SC-007 < 5 s more than the build | T040 |
| SC-008 every page offers stickers; site + < 2 MB | T045, T047, T052 |
| SC-009 10,204 one-stud pieces and one 6×6 tile | T065, T069, T082 |
| SC-010 offline tests | T001, T089 (socket guard in every run) |

## Notes for implementation (after analyze, 2026-11-23)

Resolved in the artifacts: `credit` in FR-004, Key Entities and data-model.md StickerText; the
100 m bathymetry step in the spec; synthetic plaque test pages in research R10 and
contracts/plaque-parts-file.md; plaque layout margin counts of 1,960 (contracts/in-margin-plaque.md
"Counts"; T065); `total_bytes` in FR-018; the A/B/C rule (SC-003: `to_dict()` without
`arrangement` and SVG bytes); SVG `<metadata>` citations; the price refresh with every default lot
(T091). Still open:

1. FR-016's signature still shows `--format pdf|svg` (E1 adds `json`), and FR-021 still says any
   plaque on the kit stops the build (E2 ignores a recipe `[margin].plaque` on kit builds). Those
   spec lines were outside this edit; tasks follow the contracts.
2. plan.md still says "fixtures and committed HTML excerpts" (Constitution Check VII), "small
   BrickLink page excerpts" (Project Structure, fixtures/plaque/), "The spec's '10 m are enough'"
   (note 4, now stale: the spec says 100 m), and lists palette.js for the `P` cells (Technical
   Context and the files after 016), which T076–T077 no longer change. Only plan.md's Principle I
   row was editable.
3. Research R12 says `build_variant` hands back the `MapResult` as `_result`; the af3ce57 code
   does not. T048 adds it.
4. The spec's edge case "`map cells` on a layout with an in-margin plaque" reads a layout, but
   `map cells` takes a recipe; contracts/cli.md resolves it with `map cells … --plaque`.
5. docs/vision.md on this branch has no 014, 016 or 017 row, while 016's T101 says "the 017 row
   stays as it is"; T085 adds or updates the row after the merge.

Not affiliated with or endorsed by The LEGO Group.

---

## Phase 8: Convergence

- [x] T092 Add a map stickers and in-margin plaque step to docs/runbook.md ("try everything locally"; it has no `map stickers`, `[sticker]` or `--plaque`): `map stickers` as PDF (Letter, A4), SVG and JSON, what to look for on the sheet and in the output (plaque parts, "printed, not a LEGO part", the same for A, B and C), Winkel stickers with `--template winkel-tripel`, `--plaque bottom-left` through `parts list` and `sheets build`, the "Stickers for a plaque" panel in the local web section, and a print-and-cut check under "Checks that need you"; every command run on cached data, per plan: phase 10 docs (T083-T086) (partial)

---

## Note: merge of main 6f300dc (feature 010), 2026-11-25

Main gained feature 010 (Pacific-centred combinations D and E, an assembly page in every sheet
set, ENSO recipes hung D by default) after these tasks were written. Their text is kept as it was;
on the merged tree it reads as follows (run-state.md, "Merge of main 6f300dc"):

- Wherever a task says "A, B and C" for stickers (T002, T004, T039, T044, T054, T059, the guard
  rule, SC-003), it now means A, B, C, D and E: the sticker sets, the guard digests
  (`stickers_guard.COMBINATIONS`) and the site's kit pages cover all five. The ENSO maps' own
  combination is D (was B).
- Guard: G1 (T003) pins main 6f300dc's recipe SHA-256 instead of af3ce57's (010 changed the two
  ENSO recipes); the guard golden (T005) was re-written once, with the owner's approval, from an
  unmodified export of 6f300dc with only the guard helper and test copied in, never from 017 code.
- T054's proof and regeneration of the kit goldens was repeated against main 6f300dc.

Not affiliated with or endorsed by The LEGO Group.

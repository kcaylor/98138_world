---
description: "Task list for feature 016: map templates (Winkel tripel on the kit board)"
---

# Tasks: Map Templates (016)

**Input**: spec.md, plan.md ("Phases (for tasks.md)"), research.md (R1–R22), data-model.md,
contracts/ (template-file.md, cli.md, recipe-and-outputs.md, web.md), quickstart.md, run-state.md

**Count**: 105 tasks (T001–T109 with T020a and T020b; T094–T099, the corner-label tasks, were
removed on 2026-11-23 when labels moved to feature 017, map stickers; their IDs are not reused).

**Tests**: required (constitution VII). Each implementation task follows the failing test task it
must pass. All tests run offline (SC-007): the socket guard in `cli/tests/conftest.py` stays on, and
the one pyproj end-to-end tool test is skipped without pyproj or the cached ETOPO file.

**Paths**: under `cli/` unless stated; `src/` = `cli/src/lego_image_processor/`; `tools/` =
`cli/tools/`; paths starting `web/` are in the web package.

**Kit golden rule (SC-001)**: Phase 0 writes digests of every kit output from unchanged code.
Every later checkpoint re-runs `tests/integration/test_kit_outputs_unchanged.py` and
`web/tests/test_kit_golden.py`. A changed kit digest is a bug in the new code; the golden files are
never regenerated in this feature.

**Owner stops**: tasks marked **OWNER** cannot be done by the agent: T011 (another pinned 3070b
source, only if needed), T039 (review and confirm the Winkel template), T109 (price snapshot
refresh with the owner's BrickLink credentials). Deploying (`fly`) is the owner's step and is not
planned here.

**Confirmed temporary copy**: until the owner confirms (T039 → T081), tests that build on Winkel
use the `confirmed_winkel` fixture (T030). It is a copy of the committed template with a test
confirmation, or the committed synthetic fixture template (T025) before the package file exists.
Both the CLI and web suites build it with the shared helper tools/maptemplates/testing.py. The
test confirmation does not change the template's layout digest (data-model.md
TemplateLayoutDigest), so the committed ice file stays valid for the copy. With it, Phases 4–7
can proceed before the owner answers.

**Story order**: US1 (build on Winkel, P1) and US2 (generate, check, confirm a template, P1)
interleave in the plan's order. US1 needs the template model from US2, and US2's confirmation waits
on the owner. Then US3 (web, P2). US4 (corner labels) was removed on 2026-11-23: labels moved to
feature 017, map stickers.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US3 (spec.md user stories); setup and polish tasks carry none

---

## Phase 0: Kit golden digests (before any production change)

**Purpose**: prove SC-001 from the first change on (research R9).

- [x] T001 Record the baseline: `cd cli && poetry run pytest -q` and `cd web && .venv/bin/pytest -q` (uv fallback per CLAUDE.md); write pass/skip counts into specs/016-map-templates/run-state.md
- [x] T002 (parked: commit-time step, done with the owner's approval at the first commit) Finish the constitution workflow, with the owner's approval, as part of the branch's first commit: delete only the "Sync Impact Report" HTML comment at the top of .specify/memory/constitution.md. No other change to the file. The `speckit-derive-constitution` workflow produced the comment for the owner-approved amendment 3.0.0 and marked it "remove before committing". The committed 2.0.0 constitution (8108f47) has no such comment. This is the workflow's last step, not a hand edit of the rules. The comment's README follow-up is T100
- [x] T003 Move `FixtureRegistry` (and its fixture-file table) from cli/tests/conftest.py to tools/fixtures004/registry.py, and import it from cli/tests/conftest.py, so the golden harness and the tests place the same dataset fixtures (research R9); the suite passes as at T001
- [x] T004 [P] Tests tests/unit/tools/test_kit_golden.py: digests are deterministic; layout and report digests use a fixed `generated_at`; PNG entries record decoded-pixel and byte digests; sheets are digested as SVG text (Letter, every variant) and PDF bytes (Letter, A only). `parts estimate` JSON and text on the synthetic fixture snapshot tests/fixtures/prices/bricklink_price_guide.json are digested with a fixed `--as-of`. The `map build` and `map check` text output is digested with the temporary directory replaced by a placeholder. The 6141 and 98138 blocks and citations of src/data/part_colors.json and part_numbers.json are digested as canonical JSON; entries sorted by recipe and combination; the harness uses only library functions present at commit af3ce57, so it can run against a `main` checkout
- [x] T005 Implement tools/maptemplates/__init__.py, tools/maptemplates/__main__.py (Click group, disclaimer printed last) and tools/maptemplates/golden.py: `kit-golden --out FILE [--cache-dir DIR | --fixtures]` builds the 8 bundled recipes × A, B, C on the kit and digests layout JSON, report JSON, preview pixels and PNG bytes, parts lists (full and `--kits 1`), BrickLink XML, Rebrickable CSV, `parts estimate` (fixture snapshot, fixed `--as-of`), section counts JSON, cells.json, the `map build` and `map check` text output, and sheets (research R9; contracts/template-file.md maintainer table)
- [x] T006 With no change under src/ or web/src/, run `PYTHONPATH=tools poetry run python -m maptemplates kit-golden --fixtures --out tests/fixtures/golden/kit_outputs.json`; write tests/fixtures/golden/kit_outputs.source.json (commit af3ce57, library and Python versions, generator, disclaimer). These two files are the branch's first change: commit them first when commits are allowed, after T002
- [x] T007 Integration test tests/integration/test_kit_outputs_unchanged.py: rebuild through the same harness and compare every digest with tests/fixtures/golden/kit_outputs.json, naming the recipe, combination and output that differ (SC-001); passes now
- [x] T008 [P] Real-data digests outside the repository: `PYTHONPATH=tools poetry run python -m maptemplates kit-golden --cache-dir <cache> --out ~/kit-before.json` with the cached pinned datasets (quickstart step 1); record the path and dataset ids in run-state.md (compared in T104)
- [x] T009 [P] Web golden: helper `site_digests(site_dir)` in web/tests/kit_golden.py. It covers kit variants' timestamp-free files byte for byte (previews, thumbs, exports, cells.json). Layout, `parts.json`, `parts-1kit.json` and the manifest variant entries are compared after normalisation: `generated_at` and every checksum derived from the layout are removed. That means `layout_sha256` inside the parts lists, and the `sha256` and `bytes` of each manifest file entry whose file embeds the layout checksum or a timestamp (layout, parts lists, sheets PDFs). The golden also holds the top-level manifest `part_labels`, and the rendered HTML of each kit map page (`/maps/<map>/<C>`) with content-versioned asset tokens normalised (research R9). Write web/tests/fixtures/kit_variants_golden.json from the session's small site (official-31203, ocean-sst, ocean-el-nino) with unchanged code; test web/tests/test_kit_golden.py compares (SC-001, SC-006); passes now, and twice in a row (not flaky)

**Checkpoint**: both golden tests pass; `git diff --stat -- cli/src web/src` is empty.

---

## Phase 1: Part 3070b reference data (US1 prerequisite)

**Goal**: cited colors and IDs of the 1×1 square tile 3070b, with the 6141 and 98138 data unchanged
(FR-009, FR-014; research R10).

**Independent test**: `partnumbers build --check` and `partcolors build --check` print "no
differences"; `kit part-colors --part 3070b` lists Black; kit golden unchanged.

- [x] T010 [US1] Find Internet Archive copies of the BrickLink catalog page for item 3070b and the Rebrickable part page for 3070b (network once, maintainer, as in feature 005); place them in the maintainer cache and pin URL, SHA-256 and access date in the page lists of tools/partnumbers/build.py and tools/partcolors/build.py. If either page has no archived copy, stop at T011
- [x] T011 (not needed: T010 found pinnable Internet Archive copies of both pages) [US1] **OWNER (not the agent; only if T010 finds no archived copy)**: supply another source for the missing 3070b page that the agent can pin by URL and SHA-256. T015–T019 wait for it; Phases 2 and 3 can proceed
- [x] T012 [P] [US1] Tests tests/unit/tools/test_partnumbers.py: 3070b from the pinned pages with the non-kit rules (BrickLink item equals the project ID or lists it as an alternate; LEGO design IDs are those Rebrickable lists); 6141 and 98138 keep the two kit-inventory rules; `--check` exit codes unchanged
- [x] T013 [P] [US1] Tests tests/unit/tools/test_partcolors.py: 3070b through the five join rules (pinned Rebrickable elements and colors snapshots, LDraw `LDConfig.ldr`, the BrickLink color guide, and rule 5 on the pinned 3070b catalog page); every 3070b row `in_kit: false`; the "kit colors missing" rule applies to kit parts only
- [x] T014 [P] [US1] Tests tests/unit/test_part_colors.py, tests/unit/test_part_numbers.py and tests/integration/test_map_cells.py: loaders accept exactly 6141, 98138 and 3070b; 3070b rows are `in_kit: false` and include `lego_black`; the 6141 and 98138 blocks and citations equal the digests in tests/fixtures/golden/kit_outputs.json; `colors_for_part("3070b")` and `PartColorTable.for_part("3070b")` work; `part_palette()` with no template still returns only 6141 and 98138
- [x] T015 [US1] Implement 3070b in tools/partnumbers/build.py and tools/partcolors/build.py (research R10)
- [x] T016 [US1] Implement in src/kit/part_colors.py and src/kit/part_numbers.py (`PARTS` + 3070b, role `margin`, the rules for a part not in the kit; data-model.md Part 3070b.in_kit). Restrict src/maps/cells.py `part_palette()` to the template's parts, defaulting to 6141 and 98138, so 3070b never reaches kit cells.json (research R9). Must land with T017 or the kit golden breaks
- [x] T017 [US1] Regenerate src/data/part_numbers.json and src/data/part_colors.json (new rows, snapshots and citations appended; existing blocks byte-identical); `PYTHONPATH=tools poetry run python -m partnumbers build --check` and `… -m partcolors build --check` → "no differences" (quickstart step 2)
- [x] T018 [P] [US1] Contract test tests/contract/test_kit_contract.py: `kit part-colors --part 3070b` (table and JSON) lists the cited square-tile colors including Black; `kit part-numbers` lists 3070b; the unfiltered listings gain the 3070b rows (additive)
- [x] T019 [US1] Implement `--part 3070b` in src/cli/kit.py (choice and help text "3070b tile 1x1 square")

**Checkpoint**: suite green; kit golden unchanged.

---

## Phase 2: Template model (US2 core)

**Goal**: the `templates` package: file format, loader rules, forward Winkel tripel, the kit
template in code, stud ↔ location lookups and the `template` command group (FR-001, FR-002,
FR-004, FR-005, FR-018; research R1, R3, R21).

**Independent test**: a synthetic Winkel template loads, round-trips stud ↔ location, and is
rejected for each broken rule; the kit template reproduces today's mask and projection.

- [x] T020 [US2] Create src/templates/__init__.py (module docstring only), src/data/templates/ and tests/unit/templates/__init__.py
- [x] T020a [P] [US2] Tests tests/unit/templates/test_digest.py: `layout_sha256(doc)` is the SHA-256 of the canonical JSON defined in contracts/template-file.md "Layout digest". It is unchanged by adding or changing `confirmation`, `corrections` records, `title`, `description`, `source`, `check_points`, `counts` or `disclaimer`. It changes when any class, any location, the fit, the board or the parts change
- [x] T020b [US2] Implement src/templates/digest.py (`layout_sha256`; data-model.md TemplateLayoutDigest.layout_sha256)
- [x] T021 [P] [US2] Tests tests/unit/templates/test_board.py (the four helper tests moved from tests/unit/tools/test_projection_study.py, plus corner free regions): `rim_cells` (4-neighbour ring), `module_stats` (full/partial/empty; rejects partial modules), `largest_rectangle`, corner free regions per board quadrant (margin minus ring)
- [x] T022 [US2] Implement src/templates/board.py (moved from tools/projection_study/raster.py); raster.py imports the helpers from the package; the remaining study tests still pass
- [x] T023 [P] [US2] Tests tests/unit/templates/test_winkel.py: forward Winkel tripel with φ1 50.4598° and λ0 11.1° E. Check the exact extent x = ±(π/2)(1 + cos φ1), y = ±π/2; the centre and the antimeridian edges; left–right and top–bottom symmetry; and pyproj reference values hard-coded in the test (pyproj/PROJ versions noted) to 1e-9. A 200,000-point comparison is skipped without pyproj (research R1)
- [x] T024 [US2] Implement src/templates/winkel.py (numpy, vectorised, in chunks of 10⁶ points)
- [x] T025 [US2] Shared helper tools/maptemplates/testing.py (numpy only; importable by the CLI tests through `pythonpath = ["tools"]` and by the web tests, see T084):
  - `write_synthetic_template(dir)` writes a confirmed synthetic `winkel-tripel` template and its ice file. The template is 128 × 80, the size the loader requires. Outline and check points come from src/templates/winkel.py; land from a deterministic rule; locations from the forward formula; it has a test confirmation. The ice file holds land ice on L studs south of 60° S and sea ice on O studs poleward of 75°, recording `template_layout_sha256` from src/templates/digest.py.
  - `confirmed_copy(src_dir, dst_dir, date)` copies a template and its ice file with a test confirmation.
  - `use_template_dir(dir)` (context manager) points `templates.TEMPLATE_DIR` at a directory.

  Run it once and commit the small synthetic fixture: cli/tests/fixtures/templates/winkel-tripel.json and winkel-tripel-ice.json, each with a `.source.json` (how it was made, generator, date, disclaimer), like the dataset fixtures (spec US1 Independent Test: small committed fixture template). A test in tests/unit/templates/test_fixture_template.py regenerates the fixture and compares it byte for byte
- [x] T026 [P] [US2] Tests tests/unit/templates/test_template_file.py: each rule of contracts/template-file.md fails with a `TemplateError` (a `ValueError`) that names the file and the rule. The loader derives `layout_sha256` (T020b) and the template's `dataset` from the registry entry named by `source.dataset.id`, whose version, SHA-256, citation and license must match. Rules: id pattern equal to the file stem and not `kit-31203`; `projection.name`; check points |Δ| < 1e-9; board of whole modules, 128 × 80; parts exactly 6141/98138/3070b; classes 80 strings of 128 `L`/`O`/`M`; locations non-null exactly on L and O, lon in −180..180; recorded counts equal the derived ones (land, ocean, margin, ring, modules, corners); correction and confirmation shapes; disclaimer present. An unconfirmed template loads but is not in `confirmed_templates()`
- [x] T027 [P] [US2] Tests tests/unit/templates/test_kit_template.py: `kit-31203` built in code from the existing kit files: 3,062 L / 7,178 O / 0 M equal to the land/sea mask; locations equal today's cell centres from src/maps/projection.py; arrangements A, B, C; parts 6141 and 98138; always buildable; no new data file
- [x] T028 [P] [US2] Tests tests/unit/templates/test_geometry.py: `TemplateProjection.cells_for` (−1 off the board or on a margin stud), `locations()` (NaN on margin), `abs_lat()`, `height`, `width`. `Template.stud_at(lat, lon)` and `Template.location(row, col)` round-trip on every on-globe stud whose centre lies inside the outline, and `stud_at` is None on the margin. For the kit template, `stud_at` agrees with `KitProjection.rows_for_lat` and `cols_for_lon` (FR-005)
- [x] T029 [US2] Implement src/templates/__init__.py: `Template`, `load_template`, `list_templates`, `confirmed_templates`, `KIT_TEMPLATE_ID`, `MARGIN_PART_ID`, `TemplateError`, and `TEMPLATE_DIR` = src/data/templates/. Implement src/templates/geometry.py. Cite data-model.md Template.id, Template.projection, Template.board, Template.classes, Template.locations, Template.parts, Template.frame, Template.counts, Template.source, Template.corrections, Template.confirmation; TemplateLayoutDigest.layout_sha256; TemplateDataset.id, .version, .title, .publisher, .license, .citation, .doi; TemplateCorrection.row, .col, .class, .reason; Confirmation.role, .date; TemplateProjection.cells_for, .locations, .abs_lat. Cached load < 100 ms
- [x] T030 [US2] Fixtures in tests/conftest.py, both built with tools/maptemplates/testing.py:
  - `synthetic_template`: the committed fixture from cli/tests/fixtures/templates/, with `TEMPLATE_DIR` pointed at it.
  - `confirmed_winkel`: `confirmed_copy` of src/data/templates/winkel-tripel.json and its ice file (T076), with the test confirmation `{"role": "project owner", "date": "2026-11-23"}`. Because the layout digest leaves the confirmation out, the copied ice file stays valid. It uses the committed file as is once that is confirmed, and falls back to the fixture template before T037 and T076.
- [x] T031 [P] [US2] Contract tests tests/contract/test_template_contract.py (contracts/cli.md), each command printing the disclaimer last:
  - `template list [--format table|json]`: id, title, status `reference`/`confirmed`/`unconfirmed`, counts, arrangements
  - `template show ID [--format table|json]`: projection, board, parts, counts, ring, modules, corners, source dataset, number of corrections, confirmation; an unknown ID exits 1
  - `template locate ID LAT LON`: row, column, section label and class, or "off the globe (margin)"
  - `template locate ID --stud ROW COL`: the stud's location and class; out-of-range input exits 2
- [x] T032 [US2] Implement src/cli/template.py and register the group in src/cli/main.py

**Checkpoint**: suite green; kit golden unchanged.

---

## Phase 3: Maintainer tool, review sheet, owner review (US2)

**Goal**: generate, review, write and check the Winkel layout (FR-003, FR-017, FR-018; research
R2, R4, R5).

**Independent test**: the offline tool tests pass without pyproj. With pyproj and the cached ETOPO
file, `generate` writes a candidate, a sheet and flags outside the repository, and `build --check`
prints "no differences"; changing one committed stud makes it fail.

- [x] T033 [US2] Add `pyproj = ">=3.7,<3.8"` to `[tool.poetry.group.maintainer.dependencies]` in cli/pyproject.toml (MIT; 3.8 needs Python 3.12; research R4) and run `poetry install --with maintainer`; update the install text in tools/projection_study/README.md to the pin (Spilhaus still needs pyproj ≥ 3.8)
- [x] T034 [P] [US2] Tests tests/unit/tools/test_maptemplates.py, offline, with a small numpy plate-carrée projection object instead of pyproj:
  - Method: 4 × 4 subsamples, round-trip tolerance, on the globe at ≥ 50 %, land at ≥ 50 % with elevation > 0 m.
  - Location rule: the inverse of the stud centre, or the spherical mean of on-globe subsamples when the centre lies outside the outline.
  - Flags: land share 40–60 %, and water groups not 4-connected to the main ocean, with their sizes; fields and the `reason` values as in data-model.md ReviewFlag.
  - Corrections: applied in order; out-of-board, stale, and margin → land/ocean without on-globe samples are errors.
  - Document writer: one board row per line, field order, 4 decimals. The confirmation is written only with `--confirmed-on`, is cleared when classes or locations change, and has exactly the keys role and date.
  - Differences: every field except `generated_on`; a class change names its stud.
  - Exit codes: 0, 1 (differences), 4 (dataset missing or checksum mismatch).
  - Review sheet PNG: classes, ring, module lines, section names A1–H5, flagged studs, the disclaimer. The disclaimer is printed last.
  - One end-to-end Winkel test, run only with `pytest.importorskip("pyproj")` and the cached ETOPO file.
- [x] T035 [US2] Implement tools/maptemplates/generate.py: built on projection_study.raster `Proj`, `rasterise` and `classify`, with the exact extent from src/templates/winkel.py (research R2); computes locations, the 24 check points and the flags. Implement tools/maptemplates/review.py (sheet PNG and flags JSON) and tools/maptemplates/document.py (write, read, apply corrections, diff). Add the commands `generate`, `review`, `write` and `build --check` to tools/maptemplates/__main__.py (contracts/template-file.md). Cite data-model.md Template.source; TemplateCorrection.row, .col, .class, .reason; Confirmation.role, .date; ReviewFlag.row, .col, .class, .land_share, .reason (exactly "land share 40-60%" or "water not connected to the ocean"), .group_size
- [x] T036 [US2] Run `PYTHONPATH=tools poetry run python -m maptemplates generate winkel-tripel` on the cached pinned ETOPO 2022 file; the candidate, review sheet and flags go to `<cache>/templates/`, outside the repository. Record the counts in run-state.md: about 2,553 / 5,691 / 1,996, ring 288, corners 14 × 14 (research R2), and about 194 + 97 flags
- [x] T037 [US2] Write the unconfirmed package file src/data/templates/winkel-tripel.json (`maptemplates write winkel-tripel`, no `--confirmed-on`). `build winkel-tripel --check` → exit 0 "no differences"; changing one character of `classes` → exit 1 naming the stud; then restore it (quickstart step 6)
- [x] T038 [P] [US2] Tests tests/unit/templates/test_packaged_winkel.py: the package file loads; derived counts equal the recorded ones; check points pass; `confirmation` is null or exactly role "project owner" and a date; no personal name in the file; `source.dataset` agrees with the registry entry `etopo2022-surface-10m` (id, version, SHA-256, citation, license). Extend tests/contract/test_disclaimer.py to src/data/templates/*.json (FR-022)
- [x] T039 [US2] (owner confirmed as is, 2026-11-24) **OWNER STOP (not the agent)**: the agent sends the owner the T036 review sheet, flags and counts, and asks for (1) hand corrections as row, column, new class and reason, and (2) a yes with the date. The confirmation is recorded only as role "project owner" and the date, with no personal name (research R5). This blocks only Phase 6b and the real-data web check T105; the agent continues with Phases 4–7 on `confirmed_winkel`

**Checkpoint**: suite green; the committed template is unconfirmed, and `map build` refuses it (T044).

---

## Phase 4: Building on a template (US1) 🎯 MVP core

**Goal**: `map build` and `map check` on Winkel: template resolution and errors, sampling and
rules on the template, margin and ring, layout format, preview shapes, report blocks (FR-006 –
FR-013; research R6–R9, R11–R13).

**Independent test**: on `confirmed_winkel` with the dataset fixtures, `ocean-sst` builds 10,240
positions with the template's counts, a Black square-tile margin and a recorded template; kit builds
are golden-identical.

- [x] T040 [P] [US1] Tests tests/unit/maps/test_recipe_template.py: an optional top-level `template` key (an unknown id is a recipe error at key path `template` naming the confirmed templates; an unconfirmed id parses); an optional `[margin]` table with `color` (default `lego_black`) and `ring`; unknown `[margin]` keys rejected by `_check_keys`; every bundled recipe parses as before (contracts/recipe-and-outputs.md)
- [x] T041 [US1] Implement in src/maps/recipe.py (data-model.md MarginTreatment.color, MarginTreatment.ring)
- [x] T042 [P] [US1] Tests tests/unit/maps/test_margin.py: the recipe's margin overridden per field by `--margin-color` and `--ring-color` (`none` turns a recipe ring off); colors must be cited 3070b colors, and the ring must differ from the margin; errors name the option or key path, list the available 3070b color keys, and point to `kit part-colors --part 3070b` (spec Edge Cases); ring cells are the margin studs with an on-globe 4-neighbour (count equals the template's ring); default Black with no ring (US1-4, US1-5)
- [x] T043 [US1] Implement src/maps/margin.py (data-model.md MarginTreatment.color, .ring; the color error as in MarginTreatment)
- [x] T044 [P] [US1] Tests tests/unit/maps/test_template_resolution.py (pattern of test_build_arrangement_source.py), with errors and exit codes as in contracts/cli.md:
  - Resolution: `--template` > recipe `template` > `kit-31203`; `template_source` (`option`, `recipe`, `default`) appears only in non-kit reports.
  - Errors: an unconfirmed template; a resolved arrangement other than A, from the recipe (ENSO `B`) or `--arrangement`, naming its source; a layer on a dataset whose registry entry has `format == "kit-design"` (`kit31203-design`, used by `official-31203`), suggesting `official-31203-bathymetry`; `--compare-official` on a non-kit template.
  - Allowed: an explicit `--arrangement A` builds an ENSO recipe on Winkel; the automatic official comparison is off for `official-31203-bathymetry` on Winkel.
  - `templates.compatibility(recipe, template)` over the 8 bundled recipes returns None for exactly the five eligible maps (US3-1).
- [x] T045 [US1] Implement template resolution and its errors in src/maps/build.py (`build_map(..., template=None, margin=None)`, `MapResult.template`), and `compatibility` in src/templates/__init__.py, which tests each layer's registry entry for `format == "kit-design"` (research R6, R8)
- [x] T046 [P] [US1] Tests tests/unit/maps/test_reproject_template.py (research R6):
  - `mean` sampling: forward binning into on-globe studs; margin studs receive nothing; pixels off the board or on margin studs are dropped; studs without a pixel take the nearest value, reported as `filled`.
  - `bilinear` sampling: at the stored stud locations; margin studs are skipped.
  - Points grids: binned by forward projection.
  - Chunking bounds memory; variance lost is computed over the template's studs.
- [x] T047 [US1] Implement the template branch in src/maps/reproject.py, selected by the projection's type; the kit branch stays line for line
- [x] T048 [P] [US1] Tests tests/unit/maps/test_template_rules.py: no-data `unobserved` latitudes, region overrides (Antarctica, Greenland), dataset overrides, `class_rule.land_from`, and the ice-sheet and sea-ice overrides of the recipes use each stud's own template location; the same place gets the same rule on the kit and on Winkel; the existing no-data rules apply to studs without data (spec Edge Cases)
- [x] T049 [US1] Implement the template branches in src/maps/nodata.py (`cell_latitudes`) and src/maps/overrides.py (map builds never read src/maps/ice.py; its template loader is T078)
- [x] T050 [P] [US1] Tests tests/unit/maps/test_shadow_halo_template.py: shadow = `shadow_mask(land) & ocean`, so a land stud whose eastern neighbour is margin casts none (the kit result is unchanged because ocean = ~land); halo, `mix` and `blend` never color a margin stud; nearest fill draws only from layer studs; no wrap at the board edges (research R7)
- [x] T051 [US1] Implement in src/maps/build.py and src/maps/texture.py
- [x] T052 [P] [US1] Tests tests/unit/test_position.py and tests/unit/test_grid.py: part type `square_tile` with `lego_part_id` 3070b. `metadata.template`, `metadata.margin_positions`, `metadata.map.margin`, `statistics.margin_tile_count` and `statistics.color_frequency_by_part_type.square_tile` are written only for non-kit layouts. A layout without `metadata.template` reads as the kit; `metadata.arrangement` is A (FR-010)
- [x] T053 [US1] Implement in src/layout/position.py (`PART_ID_FOR_TYPE`) and src/layout/grid.py (data-model.md Layout (extended): positions part_type, metadata.template, metadata.margin_positions, metadata.map.margin, metadata.arrangement)
- [x] T054 [P] [US1] Tests tests/unit/maps/test_preview.py: a non-kit preview draws on-globe studs as rounds (diameter 0.95 of the pitch on Black, drawn at 4× and downsampled) and margin studs as full squares (pixel probes at a stud centre and a corner); kit previews unchanged (research R13, FR-012). Updated 2026-11-23 for main 6038d9c: every preview draws main's rounds on black (diameter 0.9, 8×, background (0, 0, 0)), margin studs full squares, kit previews equal main's (research R13 note)
- [x] T055 [US1] Implement the non-kit stud shapes in src/maps/preview.py `write_preview`
- [x] T056 [P] [US1] Integration tests tests/integration/test_map_winkel.py on `confirmed_winkel` with the dataset fixtures:
  - `ocean-sst` gives 10,240 positions with the template's land, ocean and margin counts (US1-1; SC-002 on fixtures).
  - Every margin stud is 3070b Black; every on-globe stud has a cited color of its class's part.
  - `metadata.template` includes the file SHA-256, `layout_sha256`, the confirmation and `dataset`, the ETOPO 2022 provenance copied from the registry entry `etopo2022-surface-10m` (id, version, title, publisher, license, citation, doi). The report's `citations` list it once after the recipe's datasets, and the report's `template` carries it. Kit layouts and reports have none of these keys.
  - `--ring-color` colors exactly the ring studs (US1-5).
  - A recipe `template` key is used without `--template`; `--template kit-31203` wins and is golden-identical (US1-2, US1-3).
  - `[margin]` on a kit build prints the note and changes nothing.
  - All five eligible recipes build; land ≤ 3,064 and ocean ≤ 8,066 (SC-004).
  - The suitability report names the template with its counts, `template_source` and `margin` (FR-013); `map check` agrees.
- [x] T057 [US1] Implement the template build branch and the report blocks in src/maps/build.py: fill the margin from src/maps/margin.py; run suitability on the template's studs; add the template dataset to `metadata.template` and the report's `citations`; write the new keys only for non-kit builds (research R8, R11; data-model.md Layout (extended).metadata.template, SuitabilityReport.template, .template_source, .citations, TemplateDataset)
- [x] T058 [P] [US1] Contract tests tests/contract/test_map_template_contract.py:
  - Options on `map build` and `map check`: `--template`, `--margin-color`, `--ring-color`.
  - Output lines: `Template: …`, `Margin: N square tiles (part 3070b): …; ring …`, and `Layout: …, N margin tiles`.
  - Every error in the contracts/cli.md table with its exit code (2 for an unknown `--template`) and the disclaimer last.
  - Kit build output text is unchanged.
- [x] T059 [US1] Implement the options and output in src/cli/map.py and src/cli/options.py
- [x] T060 [P] [US1] Performance test in tests/integration/test_map_performance.py: a Winkel build of a fixture recipe within 2× its kit build; template load < 100 ms when cached (plan Performance Goals)

**Checkpoint**: `map build ocean-sst --template winkel-tripel -o layout.json --preview p.png` works on
the confirmed copy; kit golden unchanged.

---

## Phase 5: Parts, prices, sheets, validation (US1)

**Goal**: square tiles in every downstream output (FR-011, FR-014 – FR-016; research R14–R17).

**Independent test**: a Winkel fixture layout gives a complete parts list totalling 10,240 with
cited 3070b IDs, exports, an estimate (incomplete with the old fixture, complete with the 3070b
fixture), 40 sheets with square margin studs, and validation against its template.

- [x] T061 [P] [US1] Tests tests/unit/parts/test_partslist.py, tests/unit/parts/test_export.py and tests/integration/test_parts_winkel.py:
  - Lots: 3070b lots of type `square_tile` after 6141 and 98138, with cited LEGO, BrickLink (`item_no` from part_numbers.json: 3070, BrickLink's number for 3070b) and Rebrickable (`part_num` 3070b) IDs.
  - Totals: quantities sum to 10,240 (SC-003); `--kits 1` buys every square tile (kit supply 0, US1-6).
  - `leftovers` lists kit elements only; `layout.template` is `{id, title}`.
  - Exports: BrickLink XML `<ITEMID>3070</ITEMID>` (part_numbers.json) and Rebrickable CSV `3070b,<color>,<qty>` rows.
  - `sheets.legend.PART_LABEL` has an entry for every `PART_TYPE`.
  - web/tests/test_prebuild.py: a kit-only prebuild still writes `part_labels` with exactly 6141 and 98138.
- [x] T062 [US1] Implement in src/parts/partslist.py (`PART_ORDER`, `PART_TYPE`), src/parts/export.py, src/parts/resolve.py and src/kit/inventory.py (`supplied_for` is 0 for 3070b). Cite data-model.md PartsListLot.part_id, .part_type, .kit_supply and the lot order; PartsList.layout.template, .leftovers, .totals; ExportRow (BrickLink `ITEMID`, Rebrickable row); Part 3070b.kit_supply.
  - In the same task, add `square_tile: "tile 1x1 square"` to src/sheets/legend.py `PART_LABEL`. Without it, web/src/web98138/prebuild.py `_part_labels()`, which maps every `PART_TYPE` through `PART_LABEL`, raises `KeyError` (research R16).
  - Change `_part_labels()` to list only the part IDs that the built variants' lots use, so a kit-only site's `part_labels` stays exactly 6141 and 98138 (data-model.md Manifest.part_labels; web golden T009).
- [x] T063 [P] [US1] Extend tools/fixtures011/make_price_fixture.py to write tests/fixtures/prices/bricklink_price_guide_3070b.json (+ .source.json) with a 3070b Black lot; the existing synthetic fixture stays byte-identical (research R15)
- [x] T064 [P] [US1] Tests tests/unit/prices/test_lots.py, tests/unit/prices/test_snapshot.py, tests/unit/prices/test_estimate.py and tests/integration/test_prices_estimate.py: 3070b in `PART_ORDER`/`PART_TYPE`; `parse_lot("3070b:26")` (today's `_LOT_RE` `^(\d+):(\d+)$` rejects it), and an unknown part still rejected; `recipe_lots()` adds each bundled recipe's margin colors (one new Black lot); snapshot lots sorted 6141, 98138, 3070b; a Winkel estimate with the existing fixture is incomplete and lists the square-tile colors as unpriced, and is complete with the 3070b fixture; kit estimates unchanged (spec Edge Cases)
- [x] T065 [US1] Implement in src/prices/lots.py and src/prices/snapshot.py:
  - Widen `_LOT_RE` to `^(\d+[a-z]?):(\d+)$`; `parse_lot` keeps checking `PART_ORDER`.
  - Accept `parts prices fetch --lot 3070b:26` (never called in tests; contracts/cli.md).
  - Cite data-model.md PriceLot.id, PriceLot order (6141, 98138, 3070b, then LEGO color ID), PriceLot.recipe_lots; Estimate.complete, Estimate.lines.basis (`unpriced` with `reason`).
- [x] T066 [P] [US1] Tests tests/unit/sheets/test_compose.py, tests/unit/sheets/test_legend.py, tests/unit/sheets/test_counts.py and tests/integration/test_sheets_winkel.py (US1-7, FR-015, SC-004):
  - Pages: 40 section pages; margin studs drawn as `Rect` with their lot numbers; the overview draws small squares.
  - Legend: a square swatch labelled "tile 1x1 square".
  - Text: the totals line "N tiles 1x1 square (margin, part 3070b)"; the subtitle and arrangement sentence name the template and say the frames cannot be re-hung; the disclaimer on every page.
  - Counts: per-section counts include square tiles; `sheets counts` JSON has `template`.
  - Provenance: a template line with id, projection, file SHA-256 and confirmation, and the ETOPO 2022 dataset (id, version, title, license, citation). Kit sheets have no such line.
- [x] T067 [US1] Implement in src/sheets/compose.py, src/sheets/legend.py and src/sheets/counts.py, using the `PART_LABEL` entry from T062 (research R16). Cite data-model.md LegendRow.part_type, LegendRow.label ("tile 1x1 square"), SectionCounts.template, SheetProvenance.template
- [x] T068 [P] [US1] Tests tests/unit/test_validator.py and tests/contract/test_validate_contract.py: for a non-kit layout, the mask check compares each position's part with its template class part (`mask_mismatch` with `template`); square tiles are `color_unavailable` for 3070b with no suggestion; kit layouts validate as before (FR-016, research R17)
- [x] T069 [US1] Implement in src/layout/validator.py and src/cli/validate.py
- [x] T070 [P] [US1] Tests tests/unit/test_arrangement.py and tests/contract/test_arrange_contract.py: `layout arrange` on a layout with `metadata.template` exits 1 with "the frames of a curved map cannot be re-hung (template winkel-tripel)" (FR-011)
- [x] T071 [US1] Implement in src/layout/arrangement.py and src/cli/layout.py
- [x] T072 [P] [US1] Contract tests tests/contract/test_parts_contract.py and tests/contract/test_sheets_contract.py: `parts list`, `parts export`, `parts estimate`, `sheets build` and `sheets counts` accept a Winkel layout; "square tile" appears in tables and JSON; the disclaimer is last; kit output unchanged
- [x] T073 [US1] Implement the remaining CLI wording in src/cli/parts.py, src/cli/prices.py (`parts estimate`) and src/cli/sheets.py

**Checkpoint**: US1 complete on the confirmed copy (layout, preview, report, parts list, exports,
estimate, sheets, validation); kit golden unchanged.

---

## Phase 6: Map cells and template ice regions (US1, US2)

**Goal**: `map cells` on templates and per-template ice regions (FR-020a, FR-020b; research R18).

**Independent test**: `ice-mask winkel-tripel --check` prints "no differences"; Winkel cells.json
has `M` cells, `template`, `margin`, `palette["3070b"]` and the template's ice; its default
rendering equals the layout.

- [x] T074 [P] [US2] Tests tests/unit/tools/test_maptemplates_ice.py: `ice-mask ID [--check]` applies the kit's rules at the template's stud locations by forward binning: land ice in Antarctica and the Greenland box; sea ice where the ERSST v5 1991–2020 warmest month ≤ −1.5 °C, or no value poleward of 60°. Land ice falls only on L and sea ice only on O; the file records `template_id` and `source.template_layout_sha256` (the layout digest, not the file's SHA-256), so confirming the template leaves `--check` passing; `--check` exits 0 "no differences" or 1; no pyproj import; disclaimer (FR-020b)
- [x] T075 [US2] Implement tools/maptemplates/ice.py and the `ice-mask` command, reusing the rules in src/maps/ice.py and the tools/kit31203 `ice-mask` code (data-model.md Template ice regions.template_id, .template_layout_sha256, .land_ice, .sea_ice, .cells)
- [x] T076 [US2] Generate src/data/templates/winkel-tripel-ice.json from the committed, unconfirmed template with the cached ERSST v5 data; `PYTHONPATH=tools poetry run python -m maptemplates ice-mask winkel-tripel --check` → "no differences". It stays valid when the confirmation is written; only corrections that change classes make T082 regenerate it
- [x] T077 [P] [US1] Tests tests/unit/maps/test_ice.py: `load_template_ice(template)` reads `<id>-ice.json` and refuses a file whose `template_layout_sha256` differs from the loaded template's `layout_sha256`. It accepts the same ice file for a copy that differs only in `confirmation`, and returns `data/kit_31203_ice.json` for `kit-31203`
- [x] T078 [US1] Implement in src/maps/ice.py (data-model.md Template ice regions.template_layout_sha256)
- [x] T079 [P] [US1] Tests tests/integration/test_map_cells.py and tests/contract/test_map_cells_contract.py (FR-020a):
  - On Winkel: `cells` contains `M`; `template` is `{id, title, dataset}` with the ETOPO 2022 id, version, citation and license; `margin` is `{part_id: 3070b, color, ring}`; `palette["3070b"]` runs light → dark with L*; `ice` comes from the template's ice file.
  - The default rendering equals layout.json.
  - `map cells` takes `--template`, `--margin-color` and `--ring-color`.
  - Kit cells.json is unchanged (golden).
- [x] T080 [US1] Implement in src/maps/cells.py (`map_cells`; `part_palette` lists the template's parts) and src/cli/map.py (data-model.md Map cells.cells, .template, .template.dataset, .margin, .palette, .ice)

**Checkpoint**: suite green; kit golden unchanged.

---

## Phase 6b: Apply the owner's confirmation (US2; after T039)

**Goal**: a confirmed, reproducible Winkel template in the package (SC-002, SC-005).

- [x] T081 [US2] (2026-11-24: no corrections, so `write winkel-tripel --confirmed-on 2026-11-24` without `--corrections`; see run-state.md) Once the owner answers T039, write the corrections to a file and run `PYTHONPATH=tools poetry run python -m maptemplates write winkel-tripel --corrections FILE --confirmed-on YYYY-MM-DD` with the owner's date. Then check (quickstart steps 5–6):
  - `lego-image-processor template show winkel-tripel` shows role "project owner" and the date.
  - `build winkel-tripel --check` → exit 0 "no differences" (SC-005); a one-character change → exit 1; restore it.
  - `confirmed_winkel` now uses the committed file.
- [x] T082 [US2] (2026-11-24: "no differences"; the T076 file is kept) Run `ice-mask winkel-tripel --check` on the confirmed file. If the owner's corrections changed classes, the check reports differences: regenerate src/data/templates/winkel-tripel-ice.json and check again. If not, the T076 file is kept. Either way `--check` ends with "no differences" (quickstart step 7)
- [x] T083 [US1] (2026-11-24, on the package file; see run-state.md) Real-data builds on the confirmed template (quickstart steps 8–9) for `official-31203-bathymetry`, `ocean-sst`, `land-elevation`, `living-planet` and `rainfall`. Record counts, pieces beyond one kit and leftovers in run-state.md. Check:
  - Counts equal `template show` (SC-002); parts total 10,240 and every color is cited (SC-003); land ≤ 3,064 and ocean ≤ 8,066 (SC-004).
  - The preview, sheets, `validate`, `map cells` and `--ring-color lego_white` work.
  - The quickstart step 9 errors exit 1 with the contracts/cli.md messages.

---

## Phase 7: Winkel versions on the web site (US3, P2)

**Goal**: a Winkel variant for each eligible bundled map, with kit variants unchanged (FR-019,
FR-020, FR-020a, FR-022; research R19; contracts/web.md).

**Independent test**: an offline prebuild with fixtures lists a Winkel variant with checksummed
files, the map page links to it and works without JavaScript, and `web/tests/test_kit_golden.py`
passes.

- [x] T084 [US3] web/tests/conftest.py: put `cli/tools` on `sys.path` and import tools/maptemplates/testing.py (T025); the web suite cannot use the CLI conftest fixtures. Give the whole session a confirmed template with `confirmed_copy` of the committed template, or the committed fixture template before T037, and `use_template_dir` for the session. The small site then has a Winkel variant of ocean-sst; kit variants and the T009 golden stay unchanged
- [x] T085 [P] [US3] Tests web/tests/test_templates.py:
  - Manifest: a top-level `templates` list (id, title, projection, board, counts, `rehang: false`, description, source); `maps[].template_variants["winkel-tripel"]` for ocean-sst only, none for official-31203 or ocean-el-nino; `variants` exactly A, B, C.
  - Files under maps/ocean-sst/winkel-tripel/ with sizes and SHA-256; download names `98138-world_<map>_winkel-tripel_<stem>.<ext>`.
  - Options: `--templates none` builds kit variants only, and its top-level `part_labels` equals the T009 golden (6141 and 98138 only); a site with a template variant adds `3070b` "tile 1x1 square"; an unconfirmed template gives no variants.
  - Eligibility over all `MAP_IDS` through `templates.compatibility` is exactly the five maps (US3-1, SC-006).
  - With the fixture snapshot, the Winkel estimate is incomplete.
- [x] T086 [US3] Implement web/src/web98138/__init__.py (`TEMPLATES`) and web/src/web98138/prebuild.py: `--templates LIST|none`, template variants with the same files as kit variants, and the manifest additions. `_part_labels()` adds 3070b only when a template variant exists (data-model.md Manifest.templates, Manifest.maps[].template_variants, Manifest.part_labels)
- [x] T087 [P] [US3] Tests web/tests/test_catalog.py: `template_variants` keys must be listed in `templates` and must not be A, B or C; their files are checked like kit files; estimates as for kit variants; `variant_count` counts both
- [x] T088 [US3] Implement in web/src/web98138/catalog.py
- [x] T089 [P] [US3] Tests web/tests/test_routes.py (US3-2, US3-3, FR-020, FR-022):
  - Routes: `GET /maps/ocean-sst/winkel-tripel` and its preview.png, thumb.png, cells.json and download/<kind>; 404 for an unknown template or a map without one; `/maps/<map>` still redirects to the default combination.
  - Page: the variant nav offers "Winkel tripel" beside A, B and C; the figcaption "Round studs for land and ocean, square tiles in the margin"; the cannot-be-re-hung note and the parts note.
  - Without JavaScript: previews and downloads work.
  - The footer disclaimer, the templates paragraph on the about page, and an unchanged CSP.
  - The Winkel page's citations list ETOPO 2022 as the template's dataset (from the report).
  - Kit pages change only by the Winkel link. Kit map pages (A, B, C) of the eligible maps in the test sites (ocean-sst in the session site; living-planet and rainfall in their sites) equal the T009 golden HTML after removing the "Winkel tripel" nav item, with asset tokens normalised. Kit pages of official-31203 and ocean-el-nino equal the golden exactly.
- [x] T090 [US3] Implement in web/src/web98138/app.py, web/src/web98138/templates/map.html, web/src/web98138/templates/about.html and web/src/web98138/static/style.css; kit pages gain only the Winkel nav link
- [x] T091 [P] [US3] Node-backed tests in web/tests/test_palette.py (skipped without Node): with `M` cells, `cellColors` keeps margin and ring cells in their colors; `classShares` and the ice flags leave `M` out; template variants draw rounds and squares (US3-4)
- [x] T092 [US3] Implement in web/src/web98138/static/palette.js (pure functions and canvas drawing)
- [x] T093 [US3] Browser check (Chromium, when available) of /maps/ocean-sst/winkel-tripel on a local prebuild. With JavaScript: land and ocean recolor; the margin stays square in its color; "show ice as White" covers the template's ice; the fragment restores the state. With JavaScript off: previews and downloads work

**Checkpoint**: web suite green, including web/tests/test_kit_golden.py.

---

## Phase 8: (removed)

Corner labels in the margin (US4, P3; tasks T094–T099) were removed on 2026-11-23: labels moved to
feature 017, map stickers (spec Clarifications). The IDs T094–T099 are not reused.

---

## Phase 9: Docs and final checks

- [x] T100 [P] README.md line 3, the constitution 3.0.0 follow-up from T002: the kit is the reference template and Winkel tripel is the first other one. cli/README.md:
  - Commands: `template list/show/locate`; `map build/check/cells` with `--template`, `--margin-color` and `--ring-color`; `kit part-colors --part 3070b`.
  - Recipe keys: `template` and `[margin]`.
  - Maintainer `maptemplates` commands.
  - Line 179: replace "fixed kit 31203 template".
- [x] T101 [P] docs/vision.md: 016 row "built" (template model, Winkel tripel, square-tile margin with an optional outline ring; the 017 row stays as it is); web/README.md: template variants and `--templates`; docs/deploy.md: template variants need a confirmed template, no new build dependency, and the deploy itself is the owner's step
- [x] T102 CLAUDE.md and AGENTS.md: the same feature 016 paragraph in both. Cover: `templates/` and `data/templates/`; `template` commands; `map build --template` and `[margin]`; 3070b; `maptemplates` (generate, review, write, `build --check`, `ice-mask`, `kit-golden`); owner confirmation as role and date; the kit golden; web template variants. Add `templates/` to the Layout list and `maptemplates` to the tools line. Remove nothing else
- [x] T103 FR-022 audit, extending tests/contract/test_disclaimer.py where needed: the disclaimer is in the template and ice files; in `template` and `maptemplates` output; in the review sheet, Winkel layouts, sheets and cells.json; and on the web pages
- [x] T104 Real-data kit check (SC-001, quickstart step 10): `PYTHONPATH=tools poetry run python -m maptemplates kit-golden --cache-dir <cache> --out ~/kit-after.json`; `diff ~/kit-before.json ~/kit-after.json` prints nothing
- [x] T105 (2026-11-24, on the committed template the owner confirmed; see run-state.md) Real-data web check (quickstart step 11), local only with no `fly` command: `python -m web98138.prebuild --out site --no-prices`; serve it with uvicorn. Check:
  - /maps/<map>/winkel-tripel for the five eligible maps.
  - The cannot-be-re-hung note; the page works with JavaScript off.
  - No Winkel version for official-31203, ocean-el-nino or ocean-la-nina (SC-006).
  - Timing: also run `--templates none` into a second directory. Record the wall time and output size of both runs in run-state.md; the default run is expected about +20 % over kit-only (24 → 29 variants; plan Performance Goals).
  - Kit pages: for the five eligible maps, kit pages served from the two sites differ only by the Winkel nav link.
- [x] T106 Walk quickstart.md steps 1–11 and fix any mismatch between the docs and the behaviour (step 12 is T109)
- [x] T107 Full test runs with the socket guard on (SC-007): `cd cli && poetry run pytest` (or `.venv/bin/pytest`) and `cd web && .venv/bin/pytest` (setup per CLAUDE.md); record counts against T001 in run-state.md
- [x] T108 Update specs/016-map-templates/run-state.md: phase, the decisions taken during implementation, the owner tasks still open (T109, and T039/T081 if pending)

---

## Phase 10: Owner steps (not the agent; do not block the agent's completion)

- [ ] T109 **OWNER (not the agent)**: with the four `BRICKLINK_*` environment variables set (never written or logged), run `poetry run lego-image-processor parts prices fetch -o src/lego_image_processor/data/bricklink_price_guide.json` from `cli/`. The default lot set now includes the 3070b margin lots (T065). Review the snapshot and commit it; Winkel estimates then become complete (quickstart step 12). Until then they are marked incomplete, as 011 does for any unpriced part

---

## Dependencies and execution order

- Phase 0 first: no production change before T006 and T009. Then Phase 1 → 2 → 3 → 4 → 5 → 6 →
  7 → 9, in the plan's order (Phase 8 was removed).
- Phase 1 (3070b data) blocks every task that colors or counts square tiles: the margin color
  checks (T042–T043), the preview (T054–T055), the build and report (T056–T057), the parts
  lists (T061–T062), prices (T064–T065), sheets (T066–T067), cells (T079–T080) and the web
  phase. Phases 2–3 do not need it, so they can run while T011 waits for the owner.
- Phase 2 (template model) blocks Phases 3–7. Phase 3's offline tool tests (T034) need only
  Phase 2.
- T039 (owner) blocks only Phase 6b (T081–T083) and the real-data web check T105. Phases 4–7 run
  on `confirmed_winkel` (T030). T104 (kit real-data check) needs only the finished code.
- T020a–T020b (layout digest) precede T025 (fixture ice file) and T029. T076 needs T037 (the
  committed template) and T075; T082 needs T081 and regenerates only if corrections changed
  classes.
- T062 adds the 3070b part type, the `PART_LABEL` entry and the `_part_labels()` restriction
  together, so the web prebuild never meets a part type without a label.
- Phase 7 (web) needs Phases 4–6 (build, parts, sheets, cells).
- T109 (owner) needs T065 and gates only complete Winkel estimates; it blocks no agent task.

Within phases, each test task precedes the implementation it drives: T004→T005; T020a→T020b; T012, T013→T015;
T014→T016; T018→T019; T021→T022; T023→T024; T026–T028→T029; T031→T032; T034→T035; T040→T041;
T042→T043; T044→T045; T046→T047; T048→T049; T050→T051; T052→T053; T054→T055; T056→T057;
T058→T059; T061→T062; T064→T065; T066→T067; T068→T069; T070→T071; T072→T073; T074→T075;
T077→T078; T079→T080; T085→T086; T087→T088; T089→T090; T091→T092. T016 and T017 land together. T045, T051 and T057 all edit src/maps/build.py, so they
run in order.

## Parallel opportunities

- Phase 0: T004 alongside T003; T008 and T009 together after T006.
- Phase 1: T012, T013, T014 together; T018 alongside T015.
- Phase 2: T020a, T021, T023 together; then T026, T027, T028 together (after T025); T031 alongside T029.
- Phase 3: T034 while T033 installs pyproj; T038 after T037.
- Phase 4: the test tasks T040, T042, T044, T046, T048, T050, T052, T054 together. Of their
  implementations, T041, T043, T047, T049, T053, T055 touch different files and can run together;
  the build.py tasks run in order.
- Phase 5: T061, T063, T064, T066, T068, T070, T072 together; T062, T065, T067, T069, T071
  together after their tests.
- Phase 6: T074 and T077 together; T079 after T078.
- Phase 7: T085, T087, T089, T091 together after T084.
- Phase 9: T100, T101 together; T104 after Phase 7; T105 once T081 is done.

## Implementation strategy

1. **Golden first** (Phase 0): every later change is measured against unchanged kit outputs.
2. **MVP, a usable CLI build on Winkel**: Phases 0–5 (T001–T073) and T081, which needs the owner's
   T039. With them, `map build <recipe> --template winkel-tripel` gives a layout, preview, report,
   parts list, exports, estimate and sheets for the five eligible maps on the confirmed template.
   Before T081 the same works in tests on the confirmed copy, and the CLI refuses the unconfirmed
   package file by design (FR-004). T001–T060 alone give layout, preview and report.
3. **US2 complete**: T081–T082 (confirmed, `--check` reproducible, ice regions).
4. **US3** (web, P2): Phase 7 after Phase 6.
5. **Finish**: Phase 9; the owner runs T109 and deploys. Margin labels follow in feature 017 (map
   stickers), not in this feature.

## Coverage

| Requirement | Tasks |
|---|---|
| FR-001 template definition, versioned cited data | T020a, T020b, T026, T029, T035, T037 |
| FR-002 kit template default and unchanged | T006, T007, T009, T027, T029, T044, T045 |
| FR-003 `winkel-tripel` (φ1 50.4598°, λ0 11.1° E, 8 × 5) | T023, T024, T035–T037, T081 |
| FR-004 only confirmed templates build | T026, T029, T038, T044, T045, T081, T085 |
| FR-005 stud locations and stud lookup | T028, T029, T031, T032 |
| FR-006 template from recipe or option; additive keys | T040, T041, T044, T045, T058, T059 |
| FR-007 sampling at stud locations; margin takes no data | T046, T047, T056, T057 |
| FR-008 rules and neighbourhoods on templates | T048–T051 |
| FR-009 3070b margin, color and ring, cited colors | T010–T019, T042, T043, T056, T057 |
| FR-010 layout records template; absent = kit | T052, T053 |
| FR-011 arrangement, `layout arrange`, `official-31203` errors | T044, T045, T058, T059, T070, T071 |
| FR-012 rounds and squares in previews | T054, T055, T091, T092 |
| FR-013 reports and suitability name the template (with its dataset citation) | T056, T057, T058, T066, T067, T079, T089 |
| FR-014 parts, exports, top-up, leftovers, prices incl. 3070b | T010–T017, T061–T065, T072, T073, T109 |
| FR-015 sheets: squares, legend, counts | T066, T067 |
| FR-016 validation against the template | T068, T069 |
| FR-017 maintainer tool, review sheet, flags, `--check` | T034–T037, T039, T081 |
| FR-018 template file records source, corrections, confirmation | T026, T029, T035, T038, T081 |
| Template dataset provenance in outputs (Principle IV; research R11) | T026, T038, T056, T057, T066, T067, T079, T080, T089 |
| FR-019 web prebuild template variants, kit files unchanged | T009, T084–T088 |
| FR-020 map page offers Winkel, cannot re-hang, no-JS | T089, T090, T093 |
| FR-020a `map cells` on templates | T079, T080, T091, T092 |
| FR-020b per-template ice regions with `--check` | T020a, T020b, T074–T078, T082 |
| FR-021 corner labels | removed, moved to 017 |
| FR-022 disclaimer on new outputs | T005, T031, T034, T038, T058, T066, T074, T089, T103 |
| SC-001 kit outputs byte-identical | T004–T009, T062, T085, T089, every checkpoint, T104, T105 |
| SC-002 five maps, counts equal the confirmed template's | T056, T083 |
| SC-003 parts total 10,240, all cited | T061, T083 |
| SC-004 kit modules and frame; ≤ 3,064 plates, ≤ 8,066 tiles | T056, T066, T083 |
| SC-005 `--check` "no differences" | T037, T081 |
| SC-006 web Winkel for five maps; kit variants unchanged | T009, T085, T105 |
| SC-007 offline tests | T034, T107 |

Not affiliated with or endorsed by The LEGO Group.

---

## Phase 11: Convergence (Converge round 1, 2026-11-23)

Assessed against spec.md (FR-001 to FR-022, SC-001 to SC-007, US1 to US3 acceptance scenarios, Edge
Cases, Clarifications), plan.md, contracts/ and every task above. Owner-gated work (T002, T039,
T081 to T083, T105, T109, deploy) is not repeated here.

- [x] T110 [US1] Keep kit-layout parts lists byte-identical to main when an `--owned` or `--missing` Rebrickable CSV lists part 3070b or one of its other catalog numbers (3070, 30039, 35403, 39727, 53836, 112412, from part_numbers.json). Today, on a kit layout, a `3070b` row is no longer counted in `ignored_rows` (text "N row(s) for other parts ignored" and JSON `owned.ignored_rows` drop by one), and a row with one of the other numbers stops `parts list`/`parts export` with "part 3070 is another catalog's number for map part 3070b", where main ignored both. For a layout with no square tiles, count those rows as ignored exactly as before; keep today's counting (owned loose square tiles) and the other-number error for template layouts (src/parts/owned.py with its callers in src/parts/partslist.py and src/cli/parts.py). Add tests for both cases (kit: ignored, no error; Winkel: counted as owned 3070b) in tests/unit/parts/ and tests/contract/test_parts_contract.py per SC-001, FR-014 (contradicts)
- [x] T111 [US1] Make the ring-equals-margin error name the available 3070b color keys and point to `kit part-colors --part 3070b`, as the not-a-3070b-color error already does: src/maps/margin.py `ring_rule`, used by `resolve_margin` (`--ring-color`, `--margin-color`) and src/maps/recipe.py (`margin.ring`). Extend tests/unit/maps/test_margin.py, tests/unit/maps/test_recipe_template.py and `test_ring_equal_to_margin` in tests/contract/test_map_template_contract.py per spec Edge Cases ("or the same color for both: error naming the available colors"), contracts/cli.md error table, research R12 (partial)

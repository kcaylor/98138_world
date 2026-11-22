# Tasks: ENSO Sea Surface Temperature Anomaly Maps (009)

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/ (recipe-arrangement.md,
datasets.md, recipes.md), quickstart.md, run-state.md

**Tests**: required (Constitution VII, spec FR-019). Each implementation task follows the failing
test it makes pass. All tests offline; real-data steps are maintainer steps and marked as such.

**Paths**: all under `cli/` unless stated (`cli/src/lego_image_processor/` = `src/`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1, US2, US3 (spec.md user stories)

---

## Phase 1: Setup

- [X] T001 Record the baseline: `cd cli && poetry run pytest -q` (or `.venv/bin/pytest -q`); write the pass count into specs/009-enso-sst-maps/run-state.md

---

## Phase 2: Foundational (blocks every story)

**Purpose**: read the per-month files, pin them, and give the tests offline fixtures. Tests
parametrised over `bundled_recipes()` (references, performance, sheets, parts) need the fixtures in
`fixture_registry` before any ENSO recipe is added.

- [X] T002 [P] Reader tests in cli/tests/unit/datasets/test_readers.py (write small netCDF-3 files with `scipy.io.netcdf_file` in `tmp_path`): `(time=1, lev=1, lat, lon)` float32 reads as 2-D with the right values; `_FillValue -999.0` → NaN (FR-003); packed int16 with `scale_factor 0.01`, `_FillValue -999` → NaN and scaled values; `(time=2, lev=1, …)` with no reduce → `ValueError` naming `time=2, lev=1`; `(1, lat, lon)` and `(12, lat, lon)` + annual-mean unchanged; annual-mean on a `(1, 1, lat, lon)` field keeps "needs 12 months, found 1"; a file starting `\x89HDF` → "not a netCDF-3 classic file (netCDF-4/HDF5 signature)"; other junk → "not a netCDF-3 classic file" (data-model.md SourceGrid read rule; contracts/datasets.md Reader)
- [X] T003 Implement the size-1 leading-axis squeeze, the dimension-named error and the signature check in src/datasets/readers.py `read_netcdf3` (FR-002, FR-003; research R2)
- [X] T004 [P] Registry tests in cli/tests/unit/datasets/test_registry.py: `ersst-v5-1997-12` and `ersst-v5-1988-12` exist, `kind` download, `format` netcdf3, `size` 134832, `sha256` equal to the run-state values, NCEI https URLs and filenames, variable `ssta` units `degC` with no `reduce`, `class_rule` missing_is_land, `doi` 10.1175/JCLI-D-16-0836.1, citation contains `10.7289/V5T72FNM`, license contains "No constraints on data access or use" (data-model.md DatasetEntry.id, DatasetEntry.version, DatasetEntry.kind, DatasetEntry.url, DatasetEntry.format, DatasetEntry.sha256, DatasetEntry.size, DatasetEntry.variables, DatasetEntry.class_rule)
- [X] T005 Add the two rows to src/data/datasets.json exactly as contracts/datasets.md (FR-001; data-model.md DatasetEntry)
- [X] T006 [P] Tool test in cli/tests/unit/tools/test_fixtures_ersst_month.py: `make_ersst_month` on a synthetic 4-D source (via a stub entry/cache dir) writes netCDF-3 with dims `time=1, lev=1, lat, lon`, `ssta` int16, `scale_factor 0.01`, `_FillValue -999`, `units degree_C`, no `sst`, and a `.source.json` with fixture, dataset, version, source_sha256, source_url, method, license, citation, doi, generator, disclaimer, units, sha256 (data-model.md Fixture.structure)
- [X] T007 Implement `make_ersst_month(dataset_id, cache_dir, out)` and an `--only <dataset id>` option (repeatable; default all) in cli/tools/fixtures004/make_fixtures.py (research R6)
- [X] T008 Maintainer step (network): `lego-image-processor dataset fetch ersst-v5-1997-12` and `… ersst-v5-1988-12`, then `PYTHONPATH=tools poetry run python -m fixtures004.make_fixtures --only ersst-v5-1997-12 --only ersst-v5-1988-12`; commit-ready files cli/tests/fixtures/datasets/ersst_v5_199712_ssta.nc, ersst_v5_198812_ssta.nc and their .source.json (never the downloaded files; data-model.md Fixture.budget: total fixtures < 300,000 bytes)
- [X] T009 Extend `fixture_registry` in cli/tests/conftest.py: rewrite `filename`, `size`, `sha256` of the two new rows to the fixtures (keep `variables`), add them to `fr.files` so `place_all()` caches them
- [X] T010 Reader fixture test in cli/tests/unit/datasets/test_readers.py: `read_dataset` on each fixture via `fixture_registry` gives an 89×180 grid, land = NaN cells (5,032), values within ±5 °C (FR-002, FR-003)

**Checkpoint**: `pytest -q` passes as at T001 plus the new tests.

---

## Phase 3: User Story 1 — El Niño map, reader, recipe `arrangement` key (P1) 🎯 MVP

**Goal**: `map build ocean-el-nino` gives the December 1997 anomaly hung as B from the recipe key,
with the °C legend, extra-tile total, citations and disclaimer.

**Independent test**: with the 1997 fixture cached, build `ocean-el-nino` offline; layout records
B, ocean colors follow the legend, Niño 3.4 cells are warm.

### Recipe key and precedence

- [X] T011 [P] [US1] Recipe tests in cli/tests/unit/maps/test_recipe.py: `arrangement = "B"`, `"b"`, `"americas"` parse to B; absent → `Recipe.arrangement is None`; `"D"`, `2`, `true`, a table → `RecipeError` with path `arrangement` and message listing A, B, C, europe-africa, americas, asia-australia; `format` still "1"; an unknown top-level key is still rejected (data-model.md Recipe.arrangement; contracts/recipe-arrangement.md Recipe key)
- [X] T012 [US1] Implement the key in src/maps/recipe.py (`_TOP_KEYS`, `Recipe.arrangement`, `_arrangement()` using `layout.arrangement.parse_arrangement`) (FR-010)
- [X] T013 [P] [US1] Library tests in cli/tests/unit/maps/test_build_arrangement_source.py (use small recipes parsed from text with background layers, so no dataset is needed): `resolve_arrangement` returns (B, "recipe") for a recipe with `arrangement = "B"`, (A, "option") when A is passed, (A, "default") when neither; `build_map`/`check_recipe` report `arrangement` and `arrangement_source` accordingly and the layout's `metadata.arrangement` follows; a recipe without the key built with no arrangement gives positions and metadata equal to an explicit A build (SC-006); a recipe whose `[ocean.local]` netcdf3 file starts with `\x89HDF` (sha256 of that file declared) raises `MapBuildError` "cannot read <id>" (data-model.md ArrangementResolution; FR-011, FR-012)
- [X] T014 [US1] Implement `resolve_arrangement`, the report field `arrangement_source` and the `ValueError` → `MapBuildError` wrap in src/maps/build.py (FR-011, FR-012; research R2, R3; data-model.md ArrangementResolution, Report.arrangement_source)
- [X] T015 [P] [US1] Suitability tests in cli/tests/unit/maps/test_suitability.py: `extra_tiles(rep["supply"])` = Σ max(0, used − supplied) with a non-kit color counted in full and `extra_use` (shadow) included; 0 when within supply; `layer_report` output keys unchanged (data-model.md Report.extra_tiles)
- [X] T016 [US1] Implement `extra_tiles(supply_rows)` in src/maps/suitability.py (FR-016)

### CLI

- [X] T017 [P] [US1] Contract tests in cli/tests/contract/test_map_enso_contract.py (CliRunner, `fixture_registry`): `map build ocean-el-nino -o x.json` prints `Arrangement: B (americas, …) - from the recipe`; with `--arrangement A` prints `- from --arrangement` and the layout records A (US1-2); `map build ocean-sst` prints `- default`; the legend block for the bins layer has 9 lines from `below -1.5` to `+1 and above` under `Legend (°C):`; `Tiles beyond one kit: N` equals `extra_tiles` of the report's ocean supply rows; `--report` JSON has `arrangement_source`; `map check ocean-el-nino` shows the same source line and legend; not cached → exit 3 naming `dataset fetch ersst-v5-1997-12` with no network (US1-3); `dataset fetch ersst-v5-1997-12` with a fake opener serving wrong bytes → exit 4 (US1-4); output has the Huang et al. citation, `10.1175/JCLI-D-16-0836.1`, `10.7289/V5T72FNM`, the license and the disclaimer (US1-5); `--arrangement D` → exit 2 (contracts/recipe-arrangement.md)
- [X] T018 [US1] `map recipes` contract test in cli/tests/contract/test_map_enso_contract.py: header has `arrangement`; `ocean-el-nino` row shows `B`, `ocean-sst` row shows `A` (FR-014)
- [X] T019 [US1] Implement `arrangement_option(default=None)` use for `map build`/`map check` with the new help text in src/cli/options.py and src/cli/map.py; source suffix on the Arrangement line; legend block (units from the recipe layer, data-model.md Report.legend units) and `Tiles beyond one kit` line in `echo_report`; `arrangement` column in `map recipes` (FR-012, FR-014, FR-015; contracts/recipe-arrangement.md)
- [X] T020 [P] [US1] Update the bundled-recipe id lists in cli/tests/contract/test_map_contract.py (`BUNDLED`) and cli/tests/unit/maps/test_recipe.py (bundled set) to include `ocean-el-nino`

### The map

- [X] T021 [US1] Integration tests in cli/tests/integration/test_map_enso.py (`fixture_registry.place_all()`): `ocean-el-nino` builds offline; `metadata.arrangement.id == "B"`, report `arrangement_source == "recipe"`; ocean layer `bins` with the bounds and colors of data-model.md Shared legend (Shared legend.bounds, Shared legend.colors); no texture (Shared legend.texture); a cell at exactly −0.1 or +0.1 goes to the upper class (Shared legend.class membership, tested on a hand-made field in cli/tests/unit/maps/test_classify.py); title and description name El Niño and December 1997 (FR-009); filled share reported and below 5 %; land all `lego_white`, shadow 390 Earth Blue; every ocean color a kit 98138 color (SC-005); ≥ 90 % of Niño 3.4 cells (centres in 5° S–5° N, 170° W–120° W via `KitProjection.cell_center` of the kit column) in a class with lower bound ≥ +0.5 (SC-002); `extra_tiles` of the ocean supply ≤ 1,200 (SC-004); `outside_bounds` absent; layout metadata dataset has license, citation, doi; recipe file contains the disclaimer (FR-009); `arrange_grid` to A re-hangs without rebuilding
- [X] T022 [US1] Add src/maps/recipes/ocean-el-nino.toml exactly as contracts/recipes.md (FR-005–FR-009, FR-013; data-model.md Shared legend)

**Checkpoint**: US1 independently testable; full suite green.

---

## Phase 4: User Story 2 — La Niña map, identical legend (P2)

**Goal**: `map build ocean-la-nina` gives December 1988 hung as B with the same legend.

**Independent test**: build `ocean-la-nina` offline from its fixture; bounds and colors equal
`ocean-el-nino`; Niño 3.4 cells cold.

- [X] T023 [US2] Integration tests in cli/tests/integration/test_map_enso.py: `ocean-la-nina` builds offline as B (recipe source); its `classification.bounds` and `colors` equal `ocean-el-nino`'s (SC-003; data-model.md Shared legend.bounds, Shared legend.colors); title and description name La Niña and December 1988 (FR-009); ≥ 90 % of Niño 3.4 cells in a class with upper bound ≤ −0.5 (SC-002); `extra_tiles` of the ocean supply ≤ 1,200 (SC-004); a cell with the same color in both layouts has the same °C class (class index equality per color) (US2-3); an `empty_class` warning, if any, does not fail the build
- [X] T024 [US2] Add src/maps/recipes/ocean-la-nina.toml per contracts/recipes.md (FR-005–FR-009, FR-013)
- [X] T025 [P] [US2] Add `ocean-la-nina` to the bundled-recipe id lists in cli/tests/contract/test_map_contract.py and cli/tests/unit/maps/test_recipe.py; add a `map recipes` assertion (B) in cli/tests/contract/test_map_enso_contract.py

**Checkpoint**: both maps build; full suite green.

---

## Phase 5: User Story 3 — extra tiles in parts lists, docs (P3)

**Goal**: a maker with one kit sees exactly which ocean tiles to buy; README and runbook describe
both maps.

**Independent test**: `parts list --kits 1` on each built layout totals the build's
`extra_tiles`, within the bound.

- [X] T026 [P] [US3] Integration tests in cli/tests/integration/test_parts_topup.py (or a new cli/tests/integration/test_parts_enso.py): for both ENSO layouts built from fixtures, `build_parts_list(layout, owned=OwnedInputs(kits=1))` ocean `to_buy` equals `extra_tiles` of the report's ocean supply rows, per color equal to `max(0, used − supplied)`; land 6141 lots need 0 (US3-1; FR-016; data-model.md Report.extra_tiles)
- [X] T027 [P] [US3] Contract tests in cli/tests/contract/test_map_enso_contract.py: `parts list <el-nino.json> --kits 1` prints the shortfall colors; `parts export <layout> --kits 1 --bricklink wanted.xml` writes only the over-supply ocean lots with quantities equal to the shortfalls (US3-2); output ends with the disclaimer
- [X] T028 [US3] Fix any disagreement found by T026/T027 in src/maps/suitability.py or src/parts/ (expected: none; the arithmetic is shared, research R5)
- [X] T029 [P] [US3] Update cli/README.md "Maps from recipes": six bundled recipes, two new table rows, an "ENSO maps" paragraph with the legend table (research R1), default arrangement B and the recipe key `arrangement`, extra tiles (1,114 / 1,155) and `parts list --kits 1`, the planned 2026–27 swap (needs a netCDF-4 reader) (FR-017, FR-018)
- [X] T030 [P] [US3] Add an "ENSO maps" section to docs/runbook.md: the four commands of SC-007, expected output lines, extra tiles per map, `--arrangement` override, the 2026–27 note (FR-017)
- [X] T031 [US3] Docs test: extend cli/tests/contract/test_disclaimer.py (or a new docs check) so the README mentions `ocean-el-nino`, `ocean-la-nina` and `arrangement`; bundled recipe files carry the disclaimer (existing test covers the new files)

---

## Phase 6: Polish & cross-cutting

- [X] T032 Full suite offline: `poetry run pytest -q`; confirm `test_no_large_data.py` (fixture budget), `test_map_performance.py`, `test_sheets_layouts.py`, `test_parts_list.py` and `test_map_references.py` pass with the two new recipes
- [X] T033 SC-006 check: build `official-31203`, `official-31203-bathymetry`, `ocean-sst`, `land-elevation` from fixtures on this branch and on `main` (or compare with explicit `--arrangement A`); layouts identical apart from `generated_at`; record in run-state.md
- [X] T034 Maintainer step (network, optional): run quickstart.md section 2 on the real files; record extra tiles (expected 1,114 / 1,155) and Niño 3.4 shares in run-state.md
- [X] T035 Update specs/009-enso-sst-maps/run-state.md (Phase: implement done); add one short 009 line to the root CLAUDE.md in the style of the existing feature notes (nothing else in CLAUDE.md)

---

## Dependencies

- Phase 2 blocks all stories (fixtures + registry + reader; T009 needs T005 and T008).
- US1: T012 before T014 (build reads `recipe.arrangement`); T014, T016 before T019; T022 after
  T012/T014/T003/T009. T021 needs T022 to pass.
- US2 depends on US1 (shares the key, CLI and legend); only adds a recipe and tests.
- US3 depends on US1 (and US2 for the La Niña half); T029–T031 can start once T022/T024 exist.
- Polish after all stories.

## Parallel examples

- Phase 2: T002, T004, T006 together (different test files); then T003, T005, T007.
- US1: T011, T013, T015, T017 together (four test files); then T012 → T014 → T016 → T019; T020
  any time.
- US3: T026, T027, T029, T030 together.

## Implementation strategy

MVP = Phases 1–3 (El Niño map with the arrangement key). Then US2 (one recipe + tests), then US3
(verification and docs), then polish. Stop at each checkpoint with the full suite green.

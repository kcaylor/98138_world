# Tasks: Palette chooser and ice toggle

Tests first for core logic (constitution VII). [P] = parallelisable.

## Phase 1: Ice regions (FR-003)
- [x] T001 Test `reduce="monthly-max"` in `cli/tests/unit/datasets/test_readers.py`
- [x] T002 Implement `monthly-max` in `datasets/readers.py`
- [x] T003 Tests `cli/tests/unit/maps/test_ice.py` (regions, land/sea rules, packaged file, roll)
- [x] T004 Implement `maps/ice.py`
- [x] T005 Maintainer tool `kit31203 ice-mask [--check]`; generate `data/kit_31203_ice.json`; run `--check`

## Phase 2: Map cells, CLI first (FR-001, FR-002, FR-004, FR-005)
- [x] T006 Tests `cli/tests/integration/test_map_cells.py` (format, palette, default = layout, bounds, values, no-value, halo, categorical)
- [x] T007 Contract tests `cli/tests/contract/test_map_cells_contract.py`
- [x] T008 Implement `maps/cells.py` (`map_cells`, `part_palette`, `lightness`)
- [x] T009 Implement `map cells` in `cli/map.py`

## Phase 3: Prebuild and service (FR-006–FR-008)
- [x] T010 Tests `web/tests/test_palette.py` (manifest, route, CSP, script, markup, old output, SC-001)
- [x] T011 Prebuild writes `cells.json` (kind `cells`); catalog `DATA_KINDS`; route; CSP; static script; content-versioned assets
- [x] T012 Amend 008 tests for FR-020 (`test_routes.py`: only first-party script; cells is not a download)

## Phase 4: Chooser UI (FR-009–FR-019, FR-021)
- [x] T013 Map template markup (hidden section, noscript note, preview-only note, ice fieldset)
- [x] T014 `static/palette.js`: pure functions (classOf, equalShareBounds, spreadColors, validBounds, cellColors, classShares, encode/decodeState) + page wiring
- [x] T015 Node-backed test of the pure functions (skipped without Node)
- [x] T016 Chooser CSS; `[hidden]` override; 360 px layout
- [x] T017 Browser check (Chromium): recolor, 5 classes, invalid bound refused, ice White, fragment restore, reset

## Phase 5: Docs (FR-022)
- [x] T018 About page section; CLAUDE.md/AGENTS.md paragraph; vision row; web and CLI READMEs; 008 FR-009 amendment note
- [x] T019 Full CLI and web test runs

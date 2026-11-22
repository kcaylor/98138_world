# Tasks: Map Arrangements (007)

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/cli.md
Tests first: each implementation task follows its failing test.

## Phase 1: Setup

- [x] T001 Record baseline: `cd cli && .venv/bin/pytest -q` (879 pass)

## Phase 2: Foundational

- [x] T002 [P] Unit tests for arrangement data and model in cli/tests/unit/test_arrangement.py (load, citation, shifts A 0 / B 32 / C −32 derived from frame order, parse ids/names case-insensitive, unknown value error, to_display/to_kit inverse, roll/unroll, frame spans and boundaries A {32,96} B {32,64} C {64,96}, disclaimer)
- [x] T003 Add cli/src/lego_image_processor/data/kit_31203_arrangements.json (FR-001)
- [x] T004 Implement cli/src/lego_image_processor/layout/arrangement.py (FR-002, FR-003)
- [x] T005 [P] Unit tests for layout grid arrangement metadata (absent = A; written when set; round-trip) in cli/tests/unit/test_arrangement.py
- [x] T006 Grid support in cli/src/lego_image_processor/layout/grid.py (FR-009)

## Phase 3: User Story 1 — build any recipe in any arrangement (P1)

- [x] T007 [US1] Tests in cli/tests/unit/maps/test_build_arrangement.py: official-31203 equals shifted official design in A/B/C (FR-007, SC-001); shadow in display coordinates, none in column 0 (SC-004); halo distances in display; fixture data recipe land counts equal and per-cell equal shifted (FR-004/005); agreement in B equals A (FR-008); metadata.arrangement written (FR-009); mix no wrap (FR-006)
- [x] T008 [US1] Implement in cli/src/lego_image_processor/maps/build.py and maps/texture.py
- [x] T009 [US1] Contract tests for `map build/check --arrangement` in cli/tests/contract/test_arrange_contract.py (values, names, case, exit 2, output line, disclaimer)
- [x] T010 [US1] Implement options in cli/src/lego_image_processor/cli/map.py

## Phase 4: User Story 2 — re-hang a layout (P2)

- [x] T011 [US2] Unit tests for `arrange_grid` (A→B moves x+32; B→C equals A→C; identity; round trip byte-identical positions; partial layout; width≠128 error; unknown recorded id error) in cli/tests/unit/test_arrangement.py
- [x] T012 [US2] Implement `arrange_grid` in layout/arrangement.py (FR-010)
- [x] T013 [US2] Contract tests for `layout arrange` and unchanged `layout IMAGE` in cli/tests/contract/test_arrange_contract.py (FR-011)
- [x] T014 [US2] Implement the `layout` group with fallback in cli/src/lego_image_processor/cli/layout.py

## Phase 5: User Story 3 — validate under the arrangement (P2)

- [x] T015 [US3] Tests: B layout passes; B positions labelled A fail with mask_mismatch; CLI output names arrangement (unit + contract)
- [x] T016 [US3] Implement in layout/validator.py and cli/validate.py (FR-012)

## Phase 6: User Story 4 — preview, sheets, counts, parts (P3)

- [x] T017 [US4] Tests in cli/tests/unit/sheets/test_arrangement_sheets.py: arranged sections (labels by display, frame, kit_label, instruction page); overview frame lines B {32,64} C {64,96} A {32,96}; frame names in display order; combination text; section page frame and kit section; locator frame lines; counts JSON fields; preview pixel at display coordinates; parts list same lots + arrangement note (FR-013–FR-016)
- [x] T018 [US4] Implement in sheets/sections.py, sheets/compose.py, sheets/counts.py, parts/partslist.py

## Phase 7: Polish

- [x] T019 Integration test with real-data-shaped fixtures in cli/tests/integration/test_map_arrangements.py (build A/B/C for a fixture recipe, arrange official, validate, sheets for B)
- [x] T020 Docs: README, docs/vision.md roadmap 007, docs/runbook.md "Arrangements", scripts/demo.sh, CLAUDE.md project section (FR-018)
- [x] T021 Full test run; e2e in the session scratchpad (`e2e007/`), montage and overview PNG
- [x] T022 Commit on 007-map-arrangements

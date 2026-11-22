---
description: "Task list for feature 005: Parts Lists and Ordering"
---

# Tasks: Parts Lists and Ordering

**Input**: Design documents from `specs/005-parts-lists/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (cli.md,
export-formats.md, parts-list-format.md, data-files.md, library-api.md), quickstart.md

**Tests**: Required. Constitution VII: each test task is written first and must FAIL before its
implementation task. No test opens the network (offline guard in `cli/tests/conftest.py`) or reads
an archived page or catalog download (FR-019).

**Organization**: by user story (US1 = P1 … US4 = P4). Paths relative to the repository root; run
commands from `cli/`.

**Decisions applied** (run-state.md Q1–Q6, confirmed by the user on 2026-11-22): Q1 `--kits`,
`--owned`, `--missing` in Rebrickable import CSV; Q2 exit 6 / `--allow-partial`; Q3 widen color
tables (US4); Q4 no disclaimer inside marketplace files; Q5 `parts list|export`, `kit
part-numbers`; Q6 map pieces only. Tasks tagged with a Q id follow that answer.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US4 (story phases only)

---

## Phase 1: Setup

- [X] T001 Create package `cli/src/lego_image_processor/parts/__init__.py`, maintainer package `cli/tools/partnumbers/__init__.py`, and test dirs `cli/tests/unit/parts/`, `cli/tests/fixtures/parts/`
- [X] T002 [P] Add small fixtures in `cli/tests/fixtures/parts/`: a synthetic schema 2.0 layout builder helper (`cli/tests/unit/parts/conftest.py`) producing kit-mask layouts with chosen color counts, an uncited-color layout, a color-code-mismatch layout, and owned/missing CSVs (both header shapes, BOM+CRLF, duplicates, a bad quantity, a non-map part row)

---

## Phase 2: Foundational (blocks every story)

- [X] T003 [P] Unit test for the archived-page parser (item no, alternates, color dropdown list ending before the first "Name (count)" entry) on a trimmed synthetic HTML snippet in `cli/tests/unit/tools/test_partnumbers.py`
- [X] T004 Implement `cli/tools/partnumbers/build.py` and `__main__.py`: pinned pages (research R1 URLs + SHA-256), source cache `<cache>/sources/partnumbers/`, download if absent (maintainer only), verify SHA-256 of decoded HTML, parse with `html.parser`, write `part_numbers.json`, `--check` reports differences
- [X] T005 Run the tool and commit `cli/src/lego_image_processor/data/part_numbers.json` (contract data-files.md); confirm values: 4073 alt 6141 / Rebrickable 6141; 98138 / 98138; record the run in run-state.md
- [X] T006 [P] Unit tests for `load_part_numbers()` validation (missing part, missing SHA-256, plate alternates lack 6141) in `cli/tests/unit/kit/test_part_numbers.py`
- [X] T007 Implement `cli/src/lego_image_processor/kit/part_numbers.py` (`PartNumbers`, `PartNumberTable`, `load_part_numbers`) and export from `kit/__init__.py`
- [X] T008 [P] Unit test: part-color build applies rule 5 (a synthetic BrickLink color list without a color excludes it with reason) and writes `source.terms` in place of `license_note` in `cli/tests/unit/tools/test_partcolors.py`
- [X] T009 Extend `cli/tools/partcolors/build.py`: rule 5 using the BrickLink part pages from the partnumbers source cache, add them to `snapshots`, replace `license_note` with `terms` (research R5); loader in `kit/part_colors.py` accepts `terms`
- [X] T010 Regenerate `part_colors.json` with the current reviewed list; verify all 23 rows unchanged (diff of `parts`), `--check` "no differences"
- [X] T011 [P] Unit test `KitInventory.supplied_for(part_id, color_key)`: Bright Green plate → 0, Bright Green tile → 601, White plate → 3,064 (research R11) in `cli/tests/unit/kit/test_inventory.py`
- [X] T012 Implement `KitInventory.supplied_for` in `cli/src/lego_image_processor/kit/inventory.py`
- [X] T013 [P] Unit test layout loading helper (schema 2.0 only, SHA-256 of file bytes, `metadata.map` extraction, error on unreadable file) in `cli/tests/unit/parts/test_layout_input.py`
- [X] T014 Implement layout input helper in `cli/src/lego_image_processor/parts/partslist.py` (load via `PositionPlacementGrid.from_json`, hash bytes)

**Checkpoint**: cited part numbers and supply-by-part available.

---

## Phase 3: User Story 1 - Parts list with verified IDs (P1) MVP

- [X] T015 [P] [US1] Unit tests for `resolve_color`: kit color, non-kit cited plate color, uncited color → `no cited color for part`, code mismatch → `color code mismatch`; plate carries BrickLink 4073 / Rebrickable 6141, tile 98138 in `cli/tests/unit/parts/test_resolve.py`
- [X] T016 [US1] Implement `cli/src/lego_image_processor/parts/resolve.py`
- [X] T017 [P] [US1] Unit tests for lot grouping, ordering (plate→tile, LEGO ID, unverified last), totals, and `to_json` determinism and key order (contract parts-list-format.md) in `cli/tests/unit/parts/test_partslist.py`
- [X] T018 [US1] Implement `build_parts_list` (needed only; owned = 0) and `PartsList.to_json` in `cli/src/lego_image_processor/parts/partslist.py`, with citations and Rebrickable acknowledgement
- [X] T019 [P] [US1] Integration test: official layout (`load_official_design().to_layout()`) → 10 verified lots, 10,240 pieces, counts equal design counts; recipe fixture layout records `metadata.map` in `cli/tests/integration/test_parts_list.py`
- [X] T020 [P] [US1] Contract tests `parts list` (table/json/-o, unverified warning, exit 0, disclaimer last, bad layout exit 1) and `kit part-numbers` in `cli/tests/contract/test_parts_contract.py` (Q5)
- [X] T021 [US1] Implement `cli/src/lego_image_processor/cli/parts.py` (`parts` group, `list`), `kit part-numbers` in `cli/kit.py`, register in `cli/main.py`

**Checkpoint**: US1 works alone (SC-001 first half, SC-002, SC-007 for these commands).

---

## Phase 4: User Story 2 - BrickLink and Rebrickable exports (P2)

- [X] T022 [P] [US2] Unit tests `to_bricklink_xml`: no declaration, element order, MINQTY, CONDITION only when given, escaping, deterministic bytes, `None` when nothing to buy, `UnverifiedLotsError` unless allow_partial; parse back with `xml.etree` and compare quantities in `cli/tests/unit/parts/test_export.py`
- [X] T023 [P] [US2] Unit tests `to_rebrickable_csv`: header, Rebrickable IDs, `\n`, no BOM, round trip through `parse_owned_csv` gives the same quantities, in `cli/tests/unit/parts/test_export.py`
- [X] T024 [US2] Implement `cli/src/lego_image_processor/parts/export.py` (research R2, R3; Q4)
- [X] T025 [P] [US2] Contract tests `parts export`: needs one target, writes files, exit 6 with unverified lots and nothing written, `--allow-partial` lists omitted, nothing-to-buy message and no file, BrickLink "adds to existing quantity" note, disclaimer last in `cli/tests/contract/test_parts_contract.py` (Q2)
- [X] T026 [US2] Implement `parts export` in `cli/src/lego_image_processor/cli/parts.py`

**Checkpoint**: SC-004 on fixtures.

---

## Phase 5: User Story 3 - Kit top-up (P3)

- [X] T027 [P] [US3] Unit tests `parse_owned_csv`: both header shapes, case/order/extra columns, BOM, CRLF, duplicates summed, errors with file:line (bad header, negative/non-integer qty, uncited map-part color, unknown element), non-map rows ignored and counted, in `cli/tests/unit/parts/test_owned.py` (Q1)
- [X] T028 [US3] Implement `cli/src/lego_image_processor/parts/owned.py`
- [X] T029 [P] [US3] Unit tests for arithmetic: kits N, missing floor 0, owned added, shortfall/surplus, spares ceil with Fraction (2% of 2,145 → 43; 0 when no shortfall), in `cli/tests/unit/parts/test_partslist.py`
- [X] T030 [US3] Implement owned inputs and arithmetic in `build_parts_list` using `supplied_for`
- [X] T031 [P] [US3] Integration test: land-elevation-like synthetic layout with the real counts from research R6 → 11/6,382, 10/4,178, 9/2,912 for 1/2/3 kits; official layout `--kits 1` → nothing to buy, White plate surplus 2, in `cli/tests/integration/test_parts_topup.py`
- [X] T032 [P] [US3] Contract tests for `--kits`, `--owned`, `--missing`, `--spares` on both commands, usage errors for negative kits and spares > 100 in `cli/tests/contract/test_parts_contract.py` (Q1, Q5)
- [X] T033 [US3] Add shared top-up options to both commands in `cli/src/lego_image_processor/cli/parts.py`

**Checkpoint**: SC-003 on fixtures; quickstart §4–5.

---

## Phase 6: User Story 4 - Verified colors for every layout source (P4) (Q3)

- [X] T034 [P] [US4] Unit test: all-colors build mode keeps existing rows identical and excludes a rule-5 failure (Medium Blue analogue) on synthetic snapshots in `cli/tests/unit/tools/test_partcolors.py`
- [X] T035 [US4] Replace `REVIEWED` with an all-listed-colors mode in `cli/tools/partcolors/build.py` (opaque colors listed in elements.csv for each part); report exclusions
- [X] T036 [US4] Regenerate `part_colors.json`; expect 44 plate and 40 tile rows (research R4); record exclusions in run-state.md; `--check` "no differences"
- [X] T037 [P] [US4] Integration test: feature-002 image fixture layout → all lots verified (SC-005); `kit part-colors` lists the new rows, in `cli/tests/integration/test_parts_list.py`
- [X] T038 [US4] Re-run the 004 suite to confirm recipes and `validate` are unaffected by the wider table

---

## Phase 7: Polish

- [X] T039 [P] Disclaimer tests across `parts list`, `parts export`, `kit part-numbers` human and JSON output (SC-007)
- [X] T040 [P] Performance test: list and export of a 10,240-position layout < 2 s (SC-006) in `cli/tests/integration/test_parts_topup.py`
- [X] T041 [P] Docs: `cli/README.md` section "Parts lists and ordering" (part-number table with sources, top-up examples, upload notes, no prices, Rebrickable acknowledgement); update `docs/vision.md` roadmap row 005 to "built" only after implement
- [X] T042 Update `specs/004-map-recipes/run-state.md` open question 1 as resolved by 005 research R5
- [X] T043 Run quickstart §1–7 with real 004 layouts; record figures in run-state.md
- [X] T044 Full test suite offline (SC-008)

---

## Dependencies

- Setup → Foundational → US1 → US2; US3 depends on US1 (arithmetic) and extends US2 commands;
  US4 depends only on Foundational (T009–T010) and can run in parallel with US2/US3.
- Within a story: tests before implementation.

## Parallel example (US1)

T015, T017, T019, T020 together (different files), then T016 → T018 → T021.

## MVP

Phases 1–3 (US1): a verified parts list from any layout.

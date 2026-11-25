# Tasks: Pacific-centred Arrangements D and E (010)

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/cli.md
**Tests**: required (constitution VII): each story's tests are written first and fail before code.

## Phase 1: Setup

- [x] T001 Record the baseline (CLI 1035 passed, web 77 passed) and keep A–C reference outputs for the
  unchanged-output check: official-31203 layouts A/B/C and their parts JSON in a scratch dir

## Phase 2: Foundational (data model, blocks every story)

- [x] T002 [P] Tests first in cli/tests/unit/test_arrangement.py: five ids A–E; D/E names, shifts 64/80,
  strips, groups 2b·3·1·2a, in_instructions false, joints source pp. 134–140; loader rejects a
  non-rotation strip order, a mismatched shift and mismatched groups; A–C `record()` exactly the
  007 dict; joints()/unpeg() for A–E; error text lists all ten values
- [x] T003 Rewrite cli/src/lego_image_processor/data/kit_31203_arrangements.json as format 2 (strips,
  groups, in_instructions, D, E, joints_source, assembly facts)
- [x] T004 Generalise cli/src/lego_image_processor/layout/arrangement.py: Group, Joint, group_spans,
  group_at, joints, unpeg, order_text, source, record, describe, assembly_steps, assembly_note;
  loader validation (FR-001–FR-004, FR-006)

## Phase 3: US1 — Hang any map as D or E (P1)

- [x] T005 [P] [US1] Contract tests in cli/tests/contract/test_arrange_contract.py: `layout arrange
  --arrangement D|pacific|E|asia-pacific`, round trip A→D→E→A identical, help/metavar/error list A–E
- [x] T006 [P] [US1] Integration tests in cli/tests/integration/test_map_arrangements.py: official-31203
  built D/E equals A rolled by 64/80; recipe key `arrangement = "E"` honoured; validate, parts list,
  sheets counts accept D/E (cli/tests/unit/test_validator_arrangement.py parametrised A–E)
- [x] T007 [US1] Update cli/src/lego_image_processor/cli/options.py (metavar, help) and
  cli/src/lego_image_processor/cli/layout.py (group labels) and the recipe error text in
  cli/src/lego_image_processor/maps/recipe.py if needed
- [x] T008 [US1] Update existing tests whose expected value lists were A–C only (test_recipe.py,
  test_arrange_contract.py) to A–E

## Phase 4: US2 — Assembly instructions (P2)

- [x] T009 [P] [US2] Tests first in cli/tests/unit/sheets/test_assembly_page.py: every set ends with one
  `assembly` page; D: strips E…D, groups, unpeg D|E (15 pegs), joints F|G H|A B|C, peg budget 201 of
  205, border pp. 140–153, "not among" status and citation; E: unpeg C|D; A–C: no unpeg, cites pp. 7–8
  and 139; disclaimer/footer; subset `--sections` still has it; SVG and PDF render; A–C pages other
  than the new one equal the previous pages except the "of N" footer and the overview page list
- [x] T010 [US2] Add `assembly_page()` and wire it into `build_sheet_set` in
  cli/src/lego_image_processor/sheets/compose.py; `page_kinds` gains `assembly`; overview lists the
  page; overview/section text uses groups for D/E (FR-007–FR-010)
- [x] T011 [US2] `sheets build` output line adds "1 assembly" in cli/src/lego_image_processor/cli/sheets.py;
  update contract tests that pin the page-kind line
- [x] T012 [US2] Runbook: assembly steps for D and E in text, five combinations (docs/runbook.md) (FR-011)

## Phase 5: US3 — ENSO maps default to D (P3)

- [x] T013 [P] [US3] Update tests pinning the ENSO default B to D (cli/tests/contract/test_map_enso_contract.py,
  cli/tests/integration/test_map_enso.py, cli/tests/unit/maps/test_recipe.py,
  cli/tests/unit/maps/test_build_arrangement_source.py); keep a B build via `--arrangement B`
- [x] T014 [US3] Set `arrangement = "D"` in ocean-el-nino.toml and ocean-la-nina.toml
- [x] T015 [US3] Real-data check: build both ENSO maps in D and E with previews, parts list --kits 1,
  El Niño sheets PDF in D into scratchpad out010/; record extra tiles and shadow cells
- [x] T016 [US3] Update recipe comments, cli/README.md ENSO section, spec 009 notes and runbook with the
  measured D numbers (FR-012)

## Phase 6: US4 — Web A–E (P4)

- [x] T017 [P] [US4] Tests first in web/tests: manifest has five arrangements with strips, groups,
  in_instructions, citation, assembly; catalog rejects three; /about lists five with "not among" for
  D/E; /maps/ocean-el-nino redirects to D; D page caption and assembly steps; nav lists A–E; runtime
  imports no CLI code (existing test)
- [x] T018 [US4] COMBINATIONS A–E in web/src/web98138/__init__.py; manifest rows in
  web/src/web98138/prebuild.py; catalog message; templates about.html, map.html; CSS if the nav
  needs it
- [x] T019 [US4] Deploy docs: docs/deploy.md variant count 30 and image size, Dockerfile comment,
  web/README.md if it states counts (FR-016)
- [x] T020 [US4] Real-data check: prebuild official-31203 and ocean-el-nino in A–E into scratchpad
  out010/site; render /about and /maps/ocean-el-nino/D via the test client

## Phase 7: Polish

- [x] T021 Update cli/README.md arrangements section, AGENTS.md and CLAUDE.md feature summaries for D/E
- [x] T022 Compare A–C reference outputs from T001 with new ones (layouts and parts JSON identical)
- [x] T023 Full CLI and web test suites; update run-state.md

## Dependencies

T002–T004 block all stories. US2 (T009–T012) and US3 (T013–T016) depend on US1 only; US4 depends on
US1–US3 (manifest assembly text, ENSO default). Within a story, tests precede code.

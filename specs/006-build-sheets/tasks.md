---
description: "Task list for feature 006: Build Sheets"
---

# Tasks: Build Sheets

**Input**: Design documents from `specs/006-build-sheets/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (cli.md,
page-layout.md, counts-format.md, library-api.md), quickstart.md; feature 005 implemented
(`lego_image_processor.parts`).

**Tests**: Required (constitution VII): tests first, failing before implementation; no network; no
instructions PDF or crops (FR-017).

**Provisional decisions applied** (run-state.md Q7–Q8): Q7 PDF via ReportLab + SVG; Q8 `sheets
build|counts`, flags, Letter default, true scale, labels A1–H5.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [ ] T001 Add `reportlab = ">=4.4,<6"` (BSD) to `[tool.poetry.dependencies]` and `pypdf = ">=5"` to the dev group in `cli/pyproject.toml`; confirm install in the test venv (Q7, research R2)
- [ ] T002 [P] Create `cli/src/lego_image_processor/sheets/__init__.py` and test dirs `cli/tests/unit/sheets/`

---

## Phase 2: Foundational

- [ ] T003 [P] Unit tests for `sections()`: 40 sections A1…H5, ranges cover 128 x 80 exactly, frames 1/2/3 at columns 0–1/2–5/6–7, order equals ascending 003 instruction page, in `cli/tests/unit/sheets/test_sections.py`
- [ ] T004 Implement `cli/src/lego_image_processor/sheets/sections.py` from `load_official_design().sections`
- [ ] T005 [P] Unit tests for the page model (PageSize letter/a4 mm, item dataclasses, Latin-1 check) in `cli/tests/unit/sheets/test_model.py`
- [ ] T006 Implement `cli/src/lego_image_processor/sheets/model.py`
- [ ] T007 [P] Unit tests for `build_legend`: numbering follows 005 lot order, same color on plate and tile gets two numbers, text color by luminance (White → black, Earth Blue → white), unverified entries "no cited IDs", in `cli/tests/unit/sheets/test_legend.py`
- [ ] T008 Implement `cli/src/lego_image_processor/sheets/legend.py` using `build_parts_list` (005)
- [ ] T009 [P] Unit tests for `section_counts`: each section totals 256, per-lot sums equal parts list needed, JSON key order and determinism (contract counts-format.md) in `cli/tests/unit/sheets/test_counts.py`
- [ ] T010 Implement `cli/src/lego_image_processor/sheets/counts.py`

---

## Phase 3: User Story 1 - Section pages with counts (P1) MVP

- [ ] T011 [P] [US1] Unit tests for `section_page`: 256 circles at 8.0 mm pitch (±0.05), numbers match layout lots, plates have inner rings, edge coordinates, locator highlight, count table sums to 256, scale bar 100 mm, footer disclaimer and page n of N, in `cli/tests/unit/sheets/test_compose.py`
- [ ] T012 [US1] Implement `section_page` and a minimal `build_sheet_set` (cover + 40 sections) in `cli/src/lego_image_processor/sheets/compose.py` (contract page-layout.md)
- [ ] T013 [P] [US1] Unit tests for the PDF backend: page count and size, extracted text has every label and the disclaimer (pypdf), no image XObjects, byte-identical twice, in `cli/tests/unit/sheets/test_render_pdf.py`
- [ ] T014 [US1] Implement `cli/src/lego_image_processor/sheets/render_pdf.py` (ReportLab canvas, `invariant=1`, Helvetica, mm → pt)
- [ ] T015 [P] [US1] Integration test: official layout → 40 section pages in A1…H5 order, every stud number equals the layout's lot, counts equal parts list (SC-001, SC-002) in `cli/tests/integration/test_sheets_official.py`
- [ ] T016 [P] [US1] Contract tests `sheets build` (pdf default, -o required, bad layout exit 1, nothing written on error, disclaimer last, print-at-100% line) in `cli/tests/contract/test_sheets_contract.py` (Q8)
- [ ] T017 [US1] Implement `cli/src/lego_image_processor/cli/sheets.py` (`sheets` group, `build`) and register in `cli/main.py`

---

## Phase 4: User Story 2 - Overview and legend (P2)

- [ ] T018 [P] [US2] Unit tests for `overview_page` (map 128 x 80 at 1.4 mm, grid labels, frame lines after columns B and F, totals, provenance for recipe and image layouts, unverified warning) and `legend_pages` (fields equal 005 lots, plate 4073/6141 and tile 98138, pagination beyond one page, Rebrickable acknowledgement) in `cli/tests/unit/sheets/test_compose.py`
- [ ] T019 [US2] Implement `overview_page` and `legend_pages`; full `build_sheet_set` (overview, legend…, sections) in `cli/src/lego_image_processor/sheets/compose.py`
- [ ] T020 [P] [US2] Integration test: recipe fixture layout overview names recipe id, dataset citation and license, layout SHA-256; image fixture layout legend marks uncited lots (before/after 005 US4 via a fixture table) in `cli/tests/integration/test_sheets_layouts.py`

---

## Phase 5: User Story 3 - SVG and counts (P3)

- [ ] T021 [P] [US3] Unit tests for the SVG backend: one file per page `page-NN.svg`, 256 circles per section with fills equal to cited RGB, numbers as text, disclaimer, no `<image>`, byte-identical twice, in `cli/tests/unit/sheets/test_render_svg.py`
- [ ] T022 [US3] Implement `cli/src/lego_image_processor/sheets/render_svg.py` (stdlib, escaped text, 2-decimal numbers)
- [ ] T023 [P] [US3] Contract tests `sheets build --format svg` (directory created) and `sheets counts` (table, json, -o, disclaimer) in `cli/tests/contract/test_sheets_contract.py`
- [ ] T024 [US3] Add `--format svg` and `sheets counts` to `cli/src/lego_image_processor/cli/sheets.py`

---

## Phase 6: User Story 4 - Subsets and paper (P4)

- [ ] T025 [P] [US4] Tests: `--sections B2,C2` → overview + legend + 2 section pages in board order; unknown label exit 1 naming A1–H5; `--paper a4` page size 210 x 297 and pitch 8.0 mm; non-Latin-1 `--title` fails for PDF, works for SVG, in `cli/tests/contract/test_sheets_contract.py`
- [ ] T026 [US4] Implement `--sections`, `--paper`, `--title` in `cli/src/lego_image_processor/cli/sheets.py` and `compose.py`

---

## Phase 7: Polish

- [ ] T027 [P] Performance test: full set < 10 s and PDF < 5 MB for a 10,240-position layout (SC-004) in `cli/tests/integration/test_sheets_official.py`
- [ ] T028 [P] Test that no page in PDF or SVG contains a raster image and every page has the disclaimer (SC-006)
- [ ] T029 [P] Docs: `cli/README.md` "Build sheets" (print at 100%, scale check, section labels, formats, no LEGO artwork); `docs/vision.md` roadmap row 006 to "built" after implement
- [ ] T030 Run quickstart §1–5 with real 004 layouts; record page counts, sizes, timings in run-state.md
- [ ] T031 Full test suite offline (SC-007)

## Dependencies

Setup → Foundational → US1 → US2 → (US3, US4 in either order). Requires 005's `parts` package.

## MVP

Phases 1–3: a 40-section PDF with per-section counts.

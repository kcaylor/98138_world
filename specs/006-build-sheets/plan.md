# Implementation Plan: Build Sheets

**Branch**: `006-build-sheets` | **Date**: 2026-11-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-build-sheets/spec.md` (assumes 005 built as planned)

## Summary

Render any schema 2.0 layout as a printable sheet set: an overview page (whole map, 8 × 5 section
grid A1–H5, frames at columns 32/96, totals, provenance), legend pages (lot number, swatch, LEGO /
BrickLink / Rebrickable names and IDs from 005's resolver), and 40 section pages at true scale
(8.0 mm stud pitch) with numbered colored studs, plates ringed, a locator map, a per-section count
table and a 100 mm scale bar; every page carries the disclaimer. A backend-neutral page model (mm
coordinates; rect, circle, line, text) is rendered to PDF with ReportLab (BSD, invariant mode,
byte-identical) or to SVG with the standard library (Q7). `sheets build` and `sheets counts` (Q8).

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: NEW `reportlab >=4.4,<6` (BSD; pure-Python wheel; needs Pillow ≥ 9 and
charset-normalizer, MIT). Existing Click, Pillow. Standard library `xml.sax.saxutils` for SVG.
Dev: `pypdf >=5` (BSD-3) added to the dev group for PDF tests (already in the maintainer group).

**Storage**: none new (reads layouts and package data; writes PDF/SVG/JSON).

**Testing**: pytest unit (sections, page model, legend, colors), integration (official, recipe
fixture, image fixture, both papers), contract (CLI); offline.

**Target Platform**: macOS/Linux/Windows command line.

**Project Type**: CLI + library (`cli/`).

**Performance Goals**: full set < 10 s, PDF < 5 MB (SC-004; probe: 40 pages 0.26 s, 0.63 MB).

**Constraints**: deterministic bytes; Latin-1 PDF text; no raster images; no LEGO artwork.

**Scale/Scope**: 42–44 pages per set; ≤ ~90 lots.

## Constitution Check

| Principle | Check | Status |
|---|---|---|
| I. Fixed template | Section grid derived from the fixed 128 × 80 kit grid and 003 section data. | PASS |
| II. Recipes | Provenance from `metadata.map` printed on the overview. | PASS |
| III. Data in | Not affected. | PASS |
| IV. Reproducible acquisition | No downloads; dataset citations and licenses on the overview. | PASS |
| V. Buildable and honest | IDs only via 005's resolver; unverified lots labelled; scale stated as an LDraw approximation. | PASS |
| VI. CLI-first | `sheets build|counts` over library functions; SVG + counts JSON for the future web app, which must call these. | PASS |
| VII. Test-first, offline | Page model tested first; PDF/SVG backends tested by parsing. | PASS |
| VIII. LEGO compliance | Disclaimer on every page and output; no LEGO artwork, logo or crops. | PASS |

New dependency ReportLab is permissive (BSD): decide-and-log under run-policy, but the output
format is reserved (Q7). **Post-design re-check**: PASS; Complexity Tracking empty.

## Project Structure

### Documentation

```text
specs/006-build-sheets/
├── plan.md, research.md, data-model.md, quickstart.md, run-state.md, tasks.md
├── contracts/
│   ├── cli.md              # sheets build|counts
│   ├── page-layout.md      # what each page contains, sizes in mm
│   ├── counts-format.md    # sheets counts JSON
│   └── library-api.md
└── checklists/requirements.md
```

### Source Code

```text
cli/
├── pyproject.toml                     # + reportlab; dev + pypdf
├── src/lego_image_processor/
│   ├── sheets/                        # NEW
│   │   ├── __init__.py
│   │   ├── sections.py                # Section(label, col, row, x/y ranges, frame, page); sections()
│   │   ├── legend.py                  # LegendEntry from 005 PartsList; text contrast
│   │   ├── model.py                   # Page, Rect, Circle, Line, Text (mm); PageSize letter/a4
│   │   ├── compose.py                 # overview_page, legend_pages, section_page, build_sheet_set
│   │   ├── counts.py                  # section_counts(layout) -> SectionCounts; to_json
│   │   ├── render_pdf.py              # ReportLab backend (invariant)
│   │   └── render_svg.py              # SVG backend
│   └── cli/sheets.py                  # NEW sheets build|counts; register in cli/main.py
└── tests/
    ├── unit/sheets/                   # sections, legend, model, compose, counts, svg, pdf
    ├── integration/test_sheets_*.py
    └── contract/test_sheets_contract.py
```

**Structure Decision**: `sheets` subpackage beside `parts`; composition is pure (page model) so
both backends and the web app share it.

## Implementation phases

1. Setup: dependency, package, test dirs.
2. Foundational: sections (from 003 data, validated against 128 × 80), page model, legend from
   005 parts list, counts.
3. US1: section page composition, PDF backend, `sheets build` (section pages + minimal cover).
4. US2: overview and legend pages, provenance, unverified warning.
5. US3: SVG backend, `sheets counts`.
6. US4: `--sections`, `--paper a4`.
7. Polish: README, quickstart, determinism and performance checks, disclaimer and no-raster tests.

## Complexity Tracking

No constitution violations.

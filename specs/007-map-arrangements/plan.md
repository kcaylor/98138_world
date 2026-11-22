# Implementation Plan: Map Arrangements

**Branch**: `007-map-arrangements` | **Date**: 2026-11-22 | **Spec**: [spec.md](spec.md)

## Summary

Add the kit's three frame combinations (A 1·2·3, B 3·1·2, C 2·3·1; LEGO 31203 building
instructions, pp. 7–8) as cited package data and an `Arrangement` model (a cyclic column shift by
whole frames). `map build`/`map check` take `--arrangement`: per-cell work (reprojection,
classification, blend) stays in kit coordinates and is rolled to display coordinates; spatial
neighbourhood work (shadow, halo, mix) runs on the grid as hung with no outer wrap. A new
`layout arrange` re-hangs any layout. `validate` checks the mask under the layout's arrangement;
sheets, counts and parts-list provenance follow it.

## Technical Context

**Language/Version**: Python 3.11 (cli/.venv, uv)
**Primary Dependencies**: Click, NumPy, SciPy, Pillow, ReportLab (all existing; no new ones)
**Storage**: package data JSON (`data/kit_31203_arrangements.json`); layout JSON schema 2.0
**Testing**: pytest (unit, integration, contract), offline
**Target Platform**: CLI (macOS/Linux)
**Project Type**: single project (`cli/`)
**Performance Goals**: arrangement adds O(10,240) work; builds stay within existing budgets
**Constraints**: schema 2.0 unchanged; A outputs unchanged except `metadata.arrangement` and mix wrap
**Scale/Scope**: 3 arrangements, 4 commands touched, 1 new command

## Constitution Check

| Principle | Check |
|---|---|
| I. Kit is a fixed template | Pass: grid, mask and parts unchanged; arrangements are cited package data; the mask is only moved by whole frames, as the kit allows |
| II. Recipes | Pass: recipes unchanged; arrangement is a build option recorded in the layout |
| III. Data in | Pass: no change |
| IV. Reproducible data | Pass: no new data downloads; offline |
| V. Buildable and honest | Pass: same pieces; validate gains a mask check; citation for arrangements |
| VI. CLI first | Pass: library functions + CLI |
| VII. Test first, offline | Pass: tests written before code, fixtures only |
| VIII. LEGO compliance | Pass: disclaimer on all new output and data |

No violations; Complexity Tracking empty.

## Project Structure

### Documentation (this feature)

```text
specs/007-map-arrangements/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md, tasks.md, run-state.md
├── contracts/cli.md
└── checklists/requirements.md
```

### Source Code

```text
cli/src/lego_image_processor/
├── data/kit_31203_arrangements.json     # new, cited
├── layout/arrangement.py                # new: Arrangement, load, parse, arrange_grid
├── layout/grid.py                       # arrangement metadata in/out
├── layout/validator.py                  # mask check
├── maps/build.py                        # kit vs display coordinates
├── maps/texture.py                      # mix without wrap
├── sheets/sections.py, compose.py, counts.py
├── parts/partslist.py                   # layout block arrangement
└── cli/map.py, cli/layout.py, cli/validate.py, cli/sheets.py
cli/tests/unit/test_arrangement.py, unit/maps/test_build_arrangement.py,
         unit/sheets/test_arrangement_sheets.py, contract/test_arrange_contract.py,
         integration/test_map_arrangements.py
```

**Structure Decision**: single project, existing layout; the arrangement model lives in `layout/`
because layouts, validation, sheets and maps all use it.

## Complexity Tracking

None.

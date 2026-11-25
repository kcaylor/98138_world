# Implementation Plan: Pacific-centred Arrangements D and E

**Branch**: `010-pacific-arrangements` | **Date**: 2026-11-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/010-pacific-arrangements/spec.md` (source `design.md`)

## Summary

Generalise the arrangement model from "frame order + column shift" to "strip order + frame groups"
(frames may be split into parts 2a/2b), add combinations D (`pacific`, shift 64) and E
(`asia-pacific`, shift 80) to `kit_31203_arrangements.json` (format 2) marked as not in the
building instructions with their own citation (pp. 134–140), and keep A–C byte-identical in
behaviour and layout records. Build sheets get an assembly page (last page) drawn from the data in
the style of p. 139 for every combination; the assembly steps come from one library function used by
the sheets, the runbook examples and the web prebuild. The ENSO recipes default to D. The web site
serves A–E (30 variants) with honest captions, reading all arrangement text from the manifest.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: Click, NumPy, reportlab (sheets), FastAPI + Jinja2 (web); no new dependency
**Storage**: package data JSON (`cli/src/lego_image_processor/data/`), web manifest JSON
**Testing**: pytest (CLI `cli/tests/` unit/integration/contract; web `web/tests/`), offline
**Target Platform**: CLI on macOS/Linux; web on Fly.io (Docker)
**Project Type**: CLI library + web service (two packages)
**Performance Goals**: prebuild 30 variants within the existing image build (~75 s, scaled from 45 s for 18)
**Constraints**: A–C outputs unchanged except additive assembly content; web runtime imports no CLI code
**Scale/Scope**: 5 arrangements, 1 new sheet page kind, 2 recipe defaults, 6 maps × 5 web variants

## Constitution Check

| Principle | Check | Status |
|---|---|---|
| I. Kit is a fixed template | Grid, mask and part types unchanged; D/E are whole-strip rotations of the same board. Arrangement data is versioned package data citing its source (pp. 7–8; pp. 134–140 for D/E). | PASS |
| II. Maps are recipes | ENSO default set by the recipe key `arrangement`; official recipe unchanged. | PASS |
| III. Data in | Unchanged (rolling happens after per-cell work, as in 007). | PASS |
| IV. Reproducible data | No new dataset; real-data check uses the pinned ERSST cache. | PASS |
| V. Buildable and honest | D/E use only the kit's pieces (peg budget 201 of 205, the 205 read from `kit_31203_inventory.json` p. 159); D/E labelled "not among the building instructions' combinations" everywhere. | PASS |
| VI. CLI-first | D/E work in every CLI command before the web uses them; the web reads arrangement text from the manifest written by the prebuild via the library. | PASS |
| VII. Test-first, offline | Tests written first for data, model, CLI, sheets, recipes, web; all offline. | PASS |
| VIII. LEGO compliance | Assembly page carries the footer disclaimer; drawn from data only, no artwork; web pages keep the disclaimer. | PASS |

No violations; Complexity Tracking empty.

## Project Structure

### Documentation (this feature)

```text
specs/010-pacific-arrangements/
├── design.md        # source (owner decisions)
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/cli.md
├── checklists/requirements.md
├── tasks.md
└── run-state.md
```

### Source Code (repository root)

```text
cli/src/lego_image_processor/
├── data/kit_31203_arrangements.json   # format 2: strips, groups, in_instructions, D, E, joints source, assembly facts
├── layout/arrangement.py              # strip/group model, joints, assembly_steps(), record()
├── cli/options.py, cli/layout.py      # help/metavar A-E; group labels in arrange output
├── sheets/compose.py                  # assembly_page(); overview/section text for groups
├── cli/sheets.py                      # "1 assembly" in the page-kind line
└── maps/recipes/ocean-el-nino.toml, ocean-la-nina.toml  # arrangement = "D"
cli/tests/unit/test_arrangement.py, unit/sheets/test_assembly_page.py, contract/test_arrange_contract.py, ...
web/src/web98138/__init__.py (COMBINATIONS), prebuild.py (manifest rows), templates/about.html, map.html
web/tests/test_prebuild.py, test_routes.py, test_catalog.py
docs/runbook.md, docs/deploy.md, Dockerfile (comment), cli/README.md, AGENTS.md, CLAUDE.md, specs/009 notes
```

**Structure Decision**: existing two-package layout (`cli/`, `web/`); no new modules except a test
file for the assembly page.

## Complexity Tracking

(none)

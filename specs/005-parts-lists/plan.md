# Implementation Plan: Parts Lists and Ordering

**Branch**: `005-parts-lists` | **Date**: 2026-11-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-parts-lists/spec.md`

## Summary

Turn any schema 2.0 layout into a parts list of lots (part × color) resolved against the cited
color tables and a new cited marketplace part-number file (`part_numbers.json`: plate = BrickLink
4073 / Rebrickable 6141 / LEGO 6141; tile = 98138 on both marketplaces / LEGO 35381), with needed,
owned, shortfall, spares and to-buy quantities. Owned parts come from `--kits N` (cited kit supply)
plus Rebrickable-format CSV files of loose and missing parts (Q1). Exports: BrickLink wanted-list
XML (no declaration, `ITEMTYPE`/`ITEMID`/`COLOR`/`MINQTY`, optional `CONDITION`) and Rebrickable
`Part,Color,Quantity` CSV, verified lots only (Q2). A maintainer tool builds `part_numbers.json`
from pinned archived catalog pages; the 004 part-color tool gains join rule 5 and (US4, Q3) covers
every opaque color of both parts (44 plate, 40 tile). Rebrickable's confirmed terms replace the
open license note. No new dependencies; no network at run time.

## Technical Context

**Language/Version**: Python 3.11+ (constitution)

**Primary Dependencies**: existing Click, NumPy (not needed here), standard library `csv`,
`xml.sax.saxutils`, `hashlib`, `html.parser`, `math`. No new third-party packages.

**Storage**: package data `cli/src/lego_image_processor/data/part_numbers.json` (new) and
`part_colors.json` (regenerated); maintainer source cache `<cache>/sources/partnumbers/` (never
committed).

**Testing**: pytest unit, integration, contract; offline guard already in `cli/tests/conftest.py`;
fixtures are small synthetic layouts and owned CSVs, plus a trimmed synthetic HTML snippet for the
maintainer parser (not the archived page).

**Target Platform**: macOS/Linux/Windows command line, offline.

**Project Type**: CLI + library (single project `cli/`).

**Performance Goals**: list and export under 2 s for 10,240 positions (SC-006; expected < 0.3 s,
dominated by JSON load).

**Constraints**: deterministic bytes; no prices; no network; IDs only from cited files.

**Scale/Scope**: ≤ 85 cited rows; a layout has ≤ ~60 lots.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Fixed template | Reads layouts on the kit grid; kit supply from the cited inventory; nothing changes the template. | PASS |
| II. Recipes | Carries `metadata.map` provenance into the parts list; recipe builds and the official recipe are first-class inputs. | PASS |
| III. Data in | Not affected (works on any layout). | PASS |
| IV. Reproducible acquisition | Maintainer sources pinned by URL + SHA-256 + access date; run time is offline; Rebrickable acknowledged per its terms. | PASS |
| V. Buildable and honest | Marketplace IDs only from cited files; unverified lots never get IDs; no spare rate or price invented; exports exclude unverified lots. | PASS |
| VI. CLI-first | `parts list|export`, `kit part-numbers` over library functions in `lego_image_processor.parts`. | PASS |
| VII. Test-first, offline | Unit tests first for resolution, arithmetic, owned parsing, exporters; contract tests for CLI; no network. | PASS |
| VIII. LEGO compliance | Disclaimer on human output and JSON; marketplace import files carry none (Q4, reserved, following the user's 003 CSV decision). | PASS (pending Q4) |

**Post-design re-check**: PASS. Complexity Tracking empty.

## Reserved decisions (provisional; see spec Clarifications and run-state.md)

Q1 owned-parts input; Q2 unverified lots in exports; Q3 widen color tables; Q4 no disclaimer in
marketplace files; Q5 CLI surface (`parts list|export`, `kit part-numbers`, flags); Q6 map pieces
only. Each has a recommended answer applied provisionally in the design below.

## Project Structure

### Documentation (this feature)

```text
specs/005-parts-lists/
├── plan.md
├── research.md            # R1–R10 with pinned sources
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md             # parts list|export, kit part-numbers
│   ├── parts-list-format.md   # parts list JSON
│   ├── export-formats.md  # BrickLink XML, Rebrickable CSV, owned/missing CSV input
│   ├── data-files.md      # part_numbers.json, part_colors.json changes
│   └── library-api.md
├── checklists/requirements.md
├── run-state.md
└── tasks.md
```

### Source Code (repository root)

```text
cli/
├── src/lego_image_processor/
│   ├── data/
│   │   ├── part_numbers.json             # NEW cited marketplace part numbers (R1)
│   │   └── part_colors.json              # REGENERATED: rule 5, license terms (R5); US4 wider
│   ├── kit/part_numbers.py               # NEW load_part_numbers() -> PartNumberTable
│   ├── parts/                            # NEW
│   │   ├── __init__.py
│   │   ├── resolve.py                    # resolve_lot(part_id, color_key, lego_code) -> ResolvedColor | reason
│   │   ├── owned.py                      # parse_owned_csv(), kit_supply(kits, missing)
│   │   ├── partslist.py                  # build_parts_list(layout, ...) -> PartsList; to_json()
│   │   └── export.py                     # to_bricklink_xml(), to_rebrickable_csv()
│   └── cli/
│       ├── parts.py                      # NEW parts list|export
│       ├── kit.py                        # + part-numbers
│       └── main.py                       # register `parts`
├── tools/
│   ├── partnumbers/                      # NEW maintainer tool: build/--check part_numbers.json
│   └── partcolors/build.py               # + rule 5 (BrickLink part page colors), terms; US4 all colors
└── tests/
    ├── unit/parts/                       # NEW resolve, owned, partslist, export
    ├── unit/tools/test_partnumbers.py    # parser on a synthetic snippet
    ├── integration/test_parts_*.py       # official, recipe fixture, image fixture, top-up
    ├── contract/test_parts_contract.py
    └── fixtures/parts/                   # NEW tiny layouts, owned/missing CSVs, expected XML/CSV
```

**Structure Decision**: a `parts` subpackage beside `maps` and `datasets`, so the later web app and
feature 006 (build-sheet legend) reuse `resolve` and `build_parts_list`.

## Design notes

- **Resolution order** (FR-005): `part_id` → `PartColorTable.get(part_id, color_key)` (kit rows
  come from `kit_colors.json` through it); verified iff found and `lego.id == int(lego_color_code)`;
  part numbers from `PartNumberTable`. Reasons: `no cited color for part`, `color code mismatch`.
- **Kit supply**: `KitInventory.supplied(color_key)` restricted to the element whose role matches
  the lot's part (land → 6141 element, ocean → tile elements); 0 otherwise. `--missing` subtracts
  per lot, floor 0, before adding `--owned`.
- **Arithmetic** (FR-006/008): shortfall = max(0, needed − owned); spares = ceil(shortfall × p /
  100) if shortfall else 0 (integer arithmetic: `(shortfall * p_num + den - 1) // den` with p as a
  `Fraction` to avoid float rounding); to_buy = shortfall + spares; surplus = max(0, owned − needed).
- **Order**: plate before tile; then LEGO color ID; unverified lots last by color key.
- **Exit codes** (extending 004): 0 ok; 1 input error (layout, owned file); 2 Click usage;
  6 unverified lots in an export without `--allow-partial`.
- **Maintainer tool `partnumbers`**: `PYTHONPATH=tools python -m partnumbers build [--check]
  [--source-dir DIR]`; downloads the four pinned archived pages (R1) to the source cache if absent,
  verifies SHA-256, extracts item number, alternates and color list with `html.parser`, writes
  `part_numbers.json`. The part-color tool reads the color lists from the same cache for rule 5.

## Implementation phases (for /speckit-tasks)

1. **Setup**: package and test dirs.
2. **Foundational**: `part_numbers.json` + loader + maintainer tool; rule 5 and license terms in
   the part-color tool and regenerated `part_colors.json` (existing rows unchanged); layout read
   helper with SHA-256.
3. **US1 (P1)**: resolve, lots, `build_parts_list` (needed only), JSON and table output,
   `parts list`, `kit part-numbers`.
4. **US2 (P2)**: exporters, `parts export`, partial/allow-partial, nothing-to-buy.
5. **US3 (P3)**: owned/missing parsing, kit supply, spares; options on both commands.
6. **US4 (P4)**: all-colors build of `part_colors.json`, image fixture fully verified.
7. **Polish**: README, quickstart run, disclaimer tests, performance check, close 004 license
   question in docs.

## Complexity Tracking

No constitution violations.

# Implementation Plan: Kit Reference Data for LEGO World Map 31203

**Branch**: `003-kit-reference-data` | **Date**: 2026-11-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-kit-reference-data/spec.md`

## Summary

Replace the unverified kit data with reference data extracted from the pinned 31203 instructions
PDF and cited catalog sources: a 32-line kit inventory (page 159), a curated 10-color table with
LEGO, BrickLink and Rebrickable IDs, and the official design as a 128×80 grid of named kit colors
assembled from the 40 section images. The land/sea mask is regenerated from the design (research
shows it matches the shipped mask exactly). Land becomes part 6141 / "plate" and the layout format
moves to schema 2.0, rejecting 1.0 files. `validate` and `layout` read the new data, and the
validator's nearest-color suggestion switches to CIEDE2000.

The extraction is a maintainer tool in `cli/tools/kit31203/` using pypdf (BSD-3, optional
`maintainer` Poetry group). Section positions come from where each section image is drawn on the
page's locator, cross-checked against build order (research R5). Stud colors are sampled at cell
centers and classified against fixed reference render colors by CIEDE2000, with ambiguous
positions resolved in a committed overrides file (R6).

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Click, Pillow, NumPy (runtime, existing); pypdf ≥ 5 (maintainer group
only, BSD-3-Clause); standard library `urllib`, `hashlib`, `json` for download and checksums.

**Storage**: JSON files shipped as package data in `cli/src/lego_image_processor/data/`; PDF cached
under a per-user cache directory, never committed.

**Testing**: pytest (unit, integration, contract), offline; extractor tests on committed factual
fixtures and synthetic images (R10); pypdf-dependent tests skip when the maintainer group is not
installed.

**Target Platform**: macOS/Linux CLI (library usable by the future web app).

**Project Type**: CLI + library (single Python package) plus a maintainer tool.

**Performance Goals**: Loading inventory/colors/design < 100 ms; full extraction from a cached PDF
< 60 s on a laptop (not a hard gate).

**Constraints**: No network or API keys at run time (FR-007); deterministic regeneration
(SC-008); no LEGO artwork committed (R10).

**Scale/Scope**: 32 inventory lines, 10 colors, 10,240 positions, 40 sections.

No NEEDS CLARIFICATION remain; all were resolved in [research.md](research.md).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Kit is a fixed template | Grid, mask and one part per class unchanged in shape; land part corrected to 6141 (a correction of the template's data, not a variation per map). Mask, part IDs and inventory stored as versioned package data with a `source` block (URL, checksum, pages, date). | PASS |
| II. Maps are layers / recipes | The design grid is the target 004 must reproduce; no recipe work here. | PASS (n/a) |
| III. Data in, not pictures | Extraction reads images of the official build once, offline, to produce reference data; it is not a map input path. | PASS |
| IV. Reproducible acquisition | PDF pinned by URL + SHA-256, cached, verified before use; package works offline; no credentials. | PASS |
| V. Buildable and honest outputs | Every quantity and ID cited (PDF page, Brickset, LDraw, BrickLink, Rebrickable); invented quantities and 25-color lists removed; validator checks per-part colors and quantities. Two frame elements' part metadata flagged `verified: false` (no map role). | PASS |
| VI. CLI-first | New library API (`lego_image_processor.kit`) exposed through a `kit` CLI group; extractor is a maintainer tool, not user-facing (FR-004). | PASS (new CLI group: see E1) |
| VII. Test-first, offline | Tests written first for inventory pairing, section mapping, classification, loaders, validator, schema rejection; all offline. | PASS |
| VIII. LEGO compliance | Disclaimer in `layout`, `validate`, `kit` output, layout JSON metadata and every data file's `source.disclaimer`. | PASS |

**Post-design re-check**: PASS. No violations; Complexity Tracking is empty.

## ESCALATE (decisions reserved for the user by run-policy)

**Resolved 2026-11-21**: E1 yes, add `kit inventory` and `kit colors` (user). E2 keep 6141/98138 in
layouts and record alternates in the inventory (user). E3 synthetic fixtures (agent). E4 rename
(agent, within the approved 2.0 format change).

- **E1. New CLI command group `kit`** (public CLI change). Principle VI requires the inventory to
  be reachable from the CLI, and acceptance scenario US1-1 says "a user or library call requests
  the inventory". Recommended: add `lego-image-processor kit inventory` and `kit colors`
  (`--format table|json`), read-only. Alternative: library-only access now, CLI in 005.
- **E2. Part numbering in layout files.** Land will be `6141` (LEGO design ID, per the user's
  decision) while ocean stays `98138` (BrickLink/Rebrickable number; LEGO's design ID is 35381).
  The two use different numbering schemes. Recommended: keep `6141`/`98138` in layouts as decided,
  and record `design_id` plus all alternate numbers (`6141`/`4073`, `98138`/`35381`) in the
  inventory so 005 can pick per catalog. Alternative: use one scheme for both (e.g. `4073`/`98138`
  BrickLink, or `6141`/`35381` LEGO).
- **E3. Test fixtures.** Research recommends committing no crops of LEGO's instruction images and
  testing with synthetic section images plus a factual word list (R10), which is stricter than the
  spec's example. Recommended: approve synthetic fixtures. Alternative: commit 2–3 real 154×154
  JPEG crops (~30 KB each) as the spec's example allows.
- **E4. Layout statistics key rename** (`land_brick_count` → `land_plate_count`,
  `color_frequency_by_part_type.brick` → `.plate`) inside the already-approved 2.0 format change.
  Recommended: approve as part of the 2.0 bump (no compatibility shim).

None of these blocks planning; tasks can be generated with the recommended answers.

## Project Structure

### Documentation (this feature)

```text
specs/003-kit-reference-data/
├── plan.md               # This file
├── research.md           # Phase 0
├── data-model.md         # Phase 1
├── quickstart.md         # Phase 1
├── contracts/
│   ├── data-files.md          # JSON shapes of the shipped reference files
│   ├── library-api.md         # Python API (lego_image_processor.kit, layout changes)
│   ├── cli.md                 # kit / layout / validate CLI contract changes
│   └── maintainer-tool.md     # cli/tools/kit31203 command contract
├── projection-notes.md   # written during implementation (FR-017)
├── checklists/requirements.md
└── tasks.md              # /speckit-tasks (not created here)
```

### Source Code (repository root)

```text
cli/
├── pyproject.toml                         # + [tool.poetry.group.maintainer] pypdf (optional);
│                                          #   pytest pythonpath += ["tools"]
├── src/lego_image_processor/
│   ├── data/
│   │   ├── kit_colors.json                # NEW curated, cited 10-color table
│   │   ├── kit_31203_inventory.json       # NEW generated (page 159 + part catalog)
│   │   ├── kit_31203_design.json          # NEW generated 128×80 named-color grid + sections
│   │   ├── kit_31203_mask_changes.json    # NEW generated change record (empty today)
│   │   ├── lego_world_map_land_sea_mask.json  # regenerated, + source block
│   │   └── lego_world_map_kit.json        # REMOVED
│   ├── kit/                               # NEW library module
│   │   ├── __init__.py
│   │   ├── colors.py                      # KitColor, load_kit_colors()
│   │   ├── inventory.py                   # KitElement, KitInventory, load_kit_inventory()
│   │   ├── design.py                      # DesignGrid, Section, load_official_design()
│   │   └── source.py                      # SourceDocument (shared provenance block)
│   ├── layout/
│   │   ├── kit_spec.py                    # rebuilt from inventory + colors (plate/tile)
│   │   ├── position.py                    # plate/6141, tile/98138
│   │   ├── grid.py                        # schema 2.0, LayoutSchemaError, plate stats
│   │   ├── generator.py                   # plate/6141 labels
│   │   ├── land_sea_mask.py               # plate; reads source block
│   │   └── validator.py                   # CIEDE2000 suggestion, plate/tile, disclaimer
│   ├── palette/lego_colors.json           # + Bright Bluish Green (107)
│   └── cli/
│       ├── kit.py                         # NEW `kit inventory`, `kit colors` (E1)
│       ├── layout.py, validate.py         # wording, disclaimer, schema error
│       └── main.py                        # register `kit`
├── tools/kit31203/                        # NEW maintainer tool (not packaged)
│   ├── __main__.py                        # `python -m kit31203 extract [--check]`
│   ├── source.py                          # download, cache, checksum
│   ├── pdf_adapter.py                     # pypdf: words, image placements, image bytes
│   ├── inventory.py                       # pair counts ↔ element IDs (pure)
│   ├── sections.py                        # find 40 sections, (col,row) from placement (pure)
│   ├── classify.py                        # cell sampling, CIEDE2000, ambiguity (pure)
│   ├── assemble.py                        # grid, mask, change record, counts, writers
│   ├── part_catalog.json                  # curated part IDs/descriptions (Brickset, cited)
│   ├── reference_colors.json              # reference render RGB per kit color
│   └── overrides.json                     # manual decisions for ambiguous positions
└── tests/
    ├── fixtures/kit31203/                 # page159_words.json, placements.json
    ├── fixtures/lego_world_map_colormap.json  # relabeled with kit color keys (FR-011)
    ├── fixtures/layouts/expected_test_128x80.{json,csv}  # regenerated as 2.0
    ├── unit/test_kit_colors.py, test_kit_inventory.py, test_official_design.py
    ├── unit/tools/test_inventory_pairing.py, test_section_mapping.py, test_classify.py,
    │   test_source_cache.py
    ├── integration/test_reference_consistency.py   # FR-023 cross-file checks
    └── contract/test_kit_contract.py; layout/validate contract tests updated
```

**Structure Decision**: Single package (`cli/`). Runtime reference data and its loaders live in
the package (`data/`, new `kit/` module); the PDF tooling lives in `cli/tools/kit31203/`, outside
`src/`, so it is never shipped and its pypdf import never reaches users.

## Implementation phases (for /speckit-tasks)

1. **US1 (P1)**: color table + palette entry 107; part catalog; inventory extractor pairing (pure,
   tested on the word list); `kit` module loaders; kit_spec rebuild; 3062b/brick → 6141/plate
   across code, tests, README, fixtures; schema 2.0 with rejection; remove old kit JSON; `kit` CLI.
2. **US2 (P2)**: source cache/checksum; pypdf adapter; section finding and (col,row) mapping;
   classification with reference colors and overrides; assembly of design, mask, change record and
   counts; `--check`; run on the real PDF and commit outputs; projection notes.
3. **US3 (P3)**: validator on new data (CIEDE2000 suggestion restricted to the part's kit colors,
   shortfall reporting); generator labels; disclaimer everywhere; official-design-as-layout
   integration test (SC-005).

## Complexity Tracking

No constitution violations to justify.

Not affiliated with or endorsed by The LEGO Group.

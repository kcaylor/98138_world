# Implementation Plan: LEGO Map Layout Generation

**Branch**: `002-lego-map-layout` | **Date**: 2026-01-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-lego-map-layout/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Transform color-quantized satellite images (from spec 001) into buildable LEGO World Map position placement layouts matching the official LEGO World Map kit 31203 structure. This feature is the "projection software" layer - taking ANY global geographic dataset and mapping it onto the standardized LEGO kit format (128×80 grid = 10,240 positions: 3,062 land bricks + 7,178 ocean tiles). The tool generates machine-readable JSON/CSV layouts showing exactly which LEGO part (brick or tile) and color goes at each position, maintaining exact fidelity to the official kit's land/sea pattern while supporting infinite data visualizations (temperature, NPP, ocean currents, population, etc.).

## Technical Context

**Language/Version**: Python 3.11+ (per constitution requirement for CLI tools)
**Primary Dependencies**: Pillow (image I/O), NumPy (array operations), Click (CLI framework), json (output serialization)
**Storage**: Local filesystem only (input: quantized images; output: JSON/CSV position layouts; reference: LEGO kit config + land/sea mask JSON)
**Testing**: pytest (contract tests for CLI, integration tests for workflow, unit tests for grid logic)
**Target Platform**: CLI tool - cross-platform (Windows, macOS, Linux)
**Project Type**: Single CLI package (extends existing cli/ directory from spec 001)
**Performance Goals**:
  - Process 128×80 image (10,240 pixels) → position layout in <5 seconds
  - Linear time complexity: O(n) where n = pixel count
  - Memory: <100MB for standard map processing
**Constraints**:
  - Offline-capable (no internet required)
  - Exact 1:1 pixel-to-position mapping (no interpolation)
  - Top-left origin (0,0) coordinate system
  - Must use official land/sea mask (cli/tests/fixtures/lego_world_map_land_sea_mask.json)
  - Two part types: round bricks (3062b) for land, flat tiles (98138) for ocean
**Scale/Scope**:
  - Standard map: 128×80 = 10,240 positions (3,062 land + 7,178 ocean)
  - 3 user stories (P1: basic layout, P2: color validation, P3: shadowing - future)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. CLI-First Architecture ✅ PASS

- **Requirement**: All features MUST work as standalone CLI commands before web integration
- **Compliance**: This feature IS the CLI tool. Generates position layouts via command-line interface with JSON/CSV output. Web backend will consume these outputs but does not duplicate logic.
- **Evidence**: User stories describe CLI commands (`lego-image-processor layout ...`), outputs to stdout/files, no web dependencies

### II. Modular & Open Source Ready ✅ PASS

- **Requirement**: CLI tools designed for open-source release, no hardcoded credentials
- **Compliance**: Pure local file processing (quantized images → position layouts). No API calls, no credentials, no proprietary endpoints. Works entirely offline with local reference data (LEGO kit config + land/sea mask JSON).
- **Evidence**: FR-010 requires offline operation, FR-011 uses local configuration files

### III. Incremental Delivery ✅ PASS

- **Requirement**: P1 must be complete MVP, each story independently testable/deployable
- **Compliance**:
  - **P1 (Basic Position Placement)**: Complete translation layer - quantized image → buildable position layout with land/sea classification. Fully usable MVP.
  - **P2 (Color Validation)**: Independent enhancement - validates against kit inventory. P1 remains functional without it.
  - **P3 (Shadowing)**: Optional aesthetic - requires research into official kit patterns. P1+P2 deliver full value without it.
- **Evidence**: Spec explicitly states "Can be fully tested by..." for each story with independent acceptance criteria

### IV. Test-First Development ✅ PASS

- **Requirement**: Tests written before implementation, tests must fail first
- **Compliance**: pytest framework specified, contract/integration/unit test structure defined
- **Plan**: Phase 2 (tasks.md generation via `/speckit.tasks`) will follow TDD workflow: write tests → verify failure → implement → verify pass
- **Evidence**: Technical Context specifies pytest, spec includes test data requirements (quantized test images, land/sea mask fixture)

### V. Performance & Scale Targets ✅ PASS

- **Requirement**: CLI must process 1024×1024 image → LEGO map in <30 seconds
- **Compliance**:
  - Target: 128×80 (10,240 pixels) in <5 seconds (well under 30s requirement)
  - Linear time complexity: O(n) where n = pixel count
  - Standard map processing well within performance bounds
- **Evidence**: SC-001 requires <5s for standard map, SC-003 requires linear time

### VI. Deployment & Infrastructure ✅ PASS

- **Requirement**: Containerized backend, static frontend, Fly.io deployment
- **Compliance**: CLI tool doesn't require deployment infrastructure - runs locally. When integrated into web backend later, the CLI will be called as subprocess/library within Fly.io containerized backend.
- **Evidence**: This is CLI-only feature. Web integration is future work outside this spec's scope.

### VII. Data & Privacy ✅ PASS

- **Requirement**: User data ownership, clear LEGO disclaimer
- **Compliance**: CLI processes local files only - no user data collection or storage. When integrated into web, user-uploaded images and generated layouts will follow privacy principles.
- **LEGO Compliance**: Spec explicitly requires LEGO disclaimer in documentation and acknowledges this as homage to official kit 31203.
- **Evidence**: FR-010 (offline operation), Project Vision section documents homage philosophy and non-affiliation

### Summary: All Constitution Gates PASSED ✅

No violations detected. This feature fully aligns with all seven constitutional principles. Proceeding to Phase 0 research.

## Project Structure

### Documentation (this feature)

```text
specs/002-lego-map-layout/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── layout.json      # Position layout output schema (JSON format)
│   └── layout.csv       # Position layout output schema (CSV format)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
cli/
├── src/
│   └── lego_image_processor/
│       ├── __init__.py
│       ├── __main__.py
│       ├── palette/                    # From spec 001 (existing)
│       │   ├── __init__.py
│       │   ├── lego_colors.json
│       │   ├── loader.py
│       │   └── converter.py
│       ├── core/                       # From spec 001 (existing)
│       │   ├── __init__.py
│       │   ├── image_loader.py
│       │   ├── image_writer.py
│       │   └── color_quantizer.py
│       ├── layout/                     # NEW - This feature (002)
│       │   ├── __init__.py
│       │   ├── grid.py                 # PositionPlacementGrid class
│       │   ├── position.py             # PositionPlacement class
│       │   ├── generator.py            # Layout generation logic
│       │   ├── validator.py            # Kit color validation logic
│       │   ├── kit_spec.py             # LEGO kit configuration loader
│       │   └── land_sea_mask.py        # Land/sea mask loader and utilities
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── quantize.py             # From spec 001 (existing)
│       │   ├── layout.py               # NEW - Layout generation command
│       │   └── validate.py             # NEW - Kit validation command
│       └── data/                       # Reference data
│           ├── lego_world_map_kit.json # Kit specs (dimensions, colors, quantities)
│           └── (mask file lives in tests/fixtures/)
├── tests/
│   ├── contract/
│   │   ├── test_layout_contract.py     # NEW - Layout command I/O validation
│   │   └── test_validate_contract.py   # NEW - Validate command I/O validation
│   ├── integration/
│   │   └── test_layout_pipeline.py     # NEW - Quantized image → position layout workflow
│   ├── unit/
│   │   ├── test_grid.py                # NEW - Grid manipulation tests
│   │   ├── test_position.py            # NEW - Position placement tests
│   │   ├── test_generator.py           # NEW - Layout generation logic tests
│   │   ├── test_validator.py           # NEW - Validation logic tests
│   │   ├── test_kit_spec.py            # NEW - Kit configuration loading tests
│   │   └── test_land_sea_mask.py       # NEW - Land/sea mask loading tests
│   └── fixtures/
│       ├── images/                      # From spec 001 (existing test images)
│       ├── lego_world_map_land_sea_mask.json  # EXISTING - Extracted from official instructions
│       ├── lego_world_map_colormap.json       # EXISTING - Complete color reference
│       └── layouts/                     # NEW - Expected layout outputs for regression testing
└── pyproject.toml
```

**Structure Decision**: Single CLI project extending existing `cli/` directory from spec 001. New code lives in `cli/src/lego_image_processor/layout/` module with corresponding CLI commands in `cli/src/lego_image_processor/cli/`. This maintains the CLI-first, modular architecture established in spec 001 while adding position layout generation capabilities. The land/sea mask fixture already exists at `cli/tests/fixtures/lego_world_map_land_sea_mask.json` (extracted during spec correction phase).

## Complexity Tracking

No constitution violations detected. This section is empty.

# Implementation Tasks: LEGO Map Layout Generation

**Feature**: 002-lego-map-layout
**Branch**: `002-lego-map-layout`
**Date**: 2026-01-07
**Status**: Ready for Implementation

## Overview

This task breakdown implements LEGO World Map position layout generation, transforming color-quantized images into buildable layouts matching official kit 31203 structure (128×80 grid, 10,240 positions: 3,062 land bricks + 7,178 ocean tiles).

**Implementation Strategy**: Test-Driven Development (TDD)
- Write tests first → Verify failure → Implement → Verify pass
- Contract tests for CLI commands (I/O validation)
- Integration tests for workflows (quantized image → layout)
- Unit tests for core logic (grid manipulation, validation)

**Task Organization**:
- Tasks grouped by user story (P1, P2, P3)
- Tasks use strict checklist format: `[ ]` = pending, `[X]` = completed
- Dependencies marked explicitly
- Parallel-executable tasks marked with `[P]` flag

---

## User Story 1 (P1): Basic Position Placement Layout Generation

**Goal**: Convert color-quantized images into buildable LEGO World Map layouts with land/sea classification, part types, and position coordinates.

### Phase 1.1: Core Data Structures

**Dependencies**: None (foundational work)

- [ ] **Task 1.1.1**: Create `PositionPlacement` class
  - File: `cli/src/lego_image_processor/layout/position.py`
  - Attributes: x, y, color_id, color_name, lego_color_code, part_type, lego_part_id
  - Validation: x ≥ 0, y ≥ 0, part_type ∈ {"brick", "tile"}, lego_part_id ∈ {"3062b", "98138"}
  - Invariant: part_type="brick" ↔ lego_part_id="3062b", part_type="tile" ↔ lego_part_id="98138"
  - Methods: `__repr__()`, `to_dict()`, `from_dict()`
  - **TDD**: Write unit test first (`tests/unit/test_position.py`)

- [ ] **Task 1.1.2**: Create `PositionPlacementGrid` class
  - File: `cli/src/lego_image_processor/layout/grid.py`
  - Attributes: width, height, total_positions, land_positions, ocean_positions, unique_colors, coordinate_system, generated_at, source_image, schema_version, positions (List[PositionPlacement])
  - Validation: total_positions = width × height, land_positions + ocean_positions = total_positions
  - Methods: `add_position()`, `get_position(x, y)`, `to_json()`, `to_csv()`, `from_json()`, `compute_statistics()`
  - **TDD**: Write unit test first (`tests/unit/test_grid.py`)

- [ ] **Task 1.1.3**: Create `LayoutStatistics` class
  - File: `cli/src/lego_image_processor/layout/grid.py` (same module as PositionPlacementGrid)
  - Attributes: total_tile_count, land_brick_count, ocean_tile_count, unique_colors, color_frequency, color_frequency_by_part_type, most_common_color, coverage_percentage
  - Computed from: PositionPlacementGrid.positions
  - Methods: `to_dict()`
  - **TDD**: Write unit test first (`tests/unit/test_grid.py`)

### Phase 1.2: Land/Sea Mask Loading

**Dependencies**: None (reads existing fixture file)

- [ ] **Task 1.2.1**: Create `LandSeaMask` class
  - File: `cli/src/lego_image_processor/layout/land_sea_mask.py`
  - Attributes: width, height, total_positions, land_count, ocean_count, land_percentage, ocean_percentage, mask_2d (80×128 boolean array), source, extracted_date
  - Load from: `cli/tests/fixtures/lego_world_map_land_sea_mask.json`
  - Methods: `is_land(x, y)`, `get_part_type(x, y)` → "brick" or "tile", `get_lego_part_id(x, y)` → "3062b" or "98138"
  - Caching: Use `@lru_cache` to avoid reloading fixture
  - **TDD**: Write unit test first (`tests/unit/test_land_sea_mask.py`)

- [ ] **Task 1.2.2**: Create `load_land_sea_mask()` function
  - File: `cli/src/lego_image_processor/layout/land_sea_mask.py`
  - Returns: LandSeaMask instance
  - Validates: Dimensions (128×80), land count (3,062), ocean count (7,178)
  - Error handling: FileNotFoundError, JSON parse errors, invalid mask structure
  - **TDD**: Write unit test first (`tests/unit/test_land_sea_mask.py`)

### Phase 1.3: Layout Generation Logic

**Dependencies**: Tasks 1.1.1, 1.1.2, 1.2.1, 1.2.2

- [ ] **Task 1.3.1**: Create `LayoutGenerator` class
  - File: `cli/src/lego_image_processor/layout/generator.py`
  - Constructor: `__init__(palette: dict, land_sea_mask: LandSeaMask)`
  - Method: `generate(image: Image, source_filename: str) -> PositionPlacementGrid`
  - Algorithm:
    1. Validate image dimensions (128×80)
    2. Validate all pixels are LEGO colors from palette
    3. For each pixel (x, y):
       - Read pixel color → lookup in palette → get color_id, color_name, lego_color_code
       - Query land_sea_mask.is_land(x, y) → boolean
       - Determine part_type: "brick" if land else "tile"
       - Determine lego_part_id: "3062b" if land else "98138"
       - Create PositionPlacement(x, y, color_id, color_name, lego_color_code, part_type, lego_part_id)
    4. Create PositionPlacementGrid with all positions
    5. Compute statistics
  - Error handling: Invalid dimensions, invalid colors, mask mismatch
  - **TDD**: Write unit test first (`tests/unit/test_generator.py`)

- [ ] **Task 1.3.2**: Add dimension validation to `LayoutGenerator`
  - Method: `_validate_dimensions(image: Image)`
  - Check: width = 128, height = 80
  - Raises: `ValueError` with clear error message and resize suggestions
  - **TDD**: Write unit test for dimension mismatch cases

- [ ] **Task 1.3.3**: Add color validation to `LayoutGenerator`
  - Method: `_validate_colors(image: Image, palette: dict)`
  - Check: All pixel RGB values exist in LEGO palette
  - Raises: `ValueError` with invalid color RGB, pixel coordinates (x, y)
  - **TDD**: Write unit test for invalid color cases

### Phase 1.4: CLI Command Implementation

**Dependencies**: Tasks 1.3.1, 1.3.2, 1.3.3

- [ ] **Task 1.4.1**: Create `layout` CLI command
  - File: `cli/src/lego_image_processor/cli/layout.py`
  - Command: `lego-image-processor layout <input_image> [options]`
  - Arguments:
    - `input_image` (required): Path to quantized image
    - `--output` / `-o` (required): Output file path
    - `--format` / `-f` (optional): Output format ("json" or "csv", default: "json")
    - `--quiet` / `-q` (optional): Suppress progress output
  - Workflow:
    1. Load palette (from spec 001)
    2. Load land/sea mask
    3. Load input image
    4. Generate layout using LayoutGenerator
    5. Write output (JSON or CSV)
    6. Print summary stats (unless --quiet)
  - Error handling: File not found, invalid format, generation failures
  - **TDD**: Write contract test first (`tests/contract/test_layout_contract.py`)

- [ ] **Task 1.4.2**: Register `layout` command in CLI entry point
  - File: `cli/src/lego_image_processor/cli/__init__.py`
  - Add: Import and register layout command with Click group
  - Verify: `lego-image-processor --help` shows layout command

- [ ] **Task 1.4.3**: Add progress feedback for large layouts
  - File: `cli/src/lego_image_processor/layout/generator.py`
  - Method: `_show_progress(current, total)` using Click progress bar
  - Trigger: When total_positions > 1000
  - Suppressible: Via --quiet flag
  - **TDD**: Write unit test to verify progress callback invoked

### Phase 1.5: Output Serialization

**Dependencies**: Tasks 1.1.2, 1.1.3

- [ ] **Task 1.5.1**: Implement `PositionPlacementGrid.to_json()`
  - File: `cli/src/lego_image_processor/layout/grid.py`
  - Schema: Match `contracts/layout.json` specification
  - Structure:
    ```json
    {
      "metadata": {...},
      "positions": [...],
      "statistics": {...}
    }
    ```
  - Validation: JSON Schema validation before writing
  - **TDD**: Write unit test to verify output matches schema

- [ ] **Task 1.5.2**: Implement `PositionPlacementGrid.to_csv()`
  - File: `cli/src/lego_image_processor/layout/grid.py`
  - Columns: x_position, y_position, color_id, color_name, lego_color_code, part_type, lego_part_id
  - Header row: Yes
  - **TDD**: Write unit test to verify CSV format

- [ ] **Task 1.5.3**: Implement `PositionPlacementGrid.from_json()`
  - File: `cli/src/lego_image_processor/layout/grid.py`
  - Parse: JSON file → PositionPlacementGrid instance
  - Validation: Schema compliance, position count, land/ocean breakdown
  - **TDD**: Write unit test for round-trip serialization (to_json → from_json)

### Phase 1.6: Integration Testing

**Dependencies**: All Phase 1.1-1.5 tasks

- [ ] **Task 1.6.1**: Create end-to-end integration test
  - File: `tests/integration/test_layout_pipeline.py`
  - Test: Load quantized test image → Generate layout → Verify output
  - Assertions:
    - 10,240 positions generated
    - 3,062 land bricks (part_type="brick", lego_part_id="3062b")
    - 7,178 ocean tiles (part_type="tile", lego_part_id="98138")
    - All positions have valid coordinates (0 ≤ x < 128, 0 ≤ y < 80)
    - All colors from input image preserved in output
  - **Parallel**: Can run alongside contract tests `[P]`

- [ ] **Task 1.6.2**: Create contract test for `layout` command
  - File: `tests/contract/test_layout_contract.py`
  - Tests:
    - Valid input → Success exit code (0), valid JSON output
    - Missing file → Error exit code (1), error message
    - Invalid dimensions → Error exit code (1), resize suggestion
    - Invalid colors → Error exit code (1), color location + re-quantize suggestion
    - CSV output → Valid CSV format
  - **Parallel**: Can run alongside integration tests `[P]`

### Phase 1.7: Test Data Creation

**Dependencies**: None (can run early)

- [ ] **Task 1.7.1** `[P]`: Create test quantized images
  - Directory: `cli/tests/fixtures/images/`
  - Files needed:
    - `test_128x80_quantized.png` (valid 128×80 image with LEGO colors)
    - `test_wrong_size.png` (100×50 image for dimension error testing)
    - `test_invalid_colors.png` (128×80 with non-LEGO colors)
  - **Parallel**: Can create while implementing core logic

- [ ] **Task 1.7.2** `[P]`: Create expected layout outputs
  - Directory: `cli/tests/fixtures/layouts/`
  - Files:
    - `expected_test_128x80.json` (expected output for test_128x80_quantized.png)
    - `expected_test_128x80.csv` (CSV version)
  - Purpose: Regression testing to ensure layout generation consistency
  - **Parallel**: Can create after Task 1.7.1

### Phase 1.8: Documentation

**Dependencies**: All Phase 1 tasks completed

- [ ] **Task 1.8.1**: Add layout generation examples to CLI help
  - File: `cli/src/lego_image_processor/cli/layout.py`
  - Add: Click command docstring with examples
  - Include: Basic usage, output format options, common errors

- [ ] **Task 1.8.2**: Update main CLI README
  - File: `cli/README.md`
  - Add: Layout command documentation
  - Examples: From `quickstart.md` scenarios 1-4
  - Link: To contracts/layout.json schema

---

## User Story 2 (P2): Kit Color Validation

**Goal**: Validate generated layouts against official LEGO World Map kit 31203 inventory to ensure buildability with standard kit parts.

**Dependencies**: P1 completion (needs layout generation working)

### Phase 2.1: Kit Specification Loading

**Dependencies**: None (reads configuration file)

- [ ] **Task 2.1.1**: Create `LEGOWorldMapKitSpecification` class
  - File: `cli/src/lego_image_processor/layout/kit_spec.py`
  - Attributes:
    - Constant: kit_id, kit_name, base_plate_width, base_plate_height, total_positions, land_positions, ocean_positions, land_part_id, ocean_part_id
    - Variable: available_colors_brick, available_colors_tile, brick_quantities, tile_quantities
  - Methods: `from_json()`, `to_dict()`
  - **TDD**: Write unit test first (`tests/unit/test_kit_spec.py`)

- [ ] **Task 2.1.2**: Create kit configuration JSON file
  - File: `cli/src/lego_image_processor/data/lego_world_map_kit.json`
  - Structure: Match data-model.md LEGOWorldMapKitSpecification entity
  - Content:
    - Constant structure: kit_id="31203", dimensions 128×80, land_part_id="3062b", ocean_part_id="98138"
    - Variable components: available_colors_brick[], available_colors_tile[], brick_quantities{}, tile_quantities{}
  - Source: Research official kit 31203 inventory from instruction manual or Rebrickable
  - **Note**: May need to populate placeholder data initially, refine later

- [ ] **Task 2.1.3**: Create `load_kit_specification()` function
  - File: `cli/src/lego_image_processor/layout/kit_spec.py`
  - Parameter: kit_id (e.g., "31203")
  - Returns: LEGOWorldMapKitSpecification instance
  - Error handling: File not found, invalid kit_id
  - **TDD**: Write unit test first

### Phase 2.2: Validation Logic

**Dependencies**: Tasks 2.1.1, 2.1.3, P1 completion

- [ ] **Task 2.2.1**: Create `Violation` base class and subclasses
  - File: `cli/src/lego_image_processor/layout/validator.py`
  - Classes:
    - `Violation` (abstract base)
    - `ColorUnavailableViolation`: type, part_type, part_id, color_id, color_name, positions_required, suggested_alternative
    - `QuantityExceededViolation`: type, part_type, part_id, color_id, color_name, positions_required, kit_quantity, shortfall
  - Methods: `to_dict()` for each class
  - **TDD**: Write unit test first (`tests/unit/test_validator.py`)

- [ ] **Task 2.2.2**: Create `ColorSuggestion` class
  - File: `cli/src/lego_image_processor/layout/validator.py`
  - Attributes: color_id, color_name, color_distance (Delta E)
  - Used in: ColorUnavailableViolation.suggested_alternative
  - **TDD**: Write unit test first

- [ ] **Task 2.2.3**: Create `ValidationReport` class
  - File: `cli/src/lego_image_processor/layout/validator.py`
  - Attributes: buildable (bool), buildability_score (float), violations (List[Violation]), validated_at, kit_id, layout_file
  - Methods: `to_dict()`, `to_json()`
  - Buildability score calculation: (buildable_positions) / (total_positions)
  - **TDD**: Write unit test first

- [ ] **Task 2.2.4**: Create `LayoutValidator` class
  - File: `cli/src/lego_image_processor/layout/validator.py`
  - Constructor: `__init__(kit_spec: LEGOWorldMapKitSpecification, palette: dict)`
  - Method: `validate(layout: PositionPlacementGrid) -> ValidationReport`
  - Algorithm:
    1. Count colors by part type: {part_type: {color_id: count}}
    2. For each brick color:
       - Check if color_id in kit_spec.available_colors_brick
       - If not: Create ColorUnavailableViolation, find nearest brick color (Delta E)
       - Check if count ≤ kit_spec.brick_quantities[color_id]
       - If not: Create QuantityExceededViolation
    3. For each tile color:
       - Same checks as brick colors, but against available_colors_tile and tile_quantities
    4. Compute buildability score
    5. Create ValidationReport
  - **TDD**: Write unit test first (`tests/unit/test_validator.py`)

- [ ] **Task 2.2.5**: Implement color suggestion algorithm
  - File: `cli/src/lego_image_processor/layout/validator.py`
  - Method: `_find_nearest_color(target_color_id, available_colors, part_type, palette)`
  - Algorithm: Use Delta E 2000 to find nearest available color
  - Returns: ColorSuggestion
  - **TDD**: Write unit test to verify correct nearest color selection

### Phase 2.3: CLI Command Implementation

**Dependencies**: Tasks 2.2.1-2.2.5

- [ ] **Task 2.3.1**: Create `validate` CLI command
  - File: `cli/src/lego_image_processor/cli/validate.py`
  - Command: `lego-image-processor validate <layout_file> [options]`
  - Arguments:
    - `layout_file` (required): Path to layout JSON/CSV file
    - `--kit` (optional): Kit ID to validate against (default: "31203")
    - `--output` / `-o` (optional): Validation report output file
  - Workflow:
    1. Load layout from file (JSON or CSV)
    2. Load kit specification
    3. Load palette (for color distance calculations)
    4. Validate layout using LayoutValidator
    5. Write validation report (if --output specified)
    6. Print summary to stdout (buildable status, violations, suggestions)
  - **TDD**: Write contract test first (`tests/contract/test_validate_contract.py`)

- [ ] **Task 2.3.2**: Register `validate` command in CLI entry point
  - File: `cli/src/lego_image_processor/cli/__init__.py`
  - Add: Import and register validate command with Click group
  - Verify: `lego-image-processor --help` shows validate command

### Phase 2.4: Integration Testing

**Dependencies**: All Phase 2.1-2.3 tasks

- [ ] **Task 2.4.1**: Create integration test for validation workflow
  - File: `tests/integration/test_validation_pipeline.py`
  - Test scenarios:
    - Fully buildable layout → buildability_score = 1.0, violations = []
    - Layout with unavailable brick color → ColorUnavailableViolation with suggestion
    - Layout with unavailable tile color → ColorUnavailableViolation with suggestion
    - Layout exceeding brick quantity → QuantityExceededViolation with shortfall
    - Layout exceeding tile quantity → QuantityExceededViolation with shortfall
  - **Parallel**: Can run alongside contract tests `[P]`

- [ ] **Task 2.4.2**: Create contract test for `validate` command
  - File: `tests/contract/test_validate_contract.py`
  - Tests:
    - Valid buildable layout → Exit 0, "FULLY BUILDABLE" message
    - Invalid layout → Exit 0, validation report with violations
    - Missing layout file → Exit 1, error message
    - Invalid kit ID → Exit 1, error message
  - **Parallel**: Can run alongside integration tests `[P]`

### Phase 2.5: Documentation

**Dependencies**: All Phase 2 tasks completed

- [ ] **Task 2.5.1**: Add validation examples to CLI help
  - File: `cli/src/lego_image_processor/cli/validate.py`
  - Add: Click command docstring with examples
  - Include: Basic usage, kit options, interpreting reports

- [ ] **Task 2.5.2**: Update CLI README with validation workflow
  - File: `cli/README.md`
  - Add: Validation command documentation
  - Examples: From `quickstart.md` scenario 5
  - Include: Violation types, buildability score interpretation

---

## User Story 3 (P3): Official Kit Shadowing Replication

**Goal**: Apply exact shadowing pattern from official LEGO World Map kit 31203 to custom layouts for visual depth.

**Status**: DEFERRED - Requires research into official kit shadowing patterns

**Prerequisites**:
1. Extract shadowing pattern from official kit 31203 instruction manual
2. Document shadowing rules (which positions get shadow tiles, which shadow color)
3. Update LEGOWorldMapKitSpecification with shadowing_pattern field

**Tasks will be created after shadowing research is complete.**

---

## Dependency Graph

```
Story P1: Basic Position Placement Layout Generation
│
├─ Phase 1.1: Core Data Structures (no dependencies)
│  ├─ Task 1.1.1: PositionPlacement class
│  ├─ Task 1.1.2: PositionPlacementGrid class
│  └─ Task 1.1.3: LayoutStatistics class
│
├─ Phase 1.2: Land/Sea Mask Loading (no dependencies)
│  ├─ Task 1.2.1: LandSeaMask class
│  └─ Task 1.2.2: load_land_sea_mask() function
│
├─ Phase 1.3: Layout Generation Logic
│  │  Dependencies: 1.1.1, 1.1.2, 1.2.1, 1.2.2
│  ├─ Task 1.3.1: LayoutGenerator class
│  ├─ Task 1.3.2: Dimension validation
│  └─ Task 1.3.3: Color validation
│
├─ Phase 1.4: CLI Command Implementation
│  │  Dependencies: 1.3.1, 1.3.2, 1.3.3
│  ├─ Task 1.4.1: layout CLI command
│  ├─ Task 1.4.2: Register command
│  └─ Task 1.4.3: Progress feedback
│
├─ Phase 1.5: Output Serialization
│  │  Dependencies: 1.1.2, 1.1.3
│  ├─ Task 1.5.1: to_json() method
│  ├─ Task 1.5.2: to_csv() method
│  └─ Task 1.5.3: from_json() method
│
├─ Phase 1.6: Integration Testing
│  │  Dependencies: All Phase 1.1-1.5 tasks
│  ├─ Task 1.6.1: End-to-end integration test [P]
│  └─ Task 1.6.2: Contract test [P]
│
├─ Phase 1.7: Test Data Creation (can run early) [P]
│  ├─ Task 1.7.1: Create test images [P]
│  └─ Task 1.7.2: Create expected outputs [P]
│
└─ Phase 1.8: Documentation
   │  Dependencies: All Phase 1 tasks
   ├─ Task 1.8.1: CLI help examples
   └─ Task 1.8.2: Update README

Story P2: Kit Color Validation
│  Dependencies: P1 completion
│
├─ Phase 2.1: Kit Specification Loading (no dependencies)
│  ├─ Task 2.1.1: LEGOWorldMapKitSpecification class
│  ├─ Task 2.1.2: Kit configuration JSON
│  └─ Task 2.1.3: load_kit_specification() function
│
├─ Phase 2.2: Validation Logic
│  │  Dependencies: 2.1.1, 2.1.3, P1 completion
│  ├─ Task 2.2.1: Violation classes
│  ├─ Task 2.2.2: ColorSuggestion class
│  ├─ Task 2.2.3: ValidationReport class
│  ├─ Task 2.2.4: LayoutValidator class
│  └─ Task 2.2.5: Color suggestion algorithm
│
├─ Phase 2.3: CLI Command Implementation
│  │  Dependencies: 2.2.1-2.2.5
│  ├─ Task 2.3.1: validate CLI command
│  └─ Task 2.3.2: Register command
│
├─ Phase 2.4: Integration Testing
│  │  Dependencies: All Phase 2.1-2.3 tasks
│  ├─ Task 2.4.1: Integration test [P]
│  └─ Task 2.4.2: Contract test [P]
│
└─ Phase 2.5: Documentation
   │  Dependencies: All Phase 2 tasks
   ├─ Task 2.5.1: CLI help examples
   └─ Task 2.5.2: Update README

Story P3: Official Kit Shadowing Replication
└─ DEFERRED - Requires shadowing pattern research
```

---

## Task Execution Order

### Sequential Phases (Must Complete in Order)

**P1 Story Completion Sequence**:
1. Phase 1.1 (Core Data Structures) - No dependencies
2. Phase 1.2 (Land/Sea Mask) - No dependencies, can run parallel with 1.1 `[P]`
3. Phase 1.3 (Layout Generation) - Depends on 1.1, 1.2
4. Phase 1.4 (CLI Commands) - Depends on 1.3
5. Phase 1.5 (Output Serialization) - Depends on 1.1 (can overlap with 1.3, 1.4)
6. Phase 1.6 (Integration Testing) - Depends on all 1.1-1.5
7. Phase 1.8 (Documentation) - Depends on all Phase 1

**P2 Story Completion Sequence** (after P1):
1. Phase 2.1 (Kit Specification) - No dependencies
2. Phase 2.2 (Validation Logic) - Depends on 2.1 and P1 completion
3. Phase 2.3 (CLI Commands) - Depends on 2.2
4. Phase 2.4 (Integration Testing) - Depends on all 2.1-2.3
5. Phase 2.5 (Documentation) - Depends on all Phase 2

### Parallel Execution Opportunities

**Can be done early (during Phase 1.1-1.2)**:
- Task 1.7.1: Create test images `[P]`
- Task 1.7.2: Create expected outputs `[P]`

**Can be done in parallel within phases**:
- Phase 1.1: Tasks 1.1.1, 1.1.2, 1.1.3 can be worked on by different developers `[P]`
- Phase 1.2: Can overlap with Phase 1.1 `[P]`
- Phase 1.6: Tasks 1.6.1 and 1.6.2 can run simultaneously `[P]`
- Phase 2.4: Tasks 2.4.1 and 2.4.2 can run simultaneously `[P]`

---

## Checklist Summary

**Total Tasks**: 36 tasks (P1: 24 tasks, P2: 12 tasks, P3: deferred)

**P1 Tasks (Priority 1 - MVP)**:
- [ ] Phase 1.1: Core Data Structures (3 tasks)
- [ ] Phase 1.2: Land/Sea Mask Loading (2 tasks)
- [ ] Phase 1.3: Layout Generation Logic (3 tasks)
- [ ] Phase 1.4: CLI Command Implementation (3 tasks)
- [ ] Phase 1.5: Output Serialization (3 tasks)
- [ ] Phase 1.6: Integration Testing (2 tasks)
- [ ] Phase 1.7: Test Data Creation (2 tasks)
- [ ] Phase 1.8: Documentation (2 tasks)

**P2 Tasks (Priority 2 - Enhancement)**:
- [ ] Phase 2.1: Kit Specification Loading (3 tasks)
- [ ] Phase 2.2: Validation Logic (5 tasks)
- [ ] Phase 2.3: CLI Command Implementation (2 tasks)
- [ ] Phase 2.4: Integration Testing (2 tasks)
- [ ] Phase 2.5: Documentation (2 tasks)

**P3 Tasks (Priority 3 - Future)**:
- Deferred pending shadowing pattern research

---

## TDD Workflow Reminders

For each task marked "TDD":
1. **Write test first** (in appropriate test file)
2. **Run test** → Verify it FAILS (red)
3. **Implement feature** (minimal code to pass test)
4. **Run test again** → Verify it PASSES (green)
5. **Refactor** (if needed, keeping tests passing)

**Test Categories**:
- **Unit tests** (`tests/unit/`): Test individual classes/functions in isolation
- **Integration tests** (`tests/integration/`): Test workflows (quantized image → layout)
- **Contract tests** (`tests/contract/`): Test CLI command I/O (exit codes, outputs, errors)

---

## Notes

- All tasks follow TDD workflow per constitution requirement IV
- P1 delivers complete MVP: quantized image → buildable position layout
- P2 adds buildability validation (independent enhancement)
- P3 deferred pending research into official kit shadowing patterns
- Parallel execution opportunities marked with `[P]` flag for efficiency
- Each phase depends on previous phase completion within same story
- P2 requires P1 completion (can't validate layouts that don't exist yet)

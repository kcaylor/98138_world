# Tasks: Satellite Image to LEGO Color Palette Conversion

**Input**: Design documents from `/specs/001-image-processing/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: This feature follows TDD approach per constitution Principle IV. Tests MUST be written before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `cli/src/`, `cli/tests/` at repository root
- Paths shown below follow the single CLI package structure from plan.md

## Phase 1: Setup (Project Initialization)

**Purpose**: Initialize Python CLI package structure and dependencies

- [ ] T001 Create cli/ directory structure per plan.md (src/lego_image_processor/, tests/)
- [ ] T002 Initialize Poetry project with pyproject.toml in cli/ directory
- [ ] T003 [P] Add dependencies to pyproject.toml (Pillow, NumPy, scikit-image, Click, tqdm)
- [ ] T004 [P] Add dev dependencies to pyproject.toml (pytest, pytest-benchmark, black, mypy, ruff)
- [ ] T005 [P] Create cli/src/lego_image_processor/__init__.py with version info
- [ ] T006 [P] Create cli/README.md with installation and usage overview
- [ ] T007 [P] Create cli/LICENSE file (MIT or Apache 2.0)
- [ ] T008 [P] Create cli/CONTRIBUTING.md with development guidelines
- [ ] T009 [P] Create .gitignore for Python project (node_modules, __pycache__, dist/, .env, etc.)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T010 Create LEGO color palette JSON data file at cli/src/lego_image_processor/palette/lego_colors.json
- [ ] T011 [P] Implement LegoColor dataclass in cli/src/lego_image_processor/palette/__init__.py
- [ ] T012 [P] Implement LegoPalette dataclass in cli/src/lego_image_processor/palette/__init__.py
- [ ] T013 Implement palette loader in cli/src/lego_image_processor/palette/loader.py
- [ ] T014 [P] Implement RGB to LAB color space converter in cli/src/lego_image_processor/palette/converter.py
- [ ] T015 [P] Implement Delta E 2000 color distance calculator in cli/src/lego_image_processor/core/color_distance.py
- [ ] T016 [P] Create CLI entry point module at cli/src/lego_image_processor/__main__.py
- [ ] T017 [P] Set up Click command group structure in cli/src/lego_image_processor/cli/__init__.py
- [ ] T018 Create test fixtures directory at cli/tests/integration/fixtures/ with sample satellite images

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Basic Image Color Quantization (Priority: P1) 🎯 MVP

**Goal**: Users can convert satellite images to LEGO color palette and see quantized output

**Independent Test**: Provide sample satellite image, verify output contains only LEGO colors with visual similarity

### Tests for User Story 1 (TDD - Write FIRST, Ensure FAIL)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T019 [P] [US1] Write contract test for quantize command in cli/tests/contract/test_quantize_contract.py
- [ ] T020 [P] [US1] Write integration test for image-to-LEGO workflow in cli/tests/integration/test_image_to_lego_workflow.py
- [ ] T021 [P] [US1] Write unit test for image loader in cli/tests/unit/test_image_loader.py
- [ ] T022 [P] [US1] Write unit test for color quantizer in cli/tests/unit/test_color_quantizer.py
- [ ] T023 [P] [US1] Write unit test for image writer in cli/tests/unit/test_image_writer.py

### Implementation for User Story 1

- [ ] T024 [P] [US1] Implement InputImage dataclass and from_file() method in cli/src/lego_image_processor/core/image_loader.py
- [ ] T025 [P] [US1] Implement QuantizedImage dataclass and save() method in cli/src/lego_image_processor/core/image_writer.py
- [ ] T026 [US1] Implement ColorQuantizer class with quantize() method in cli/src/lego_image_processor/core/color_quantizer.py
- [ ] T027 [US1] Implement quantize CLI command in cli/src/lego_image_processor/cli/quantize.py with Click decorators
- [ ] T028 [US1] Add input validation (file exists, format check, size limits) to quantize command
- [ ] T029 [US1] Add progress feedback with tqdm in quantize command
- [ ] T030 [US1] Add --verbose and --quiet flags to quantize command
- [ ] T031 [US1] Implement output file collision handling (prompt for confirmation) in quantize command
- [ ] T032 [US1] Add error handling for corrupted files with helpful diagnostic messages
- [ ] T033 [US1] Add error handling for large images (>100 MP) with downsampling guidance
- [ ] T034 [US1] Add grayscale image auto-conversion with warning message
- [ ] T035 [US1] Add --force/--overwrite flag for non-interactive mode

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Color Statistics (Priority: P2)

**Goal**: Users can analyze color usage in quantized images to understand LEGO brick requirements

**Independent Test**: Run stats command on quantized image, verify accurate pixel counts and percentages

### Tests for User Story 2 (TDD - Write FIRST, Ensure FAIL)

- [ ] T036 [P] [US2] Write contract test for stats command in cli/tests/contract/test_stats_contract.py
- [ ] T037 [P] [US2] Write unit test for color statistics calculator in cli/tests/unit/test_color_stats.py

### Implementation for User Story 2

- [ ] T038 [P] [US2] Implement ColorUsage dataclass in cli/src/lego_image_processor/analysis/color_stats.py
- [ ] T039 [P] [US2] Implement ColorStatistics dataclass with from_quantized_image() method in cli/src/lego_image_processor/analysis/color_stats.py
- [ ] T040 [US2] Implement to_json() method for ColorStatistics in cli/src/lego_image_processor/analysis/color_stats.py
- [ ] T041 [US2] Implement to_human_readable() method for ColorStatistics in cli/src/lego_image_processor/analysis/color_stats.py
- [ ] T042 [US2] Implement stats CLI command in cli/src/lego_image_processor/cli/stats.py
- [ ] T043 [US2] Add --format flag (text/json) to stats command
- [ ] T044 [US2] Add --output flag to save statistics to file
- [ ] T045 [US2] Add --sort-by flag (frequency/name/color_id) to stats command
- [ ] T046 [US2] Add validation to detect non-quantized images (>100 unique colors warning)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Batch Processing (Priority: P3)

**Goal**: Users can process multiple images efficiently with parallel processing support

**Independent Test**: Provide directory with multiple images, verify all are processed with individual outputs

### Tests for User Story 3 (TDD - Write FIRST, Ensure FAIL)

- [ ] T047 [P] [US3] Write contract test for batch command in cli/tests/contract/test_batch_contract.py
- [ ] T048 [P] [US3] Write integration test for batch processing in cli/tests/integration/test_batch_processing.py

### Implementation for User Story 3

- [ ] T049 [P] [US3] Implement ProcessingStatus enum in cli/src/lego_image_processor/core/__init__.py
- [ ] T050 [P] [US3] Implement ImageProcessingResult dataclass in cli/src/lego_image_processor/core/__init__.py
- [ ] T051 [P] [US3] Implement BatchProcessingResult dataclass in cli/src/lego_image_processor/core/__init__.py
- [ ] T052 [US3] Implement batch CLI command in cli/src/lego_image_processor/cli/batch.py
- [ ] T053 [US3] Add directory discovery with glob pattern matching in batch command
- [ ] T054 [US3] Add --recursive flag for subdirectory processing in batch command
- [ ] T055 [US3] Add --parallel flag with worker count in batch command
- [ ] T056 [US3] Implement sequential processing loop in batch command
- [ ] T057 [US3] Implement parallel processing with concurrent.futures in batch command
- [ ] T058 [US3] Add --continue-on-error and --fail-fast flags in batch command
- [ ] T059 [US3] Add --dry-run flag to preview files without processing
- [ ] T060 [US3] Implement batch summary report with success/failure counts

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and final quality checks

- [ ] T061 [P] Add type hints throughout codebase and run mypy validation
- [ ] T062 [P] Run black formatter on all Python files
- [ ] T063 [P] Run ruff linter and fix any issues
- [ ] T064 [P] Create cli/tests/unit/test_palette_loader.py for palette loading edge cases
- [ ] T065 [P] Create cli/tests/unit/test_color_distance.py for Delta E accuracy validation
- [ ] T066 [P] Add performance benchmarks using pytest-benchmark for 1024x1024 image processing
- [ ] T067 Update cli/README.md with complete usage examples from quickstart.md
- [ ] T068 [P] Add LEGO disclaimer to CLI help text and README
- [ ] T069 [P] Create example satellite images for cli/tests/integration/fixtures/
- [ ] T070 Run full test suite and ensure all tests pass
- [ ] T071 Validate quickstart.md examples work correctly
- [ ] T072 [P] Add cross-platform testing on Windows, macOS, Linux (if possible)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - US1 (P1): Can start after Foundational - No dependencies on other stories
  - US2 (P2): Can start after Foundational - May use US1 for testing but independently functional
  - US3 (P3): Can start after Foundational - Builds on US1 quantization but independently testable
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories ✅ MVP
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1 (can analyze any quantized image)
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Uses US1 quantization logic but is independently testable

### Within Each User Story

- **TDD Flow**: Tests MUST be written first and MUST fail before implementation
- **Order**: Tests → Dataclasses → Core Logic → CLI Command → Validation/Error Handling
- **Parallel Opportunities**: Tests can be written in parallel, dataclasses can be created in parallel

### Parallel Opportunities

**Phase 1 (Setup) - All tasks [P] can run in parallel**:
- T003-T009 can all execute simultaneously (different files)

**Phase 2 (Foundational) - Many tasks [P] can run in parallel**:
- T011, T012 (dataclasses) can run in parallel
- T014, T015 (converters, color distance) can run in parallel
- T016, T017 (CLI setup) can run in parallel

**Phase 3 (US1) - Test tasks [P] can run in parallel**:
- T019-T023 (all test files) can be written simultaneously
- T024, T025 (dataclasses) can run in parallel

**Phase 4 (US2) - Test tasks [P] can run in parallel**:
- T036, T037 (test files) can be written simultaneously
- T038, T039 (dataclasses) can run in parallel

**Phase 5 (US3) - Test tasks [P] can run in parallel**:
- T047, T048 (test files) can be written simultaneously
- T049, T050, T051 (dataclasses) can run in parallel

**Phase 6 (Polish) - Most tasks [P] can run in parallel**:
- T061-T069, T072 can all execute simultaneously

**Once Foundational is complete, all three user stories can be worked on in parallel by different team members**

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all test writing tasks for User Story 1 together:
Task: "Write contract test for quantize command in cli/tests/contract/test_quantize_contract.py"
Task: "Write integration test for image-to-LEGO workflow in cli/tests/integration/test_image_to_lego_workflow.py"
Task: "Write unit test for image loader in cli/tests/unit/test_image_loader.py"
Task: "Write unit test for color quantizer in cli/tests/unit/test_color_quantizer.py"
Task: "Write unit test for image writer in cli/tests/unit/test_image_writer.py"

# Then launch dataclass creation in parallel:
Task: "Implement InputImage dataclass in cli/src/lego_image_processor/core/image_loader.py"
Task: "Implement QuantizedImage dataclass in cli/src/lego_image_processor/core/image_writer.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T009)
2. Complete Phase 2: Foundational (T010-T018) - CRITICAL blocking phase
3. Complete Phase 3: User Story 1 (T019-T035)
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

**MVP Deliverable**: Working CLI tool that quantizes satellite images to LEGO colors

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP! ✅)
3. Add User Story 2 → Test independently → Deploy/Demo (Now with analytics)
4. Add User Story 3 → Test independently → Deploy/Demo (Now with batch processing)
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T018)
2. Once Foundational is done (after T018):
   - Developer A: User Story 1 (T019-T035)
   - Developer B: User Story 2 (T036-T046)
   - Developer C: User Story 3 (T047-T060)
3. Stories complete and integrate independently
4. Team reconvenes for Polish phase (T061-T072)

---

## Notes

- **[P] tasks**: Different files, no dependencies on incomplete tasks
- **[Story] label**: Maps task to specific user story for traceability
- **Each user story is independently completable and testable**
- **TDD MANDATORY**: Tests MUST be written first and MUST fail before implementation
- **Verify tests fail before implementing**: Run pytest after writing tests to see red, then implement to see green
- **Commit after each task or logical group**
- **Stop at any checkpoint to validate story independently**
- **File paths are exact**: Use these paths verbatim when creating files
- **Avoid**: Vague tasks, same file conflicts, cross-story dependencies that break independence

---

## Validation Checklist

Before marking a user story complete:

**User Story 1 (P1)**:
- [ ] All US1 tests pass (contract, integration, unit)
- [ ] Can quantize PNG, JPEG, TIFF images
- [ ] Output contains only LEGO colors
- [ ] Processing completes in <30s for 1024x1024 images
- [ ] Error messages are clear and helpful
- [ ] Progress feedback works correctly
- [ ] Works on Windows, macOS, Linux

**User Story 2 (P2)**:
- [ ] All US2 tests pass
- [ ] Color statistics match pixel counts exactly (100% accuracy)
- [ ] JSON output is valid and parseable
- [ ] Text output is human-readable
- [ ] Statistics complete in <5 seconds
- [ ] Sort options work correctly

**User Story 3 (P3)**:
- [ ] All US3 tests pass
- [ ] Can process multiple images in directory
- [ ] Parallel processing reduces total time
- [ ] Continue-on-error works correctly
- [ ] Dry-run mode previews without processing
- [ ] Batch summary report is accurate

**Overall Quality**:
- [ ] All 72 tasks completed
- [ ] Full test suite passes (pytest)
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Formatting consistent (black)
- [ ] Performance benchmarks meet targets
- [ ] Documentation complete and accurate
- [ ] LEGO disclaimer included

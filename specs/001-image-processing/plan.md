# Implementation Plan: Satellite Image to LEGO Color Palette Conversion

**Branch**: `001-image-processing` | **Date**: 2026-01-04 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-image-processing/spec.md`

## Summary

Create a Python CLI tool that converts satellite images to LEGO World Map compatible color palettes through perceptual color quantization. The tool reads image files (PNG, JPEG, TIFF), maps each pixel to the closest LEGO brick color using Delta E color distance in LAB space, and outputs quantized images with optional color usage statistics. This is the foundational component for the 98138.world LEGO map generation system.

## Technical Context

**Language/Version**: Python 3.11+ (per constitution requirement for CLI tools)
**Primary Dependencies**: Pillow (image I/O), NumPy (array operations), scikit-image (color space conversion), Click (CLI framework)
**Storage**: Local filesystem only (input images, output images, LEGO color palette JSON/CSV)
**Testing**: pytest (unit and integration tests), pytest-benchmark (performance validation)
**Target Platform**: Cross-platform (Windows, macOS, Linux) - desktop CLI tool
**Project Type**: Single CLI package (no web components in this feature)
**Performance Goals**: Process 1024x1024 image in <10 seconds, 10 megapixel image in <30 seconds
**Constraints**: Offline operation (no internet required), <500MB memory for 10MP images, cross-platform compatibility
**Scale/Scope**: Single-user CLI tool, ~2000 LOC estimated, 3 user stories (P1=quantization, P2=statistics, P3=batch)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: CLI-First Architecture
✅ **PASS** - This entire feature IS a CLI tool. No web integration in this phase.
- All functionality accessible via command-line interface
- Inputs via args/stdin, outputs to stdout (JSON and human-readable)
- Independently testable without any web dependencies

### Principle II: Modular & Open Source Ready
✅ **PASS** - Designed for open-source release from the start.
- Separate `cli/` package with independent versioning
- No hardcoded credentials or proprietary endpoints
- Works entirely offline with local files
- Clear separation from future web backend

### Principle III: Incremental Delivery
✅ **PASS** - Three independently testable user stories.
- P1 (MVP): Basic color quantization - delivers immediate visual preview value
- P2: Color statistics - adds analytical value, independent of P1
- P3: Batch processing - convenience feature, works independently
- Each story can be deployed/demoed independently

### Principle IV: Test-First Development
✅ **PASS** - TDD approach planned.
- Contract tests for CLI commands (validate inputs/outputs)
- Integration tests for end-to-end image processing workflows
- Unit tests for color distance algorithms
- Test data includes sample satellite images and LEGO palette reference

### Principle V: Performance & Scale Targets
✅ **PASS** - Meets constitution requirements.
- Target: 1024x1024 image in <30 seconds (constitution: <30s) ✓
- Target: 10 megapixel image in <30 seconds (within spec limits) ✓
- No concurrent user requirements (single-user CLI tool)

### Principle VI: Deployment & Infrastructure
✅ **PASS** - CLI tool, no deployment infrastructure needed yet.
- Packaged as Python package (Poetry/setuptools)
- Distributed via PyPI (future) or direct installation
- No Docker/Fly.io requirements for CLI-only feature

### Principle VII: Data & Privacy
✅ **PASS** - Local file processing only.
- All processing happens locally on user's machine
- No data uploaded or stored remotely
- Users retain full ownership of input/output files
- LEGO disclaimer will be included in CLI help text and documentation

## Project Structure

### Documentation (this feature)

```text
specs/001-image-processing/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0: Technology decisions and color algorithm research
├── data-model.md        # Phase 1: LEGO color palette and image data structures
├── quickstart.md        # Phase 1: Quick start guide and usage examples
├── contracts/           # Phase 1: CLI command contracts (input/output schemas)
│   ├── quantize.json    # Contract for main quantization command
│   ├── stats.json       # Contract for color statistics command
│   └── batch.json       # Contract for batch processing command
└── checklists/
    └── requirements.md  # Spec quality checklist (completed)
```

### Source Code (repository root)

```text
cli/                              # Python CLI package (open-source ready)
├── src/
│   └── lego_image_processor/     # Main package namespace
│       ├── __init__.py
│       ├── __main__.py           # CLI entry point
│       ├── cli/                  # Click command definitions
│       │   ├── __init__.py
│       │   ├── quantize.py       # P1: Image quantization command
│       │   ├── stats.py          # P2: Color statistics command
│       │   └── batch.py          # P3: Batch processing command
│       ├── core/                 # Core processing logic
│       │   ├── __init__.py
│       │   ├── image_loader.py   # Load and validate images
│       │   ├── color_quantizer.py # Pixel-to-LEGO color mapping
│       │   ├── color_distance.py  # Delta E calculations (LAB space)
│       │   └── image_writer.py    # Save quantized images
│       ├── palette/              # LEGO color palette management
│       │   ├── __init__.py
│       │   ├── loader.py         # Load palette from JSON/CSV
│       │   ├── lego_colors.json  # Official LEGO World Map colors
│       │   └── converter.py      # RGB ↔ LAB color space conversion
│       └── analysis/             # Color analysis and statistics
│           ├── __init__.py
│           └── color_stats.py    # Calculate color usage statistics
├── tests/
│   ├── contract/                 # CLI command contract tests
│   │   ├── test_quantize_contract.py
│   │   ├── test_stats_contract.py
│   │   └── test_batch_contract.py
│   ├── integration/              # End-to-end workflow tests
│   │   ├── test_image_to_lego_workflow.py
│   │   ├── test_batch_processing.py
│   │   └── fixtures/             # Test images and expected outputs
│   │       ├── sample_satellite_1.png
│   │       ├── sample_satellite_2.jpg
│   │       └── expected_outputs/
│   └── unit/                     # Algorithm and component tests
│       ├── test_color_distance.py
│       ├── test_color_quantizer.py
│       ├── test_image_loader.py
│       └── test_palette_loader.py
├── pyproject.toml                # Poetry configuration
├── README.md                     # Installation and usage guide
├── LICENSE                       # MIT or Apache 2.0
└── CONTRIBUTING.md               # Development and contribution guide
```

**Structure Decision**: Single CLI package structure chosen (per constitution). This is a standalone Python CLI tool with no web components. The `cli/` directory at repository root will contain the complete open-source-ready package. Future features will add `backend/` and `frontend/` directories, but this feature focuses solely on the CLI foundation.

## Complexity Tracking

> No constitution violations - all checks passed. This section is empty.

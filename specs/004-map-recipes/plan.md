# Implementation Plan: Map Recipes and Canonical Datasets

**Branch**: `004-map-recipes` | **Date**: 2026-11-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-map-recipes/spec.md`

## Summary

Add a recipe-driven map pipeline to the CLI: a TOML recipe (Q1) names a land layer and
an ocean layer, each data-driven or background. Data layers read a pinned, cached dataset,
reproject it onto the kit grid with the fitted equirectangular kit projection (94.2% mask
agreement, research R2), classify it (`bins`, `quantile`, `rank`, `rank-to-supply`,
`categorical`) onto an ordered scale of colors available for the layer's part, and soften steps
with a seeded texture. Background layers mix weighted colors with clustered noise. The kit mask
decides land and ocean. Each build writes a schema 2.0 layout with a `metadata.map` provenance
block (Q3), an optional preview PNG and a suitability report. Two datasets are
registered: ETOPO 2022 (10′ OPeNDAP subset, 9.4 MB, public domain) and ERSST v5 1991–2020
climatology (1.2 MB, public domain). Four bundled recipes are the acceptance tests:
`official-31203` (exact, 10,240/10,240), `official-31203-bathymetry` (derived, ≥ 24% ocean
agreement, kit-buildable) (Q5), `ocean-sst` (kit colors, within one kit's supply) and
`land-elevation` (plate colors from a new cited part-color table) (Q4). New CLI groups
`map` and `dataset` and `kit part-colors`; `map build --fetch` downloads missing pinned data on request (Q2). No new third-party dependencies (SciPy
becomes explicit; TOML and HTTP use the standard library).

## Technical Context

**Language/Version**: Python 3.11+ (constitution; `tomllib` needs 3.11)

**Primary Dependencies**: existing NumPy, Pillow, Click, scikit-image; SciPy declared explicitly
(already installed through scikit-image; BSD-3-Clause) for `scipy.io.netcdf_file` and
`scipy.ndimage` (nearest fill, Gaussian noise). Standard library `tomllib`, `urllib.request`,
`hashlib`. No new third-party packages.

**Storage**: files. Package data in `cli/src/lego_image_processor/data/` (projection, dataset
registry, part colors) and bundled recipes in `cli/src/lego_image_processor/maps/recipes/`;
per-user cache for datasets (003 cache root).

**Testing**: pytest (unit, integration, contract), offline guard in `tests/conftest.py`; small
synthetic and derived fixtures only.

**Target Platform**: macOS/Linux/Windows command line, offline after fetch.

**Project Type**: CLI + library (single project, `cli/`).

**Performance Goals**: a bundled recipe builds from cache in < 30 s (SC-006; expected < 5 s:
reprojection is a `bincount` over ≤ 2.4 M samples); failure for a missing dataset in < 2 s
(SC-004).

**Constraints**: no network in tests or builds; deterministic output; downloads ≤ 15 MB total for
bundled recipes (10.5 MB measured); never commit downloaded files.

**Scale/Scope**: one template (31203), 4 bundled recipes, 2 registry datasets, ~25 part colors.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Kit is a fixed template | Kit mask decides every cell's class and part; maps vary colors only. Projection stored as versioned package data with its derivation (R2). | PASS |
| II. Maps are layers / recipes | Recipe = land + ocean layer, roles data/background, dataset, classification, color scale, texture. Official design reproducible as a recipe (exact tier). | PASS |
| III. Data in, not pictures | Bundled maps read gridded data; the image path is untouched and secondary. | PASS |
| IV. Reproducible acquisition | Registry pins URL, version, size, SHA-256; verified cache; offline after fetch; citation and license in layout metadata and reports; no credentials needed. | PASS |
| V. Buildable and honest | Colors must be in the kit table or the cited part-color table; rows with missing IDs excluded; suitability check on every build; supply comparison. | PASS (depends on Q4) |
| VI. CLI-first | Every capability is a library function with a CLI command; no web code. | PASS |
| VII. Test-first, offline | Unit tests first for readers, projection, reprojection, classification, texture, suitability, recipe parsing; fetch tested with a fake opener. | PASS |
| VIII. LEGO compliance | Disclaimer on every new command's human output, in JSON reports, layout metadata, recipe files' comments and data files. | PASS |

**Post-design re-check**: PASS. No violations; Complexity Tracking is empty.

## Reserved decisions (answered by the user, 2026-11-22)

All six were answered; Q2 differs from the planner's recommendation (`map build --fetch` is an
opt-in download). Details: `run-state.md` Decisions and spec Clarifications.

- **Q1 Recipe file format** (file format others use): TOML via `tomllib` (recommended), YAML, or
  JSON.
- **Q2 New CLI commands** (public CLI): `map build|check|recipes`, `dataset list|fetch|info`,
  `kit part-colors`; builds download only with `map build --fetch` (user choice).
- **Q3 Layout provenance** (file format others use): additive `metadata.map` block in schema 2.0
  (recommended), sidecar file, or schema 2.1.
- **Q4 Colors beyond the kit** (reference data policy, constitution V): curated cited
  `part_colors.json` from pinned catalog snapshots (recommended), runtime API, or kit colors only.
- **Q5 Acceptance for the official design** (product scope): two tiers, exact + derived ≥ 24%.
- **Q6 Local data files in recipes** (product scope): allowed with declared SHA-256, citation and
  license (recommended), or registry only.

## Project Structure

### Documentation (this feature)

```text
specs/004-map-recipes/
├── plan.md               # This file
├── research.md           # Phase 0: measurements and decisions R1–R12
├── data-model.md         # Phase 1: entities and validation rules
├── quickstart.md         # Phase 1: validation run guide
├── contracts/
│   ├── recipe-format.md  # Recipe file (TOML) schema
│   ├── cli.md            # map, dataset, kit part-colors commands
│   ├── data-files.md     # projection, datasets registry, part colors, layout metadata.map
│   └── library-api.md    # Python API
├── checklists/requirements.md
├── run-state.md
└── tasks.md              # Phase 2 (speckit-tasks)
```

### Source Code (repository root)

```text
cli/
├── pyproject.toml                        # + scipy (explicit)
├── src/lego_image_processor/
│   ├── data/
│   │   ├── kit_31203_projection.json     # NEW (R2)
│   │   ├── datasets.json                 # NEW registry (R3, R4)
│   │   └── part_colors.json              # NEW cited part colors (R9)
│   ├── datasets/                         # NEW
│   │   ├── __init__.py
│   │   ├── registry.py                   # DatasetEntry, load_registry
│   │   ├── cache.py                      # cache_root, fetch, verify, cached_path
│   │   ├── readers.py                    # read_dods, read_netcdf3, read_npy -> SourceGrid
│   │   └── grid.py                       # SourceGrid (values, lat, lon, class rule)
│   ├── maps/                             # NEW
│   │   ├── __init__.py
│   │   ├── recipe.py                     # Recipe, Layer, parse/validate (tomllib)
│   │   ├── projection.py                 # KitProjection, cell index of (lat, lon)
│   │   ├── reproject.py                  # cell means by class, nearest fill
│   │   ├── classify.py                   # bins, quantile, rank, rank-to-supply, categorical
│   │   ├── texture.py                    # blend, pairwise swap, mix
│   │   ├── suitability.py                # SuitabilityReport
│   │   ├── build.py                      # build_map(recipe) -> MapResult (layout, report)
│   │   ├── preview.py                    # PNG preview
│   │   └── recipes/                      # bundled: official-31203.toml, official-31203-bathymetry.toml,
│   │                                     #          ocean-sst.toml, land-elevation.toml
│   ├── kit/part_colors.py                # NEW load_part_colors, colors_for_part
│   ├── layout/grid.py                    # keep metadata.map through to_json/from_json
│   └── cli/
│       ├── map.py                        # NEW map build|check|recipes
│       ├── dataset.py                    # NEW dataset list|fetch|info
│       ├── kit.py                        # + part-colors
│       └── main.py                       # register groups
├── tools/
│   ├── kit31203/__main__.py              # + fit-projection [--check]
│   ├── kit31203/source.py                # import cache_root from the package
│   ├── partcolors/                       # NEW maintainer tool: build part_colors.json from pinned snapshots
│   └── fixtures004/                      # NEW maintainer script: derived test fixtures
└── tests/
    ├── unit/maps/, unit/datasets/        # NEW
    ├── integration/test_map_*.py         # NEW (official exact, bathymetry derived, sst, elevation)
    ├── contract/test_map_contract.py, test_dataset_contract.py
    └── fixtures/datasets/                # NEW small derived fixtures + .source.json
```

**Structure Decision**: single project as in 001–003. New `datasets` and `maps` subpackages keep
data access separate from map logic so the web app (later) can reuse both.

## Implementation phases (for /speckit-tasks)

1. **Setup**: scipy explicit; package-data include for `maps/recipes/*.toml`; test fixture dirs.
2. **Foundational**: cache helper moved into the package (003 tool imports it); dataset registry
   loader; SourceGrid + readers; kit projection data + loader; part-color loader skeleton with the
   kit's 10 colors; recipe parser; layout `metadata.map` round trip.
3. **US1 (P1)**: categorical design dataset, background layer, `categorical` classification,
   build pipeline, `map build`/`map recipes`, `official-31203.toml`; exact-match test.
4. **US2 (P2)**: fetch with verification, `dataset list|fetch|info`, missing-dataset errors,
   fake-opener tests.
5. **US3 (P3)**: reprojection, `bins`/`quantile`/`rank`/`rank-to-supply`, texture blend and
   swaps, background mix, suitability in builds, preview PNG; `official-31203-bathymetry.toml` and
   `ocean-sst.toml`; derived fixtures; `fit-projection` maintainer command.
6. **US4 (P4)**: part-color maintainer tool and `part_colors.json`; `kit part-colors`;
   `land-elevation.toml`; validate behaviour test.
7. **US5 (P5)**: `map check`, full report JSON, synthetic suitability tests.
8. **Polish**: docs (cli/README, quickstart run), disclaimer tests across commands, offline
   guard check, performance check, vision roadmap note.

## Complexity Tracking

No constitution violations.

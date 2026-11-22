# Implementation Plan: ENSO Sea Surface Temperature Anomaly Maps

**Branch**: `009-enso-sst-maps` | **Date**: 2026-11-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/009-enso-sst-maps/spec.md`; decisions, measurements
and the legend derivation in [run-state.md](run-state.md).

## Summary

Two bundled recipes, `ocean-el-nino` (ERSST v5 `ssta`, December 1997) and `ocean-la-nina`
(December 1988), share one fixed `bins` legend in °C of anomaly on the kit's nine ocean colors in
the `ocean-sst` cold-to-warm order, with bounds −9, −1.5, −0.5, −0.25, −0.1, +0.1, +0.3, +0.5,
+1.0, +9 (research R1). Both set the new optional top-level recipe key `arrangement = "B"`, which
replaces only the default of `map build`/`map check --arrangement` (an explicit flag wins; R3).
The netCDF-3 reader drops size-1 leading axes so the per-month files' `(time=1, lev=1, lat, lon)`
variables read as one field, and rejects netCDF-4 files by signature (R2). Two pinned registry
entries hold the NCEI URLs and the measured SHA-256s (R4). The build output gains each `bins`
color's °C range and a "tiles beyond one kit" total computed from the report's existing supply
rows; the report JSON gains one field, `arrangement_source` (R5; owner sign-off pending, see
run-state ESCALATE). Tests run offline on two derived int16 fixtures of the
full 2° grid (R6). No new dependency, no layout format change.

## Technical Context

**Language/Version**: Python 3.11 (Poetry; `cli/.venv` via uv also supported)

**Primary Dependencies**: Click, NumPy, SciPy (`scipy.io.netcdf_file`), all existing; none added

**Storage**: package data (`data/datasets.json`, `maps/recipes/*.toml`); per-user dataset cache;
layout JSON schema 2.0 (unchanged)

**Testing**: pytest (unit, integration, contract), offline (suite-wide socket guard in
`cli/tests/conftest.py`), dataset fixtures via the `fixture_registry` conftest fixture

**Target Platform**: CLI on macOS/Linux

**Project Type**: single project (`cli/`, package `lego_image_processor`)

**Performance Goals**: each ENSO build well under the existing 30 s per recipe budget
(`tests/integration/test_map_performance.py`); per-month files are 134,832 bytes

**Constraints**: offline once cached; fixtures total under the existing 300,000-byte budget
(`tests/integration/test_no_large_data.py`); recipe format stays "1"; existing recipes built
without `--arrangement` give byte-identical layouts (SC-006)

**Scale/Scope**: 2 recipes, 2 registry entries, 2 fixtures, 1 optional recipe key, 3 commands
touched (`map build`, `map check`, `map recipes`), docs (README, runbook)

## Constitution Check

*GATE: checked before Phase 0 and re-checked after Phase 1.*

| Principle | Check |
|---|---|
| I. Kit is a fixed template | Pass: grid, mask and parts unchanged; the board is hung as B, a whole-frame shift the kit allows (feature 007) |
| II. Maps are layers from recipes | Pass: both maps are declarative recipes (land background, ocean `bins` data layer); the default arrangement moves into the recipe so the map is reproducible from the file |
| III. Data in, not pictures | Pass: gridded `ssta` reprojected and classified; color order follows the data (cold to warm, R1) |
| IV. Reproducible data | Pass: two entries pinned by URL, size, SHA-256; citation (Huang et al. 2017 + dataset DOI) and license in outputs; offline once cached; no credentials |
| V. Buildable and honest | Pass: kit colors only (SC-005); extra tiles reported per color by the build report and `parts list --kits 1` (same arithmetic, R5); suitability report runs as for every recipe |
| VI. CLI first | Pass: library (`build_map`, `check_recipe`, `resolve_arrangement`) and CLI; no web work |
| VII. Test first, offline | Pass: tests precede code in every phase; small derived fixtures, no network |
| VIII. LEGO compliance | Pass: disclaimer in both recipe files, all output, fixture `.source.json`, docs |

No violations. Post-design re-check (after data-model and contracts): still no violations; the
format changes are the optional recipe key `arrangement` (approved) and one additive report JSON
field, `arrangement_source`, required by FR-012 (escalated for sign-off; no layout change).

## Project Structure

### Documentation (this feature)

```text
specs/009-enso-sst-maps/
├── spec.md, run-state.md, plan.md, research.md, data-model.md, quickstart.md, tasks.md
├── contracts/
│   ├── recipe-arrangement.md   # recipe key `arrangement` + CLI/library precedence and output
│   ├── datasets.md             # the two registry entries + reader behaviour
│   └── recipes.md              # ocean-el-nino.toml and ocean-la-nina.toml
└── checklists/requirements.md
```

### Source Code (repository root)

```text
cli/src/lego_image_processor/
├── data/datasets.json                    # + ersst-v5-1997-12, ersst-v5-1988-12 (FR-001)
├── datasets/readers.py                   # squeeze size-1 leading axes; netCDF-3 signature check (FR-002, FR-003)
├── maps/recipe.py                        # optional top-level `arrangement` key (FR-010)
├── maps/build.py                         # resolve_arrangement, arrangement_source, read errors (FR-011, FR-012)
├── maps/suitability.py                   # extra_tiles(supply rows) helper (FR-016)
├── maps/recipes/ocean-el-nino.toml       # new (FR-005-FR-009, FR-013)
├── maps/recipes/ocean-la-nina.toml       # new
├── cli/options.py                        # arrangement_option(default=None) for map build/check
└── cli/map.py                            # source in the Arrangement line, °C ranges, extra total, recipes column (FR-012, FR-014, FR-015)
cli/tools/fixtures004/make_fixtures.py    # + make_ersst_month (int16-packed ssta fixtures), --only
cli/tests/
├── conftest.py                           # fixture_registry: the two new entries
├── fixtures/datasets/ersst_v5_199712_ssta.nc (+ .source.json)
├── fixtures/datasets/ersst_v5_198812_ssta.nc (+ .source.json)
├── unit/datasets/test_readers.py         # 4-D squeeze, fill, larger axis error, netCDF-4 rejection
├── unit/datasets/test_registry.py        # new entries
├── unit/maps/test_recipe.py              # `arrangement` key rules
├── unit/maps/test_suitability.py         # extra_tiles
├── unit/maps/test_build_arrangement_source.py   # precedence + source (library)
├── integration/test_map_enso.py          # both maps on fixtures: B, legend, Niño 3.4, bound, parts agreement
└── contract/test_map_enso_contract.py    # CLI output: source, ranges, extra total, recipes column, fetch errors
cli/README.md, docs/runbook.md            # FR-017
```

**Structure Decision**: single project, existing layout. The arrangement default is resolved in
`maps/build.py` (the one place that turns a recipe into a layout), so the CLI and library callers
share one rule. The recipe stores the parsed `Arrangement` (from `layout/arrangement.py`, which
has no dependency on `maps/`, so no import cycle).

## Complexity Tracking

None.

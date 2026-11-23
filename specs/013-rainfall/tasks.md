# Tasks: Rainfall map (013)

**Input**: spec.md, plan.md, research.md, contracts/recipe-and-datasets.md

**Tests**: required (Constitution VII). Each implementation task follows the failing test it makes
pass. All tests offline. Paths under `cli/` unless stated (`src/` = `cli/src/lego_image_processor/`).

## Phase 1: Setup

- [X] T001 Baseline `cd cli && .venv/bin/pytest -q` and web tests (record counts in run-state.md)
- [X] T002 Add h5py to pyproject.toml and web/requirements-build.txt

## Phase 2: Foundational (US2: netCDF-4, multi-file)

- [X] T003 [P] Tests tests/unit/datasets/test_netcdf4.py: regular grid decode (fill, missing, valid range, packing, descending lat), size-1 axes, annual-mean, climatology-mean, netCDF-3 signature rejected, ERSST fixture converted to netCDF-4 reads equal to netCDF-3, polar stereographic inverse vs NSIDC reference points, points grid, multi-file mean (FR-001, FR-002)
- [X] T004 Implement src/datasets/netcdf4.py and SourceGrid.points in src/datasets/grid.py; route in readers.py
- [X] T005 [P] Registry and cache tests tests/unit/datasets/test_multifile.py (multi-file is_cached/verify/resolve/fetch, provenance files_sha256) (FR-003)
- [X] T006 Implement in src/datasets/registry.py and cache.py; dataset CLI rows

## Phase 3: US1/US3 recipe options

- [X] T007 [P] Recipe tests tests/unit/maps/test_rainfall_options.py: sampling, override (region/dataset) and legend rules (FR-004–FR-006)
- [X] T008 Implement in src/maps/recipe.py
- [X] T009 [P] Reprojection tests: bilinear (exact on a linear field, periodic, clamp), points grid cell mean (FR-004)
- [X] T010 Implement in src/maps/reproject.py
- [X] T011 [P] Build tests tests/unit/maps/test_rainfall_options.py: region/dataset overrides, unobserved_lat, order, shadow wins, supply and report, arrangement B = A rolled (FR-005)
- [X] T012 Implement src/maps/overrides.py and wire into src/maps/build.py; CLI legend/overrides in src/cli/map.py

## Phase 4: US1 recipe and data

- [X] T013 Registry entries gpcp-v23-ltm-1991-2020 and nsidc-cdr-v6-seaice-minimum-1991-2020 in data/datasets.json (FR-008)
- [X] T014 Fixtures (make_fixtures.py: GPCP 10°, NSIDC coarsened) with .source.json; conftest FixtureRegistry multi-file (FR-011)
- [X] T015 Recipe maps/recipes/rainfall.toml (FR-007)
- [X] T016 [P] Integration tests/integration/test_rainfall.py and contract tests/contract/test_map_rainfall_contract.py; update bundled-recipe lists in existing tests
- [X] T017 FR-010 regression: every existing recipe identical to main (fixtures, A/B/C)

## Phase 5: US4 web

- [X] T018 web: MAP_IDS, tests (catalog, prebuild, routes), requirements-build

## Phase 6: Polish

- [X] T019 Real-data build: compare with prototype 3A; record agreement, counts, pieces beyond one kit; preview PNG
- [X] T020 Docs: CLAUDE.md/AGENTS.md project section, docs/runbook.md, cli/README.md, docs/deploy.md, datasets.json docs
- [X] T021 Full test suites (CLI, web); run-state.md final

Not affiliated with or endorsed by The LEGO Group.

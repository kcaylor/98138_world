# Tasks: Living planet map (012)

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/recipe-and-datasets.md

**Tests**: required (Constitution VII). Each implementation task follows the failing test it makes
pass. All tests offline. Paths under `cli/` unless stated (`src/` = `cli/src/lego_image_processor/`).

## Phase 1: Setup

- [X] T001 Baseline `cd cli && .venv/bin/pytest -q` (record the count in run-state.md)

## Phase 2: Foundational (readers, registry, cache)

- [X] T002 [P] GeoTIFF tests in tests/unit/datasets/test_geotiff.py: tiny LZW (rows per strip 1 and 3) and uncompressed files written with Pillow + GeoTIFF tags; block 1 and 2 means; valid_max/fill → NaN; scale; lat/lon centres; tiled/BigTIFF/no-georef errors (FR-003)
- [X] T003 Implement src/datasets/geotiff.py `read_geotiff(path, block, scale_factor, add_offset, valid_min, valid_max, fill)` (R1)
- [X] T004 [P] netCDF tests in tests/unit/datasets/test_readers.py: `latitude`/`longitude` names; `climatology-mean` mean, counts, steps, all-NaN pixel; `content_sha256` ignores global attributes and changes with data; log10 transform (FR-004, FR-005, FR-007)
- [X] T005 Implement in src/datasets/readers.py and grid.py (SourceGrid.counts/steps/missing, `extend_latitudes`)
- [X] T006 [P] Registry tests in tests/unit/datasets/test_registry.py: geotiff + block; http_only rules; content_sha256 rules; land_from rules; climatology-mean (FR-002, FR-005, FR-006)
- [X] T007 Implement in src/datasets/registry.py
- [X] T008 [P] Cache tests in tests/unit/datasets/test_cache.py: verify/fetch with content_sha256 (pass, mismatch removes part file), http_only entry fetch via opener (FR-005)
- [X] T009 Implement in src/datasets/cache.py
- [X] T010 [P] land_from tests: reader sets `land` from a mask dataset, extends latitudes; recipe datasets include the mask (FR-006)
- [X] T011 Implement land_from in src/datasets/readers.py and `Recipe.datasets()`

## Phase 3: US2 recipe options (P2, needed by US1)

- [X] T012 [P] Recipe tests in tests/unit/maps/test_recipe_no_data.py: log10 transform and bounds rules; every no_data rule of the contract (FR-007, FR-008)
- [X] T013 Implement in src/maps/recipe.py (`NoData`, `_no_data`, log10 bounds)
- [X] T014 [P] Build tests in tests/unit/maps/test_no_data.py: synthetic grids → unobserved, sparse, share cells; value fill; shadow wins; supply rows count no-data color; provenance/report; arrangement B equals A rolled for per-cell rules (FR-009)
- [X] T015 Implement src/maps/nodata.py and wire into src/maps/build.py; CLI print in src/cli/map.py

## Phase 4: US1 the map (P1)

- [X] T016 Maintainer step (network): fetch both datasets; compute content checksum; write registry rows in src/data/datasets.json (FR-001)
- [X] T017 Fixtures via tools/fixtures004/make_fixtures.py `make_npp`, `make_chla` + `.source.json`; conftest `fixture_registry` rows; raise fixture budget to 450 kB
- [X] T018 [P] Integration test tests/integration/test_living_planet.py: build from fixtures (A and B), colors per part, no-data counts > 0, Black shadow, citations of three datasets, validate passes
- [X] T019 Recipe src/maps/recipes/living-planet.toml (FR-010)
- [X] T020 Contract test: `map build living-planet` output prints the no-data lines and the disclaimer
- [X] T021 Real-data check (maintainer): build, compare with the prototype grid (SC-001), memory (SC-002), counts; record in run-state.md

## Phase 5: US3 web (P3)

- [X] T022 Add `living-planet` to web MAP_IDS; update web tests (variant count 21, fixture prebuild)
- [X] T023 Prebuild real site for living-planet locally; check pages and downloads (SC-004)

## Phase 6: Polish

- [X] T024 Docs: recipe contract (004) pointer, README, docs/deploy.md runbook, docs/vision.md roadmap, CLAUDE.md / AGENTS.md project sections, Dockerfile comment
- [X] T025 Full CLI + web test runs; FR-013 unchanged layouts for existing recipes

Not affiliated with or endorsed by The LEGO Group.

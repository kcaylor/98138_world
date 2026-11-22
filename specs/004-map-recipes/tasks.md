---
description: "Task list for feature 004: Map Recipes and Canonical Datasets"
---

# Tasks: Map Recipes and Canonical Datasets

**Input**: Design documents from `specs/004-map-recipes/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (recipe-format.md,
cli.md, data-files.md, library-api.md), quickstart.md

**Tests**: Required. Constitution VII: each test task is written first and must FAIL before its
implementation task. No test opens the network (offline guard in `cli/tests/conftest.py`) or reads
a downloaded file (FR-025, SC-008).

**Organization**: by user story (US1 = P1 … US5 = P5). Paths relative to the repository root; run
commands from `cli/`.

**User decisions applied** (run-state.md Q1–Q6, answered 2026-11-22): Q1 TOML recipes;
Q2 commands `map build|check|recipes`, `dataset list|fetch|info`, `kit part-colors`, and an opt-in
`map build --fetch` that downloads missing pinned datasets (no download without it); Q3 `metadata.map` inside schema 2.0; Q4 curated `part_colors.json` from pinned catalog
snapshots; Q5 two acceptance tiers (exact; derived ≥ 24%); Q6 local data files allowed with
declared SHA-256, citation and license. Tasks tagged with a Q id follow that answer.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US5 (story phases only)

---

## Phase 1: Setup

- [X] T001 Declare `scipy` (BSD-3-Clause, `^1.11`) as an explicit runtime dependency and include `maps/recipes/*.toml` as package data in `cli/pyproject.toml`; confirm `import scipy.io, scipy.ndimage` works in the test venv (research R5)
- [X] T002 [P] Create packages `cli/src/lego_image_processor/datasets/__init__.py` and `cli/src/lego_image_processor/maps/__init__.py` (empty exports for now) and test dirs `cli/tests/unit/datasets/`, `cli/tests/unit/maps/`, `cli/tests/fixtures/datasets/`, `cli/tests/fixtures/recipes/`

---

## Phase 2: Foundational (blocks every story)

### Tests first

- [X] T003 [P] Unit tests for the cache helper in `cli/tests/unit/datasets/test_cache.py`: root resolution order (`$LEGO_IMAGE_PROCESSOR_CACHE`, `$XDG_CACHE_HOME/lego-image-processor`, `~/.cache/lego-image-processor`), path layout `<root>/datasets/<id>/<version>/<filename>` (data-model.md CachedDataset.path), `verify` re-hashes and raises `ChecksumMismatchError` with expected/actual (data-model.md DatasetEntry.sha256, DatasetEntry.size)
- [X] T004 [P] Unit tests for the registry loader in `cli/tests/unit/datasets/test_registry.py`: shipped `datasets.json` parses; rejects duplicate ids (data-model.md DatasetEntry.id), a `download` entry without https url/size/sha256/filename (DatasetEntry.kind, DatasetEntry.url, DatasetEntry.size, DatasetEntry.sha256), missing license or citation (DatasetEntry.license, DatasetEntry.citation), unknown `format` (DatasetEntry.format) or `class_rule` (DatasetEntry.class_rule)
- [X] T005 [P] Unit tests for readers in `cli/tests/unit/datasets/test_readers.py`: a tiny DODS file written in `tmp_path` (DDS header + `Data:\n` + XDR float32 grid + float64 lat/lon) round-trips; netCDF-3 written with `scipy.io.netcdf_file` (12-month variable with missing values) reduces to an annual mean only where all months are valid (DatasetEntry.variables `reduce`); `.npy` with lat/lon ranges; longitudes 0–360 normalised to −180..180 and lat sorted ascending (data-model.md SourceGrid.lat, SourceGrid.lon); fill values become NaN
- [X] T006 [P] Unit tests for the kit projection in `cli/tests/unit/maps/test_projection.py`: shipped file loads; known points map to expected cells (lon −168.9 → col 0, lon 191.0 wraps, lat 0 → row 42, lat 89.8 → row 0, lat −82 → row 79); points outside rows 0–79 are dropped (data-model.md KitProjection.left_edge_lon, KitProjection.deg_per_col, KitProjection.equator_row, KitProjection.rows_per_radian)
- [X] T007 [P] Unit tests for the recipe parser in `cli/tests/unit/maps/test_recipe.py` using small TOML strings: valid data and background layers parse; each rule of contracts/recipe-format.md "Rules" fails with the key path (data-model.md Recipe.format, Recipe.id, Layer.role, Layer.colors, Layer.weights, Layer.transform, Classification method parameters, Texture kind/parameters); unknown keys fail; `Recipe.sha256` equals the file's SHA-256; part is derived from the layer class (Layer.part_id)
- [X] T008 [P] Unit tests for the part-color loader in `cli/tests/unit/test_part_colors.py`: kit colors are available for their part (White for 6141; the 9 tile colors for 98138); `colors_for_part` rejects an unknown part; rows with null IDs or "estimate/placeholder" notes are rejected; kit rows must equal `kit_colors.json` (data-model.md PartColor.key, PartColor.part_id, PartColor.element_id, PartColor.in_kit, PartColor.citations)
- [X] T009 [P] Unit test for layout provenance round trip in `cli/tests/unit/test_grid.py` (extend): a grid with `map_metadata` writes `metadata.map`, `from_json` keeps it, `schema_version` stays "2.0", and a layout without it still loads (data-model.md MapProvenance; contracts/data-files.md "Layout metadata.map") [Q3]

### Implementation

- [X] T010 Implement `cache_root`, `cached_path`, `is_cached`, `verify` and errors in `cli/src/lego_image_processor/datasets/cache.py` (research R12); change `cli/tools/kit31203/source.py` to import `cache_root` from it (one definition; existing tool tests stay green)
- [X] T011 Write `cli/src/lego_image_processor/data/datasets.json` with the three entries of contracts/data-files.md (values from research R3, R4) and implement `DatasetEntry`, `load_registry`, `get_entry` in `cli/src/lego_image_processor/datasets/registry.py` (data-model.md DatasetEntry.*)
- [X] T012 Implement `SourceGrid` in `cli/src/lego_image_processor/datasets/grid.py` and `read_dods`, `read_netcdf3`, `read_npy`, `read_dataset` in `cli/src/lego_image_processor/datasets/readers.py` (research R3–R5; data-model.md SourceGrid.*); apply `class_rule` to set `SourceGrid.land`
- [X] T013 Implement `KitProjection`, `load_kit_projection` and cell indexing in `cli/src/lego_image_processor/maps/projection.py`, and write `cli/src/lego_image_processor/data/kit_31203_projection.json` with research R2 values and a `source` block (contracts/data-files.md); the file is regenerated by T048
- [X] T014 (after T015) Implement `Recipe`, `Layer`, `Classification`, `Texture`, `RecipeError`, `parse_recipe`, `load_recipe`, `bundled_recipes` in `cli/src/lego_image_processor/maps/recipe.py` with `tomllib` (contracts/recipe-format.md; data-model.md Recipe.*, Layer.*, Classification, Texture) [Q1]
- [X] T015 Implement `PartColor`, `load_part_colors`, `colors_for_part` in `cli/src/lego_image_processor/kit/part_colors.py`; ship an initial `cli/src/lego_image_processor/data/part_colors.json` holding only the kit's 10 colors (copied from `kit_colors.json`, same citations); export from `cli/src/lego_image_processor/kit/__init__.py` (data-model.md PartColor.*)
- [X] T016 Add optional `map_metadata` to `PositionPlacementGrid` (constructor, `to_json` as `metadata.map`, `from_json` preserves it) in `cli/src/lego_image_processor/layout/grid.py` [Q3]

**Checkpoint**: registry, cache, readers, projection, recipe parser, part colors and provenance
work in isolation; full suite green.

---

## Phase 3: User Story 1 - Build the official map from a recipe (P1) MVP

**Goal**: `map build official-31203` reproduces the official design exactly, offline.
**Independent test**: build with an empty cache and no network; compare with
`DesignGrid.to_layout()`; `validate` FULLY BUILDABLE.

### Tests first

- [X] T017 [P] [US1] Unit tests for `categorical` classification and the background layer (single color, weights) in `cli/tests/unit/maps/test_classify.py` (data-model.md Classification `categorical` rules; Layer.weights)
- [X] T018 [P] [US1] Integration test in `cli/tests/integration/test_map_official.py`: `build_map(load bundled official-31203)` with an empty `cache_dir` equals the official design in 10,240/10,240 positions (color_id, part_type, lego_part_id); land = 3,062; two builds identical; `metadata.map` names recipe id, sha256, layer roles, `kit31203-design` citation and license, disclaimer (FR-004–FR-006, FR-012, FR-020, SC-001)
- [X] T019 [P] [US1] Contract tests in `cli/tests/contract/test_map_contract.py`: `map recipes` lists the four bundled ids; `map build official-31203 -o X.json` exit 0, last line disclaimer, `validate X.json` reports FULLY BUILDABLE; `map build bad.toml` (fixtures in `cli/tests/fixtures/recipes/`) exits 1 naming the key path and writes nothing; `map recipes --copy official-31203 DEST` writes the file and refuses to overwrite without `--force` (contracts/cli.md) [Q2]

### Implementation

- [X] T020 [US1] Implement the `kit-design` reader (packaged design grid → categorical SourceGrid on the kit grid, no projection) in `cli/src/lego_image_processor/datasets/readers.py` (DatasetEntry.format `kit-design`)
- [X] T021 [US1] Implement `categorical` and the background single/weighted fill without texture in `cli/src/lego_image_processor/maps/classify.py`
- [X] T022 [US1] Implement `build_map` and `MapResult` in `cli/src/lego_image_processor/maps/build.py`: load mask and projection, per layer obtain values (packaged or cached dataset; raise `DatasetNotCachedError` otherwise), classify, assign part and kit/part-color labels, build `PositionPlacementGrid` with `source_image="recipe:<id>"` and `map_metadata` (data-model.md MapProvenance, MapResult); `agreement_with_official`
- [X] T023 [US1] Write bundled recipe `cli/src/lego_image_processor/maps/recipes/official-31203.toml` (contracts/recipe-format.md "Bundled recipes"), with the disclaimer comment
- [X] T024 [US1] Implement the `map` group with `build` (`-o`, `--report`, `--cache-dir`, `--compare-official`, `-q`; `--preview` is added in T045) and `recipes` (`--copy`, `--force`) in `cli/src/lego_image_processor/cli/map.py`; register in `cli/src/lego_image_processor/cli/main.py` (contracts/cli.md) [Q2]
- [X] T025 [US1] Export the US1 library API from `cli/src/lego_image_processor/maps/__init__.py` (contracts/library-api.md)

**Checkpoint**: MVP. SC-001 passes offline.

---

## Phase 4: User Story 2 - Fetch and cache canonical datasets (P2)

**Goal**: list, fetch (verified), inspect datasets; builds use the cache offline.
**Independent test**: fake opener fetch, then offline build and info.

### Tests first

- [X] T026 [P] [US2] Unit tests for `fetch` in `cli/tests/unit/datasets/test_fetch.py` with an injected fake opener: writes `<filename>.part` then renames after size + SHA-256 match; mismatch deletes the part file and raises with expected/actual; interrupted stream leaves no file; already-cached valid file is not re-downloaded; read-only cache dir fails cleanly (data-model.md CachedDataset state transitions)
- [X] T027 [P] [US2] Contract tests in `cli/tests/contract/test_dataset_contract.py`: `dataset list` (table and `--format json`) shows id, version, size, license, cached; `dataset info etopo2022-surface-10m` shows URL, SHA-256, citation, DOI; `dataset fetch` with a monkeypatched opener exits 0 and prints the citation; checksum mismatch exits 4; network error exits 5; disclaimer last (contracts/cli.md) [Q2]
- [X] T028 [P] [US2] Contract test in `cli/tests/contract/test_map_contract.py` (extend): with an empty `--cache-dir`, `map build ocean-sst -o X` exits 3, prints `dataset fetch ersst-v5-ltm-1991-2020` and `--fetch`, writes nothing, opens no network, and runs in < 2 s; with `--fetch` and a mocked opener the missing dataset is fetched, verified and the build exits 0; with `--fetch` and a bad checksum it exits 4 and writes nothing (FR-010, SC-004, US2 scenarios 5 and 7) [Q2]
- [X] T029 [P] [US2] Integration test in `cli/tests/integration/test_dataset_offline.py`: a fixture file placed in a temp cache with a registry override (monkeypatched entry whose sha256/size match the fixture) builds offline; altering one byte makes the next use fail with the fetch hint (US2 scenarios 4 and 6)

### Implementation

- [X] T030 [US2] Implement `fetch(entry, *, cache_dir=None, opener=None)` with streaming download, size and SHA-256 checks and atomic rename in `cli/src/lego_image_processor/datasets/cache.py` (research R12; FR-008)
- [X] T031 [US2] Implement the `dataset` group (`list`, `fetch ID... | --recipe`, `info`) with exit codes 3/4/5 in `cli/src/lego_image_processor/cli/dataset.py`; register in `cli/src/lego_image_processor/cli/main.py` (contracts/cli.md) [Q2]
- [X] T032 [US2] Map `DatasetNotCachedError` to exit 3 with the fetch command and the `--fetch` hint, and add `map build --fetch` (fetch each missing dataset via `fetch`, exit 4/5 on failure, then build) in `cli/src/lego_image_processor/cli/map.py` [Q2]
- [X] T033 [US2] Export the datasets API from `cli/src/lego_image_processor/datasets/__init__.py` (contracts/library-api.md)

**Checkpoint**: SC-004 passes.

---

## Phase 5: User Story 3 - Ocean maps from data: bathymetry and SST (P3)

**Goal**: reprojection, ordered classification, texture, suitability-in-build, preview;
`official-31203-bathymetry` and `ocean-sst`.
**Independent test**: synthetic fields and the derived fixtures, offline.

### Tests first

- [X] T034 [P] [US3] Unit tests for reprojection in `cli/tests/unit/maps/test_reproject.py`: a synthetic lat/lon field gives the expected cell means; only same-class source values are averaged (land values never enter ocean cells); cells without values are nearest-filled and flagged; within-cell and total variance computed (data-model.md LayerField.*; FR-014)
- [X] T035 [P] [US3] Unit tests for ordered classification in `cli/tests/unit/maps/test_classify.py` (extend): `bins` below/above range clamp and are counted; `quantile` equal counts; `rank` largest-remainder shares; `rank-to-supply` never exceeds one kit's supply and fails when cells exceed total supply; monotonic: a higher value never gets a lower class; ties row-major (data-model.md Classification rules; FR-015)
- [X] T036 [P] [US3] Unit tests for texture in `cli/tests/unit/maps/test_texture.py`: same seed → identical; new seed changes only cells within the blend zone; no move > 1 class; rank methods keep exact counts (pair swaps); `mix` gives exact counts by weight and larger `cluster` gives larger same-color patches (data-model.md Texture.*; FR-017)
- [X] T037 [P] [US3] Unit tests for suitability metrics in `cli/tests/unit/maps/test_suitability.py`: smooth gradient → no detail warning; 1-cell checkerboard → variance lost > 50% warning; filled share > 5% warning; empty class warning; neighbouring colors ΔE00 < 5 warning naming the pair; supply table (data-model.md SuitabilityReport.*; research R8)
- [X] T038 [P] [US3] Unit test for the preview in `cli/tests/unit/maps/test_preview.py`: PNG is 1024×640 (8 px per stud) and each square's RGB equals the cited color RGB (FR-024)
- [X] T039 [US3] Maintainer script `cli/tools/fixtures004/make_fixtures.py` (reads cached ETOPO and ERSST, writes `cli/tests/fixtures/datasets/etopo2022_1deg.npy` int16 block means, `ersst_v5_annual_2deg.nc` netCDF-3, and a `.source.json` beside each with dataset id, source sha256, method, license); run it once and commit the outputs (< 300 KB total) (research R11; FR-025)
- [X] T040 [P] [US3] Integration test in `cli/tests/integration/test_map_bathymetry.py` on the ETOPO fixture (registry entry monkeypatched to format `npy` with the fixture's size and SHA-256, file placed in a temp cache as in T029): land identical to the kit mask (3,062); every ocean color ≤ supply; validator FULLY BUILDABLE; ocean agreement with the official design ≥ the fixture threshold measured in T047 (target 24%) and printed; color median depths follow the recipe order (FR-021, SC-003) [Q5]
- [X] T041 [P] [US3] Integration test in `cli/tests/integration/test_map_sst.py` on the ERSST fixture: classes monotonic in SST before texture; all colors within supply; FULLY BUILDABLE; filled share reported (≈ 4%); build deterministic (US3 scenarios 2, 3, 5)

### Implementation

- [X] T042 [US3] Implement `reproject_layer` (bincount means by class, nearest fill with `scipy.ndimage.distance_transform_edt`, variance terms) in `cli/src/lego_image_processor/maps/reproject.py`
- [X] T043 [US3] Implement `bins`, `quantile`, `rank`, `rank-to-supply` in `cli/src/lego_image_processor/maps/classify.py` (supply from `load_kit_specification()`)
- [X] T044 [US3] Implement `apply_texture` (`blend` with pair swaps for rank methods; `mix` with Gaussian-smoothed noise ranked by weight) in `cli/src/lego_image_processor/maps/texture.py` (research R7)
- [X] T045 [US3] Implement `write_preview` in `cli/src/lego_image_processor/maps/preview.py` and wire `--preview` in `cli/src/lego_image_processor/cli/map.py`
- [X] T046 [US3] Implement `SuitabilityReport` and per-layer metrics in `cli/src/lego_image_processor/maps/suitability.py`; `build_map` attaches the report and `map build` prints warnings, supply table and (`--report`) JSON with citations and disclaimer (FR-019)
- [X] T047 [US3] Write bundled recipes `cli/src/lego_image_processor/maps/recipes/official-31203-bathymetry.toml` (rank with the official counts, research R1 color order, blend 0.25) and `ocean-sst.toml` (rank-to-supply, cold → warm, blend 0.25); measure agreement on the real cached ETOPO and on the fixture, record both in `specs/004-map-recipes/research.md` R1 and set the fixture threshold in T040 to the measured fixture value minus 1 point (never above the measured value) [Q5]
- [X] T048 [US3] Add `fit-projection [--check] [--dataset PATH]` to `cli/tools/kit31203/__main__.py` (new module `cli/tools/kit31203/projection_fit.py`) reproducing research R2 from the cached ETOPO file and writing `kit_31203_projection.json`; unit test on a synthetic mask in `cli/tests/unit/tools/test_projection_fit.py`

**Checkpoint**: SC-002 (three recipes), SC-003, SC-006 on cached data.

---

## Phase 6: User Story 4 - Land elevation map with verified plate colors (P4)

**Goal**: cited part-color table beyond the kit; `land-elevation` recipe; `kit part-colors`.
**Independent test**: elevation fixture build; validate lists non-kit plates without error.

### Tests first

- [X] T049 [P] [US4] Unit tests for the part-color maintainer tool in `cli/tests/unit/tools/test_partcolors.py` using tiny synthetic `elements.csv`/`colors.csv`/LDConfig/BrickLink snippets in `tmp_path`: builds rows only when every ID resolves; excludes and reports incomplete rows; kit colors equal `kit_colors.json`; `--check` reports "no differences" on an unchanged build (data-model.md PartColor.*) [Q4]
- [X] T050 [P] [US4] Integration test in `cli/tests/integration/test_map_elevation.py` on the ETOPO fixture: every land position uses a 6141 color from `part_colors.json`; classes monotonic in elevation before texture; ocean background colors within supply; `validate` exit 0 and lists the non-kit plate colors as `color_unavailable` (US4 scenarios 1, 3)
- [X] T051 [P] [US4] Contract test in `cli/tests/contract/test_kit_contract.py` (extend): `kit part-colors --part 6141` lists LEGO/BrickLink/Rebrickable names and IDs, element ID, kit marker; `--format json` parses; disclaimer last; recipe naming a color not available for its part fails naming color and part (US4 scenarios 2, 4) [Q2]

### Implementation

- [X] T052 [US4] Implement maintainer tool `cli/tools/partcolors/` (`__main__.py` `build [--check] [--snapshot-dir]`): pins snapshot SHA-256s, joins Rebrickable elements/colors with LDraw LEGO IDs and BrickLink IDs (003 sources), reconciles the 6141/4073 part number noted in research R9, writes `cli/src/lego_image_processor/data/part_colors.json` for the reviewed color list [Q4]
- [X] T053 [US4] Run the tool and commit `part_colors.json` with the plate colors of research R9 (rows with any unresolved ID dropped and logged in run-state.md); snapshots stay in the cache, not the repository
- [X] T054 [US4] Add `kit part-colors` to `cli/src/lego_image_processor/cli/kit.py` (contracts/cli.md) [Q2]
- [X] T055 [US4] Write `cli/src/lego_image_processor/maps/recipes/land-elevation.toml` (bins in metres over the verified plate colors; ocean `mix` background within supply); adjust the color list so the suitability check reports neighbouring ΔE00 ≥ 5 and no empty class on the real data
- [X] T056 [US4] Make generated layouts label non-kit colors with `part_colors.json` names and LEGO IDs in `cli/src/lego_image_processor/maps/build.py`; confirm `validate` needs no change (spec Clarifications)

**Checkpoint**: SC-002 (four recipes), SC-009.

---

## Phase 7: User Story 5 - Suitability check before building (P5)

**Goal**: standalone `map check` with full report.
**Independent test**: synthetic recipes with expected warnings.

- [X] T057 [P] [US5] Contract tests in `cli/tests/contract/test_map_contract.py` (extend): `map check` on a recipe over a fine checkerboard `.npy` local fixture (Q6) prints the detail warning and exits 0; `--report` JSON has recipe id, thresholds, citations, licenses and `disclaimer` (US5 scenarios 1–5) [Q2][Q6]
- [X] T058 [P] [US5] Unit tests for local datasets in recipes in `cli/tests/unit/maps/test_recipe.py` (extend): `[ocean.local]` requires path, format, sha256, variable, citation, license; a wrong sha256 fails; relative paths resolve against the recipe file (contracts/recipe-format.md `local`) [Q6]
- [X] T059 [US5] Implement local dataset references in `cli/src/lego_image_processor/maps/recipe.py` and `build.py` (data-model.md DatasetEntry.kind `local`) [Q6]
- [X] T060 [US5] Implement `check_recipe` in `cli/src/lego_image_processor/maps/suitability.py` and the `map check` command in `cli/src/lego_image_processor/cli/map.py` [Q2]

---

## Phase 8: Polish & cross-cutting

- [X] T061 [P] Extend `cli/tests/contract/test_disclaimer.py` to every new command (human output last line; JSON `disclaimer`) (FR-023)
- [X] T062 [P] Performance test in `cli/tests/integration/test_map_performance.py`: each bundled recipe on fixtures builds in < 30 s (expected < 5 s) (SC-006)
- [X] T063 [P] Test in `cli/tests/integration/test_reference_consistency.py` (extend): every color in every bundled recipe resolves to a cited entry with LEGO, BrickLink and Rebrickable IDs; each bundled recipe's datasets exist in the registry; registry downloads total < 15 MB (SC-005, SC-009)
- [X] T064 [P] Test that no file under `cli/` larger than 1 MB is a dataset and that fixtures carry `.source.json` in `cli/tests/integration/test_no_large_data.py` (FR-025)
- [X] T065 Update `cli/README.md` (map/dataset commands, recipe format, datasets with licenses and citations; note that 002's shadowing is replaced by the recipe texture rule, FR-018) and the 004 row of `docs/vision.md` if wording changes; keep both disclaimers
- [X] T066 Run `specs/004-map-recipes/quickstart.md` end to end with real cached datasets; record results (agreements, sizes, timings) in `specs/004-map-recipes/run-state.md`
- [X] T067 Run the full suite (`pytest -q`) with and without network blocked; confirm 436 existing tests still pass

---

## Dependencies & execution order

- Setup (T001–T002) → Foundational (T003–T016) → stories.
- US1 (T017–T025) needs Foundational only. MVP.
- US2 (T026–T033) needs Foundational; T032 touches the US1 `map` command.
- US3 (T034–T048) needs US1 (build pipeline) and US2 (cache) ; T039 needs the real datasets in a
  maintainer cache (one-time, outside tests); T047 needs T039.
- US4 (T049–T056) needs US3 (reprojection, bins, texture `mix`).
- US5 (T057–T060) needs US3 (suitability metrics).
- Polish after all stories.

## Parallel examples

- Foundational tests T003–T009 in parallel; then T010–T016 (T015 before T014, which validates colors against part colors; T010 before T030).
- US3 tests T034–T038 in parallel; T040/T041 after T039.
- US4 T049–T051 in parallel.

## Implementation strategy

1. MVP: Setup + Foundational + US1 → official map exact, offline (SC-001).
2. Add US2 (datasets) → US3 (ocean data maps, derived acceptance) → US4 (elevation, part colors) →
   US5 (standalone check) → Polish.
3. Q1–Q6 confirmed by the user on 2026-11-22.

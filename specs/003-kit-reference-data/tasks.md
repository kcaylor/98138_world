---
description: "Task list for feature 003: Kit Reference Data for LEGO World Map 31203"
---

# Tasks: Kit Reference Data for LEGO World Map 31203

**Input**: Design documents from `/specs/003-kit-reference-data/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (cli.md, data-files.md,
library-api.md, maintainer-tool.md), quickstart.md

**Tests**: Required. Constitution VII (test-first, offline) applies: every test task below is
written first and must FAIL before the matching implementation task starts. All tests run with no
network and no PDF (FR-022, SC-007); pypdf-dependent tests use `pytest.importorskip("pypdf")`.

**Organization**: Tasks are grouped by user story (US1 = P1, US2 = P2, US3 = P3). Paths are relative
to the repository root; run commands from `cli/` unless stated.

**Resolved decisions applied** (plan.md "Resolved", run-state.md Decisions): E1 add `kit inventory`
and `kit colors`; E2 layouts use `6141` (land) / `98138` (ocean), inventory records `design_id` and
all `part_ids`; E3 synthetic test fixtures only, no crops of LEGO instruction images; E4 statistics
key `land_brick_count` → `land_plate_count` (and `color_frequency_by_part_type.brick` → `.plate`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1, US2, US3 (story phases only)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: dependency groups, test paths and empty packages.

- [X] T001 Add optional Poetry group `[tool.poetry.group.maintainer]` (`optional = true`) with `pypdf = ">=5"` and add `pythonpath = ["tools"]` to `[tool.pytest.ini_options]` in `cli/pyproject.toml`; confirm `poetry install` (without `--with maintainer`) does not install pypdf (FR-004, research R7)
- [X] T002 [P] Create the maintainer tool package skeleton `cli/tools/kit31203/__init__.py` and `cli/tools/kit31203/__main__.py` (Click group with `extract` and `review` stubs; `__main__` inserts `cli/tools` on `sys.path`), outside `src/` so it is never packaged (contracts/maintainer-tool.md)
- [X] T003 [P] Create the library package skeleton `cli/src/lego_image_processor/kit/__init__.py` exporting the names listed in contracts/library-api.md (stubs raising `NotImplementedError`)
- [X] T004 [P] Create test directories `cli/tests/unit/tools/__init__.py` and `cli/tests/fixtures/kit31203/` (empty `README.md` stating fixtures are factual data or synthetic, never LEGO artwork, per research R10)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: provenance block shared by every reference file, and the PDF source cache and adapter
that both US1 (inventory) and US2 (design) extraction use.

**⚠️ CRITICAL**: no user story work begins until this phase is complete.

### Tests (write first, must fail)

- [X] T005 [P] Unit tests for the provenance block in `cli/tests/unit/test_kit_source.py`: parse/serialize `SourceDocument` and `Citation`; reject a `sha256` that is not 64 hex chars or differs from the pinned value; reject a missing `disclaimer`; `generated_on` must be YYYY-MM-DD (data-model.md `SourceDocument.sha256`, `SourceDocument.generated_on`, `SourceDocument.disclaimer`, `SourceDocument.citations`)
- [X] T006 [P] Unit tests for download/cache/checksum in `cli/tests/unit/tools/test_source_cache.py` with a mocked opener and `tmp_path` (no network): cache root resolution order `$LEGO_IMAGE_PROCESSOR_CACHE` → `$XDG_CACHE_HOME/lego-image-processor` → `~/.cache/lego-image-processor`; download streams to `.part` and renames only after the checksum passes; an interrupted download leaves no file marked complete (exit code 3 path); a checksum mismatch deletes the `.part` file and raises an error naming expected and actual digests (exit code 4 path); a cached file is re-hashed on every use; `--pdf PATH` is still verified (FR-001, spec Edge Cases, US2-6, research R8)
- [X] T007 [P] PDF adapter tests in `cli/tests/unit/tools/test_pdf_adapter.py` (skip without pypdf): build a tiny synthetic PDF in the test with pypdf containing positioned text and one JPEG XObject drawn under a `cm` matrix inside a Form XObject; assert words come back as `(x, y, text)` and image placements as `(page, name, w, h, x, y, scale)` (research R1, R4, R7)

### Implementation

- [X] T008 Implement `SourceDocument` and `Citation` (dataclasses, `from_dict`/`to_dict`, pinned URL and SHA-256 constants, disclaimer constant) in `cli/src/lego_image_processor/kit/source.py` (data-model.md `SourceDocument.title`, `SourceDocument.url`, `SourceDocument.sha256`, `SourceDocument.pages`, `SourceDocument.generated_on`, `SourceDocument.generator`, `SourceDocument.citations`, `SourceDocument.disclaimer`; `Citation`)
- [X] T009 Implement download, cache and SHA-256 verification with the standard library in `cli/tools/kit31203/source.py` (raises typed errors mapped to exit codes 3 and 4 in contracts/maintainer-tool.md)
- [X] T010 Implement the pypdf adapter (page words with positions via `extract_text(visitor_text=...)`; image XObjects with pixel size, raw JPEG bytes and placement tracked through `q`/`Q`/`cm` and Form XObject matrices) in `cli/tools/kit31203/pdf_adapter.py`; this is the only module that imports pypdf
- [X] T011 Implement deterministic JSON writing (2-space indent, trailing newline, stable key order, `generated_on` from `--date`) and the all-or-nothing writer (write to a temp dir, move into `--out-dir` only when every step passes) in `cli/tools/kit31203/assemble.py` (contracts/data-files.md header rules, research R9)

**Checkpoint**: provenance type, cache and adapter pass their tests.

---

## Phase 3: User Story 1 - Verified kit inventory and correct land part (Priority: P1) 🎯 MVP

**Goal**: the package ships a cited 32-line inventory and a cited 10-color table, exposes them via
library and `kit` CLI, and land is part 6141 / "plate" everywhere with layout schema 2.0.

**Independent Test**: load the shipped inventory and check it against
`cli/tests/fixtures/kit31203/page159_words.json`: every element ID, quantity and color matches,
every entry has a source page; `git grep` finds no `3062b` or land `"brick"` outside specs 001/002
(quickstart §2).

### Tests for User Story 1 (write first, must fail)

- [X] T012 [P] [US1] Commit the factual fixture `cli/tests/fixtures/kit31203/page159_words.json` (count tokens `\d+x` and element ID tokens with x/y coordinates for page 159, transcribed from research R1; no images) and `cli/tests/fixtures/kit31203/inventory_expected.json` (the 32 element/quantity pairs from research R1)
- [X] T013 [P] [US1] Pairing tests in `cli/tests/unit/tools/test_inventory_pairing.py`: the fixture yields exactly 32 pairs equal to `inventory_expected.json`, total 11,694; a count with no ID below it, an ID used twice, |Δx| ≥ 3 pt or Δy ≥ 20 pt each raise a pairing error (exit code 9 path); joining a pair whose element is missing from `part_catalog.json` raises (research R1; data-model.md `KitElement.element_id`, `KitElement.quantity`)
- [X] T014 [P] [US1] Loader tests for the color table in `cli/tests/unit/test_kit_colors.py`: 10 rows, keys unique, exactly 1 `land` and 9 `ocean`, `lego.id` unique, every LEGO/BrickLink/Rebrickable name and ID non-null, every citation id resolves to `source.citations`, no row marked estimate or placeholder, no network used (US1-3; data-model.md `KitColor.key`, `KitColor.role`, `KitColor.lego`, `KitColor.bricklink`, `KitColor.rebrickable`, `KitColor.citations`, `KitColor.element_id`); a malformed copy in `tmp_path` raises `ValueError` naming the file and rule
- [X] T015 [P] [US1] Loader tests for the inventory in `cli/tests/unit/test_kit_inventory.py`: matches `inventory_expected.json` line for line (SC-002); every line has `source_page == 159` and a `citation`; exactly one `land` element (614101, `design_id` "6141", `part_ids` ["6141","4073"], White, 3064); nine `ocean` elements, all with `part_ids` containing "98138" and "35381", nine distinct `color_key`s; one `section_base` (6302092, 40); map elements `metadata_verified` true; 4121715 and 4160228 `metadata_verified` false with role `frame_other`; `supplied(color_key)`, `by_role`, `land_element`, `ocean_elements` helpers; `load_kit_inventory("999")` raises `UnsupportedKitError` (US1-1, US1-2; data-model.md `KitElement.role`, `KitElement.design_id`, `KitElement.part_ids`, `KitElement.color`, `KitElement.color_key`, `KitElement.metadata_verified`, `KitElement.source_page`, `KitInventory`)
- [X] T016 [P] [US1] Rewrite `cli/tests/unit/test_kit_spec.py` for the rebuilt spec: `land_part_id == "6141"`, `ocean_part_id == "98138"`, `available_colors_plate == ["lego_white"]`, 9 `available_colors_tile`, quantities equal the inventory, `is_plate_color_available`, `get_plate_quantity`, no `brick` attribute remains (data-model.md `KitSpecification`)
- [X] T017 [P] [US1] Update `cli/tests/unit/test_position.py` and `cli/tests/unit/test_land_sea_mask.py` to expect `part_type` "plate" / `lego_part_id` "6141" for land and "tile"/"98138" for ocean, and that any other pairing is rejected (data-model.md `PositionPlacement.part_type`, `PositionPlacement.lego_part_id`)
- [X] T018 [P] [US1] Update `cli/tests/unit/test_grid.py`: default `schema_version == "2.0"`; statistics key `land_plate_count`; `color_frequency_by_part_type` keys `plate`/`tile`; `metadata.disclaimer` present; `from_json` raises `LayoutSchemaError` for "1.0" and for a missing version, with a message naming the found version and the `layout` regenerate command (FR-009, US3-4; data-model.md `PositionPlacementGrid.schema_version`, Layout state transition)
- [X] T019 [P] [US1] Add legacy fixture `cli/tests/fixtures/layouts/legacy_v1_layout.json` (small schema 1.0 layout with land `brick`/`3062b`; this is the only allowed non-spec occurrence of the old values, listed as an exclusion in the T034 grep test)
- [X] T020 [P] [US1] Contract tests for the `kit` CLI in `cli/tests/contract/test_kit_contract.py`: `kit inventory` table columns and footer (32 lines, 11,694 pieces, source URL + SHA-256); `--role land` filters; `kit colors` columns; `--format json` output equals the package data file content; `--kit 999` exits 1 with the unsupported-kit message; last line of human output is the disclaimer (contracts/cli.md `kit` group, FR-021)
- [X] T021 [P] [US1] Update `cli/tests/contract/test_layout_contract.py` and `cli/tests/integration/test_layout_pipeline.py` for schema 2.0: `land_plate_count == 3062`, summary line `Land plates (6141): 3,062 (29.9%)`, CSV land rows `plate,6141`, JSON `schema_version "2.0"` and `disclaimer` (contracts/cli.md `layout`, US1-4)
- [X] T022 [P] [US1] Palette test in `cli/tests/unit/test_palette_loader.py`: Bright Bluish Green (id 107, `#008F9B`) is present and every kit color `lego.id` is in the palette with a unique RGB (data-model.md cross-file rule 5)

### Implementation for User Story 1

- [X] T023 [P] [US1] Curate `cli/tools/kit31203/part_catalog.json`: one entry per page-159 element (design ID, all part numbers, description, LEGO color name, `verified`, citation `brickset`), with 4121715 and 4160228 recorded per research R1 as `verified: false` and a note that the element ID differs from Brickset (feeds data-model.md `KitElement.design_id`, `KitElement.part_ids`, `KitElement.description`, `KitElement.color`, `KitElement.metadata_verified`, `KitElement.citation`)
- [X] T024 [P] [US1] Curate `cli/src/lego_image_processor/data/kit_colors.json` with the 10 rows of research R3 in the shape of contracts/data-files.md (land first, then ocean by descending kit quantity; `rgb` from Rebrickable; `source.generator` "curated by hand"; citations ldraw, bricklink, rebrickable, brickset with URLs and access dates) ; `source` also carries the pinned `title`, `url`, `sha256` and `pages: [159]` (element ↔ color cross-checked on page 159, research R2) so cross-file rule 4 holds (FR-003, FR-006; data-model.md `KitColor.key`, `KitColor.lego`, `KitColor.bricklink`, `KitColor.rebrickable`, `KitColor.rgb`, `KitColor.role`, `KitColor.element_id`, `KitColor.citations`, `KitColor.notes`, `SourceDocument.sha256`, `SourceDocument.pages`)
- [X] T025 [P] [US1] Add `{"id": 107, "name": "Bright Bluish Green", "rgb": [0,143,155], "hex": "#008F9B"}` with a Rebrickable citation note to `cli/src/lego_image_processor/palette/lego_colors.json`; do not change other colors' RGB (contracts/library-api.md "Changed: palette")
- [X] T026 [US1] Implement pure pairing of count and element ID words and the join with `part_catalog.json` in `cli/tools/kit31203/inventory.py` (research R1; makes T013 pass)
- [X] T027 [US1] Wire the inventory stage into `extract` in `cli/tools/kit31203/__main__.py` (resolve PDF via T009, read page-159 words via T010, pair via T026, validate the colors file against the inventory, write `kit_31203_inventory.json` via T011 with `source.pages == [159]`; exit 9 on pairing failure) (contracts/maintainer-tool.md steps 1, 2, 5)
- [X] T028 [US1] Implement `KitColor`, `CatalogColor` and cached `load_kit_colors()` with on-load validation in `cli/src/lego_image_processor/kit/colors.py` (data-model.md `KitColor.key`, `KitColor.lego`, `KitColor.bricklink`, `KitColor.rebrickable`, `KitColor.rgb`, `KitColor.role`, `KitColor.element_id`, `KitColor.citations`, `KitColor.notes` and the KitColor validation rules; contracts/library-api.md)
- [X] T029 [US1] Implement `KitElement`, `KitInventory` (with `land_element`, `ocean_elements`, `by_role`, `supplied`), `UnsupportedKitError` and cached `load_kit_inventory()` with on-load validation in `cli/src/lego_image_processor/kit/inventory.py` (data-model.md `KitElement.element_id`, `KitElement.quantity`, `KitElement.source_page`, `KitElement.design_id`, `KitElement.part_ids`, `KitElement.description`, `KitElement.color`, `KitElement.color_key`, `KitElement.role`, `KitElement.metadata_verified`, `KitElement.citation`, `KitInventory` and the KitElement validation rules)
- [X] T030 [US1] **Maintainer run (inventory)**: with `poetry install --with maintainer`, run `poetry run python -m kit31203 extract` against the cached, checksum-verified PDF; confirm the output reports 32 lines and 11,694 pieces and that `cli/src/lego_image_processor/data/kit_31203_inventory.json` matches `inventory_expected.json`; commit the generated file (US2 adds the design stage and re-runs; see T057)
- [X] T031 [US1] Rebuild `LEGOWorldMapKitSpecification` and `load_kit_specification()` from the inventory, color table and mask in `cli/src/lego_image_processor/layout/kit_spec.py` (plate/tile fields and methods; no quantities stored in kit_spec) (data-model.md `KitSpecification`)
- [X] T032 [US1] Change land to `plate`/`6141` in `cli/src/lego_image_processor/layout/position.py`, `cli/src/lego_image_processor/layout/land_sea_mask.py` and `cli/src/lego_image_processor/layout/generator.py` (enforce plate↔6141, tile↔98138) (FR-008, FR-020 part labels; data-model.md `PositionPlacement.part_type`, `PositionPlacement.lego_part_id`)
- [X] T033 [US1] Implement schema 2.0 in `cli/src/lego_image_processor/layout/grid.py`: `CURRENT_SCHEMA_VERSION = "2.0"`, `LayoutSchemaError(ValueError)` raised by `from_json` for any other or missing version, `land_plate_count`, `color_frequency_by_part_type` keys `plate`/`tile`, `metadata.disclaimer` (FR-009, E4; data-model.md `PositionPlacementGrid.schema_version`)
- [X] T034 [P] [US1] Add a repository grep test `cli/tests/integration/test_no_legacy_land_part.py` that fails if `3062b`, `land_brick` or a land part type `"brick"` appears in `cli/src`, `cli/tests` (excluding `fixtures/layouts/legacy_v1_layout.json` and this test), `cli/README.md`, `README.md` or `docs/` (US1-5, SC-006)
- [X] T035 [US1] Rename brick → plate in the validator's part lookups (`is_plate_color_available`, `get_plate_quantity`, `available_colors_plate`) in `cli/src/lego_image_processor/layout/validator.py`, and in the kit summary of `cli/src/lego_image_processor/cli/validate.py` (`Plate colors: 1`, `Tile colors: 9`, `Inventory: 32 lines, cited from instructions page 159`); behavior change of the suggestion is US3 (contracts/cli.md `validate`)
- [X] T036 [US1] Update layout summary lines and disclaimer output in `cli/src/lego_image_processor/cli/layout.py` (`Land plates (6141)`, `Ocean tiles (98138)`, disclaimer as last line) (contracts/cli.md `layout`, FR-021)
- [X] T037 [US1] Implement `kit inventory` and `kit colors` (`--kit`, `--format table|json`, `--role`) in `cli/src/lego_image_processor/cli/kit.py` and register the group in `cli/src/lego_image_processor/cli/main.py` (contracts/cli.md, E1)
- [X] T038 [US1] Regenerate `cli/tests/fixtures/layouts/expected_test_128x80.json` and `cli/tests/fixtures/layouts/expected_test_128x80.csv` as schema 2.0 with the layout command, and update remaining brick references in `cli/tests/contract/test_validate_contract.py`, `cli/tests/integration/test_validation_pipeline.py` and `cli/tests/unit/test_generator.py` and `cli/tests/unit/test_validator.py`
- [X] T039 [US1] Relabel `cli/tests/fixtures/lego_world_map_colormap.json`: replace the ad hoc `color_legend` labels with kit color keys from `kit_colors.json` (e.g. "White brick (land)" → `lego_white`), keeping the grid values; update any reader (FR-011)
- [X] T040 [US1] Remove `cli/src/lego_image_processor/data/lego_world_map_kit.json` and every reference to it (FR-010)
- [X] T041 [P] [US1] Update `cli/README.md` (land is a 1x1 round plate, part 6141; ocean 1x1 round tile 98138; layout schema 2.0 and rejection of 1.0; `kit` commands; disclaimer) (FR-008, FR-009 "format change MUST be documented")

**Checkpoint**: `poetry run pytest` passes; `kit inventory` and `kit colors` work offline; no legacy land part outside allowed files.

---

## Phase 4: User Story 2 - Official design as a named-color grid, mask derived from it (Priority: P2)

**Goal**: the maintainer extraction produces the committed 128×80 design grid with 40 cited
sections, regenerates the mask from it, records mask changes and per-color spares.

**Independent Test**: from the committed design grid, count positions per color (each ≤ supplied);
regenerate the mask and confirm it equals the shipped mask with the change record listing any
differences (quickstart §3).

### Tests for User Story 2 (write first, must fail)

- [X] T042 [P] [US2] Commit the factual fixture `cli/tests/fixtures/kit31203/placements.json` (measured panel and section placements for at least pages 22, 26, 66 and 132, from research R5) and a synthetic placement list covering all 40 pinned pages
- [X] T043 [P] [US2] Section-mapping tests in `cli/tests/unit/tools/test_section_mapping.py`: column origins derived from the three panel placements; `(col,row)` from placement equals the page-order position for all 40 (data-model.md `Section.col`, `Section.row`, `Section.order_check`); a page with no section image or with two, or a missing pinned page, fails naming the pages (exit 5, US2-2, FR-013); a placement > 3 pt from a slot or disagreeing with page order fails (exit 6); 154×153 and 154×154 accepted, overview sizes (247×247, 132×132) excluded (data-model.md `Section.image_size`, `Section.page`)
- [X] T044 [P] [US2] Synthetic section image helper `cli/tests/unit/tools/synthetic_sections.py`: render a 16×16 color grid with the reference render colors as studs into 154×154 or 154×153 RGB, add noise and JPEG compression (E3, research R10)
- [X] T045 [P] [US2] Classification tests in `cli/tests/unit/tools/test_classify.py` using T044: cell centres use the image's own w/h; median 5×5 sampling; every cell of a clean synthetic section classified correctly; a cell painted halfway between two blues is flagged ambiguous (ratio > threshold); an ambiguous cell without an override fails (exit 7 with the first 20 positions); an override for a non-ambiguous cell that contradicts it without `force: true` fails; CIEDE2000 from `core.color_quantizer.delta_e_2000` is used (FR-016, research R6; data-model.md `DesignGrid.classification`, `Override`)
- [X] T046 [P] [US2] Assembly tests in `cli/tests/unit/tools/test_assemble.py`: 40 synthetic sections assemble into a 128×80 grid with `rows[y][x]` base-36 palette indices; counts `used/supplied/spare` with `spare_note "unexplained"`; a color with used > supplied fails (exit 8); the mask derived from white cells and the change record against a previous mask list `(x, y, old, new)`; any failing step writes no outputs into `--out-dir`; `--check` exits 0 on identical output and 1 with the first differing keys otherwise, ignoring only `generated_on` (US2-1, US2-3, US2-4, SC-008; data-model.md `DesignGrid.width`, `DesignGrid.height`, `DesignGrid.palette`, `DesignGrid.rows`, `ColorCount.spare`, `MaskChangeRecord`, `LandSeaMask`)
- [X] T047 [P] [US2] Loader tests in `cli/tests/unit/test_official_design.py`: `load_official_design()` returns 128×80, exactly 10 distinct keys, Σused = 10,240, 40 sections with unique `(col,row)` and pages equal to the pinned list, `flagged == resolved`, `color_at`, `land_positions()`; malformed copy raises `ValueError` naming the rule (US2-5, SC-003, SC-004; data-model.md `DesignGrid.*`, `Section.*`)
- [X] T048 [P] [US2] Cross-file consistency tests in `cli/tests/integration/test_reference_consistency.py` implementing data-model.md rules 1–5: color element in inventory with matching name/role; design used ≤ supplied and counts agree with both files; mask land count and coordinates equal design white cells and inventory land quantity − spare; all files share `source.sha256`; palette contains every kit `lego.id` (FR-023)
- [X] T049 [P] [US2] Update `cli/tests/unit/test_land_sea_mask.py` for the new `source` block and `derived_from` (loader reads `source.url`/`source.generated_on`; tests pin the new form) (contracts/data-files.md mask section)

### Implementation for User Story 2

- [X] T050 [P] [US2] Commit `cli/tools/kit31203/reference_colors.json` (one reference render RGB per kit color key, derived once by the seeded k-means pass in research R6, with a note of how it was derived)
- [X] T051 [US2] Implement section finding and `(col,row)` mapping (pure, over adapter placements) in `cli/tools/kit31203/sections.py` with the pinned 40-page list from spec Clarifications (FR-013, research R4, R5; data-model.md `Section.col`, `Section.row`, `Section.page`, `Section.image_size`, `Section.placement`, `Section.order_check`)
- [X] T052 [US2] Implement cell sampling, CIEDE2000 classification against `reference_colors.json`, ambiguity flagging and override application in `cli/tools/kit31203/classify.py` (research R6; data-model.md `DesignGrid.classification`, `Override`)
- [X] T053 [US2] Implement design, mask, mask change record and counts assembly in `cli/tools/kit31203/assemble.py` (contracts/data-files.md shapes for `kit_31203_design.json`, `lego_world_map_land_sea_mask.json`, `kit_31203_mask_changes.json`; data-model.md `DesignGrid.width`, `DesignGrid.height`, `DesignGrid.palette`, `DesignGrid.rows`, `DesignGrid.sections`, `DesignGrid.overrides`, `DesignGrid.counts`, `DesignGrid.classification`, `ColorCount.spare`, `MaskChangeRecord`, `LandSeaMask`)
- [X] T054 [US2] Extend `extract` in `cli/tools/kit31203/__main__.py` with steps 3–5 (sections, classify, assemble), the `--check` and `--report` options and the full exit-code table, and implement `review` (PNG contact sheet written outside the repository by default, plus an overrides JSON stub) (contracts/maintainer-tool.md)
- [X] T055 [US2] Implement `Section`, `DesignGrid` (`color_at`, `counts`, `sections`, `land_positions`) and cached `load_official_design()` with on-load validation in `cli/src/lego_image_processor/kit/design.py` (data-model.md `DesignGrid.width`, `DesignGrid.height`, `DesignGrid.palette`, `DesignGrid.rows`, `DesignGrid.sections`, `DesignGrid.counts`, `DesignGrid.classification`, `Section.col`, `Section.row`, `Section.page`, `Section.image_size`, `Section.order_check`; `to_layout()` is added in US3, T066)
- [X] T056 [US2] Update `cli/src/lego_image_processor/layout/land_sea_mask.py` to read the new `source` block and `derived_from`, accepting the old string form only for the date during the transition (contracts/data-files.md; data-model.md `LandSeaMask`)
- [X] T057 [US2] **Maintainer run (full extraction)**: run `poetry run python -m kit31203 review` and resolve every flagged position in `cli/tools/kit31203/overrides.json` (including Earth Blue at (0, 32) per research R6), recording reason, `decided_by` and `decided_on`; then run `poetry run python -m kit31203 extract`; commit the generated `kit_31203_design.json`, `kit_31203_inventory.json` (unchanged from T030), `kit_31203_mask_changes.json`, regenerated `lego_world_map_land_sea_mask.json` and `overrides.json`. Do not commit the review sheet (FR-012, FR-014, FR-016)
- [X] T058 [US2] **Verify the generated data**: run `poetry run python -m kit31203 extract --check` and confirm exit 0 ("no differences", SC-008); confirm the run summary shows 40 sections, `flagged == resolved`, every `spare ≥ 0`, White used 3,062 / supplied 3,064, and the mask change count; record the SHA-256 of each generated data file and the per-color used/supplied/spare table in `specs/003-kit-reference-data/run-state.md`; run `extract --pdf <a non-matching file>` and confirm exit 4 with expected/actual checksums and no files written (US2-6)
- [X] T059 [US2] If the mask change record is non-empty, update affected test expectations (land counts, `expected_test_128x80.*`, contract tests) and list the changes in `specs/003-kit-reference-data/run-state.md` (FR-014)
- [X] T060 [P] [US2] Write `specs/003-kit-reference-data/projection-notes.md` from research R12 plus latitudes of identifiable features measured on the committed grid (FR-017)

**Checkpoint**: `poetry run pytest` passes offline including `test_reference_consistency.py`; `extract --check` exits 0.

---

## Phase 5: User Story 3 - Validation and layout generation use the corrected data (Priority: P3)

**Goal**: `validate` and `layout` report against the real kit: per-part colors, real quantities,
CIEDE2000 suggestions, schema 1.0 rejection, disclaimer everywhere.

**Independent Test**: the official design as a layout validates as fully buildable; a non-kit
ocean color and an overused color are each reported against the real inventory (quickstart §4).

### Tests for User Story 3 (write first, must fail)

- [X] T061 [P] [US3] Validator unit tests in `cli/tests/unit/test_validator.py`: an ocean position with a non-kit color yields a `ColorUnavailableViolation` naming the color, part `tile (98138)`, position count and a suggestion chosen by CIEDE2000 among the 9 ocean colors only (never `lego_white`); a land position with a non-white color suggests only `lego_white`; overuse yields a `QuantityExceededViolation` with required, available and shortfall from the inventory; `ValidationReport.to_dict()` has `disclaimer` (US3-2, US3-3, FR-018, FR-019)
- [X] T062 [P] [US3] Contract tests in `cli/tests/contract/test_validate_contract.py`: `validate legacy_v1_layout.json` exits 1 with the schema 1.0 message (US3-4); color detail line `Suggested alternative: <kit color> (ΔE00 x.x)`; quantity lines `Required/Available/Shortfall`; report JSON `disclaimer` and `part_type` plate/tile; disclaimer is the last line (contracts/cli.md `validate`, FR-021, US3-5)
- [X] T063 [P] [US3] Integration test in `cli/tests/integration/test_validation_pipeline.py`: `load_official_design().to_layout()` written to JSON and validated reports 100% buildable with zero violations (US3-1, SC-005); a layout built from it with one ocean cell changed to a non-kit color and one with an extra Earth Blue cell report exactly those violations
- [X] T064 [P] [US3] Generator tests in `cli/tests/unit/test_generator.py`: generated positions carry kit color keys as `color_id` and plate/6141, tile/98138 labels (FR-020)

### Implementation for User Story 3

- [X] T065 [US3] Replace Euclidean nearest color with CIEDE2000 (`core.color_quantizer.delta_e_2000`, `palette.converter.rgb_to_lab`) restricted to the affected part's kit colors, report ΔE00, check quantities from the inventory, and add `disclaimer` to `ValidationReport.to_dict()` in `cli/src/lego_image_processor/layout/validator.py` (contracts/library-api.md)
- [X] T066 [US3] Add `DesignGrid.to_layout()` returning a schema 2.0 `PositionPlacementGrid` with `source_image="official-31203-design"` in `cli/src/lego_image_processor/kit/design.py` (data-model.md `PositionPlacementGrid.schema_version`, `PositionPlacement.part_type`, `PositionPlacement.lego_part_id`)
- [X] T067 [US3] Update `cli/src/lego_image_processor/cli/validate.py`: catch `LayoutSchemaError` and exit 1 with its message; color and quantity detail lines; `Land plates`/`Ocean tiles` loading summary; disclaimer as last line (contracts/cli.md `validate`)
- [X] T068 [US3] Ensure the layout generator labels positions with kit color names from `kit_colors.json` and corrected parts in `cli/src/lego_image_processor/layout/generator.py` (FR-020)

**Checkpoint**: all three stories pass independently; quickstart §4 commands behave as documented.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T069 [P] Disclaimer audit test `cli/tests/contract/test_disclaimer.py`: `layout`, `validate`, `kit inventory`, `kit colors` human output ends with the disclaimer; their JSON outputs and every data file's `source.disclaimer` carry it (FR-021, constitution VIII)
- [X] T070 [P] Offline guard: add a `conftest.py` fixture in `cli/tests/conftest.py` that blocks `socket.socket.connect` for the whole suite, and confirm the suite passes without the PDF and without pypdf installed (SC-007)
- [X] T071 [P] Remove the "not yet verified (feature 003)" caveat for part IDs and kit inventory from `CLAUDE.md` and any matching note in `README.md`/`docs/`, replacing it with a pointer to the cited data files
- [X] T072 Run every command in `specs/003-kit-reference-data/quickstart.md` and record results in `specs/003-kit-reference-data/run-state.md`
- [X] T073 Run `cd cli && poetry run pytest` (with and without `--with maintainer`) and fix any failure
- [X] T074 [P] Guard FR-002: add `*.pdf` to the repository `.gitignore`, and add `cli/tests/integration/test_no_pdf_shipped.py` asserting no `.pdf` file is tracked by git or present under `cli/src/lego_image_processor/` (so none is packaged) (FR-002)

---

## Dependencies & Execution Order

### Phase dependencies

- Setup (Phase 1) → Foundational (Phase 2) → US1 → US2 → US3 → Polish.
- **US2 depends on US1**: it names cells with `kit_colors.json` keys, checks supply against the
  inventory, and extends the `extract` command built in T027.
- **US3 depends on US1** (plate/tile kit spec, schema 2.0) **and US2** (`DesignGrid` for SC-005).
  T061, T062 and T064 can start right after US1; T063 and T066 need T055 and T057.

### Within each story

- Test tasks first; confirm they fail; then implementation.
- Pure logic (T026, T051, T052, T053) before CLI wiring (T027, T054).
- Curated data (T023, T024, T050) before maintainer runs (T030, T057).
- Maintainer run T057 before verification T058; T058 before T059.

### Parallel opportunities

- Phase 1: T002, T003, T004.
- Phase 2 tests: T005, T006, T007.
- US1 tests: T012–T022 all [P]; then T023, T024, T025 in parallel; T034 and T041 in parallel with the code tasks.
- US2 tests: T042–T049 all [P]; T050 and T060 in parallel with the code tasks.
- US3 tests: T061–T064 all [P].

### Parallel example: User Story 1

```text
T013 test_inventory_pairing.py | T014 test_kit_colors.py | T015 test_kit_inventory.py |
T016 test_kit_spec.py | T018 test_grid.py | T020 test_kit_contract.py
then: T023 part_catalog.json | T024 kit_colors.json | T025 lego_colors.json
```

## Implementation Strategy

1. **MVP (US1)**: Phases 1–3. Delivers the cited inventory and color table, the `kit` commands, and
   the corrected land part with schema 2.0. Stop and validate with quickstart §2.
2. **US2**: adds the official design, the regenerated mask and the reproducibility check.
3. **US3**: switches validation to the real kit and proves SC-005 on the official design.
4. **Polish**: disclaimer audit, offline guard, caveat removal, quickstart run.

Not affiliated with or endorsed by The LEGO Group.

## Phase 7: Convergence

- [X] T075 Add a loader timing test in `cli/tests/integration/test_reference_consistency.py`: cold `load_kit_inventory()`, `load_kit_colors()` and `load_official_design()` (caches cleared) together finish in < 100 ms per plan: Performance Goals (partial)

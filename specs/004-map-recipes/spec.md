# Feature Specification: Map Recipes and Canonical Datasets

**Feature Branch**: `004-map-recipes`

**Created**: 2026-11-22

**Status**: Implemented (the six reserved decisions Q1–Q6 were answered by the user on 2026-11-22;
see Clarifications and `run-state.md`)

**Input**: User description: "Feature 004: map recipes and canonical datasets. A map is a land
layer plus an ocean layer on the fixed 31203 template. Each layer is data-driven (gridded field,
classification, ordered LEGO color scale) or background (fixed treatment). A declarative recipe
fully describes a map and produces a layout that `validate` accepts. The tool downloads canonical
public datasets, pinned and cached, with citation and license carried into outputs, and works
offline once cached. Reprojection uses the kit's projection. A texture rule replaces 002's
shadowing. A suitability check warns about lost detail and whether the colors can carry the
pattern. First examples, which are the acceptance tests: the official 31203 design as a recipe,
an ocean sea surface temperature map, and a land elevation map." (scoping taken from
`docs/vision.md` and the user's brief of 2026-11-22; see run-state.md)

## Context

Features 001–003 built image quantization, layout generation and validation, and cited kit
reference data (parts inventory, 10 kit colors, the official design as a 128×80 grid of named
colors). Constitution v2.0.0 (principles II–V) now requires that every map is built from data
through a declarative recipe, that the official design is reproducible as a recipe, and that
datasets are pinned, cached and cited. Nothing in the CLI reads gridded data today.

Three measured facts shape this feature (details in `research.md`):

1. **The kit's projection.** Fitting the kit's land/sea mask against real land (ETOPO 2022) gives
   an equirectangular (plate carrée) grid whose left edge is at about 168.9° W, with 2.8125° of
   longitude per column and about 2.18° of latitude per row, the equator near row 42.2. It matches
   the kit's land/sea mask in 94.2% of cells (Miller cylindrical 90.9%, Mercator 87.0%).
2. **The official ocean is only partly bathymetry.** Its 9 tile colors follow depth loosely
   (shallow: Earth Blue, Brick Yellow; deep: Bright Bluish Green, Bright Green, Medium Azur) but
   are mixed like a texture. The best possible color-per-cell rule from depth alone agrees with
   the official design in about 33% of ocean cells (in-sample upper bound); a depth ranking that
   reproduces the official color counts agrees in 25–27%; a random shuffle of the official colors
   agrees in 16%. An exact reproduction from real bathymetry is therefore not achievable, and
   "reproduced" needs two tiers (FR-020, FR-021).
3. **Colors beyond the kit.** The kit has one land color (White plate) and nine ocean tile colors.
   A land elevation map needs plate colors the kit does not contain; they must be verified and
   cited before a recipe can use them (constitution V).

## Clarifications

### Session 2026-11-22

- Q: Does `validate` need to change to accept layouts with plate colors outside the kit? → A: No. It already loads any schema 2.0 layout, exits 0, and reports non-kit colors as `color_unavailable` (parts beyond the kit), which is the intended message; feature 005 turns that into a top-up list (auto-resolved: `cli/src/lego_image_processor/layout/validator.py`, `cli/validate.py` exit behaviour).
- Q: What color keys do non-kit colors use in layouts? → A: The existing convention `lego_<snake_case LEGO name>` used by `kit_colors.json` and the palette (auto-resolved: `kit/colors.py` key rule, `validator._make_color_id`).
- Q: How can texture keep "rank-to-supply" within supply? → A: For `rank-to-supply`, texture swaps cells in pairs across a class boundary, so class counts never change; for other methods texture may change counts and the supply comparison is made after texture (auto-resolved: FR-015/FR-017 consistency; constitution V buildability).
- Q: Are cell means weighted by area? → A: No. All registry sources are regular latitude-longitude grids, and each kit cell spans at most about 2.2° of latitude, so the area change inside one cell is under 4% away from the poles; plain means of the source values are used and the choice is recorded in the projection notes (auto-resolved: research R2/R3 measurements).
- Q: Which elevation surface is used over Greenland and Antarctica? → A: The ice surface (ETOPO 2022 "surface" variant), so ice sheets read as high ground, which matches the official white land there (auto-resolved: research R3).
- Q: How does a source say which values are land and which are ocean? → A: Per dataset entry: elevation datasets split at 0 m (land > 0, ocean ≤ 0); SST datasets have missing values on land. The registry records the rule per dataset (auto-resolved: research R3/R4).
- Q: Which colors does the preview PNG use? → A: Each color's cited RGB (`kit_colors.json` or the part-color table), one 8×8-pixel square per stud, with no decoration (auto-resolved: 003 `rgb` fields; FR-024 says the preview is not a build sheet).
- Q: How is progress reported? → A: Like the existing commands: human-readable lines on stdout, `-q` for quiet, JSON written only to files (auto-resolved: `cli/layout.py`, `cli/validate.py`).
- Q: What scoping answers were used, since the fallback drafting path normally asks four questions? → A: The user's brief of 2026-11-22 and `docs/vision.md` (outcome: maps from recipes, official map as the reference test; scope: datasets, reprojection, classification, texture, suitability and three examples; constraints: offline tests, cited colors, pinned data; priority: official map first) (auto-resolved: brief; recorded in run-state.md).

Reserved decisions (run-policy), answered by the user on 2026-11-22:

- Q: Recipe file format? → A: TOML, read with the standard library `tomllib` (user).
- Q: May a build download data? → A: Only when asked: `map build --fetch` downloads missing pinned datasets before building; without `--fetch`, a build with a missing dataset fails with a message naming `dataset fetch <id>` and `--fetch`. Other commands never use the network except `dataset fetch` (user).
- Q: Where does map provenance go in a layout? → A: A new `metadata.map` block; the layout schema stays 2.0 (user).
- Q: How are colors beyond the kit verified? → A: A curated, committed `part_colors.json` built by a maintainer tool from checksum-pinned Rebrickable catalog files, with LEGO and BrickLink IDs cited as in feature 003 (user).
- Q: What does "reproduced" mean for the official design? → A: Two tiers: exact 10,240/10,240 for `official-31203`; the derived bathymetry recipe keeps land identical, stays within kit supply and agrees in at least 24% of ocean cells (user).
- Q: May recipes point at local data files? → A: Yes, when the recipe declares the file's SHA-256, citation and license (user).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build the official map from a recipe (Priority: P1)

A maker runs one command on the bundled recipe `official-31203` and gets a layout file identical,
cell for cell, to the official kit design. The recipe describes the map in the same terms as any
other map: a white background land layer and an ocean layer whose data is the official design's
color grid, classified one-to-one onto the kit's tile colors. The layout passes `validate` as
fully buildable with one kit, and it records the recipe, its sources and the disclaimer.

**Why this priority**: it is the reference acceptance test of constitution principle II and the
smallest slice that proves the whole recipe-to-layout path (recipe file, layer roles, mask,
classification, color scale, layout output, provenance) without any download.

**Independent Test**: run the build on `official-31203` with no network and no cache; compare the
layout with the official design and run `validate` on it.

**Acceptance Scenarios**:

1. **Given** a fresh install with no cache and no network, **When** the maker builds
   `official-31203`, **Then** a schema 2.0 layout is written whose 10,240 positions equal the
   official design's colors, part types and part IDs exactly.
2. **Given** that layout, **When** the maker runs `validate`, **Then** it reports FULLY BUILDABLE
   with 0 violations.
3. **Given** that layout, **When** the maker reads its metadata, **Then** it names the recipe (id,
   version, file checksum), each layer's role and data source with citation and license, and the
   disclaimer "Not affiliated with or endorsed by The LEGO Group."
4. **Given** a recipe with an error (unknown key, a color not available for the layer's part,
   class bounds out of order, a missing layer), **When** the maker builds it, **Then** the command
   fails before writing anything and names the field and the problem.
5. **Given** the same recipe built twice, **When** the two layouts are compared, **Then** their
   positions are identical (builds are deterministic).

---

### User Story 2 - Fetch and cache canonical datasets (Priority: P2)

A maker lists the canonical datasets the tool knows, sees each one's size, version, license and
citation, and fetches one. The file is downloaded once from its pinned address, checked against
its pinned checksum and kept in the user cache. After that every command that uses it works
offline. A recipe that needs a dataset that is not cached says which one and how to fetch it, and
`map build --fetch` fetches it on request.

**Why this priority**: every data-driven map (stories 3 and 4) depends on it, and constitution IV
makes pinning, caching, offline use and attribution mandatory.

**Independent Test**: with a mocked download source, fetch a registered dataset, check that the
cache holds a verified file, then cut the network and confirm that `dataset info` and a build use
the cached copy.

**Acceptance Scenarios**:

1. **Given** the registry, **When** the maker lists datasets, **Then** each entry shows id,
   title, version, size, license, citation, and whether it is cached.
2. **Given** a dataset not yet cached, **When** the maker fetches it, **Then** it is downloaded,
   its SHA-256 matches the pinned value, and it is stored in the user cache.
3. **Given** a download whose checksum does not match, **When** the fetch finishes, **Then** the
   file is discarded, nothing is left in the cache, and the error shows the expected and actual
   checksums.
4. **Given** a cached dataset, **When** the maker builds a recipe that uses it with the network
   unavailable, **Then** the build succeeds.
5. **Given** a recipe whose dataset is not cached, **When** the maker builds it without
   `--fetch`, **Then** the command fails without using the network, names the dataset id, the
   exact fetch command and the `--fetch` option, and writes nothing.
6. **Given** a cached file that was altered on disk, **When** it is next used, **Then** the
   checksum check fails and the maker is told to fetch again.
7. **Given** a recipe whose dataset is not cached, **When** the maker builds it with `--fetch`,
   **Then** the dataset is downloaded and verified as in scenario 2 and the build then runs.

---

### User Story 3 - Ocean maps from data: bathymetry and sea surface temperature (Priority: P3)

A maker builds two bundled ocean recipes. `official-31203-bathymetry` derives the official map's
look from real bathymetry: depth is reprojected onto the kit grid, ranked into the kit's nine tile
colors in the official design's proportions, and textured. `ocean-sst` maps the annual mean sea
surface temperature onto an ordered cold-to-warm scale of the nine kit tile colors. Both keep the
official white land as background, and each build prints a suitability report.

**Why this priority**: it exercises reprojection, classification, ordered color scales, the
texture rule and the suitability check on real data, using only kit colors, so both maps can be
built from one kit's parts where the supply allows.

**Independent Test**: build both recipes from small synthetic or downsampled test fixtures with no
network; check class order, texture determinism, supply limits and the suitability report. With
the real cached datasets, check the agreement figures in SC-003.

**Acceptance Scenarios**:

1. **Given** cached bathymetry, **When** the maker builds `official-31203-bathymetry`, **Then**
   land equals the official land exactly, every ocean color count is within the kit's supply,
   `validate` reports FULLY BUILDABLE, and the build reports the cell agreement with the official
   design.
2. **Given** cached SST data, **When** the maker builds `ocean-sst`, **Then** warmer cells never
   get a colder class than cooler cells before texture, the scale runs from the coldest to the
   warmest color named in the recipe, and the suitability report is shown.
3. **Given** a recipe whose classification is "rank to supply", **When** it is built, **Then** no
   color is used more times than the kit supplies it.
4. **Given** a texture rule with a seed, **When** the recipe is built twice, **Then** the outputs
   are identical; **When** the seed changes, **Then** only cells within the texture's blend zone
   change.
5. **Given** kit ocean cells where the data has no ocean value (coast mismatch or data gap),
   **When** the map is built, **Then** those cells take the value of the nearest ocean data cell
   and the suitability report counts them.

---

### User Story 4 - Land elevation map with verified plate colors (Priority: P4)

A maker builds the bundled recipe `land-elevation`: land shows elevation on an ordered scale of
1×1 round plate colors (low greens through tans and browns to white), and the ocean is a
background of kit tile colors with subtle shading. Every plate color the recipe uses is listed in
a cited table of colors in which the land part is made. The suitability report and `validate`
show which pieces go beyond one kit.

**Why this priority**: it is the third example and the first map whose land is data-driven. It
depends on a verified, cited table of part colors beyond the kit, which is new reference data.

**Independent Test**: build `land-elevation` from a downsampled fixture; check that every land
color is in the part-color table with cited IDs, that the class order follows elevation, and that
`validate` lists the non-kit plate colors as needing parts beyond the kit.

**Acceptance Scenarios**:

1. **Given** cached elevation data, **When** the maker builds `land-elevation`, **Then** every land
   position uses a plate color from the part-color table, and higher cells never get a lower class
   than lower cells before texture.
2. **Given** a recipe that names a color not available for its layer's part, **When** it is
   built, **Then** it fails and names the color and part.
3. **Given** the elevation layout, **When** the maker runs `validate`, **Then** the file is
   accepted and the report lists the non-kit plate colors and quantities beyond the kit (no crash,
   no unknown-color error).
4. **Given** the part-color table, **When** the maker lists colors for a part, **Then** each entry
   shows its LEGO, BrickLink and Rebrickable names and IDs and its citation.

---

### User Story 5 - Suitability check before building (Priority: P5)

A maker who is designing a new recipe runs a check without writing a layout. The report says how
much of the data's variation survives at the kit's grid scale, how much of each layer had to be
filled from neighbouring cells, how many cells each class gets, whether neighbouring colors on the
scale are distinguishable, and how the color counts compare with one kit's supply. Warnings are
explicit; a recipe with warnings still builds.

**Why this priority**: constitution V requires a suitability check for every map. The check runs
inside every build from story 3 on; this story adds the standalone command and the full report for
recipe authors.

**Independent Test**: run the check on synthetic fields (smooth gradient, fine checkerboard,
political-map-like patches) and confirm the expected warnings.

**Acceptance Scenarios**:

1. **Given** a smooth field, **When** checked, **Then** no detail warning is raised.
2. **Given** a field whose variation is mostly finer than one grid cell, **When** checked, **Then**
   a detail-loss warning is raised with the measured share of variation lost.
3. **Given** a color scale with two neighbouring colors closer than the distinguishability
   threshold, **When** checked, **Then** a warning names the pair and their color difference.
4. **Given** a classification that leaves a class empty, **When** checked, **Then** a warning names
   the class.
5. **Given** any check, **When** the report is written as JSON, **Then** it carries the recipe id,
   dataset citations and licenses, and the disclaimer.

### Edge Cases

- A dataset's longitudes run 0–360 instead of −180–180, or latitudes run south to north: the
  reprojection handles both.
- The grid's top row reaches about 89.8° N and the bottom row about 82° S; data sources that stop
  short of a row (for example SST beyond the sea ice) leave cells that are filled from the nearest
  valid cell and counted in the suitability report.
- A dataset value is a fill or missing value: it is excluded from cell averages.
- A class bin receives no cells: the map still builds; the suitability check warns.
- A layer's data falls outside the recipe's class bounds: values below the first bound go to the
  first class and above the last bound to the last class; the count is reported.
- A recipe uses "rank to supply" but asks for more cells than all its colors' supply together:
  the build fails and says by how many.
- The cache directory is read-only or the disk is full: the fetch fails cleanly and leaves no
  partial file.
- A download is interrupted: a partial file is never used; the next fetch starts over.
- A recipe from a newer recipe format version: rejected with a message naming the supported
  version.
- Two recipes with the same id in the bundled set: rejected when the recipe list is loaded.

## Requirements *(mandatory)*

### Functional Requirements

**Recipes**

- **FR-001**: A map MUST be described by a recipe file that names: an id, title and recipe format
  version; the land layer and the ocean layer, each with a role of `data` or `background`; for a
  data layer, its dataset, the variable, any value transform (for example depth as the negative of
  elevation), the classification, the ordered color scale and the texture rule; for a background
  layer, its colors, their weights and the texture rule. Recipe files are TOML (Q1).
- **FR-002**: Recipes MUST be validated before any work: unknown keys, missing layers, a layer
  with the wrong role fields, colors not available for the layer's part (FR-016), class bounds not
  strictly increasing, a number of classes different from the number of colors, and unknown
  dataset ids MUST each fail with the field path and the problem.
- **FR-003**: The package MUST ship the bundled recipes `official-31203`, `official-31203-bathymetry`,
  `ocean-sst` and `land-elevation`, and a maker MUST be able to list them and copy one to start a
  new recipe.
- **FR-004**: Building a recipe MUST write a layout in the existing layout schema 2.0 that
  `validate` loads without error, with land on the land part (6141 plate) and ocean on the ocean
  part (98138 tile) at exactly the kit mask's positions.
- **FR-005**: The layout MUST record the map's provenance: recipe id, recipe format version, the
  recipe file's SHA-256, each layer's role, dataset id, version, citation and license, the texture
  seed, and the disclaimer. It is an additional `metadata.map` block inside schema 2.0
  layouts; existing readers ignore it (Q3).
- **FR-006**: Builds MUST be deterministic: the same recipe, datasets and tool version give
  identical positions.

**Datasets**

- **FR-007**: The package MUST ship a dataset registry. Each entry has an id, title, publisher,
  version, source URL, exact byte size, SHA-256, file format, variable names, grid description,
  license and citation (with DOI where one exists).
- **FR-008**: Fetching MUST download to a temporary file, verify size and SHA-256, and only then
  move the file into the cache. A mismatch MUST delete the temporary file and report the expected
  and actual checksums.
- **FR-009**: The cache MUST live in the per-user cache directory already used by feature 003
  (`$LEGO_IMAGE_PROCESSOR_CACHE`, else `$XDG_CACHE_HOME/lego-image-processor`, else
  `~/.cache/lego-image-processor`), and MUST be overridable per command.
- **FR-010**: A cached file MUST be checksum-verified before use. Commands MUST NOT touch the
  network unless the maker asked to fetch (`dataset fetch`, or `map build --fetch`, which downloads
  the recipe's missing pinned datasets, verified as in FR-008, before building). Without `--fetch`,
  a build with a missing dataset MUST fail before writing anything, naming the dataset and both
  ways to get it: `dataset fetch <id>` and `--fetch` (Q2).
- **FR-011**: The registry MUST include a bathymetry/elevation dataset and an SST dataset, both
  openly licensed, each under 20 MB, and each resolving at least one value per kit grid cell.
- **FR-012**: The official design grid MUST be available to recipes as a packaged (no-download)
  categorical dataset on the kit grid.

**Reprojection, classification, color and texture**

- **FR-013**: The kit grid's projection MUST be stored as versioned package data citing how it was
  derived: equirectangular, left edge longitude, degrees per column, equator row and rows per
  radian, with the measured mask agreement of the chosen and the rejected models.
- **FR-014**: Reprojection MUST compute each kit cell's value as the mean of the valid source
  values whose centers fall in that cell, using only source values of the layer's own class (land
  values for the land layer, ocean values for the ocean layer) where the source says which is
  which. Kit cells with no such value MUST take the value of the nearest valid cell, and their
  count MUST be reported.
- **FR-015**: Classification MUST support: explicit bounds (`bins`), equal-count classes
  (`quantile`), classes with given shares by rank (`rank`), counts limited by one kit's supply of each color (`rank-to-supply`), and one-to-one
  category mapping (`categorical`). For every ordered method, a higher value MUST never get a lower
  class than a lower value, before texture.
- **FR-016**: A recipe MUST only use colors available for its layer's part: the kit's colors, plus
  colors in a cited part-color table that lists, for each color, the part, LEGO, BrickLink and
  Rebrickable names and IDs and the element ID, each with its citation.
  The table is curated and committed, built from checksum-pinned catalog snapshots (Q4).
- **FR-017**: The texture rule MUST be deterministic for a given seed and MUST support: for data
  layers, mixing a cell with the neighbouring class when its value is within a blend fraction of a
  class boundary (softening steps); for background layers, mixing a set of colors by weights with
  optional spatial clustering so a uniform area does not look flat. A texture that would move a
  cell more than one class away MUST NOT exist. With `rank-to-supply`, texture MUST swap cells in pairs across a
  class boundary so class counts do not change.
- **FR-018**: The existing `layout` command's "shadowing" story from feature 002 is replaced by
  this texture rule; no separate shadowing option is added.

**Suitability**

- **FR-019**: Every build and the standalone check MUST report, per data layer: share of the
  field's variance lost below grid scale; share of cells filled from neighbours; cells per class;
  the smallest color difference (CIEDE2000) between neighbouring scale colors; and color counts
  against one kit's supply. Warnings MUST be raised when variance lost exceeds 50%, filled cells
  exceed 5% of the layer, a class is empty, or neighbouring colors differ by less than ΔE00 5
  (thresholds recorded in the report).

**Acceptance against the official design**

- **FR-020** (exact tier): building `official-31203` MUST reproduce the official design exactly
  (10,240 of 10,240 positions: color, part type and part ID).
- **FR-021** (derived tier): building `official-31203-bathymetry` from the registry's bathymetry
  MUST give: land identical to the kit mask; every ocean color count within the kit's supply;
  `validate` FULLY BUILDABLE; ocean cell agreement with the official design of at least 24% (the
  measured figure for a depth ranking is 25–27%; a random shuffle of the official colors gives
  16%); and the nine colors' median depths in the same order as in the official design. The build
  MUST print the measured agreement. (two tiers, Q5)

**Commands and outputs**

- **FR-022**: All capabilities MUST be available as library functions and as CLI commands on local
  files. Command set: `map build` (with `--fetch`), `map check`, `map recipes`, `dataset list`,
  `dataset fetch`, `dataset info`, `kit part-colors` (Q2).
- **FR-023**: All human-readable output of the new commands MUST end with "Not affiliated with or
  endorsed by The LEGO Group." and JSON outputs MUST carry it in a `disclaimer` field; layout CSV
  output stays as it is (user decision recorded in feature 003).
- **FR-024**: `map build` MUST optionally write a preview PNG of the layout (one pixel or one
  square per stud) so a maker can see the map before building.
- **FR-025**: No test may use the network; dataset tests MUST use small fixtures or mocks, and
  committed fixtures MUST be small derived grids, never the downloaded files.

### Key Entities

- **Recipe**: id, title, format version, description, land layer, ocean layer, optional texture
  seed. Identified by its id; its file checksum is recorded in outputs.
- **Layer**: class (land or ocean), role (data or background), part (derived from the class),
  dataset reference, variable, transform, classification, color scale, texture rule.
- **Classification**: method (`bins`, `quantile`, `rank`, `rank-to-supply`, `categorical`) and
  its parameters (bounds, shares, category map).
- **Color scale**: ordered list of color keys, each available for the layer's part.
- **Texture rule**: kind (`blend` for data layers, `mix` for backgrounds), blend fraction or color
  weights, clustering scale, seed.
- **Dataset entry**: id, title, publisher, version, URL, size, SHA-256, format, variables, grid,
  license, citation, DOI.
- **Cached dataset**: a verified local copy of a dataset entry.
- **Kit projection**: model, parameters, derivation source and measured agreements.
- **Part color**: part, color key, LEGO/BrickLink/Rebrickable names and IDs, element ID, RGB,
  citations.
- **Suitability report**: per-layer metrics, warnings, thresholds, recipe id, citations,
  disclaimer.
- **Map provenance**: the block written into the layout (FR-005).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `official-31203` builds offline on a fresh install and matches the official design in
  10,240 of 10,240 positions; `validate` reports FULLY BUILDABLE.
- **SC-002**: Each of the four bundled recipes builds, and its layout loads in `validate` without
  error (exit 0).
- **SC-003**: `official-31203-bathymetry` built from the registry bathymetry has land identical to
  the kit (3,062 positions), every ocean color within supply, ocean cell agreement ≥ 24% with the
  official design, and the official median-depth order of the nine colors.
- **SC-004**: With datasets cached and the network disabled, every bundled recipe builds; with a
  dataset missing and the network disabled, the build fails within 2 seconds with the fetch
  command.
- **SC-005**: The two downloads needed for all bundled recipes total under 15 MB.
- **SC-006**: A build of any bundled recipe from cached data completes in under 30 seconds on a
  laptop.
- **SC-007**: Every layout and suitability report names the citation and license of each dataset it
  used and carries the disclaimer.
- **SC-008**: The full test suite passes with no network access and no downloaded files.
- **SC-009**: Every color used by a bundled recipe resolves to a cited entry (kit color table or
  part-color table) with LEGO, BrickLink and Rebrickable IDs.

## Assumptions

- The user's brief and `docs/vision.md` answer the specification's scoping questions (outcome,
  scope, constraints, priority); no separate scoping round was held (recorded in run-state.md).
- The kit's projection is an equirectangular grid fitted to the kit mask (research R2). The fit is
  good to about one row; the kit's own mask always decides which cells are land and ocean.
- Parts lists, wanted lists and kit top-up quantities are feature 005; this feature only reports
  color counts against one kit's supply.
- Build sheets are feature 006; the preview PNG is not a build sheet.
- Datasets are climatologies or static grids; time series, animations and user-uploaded rasters in
  arbitrary formats are out of scope. A recipe may also point to a local file in a
  supported format with a declared citation, license and SHA-256 (Q6).
- The legacy image path (`quantize`, `layout`) keeps working unchanged (constitution III makes it a
  secondary input).
- Only kit 31203 is supported as the template.
- Not affiliated with or endorsed by The LEGO Group.

# Feature Specification: Living planet map (land NPP, ocean chlorophyll)

**Feature Branch**: `012-living-planet`

**Created**: 2026-11-22

**Status**: Clarified (autonomous mode, 2026-11-22)

**Input**: Owner-approved design (prototyped over five rounds; the approved image is the
prototype's `round5/A5.png`), relayed by the coordinating session on 2026-11-22: a "Living
planet" map with plant productivity on land and ocean chlorophyll at sea. Design details, data
sources and prototype counts are summarised below and in `research.md`; the prototype material is
outside the repository (read-only).

## Context

A new bundled recipe, `living-planet`, shows where the planet is green:

- **Land** (1×1 round plates, part 6141): MODIS MOD17A3 annual net primary production (NPP),
  NTSG (University of Montana), mean 2000–2015, Collection 5.5, in g C m⁻² yr⁻¹, on six plate
  colors. Land with no NPP value (deserts, rock, ice, urban) counts as NPP 0. A kit land cell is
  White (ice) if more than half of its land is unvegetated and poleward of 55° (Antarctica lies
  outside the NPP file and is unvegetated by this rule).
- **Ocean** (1×1 round tiles, part 98138): MODIS-Aqua chlorophyll-a (NASA OBPG R2022.0, served by
  NOAA CoastWatch ERDDAP `erdMH1chlamday_R2022SQ`), 2013–2024 climatology = the mean over every
  valid month in each pixel, classified on log10 into five tile colors. Polar ocean that the
  satellite never (or hardly ever) saw is sea ice and takes White tiles.
- **Land shadow**: Black tiles one stud east of land (existing `[shadow] color` option).
- Default arrangement A.

The prototype's final grid (round 5) is the acceptance reference: the recipe built from the same
data must agree with it cell for cell as closely as the general implementation allows.

## Clarifications

### Session 2026-11-22 (autonomous)

- Q: Where do the chlorophyll bin bounds live when classification is on log10? → A: In the
  recipe, in the variable's own units (mg m⁻³); with `transform = "log10"` they are compared on
  log10 and reported in mg m⁻³ (auto-resolved: owner design "bins in mg m⁻³ … classify on log10";
  prototype RECIPE-NOTES §3).
- Q: How is the ERDDAP data pinned, given ERDDAP builds files on request? → A: One ERDDAP request
  for all 2013–2024 months at stride 12 (≈0.5°), pinned by URL, size and a SHA-256 over the decoded
  data (the variable and its coordinate arrays as stored), not over the file bytes: ERDDAP writes
  the request time into the global `history` attribute, so the file bytes change on every request
  (verified 2026-11-22). (agent decision: the constitution requires a checksum and offline,
  cached, cited data; a content checksum is the only stable one without hosting a derived file.)
- Q: The NPP host serves HTTP only. → A: The registry accepts an `http` URL only for an entry that
  states why (`http_only`) and pins size and SHA-256; integrity comes from the checksum (agent
  decision; recorded for owner review).
- Q: How does the NPP layer know which pixels are land, given the file stores ocean and barren
  land alike as fill? → A: The NPP registry entry takes its land/ocean split from another pinned
  dataset (`class_rule.land_from`: ETOPO 2022 surface, z > 0), sampled at the nearest mask cell.
  The recipe's datasets then include ETOPO (fetched, cited) (auto-resolved: prototype method;
  existing ETOPO entry).
- Q: Memory on the Fly image builder? → A: The GeoTIFF reader decodes strip by strip and averages
  `block`×`block` pixels while reading (12 → 0.1°), never holding the full 43200×16800 image; the
  netCDF climatology mean reads one time step at a time (agent decision; owner constraint).
- Q: Is the near-pair Medium Azur / Bright Bluish Green (ΔE00 10.3) acceptable? → A: Yes, as
  approved. The report's `colors_close` threshold is ΔE00 5 (feature 004), so no warning is raised;
  the report shows the pair as the closest neighbours and the recipe comment names it
  (auto-resolved: approved prototype scale, round 1 unchanged; `maps/suitability.py` THRESHOLDS).
- Q: Fixture size budget (300 kB total) is nearly used. → A: Raise the budget to 450 kB for two new
  derived fixtures (a 1° GeoTIFF and a 4°, six-step netCDF) (agent decision: test-only rule).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build the living-planet map (Priority: P1)

A maker runs `map build living-planet --fetch -o living.json` and gets a layout with NPP classes on
land, chlorophyll classes at sea, White ice on land and sea, and a Black land shadow. The report
lists the three datasets' citations and licenses, each class's range, the no-data (ice) cells and
the tiles beyond one kit.

**Why this priority**: it is the owner's request; it delivers the approved map.

**Independent Test**: with the derived fixtures cached in place of the downloads, build
`living-planet` offline; land cells use only the six NPP colors and White; ocean cells only the five
chlorophyll colors, White and Black; the report records the no-data rules and counts.

**Acceptance Scenarios**:

1. **Given** the three datasets are cached, **When** the maker runs `map build living-planet -o
   out.json`, **Then** the layout validates, uses part 6141 on land and 98138 at sea, and its
   metadata names the recipe, the three datasets and the disclaimer.
2. **Given** real data, **When** the map is built, **Then** at least 95% of the 10,240 cells agree
   with the prototype's final grid (SC-001), with about 705 White land cells and 738 White ocean
   cells (each within 5%).
3. **Given** a recipe with `--arrangement B`, **When** built, **Then** per-cell values match A
   shifted by whole frames and the shadow is computed on the board as hung (feature 007 rules).

### User Story 2 - General recipe options for gridded science data (Priority: P2)

A recipe author can use, for any dataset: a GeoTIFF source (strip-read, block-averaged), an ERDDAP
netCDF-3 file (`latitude`/`longitude` names), a multi-step climatology mean with a per-pixel count
of valid steps, a `log10` transform, a land/ocean split taken from another dataset, and a
`[<layer>.no_data]` table that fills missing class pixels with a value and/or gives a fixed color to
unobserved, sparse or mostly-missing cells.

**Why this priority**: the map needs them, and they are reusable for later maps (vision: LAI, land
cover, productivity).

**Independent Test**: unit tests on tiny synthetic files and recipe texts.

**Acceptance Scenarios**:

1. **Given** a strip-organised LZW GeoTIFF, **When** read with `block = 2`, **Then** the values are
   the means of valid pixels in each 2×2 block, scaled, and NaN where a block has none.
2. **Given** a netCDF-3 file with `chlor_a(time, latitude, longitude)` and `reduce =
   "climatology-mean"`, **When** read, **Then** values are the mean over valid steps and `counts`
   gives the valid steps per pixel; a pixel with no valid step is NaN with count 0.
3. **Given** `transform = "log10"`, **When** read, **Then** values are log10 and values ≤ 0 are
   missing; bins bounds given in data units classify on log10.
4. **Given** a malformed `no_data` table (unknown key, a color not available for the part, a rule
   without its parameters, `value` on a dataset without a land/ocean split), **When** parsed,
   **Then** a `RecipeError` names the key path.

### User Story 3 - See it on 98138.world (Priority: P3)

The web prebuild includes `living-planet` in combinations A, B and C (21 variants in total) with
its preview, description, citations, parts lists and build sheets.

**Independent Test**: web tests build the site from fixtures and find the new map's pages and
downloads.

**Acceptance Scenarios**:

1. **Given** the prebuilt site, **When** a visitor opens `/maps/living-planet`, **Then** the page
   shows the map in A by default with B and C links, the citations of MOD17A3, MODIS-Aqua
   chlorophyll and ETOPO 2022, and the disclaimer.

### Edge Cases

- A dataset entry with `http_only` but no SHA-256, or an `http` URL without `http_only`: registry
  error.
- A content-checksummed entry whose file decodes to different data: `ChecksumMismatchError`
  ("content SHA-256 mismatch"), with the re-pin path in the error text and docs.
- ERDDAP later adds months to 2024: the content checksum fails; the maintainer re-pins (new
  version) after checking the data (documented in `research.md` R2 and the registry notes).
- A no-data rule leaves no cells for the data layer: build error naming the layer.
- A GeoTIFF that is tiled, BigTIFF, multi-band or lacks georeferencing tags: a plain `ValueError`
  naming what is unsupported (exit 1 through `MapBuildError`).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The registry MUST pin `mod17a3-npp-mean-2000-2015` (HTTP URL with `http_only`
  reason, size 384,939,658, SHA-256 `cba00628…ffef`, citation Zhao et al. 2005, license) and
  `modis-aqua-chla-2013-2024` (ERDDAP URL, size, content SHA-256, citation NASA OBPG R2022.0
  doi:10.5067/AQUA/MODIS/L3M/CHL/2022 distributed by NOAA ERD, license NASA open data policy).
- **FR-002**: The registry MUST accept `format = "geotiff"` with `grid.block` (positive integer)
  and per-variable `scale_factor`, `add_offset`, `valid_min`, `valid_max`, `fill`.
- **FR-003**: The GeoTIFF reader MUST read classic (not Big) TIFF, one band, strips (any rows per
  strip), compression none/LZW/Deflate (with or without predictor), 8/16/32-bit integer or float
  samples, georeferenced by ModelTiepoint + ModelPixelScale, without decoding the whole image at
  once; with `block` it returns block means of valid pixels.
- **FR-004**: `read_netcdf3` MUST accept coordinate variables `lat`/`lon` or `latitude`/
  `longitude`, and `reduce = "climatology-mean"`: the mean over all valid steps of the leading
  axis, plus `counts` (valid steps per pixel) and `steps` (total), read one step at a time.
- **FR-005**: The registry MUST accept `content_sha256` in place of `sha256` for download entries
  (netCDF-3 only); the cache MUST verify size and the content checksum on use and after download.
- **FR-006**: The registry MUST accept `class_rule.land_from = {dataset, variable, split_at}`;
  the reader MUST set the grid's land mask from that dataset (nearest mask cell; grid extended to
  the mask's latitude range with missing rows), and the recipe's datasets MUST include it.
- **FR-007**: Recipes MUST accept `transform = "log10"` on data layers (values ≤ 0 missing); with
  `bins`, bounds are in data units, MUST be > 0, are compared on log10, and are reported in data
  units.
- **FR-008**: Recipes MUST accept an optional `[<layer>.no_data]` table on data layers with:
  `value` (missing source pixels of the layer's class take this value; needs a land/ocean split),
  `color` (a color of the layer's part), and `rule` = `"unobserved"` (cell with no valid source
  value and |cell-centre latitude| > `min_lat`; optional `sparse_lat` + `min_steps`: also cells
  poleward of `sparse_lat` whose best source pixel has fewer than `min_steps` valid steps, needs a
  climatology-mean source) or `"share"` (share of the cell's class source pixels that had no value
  and lie poleward of `min_lat` exceeds `min_share`).
- **FR-009**: No-data cells MUST be assigned before the layer is classified (after the shadow, which
  wins), counted in that layer's supply rows, and recorded in layout metadata and the report
  (`no_data`: rule, parameters, color, cells); the CLI report MUST print them.
- **FR-010**: The bundled recipe `living-planet` MUST implement the owner design (colors, bounds,
  blend on land width 0.25, no ocean texture, Black shadow, arrangement A) with a header comment
  citing data and the disclaimer.
- **FR-011**: Offline tests MUST cover every new reader path, registry rule, recipe key and build
  rule, using small derived fixtures with `.source.json`; downloaded data MUST NOT be committed.
- **FR-012**: The web prebuild MUST include `living-planet` (A/B/C); docs (README, runbook,
  vision, CLAUDE.md/AGENTS.md project sections, recipe contract) MUST be updated.
- **FR-013**: Existing recipes MUST build exactly as before (layouts identical apart from
  `generated_at`).

### Key Entities

- **DatasetEntry** (extended): `format` geotiff; `grid.block`; `http_only`; `content_sha256`;
  `class_rule.land_from`; variable `reduce = "climatology-mean"`, `scale_factor`, `valid_max`.
- **SourceGrid** (extended): `counts`, `steps`, `missing` (class pixels whose value was filled by
  `no_data.value`).
- **NoData** (recipe): value, color, rule, min_lat, min_share, sparse_lat, min_steps.

## Success Criteria *(mandatory)*

- **SC-001**: On real data, the layout agrees with the prototype's round-5 grid in ≥ 95% of cells
  (target ≥ 98%); the agreement and per-class differences are reported in `run-state.md`.
- **SC-002**: Peak memory of `map build living-planet` on real data ≤ 1 GB (the naive full decode
  needs ≈1.4 GB for the image alone).
- **SC-003**: All CLI and web tests pass offline; existing recipes' layouts are unchanged (FR-013).
- **SC-004**: The prebuilt site serves 21 variants; the living-planet pages and downloads return
  200 locally.

## Assumptions

- Pieces beyond one kit (≈6,600 in the prototype) are expected and acceptable: the map is a top-up
  build by design; the report and parts lists show them.
- The 2024 record has 10 monthly composites (142 months in total), as when prototyped.
- Not affiliated with or endorsed by The LEGO Group.

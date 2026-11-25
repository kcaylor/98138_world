# Feature Specification: Rainfall map (GPCP precipitation on land and sea)

**Feature Branch**: `013-rainfall`

**Created**: 2026-11-22

**Status**: Clarified (autonomous mode, 2026-11-22)

**Input**: Owner-approved design "3A" (prototyped over three rounds; the approved image is the
prototype's `round3/3A-darkblue.png`, counts in `round3/stats3.json`), relayed by the coordinating
session on 2026-11-22 together with two owner decisions (netCDF-4 reader; NSIDC sea ice). The
prototype material is outside the repository (read-only); its notes are summarised in
`research.md`.

## Context

A new bundled recipe, `rainfall` ("Rainfall"), shows global annual mean precipitation:

- **Data**: GPCP v2.3 monthly long-term mean 1991–2020 (NOAA PSL, `precip.mon.ltm.1991-2020.nc`,
  netCDF-4; Adler et al. 2018), reduced to the annual mean of the 12 months, in mm/day. Each kit
  cell takes the bilinear interpolation of the 2.5° field at its centre (periodic in longitude;
  latitudes beyond the outermost source rows take the outermost row), with no nearest-cell fill.
- **Land** (1×1 round plates, part 6141), bins at 0.5, 1, 1.5, 2.5 and 4 mm/day: Brick Yellow
  [BrickLink Tan], Sand Yellow [Dark Tan], Sand Green, Bright Yellowish Green [Lime], Bright
  Green, Dark Green [Green]. Ice sheets are White: Antarctica (land south of 60° S) and Greenland
  (a box, Iceland excluded).
- **Ocean** (1×1 round tiles, part 98138), bins at 0.75, 1.5, 3 and 5 mm/day: Light Royal Blue
  [Bright Light Blue], Medium Azur, Dark Azur, Bright Blue [Blue], Earth Blue [Dark Blue]. Sea ice
  is White, from an NSIDC sea-ice concentration climatology (owner decision 2). Black land shadow.
- The legend shows mm/yr as well as mm/day. Default arrangement A.
- Expected: about 8,140 pieces beyond one kit; Earth Blue 567 (the kit has 393).
- Accepted trade-off: the Black shadow is weak against Earth Blue on wet coasts. Not to be fixed.

## Clarifications

### Session 2026-11-22 (owner decisions, relayed)

- Q: GPCP is distributed as netCDF-4 only; how is it read? → A: Add a real netCDF-4/HDF5 reader
  (new dependency h5py, pinned) and pin NOAA's original netCDF-4 file by URL, size and SHA-256.
  The netCDF-3 reader keeps its behaviour (it still rejects netCDF-4); files are routed by the
  registry `format`. The reader must also suit ERSST v5 per-month netCDF-4 files (for a later El
  Niño update), but the ENSO recipes do not change. h5py goes into the web image build
  requirements, not the runtime image. (user)
- Q: Where does sea ice come from? → A: An NSIDC sea-ice concentration climatology (proper
  source), not the prototype's chlorophyll-coverage shortcut: a public, stable, checksum-pinnable
  product for both hemispheres, with a documented rule chosen to look close to the prototype's 738
  sea-ice tiles, reported as cells agreeing / differing. It must be reusable by other recipes;
  `living-planet` does not change. Keep the new download size reasonable. (user)

### Session 2026-11-22 (autonomous)

- Q: Which NSIDC product and rule? → A: NOAA/NSIDC CDR of Passive Microwave Sea Ice
  Concentration, Version 6 (G02202, v06r00; DOI 10.7265/b18j-z797), the monthly files for the
  hemisphere's minimum month, September (north) and February (south), of each year 1991–2020:
  60 files, 17.8 MB, each pinned by URL, size and SHA-256 (all matched NSIDC's MD5 manifests on
  2026-11-22). Rule: an ocean cell is sea ice when the mean, over the cell's NSIDC pixels, of the
  pixels' 1991–2020 mean minimum-month concentration is at least 0.7 (ice that survives the melt
  season in most years), or when the cell has no NSIDC ocean pixel and its centre lies poleward of
  60° (coast and ice shelves). On the prototype grid this gives 759 cells against 738, agreeing in
  6,705 of 6,786 classified ocean cells. (agent decision: research R2; the only NSIDC climatology
  products are login-only or monthly files; the whole-record aggregates are rewritten every month
  under a new name, so they cannot be pinned.)
- Q: The NSIDC files store projected x/y (polar stereographic) with no latitude/longitude. → A:
  The netCDF-4 reader computes latitude/longitude from the CF `grid_mapping` (polar_stereographic,
  ellipsoidal, Snyder 1987 inverse); it agrees with NSIDC's own ancillary grids to 3e-10°
  (agent decision: research R3).
- Q: How does one registry entry hold 60 files? → A: An optional `files` list (url, size, sha256
  each) on a download entry; `size` is the total. The cache keeps the files in the entry's
  version directory; `resolve` returns that directory after checking every file; `fetch`
  downloads each. Single-file entries do not change (agent decision: research R4).
- Q: How are per-cell values taken for GPCP? → A: A data-layer key `sampling = "bilinear"`
  (default `"mean"`, the existing cell mean with nearest fill). Bilinear needs a regular
  latitude/longitude grid (agent decision: owner design; prototype `rain2.py`).
- Q: How are the ice sheets and the sea ice expressed? → A: One repeatable recipe table
  `[[<layer>.override]]`: a named region (cell-centre latitude/longitude bounds, strict, with
  optional excluded boxes) or a dataset rule (`dataset`, `variable`, `min_value`, optional
  `unobserved_lat`). Override cells take the override's color and are left out of the
  classification, like no-data cells (feature 012) (agent decision: reusable, research R5).
- Q: How does the legend show mm/yr? → A: An optional data-layer table `[<layer>.legend]` with
  `units` and `factor`; `map build`/`map check` print each bin in both units, and the report's
  layer gains `legend` (agent decision: additive).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build the rainfall map (Priority: P1)

A maker runs `map build rainfall --fetch -o rain.json` and gets a layout with six rain classes on
land, five at sea, White ice sheets and sea ice, and a Black land shadow. The report lists GPCP's
and NSIDC's citations and licenses, the class ranges in mm/day and mm/yr, the override cells and
the tiles beyond one kit.

**Why this priority**: it is the owner's request; it delivers the approved map.

**Independent Test**: with derived fixtures cached in place of the downloads, build `rainfall`
offline; land cells use only the six land colors and White; ocean cells only the five ocean
colors, White and Black; the report records the overrides and both legends.

**Acceptance Scenarios**:

1. **Given** the datasets are cached, **When** the maker builds `rainfall`, **Then** the build
   needs no network and every land cell south of 60° S is White.
2. **Given** a build, **When** the maker reads the report, **Then** each layer lists its overrides
   (name, color, cells) and its legend in mm/day and mm/yr.
3. **Given** `--arrangement B`, **When** the maker builds, **Then** per-cell classes and overrides
   equal combination A's, rolled by whole frames.

### User Story 2 - Read netCDF-4 data (Priority: P2)

A maker (or a recipe) uses a netCDF-4/HDF5 file: GPCP's long-term mean, an ERSST v5 per-month
file, or NSIDC's polar-stereographic sea-ice files. The reader applies `_FillValue`,
`missing_value`, `valid_range`, `scale_factor` and `add_offset`, drops size-1 leading axes, supports
`annual-mean` and `climatology-mean`, and computes latitude/longitude for CF polar-stereographic
grids. A netCDF-4 file declared as `netcdf3` is still rejected with a clear message.

**Independent Test**: unit tests on small netCDF-4 files written with h5py, including an ERSST
per-month fixture converted to netCDF-4, which reads the same as the netCDF-3 original.

### User Story 3 - Reuse the sea-ice override (Priority: P3)

A recipe author adds `[[ocean.override]]` with `dataset = "nsidc-cdr-v6-seaice-minimum-1991-2020"`
to any recipe and gets the same sea-ice cells. Region overrides work on either layer.

**Independent Test**: recipe validation tests for every override rule; build tests on synthetic
data for region and dataset overrides.

### User Story 4 - See the map on the web site (Priority: P3)

The rainfall map appears in the gallery in combinations A, B and C with every build file, like
the other bundled maps.

**Independent Test**: web tests (offline) list `rainfall` in the catalog and prebuild.

### Edge Cases

- A multi-file dataset with one file missing or wrong: not cached / checksum mismatch naming the
  file; `fetch` downloads only what is missing.
- `sampling = "bilinear"` on a categorical layer, a points grid or an irregular grid: error.
- A dataset override whose dataset has no value anywhere in the layer: no cells, no error.
- Overrides overlapping: the first listed wins. An override and the shadow: the shadow wins
  (assigned first). An override and a `no_data` rule: no-data first, then overrides.
- netCDF-4 with an unsupported `grid_mapping` and no latitude/longitude: error naming it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The registry MUST accept `format = "netcdf4"`, read with h5py; `netcdf3` stays as is.
- **FR-002**: The netCDF-4 reader MUST decode CF missing values, valid range and packing; find
  `lat`/`latitude`/`lon`/`longitude` coordinates, or 1-D projected `x`/`y` with a CF
  `polar_stereographic` grid mapping (result: a points grid); drop size-1 leading axes; support
  `annual-mean` and `climatology-mean`.
- **FR-003**: A download entry MAY list `files` (url, size, sha256 each, at least 2); the entry
  `size` MUST equal their total; verify, fetch, cache status and provenance MUST cover every file.
  A multi-file netCDF-4 variable with `reduce = "climatology-mean"` MUST be the mean over files of
  each pixel's valid values (files on the same grid are averaged; different grids are joined as
  points).
- **FR-004**: Data layers MUST accept `sampling = "mean" | "bilinear"` (default mean, unchanged).
  Bilinear: at each kit cell centre, periodic in longitude, latitude clamped to the outermost
  source rows, corners of the layer's class only (missing corners dropped, weights renormalised),
  no fill unless no corner has a value (then nearest fill, flagged).
- **FR-005**: Data layers MUST accept `[[<layer>.override]]` tables (contract): region overrides
  and dataset overrides, applied in kit coordinates before classification; their cells take the
  override color, are left out of the classification, count in the supply table, and are reported
  (`overrides`: name, kind, color, cells) in the report and layout metadata.
- **FR-006**: Data layers MUST accept `[<layer>.legend]` (`units`, `factor` > 0); the CLI legend
  MUST print both units; the report layer MUST record it.
- **FR-007**: Recipe `rainfall` MUST implement the owner's design with the pinned GPCP file and
  NSIDC entry, with citations and licenses.
- **FR-008**: Registry entries `gpcp-v23-ltm-1991-2020` and
  `nsidc-cdr-v6-seaice-minimum-1991-2020` MUST be pinned (URL, size, SHA-256) and cited.
- **FR-009**: The web prebuild MUST include `rainfall` (A, B, C); web tests pass; h5py in
  `web/requirements-build.txt`, not `web/requirements.txt`.
- **FR-010**: Every existing recipe MUST build exactly as before (layouts and reports identical
  apart from `generated_at`).
- **FR-011**: Tests MUST stay offline, with small derived fixtures (each with `.source.json`).

### Key Entities

- **DatasetEntry.files**: the pinned files of a multi-file dataset.
- **SourceGrid (points)**: values with per-point latitude/longitude (no regular grid).
- **Override**: name, color, and a region (bounds, exclusions) or a dataset rule.
- **Legend**: secondary units and factor for a data layer's bins.

## Success Criteria *(mandatory)*

- **SC-001**: The real-data build agrees with the prototype 3A grid in at least 98% of cells;
  differences are explained (expected: sea-ice rule only).
- **SC-002**: Pieces beyond one kit within 1% of the prototype's 8,143.
- **SC-003**: New downloads for `rainfall` under 20 MB.
- **SC-004**: CLI and web test suites pass offline; existing recipes unchanged (FR-010).

## Assumptions

- Override region bounds are strict inequalities on kit cell-centre latitude/longitude, as in the
  prototype.
- The NSIDC files are versioned (v06r00); if NSIDC revises a file, the checksum fails and a new
  version is pinned.

Not affiliated with or endorsed by The LEGO Group.

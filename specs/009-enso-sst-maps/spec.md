# Feature Specification: ENSO Sea Surface Temperature Anomaly Maps

**Feature Branch**: `009-enso-sst-maps`

**Created**: 2026-11-22

**Status**: Draft (clarified 2026-11-22, autonomous mode)

**Input**: Owner (2026-11-22): "build both a strong La Niña and a strong El Niño SST map ... Pacific
centric ... use as much as possible the parts list from the original set, some additional ocean
tiles allowed". Scoping answers and data findings are in `run-state.md`.

> **Note (feature 010, 2026-11-22)**: at the owner's request both ENSO recipes now default to
> `arrangement = "D"` (`pacific`, the date line centred; not among the building instructions'
> combinations; see `specs/010-pacific-arrangements/`). This supersedes FR-013's value B; B is still
> available with `--arrangement B`. Measured with the real ERSST files: in D the land shadow takes
> 387 Earth Blue tiles (390 in B) and the tiles beyond one kit are 1,114 (El Niño, as in B) and
> 1,152 (La Niña; 1,155 in B); in E 1,112 and 1,158.

## Context

Two new bundled map recipes show the sea surface temperature (SST) anomaly of a strong El Niño
(December 1997) and a strong La Niña (December 1988) on the kit 31203 board, hung as combination B
(3·1·2) so the Pacific is whole. Both maps use one fixed legend in °C of anomaly, so a viewer can
set them side by side and compare them tile for tile.

Data: NOAA Extended Reconstructed SST version 5 (ERSST v5), one file per month from NOAA NCEI
(`https://www.ncei.noaa.gov/pub/data/cmb/ersst/v5/netcdf/ersst.v5.199712.nc` and
`.../ersst.v5.198812.nc`). Each file is netCDF-3 classic, 134,832 bytes, last modified 2017-06-30,
and holds the variable `ssta`: the anomaly against the 1971–2000 climatology (the file's
`climatology` attribute), on a 2° grid of 89 latitudes × 180 longitudes, with singleton time and
level axes and a fill value of −999 over land and missing cells.

Facts measured before this specification (`run-state.md`):

- Niño 3.4 region (5° S–5° N, 170° W–120° W) mean anomaly: December 1997 +2.28 °C; December 1988
  −1.97 °C.
- In arrangement B the land shadow takes 390 ocean cells, leaving 6,788 ocean cells for the data.
- One kit's ocean tile supply (inventory page 159): Bright Bluish Green 1,879, Medium Azur 1,607,
  Bright Yellowish Green 1,060, Brick Yellow 725, Bright Green 601, Bright Orange 601, Vibrant
  Coral 601, Flame Yellowish Orange 599, Earth Blue 393 (of which the shadow takes 390).
- With trial bounds −1.5, −1, −0.5, −0.25, +0.25, +0.5, +1, +1.5 °C the cell counts per class are
  (cold to warm) 1997: 14, 219, 757, 640, 2,909, 708, 1,008, 247, 286; 1988: 179, 263, 909, 838,
  3,132, 778, 635, 54, 0. The near-zero class far exceeds any single color's supply, so some extra
  tiles beyond one kit are expected; the final bounds are set in planning.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build the El Niño map (Priority: P1)

A maker runs `map build ocean-el-nino --fetch -o el-nino.json` and gets a layout of the December
1997 SST anomaly, hung as B with the Pacific whole, white land with the default land shadow, and an
ocean colored by the shared °C anomaly legend. The report lists the dataset's citation and license,
each color's °C range, and how many tiles go beyond one kit's supply.

This story includes what the map needs: the pinned dataset entry, reading the per-month ERSST file
(which has singleton time and level axes), and the new optional recipe key `arrangement`.

**Why this priority**: it is the owner's primary request and the smallest slice that delivers a
buildable, Pacific-centred ENSO map.

**Independent Test**: with the small derived fixture in place of the cached file, build
`ocean-el-nino` offline; the layout records arrangement B, its ocean colors follow the shared
legend, and the cells of the Niño 3.4 region get warm classes.

**Acceptance Scenarios**:

1. **Given** the December 1997 file is cached, **When** the maker runs `map build ocean-el-nino -o
   layout.json` with no `--arrangement`, **Then** the layout is hung as B, records
   `metadata.arrangement` B, and the output says the arrangement came from the recipe.
2. **Given** the same cache, **When** the maker passes `--arrangement A`, **Then** the layout is
   hung as A (the explicit flag wins over the recipe key).
3. **Given** the file is not cached, **When** the maker runs `map build ocean-el-nino` without
   `--fetch`, **Then** the build stops with the existing "not cached" error naming `dataset fetch`
   and no network access happens.
4. **Given** `dataset fetch` downloads the file, **When** its size or SHA-256 differs from the
   pinned entry, **Then** the file is rejected with the existing checksum error.
5. **Given** the built El Niño layout, **When** the maker reads the report, **Then** it shows the
   ERSST v5 citation (Huang et al. 2017, doi 10.1175/JCLI-D-16-0836.1), the dataset DOI
   10.7289/V5T72FNM, the license, the °C range of each color, the cells per color against one
   kit's supply, and the disclaimer "Not affiliated with or endorsed by The LEGO Group."
6. **Given** a recipe without an `arrangement` key, **When** it is built without `--arrangement`,
   **Then** it is hung as A exactly as before this feature.

---

### User Story 2 - Build the La Niña map with the identical legend (Priority: P2)

A maker runs `map build ocean-la-nina -o la-nina.json` and gets the December 1988 SST anomaly, hung
as B, with exactly the same °C bounds and colors as the El Niño map, so the two boards compare
directly.

**Why this priority**: the pair is the point of the request, but it reuses everything from P1 and
adds only a second dataset entry and recipe.

**Independent Test**: build `ocean-la-nina` offline from its fixture; its classification bounds and
color list are identical to `ocean-el-nino`, and the cells of the Niño 3.4 region get cold classes.

**Acceptance Scenarios**:

1. **Given** both recipes, **When** their classification bounds and color lists are compared,
   **Then** they are identical.
2. **Given** the cached December 1988 file, **When** the maker builds `ocean-la-nina`, **Then** the
   layout is hung as B and the Niño 3.4 cells get cold classes.
3. **Given** both built layouts, **When** a cell holds the same color in both, **Then** it means the
   same °C anomaly range in both.

---

### User Story 3 - Report the extra tiles and document the maps (Priority: P3)

A maker who owns one kit 31203 runs `parts list el-nino.json --kits 1` (and the same for La Niña)
and sees exactly which ocean tiles they must buy beyond the kit, by color, with cited IDs, and can
export a BrickLink wanted list or Rebrickable CSV of only those. The README recipe list and the demo
runbook describe both maps, their legend, their data and their default arrangement.

**Why this priority**: the parts tooling (feature 005) already does the arithmetic; this story
verifies it on the new maps and documents them.

**Independent Test**: run `parts list --kits 1` on each built layout; the top-up totals equal the
over-supply reported by `map build` for the same layout, and both stay within the bound set in
planning.

**Acceptance Scenarios**:

1. **Given** a built ENSO layout, **When** the maker runs `parts list <layout> --kits 1`, **Then**
   every color whose use exceeds one kit's supply appears with the shortfall, and the land plates
   need no top-up.
2. **Given** the same layout, **When** the maker runs `parts export <layout> --kits 1 --bricklink
   wanted.xml`, **Then** the wanted list holds only the extra tiles.
3. **Given** the README and the runbook, **When** a reader looks for the ENSO maps, **Then** both
   recipes are listed with their month, data source, legend and default arrangement B.

---

### Edge Cases

- Ocean cells of the kit mask with no data in the source (land in ERSST, missing values): filled
  from the nearest cell as for every recipe, and reported in the build report's "filled" share.
- Anomalies beyond the outermost inner bounds (for example above +3 °C off Peru in 1997): they take
  the first or last color (existing `bins` clamping; the end classes are open). The outer bounds
  (−9 and +9 °C, plan research R1) lie beyond every value in both months, so the report's
  "outside the class bounds" count is zero; a value beyond them would still be clamped and counted.
- A legend class that gets no cells in one of the two months (likely the warmest class in 1988):
  the existing `empty_class` warning appears; this is expected and does not fail the build.
- A recipe with an invalid `arrangement` value (for example `D` or a number): rejected at load with
  an error naming the key path `arrangement` and the valid values.
- A recipe with `arrangement` read by a tool from before this feature: rejected there as an unknown
  key (recipe validation is strict); the format stays "1", as when the `shadow` table was added.
- A per-month file whose variable has a non-singleton leading axis (more than one time step or
  level) and no reduce rule: the reader stops with an error naming the axis sizes.
- A netCDF-4 file (ERSST months from 2010 on) given to the netCDF-3 reader: it stops with a clear
  "not a netCDF-3 classic file" error rather than reading garbage.
- `layout arrange` on an ENSO layout re-hangs it without rebuilding, as for any layout.

## Requirements *(mandatory)*

### Functional Requirements

**Data**

- **FR-001**: The dataset registry MUST hold two pinned entries, `ersst-v5-1997-12` and
  `ersst-v5-1988-12`, each with the NCEI file URL, size (134,832 bytes), SHA-256, format netCDF-3,
  the variable `ssta` (units °C, anomaly against 1971–2000), the title, publisher NOAA NCEI, the
  citation Huang et al. 2017 (doi 10.1175/JCLI-D-16-0836.1), the dataset DOI 10.7289/V5T72FNM, the
  license "No constraints on data access or use" (public domain, U.S. Government work), the grid,
  and the rule that missing values are land.
- **FR-002**: The netCDF-3 reader MUST accept a variable whose axes before latitude and longitude
  all have size 1 (for example time = 1, level = 1) and read it as one 2-D field; it MUST keep
  rejecting a variable with a leading axis larger than 1 unless a reduce rule is declared.
- **FR-003**: The reader MUST treat the file's `_FillValue` (−999) as missing.
- **FR-004**: Only `dataset fetch` and `map build --fetch` MAY use the network; with the files
  cached, both maps MUST build offline.

**Recipes**

- **FR-005**: Two bundled recipes MUST exist: `ocean-el-nino` (December 1997) and `ocean-la-nina`
  (December 1988). Each MUST have a white land background (as `ocean-sst`), the default land shadow
  (Earth Blue, cast east), and an ocean data layer of `ssta` classified with `bins`.
- **FR-006**: Both recipes MUST use one identical legend: the same bounds in °C and the same ordered
  list of ocean tile colors. The legend MUST read cold to warm (negative anomalies in the blue and
  green colors, positive anomalies in the yellow, orange and coral colors, the class containing
  zero in the middle of the order), and every color MUST be a valid color of part 98138.
- **FR-007**: Within FR-006, the bounds and the assignment of colors to classes MUST be chosen to
  minimise the tiles needed beyond one kit 31203's ocean supply: first the larger of the two maps'
  extra-tile totals, then their sum. An extra tile is a tile of a color not in the kit, or a tile
  above the kit's supply of its color, counting the 390 shadow tiles against Earth Blue.
- **FR-008**: The ocean layer of both recipes MUST have no `blend` texture, so every tile's color
  states its °C class exactly and the two maps compare cell for cell.
- **FR-009**: Each recipe's title and description MUST name the event and the month, and the recipe
  file MUST carry the disclaimer.

**Recipe key `arrangement`**

- **FR-010**: A recipe MAY have an optional top-level key `arrangement` with a value the
  `--arrangement` option accepts (`A`, `B`, `C`, any case, or `europe-africa`, `americas`,
  `asia-australia`). Absent means A. The recipe format stays "1".
- **FR-011**: `map build` and `map check` MUST hang the map in the recipe's arrangement unless
  `--arrangement` is given on the command line, in which case the flag wins. Library callers
  (`build_map`, `check_recipe`) MUST behave the same way when no arrangement is passed.
- **FR-012**: The command output and the report MUST state the arrangement used and whether it
  came from the recipe, the command line, or the default.
- **FR-013**: Both ENSO recipes MUST set `arrangement = "B"`.
- **FR-014**: The `map recipes` listing SHOULD show each recipe's default arrangement.

**Reports, parts and docs**

- **FR-015**: The `map build` and `map check` output for a `bins` layer MUST show each color's °C
  range (the report JSON already holds the class bounds).
- **FR-016**: The build report MUST list, per color, the tiles used against one kit's supply and
  warn about colors over supply or not in the kit (existing behaviour); `parts list --kits 1` and
  `parts export --kits 1` MUST give the same extra tiles for the same layout.
- **FR-017**: The recipe list in `cli/README.md` and the runbook `docs/runbook.md` MUST describe both maps (month, data,
  legend, default arrangement B) and note that the El Niño map is meant to move to the 2026–27
  event later.
- **FR-018**: All user-facing output MUST carry "Not affiliated with or endorsed by The LEGO Group."

**Tests**

- **FR-019**: Tests MUST run offline with small derived fixtures under `cli/tests/fixtures/datasets/`,
  each with a `.source.json` naming the source file, its SHA-256, the derivation method, citation
  and license; the fixtures MUST keep the per-month file's structure (singleton time and level
  axes, fill value). Downloaded datasets MUST NOT be committed.

### Out of scope

- Switching the El Niño map to the 2026–27 event. NCEI per-month files from 2010 on are netCDF-4,
  which the current reader cannot read without a new dependency. The design keeps the swap to a new
  dataset entry plus a changed `dataset` line and title in `ocean-el-nino` (recipe id and legend
  unchanged); it is a follow-up feature.
- Printing the °C legend on build sheets (feature 006 sheets show colors and counts only); the
  legend is in the recipe, the build output and the docs. Follow-up.
- A rank-based or per-map legend; any change to the kit's grid, mask or parts.

### Key Entities

- **Dataset entry (per month)**: one ERSST v5 per-month file pinned by URL, size and SHA-256, with
  its variable `ssta`, grid, land rule, citation, DOI and license.
- **ENSO recipe**: land background, shadow, ocean `bins` layer of `ssta`, the shared legend, and the
  default arrangement B.
- **Shared legend**: ordered °C bounds and ocean tile colors, identical in both recipes.
- **Recipe arrangement**: optional recipe default for how the frames are hung; the command-line
  flag overrides it.
- **Extra tiles**: per color, tiles needed beyond one kit 31203's supply (non-kit colors and over
  supply), reported by the build report and the parts list.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With both files cached and the network unavailable, both maps build, and the whole
  test suite passes offline.
- **SC-002**: In the December 1997 map at least 90% of the ocean cells whose centres fall in the
  Niño 3.4 region (5° S–5° N, 170° W–120° W) get a class whose lower bound is at least +0.5 °C; in
  the December 1988 map at least 90% get a class whose upper bound is at most −0.5 °C.
- **SC-003**: The two recipes' bounds and color lists are identical (checked by a test).
- **SC-004**: For each map the extra tiles beyond one kit are reported and stay at or below a bound
  per map fixed in planning from the measured data (the bound is a planning detail); the build
  report and `parts list --kits 1` agree on the number.
- **SC-005**: Both maps use no color outside the kit's nine ocean colors unless planning shows that
  one reduces the extra-tile total.
- **SC-006**: Existing recipes built without `--arrangement` give byte-identical layouts to before
  this feature (apart from timestamps).
- **SC-007**: A maker can go from nothing to both layouts and their top-up lists with four commands
  (`dataset fetch` or `--fetch`, two `map build`, `parts list`), following the runbook.

## Assumptions

- December is the representative month for both events (owner's choice; the files are stable,
  last modified 2017-06-30).
- The anomaly baseline is the files' own 1971–2000 climatology; no re-baselining is done.
- One kit's supply is the cited inventory (page 159); the shadow's 390 Earth Blue tiles count
  against it first, as in `ocean-sst`.
- ERSST's 2° grid is reprojected to the kit grid by the existing reprojection; at about 2.8° per
  stud the grid loses little detail.
- No new dependency is needed: the existing netCDF-3 reader is extended.
- The recipe ids name the phenomenon, not the year, so the planned swap to 2026–27 keeps the id.

## Clarifications

### Session 2026-11-22 (autonomous)

- Q: What are the recipe and dataset ids? → A: recipes `ocean-el-nino` and `ocean-la-nina` (no year,
  so the 2026–27 swap keeps the id); datasets `ersst-v5-1997-12` and `ersst-v5-1988-12`.
  (auto-resolved: naming pattern of `ocean-sst` and `ersst-v5-ltm-1991-2020` in
  `cli/src/lego_image_processor/maps/recipes/` and `data/datasets.json`; owner's planned swap)
- Q: Does adding `arrangement` need a new recipe format version? → A: No; it stays format "1" as an
  optional key, like the `shadow` table added on 2026-11-22. (auto-resolved:
  `specs/004-map-recipes/contracts/recipe-format.md` line 39, 69)
- Q: Which wins, the recipe key or `--arrangement`? → A: the explicit flag; the recipe key replaces
  only the default. Today the option defaults to "A", so the CLI must tell "not given" from "A".
  (auto-resolved: owner's scoping answer in `run-state.md`; `cli/options.py`)
- Q: Should the output say where the arrangement came from? → A: yes, "recipe", "command line" or
  "default", so a B layout is never a surprise. (auto-resolved: existing "Arrangement: …" line in
  `cli/map.py`; decide-and-log per run policy)
- Q: How is "minimise extra tiles" measured across two maps with one legend? → A: minimise the
  larger per-map extra total, then the sum; extras = non-kit colors plus over-supply, shadow
  counted. (auto-resolved: each map is built from one kit; `maps/suitability.py` supply rows define
  over-supply and beyond-kit)
- Q: May minimisation reorder colors freely? → A: no; the order must still read cold to warm with
  zero in the middle class (Constitution III, data order follows color order; `ocean-sst` color
  order); within that, any assignment. (auto-resolved; the owner may want to confirm, see run-state)
- Q: Use the `blend` texture as `ocean-sst` does? → A: no; with a fixed °C legend, blend would move
  cells across classes and break the tile-for-tile comparison the owner asked for.
  (auto-resolved: `maps/texture.py` `apply_blend` shifts `bins` classes ±1)
- Q: Values beyond the outer bounds? → A: clamped to the first or last class and counted in the
  report (existing `bins` behaviour). (auto-resolved: `maps/classify.py`, 004 spec edge cases)
- Q: Where does the user see the °C legend? → A: recipe, report JSON (`class_bounds`, already
  present), and the build output (FR-015); not on build sheets this version. (auto-resolved:
  `maps/suitability.py`, `sheets/legend.py` has no value ranges; kept out of scope)
- Q: How should the reader handle the 4-D variable? → A: drop all leading axes of size 1; keep the
  error for a larger leading axis without a reduce rule. (auto-resolved: `datasets/readers.py`
  `read_netcdf3` already squeezes one time axis)
- Q: Which tool reports the extra tiles? → A: the existing build report supply table and warnings,
  and `parts list/export --kits 1`; no new command. (auto-resolved: `maps/suitability.py`,
  `cli/parts.py`)

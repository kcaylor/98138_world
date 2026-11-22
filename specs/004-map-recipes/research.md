# Research: Map Recipes and Canonical Datasets (004)

**Feature**: 004-map-recipes | **Date**: 2026-11-22 | **Spec**: [spec.md](spec.md)

All downloads in this research went to the session scratchpad (outside the repository) and were
treated as untrusted data. Nothing downloaded is committed. Measurement scripts were run with
`python -I` from a separate scripts directory.

## R1. Official design: how much of the ocean is bathymetry? (FR-020, FR-021, Q5)

**Measured** on `cli/src/lego_image_processor/data/kit_31203_design.json` and the ETOPO 2022
subset of R3 reprojected with R2:

| Tile color | Cells | Median depth (m) | 10th–90th percentile (m) |
|---|---|---|---|
| Earth Blue | 392 | 483 | 30–3,444 |
| Brick Yellow | 724 | 1,981 | 65–4,266 |
| Flame Yellowish Orange | 597 | 3,258 | 189–4,700 |
| Vibrant Coral | 203 | 3,401 | 162–4,822 |
| Bright Orange | 230 | 3,415 | 110–4,978 |
| Bright Yellowish Green | 1,019 | 3,596 | 430–4,902 |
| Medium Azur | 1,606 | 4,045 | 2,115–5,178 |
| Bright Green | 529 | 4,410 | 2,602–5,493 |
| Bright Bluish Green | 1,878 | 4,455 | 2,915–5,395 |

- Earth Blue sits on the coast (26% of ocean cells next to land; none further out).
- Neighbouring cells repeat a color only slightly more than chance (for example Bright Bluish
  Green 0.37 against a share of 0.26): the ocean is a textured mix.
- Colors do cluster regionally: the variance of each color's share in 8×8 blocks is 2–6× what a
  random placement gives.
- Cell agreement with the official ocean (7,178 cells):

| Rule | Agreement |
|---|---|
| Best color per depth bin (40 bins, in-sample upper bound) | 33.0% |
| Same, with distance to coast | 35.7% |
| Depth rank onto the official counts, colors in median-depth order | 26.8% |
| Same with 600 m of random depth noise (a stand-in for texture) | 25.1% |
| Official colors shuffled at random | 16.0% |

**Measured at implement time (T047)** with the built recipe `official-31203-bathymetry` (rank
with the official counts, median-depth color order, blend 0.25, seed 31203): ocean agreement
1,918 / 7,178 = 26.7% on the full 10' ETOPO subset and 26.71% on the 1° test fixture; land 3,062 /
3,062; counts equal the official counts (all within supply); colors' median depths in the recipe
order. The fixture test threshold is 25.7% (fixture value minus 1 point).

**Decision**: two acceptance tiers. Exact: `official-31203` uses the design grid as a packaged
categorical dataset and must match 10,240/10,240. Derived: `official-31203-bathymetry` ranks depth
into the official counts in median-depth order, adds texture, and must reach ≥ 24% ocean agreement
(measured 25–27%, chance 16%), stay within kit supply, and keep land identical.
**Rationale**: an exact match from real data is impossible (≤ 36% even in-sample); the exact tier
tests the recipe machinery, the derived tier tests the data path honestly.
**Alternatives**: exact tier only (does not test data); derived tier with a high threshold
(unachievable); learning a per-region color model from the design (overfits one map, not a recipe).
**Status**: provisional, reserved for the user (Q5).

## R2. The kit's projection and frame (FR-013, FR-014)

**Method**: land fraction of ETOPO 2022 (surface > 0 m) binned into 128×80 cells; prediction
"land if ≥ 50%" compared with the kit mask. Longitude of the left edge fitted first from the
column profile of land (correlation 0.990), then per model the equator row and the scale
(rows per radian of the model's y) by grid search.

| Model | Left edge | Equator row | Scale | Mask agreement |
|---|---|---|---|---|
| **Equirectangular** | 168.9° W | 42.2 | 26.3 rows/rad (2.18°/row) | **94.2%** |
| Miller cylindrical | 168.9° W | 41.6 | 22.0 rows/unit | 90.9% |
| Mercator | 168.9° W | 42.7 (41.7 ties) | 18.6 rows/unit (19.2 ties) | 87.0% |

- Columns: 360° / 128 = 2.8125° each, column 0 starts at 168.9° W.
- Rows: the top row reaches about 89.8° N and the bottom row about 82.3° S; the equator is at row
  42.2, below the middle row, consistent with `specs/003-kit-reference-data/projection-notes.md`.
- Cells are not square in degrees (2.81° × 2.18°); the kit stretches latitude by 1.29 relative to
  longitude.

**Decision**: equirectangular with the parameters above, stored as
`data/kit_31203_projection.json` with method, data source, and the three models' agreements. The
maintainer tool gains a `fit-projection` command that reproduces the fit from a cached ETOPO file
(`--check` compares with the committed file). The kit mask always decides land/ocean; data is
only read through the projection.
**Rationale**: best agreement by 3 points; simplest model; matches the 003 notes.
**Alternatives**: Miller (the 003 notes' best guess from 4 points; worse on the full mask),
a free monotone row-to-latitude table (more parameters, little gain at 1-stud precision).

## R3. Bathymetry and elevation dataset (FR-011)

| Candidate | Resolution | Size | License | Notes |
|---|---|---|---|---|
| **ETOPO 2022 60″ surface, OPeNDAP subset every 10th sample (10′)** | 10′ (1080×2160) | **9,357,398 B** | Public domain (NOAA NCEI, US Government work) | Current canonical NOAA relief model; deterministic response |
| ETOPO 2022 60″ surface, full netCDF | 1′ | 478.2 MB | Public domain | Same data; too large for a first fetch |
| ETOPO5 (1988) | 5′ | 18.7 MB | Public domain | Superseded, poor in parts of the ocean |
| GMT `earth_relief_10m` (SRTM15+ V2.7, filtered) | 10′ | 3.1 MB | Not stated on the GMT page | License unclear; rejected |
| GEBCO 2024 | 15″ | ~7 GB | GEBCO terms (permissive, attribution) | Far too large |

- URL: `https://www.ngdc.noaa.gov/thredds/dodsC/global/ETOPO2022/60s/60s_surface_elev_netcdf/ETOPO_2022_v1_60s_N90W180_surface.nc.dods?z[0:10:10799][0:10:21599]`
  (brackets percent-encoded when fetched).
- SHA-256 `575c7a0c84f18b41430a723f26475fa41b1d787c94fa641f0d0705291e3991fd`; two requests of a
  smaller subset returned identical bytes (determinism checked).
- Format: DAP2 binary (`.dods`): a text DDS header, `Data:\n`, then XDR arrays `z` (float32,
  1080×2160, lat ascending from −89.99°), `lat` and `lon` (float64). Parsed with NumPy only.
- Grid: cell-registered (`node_offset 1`), WGS 84, heights in metres relative to EGM2008,
  `positive up`, fill −99999. The surface variant has ice-sheet tops over Greenland and Antarctica.
- Samples per kit cell: about 17 × 13 = 220, so sub-sampling every 10th value does not alias at
  grid scale. Within-cell share of variance: land elevation 7.7%, bathymetry 11.7% (both "smooth").
- Kit cells with no same-class data: 26 land cells (0.8%), 69 ocean cells (1.0%), filled from the
  nearest cell.
- Citation: NOAA National Centers for Environmental Information. 2022: ETOPO 2022 15 Arc-Second
  Global Relief Model. NOAA National Centers for Environmental Information.
  https://doi.org/10.25921/fd45-gt74 (the 60″ grid is NCEI's downsampled product of it).
- Land/ocean rule: land > 0 m, ocean ≤ 0 m; depth = −z.

**Decision**: register `etopo2022-surface-10m` (the subset). Record the full 478 MB file as a
documented alternative in the registry notes, not as an entry, until its checksum is measured.
**Rationale**: canonical, public domain, 9.4 MB, no new dependency.
**Risk**: if NCEI changes its server so the subset bytes change, the checksum fails loudly; the
fix is a new registry version with a new checksum (data unchanged). Logged as agent decision.

## R4. Sea surface temperature dataset (FR-011)

| Candidate | Grid | Size | Format | Readable without new dependency |
|---|---|---|---|---|
| **NOAA ERSST v5, monthly long-term mean 1991–2020 (PSL)** | 2° (89×180) | **1,160,004 B** | netCDF-3 classic | Yes (SciPy `netcdf_file`) |
| NOAA OISST v2 (1°), long-term mean 1991–2020 (PSL) | 1° | 3,441,836 B | netCDF-4/HDF5 | No (needs h5py or netCDF4) |
| ERSST v5 LTM 1981–2010 | 2° | 1,159,964 B | netCDF-3 | Yes; older normal |

- URL: `https://downloads.psl.noaa.gov/Datasets/noaa.ersst.v5/sst.mon.ltm.1991-2020.nc`,
  last modified 2021-02-09, SHA-256
  `b4f20ecfbf5e4c9276ff9e72adbf6205663e9efd64a3b1e74a0fcd2b3c72e99f`.
- Variable `sst` (12, 89, 180), degC, missing value −9.96921e36 over land and ice; lat 88° N to
  88° S, lon 0–358° E. The annual mean is the mean of the 12 months where all are valid.
- Coverage on the kit grid: 311 of 7,178 ocean cells (4.3%) have no SST value (sea ice and
  coasts), filled from the nearest cell; below the 5% warning threshold (FR-019).
- The file's global `climatology` attribute still names 1971–2000; the file name, PSL listing and
  `climatology_bounds` define the period. Recorded in the registry notes.
- License: NOAA data, public domain; PSL asks for the acknowledgement "NOAA ERSST V5 data provided
  by the NOAA PSL, Boulder, Colorado, USA, from their website at https://psl.noaa.gov".
- Citation: Huang, B., P. W. Thorne, V. F. Banzon, et al., 2017: Extended Reconstructed Sea
  Surface Temperature, Version 5 (ERSSTv5): Upgrades, Validations, and Intercomparisons. J.
  Climate, 30, 8179–8205, https://doi.org/10.1175/JCLI-D-16-0836.1.

**Decision**: register `ersst-v5-ltm-1991-2020`. **Rationale**: smallest file that resolves the
kit cells, no new dependency. **Alternative**: OISST 1° (better coasts, 3.4 MB) would need an HDF5
reader; revisit if a later feature adds one.

Both downloads together: 10.5 MB (SC-005).

## R5. Reading data without new dependencies

**Decision**: readers for (1) DAP2 `.dods` binary (NumPy, ~40 lines), (2) netCDF-3 classic
(`scipy.io.netcdf_file`), (3) NumPy `.npy` (for local files and test fixtures). Downloads use
`urllib.request` like `cli/tools/kit31203/source.py`. SciPy is already installed through
scikit-image; it becomes an explicit dependency in `pyproject.toml` because the package now imports
it directly. **Alternatives**: xarray + netCDF4 (heavy, HDF5 binaries; not needed for the chosen
files), requests (stdlib is enough).

## R6. Recipe format (FR-001, Q1)

**Decision (provisional, Q1)**: TOML read with `tomllib` (standard library since Python 3.11,
which the constitution already requires). Recipes are read-only for the tool, so no TOML writer is
needed. **Alternatives**: YAML (PyYAML dependency, implicit typing pitfalls), JSON (no comments,
awkward to hand-write).

## R7. Classification and texture (FR-015, FR-017)

- `bins`: explicit bounds b0 < b1 < … < bn for n colors; values below b0 → class 0, above bn →
  last class (counted).
- `quantile`: equal counts by rank; ties broken by cell order (row-major) for determinism.
- `rank`: classes take given shares (weights normalised to the layer's cells, largest-remainder
  rounding); used by `official-31203-bathymetry` with the official counts.
- `rank-to-supply`: shares proportional to one kit's supply of each color, rounded so that no color
  exceeds its supply; fails if the layer has more cells than the colors' total supply.
- `categorical`: a map from source category to color key; used by `official-31203`.
- Texture `blend` (data layers): a cell within `blend` × class width of a boundary moves to the
  neighbouring class with probability falling linearly from 0.5 at the boundary to 0 at the
  blend edge. For rank methods, "width" is in rank units and moves are made as swaps between
  pairs of boundary cells on either side, so counts never change.
- Texture `mix` (backgrounds): Gaussian-smoothed white noise (sigma = `cluster` studs, 0 = no
  clustering) ranked into the colors by weight, giving exact counts by weight and soft patches.
- Randomness: `numpy.random.default_rng(seed)` drawn in row-major order; seed from the recipe
  (default 31203). **Rationale**: deterministic, simple, testable; replaces 002's shadowing.

## R8. Suitability metrics (FR-019)

| Metric | Definition | Warning when |
|---|---|---|
| Variance lost | mean within-cell variance / total variance of source values in the layer | > 50% |
| Filled cells | layer cells without same-class source values | > 5% |
| Empty classes | classes with 0 cells | any |
| Color distinctness | min ΔE00 between neighbouring scale colors | < 5 |
| Supply | per color: cells vs one kit's supply (kit colors) | informational |

Measured: ETOPO land 7.7%, bathymetry 11.7% variance lost; ERSST 4.3% filled. A synthetic
1-cell checkerboard gives ~100% lost (test case). Thresholds are agent defaults, recorded in every
report.

## R9. Colors beyond the kit (FR-016, Q4)

- Rebrickable `elements.csv` (fetched 2026-11-22, 1,137,218 B gz) lists elements of part 6141 in
  70 colors (opaque examples: Black, Green, Bright Green, Lime, Olive Green, Sand Green, Tan, Dark
  Tan, Medium Nougat, Reddish Brown, Dark Brown, Light Bluish Gray, Dark Bluish Gray, White) and of
  98138 in 69 colors. Rebrickable files part 6141 under `6141` here, while feature 003 recorded
  `4073` as its BrickLink/Rebrickable number; to be reconciled when the table is built (005 needs
  it for wanted lists).
- The license of Rebrickable's CSV downloads could not be confirmed (downloads page returned HTTP
  402 to the fetcher; no license found by search). Feature 003 already cites Rebrickable
  `colors.csv`; the table would record facts (which colors a part is made in) with citations, not
  redistribute the file.
- Candidate elevation scale (Rebrickable RGB, neighbouring ΔE00): Green → Bright Green 15.1 →
  Lime 25.9 → Olive Green 23.6 → Tan 17.8 → Dark Tan 20.6 → Medium Nougat 12.4 → Reddish Brown 29.5
  → Dark Brown 11.2 → Light Bluish Gray 50.7 → White 21.9. All above the ΔE00 5 threshold.

**Decision (provisional, Q4)**: a curated `data/part_colors.json` (format like `kit_colors.json`:
source block, citations, LEGO/BrickLink/Rebrickable names and IDs, element ID, RGB) for parts 6141
and 98138, produced by a maintainer tool from SHA-256-pinned snapshots of Rebrickable
`elements.csv` and `colors.csv`, with LEGO IDs from LDraw `LDConfig.ldr` and BrickLink IDs from
the archived BrickLink color catalog (the 003 sources). Limited to the kit's 10 colors plus a
reviewed list of opaque plate colors needed by bundled recipes (about 11). Rows with any missing
ID are excluded, not guessed (constitution V). The kit's own table stays the authority for kit
colors.

## R10. Map provenance in layouts (FR-005, Q3)

`PositionPlacementGrid.from_json` reads named metadata keys and ignores others, so an added
`metadata.map` block keeps every schema 2.0 reader working. **Decision (provisional, Q3)**: write
`metadata.map` (recipe id, format version, recipe SHA-256, layers with role/dataset/version/
citation/license, texture seed, tool version, disclaimer); `from_json` keeps it so a loaded layout
can be re-saved without losing it. `source_image` is set to `recipe:<id>` for recipe builds.

## R11. Test data without downloads (FR-025, SC-008)

- Unit tests build synthetic grids in memory (gradients, checkerboards, patches) and tiny DODS
  and netCDF-3 files in `tmp_path` (SciPy can write netCDF-3).
- Integration fixtures (committed, derived, small): ETOPO 2022 block means at 1° as `.npy` int16
  (~130 KB) and the ERSST annual mean as netCDF-3 (~70 KB), produced by a maintainer script from
  the cached files, each with a `.source.json` naming the dataset, checksum, method and license
  (public domain). The derived-tier test (SC-003) runs on the 1° fixture; its agreement is
  measured at implement time and the fixture threshold recorded (expected close to the full-data
  figure).
- Downloads are tested with a fake opener injected into the fetch function; the session offline
  guard (`tests/conftest.py`) stays.

## R12. Cache layout (FR-009)

Reuse the 003 cache root. Datasets go to `<root>/datasets/<id>/<version>/<filename>`; a fetch
writes `<filename>.part`, verifies size and SHA-256, then renames. The cache helper moves into the
package (`lego_image_processor/datasets/cache.py`); `cli/tools/kit31203/source.py` imports
`cache_root` from it so there is one definition.

## R13. Land shadow and coastal halo (amendment 2026-11-22)

**Shadow, measured** on `kit_31203_design.json` with the kit mask: 392 ocean cells have land
directly to the west (x-1, same row; none at x = 0). Of these, 391 are Earth Blue and 1 is Brick
Yellow; the design has 392 Earth Blue cells, 391 of them in this set (the other one is elsewhere).
The kit holds 393 Earth Blue tiles. So the design's Earth Blue is a one-stud drop shadow cast
east, and a rule "ocean cell east of land = Earth Blue" reproduces it with 1 cell of difference
each way.

**Decision**: shadow on by default, Earth Blue, east, drawn before the ocean layer. For
`official-31203-bathymetry`, Earth Blue leaves the depth scale (it is the shadow, not a depth
class); the other eight colors keep their official counts and median-depth order. Agreement with
the official ocean: 32.0% on real data (2,298 / 7,178), 31.88% on the 1-degree fixture (test
threshold 30.8%, measured minus 1 point as before); it was 26.7% / 26.71%.
**Alternative rejected**: keeping Earth Blue as a ranked class with share 1 (keeps nine ranked
colors) would make the Earth Blue total 393 and Brick Yellow 723, so the counts would no longer
equal the official design's.

**Halo**: the owner approved prototype option B (scratchpad `proto/ocean_options.py`): base Dark
Turquoise; Euclidean distance to land (`scipy.ndimage.distance_transform_edt`) <= 1.5 → Medium
Azure; 1.5 < d <= 3.0 → Medium Azure on a Poisson-disk subset (minimum spacing 2.0); farther →
base; shadow on top. Implemented as texture `halo`, with parameters in the recipe. The Poisson-disk
pass visits band cells in a random order from `default_rng((seed, 1))` (the ocean layer's seed,
as for the other textures) and only over the ocean layer's cells (shadow cells excluded), so the
result is not pixel-identical to the prototype (which used `default_rng(31203)` over all ocean
cells) but follows the same rule. On the real land-elevation map: 5,297 Bright Bluish Green,
1,489 Medium Azure, 392 Earth Blue.

Not affiliated with or endorsed by The LEGO Group.

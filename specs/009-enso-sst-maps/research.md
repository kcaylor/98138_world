# Research: ENSO SST Anomaly Maps (009)

All numbers were measured on the real NCEI files (`ersst.v5.199712.nc`, `ersst.v5.198812.nc`,
SHA-256 in R4) through the existing reprojection (`maps/reproject.py`) onto the kit grid hung as B
with the default land shadow (390 cells), leaving 6,788 ocean cells per map. They reproduce the
figures in `run-state.md` exactly. Not affiliated with or endorsed by The LEGO Group.

## R1. The shared legend (FR-006, FR-007, SC-003, SC-005)

**Decision**: colors in the `ocean-sst` order, all kit colors:
Earth Blue, Bright Bluish Green, Medium Azur, Bright Green | Bright Yellowish Green (zero class) |
Brick Yellow, Flame Yellowish Orange, Bright Orange, Vibrant Coral.
Bounds (°C of anomaly): **−9, −1.5, −0.5, −0.25, −0.1, +0.1, +0.3, +0.5, +1.0, +9**.

| Class | Color | Range (°C) | Dec 1997 cells | Dec 1988 cells | One kit (net of shadow) |
|---|---|---|---|---|---|
| 0 | Earth Blue | below −1.5 | 14 | 179 | 3 (393 − 390 shadow) |
| 1 | Bright Bluish Green | −1.5 to −0.5 | 976 | 1,172 | 1,879 |
| 2 | Medium Azur | −0.5 to −0.25 | 640 | 838 | 1,607 |
| 3 | Bright Green | −0.25 to −0.1 | 610 | 672 | 601 |
| 4 | Bright Yellowish Green | −0.1 to +0.1 | 1,747 | 1,882 | 1,060 |
| 5 | Brick Yellow | +0.1 to +0.3 | 707 | 777 | 725 |
| 6 | Flame Yellowish Orange | +0.3 to +0.5 | 553 | 579 | 599 |
| 7 | Bright Orange | +0.5 to +1.0 | 1,008 | 635 | 601 |
| 8 | Vibrant Coral | +1.0 and above | 533 | 54 | 601 |

Extra tiles beyond one kit (shadow counted against Earth Blue): **1997: 1,114** (Earth Blue 11,
Bright Green 9, Bright Yellowish Green 687, Bright Orange 407); **1988: 1,155** (Earth Blue 176,
Bright Green 71, Bright Yellowish Green 822, Brick Yellow 52, Bright Orange 34).

**Derivation** (main thread, run-state "Legend derivation"): colors fixed in the `ocean-sst` order;
inner bounds searched over {±0.1, ±0.15, ±0.2, ±0.25, ±0.3, ±0.4, ±0.5, ±0.6, ±0.75, ±1, ±1.25,
±1.5}; constraints: zero inside the middle (Bright Yellowish Green) class; at least three classes
on each side beyond ±0.25 with a bound at or beyond −0.5 and +0.5, and the outermost inner bound in
[1.0, 1.5] in magnitude; objective: minimise the larger map's extras, then the sum (FR-007).

**Outer bounds ±9**: `bins` needs n+1 bounds for n colors (`maps/recipe.py` `_classification`).
`classify.py` assigns classes with `searchsorted(bounds[1:-1], v, side="right")`, so the outer
bounds never change a class: values below −1.5 take class 0 and values ≥ +1.0 take class 8 (the
end classes are open). The outer bounds only feed the report's `outside_bounds` count and the blend
distance (unused here, FR-008). ±9 lies outside every value in both months (measured minimum and
maximum anomalies: 1997 −4.76 / +4.93 °C, 1988 −3.54 / +1.40 °C) and inside the file's
`valid_min`/`valid_max` (±12), so `outside_bounds` is 0 for both maps and the build output shows
the end classes as "below −1.5" and "+1.0 and above". Precedent: `land-elevation` closes its bins with 9000 m. Class membership is half-open,
[lower, upper): a value equal to a bound takes the upper class.

**Alternatives rejected**:
- *Pure minimisation with free color order* (owner question in run-state): collapses −2 to −0.5 °C
  into one color, so La Niña's cold tongue disappears; breaks FR-006 (cold-to-warm reading).
- *Greens on the cold side ramp* (605 extras): fewer extras but the order no longer reads cold to
  warm (FR-006, Constitution III).
- *Symmetric legend* (−1.25, −0.5, −0.25, −0.1, +0.1, +0.25, +0.5, +1.25): 1,439 extras for the
  larger map.
- *Trial bounds of the spec* (−1.5, −1, −0.5, −0.25, +0.25, +0.5, +1, +1.5): near-zero class of
  2,909/3,132 cells against 1,060 Bright Yellowish Green, about 2,000 extras.
- *A non-kit color for the zero class*: every non-kit tile counts in full as extra, so no non-kit
  color can lower the total below a kit color with supply (SC-005 holds with kit colors only).
- *Per-map or rank-based legends*: out of scope (spec); they break the tile-for-tile comparison.
- *Real outer bounds (e.g. −3, +3)*: would count cells as "outside" and clamp them anyway; ±9 says
  plainly that the end classes are open-ended while still satisfying the n+1 rule.

## R2. Reading the per-month files (FR-002, FR-003, edge cases)

Facts (file inspected with `scipy.io.netcdf_file`): netCDF-3 classic (signature `CDF\x01`);
dimensions `time=1, lev=1, lat=89, lon=180`; variables `time`, `lev`, `lat` (−88..88 by 2), `lon`
(0..358 by 2), `sst` and `ssta`, both float32 `(time, lev, lat, lon)` with `_FillValue = -999.0`,
`scale_factor = 1.0`, `add_offset = 0.0`, `units = "degree_C"`; global `date_modified =
2017-06-30T12:18:00Z`, `license = "No constraints on data access or use"`, `climatology` = 1971–2000
(Xue et al. 2003). 10,988 valid and 5,032 missing cells per month.

**Decision**: in `read_netcdf3`, after fill/scale handling, drop every axis before the last two
whose size is 1; then a 2-D array is the field; a 3-D array keeps the existing rules (`reduce =
"annual-mean"` needs 12; otherwise error); anything else (a leading axis > 1 with no rule, or more
than one leading axis > 1) raises `ValueError` naming the variable's dimensions and sizes, e.g.
`ssta has leading axes time=2, lev=1; declare a reduce rule`. A declared `annual-mean` on a field
with no 12-step axis keeps today's error ("annual-mean needs 12 months, found 1"). `_FillValue`
-999 is already handled by the existing `missing_value`/`_FillValue` loop (FR-003); a test pins it.

Before opening, the reader checks the first 4 bytes: `CDF\x01` or `CDF\x02` proceed; `\x89HDF`
raises `ValueError("<path>: not a netCDF-3 classic file (netCDF-4/HDF5 signature); this reader
reads netCDF-3 only")`; anything else raises "not a netCDF-3 classic file". Today scipy raises a
`TypeError` with a less clear message.

`build._layer_classes` wraps `ValueError` from `read_dataset` in `MapBuildError("<cls>: cannot read
<dataset id>: <message>")`, so `map build`/`map check` exit 1 with "Cannot build …" instead of a
traceback (`cli/map.py` catches `MapBuildError` only). Pinned downloads cannot reach this path with a
wrong file (checksum first), but `[ocean.local]` netCDF files can.

**Alternatives rejected**: a per-entry `squeeze` or `select` declaration in the registry (format
change, not needed: the squeeze is always safe for size-1 axes); `netCDF4`/`h5netcdf` dependency
(owner decision, deferred with the 2026–27 swap); reading `sst` minus a climatology ourselves
(the file's own `ssta` is the documented anomaly, spec Assumptions).

## R3. Recipe key `arrangement` and precedence (FR-010–FR-014)

**Decision**:
- `maps/recipe.py`: `_TOP_KEYS` gains `arrangement`. Value must be a string accepted by
  `layout.arrangement.parse_arrangement` (A/B/C any case, or `europe-africa`, `americas`,
  `asia-australia`); otherwise `RecipeError("arrangement", "must be one of A, B, C,
  europe-africa, americas, asia-australia")` (non-strings: same message). `Recipe` gains
  `arrangement: Optional[Arrangement] = None` (None = key absent). Format stays "1" (precedent:
  `[shadow]`, `specs/004-map-recipes/contracts/recipe-format.md`).
- `maps/build.py`: `resolve_arrangement(recipe, arrangement=None) -> (Arrangement, source)` with
  source `"option"` (an arrangement was passed: CLI `--arrangement` or a library argument),
  `"recipe"` (key present), else `"default"` (A). `build_map`/`check_recipe` call it when
  `arrangement` is None; the report gains `arrangement_source`.
- `cli/options.py`: `arrangement_option(required=False, default="A")` keeps its signature;
  `map build` and `map check` call `arrangement_option(default=None)` so "not given" is None, with
  help text "default: the recipe's `arrangement`, else A". `layout arrange` (required) is unchanged.
- CLI output line: `Arrangement: B (americas, frames 3·1·2, America in the centre) - from the
  recipe` / `- from --arrangement` / `- default`.
- `map recipes` gains an `arrangement` column (recipe value, else `A`).

**Rationale**: the explicit flag must win (owner); Click's `default="A"` cannot tell "not given"
from "A", hence `None`. Resolving in `build_map` gives library callers the same rule (FR-011).
The layout keeps recording only `metadata.arrangement` (no source), so layouts of existing recipes
stay byte-identical (SC-006).

**Alternatives rejected**: a `ParameterSource` check in Click (works for the CLI only, not for
library callers); recording the source in the layout (layout format change, not required);
a new recipe format "2" (breaks every existing recipe file for no gain).

## R4. Registry entries (FR-001)

**Decision**: two `download` entries following `ersst-v5-ltm-1991-2020`; full text in
[contracts/datasets.md](contracts/datasets.md).

| id | version | filename | size | SHA-256 |
|---|---|---|---|---|
| `ersst-v5-1997-12` | `v5-1997-12` | `ersst.v5.199712.nc` | 134,832 | `9f96dbe3aadf8b261e607a8337de02425c65e67803929c592bf1271b2c4e9ebe` |
| `ersst-v5-1988-12` | `v5-1988-12` | `ersst.v5.198812.nc` | 134,832 | `f6d21ff447213c6abd32ee32bb1a4a26b5d847a5abb3dee33baed3f250bb14db` |

Both checksums re-measured on 2026-11-22 from the downloaded files. Variable `ssta` (units `degC`,
anomaly against 1971–2000), `class_rule = {"missing_is_land": true}`, grid node-registered 2°.

The registry has one `doi` field, which `echo_citations` prints after the citation. It holds the
paper DOI 10.1175/JCLI-D-16-0836.1 (as in the existing ERSST entry); the dataset DOI
10.7289/V5T72FNM is written into the `citation` text as a second, data citation ("Dataset: Huang,
B., et al., 2017: NOAA Extended Reconstructed Sea Surface Temperature (ERSST), Version 5. NOAA
NCEI. doi:10.7289/V5T72FNM"), so both appear in the build output, the report and layout metadata
(US1 scenario 5) with no registry format change. License text: "Public domain (U.S. Government
work, NOAA NCEI); the file's license attribute reads 'No constraints on data access or use'".

**Alternative rejected**: a second `dataset_doi` registry field (format change).

## R5. Reports and output (FR-012, FR-015, FR-016, US1 scenario 5)

**Decision** (layout JSON unchanged; one additive report JSON field):
- report `arrangement_source`: `"recipe"` | `"option"` | `"default"` (R3). This is the only report
  format change; FR-012 requires the report to state the source. Additive (readers that ignore
  unknown keys are unaffected), but the run policy reserves file-format changes for the owner, so it
  is escalated with the recommendation to accept.
- `maps.suitability.extra_tiles(supply_rows) -> int`: Σ over the layer report's existing `supply`
  rows of `max(0, used − supplied)` (`supplied` is 0 for a color not in the kit, `used` already
  includes the shadow via `extra_use`) — the same quantity `parts list --kits 1` reports as
  `to_buy` for that part with no spares, loose or missing parts (`parts/owned.py`, feature 005). A
  library function, not a stored report field, so the report format does not grow.
- units for the legend header come from the recipe's layer (`layer.dataset.variables[variable]
  ["units"]`), passed to `echo_report` by `map build`/`map check`; `degC`/`degree_C` render as
  `°C`, others as given, none → no unit. Not stored in the report.
- `echo_report` for a `bins` layer prints a legend block: one line per color, `color  range  cells`,
  with the first class "below b1", the last "b(n−1) and above", others "b(i) to b(i+1)" (2 decimals
  stripped of trailing zeros, sign shown), units appended. Then, for every layer,
  `Tiles beyond one kit: N` (N = `extra_tiles(layer["supply"])`).

**Alternatives rejected**: storing `units` and `extra_tiles` in the report (more format change
for values derivable from the recipe and the supply rows).

**Rationale**: the report already carries `class_bounds` and per-color `supply`; FR-015 only needs
them rendered. A single extra-tile number is what SC-004 bounds and what the maker compares with
`parts list --kits 1`.

## R6. Fixtures (FR-019, SC-001)

**Decision**: two derived fixtures, `cli/tests/fixtures/datasets/ersst_v5_199712_ssta.nc` and
`ersst_v5_198812_ssta.nc`, written by a new `make_ersst_month(dataset_id)` in
`cli/tools/fixtures004/make_fixtures.py` (with `--only` to pick fixtures): netCDF-3 classic, the
source's dimensions `time=1, lev=1, lat=89, lon=180` and coordinate variables, one variable
`ssta(time, lev, lat, lon)` packed as int16 with `scale_factor = 0.01`, `add_offset = 0.0`,
`_FillValue = -999` (int16), `units = "degree_C"`; `sst` dropped. About 34 KB each; the fixture
total stays under the 300,000-byte budget of `test_no_large_data.py` (195,208 bytes today). Each has a
`.source.json` (fixture, dataset, version, source_sha256, source_url, method, license, citation,
doi, generator, disclaimer, units, sha256) as the existing ones.

`cli/tests/conftest.py` `fixture_registry` points the two new entries at the fixtures (filename,
size, sha256 rewritten; variables kept), so `place_all()` caches them and every test parametrised
over `bundled_recipes()` (references, performance, sheets, parts) keeps working.

Measured on the fixture data (values rounded to 0.01 °C): extras 1997 **1,126**, 1988 **1,159**;
Niño 3.4 region 68 cells, 100 % warm (≥ +0.5) in 1997 and 100 % cold (≤ −0.5) in 1988; filled
cells 237 (3.5 %, under the 5 % threshold).

**Alternatives rejected**:
- float32 full grid (≈ 65 KB each): total ≈ 326 KB, over the 300 KB budget;
- 4° subsample (every other row and column, ≈ 17 KB): 4,296 of 6,788 cells (63 %) filled from
  neighbours, a `filled` warning and a poor proxy for the real counts;
- committing the downloaded files: forbidden (004 FR-025, project rules);
- packed fill −999 collides with a valid −9.99 °C: no ERSST anomaly in either month is below
  −4.8 °C, and `valid_min` is −12, so the collision is documented, not reachable in the fixtures.

## R7. SC-004 bound and SC-002 check

**Decision**: SC-004 bound **≤ 1,200 extra tiles per map** (run-state; real 1,114 / 1,155,
fixture 1,126 / 1,159). Tested on the fixtures, and documented in the runbook with the real numbers.
SC-002 test: kit cells (display coordinates, B) whose centre (`KitProjection.cell_center` of the
kit column) lies in 5° S–5° N, 170° W–120° W; ≥ 90 % in classes with lower bound ≥ +0.5 (1997) or
upper bound ≤ −0.5 (1988).

## R8. Documentation (FR-017)

README "Maps from recipes" table gains two rows and the recipe count changes from four to six; a
short "ENSO maps" paragraph gives the legend table (R1), the default arrangement B and the planned
2026–27 swap (needs a netCDF-4 reader). `docs/runbook.md` gains a section with the four commands of
SC-007 and the expected extra-tile numbers. `specs/004-map-recipes/contracts/recipe-format.md` is
not edited (feature 004 artifact); the new key is specified in this feature's contract.

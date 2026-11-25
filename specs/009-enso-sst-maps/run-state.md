# Run state: ENSO SST maps (strong El Niño and La Niña, Pacific-centred)

Source: prompt (2026-11-22): "build both a strong La Niña and a strong El Niño SST map ... Pacific
centric ... use as much as possible the parts list from the original set, some additional ocean
tiles allowed"
Phase: done (implement + converge)
Status: done
Branch: 009-enso-sst-maps
Updated: 2026-11-22 (implement done)

## Findings before specify
- NCEI per-month ERSST v5 files (ersst.v5.YYYYMM.nc, 134,832 B) are netCDF-3 classic for months
  before 2010 (date_modified 2017-06-30, stable); 2010+ files are netCDF-4 (unreadable without a new
  dependency). Variables sst and ssta (anomaly vs 1971-2000), shape (1, 1, 89, 180); the reader
  needs to squeeze the singleton lev axis.
- Niño 3.4 (5S-5N, 170W-120W) ssta: Dec 1997 +2.28, Nov 1997 +2.46, Jan 1998 +2.33;
  Dec 1988 -1.97, Nov 1988 -1.99, Jan 1989 -2.01; Dec 1973 -2.26; Dec 1999 -1.74.
- Arrangement B (3·1·2): 6,788 ocean cells net of a 390-cell shadow.
- ssta distribution on the kit grid (B, net of shadow), cells per bin
  (<-1.5, -1.5..-1, -1..-0.5, -0.5..-0.25, ±0.25, 0.25..0.5, 0.5..1, 1..1.5, >1.5):
  Dec 1997: 14, 219, 757, 640, 2909, 708, 1008, 247, 286
  Dec 1988: 179, 263, 909, 838, 3132, 778, 635, 54, 0
- Kit ocean supply: bluish green 1879, medium azur 1607, yellowish green 1060, brick yellow 725,
  bright green 601, orange 601, coral 601, flame yellowish orange 599, earth blue 393 (shadow takes 390).

## Open questions
- (owner, confirm) Legend color order is constrained to read cold to warm with zero in the middle
  class; minimisation of extra tiles works only within that order. Pure minimisation could put the
  near-zero class on Bright Bluish Green (1,879, the largest supply) at the cost of a readable scale.
  Recommended: keep the constraint (spec FR-006/FR-007).

## Decisions
- scoping: maps show the SST anomaly (ERSST v5 ssta) (user)
- scoping: El Niño = Dec 1997 for now; the user expects to switch the El Niño map to the 2026-27
  event once it peaks (a month or two). La Niña = Dec 1988 (user; recommended pair accepted)
- scoping: one fixed °C anomaly legend shared by both maps; bins and color order chosen to keep
  extra (non-kit or over-supply) tiles to a minimum; extras reported in the parts list (user)
- scoping: optional recipe key `arrangement`, both ENSO recipes default to B; --arrangement
  overrides (user)

- specify: recipes `ocean-el-nino`, `ocean-la-nina`; datasets `ersst-v5-1997-12`,
  `ersst-v5-1988-12` (agent; naming pattern of ocean-sst / ersst-v5-ltm-1991-2020; id has no year so
  the 2026-27 swap keeps it)
- clarify: `arrangement` stays an optional key under recipe format "1" (precedent: `shadow`) (agent)
- clarify: explicit `--arrangement` wins; output and report say the source (recipe, command line,
  default); CLI must distinguish "not given" from "A" (agent)
- clarify: extras = non-kit colors + over-supply, shadow counted; minimise max per-map extras, then
  sum (agent)
- clarify: legend reads cold to warm, zero class in the middle; kit colors only unless a non-kit one
  lowers extras (agent; owner to confirm, see Open questions)
- clarify: no `blend` texture on the ENSO ocean layers (exact tile-for-tile comparison) (agent)
- clarify: reader drops all size-1 leading axes; larger leading axis still needs a reduce rule (agent)
- clarify: °C ranges shown in build/check output and report JSON; not on build sheets (follow-up)
  (agent)
- clarify: extras reported by existing build report + `parts list/export --kits 1`; no new command
  (agent)
- clarify: SC-004 extra-tile bound per map is set in plan from data (agent)

- plan: legend = ocean-sst color order, bounds [-9, -1.5, -0.5, -0.25, -0.1, 0.1, 0.3, 0.5, 1.0, 9];
  outer ±9 only close the list (classify.py searchsorted on inner bounds; precedent land-elevation
  9000); end classes open, `outside_bounds` 0 (data range 1997 -4.76..+4.93, 1988 -3.54..+1.40)
  (agent; research R1)
- plan: counts re-measured with the worktree code on the real files: identical to the derivation
  (1,114 / 1,155 extras; Niño 3.4 68/68 cells in the expected classes both months) (agent)
- plan: reader drops size-1 leading axes, errors name dims for larger ones, keeps the annual-mean
  error, rejects netCDF-4 by the `\x89HDF` signature; reader ValueError -> MapBuildError (exit 1)
  (agent; research R2)
- plan: `resolve_arrangement(recipe, arrangement)` in maps/build.py, sources recipe/option/default;
  `arrangement_option(default=None)` for map build/check only; layout records no source (SC-006)
  (agent; research R3)
- plan: dataset DOI 10.7289/V5T72FNM goes into the citation text (registry has one doi field, which
  keeps the paper DOI as in ersst-v5-ltm-1991-2020); no registry format change (agent; research R4)
- plan: extra tiles = `extra_tiles(supply rows)` helper, legend units from the recipe; neither
  stored in the report (keeps report format change to `arrangement_source` only) (agent; R5)
- plan: fixtures = full 2° grid, dims (time=1, lev=1, 89, 180), ssta int16 scale 0.01, _FillValue
  -999, ~34 KB each (float32 would exceed the 300 KB fixture budget; a 4° subsample fills 63% of
  cells); fixture extras 1,126 / 1,159; generated by fixtures004 `make_ersst_month --only` (agent;
  research R6)
- plan: SC-004 bound <= 1,200 per map, tested on fixtures (agent; research R7)
- plan: agent-context script not run (plan template does not require it); CLAUDE.md gets one short
  009 line at implement time (T035) (agent)
- tasks: 35 tasks; Phase 2 foundational (reader, registry, fixtures, conftest) blocks the stories
  because tests parametrised over bundled_recipes() need the fixtures (agent)
- analyze: fixed HIGH I1 (spec edge case said outside-bound values are counted; with ±9 outer bounds
  the count is 0) in spec.md; fixed HIGH C1 (missing data-model constrained-field citations) in
  tasks T004, T005, T014, T015, T021, T022, T023; fixed MEDIUM C2 (FR-009 title/description and
  filled-share edge case untested) in T021/T023; clarified T013's reader-error fixture (agent)

## ESCALATE
- (resolved 2026-11-22, see Decisions) report field `arrangement_source`; legend order constraint.

- implement: owner-level choices relayed by the coordinating session and recorded as agent
  decisions: accept the additive report field `arrangement_source` (recipe | option | default);
  keep the cold-to-warm legend rule (agent)
- implement: `MapResult` gains `arrangement` (the resolved arrangement) so the CLI prints the
  arrangement actually used; library-only, no file format change (agent)
- implement: `--arrangement` help for `map build`/`map check` drops "(default)" after A and adds
  "Default: the recipe's `arrangement`, else A; an explicit --arrangement wins." (agent)
- implement: the two new registry rows are written as UTF-8 (Niño, °C, −) like the recipe files;
  the rest of datasets.json is unchanged byte for byte (agent)
- implement: `Tiles beyond one kit: N` is printed for every layer (0 for land), as the contract
  says; the legend block only for `bins` layers (agent)

## Implementation results (2026-11-22)
- T001 baseline: 965 passed (worktree venv, uv, Python 3.11). Final: 1,033 passed, 0 failed
  (`.venv/bin/pytest`, offline). No lint is configured in pyproject.toml.
- T008 fixtures from the verified real files (SHA-256 as below): ersst_v5_199712_ssta.nc and
  ersst_v5_198812_ssta.nc, 34,568 bytes each; all fixtures 268,344 bytes (< 300,000).
- T033 SC-006: official-31203, official-31203-bathymetry, ocean-sst, land-elevation built from the
  fixtures with this branch (no flag), this branch (explicit A) and the base commit a5542f3: layout
  JSON (generated_at removed) identical in all three for every recipe.
- T034 real data (cached copies of the verified files, no download): extra tiles 1,114 (El Niño:
  Earth Blue 11, Bright Green 9, Bright Yellowish Green 687, Bright Orange 407) and 1,155 (La Niña:
  Earth Blue 176, Bright Green 71, Bright Yellowish Green 822, Brick Yellow 52, Bright Orange 34);
  `parts list --kits 1` gives the same totals and per-color quantities. Niño 3.4: 68/68 cells
  >= +0.5 in 1997, 68/68 <= -0.5 in 1988. Filled 237 cells (3.5 %) both.
- converge: no gaps found against spec, plan and tasks; tasks.md unchanged by converge.

## Blocked tasks
(none)

## Deferred findings
- Follow-up: El Niño 2026-27 swap needs a netCDF-4 reader for NCEI files from 2010 on (new dependency,
  owner decision); design keeps it a dataset-entry + recipe `dataset`/title change.
- Follow-up: °C legend on build sheets (feature 006 legend shows colors and counts only).
- analyze M1 (MEDIUM, terminology): FR-012 says "command line"; the report value is "option"
  (covers the CLI flag and a library argument); the CLI prints "from --arrangement". Contract
  documents it; spec wording left.
- analyze M2 (MEDIUM): fixtures are int16-packed (0.01 °C) while the source is float32; FR-019
  "keep the structure" is met (dims, singleton axes, _FillValue -999), dtype differs. Fixture
  counts differ from real ones by <= 12 cells per map; tests use the SC-004 bound, not exact counts.
- analyze L1 (LOW): packed fill -999 equals a valid -9.99 °C; unreachable in both months (min
  -4.76 °C); documented in research R6.
- analyze L2 (LOW): legend text "+1 and above" (trailing zeros stripped) vs "+1.0" in recipe
  comments; cosmetic.
- Observation (real data): 1,006 of 1,747 (1997) and 1,005 of 1,882 (1988) Bright Yellowish Green
  cells lie at latitude >= 60 (mostly ice-covered Arctic rows where ssta is ~0); that alone exceeds
  the color's shortfall (687 / 822). Handling sea-ice/high-latitude cells separately (e.g. a fixed
  background color there) could remove most extras; owner decision, out of scope for 009.
- analyze L3 (LOW): real-data checks (SC-002/SC-004 on the downloaded files, SC-007) are
  maintainer steps (T008, T034) because tests are offline.

## Legend derivation (main thread, 2026-11-22)
- clarify ESCALATE "color order vs fewest extras": resolved (agent decision): the rule stands; a
  cold-to-warm ramp may still put a high-supply kit color on the zero class, so it costs nothing
  the order rule forbids. Pure minimisation was tried and rejected: it collapses all of -2..-0.5 °C
  into one color (La Niña invisible).
- Search (B, net of shadow, 6,788 cells per map): colors fixed in the ocean-sst order (eb, bg, az,
  gr, yg, ty, fo, or, co, all kit); bounds from {±0.1, .15, .2, .25, .3, .4, .5, .6, .75, 1, 1.25,
  1.5}; constraints: zero inside the middle (yg) class; >= 3 classes on each side beyond ±0.25 with
  a bound at or beyond -0.5/+0.5 and the outermost bound in [1.0, 1.5] in magnitude; minimise the
  larger map's extras, then the sum.
- Result: bounds -1.5, -0.5, -0.25, -0.1, +0.1, +0.3, +0.5, +1.0 (outer ±9 for bins)
  1997-12 counts 14, 976, 640, 610, 1747, 707, 553, 1008, 533 -> extras 1,114
    (eb 11, gr 9, yg 687, or 407)
  1988-12 counts 179, 1172, 838, 672, 1882, 777, 579, 635, 54 -> extras 1,155
    (eb 176, gr 71, yg 822, ty 52, or 34)
  Symmetric alternative (-1.25,-0.5,-0.25,-0.1,±...) costs 1,439. A ramp with the greens on the
  cold side costs 605 but breaks the cold-to-warm reading (rejected).
- SC-004 bound: <= 1,200 extra tiles per map.
- SHA-256: ersst.v5.199712.nc 9f96dbe3aadf8b261e607a8337de02425c65e67803929c592bf1271b2c4e9ebe;
  ersst.v5.198812.nc f6d21ff447213c6abd32ee32bb1a4a26b5d847a5abb3dee33baed3f250bb14db
  (both 134,832 bytes).

> **Note (feature 010, 2026-11-22)**: at the owner's request both ENSO recipes now default to
> `arrangement = "D"` (`pacific`, the date line centred; not among the building instructions'
> combinations; see `specs/010-pacific-arrangements/`). This supersedes FR-013's value B; B is still
> available with `--arrangement B`. Measured with the real ERSST files: in D the land shadow takes
> 387 Earth Blue tiles (390 in B) and the tiles beyond one kit are 1,114 (El Niño, as in B) and
> 1,152 (La Niña; 1,155 in B); in E 1,112 and 1,158.

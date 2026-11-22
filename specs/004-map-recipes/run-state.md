# Run state: 004 map recipes and canonical datasets

Source: prompt (fallback 2B). Scoping answers taken from the user's brief of 2026-11-22 and
`docs/vision.md` (outcome, scope, constraints, priority), relayed by the coordinating agent; no
separate four-question round was held.
Phase: done
Status: done (uncommitted; awaiting user review)
Updated: 2026-11-22

## Open questions
1. Rebrickable CSV license (still open). rebrickable.com/downloads/ returned HTTP 402 to the
   fetcher again on 2026-11-22; no license was found. `part_colors.json` cites the pinned
   Rebrickable snapshots (URL, SHA-256, access date), records facts with citations, does not
   redistribute the files, and states the open question in `source.license_note`. No license was
   invented. Needs the user to confirm Rebrickable's terms.

(Q1–Q6 answered by the user on 2026-11-22; see Decisions.)

## Decisions
- user (2026-11-22): Q1 recipe format = TOML via `tomllib` (user, accepted recommendation)
- user (2026-11-22): Q2 downloads are opt-in: `map build --fetch` downloads missing pinned
  datasets before building; without `--fetch` a build with a missing dataset fails naming
  `dataset fetch <id>` and `--fetch`. Differs from the planner's recommendation; spec FR-010,
  US2 scenarios 5/7, contracts/cli.md, tasks T028/T032 updated. Tests mock the network (user)
- user (2026-11-22): Q3 provenance = new `metadata.map` block, layout schema stays 2.0 (user)
- user (2026-11-22): Q4 colors beyond the kit = curated committed `part_colors.json` from
  checksum-pinned Rebrickable catalog files, LEGO/BrickLink IDs cited as in 003; if the Rebrickable
  CSV license cannot be confirmed, cite the source and keep the question open; check the 6141 vs
  4073 part number against the pinned files (user)
- user (2026-11-22): Q5 two acceptance tiers (exact 10,240/10,240; derived: land identical,
  within supply, >= 24% ocean agreement) (user)
- user (2026-11-22): Q6 local data files allowed in recipes with declared checksum, citation and
  license (user)
- specify: branch `004-map-recipes` created with `git checkout -b` (the create-new-feature script
  created the directory but did not switch branches) (agent)
- specify: user decisions from 003 review recorded in specs/003-kit-reference-data/run-state.md:
  no CSV disclaimer; four coin-flip colors stay as in overrides.json; 3062b exemption stays (user)
- specify: two-tier acceptance for the official design, figures measured in research (agent,
  provisional pending Q5)
- clarify: 9 items auto-resolved (see spec Clarifications) (auto-resolved)
- clarify: rank-to-supply texture swaps cells in pairs so counts never change (auto-resolved)
- plan: projection = equirectangular, left edge 168.9° W, equator row 42.2, 26.3 rows/rad; mask agreement 94.2% (Miller 90.9%, Mercator 87.0%) (agent, measured R2)
- plan: bathymetry/elevation = ETOPO 2022 60s surface via a pinned OPeNDAP subset (every 10th sample, 9,357,398 B, public domain); full 478 MB file noted as alternative (agent: same canonical data, 50x smaller; byte-determinism checked)
- plan: SST = ERSST v5 LTM 1991-2020 (PSL, 1,160,004 B, netCDF-3, public domain); OISST 1° rejected because it is HDF5 and needs a new dependency (agent)
- plan: no new third-party dependencies; SciPy (BSD-3, already installed via scikit-image) declared explicitly; tomllib/urllib/hashlib from the standard library; DODS parsed with NumPy (agent)
- plan: classification adds `rank` (given shares) so the derived official recipe can use the official counts (agent)
- plan: dataset cache helper moves into the package; the 003 maintainer tool imports it (agent: one definition)
- plan: suitability thresholds variance lost 50%, filled 5%, ΔE00 5 (agent defaults, recorded in reports)
- plan: speckit `update-agent-context.sh` not run, to avoid editing CLAUDE.md/AGENTS.md (agent)
- tasks: 67 tasks (Setup 2, Foundational 14, US1 9, US2 8, US3 15, US4 8, US5 4, Polish 7) (agent)
- analyze: added `rank` to spec FR-015 and Key Entities (HIGH, mechanical); T040 no longer depends on Q6 local files; `--preview` added in T045 instead of a stub; T015 before T014; FR-018 covered by T065 docs (agent)

- implement: TOML recipes parsed with `tomllib`; errors carry the key path (agent: contract)
- implement: Q2 applied: `map build --fetch` (only build has it; `map check` with a missing dataset
  exits 3 naming `dataset fetch <id>`). NEEDS USER REVIEW: adding `--fetch` to `map check` too
  (CLI flag; not added) (agent)
- implement: error output of the new commands also ends with the disclaimer line (agent:
  constitution VIII)
- implement: a background layer with more than one color must use `texture.kind = "mix"`; blend
  is rejected for categorical classifications (agent: recipe rule, NEEDS USER REVIEW as format rule)
- implement: local data files (Q6): `[<layer>.local]` with path, format (npy/netcdf3/dods),
  sha256, variable, citation, license (+ lat/lon for npy, optional split_at/missing_is_land/fill/
  title/units); `variable` lives inside the local table; .npy rows run south to north (agent:
  NEEDS USER REVIEW, file format others use)
- implement: categorical data on a non-kit grid is reprojected by the most frequent category per
  cell (agent)
- implement: part_colors.json: 14 plate colors for 6141 (White + 13 beyond the kit: Black, Dark
  Green, Bright Green, Bright Yellowish Green, Sand Green, Brick Yellow, Sand Yellow, Nougat,
  Medium Nougat, Reddish Brown, Dark Brown, Medium Stone Grey, Dark Stone Grey) and the kit's 9
  tile colors for 98138. Join rule: Rebrickable id = LDraw CODE with matching names, BrickLink by
  exact Rebrickable name; element = lowest numeric element with design_id = part. Excluded:
  Olive Green (Rebrickable 326; LDraw code 326 is Yellowish Green, so no verified LEGO id).
  All kit rows agree with the snapshots (agent)
- implement: part-number finding (Q4): the pinned Rebrickable elements.csv files element 614101
  and every 1x1 round plate element under part_num 6141 (design_id 6141) and lists no element
  under 4073. Feature 003's data (`part_ids: ["6141", "4073"]`) is not wrong (4073 is BrickLink's
  number, from Brickset), so no data was changed; the comment in `layout/position.py` and
  cli/README that said "BrickLink/Rebrickable 4073" now say "Rebrickable 6141, BrickLink 4073".
  BrickLink's 4073 was not checked against a pinned BrickLink part page (agent)
- implement: land-elevation ocean background = the kit's nine tile colors mixed in the official
  counts (cluster 1.5): the only kit-tile mix that covers 7,178 cells within one kit's supply
  (blues alone supply 3,879). It looks busy next to the land data. NEEDS USER REVIEW (product look)
- implement: land-elevation bins (m) 0,150,300,500,750,1000,1500,2000,2500,3000,9000 on Dark
  Green -> White; no empty class, min neighbour ΔE00 11.2 on real data (agent)
- implement: Miller agreement measured 0.909375 (research had rounded to 91.0%); projection file,
  spec and research now say 90.9%. Mercator best fit ties at 0.870 (42.7/18.6 vs 41.7/19.2) (agent)
- implement: fit-projection uses a coarse-to-fine search (0.5 then 0.1); reproduces the committed
  file exactly ("no differences") in ~2 s (agent)
- implement: derived-tier fixture threshold 25.7% (fixture measured 26.71%, minus 1 point) (agent)
- converge: assessed every FR/SC/edge case against code and tests; no new tasks (agent)

## Results (T066, real data in the session scratchpad cache)
- official-31203: 10,240 / 10,240; validate FULLY BUILDABLE, 0 violations; 0.29 s
- official-31203-bathymetry: land 3,062/3,062; ocean 1,918/7,178 = 26.7%; counts = official
  counts; median depths in order; FULLY BUILDABLE; variance lost 12.5%, 69 cells filled (1.0%);
  no warnings; 0.40 s
- ocean-sst: FULLY BUILDABLE, 0 violations; 311 cells filled (4.3%), variance lost 0.0%; no
  warnings; 0.36 s
- land-elevation: buildable as a layout; validate 71.6% (PARTIALLY BUILDABLE), 9 violations = the 9
  non-kit plate colors (color_unavailable on 6141); warning `beyond_kit`; variance lost 8.6%,
  26 land cells filled (0.9%); 0.33 s
- fit-projection --check and partcolors build --check: no differences
- tests: 666 passed (436 before), offline

## Blocked tasks

## Deferred findings
- [MEDIUM] Rebrickable CSV license could not be confirmed (HTTP 402 again at implement); see Open questions.
- [MEDIUM] ETOPO subset checksum depends on NCEI's OPeNDAP server producing the same bytes; a server change fails loudly and needs a new registry version. Full-file alternative's checksum not measured (478 MB).
- [MEDIUM] SC-006 timing is tested on fixtures (T062); real-data timing only in the quickstart run (T066).
- [RESOLVED] Derived-tier threshold: full data 26.7%, fixture 26.71%, test threshold 25.7%.
- [RESOLVED] 6141/4073: see Decisions (Rebrickable 6141, BrickLink 4073; 003 data unchanged).
- [LOW] ERSST file's `climatology` attribute names 1971–2000 although the file is the 1991–2020 normal; recorded in registry notes.
- [LOW] ERSST leaves 4.3% of ocean cells to nearest-fill, close to the 5% warning threshold.

# Run state: Rainfall map (013)

Source: owner-approved design "3A" and two owner decisions relayed by the coordinating session
(2026-11-22); prototype material (read-only, outside the repo): `proto-rain/NOTES.md`,
`SOURCES.md`, `scripts/rain.py`, `rain2.py`, `rain3.py`, `round3/3A-darkblue.png`,
`round3/stats3.json`. Path 2B (no prior spec): the design and decisions answered the scoping
questions, so none were asked.
Phase: done (implement + converge)
Status: done
Branch: 013-rainfall (from origin/main at 32a3a11, which includes 012)
Updated: 2026-11-22

## Open questions (owner review; work proceeded with the choice below)
1. **Sea-ice product and rule (decision 2).** NSIDC has no pinnable public climatology file: the
   climatology products (NSIDC-0192, -0051) need an Earthdata login, and the CDR's whole-record
   monthly aggregate is rewritten under a new name every month. Chosen: NOAA/NSIDC CDR v6 (G02202)
   per-month files for each hemisphere's minimum month (September north, February south),
   1991–2020: 60 files, 17.8 MB, each pinned by SHA-256 (all matched NSIDC's MD5 manifests). Rule:
   cell mean of the 30-year minimum-month mean ≥ 0.7, or no NSIDC ocean pixel poleward of 60°.
   759 cells against the prototype's 738; 6,705 of 6,786 classified ocean cells agree. Close
   call: threshold 0.6 gives 806 cells (6,692 agree), 0.8 gives 720 (6,694). Recommended: accept.
2. **Multi-file registry entries** (`files`): one entry for 60 files keeps one citation and one
   `dataset list` row; the alternative (60 entries) floods every citation list. Additive to
   `datasets.json` (package data). Recommended: accept.
3. **h5py 3.16.0** (2026-03-06; BSD-3-Clause; cp311 wheels for macOS, manylinux_2_28, musllinux):
   `h5py = "^3.16.0"` in `cli/pyproject.toml`; `h5py==3.16.0` (hashed) in
   `web/requirements-build.txt` only. Recompiling the lock changed nothing else.

## Decisions
- specify: recipe id `rainfall`, title "Rainfall", default arrangement A; dataset ids
  `gpcp-v23-ltm-1991-2020` (version `v2.3-ltm-1991-2020`) and
  `nsidc-cdr-v6-seaice-minimum-1991-2020` (version `v06r00-sep-n-feb-s-1991-2020`) (agent; naming
  like existing entries)
- clarify: netCDF-4 reader with h5py, GPCP pinned as NOAA's original netCDF-4; netCDF-3 reader
  unchanged; routing by registry `format` (user, decision 1)
- clarify: NSIDC sea ice as a reusable dataset override; living-planet unchanged (user, decision 2;
  product and rule: agent, open question 1)
- clarify: CF polar-stereographic latitude/longitude computed in the reader (Snyder 1987);
  matches NSIDC's ancillary grids to 3e-10° (agent; research R3)
- clarify: `sampling = "bilinear"` as a data-layer key, default `mean` (agent; owner design)
- clarify: `[[<layer>.override]]` region or dataset rule; strict bounds on kit cell centres; first
  override wins; shadow and `no_data` first (agent; research R5)
- clarify: `[<layer>.legend]` (`units`, `factor`) for mm/yr (agent; owner "legend shows mm/yr")
- clarify: fixture budget 450 kB → 540 kB (five netCDF-4 fixtures, 129 kB) (agent; test-only rule)
- plan: no constitution violations; no Complexity Tracking entries (agent)
- implement: legend text `4 and above (1460 mm/yr and above)`; secondary bounds printed like the
  primary ones (agent)
- implement: report/provenance gain `sampling` only when not `mean`, `overrides`/`legend` only
  when set, so existing layouts and reports are byte-identical apart from `generated_at` (agent)
- implement: web map page shows "Pinned files: <id>, N files, size, manifest SHA-256" for
  multi-file entries; manifest dataset rows gain `files`/`files_sha256` (additive) (agent)
- implement: the Black shadow / Earth Blue trade-off is left as approved (owner)

## Results (2026-11-22)
- Baseline: CLI 1,131 passed; web 80 (012 run-state).
- Final: CLI `1221 passed`; web `83 passed` (offline, `.venv/bin/pytest`).
- FR-010: the seven existing recipes built from the fixtures in A, B and C (21 variants) with
  `main` and with this branch: layouts and reports identical apart from `generated_at`.
- Real data (`dataset fetch --recipe rainfall`): GPCP 677,810 B, SHA-256 `e72475e6…6281c`
  (same as the prototype's copy); NSIDC 60 files, 17,826,152 B; 33 s. The netCDF-4 GPCP read is
  identical (values and coordinates) to the prototype's netCDF-3 conversion.
- Agreement with prototype 3A (decoded from `round3/3A-darkblue.png`; its counts equal
  `stats3.json`): 10,159 / 10,240 cells (99.21%); land 3,062 / 3,062 (100%); ocean 7,097 / 7,178.
  All 81 differences are the sea-ice edge: 51 cells now White (31 north: Canadian Archipelago,
  Nares Strait, East Greenland/Fram Strait, where NSIDC keeps ≥ 70% ice in September; 20 south:
  Weddell and Ross Sea pack) and 30 no longer White (28 north: Beaufort–Chukchi–Siberian sector
  at 75–80° N, where September ice has thinned below 70% in the 1991–2020 mean; 2 south).
- Counts (A): land 6141 — Brick Yellow 260, Sand Yellow 355, Sand Green 416, Bright Yellowish
  Green 588, Bright Green 380, Dark Green 352, White 711 (Antarctica 595, Greenland 116): equal to
  the prototype. Ocean 98138 — Light Royal Blue 658 (656), Medium Azur 973 (993), Dark Azur 2,029
  (2,032), Bright Blue 1,800 (1,800), Earth Blue 567 (567), White 759 (738), Black 392 (392).
- Pieces beyond one kit: 8,163 (prototype 8,143); 14 lots, to buy in 12 lots.
- Web prebuild (real data, rainfall only): 3 variants, 18.0 MB, 5.4 s, peak memory 169 MB; the
  app serves all 37 requests checked (pages and every file, SHA-256 equal to the manifest); page
  shows Adler, Meier, "60 files", disclaimer.
- New downloads for the Docker prebuild: 18.5 MB (total ~561 MB).

## Blocked tasks
(none)

## Deferred findings
- analyze L1 (LOW): a dataset override re-reads its files for each combination (A, B, C); 0.2 s
  for 60 files, so not cached.
- analyze L2 (LOW): the site preview draws White plates/tiles on the page's white background
  (existing renderer behaviour, as noted in 012).
- analyze L3 (LOW): `http_only` on a `files` entry needs at least one http:// file URL (tested);
  no shipped entry uses it.
- converge: no gaps against spec, plan and tasks.

Not affiliated with or endorsed by The LEGO Group.

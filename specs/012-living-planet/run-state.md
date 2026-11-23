# Run state: Living planet map (012)

Source: owner-approved design relayed by the coordinating session (2026-11-22); prototype material
(read-only, outside the repo): `proto-npp/RECIPE-NOTES.md`, `SOURCES.md`, `scripts/proto5.py`,
`round5/A5.png`, `round5/stats5.md`. Path 2B (no prior spec): the design answered the four scoping
questions, so none were asked.
Phase: done (implement + converge)
Status: done
Branch: 012-living-planet (010 and 011 are taken by local branches `010-pacific-arrangements` and
`011-price-estimates`)
Updated: 2026-11-22

## Open questions (owner review; work proceeded with the conservative choice)
1. **Close call: ETOPO lookup convention vs. cell agreement.** With the nearest ETOPO cell for the
   NPP land/ocean split (the general rule shipped), the build agrees with the prototype's round-5
   grid in 9,797 / 10,240 cells (95.7%): ocean 7,178 / 7,178 (100%), land 2,619 / 3,062. The land
   differences are all swaps between neighbouring NPP classes caused by the blend texture's seeded
   draws shifting when a few cell means change. The prototype used `searchsorted` (the next ETOPO
   sample at or after the pixel centre, up to 1/6° off); with that lookup the build agrees in
   10,240 / 10,240 cells (verified). Recommended: keep nearest (principled, documented); the map
   looks the same and class counts differ by ≤ 15 cells per class. Switching is a one-line change
   in `datasets/readers.py::_land_from_mask`.
2. **HTTP download** (`http_only`): the NTSG host serves the NPP GeoTIFF over HTTP only (HTTPS
   timed out 2026-11-22). The registry now allows `http://` only with a stated reason and a file
   SHA-256 (integrity kept; the file is public). Recommended: accept.
3. **Content checksum** (`content_sha256`): ERDDAP writes the request time into `history`, so file
   bytes differ per request (verified). The pin is a SHA-256 over the decoded variable and
   coordinates; size is still pinned. Recommended: accept; re-pin path in the registry notes.
4. **Download size**: feature 004's SC-009 bound (all bundled-recipe downloads < 15 MB) now holds
   for every recipe except `living-planet` (532 MB: 385 + 147, plus the shared ETOPO); the Docker
   build downloads ~543 MB and needs ~650 MB RAM. Test kept for the others, a separate bound for
   living-planet. Recommended: accept (the owner asked for this dataset).

## Decisions
- specify: recipe id `living-planet`; dataset ids `mod17a3-npp-mean-2000-2015` (version
  `c55-mean-2000-2015`) and `modis-aqua-chla-2013-2024` (version `r2022.0-2013-01-2024-12-stride12`)
  (agent; naming like existing entries)
- clarify: bins bounds with `log10` stay in data units (mg m-3), must be > 0, are compared on log10
  and reported in data units (agent; owner design)
- clarify: ERDDAP pin by content checksum, one request for all 142 months at stride 12 instead of
  12 yearly files; decoded data identical to the prototype's 12 files (means and counts equal,
  verified) (agent; R2)
- clarify: `http_only` registry exception for NTSG (agent; R3; owner review item 2)
- clarify: NPP land/ocean split from ETOPO via `class_rule.land_from`; the grid is extended to
  the mask's latitudes so Antarctica is land without value (agent; R4)
- clarify: GeoTIFF read strip by strip through minimal in-memory TIFFs decoded by Pillow (bundled
  libtiff), block means while reading; no new dependency (agent; R1)
- clarify: no-data rules as one `[<layer>.no_data]` table with `rule` = unobserved | share
  (agent; R5)
- clarify: fixture budget 300 kB → 450 kB (two fixtures, 146 kB) (agent; R6)
- plan: no constitution violations; no Complexity Tracking entries (agent)
- implement: report `transform` key only for log10 (so existing reports are byte-identical apart
  from `generated_at`) (agent)
- implement: CLI legend prints signs only when a bound is negative (ENSO legends unchanged; NPP
  and chlorophyll legends read "100 to 250", "0.08 to 0.15") (agent)
- implement: web map page shows "content SHA-256" for content-pinned files; manifest dataset rows
  gain `content_sha256` when set (additive) (agent)
- implement: the ΔE00 Medium Azur / Bright Bluish Green pair (10.3) raises no warning (threshold
  5); named in the recipe comment (agent)

## Results (2026-11-22)
- Baseline: CLI 1,035 passed; web 77 passed.
- Final: CLI `1131 passed in 87.62s`; web `80 passed in 30.00s` (offline, `.venv/bin/pytest`).
- FR-013: the six existing recipes built from the fixtures in A, B and C (18 variants) with `main`
  and with this branch: layouts and reports identical apart from `generated_at`.
- Real data (`map build living-planet --fetch`): NPP fetched over HTTP, SHA-256 verified; ERDDAP
  file 147,236,600 bytes, content SHA-256 `184c7b1d…708c` verified. 3.9 s, peak RSS 580 MB
  (prebuild of three variants 18 s, 645 MB).
- Counts (A): land 6141 — Brick Yellow 520, Sand Yellow 481, Sand Green 419, Bright Yellowish
  Green 377, Bright Green 416, Dark Green 147, White (ice) 702; ocean 98138 — Bright Blue 1,199,
  Dark Azur 1,376, Medium Azur 1,713, Bright Bluish Green 1,342, Earth Green 418, White (sea ice)
  738, Black (shadow) 392. Prototype: land White 705, Tan 517, Dark Tan 496, Sand Green 404, Lime
  389, Bright Green 417, Green 134; ocean identical.
- Pieces beyond one kit: 6,589 (prototype 6,586); `parts list --kits 1`: 14 lots, to buy 6,589 in
  12 lots.
- `validate`: mask check passes; 12 violations (11 colors not in the kit, Medium Azur 1,713 >
  1,607), buildability 35.7% from one kit (expected: a top-up build).
- Web prebuild (real data): 3 variants, 18.1 MB; served locally with uvicorn: 36 requests (home,
  map page, 33 files) all 200; page shows Zhao, R2022.0, ETOPO, content SHA-256, disclaimer.

## Blocked tasks
(none)

## Deferred findings
- analyze L1 (LOW): the land no-data `share` rule uses pixel latitude while `unobserved` uses
  cell-centre latitude (both as in the prototype); documented in the contract.
- analyze L2 (LOW): the site preview draws White plates on the page's white background, so ice
  reads as blank; existing renderer behaviour (also true of the official map's White land).
- analyze L3 (LOW): `predictor` support relies on Pillow's libtiff; the test cannot force Pillow to
  write a predictor, so that path is exercised only when a file has one.
- converge: no gaps against spec, plan and tasks.

Not affiliated with or endorsed by The LEGO Group.

# Run state: 006 build sheets

Source: prompt (fallback 2B). Scoping from `docs/vision.md` and the coordinating agent's brief of
2026-11-22; no separate four-question round. Planned in one session assuming 005 as planned;
implemented in a second session on top of 005 as built (0548c0e).
Phase: done
Status: done (committed locally on 006-build-sheets; awaiting user review)
Updated: 2026-11-22

## Open questions

(Q7–Q8 answered by the user on 2026-11-22, each with the planner's recommendation; see Decisions.)

For user review (agent decisions made during implement, details in Decisions):
1. Build sheets require a full layout (all 10,240 positions); a partial layout fails with exit 1.
2. Every page (not only section pages) carries the 100 mm scale bar and print note (FR-008 read
   literally).
3. Stud numbers are 8 pt bold (about 2.8 mm), 6 pt for 3-digit numbers, instead of the planned
   "3 mm high", so two digits fit inside the plate ring.
4. `sheets build --format svg` writes into an existing directory without deleting older
   `page-NN.svg` files from a larger earlier build (no deletion of user files).

## Decisions
- user (2026-11-22): Q7 PDF via ReportLab (BSD) plus SVG pages and a per-section counts JSON;
  `reportlab >=4.4,<6` runtime dependency, `pypdf >=5` dev dependency (user)
- user (2026-11-22): Q8 commands `sheets build` / `sheets counts` with
  `--format/--paper/--sections/--title`, Letter default, true scale (8.0 mm pitch), 100 mm scale
  bar (user)
- implement: reconciled with 005 as built (0548c0e): `build_parts_list(layout, layout_path, owned)`
  and `Lot`/`ResolvedColor` match the plan; lot order is verified lots first (plate before tile,
  then LEGO color ID), then unverified lots (plate before tile, then color key), so unverified lots
  get the highest numbers; the parts list's `layout.map` block drops the recipe title, so 006 reads
  the title from the layout's `metadata.map.recipe.title`; part numbers (BrickLink 4073 /
  Rebrickable 6141 plates, 98138 tiles) come from `part_numbers.json` via `ResolvedColor`; the
  widened 44 plate / 40 tile table means up to 84 cited lots, covered by legend pagination (agent)
- specify: branch `006-build-sheets` created from `005-parts-lists` with `git checkout -b` (the
  script made the directory without switching) (agent)
- specify: section geometry = 40 × 16 x 16, 8 x 5; 154x153 images are a rasterisation detail; all
  sections hold 256 positions on four layouts (agent, research R1)
- clarify: 9 items auto-resolved (labels and order, north up, numbered studs, plate rings, legend
  fields from 005, no top-up on sheets, Latin-1, determinism, no LEGO artwork) (auto-resolved)
- plan: ReportLab 5.1.0 probe: 40 pages 0.63 MB in 0.26 s, byte-identical with invariant=1, text
  extractable with pypdf (agent, research R2)
- plan: new dependencies (permissive, decide-and-log): reportlab >=4.4,<6 (BSD; pulls
  charset-normalizer, MIT); pypdf >=5 in the dev group (BSD-3) (agent)
- plan: copyleft options rejected: fpdf2, CairoSVG, svglib (LGPL-3.0) (agent)
- plan: 8.0 mm pitch cited to LDraw's "1 brick width = 20 LDU, 1 LDU = 0.4 mm" as an approximation
  (agent, research R4)
- plan: speckit `update-agent-context.sh` not run (agent, as in 004/005)
- tasks: 31 tasks (Setup 2, Foundational 8, US1 7, US2 3, US3 4, US4 2, Polish 5) (agent)
- analyze: inline; 0 CRITICAL, 0 HIGH (agent)

- implement: build sheets need all 10,240 positions (every kit position holds a piece); a partial
  layout fails with "layout has N of 10,240 positions" (exit 1). NEEDS USER REVIEW (agent)
- implement: the scale bar, "Print at 100% (no fit-to-page)" and the footer are on every page
  (FR-008 says "each page"), not only on section pages (agent)
- implement: text colour on studs = black or white by the higher WCAG contrast ratio (the spec's
  "whichever contrasts more"), not the research's luminance threshold 0.5 (agent)
- implement: stud numbers 8 pt bold, 6 pt for 3-digit numbers; plate ring at 60% diameter in the
  number's colour (agent; contract page-layout updated)
- implement: legend rows are 9 mm with two lines (names/IDs on line 2) instead of 6 mm, so every
  ID fits: 23 rows per page on Letter, 25 on A4 (agent; contract updated)
- implement: legend acknowledgement reuses 005's `ACKNOWLEDGEMENT` text plus "Full citations: parts
  list LAYOUT --format json." (agent: no duplicated text)
- implement: unverified lots' swatch RGB comes from the 001 palette matched by LEGO code and name,
  else mid grey (display only) (agent, as planned)
- implement: page model items carry `tag` and `data`; SVG writes them as `class` and `data-*`
  (stud x, y, lot) so the web app and tests read studs back (agent)
- implement: compose measures text with ReportLab's standard Helvetica metrics (`stringWidth`) to
  wrap and fit lines; no font files are shipped (agent)
- implement: PDF uses `pageCompression=1` with `invariant=1` (still byte-identical); non-Latin-1
  text other than the title (for example a layout path) is replaced by "?" in the PDF only (agent)
- implement: SVG output into an existing directory does not delete stale `page-NN.svg` files
  (agent: avoid deleting user files). NEEDS USER REVIEW
- implement: `sheets counts` takes `--format table|json`, `-o` (implies JSON) and `-q`, like
  `parts list` (agent, existing pattern)
- converge: round 1 added T032–T034 (3-digit lot numbers, SVG pitch and stud outline tests,
  contract/data-model sync); round 2 added T035 (schema 1.x layout rejected); a final pass over
  FR-001–FR-017, SC-001–SC-007, edge cases and contracts found nothing further (agent)

## Results (T030, real data in the session scratchpad `e2e006/`)
- tests: 850 passed (767 before), offline, about 95 s
- official-31203: 42 pages (1 overview, 1 legend, 40 sections), 1,940,439 bytes, 1.1 s wall;
  every section 256; per-lot sums over sections = parts list needed (10 lots, 10,240); 5–10 lots
  per section; disclaimer on every PDF page; two PDF builds, two SVG builds (42 files, 5.3 MB) and
  two counts JSON identical
- land-elevation: 42 pages, 1,950,023 bytes, 1.1 s; 13 lots; 3–13 lots per section; sums equal the
  parts list; byte-identical rebuilds
- `--paper a4 --sections B2,C2`: 4 pages, 210.0 x 297.0 mm, sections B2 and C2
- PNG renders (pdftoppm 110 dpi): overview, legend, section C2; SVG page rendered with Quick Look

## Blocked tasks

## Deferred findings
- [RESOLVED] Depends on 005 being implemented as planned: reconciled with 005 as built (Decisions).
- [MEDIUM] True-scale printing depends on printer settings; only the scale bar guards it.
- [LOW] Legend pagination (23 rows Letter / 25 A4) tested with synthetic 90- and 120-lot layouts.
- [LOW] SC-003 pitch is checked in the page model and SVG coordinates; the PDF backend applies the
  same mm-to-point factor to every item but its content stream is not parsed for positions.
- [LOW] A section with more than about 24 lots (none measured; 13 max) gets more, narrower count
  table columns; names are shortened with "...".
- [LOW] Quickstart §3 (printing and measuring on paper) needs a printer; not run.
- [LOW] Unverified lots' display RGB comes from the 001 palette (`palette/lego_colors.json`), which
  is not a cited table; used for display only, labelled "no cited IDs".

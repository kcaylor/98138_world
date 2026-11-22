# Run state: 006 build sheets

Source: prompt (fallback 2B). Scoping from `docs/vision.md` and the coordinating agent's brief of
2026-11-22; no separate four-question round. Assumes feature 005 is built as planned. Planning
only: stop before implement.
Phase: analyze (planning complete)
Status: waiting on user (reserved decisions Q7–Q8 provisional; 005 Q1–Q6 also open)
Updated: 2026-11-22

## Open questions (reserved; provisional answers applied)
1. Q7 Output format and new dependency. Options: (a) PDF via ReportLab (BSD) + SVG pages from one
   page model [recommended: one printable file, deterministic, tiny; SVG for the web app];
   (b) SVG/HTML only, no new dependency (user prints from a browser; scale less reliable);
   (c) PDF only.
2. Q8 CLI and page conventions: `sheets build LAYOUT -o PATH [--format pdf|svg] [--paper
   letter|a4] [--sections LIST] [--title TEXT]`, `sheets counts LAYOUT [--format] [-o]`; Letter
   default; true scale 8.0 mm pitch; labels A1–H5 in instruction order. Options: (a) as proposed
   [recommended]; (b) A4 default; (c) fit-to-page scaling instead of true scale.

## Decisions
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

## Blocked tasks

## Deferred findings
- [MEDIUM] Depends on 005 being implemented as planned (lot order, resolver, part numbers); if 005's
  Q1–Q6 answers change the lot model, revisit T007–T008.
- [MEDIUM] True-scale printing depends on printer settings; only the scale bar guards it.
- [LOW] Legend pagination threshold (~25 rows) is a layout estimate; tested with a synthetic
  90-lot layout only.
- [LOW] Unverified lots' display RGB comes from the 001 palette (`palette/lego_colors.json`), which
  is not a cited table; used for display only, labelled "no cited IDs".

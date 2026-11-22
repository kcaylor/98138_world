# Research: Build Sheets (006)

Measurements on the real-data layouts from 004 (session scratchpad `e2e/`) and the feature-002
image fixture layout. Probe scripts live in the session scratchpad (`scripts006/`), never in the
repository.

## R1. Section geometry

- `kit_31203_inventory.json`: element 6302092 "BRICK 4/3, 16X16 W/ 4.85 HOLE", quantity 40, role
  `section_base`.
- `kit_31203_design.json` `sections`: 40 entries, `col` 0–7, `row` 0–4, each with its instructions
  page; pages run column by column: (0,0) p22, (0,1) p24 … (0,4) p30, (1,0) p36 … (7,4) p132.
- `image_size` is 154×154 for most and 154×153 for some section images. 003's spec (edge cases)
  records that both sizes are read as full 16×16 sections; the one-pixel difference is how the PDF
  rasterised the image. Measured: every section of the official, land-elevation, ocean-sst and
  image layouts holds exactly 256 positions (x = 16·col … +15, y = 16·row … +15).
- 003 projection notes: the three frames split the map at columns 32 and 96 (section columns A–B,
  C–F, G–H).
- Lots per section (measured): official 5–10 (10 total), land-elevation 3–13 (13), ocean-sst 3–8
  (10), image fixture 2–4 (8); 3 sections are all ocean in every layout (none all land).

**Decision**: labels A–H × 1–5, pages in the instructions' column-by-column order, frame number
from the column, per-page legend of the section's lots only (≤ 13 measured; paginate beyond ~20).

## R2. Output format and library (Q7)

| Option | License | Notes |
|---|---|---|
| **ReportLab 5.1.0** (2026-10-22; 4.x line also current) | BSD ("BSD license … Copyright (c) 2000-2025, ReportLab Inc.", PyPI classifier OSI BSD) | Pure-Python wheel (`py3-none-any`); requires Pillow ≥ 9 (project has Pillow 10.4) and charset-normalizer (MIT); `invariant=1` gives byte-identical PDFs; standard Helvetica needs no font embedding |
| fpdf2 2.9.0 | LGPL-3.0 | copyleft: reserved (non-permissive) |
| CairoSVG 2.9.1 / svglib 2.4.0 | LGPL-3.0 | copyleft; CairoSVG also needs the Cairo C library |
| WeasyPrint 70.0 | BSD | needs Pango/HarfBuzz native libraries; heavy for a CLI |
| Pillow multi-page PDF | (already a dependency) | raster only: large files, blurry text at small sizes, numbers not extractable for tests |
| SVG via standard library | — | vector, no dependency, viewable and printable from any browser; one file per page; no single printable file |

Probe (`scripts006/rl_probe.py`, ReportLab 5.1.0 in a scratch venv): 40 section pages × 256
circles with labels and a footer → 632,358 bytes in 0.26 s; two builds byte-identical with
`invariant=1`; pypdf 7.1.1 extracted every label and the disclaimer.

**Decision (provisional, Q7)**: PDF via ReportLab as the primary output (required runtime
dependency `reportlab >=4.4,<6`, BSD) and SVG via the standard library from the same page model.
Tests read PDFs with pypdf (BSD-3, already in the maintainer group; added to the dev group).

## R3. Fonts and characters

ReportLab's standard Type 1 fonts (Helvetica, Helvetica-Bold) are not embedded and use
WinAnsi/Latin-1 encoding; Greek letters (Δ) and symbols such as "≈" and "×" are not available
without embedding a TTF. **Decision**: Helvetica only, Latin-1 text, "x" for dimensions, no ΔE in
the sheets; SVG uses `font-family="Helvetica, Arial, sans-serif"`. No font files are shipped
(avoids font licensing).

## R4. True scale

LDraw file format specification (https://www.ldraw.org/article/218.html, "Real World
Approximations"): "1 brick width/depth = 20 LDU", "1 LDU = 0.4 mm", which the page itself calls
approximations → stud pitch about 8.0 mm; a 16 × 16 section is about 128 mm square. Letter (215.9 ×
279.4 mm) and A4 (210 × 297 mm) both leave ≥ 70 mm of width or height for counts with 12 mm
margins. **Decision**: draw at 8.0 mm pitch, stud circle diameter 7.0 mm, number 3 mm high;
print a 100 mm scale bar and "Print at 100% (no fit-to-page)". The 8 mm figure is cited to LDraw
as an approximation, not as a LEGO specification.

## R5. Page layout (portrait, both papers)

| Block | Height (mm) |
|---|---|
| Header: label, ranges, frame, page n of N, title | 18 |
| Locator: 8 × 5 board, 4 mm cells, section highlighted | 22 |
| Grid with edge coordinates | 136 |
| Count table, two columns of up to 10 rows at 5 mm | 55 |
| Scale bar, footer with disclaimer | 14 |
| Total | 245 (Letter usable 255.4, A4 273) |

Overview: the whole map at 1.4 mm per stud (179 × 112 mm, discs without numbers), section grid
lines and labels, frame boundaries drawn heavier, totals, provenance; legend rows at 6 mm (about
25 per page). Numbers: lot numbers on studs; text color black or white by WCAG relative luminance
of the cited RGB (threshold 0.5); circles outlined 0.2 mm grey so White and Black read on paper.
Plates: an inner ring at 60% diameter.

## R6. No LEGO artwork

The sheets are generated from layout data (positions, colors) and the cited tables only. They do
not use any page, image, crop, logo, font, or step graphic from the instructions PDF; the
instructions' page numbers are cited only as the source of the section order. Matches CLAUDE.md
("Never commit the PDF or crops of it") and constitution VIII.

## R7. Reuse of 005

Lot order and legend text come from `lego_image_processor.parts` (`build_parts_list` with no owned
inputs, `resolve_color`); 006 adds no ID lookup of its own (constitution VI: no duplicated logic).
The legend's Rebrickable acknowledgement and part numbers come from 005's data.

## R8. Determinism and tests

PDF: `invariant=1`, fixed document title/author/subject strings (title = sheet title, author
"98138.world", no creation date). SVG: fixed attribute order, numbers formatted to 2 decimals,
`\n` endings. Tests: page model (pure Python) for counts, coordinates, numbers; PDF via pypdf for
page count, page size and extracted text; SVG via `xml.etree` for 256 circles per section and
fill colors; byte equality of two builds.

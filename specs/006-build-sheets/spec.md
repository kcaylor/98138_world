# Feature Specification: Build Sheets

**Feature Branch**: `006-build-sheets`

**Created**: 2026-11-22

**Status**: Planned (assumes feature 005 is built as planned; reserved decisions carry a
recommended answer marked **[PROVISIONAL]**; see Clarifications and `run-state.md`)

**Input**: User description: "Feature 006: build sheets. Printable, section-by-section,
paint-by-number pages with per-section color counts, matching the kit's physical structure (40
section bases of 16×16 laid out 8×5). Include an overview page, a legend with color names and IDs,
and the disclaimer. Output format likely PDF and/or HTML/SVG, chosen with research; dependencies
must be permissively licensed. Never reuse LEGO's instruction artwork or crops of the PDF."
(scoping from `docs/vision.md` and the coordinating agent's brief of 2026-11-22; see run-state.md)

## Context

Features 001–004 produce layouts (schema 2.0, 128×80 positions on the kit mask). Feature 005 turns
a layout into a parts list of lots (part × color) with cited LEGO, BrickLink and Rebrickable IDs,
and marks colors it cannot verify. What a maker still lacks is a way to place 10,240 pieces: a
printed guide, section by section, that says which color goes where and how many of each a section
needs, so pieces can be sorted per section before building.

Facts that shape this feature (details in `research.md`):

1. **Section geometry.** The kit's board is 40 section bases (element 6302092, "BRICK 4/3, 16X16",
   40 on the inventory page), 8 columns × 5 rows, each exactly 16 × 16 positions: 8 × 16 = 128 and
   5 × 16 = 80. Feature 003 mapped every section to its instructions page; the section images
   there come in two pixel sizes (154×154 and 154×153), which is a rendering detail of the PDF, not
   a smaller section: every section holds 256 positions (measured on four layouts). The three
   frames split the board at columns 32 and 96 (2 + 4 + 2 section columns).
2. **True scale fits on paper.** One stud pitch is 20 LDraw units, about 8 mm (LDraw file format
   specification), so a 16 × 16 section is about 128 mm square and prints at 1:1 on both Letter and
   A4 with room for counts. A maker can lay the base on the sheet.
3. **Colors per section are few.** Measured: the official map uses 5–10 lots per section (10 in
   total), `land-elevation` 3–13 (13), `ocean-sst` 3–8 (10), the image fixture 2–4 (8). Three
   sections are all ocean in every layout. A per-page legend of up to ~15 lots fits beside the grid.
4. **PDF can be produced deterministically with a permissive library.** ReportLab (BSD license,
   pure-Python wheel, depends on Pillow, which the project already uses) writes PDF with an
   "invariant" mode for byte-identical output; SVG can be written with the standard library.
   Copyleft alternatives (fpdf2, CairoSVG, svglib: LGPL) are excluded (research R2).

## Clarifications

### Session 2026-11-22

- Q: How are sections named and ordered? → A: Column letter A–H (west to east) and row number 1–5
  (north to south), for example `C2` = columns 32–47, rows 16–31. Pages run column by column (A1,
  A2 … A5, B1 …), the same order as the kit's instruction pages for the sections (003
  `kit_31203_design.json` `sections[].page`), so a maker following either gets the same sequence
  (auto-resolved: 003 data; agent decision on labels).
- Q: Which way is up? → A: North up, west left, exactly as the layout's `top_left_origin`
  coordinates (auto-resolved: layout schema 2.0).
- Q: How are colors identified on paper? → A: Each lot gets a number (1, 2, …) in the 005
  parts-list lot order (plate before tile, then LEGO color ID); each stud is drawn as a filled
  circle in the color's cited RGB with its number on it in black or white, whichever contrasts
  more, so the sheet works on a black-and-white printer (auto-resolved: 005 lot order; 004 preview
  uses cited RGB).
- Q: How are plates and tiles told apart? → A: Land plates are drawn with an inner ring (a stud);
  ocean tiles as plain discs; the legend says "plate 1×1 round" or "tile 1×1 round" per lot
  (auto-resolved: layout `part_type`).
- Q: What do the legend and overview show per lot? → A: Number, swatch, LEGO color name and ID,
  element ID, BrickLink color name and ID with item number, Rebrickable color ID with part number
  (from 005 `resolve_color`), and total count. Unverified lots show the layout's color name and
  code and "no cited IDs" (auto-resolved: 005 FR-005, constitution V).
- Q: Does the build sheet include top-up quantities? → A: No; it shows what each section needs.
  Ordering is 005's job (`parts list`, `parts export`) (auto-resolved: vision pipeline; scope).
- Q: Which text characters can the PDF use? → A: Latin-1 only (ReportLab's standard Helvetica is
  not embedded and has no Greek): no "Δ", "≈" or "×" in the PDF; use "x" and plain words
  (auto-resolved: research R3).
- Q: Must output be deterministic? → A: Yes: same layout and options give identical bytes (PDF
  in invariant mode, SVG without timestamps) (auto-resolved: 004 FR-006 pattern).
- Q: Can LEGO artwork, logos or images from the instructions be used? → A: No. Every page is drawn
  from primitives (circles, lines, text) from the layout data; no image from the instructions
  PDF, no LEGO logo, no LEGO fonts or instruction-style step graphics (auto-resolved: CLAUDE.md,
  constitution VIII).

Reserved decisions (run-policy: file formats others use, new dependency, CLI flags), each with a
recommended provisional answer:

- **Q7** [PROVISIONAL] Output format and dependency → PDF as the primary output via ReportLab
  (BSD, new required dependency), plus SVG (one file per page, standard library) as a second
  format for the web app and for users who print from a browser.
- **Q8** [PROVISIONAL] CLI and page conventions → new group `sheets` with `sheets build LAYOUT -o
  PATH [--format pdf|svg] [--paper letter|a4] [--sections LIST] [--title TEXT]` and `sheets counts
  LAYOUT [-o PATH]`; default paper Letter; section grids at true scale (8.0 mm pitch) with a
  printed 100 mm scale check; section labels A1–H5.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Section pages with per-section counts (Priority: P1)

A maker turns a layout into a printable PDF: one page per section base, 40 in all, each showing
the 16 × 16 positions as numbered colored studs at true size, the section's label and place on the
board, and how many pieces of each color the section needs.

**Why this priority**: it is the build guide itself; without it the parts list is a pile of
10,240 pieces. It needs only the layout and the 005 lot numbering.

**Independent Test**: build sheets for the official layout and a synthetic layout; check the page
count, that every section's stud colors and numbers equal the layout's positions, that each
page's counts sum to 256, and that the sum over all pages equals the parts list totals.

**Acceptance Scenarios**:

1. **Given** a schema 2.0 layout, **When** the maker builds sheets, **Then** the PDF has one page
   for each of the 40 sections, in the order A1 … A5, B1 … H5.
2. **Given** section `C2`, **When** its page is read, **Then** it shows positions x 32–47, y 16–31,
   each stud in the lot's color with the lot's number, plates with an inner ring and tiles plain,
   and global row and column numbers along the edges.
3. **Given** any section page, **When** its count table is read, **Then** it lists every lot in
   that section with number, color name, part type and count, and the counts sum to 256.
4. **Given** all section pages, **When** their counts are summed per lot, **Then** they equal the
   005 parts list's needed quantities for the layout.
5. **Given** a section page, **When** printed at 100% on the chosen paper, **Then** the stud pitch
   is 8.0 mm and a printed 100 mm scale bar lets the maker check the printer's scaling.
6. **Given** the same layout and options twice, **When** the PDFs are compared, **Then** they are
   byte-identical.
7. **Given** a layout that is not schema 2.0 or cannot be read, **When** sheets are requested,
   **Then** the command fails with the reason and writes nothing.

---

### User Story 2 - Overview and legend (Priority: P2)

The sheet set opens with an overview page showing the whole map, the 8 × 5 section grid with
labels and the three frames, followed by legend pages: every lot's number, swatch, names and IDs for LEGO,
BrickLink and Rebrickable, part and total count, plus the map's provenance and the disclaimer.

**Why this priority**: it orients the builder and is where verified IDs and attribution appear;
it depends on US1's page model and 005's resolver.

**Independent Test**: build the official and an image-derived layout; read the overview text and
compare legend rows with `parts list --format json`.

**Acceptance Scenarios**:

1. **Given** a layout, **When** sheets are built, **Then** page 1 shows the full 128 × 80 map at
   reduced size with the section grid, labels A1–H5 and the frame boundaries at columns 32 and 96.
2. **Given** the legend, **When** compared with the parts list, **Then** each verified lot shows
   the same LEGO, BrickLink and Rebrickable names and IDs, element ID, part numbers (BrickLink
   4073 / Rebrickable 6141 for plates, 98138 for tiles) and total count.
3. **Given** an unverified lot, **When** shown in the legend, **Then** it carries the layout's color
   name and code and "no cited IDs", and the overview warns that the set includes colors without
   verified IDs.
4. **Given** a recipe-built layout, **When** the overview is read, **Then** it names the recipe id
   and title, each dataset's citation and license, the layout file's SHA-256, and the tool version.
5. **Given** any page of the set, **When** read, **Then** its footer carries "Not affiliated with
   or endorsed by The LEGO Group." and the page number.
6. **Given** a legend with more lots than fit on one legend page (about 25), **When** built,
   **Then** the legend continues on following pages, all before the section pages.

---

### User Story 3 - SVG pages and per-section counts data (Priority: P3)

A maker (or the future web app) gets the same pages as SVG files, and the per-section counts as
JSON, so the sheets can be shown in a browser or used to sort pieces into 40 bags.

**Why this priority**: the web app must call the CLI rather than redraw maps (constitution VI);
SVG and a counts file give it what it needs without PDF handling. It reuses US1–US2's page model.

**Independent Test**: build SVG output and the counts JSON; parse the SVGs and compare circle
colors and numbers with the layout; compare counts with US1's tables.

**Acceptance Scenarios**:

1. **Given** `--format svg` and an output directory, **When** built, **Then** it holds one SVG per
   page named `page-01.svg` … with the same content as the PDF pages, and the disclaimer in each.
2. **Given** an SVG section page, **When** parsed, **Then** it has 256 stud circles whose fill
   colors and numbers match the layout's positions for that section.
3. **Given** `sheets counts`, **When** run, **Then** it writes JSON with, for each section label,
   its column and row ranges and the count per lot number and color key, plus the legend, layout
   SHA-256 and disclaimer; the table form prints one line per section.
4. **Given** the same inputs twice, **When** compared, **Then** SVG files and counts JSON are
   byte-identical.

---

### User Story 4 - Print a subset, on A4 or Letter (Priority: P4)

A maker reprints only the sections they are about to build, on the paper they have.

**Why this priority**: convenience; the full set is already usable from US1.

**Independent Test**: build with `--sections B2,C2` and `--paper a4`; check page count, labels and
page size.

**Acceptance Scenarios**:

1. **Given** `--sections B2,C2`, **When** built, **Then** the output has the overview and legend
   pages and the two section pages in board order.
2. **Given** an unknown label (for example `J9`), **When** built, **Then** the command fails naming
   the label and the valid range.
3. **Given** `--paper a4`, **When** built, **Then** pages are 210 × 297 mm and the stud pitch is
   still 8.0 mm.

### Edge Cases

- A section entirely ocean (three in every current layout): page still printed; counts show only
  tiles.
- A layout with more than 99 lots (not possible with today's tables, max 84 cited colors plus
  uncited): numbers stay readable up to 3 digits; the legend paginates.
- Two lots with the same color on different parts (for example Bright Green plate and tile):
  different numbers; legend rows say plate or tile.
- A color whose cited RGB is very light (White) or very dark (Black): circle outlined in a thin
  grey stroke so it is visible on white paper.
- An image-derived layout whose `metadata.map` is absent: provenance shows the `source_image`
  instead of a recipe.
- `--title` with non-Latin-1 characters: rejected for PDF with a message (PDF uses Latin-1 fonts);
  allowed in SVG.
- The output file exists: overwritten; output directory for SVG missing: created; output path is a
  directory for PDF: error.

## Requirements *(mandatory)*

### Functional Requirements

**Pages**

- **FR-001**: The tool MUST divide a layout into the kit's 40 sections of 16 × 16 positions (8
  columns × 5 rows), labelled column letter A–H and row number 1–5, ordered column by column
  (A1–A5, B1–B5, …), matching the order of the kit's section instruction pages recorded in 003.
- **FR-002**: Each section page MUST show: the label, its global column and row ranges, its frame
  (1–3), a locator map of the 8 × 5 board with the section highlighted, the 16 × 16 grid at true
  scale (8.0 mm stud pitch) with global coordinates on the edges, each position drawn in its lot's
  color with its lot number, plates distinguished from tiles, and a count table of the section's
  lots that sums to 256.
- **FR-003**: Lot numbers MUST follow the 005 parts-list lot order and be the same on every page of
  a set.
- **FR-004**: The set MUST begin with an overview page: the whole map, the section grid with
  labels, frame boundaries (columns 32 and 96), totals, provenance (layout path and SHA-256, source
  image or recipe id/title, dataset citations and licenses, tool version) and a warning when
  unverified lots exist.
- **FR-005**: The legend MUST list every lot: number, swatch, part type and BrickLink/Rebrickable
  part numbers, LEGO color name and ID, element ID, BrickLink color name and ID, Rebrickable color
  name and ID, and total count, taken from 005's resolver; unverified lots show the layout's name
  and code and "no cited IDs" and never any invented ID. It MUST paginate when it does not fit.
- **FR-006**: Every page MUST carry "Not affiliated with or endorsed by The LEGO Group." and
  "Page n of N". The legend MUST acknowledge Rebrickable as a catalog data source (005 FR-002).
- **FR-007**: Pages MUST be drawn only from the layout and cited data using basic shapes and text;
  they MUST NOT include any image, artwork, logo or crop from LEGO instructions or products.
- **FR-008**: Each page MUST print a 100 mm scale bar with the instruction "Print at 100% (no
  fit-to-page)".

**Formats and options**

- **FR-009**: The tool MUST write the set as one PDF (default) or as one SVG file per page in a
  directory (Q7).
- **FR-010**: Paper MUST be selectable as Letter (default) or A4 (Q8); content keeps true scale on
  both.
- **FR-011**: `--sections` MUST accept a comma-separated list of labels and print only those
  section pages (plus overview and legend); unknown labels fail naming the valid range.
- **FR-012**: `--title` MUST set the overview's title; default is the recipe title, else the layout
  file name.
- **FR-013**: The per-section counts MUST be available as a library function and as `sheets
  counts` (table or JSON with sections, ranges, counts per lot, legend, layout SHA-256 and the
  disclaimer).
- **FR-014**: Output MUST be deterministic: identical bytes for identical inputs and options.
- **FR-015**: PDF text MUST be Latin-1; non-Latin-1 `--title` text fails for PDF.

**Commands**

- **FR-016**: All capabilities MUST be library functions and CLI commands on local files: `sheets
  build`, `sheets counts` (Q8). No network use. Human output ends with the disclaimer.
- **FR-017**: Tests MUST NOT use the network and MUST NOT use the instructions PDF or crops of it.

### Key Entities

- **Section**: label, column and row (0-based), x and y ranges, frame number, instruction page (003).
- **Legend entry**: lot number, lot (005), swatch RGB, text fields.
- **Page model**: page size, list of drawing primitives (rect, circle, line, text) in millimetres;
  rendered by a PDF or SVG backend.
- **Sheet set**: title, provenance, legend, pages, options (format, paper, sections).
- **Section counts**: per section, count per lot.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For the official layout, a full set has 1 overview page, the legend, and 40 section
  pages; the 40 count tables sum to 10,240 and equal the parts list per lot.
- **SC-002**: On every section page of every bundled recipe's layout, the stud colors and numbers
  match the layout positions exactly (checked from the SVG and from the PDF's text).
- **SC-003**: Stud pitch is 8.0 mm ± 0.05 mm in the PDF and SVG coordinates on both paper sizes.
- **SC-004**: A full set builds in under 10 seconds and the PDF is under 5 MB.
- **SC-005**: Repeated builds give byte-identical PDF, SVG and counts JSON.
- **SC-006**: Every page carries the disclaimer; no page embeds a raster image.
- **SC-007**: The full test suite passes offline.

## Assumptions

- Feature 005 is built as planned: `resolve_color`, `build_parts_list` and the lot order exist, and
  part numbers are cited in `part_numbers.json`.
- Only kit 31203 is supported; its section grid is fixed (constitution I).
- Printing at true scale depends on the user's printer settings; the scale bar lets them check.
- Building order inside a section is the maker's choice; the sheet does not prescribe steps.
- Accessibility beyond numbered studs (for example large-print modes) is out of scope.
- The coordinating agent's brief of 2026-11-22 and `docs/vision.md` answer the scoping questions.
- Not affiliated with or endorsed by The LEGO Group.

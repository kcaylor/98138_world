# Feature Specification: Kit Reference Data for LEGO World Map 31203

**Feature Branch**: `003-kit-reference-data`

**Created**: 2026-11-21

**Status**: Draft

**Input**: User description: "Kit reference data for LEGO World Map 31203, extracted from the official instructions PDF and verified against it, so the template (constitution principle I) and buildable outputs (principle V) rest on cited facts."

## Context

The template (constitution principle I) and every buildable output (principle V) depend on
reference data about kit 31203: which parts it uses, in which colors, in what quantities, and which
color sits at each of the 10,240 positions. The data shipped today is unverified and partly wrong:

- `lego_world_map_kit.json` lists about 25 colors per part and invented quantities; the kit has 10
  colors.
- The land part is recorded as `3062b` (1x1 round brick). The kit's parts inventory shows the land
  piece is a white 1x1 round **plate** (part 6141/4073, element 614101).
- The test colormap fixture uses ad hoc color labels ("Teal tile", "Pink/magenta tile") that do not
  match LEGO color names.

The single authoritative source is the official building instructions PDF:

| Field | Value |
|---|---|
| URL | `https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6372756.pdf` |
| Pages | 160 |
| SHA-256 | `b593e2f4befbc227c5b12fec9b58a1bd6141d19b54de5f5336dcc8cc9eb43c4c` |
| Size | about 70 MB (never committed) |

### Preliminary findings (to be verified by this feature)

- Page 159 is the parts inventory: counts paired with LEGO element IDs.
- Land: 3,064 × element 614101, white 1x1 round plate (part 6141/4073).
- Ocean: 1x1 round tiles (part 98138) in 9 colors, 8,066 tiles for 7,178 ocean positions:
  6311437 ×1879, 6322819 ×1607, 6284583 ×1060, 6284573 ×725, 6353793 ×601, 6284582 ×601,
  6311436 ×601, 6322822 ×599, 6284584 ×393.
- 40 × element 6302092, 16x16 baseplates (8 columns × 5 rows of sections).
- About 21 further frame and hanger elements.
- Build pages contain a top-down 16x16 image of each section. All 40 have been located: 32 at
  154×154 px and 8 at 154×153 px (see Clarifications).

## Clarifications

### Session 2026-11-21

- Q: How are LEGO, BrickLink and Rebrickable color IDs obtained? → A: A curated table, committed to
  the repository, maps each of the kit's colors to its LEGO, BrickLink and Rebrickable names and
  IDs, and every entry cites its source. No API key or network access is needed at run time.
  (user)
- Q: How is the land part corrected in the layout format? → A: Land becomes part 6141 with part
  type "plate" everywhere (code, tests, docs, layout files), and the layout schema version is
  bumped. (user)
- Q: Who runs the extraction from the PDF? → A: A maintainer script under `cli/tools/`, whose PDF
  library is a development-only dependency. Its outputs are committed as package data, so end
  users never download the PDF. (user)
- Q: What if the extracted design disagrees with the current land/sea mask? → A: The PDF
  extraction wins. Every changed position is documented and test expectations are updated. (user)
- Q: Should layout files written with the previous schema version (land as part 3062b, type
  "brick") be read and upgraded, or rejected? → A: Rejected with a clear error that names the old
  schema version and tells the user to regenerate the layout with the current version. (agent
  decision: no layouts have been shared outside the repo; the user approved the format change;
  reading both formats adds complexity for no users)
- Q: What if some of the 40 section images cannot be located in the PDF? → A: All 40 exist in the
  pinned PDF: 32 at 154×154 px on pages 22, 24, 28, 30, 36, 38, 42, 44, 52, 54, 58, 60, 66, 68, 72,
  74, 80, 82, 86, 88, 94, 96, 100, 102, 110, 112, 116, 118, 124, 126, 130, 132, and 8 at 154×153 px
  on pages 26, 40, 56, 70, 84, 98, 114, 128. The overview images on page 17 (4 at 247×247 px) and
  page 19 (1 at 132×132 px) are not sections. Extraction MUST find all 40 and fail loudly, writing
  no outputs, if any is missing. (auto-resolved: pdfimages -list on the pinned PDF)
- Q: Which color distance picks the "nearest kit color" suggested for an unavailable color? → A:
  CIEDE2000 (Delta E 2000), computed only against the kit colors available for the affected part.
  (auto-resolved: project instructions name CIEDE2000 matching; `cli/src/lego_image_processor/core/color_quantizer.py`
  already provides `delta_e_2000`, while `layout/validator.py` uses Euclidean RGB marked "for now")
- Q: What schema version does the corrected layout format carry? → A: "2.0" (the current layout
  format is "1.0"; the land part change is breaking, so the major number is bumped). (auto-resolved:
  `cli/src/lego_image_processor/layout/grid.py` default `schema_version="1.0"`; semantic versioning
  as used by the constitution)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Verified kit inventory and correct land part (Priority: P1)

A map maker (or a later feature, such as parts lists) needs to know exactly what kit 31203
contains: each element, its part, its color under LEGO, BrickLink and Rebrickable naming, its
quantity, and where in the instructions that fact comes from. Today the tool claims a round brick
for land and 25 colors per part; after this story it reports the kit's real 10 colors and real
quantities, and calls the land piece a 1x1 round plate everywhere.

**Why this priority**: every buildability claim and every future parts list rests on this
inventory. Wrong part IDs lead directly to wrong purchases. This story alone removes the
"not verified, do not rely on for purchasing" caveat for the inventory.

**Independent Test**: load the shipped inventory and check it against the inventory fixture taken
from page 159: every element ID, quantity and color matches, every entry has a source page, and no
code, test, doc or layout output still names part 3062b or part type "brick" for land.

**Acceptance Scenarios**:

1. **Given** the installed package with no network access, **When** a user or library call
   requests the kit 31203 inventory, **Then** it returns every element listed on the parts
   inventory page, each with element ID, part ID, part description, color (LEGO name and ID,
   BrickLink name and ID, Rebrickable name and ID), quantity and source page.
2. **Given** the inventory, **When** land and ocean pieces are listed, **Then** land is exactly one
   element (white 1x1 round plate, part 6141) and ocean is part 98138 in exactly 9 colors, for 10
   map colors in total.
3. **Given** the color table, **When** any entry is inspected, **Then** it names the source of each
   ID mapping (for example, a specific catalog page), and no entry is marked as an estimate or
   placeholder.
4. **Given** a newly generated layout, **When** it is written to JSON or CSV, **Then** land
   positions use part 6141 with part type "plate" and the file carries the new schema version.
5. **Given** the repository after this story, **When** it is searched for the old land part
   (`3062b`) or for "brick" as the land part type, **Then** no matches remain outside historical
   spec documents for features 001 and 002.

---

### User Story 2 - Official design as a named-color grid, with the mask derived from it (Priority: P2)

A maintainer extracts the official 31203 design from the instructions into a 128×80 grid where
each position holds a named kit color. The land/sea mask is then regenerated from that grid (land
= positions holding the white plate) and compared with the current mask. This grid is the target
that feature 004 must reproduce as a recipe (constitution principle II).

**Why this priority**: the reference acceptance test for the whole system needs the official
design as data. It depends on the color table from Story 1 to name colors, but can be checked on
its own against the PDF.

**Independent Test**: from the committed design grid, count positions per color and check that
the counts are consistent with the inventory (no color used more often than the kit supplies);
regenerate the mask and confirm it matches the shipped mask, with any differences listed in a
committed change record.

**Acceptance Scenarios**:

1. **Given** the cached, checksum-verified PDF, **When** the maintainer runs the extraction,
   **Then** it produces a 128×80 grid where every one of the 10,240 positions holds one of the 10
   kit colors, plus a record of which page and section image each 16x16 block came from.
2. **Given** all 40 sections of the 8 × 5 layout, **When** extraction finishes, **Then** each
   section is mapped to exactly one of the 40 section images (on the pages listed in
   Clarifications) and to one position on the board, with none missing and none duplicated; if any
   of the 40 images is not found, extraction fails with an error naming the missing pages and
   writes no outputs.
3. **Given** the extracted grid, **When** the land/sea mask is regenerated from it, **Then** the
   package mask is replaced by the regenerated one, and every position whose class changed is
   listed with its coordinates and old and new class.
4. **Given** the extracted grid, **When** per-color counts are computed, **Then** no color is used
   more often than the kit supplies, and the difference between supplied and used for each color
   is recorded (spares).
5. **Given** a machine without the PDF and without network access, **When** the test suite runs,
   **Then** extraction is tested on small committed fixtures (for example, a few section images),
   and the committed design grid is checked for shape, color set and consistency with the
   inventory.
6. **Given** a downloaded PDF whose checksum does not match the pinned value, **When** extraction
   is attempted, **Then** it stops with an error naming the expected and actual checksums and
   writes no outputs.

---

### User Story 3 - Validation and layout generation use the corrected data (Priority: P3)

A user runs `validate` on a layout and gets an answer based on the real kit: 10 colors, real
quantities, the correct land part. The layout generator labels land and ocean with the correct
parts and colors.

**Why this priority**: this is where users see the corrected data. It depends on Story 1 (and on
Story 2 for the mask) but is a thin change to existing commands.

**Independent Test**: validate the official design grid (from Story 2) as a layout and confirm it
is reported fully buildable; validate a layout that uses a color not in the kit and one that
exceeds a kit quantity, and confirm each problem is reported against the real inventory.

**Acceptance Scenarios**:

1. **Given** a layout equal to the official design, **When** `validate` is run against kit 31203,
   **Then** it reports the layout as fully buildable with no color or quantity violations.
2. **Given** a layout that places a color outside the kit's 9 ocean colors on an ocean position,
   **When** it is validated, **Then** the report names that color, the part, the number of
   positions affected, and the nearest kit color as a suggested alternative.
3. **Given** a layout whose use of one kit color exceeds the kit quantity, **When** it is
   validated, **Then** the report states the color, the number needed, the number supplied and the
   shortfall.
4. **Given** a layout file written with the previous schema version (land as part 3062b, type
   "brick"), **When** it is validated or loaded, **Then** the tool rejects it with a clear error
   that names the file's schema version and tells the user to regenerate the layout with the
   current version; it does not read or upgrade the old format.
5. **Given** any validation or layout output, **When** it is shown to the user, **Then** it
   includes "Not affiliated with or endorsed by The LEGO Group."

### Edge Cases

- The PDF is unavailable at its URL or the download is interrupted: the maintainer sees a clear
  error; a partial file is never cached as complete.
- The cached PDF is present but corrupted or replaced: the checksum check catches it before
  extraction.
- One or more of the 40 section images is not found during extraction (for example, a changed
  PDF layout): extraction fails loudly, naming the missing pages, and writes no outputs.
- Section images come in two sizes (154×154 and 154×153 px): both are read as 16×16 sections.
  Non-section images (the overviews on pages 17 and 19) are excluded.
- A pixel in a section image is ambiguous between two similar kit colors (for example, two blues):
  the extractor flags the position for manual review rather than guessing silently, and the
  committed grid records any manual decision.
- The inventory count for land plates (3,064) differs from the mask's land positions (3,062): the
  difference is recorded as spares, not treated as an error, once the mask is confirmed from the
  design.
- Ocean tiles exceed ocean positions (8,066 vs 7,178, 888 more): the per-color surplus is recorded;
  the feature explains it (spares, or tiles used outside the map area) if the instructions show
  why, and otherwise records it as unexplained.
- Frame and hanger elements have no map color role: they appear in the inventory but are excluded
  from map color validation.
- A kit color has no exact BrickLink or Rebrickable equivalent: the table records the closest
  catalog color and says so in that entry's source note rather than leaving it blank.

## Requirements *(mandatory)*

### Functional Requirements

**Source and provenance**

- **FR-001**: The source PDF MUST be pinned by URL and SHA-256 checksum, downloaded on demand by
  the maintainer extraction, cached locally, and verified against the checksum before use.
- **FR-002**: The PDF MUST NOT be committed to the repository or shipped in the package.
- **FR-003**: Every reference data file produced by this feature MUST record its source (PDF URL,
  checksum, page numbers) and the date it was generated, as required by constitution principle I.
- **FR-004**: Extraction MUST be a maintainer tool kept apart from the user-facing CLI; its PDF
  handling dependency MUST be development-only, and end users MUST NOT need the PDF or network
  access to use any reference data.

**Kit inventory (Story 1)**

- **FR-005**: The package MUST ship a kit inventory listing every element on the instructions'
  parts inventory page with: element ID, part ID (including alternate part numbers such as
  6141/4073), part description, color, quantity, role (land, ocean, baseplate, frame/other) and
  source page.
- **FR-006**: The package MUST ship a curated color table covering each of the kit's 10 map colors,
  with LEGO color name and ID, BrickLink color name and ID, Rebrickable color name and ID, and a
  source citation for each mapping.
- **FR-007**: The color table and inventory MUST be readable with no network access and no API
  keys.
- **FR-008**: The land part MUST be part 6141 (1x1 round plate, white) with part type "plate" in
  all code, tests, documentation and generated layouts; part 3062b and land part type "brick" MUST
  be removed.
- **FR-009**: The layout file format MUST carry a new schema version ("2.0", up from "1.0")
  reflecting the land part change, and the format change MUST be documented. Layout files with an
  older schema version MUST be rejected with an error that tells the user to regenerate the
  layout; they are not read or upgraded.
- **FR-010**: The previous invented quantities and non-kit colors MUST be removed from package
  data; no quantity may appear without a cited source.
- **FR-011**: The mislabeled test colormap fixture MUST be replaced or relabeled using the kit's
  color names from the color table.

**Official design and mask (Story 2)**

- **FR-012**: The maintainer extraction MUST produce the official design as a 128×80 grid of named
  kit colors, committed as package data, with a per-section record of source page and image.
- **FR-013**: All 40 sections (8 columns × 5 rows of 16x16) MUST be accounted for: extraction MUST
  find all 40 section images on the pages listed in Clarifications and MUST fail loudly, writing
  no outputs, if any is missing.
- **FR-014**: The land/sea mask MUST be regenerated from the design grid and replace the shipped
  mask; every position whose class changes MUST be listed in a committed change record, and
  affected test expectations MUST be updated.
- **FR-015**: The feature MUST record per-color used counts from the design next to supplied
  counts from the inventory, and the resulting spares.
- **FR-016**: Positions whose color could not be determined with confidence MUST be flagged and
  resolved by a recorded manual decision before the grid is committed.
- **FR-017**: Any findings about the kit's map projection seen during extraction MUST be written
  down as notes for feature 004; determining the projection is out of scope.

**Validation and layout (Story 3)**

- **FR-018**: The `validate` command MUST check layouts against the verified inventory: colors per
  part from the color table, quantities from the inventory.
- **FR-019**: Validation reports MUST name each unavailable color with its affected part and
  position count and suggest the nearest kit color for that part by CIEDE2000, and MUST report each quantity shortfall with
  needed, supplied and missing counts.
- **FR-020**: The layout generator MUST label positions with the corrected parts, part types and
  kit color names.
- **FR-021**: All user-facing output touched by this feature MUST include "Not affiliated with or
  endorsed by The LEGO Group."

**Testing**

- **FR-022**: All tests MUST run offline, using small committed fixtures derived from the PDF
  (for example, a cropped inventory image or text and a few section images), never the full PDF.
- **FR-023**: Tests MUST check the committed inventory, color table, design grid and mask for
  internal consistency (totals, color sets, land count equal to mask land positions).

### Key Entities

- **Source document**: the pinned instructions PDF (URL, checksum, page count) cited by every
  reference file.
- **Kit element**: one inventory line: element ID, part ID(s), description, color, quantity, role,
  source page.
- **Kit color**: one of the kit's 10 map colors, with LEGO, BrickLink and Rebrickable names and IDs
  and a citation for each.
- **Section**: one 16x16 baseplate of the 8 × 5 board, with board position, source page and image.
- **Design grid**: 128×80 positions, each holding one kit color; derived from the 40 sections.
- **Land/sea mask**: the land or ocean class of each position, derived from the design grid.
- **Mask change record**: positions whose class differs between the old and the regenerated mask.
- **Layout**: a generated placement of parts and colors on the grid, with a schema version.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of inventory lines and color mappings carry a source citation; zero quantities
  or IDs are uncited.
- **SC-002**: The shipped inventory matches the parts inventory page exactly for every element ID
  and quantity (every line: the 10 map-color elements, the baseplates and the frame and hanger
  elements).
- **SC-003**: The design grid covers all 10,240 positions with exactly 10 distinct colors, and its
  per-color usage never exceeds the kit quantity for that color.
- **SC-004**: All 40 sections are mapped to a source in the instructions.
- **SC-005**: Validating the official design as a layout reports it fully buildable with zero
  violations.
- **SC-006**: Zero occurrences of the old land part or land part type remain in code, tests,
  current documentation and generated outputs.
- **SC-007**: The full test suite passes with networking disabled and without the PDF present.
- **SC-008**: A maintainer can regenerate all reference data from the pinned PDF with one command,
  and the result is identical to the committed data.

## Assumptions

- The parts inventory page and the section images in the PDF are authoritative; where they
  disagree with any other source (catalog sites, the current data), the PDF wins.
- Each of the 10 map colors corresponds to exactly one element ID in the inventory (1 land, 9
  ocean).
- Color mappings to BrickLink and Rebrickable are taken from their public catalog pages at the time
  of curation and cited by URL; they are refreshed only by a maintainer, by hand.
- The grid convention stays as in feature 002 (128 columns × 80 rows, top-left origin).
- Inventory surpluses (2 land plates, 888 ocean tiles) are treated as spares unless the
  instructions show another use.
- The cache location for the PDF follows the project's existing data cache convention, or a
  per-user cache directory if none exists yet.
- Out of scope: determining the kit's map projection (only notes for 004), map recipes, datasets,
  parts-list export and build sheets.
- Feature 002's "shadowing" story is not touched here; it is replaced by the texture rule in 004.

Not affiliated with or endorsed by The LEGO Group.

# Research: Kit Reference Data for LEGO World Map 31203

**Feature**: 003-kit-reference-data | **Date**: 2026-11-21 | **Plan**: [plan.md](plan.md)

All findings below were checked against the pinned PDF
(`https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6372756.pdf`, SHA-256
`b593e2f4befbc227c5b12fec9b58a1bd6141d19b54de5f5336dcc8cc9eb43c4c`, checksum confirmed on the local
copy) with poppler (`pdftotext`, `pdfimages`, `pdftoppm`) and pypdf 7.1.1, run in a scratch
environment. Nothing from the PDF is committed by this research.

---

## R1. Reading the parts inventory (page 159)

**Decision**: Read page 159's text with word positions and pair each count token (`\d+x`) with the
element ID token (`\d{6,7}`) directly below it: same column (|Δx| < 3 pt) and the smallest positive
Δy under 20 pt. In the extractor, word positions come from pypdf's `extract_text(visitor_text=...)`;
the pairing logic is a pure function over a list of `(x, y, text)` words, so tests run on a small
committed word-list fixture (facts only, no artwork).

**Result** (from `pdftotext -bbox -f 159 -l 159`, paired as above): 32 lines, 11,694 pieces.

| Element | Qty | Element | Qty | Element | Qty | Element | Qty |
|---|---|---|---|---|---|---|---|
| 614101 | 3064 | 6311437 | 1879 | 6322819 | 1607 | 6284583 | 1060 |
| 6284573 | 725 | 6353793 | 601 | 6284582 | 601 | 6311436 | 601 |
| 6322822 | 599 | 6284584 | 393 | 6302092 | 40 | 4121715 | 205 |
| 4160228 | 52 | 416201 | 48 | 4518400 | 40 | 300801 | 34 |
| 4211002 | 32 | 246501 | 22 | 301001 | 22 | 4119227 | 22 |
| 300501 | 12 | 379501 | 8 | 4558168 | 8 | 235701 | 4 |
| 242001 | 4 | 6104805 | 4 | 6302094 | 2 | 428226 | 1 |
| 6056774 | 1 | 6302093 | 1 | 6329429 | 1 | 6329436 | 1 |

Every count/ID pair was unambiguous (no count without an ID, no ID used twice).

**Part numbers and descriptions** are not printed on page 159 (it shows only images, counts and
element IDs). They come from a curated, cited part catalog file kept with the extractor
(`cli/tools/kit31203/part_catalog.json`), sourced from the Brickset inventory
(https://brickset.com/inventories/31203-1, fetched 2026-11-21). Brickset agrees with page 159 on
30 of 32 lines; it lists 6279875 ×206 (connector peg) and 6406522 ×52 (brick 1x2 with snap) where
the PDF prints 4121715 ×205 and 4160228 ×52. **The PDF wins** (spec Assumptions): the inventory
uses the PDF's element IDs and counts; the two catalog rows for 4121715 and 4160228 are recorded
with the design number and description Brickset gives for the equivalent line (61332 connector
peg w. friction; 44865 brick 1x2 w. horizontal snap) and a note that the element ID differs, so
part metadata for those two frame elements is marked `"verified": false` in the catalog file. They
have no map role and are excluded from color validation.

**Alternatives considered**: `pdftotext -layout` text-only parsing (ordering is column-dependent and
fragile); OCR of the rendered page (unnecessary: the text is real text).

## R2. Map elements and their colors

**Decision**: Map colors are keyed by LEGO color name (snake case, `lego_` prefix, matching the
existing `_make_color_id` convention). Element → color comes from Brickset's inventory (LEGO color
names), cross-checked by sampling the tile icon drawn above each count on a 150 dpi render of
page 159.

| Element | Role | Qty | LEGO color (Brickset) | Icon color sampled on p.159 |
|---|---|---|---|---|
| 614101 | land (round plate 1x1, design 6141) | 3064 | White | white |
| 6311437 | ocean (round tile 1x1) | 1879 | Bright Bluish Green | #189090 teal |
| 6322819 | ocean | 1607 | Medium Azur | #58A8C8 light blue |
| 6284583 | ocean | 1060 | Bright Yellowish Green | #A0C840 lime |
| 6284573 | ocean | 725 | Brick Yellow | #C0B078 tan |
| 6353793 | ocean | 601 | Bright Green | #58C040 green |
| 6284582 | ocean | 601 | Bright Orange | #F08828 orange |
| 6311436 | ocean | 601 | Vibrant Coral | #F86088 pink-coral |
| 6322822 | ocean | 599 | Flame Yellowish Orange | #F8A828 yellow-orange |
| 6284584 | ocean | 393 | Earth Blue | #203868 dark navy |

Brickset gives the ocean tile's LEGO design number as **35381** ("FLAT TILE 1X1, ROUND"); the
project's `98138` is the BrickLink/Rebrickable catalog number for the same 1x1 round tile. The
inventory records both (`design_id: "35381"`, `part_ids: ["98138", "35381"]`). Likewise land
records `design_id: "6141"`, `part_ids: ["6141", "4073"]`. Layout files keep `lego_part_id`
`"6141"` (land, per the user's decision) and `"98138"` (ocean, unchanged). See plan ESCALATE E2.

## R3. Curated color table (FR-006)

**Decision**: Commit `cli/src/lego_image_processor/data/kit_colors.json` with the 10 rows below.
Each ID mapping carries its own citation URL and access date.

Sources:
- **[LD]** LDraw `LDConfig.ldr`, update 2026-11-09, https://library.ldraw.org/library/official/LDConfig.ldr
  (each colour line carries a `// LEGOID n - <LEGO name>` comment; header: "The LEGO numbers, names
  and LDD colours are taken directly from LEGO Digital Designer").
- **[RB]** Rebrickable `colors.csv`, https://cdn.rebrickable.com/media/downloads/colors.csv.gz
  (fetched 2026-11-21; listed on https://rebrickable.com/downloads/). Rebrickable's HTML pages
  returned HTTP 402 to automated fetches, so the CSV is the citation.
- **[BL]** BrickLink Color Guide, https://www.bricklink.com/catalogColors.asp, read from the
  Internet Archive snapshot
  http://web.archive.org/web/20251002182704/https://www.bricklink.com/catalogColors.asp
  (the live site redirected to a maintenance page on 2026-11-21).
- **[BS]** Brickset inventory 31203-1, https://brickset.com/inventories/31203-1 (element → LEGO
  color name).

| Key | LEGO name / ID [LD] | BrickLink name / ID [BL] | Rebrickable name / ID [RB] | Element [BS] | Status |
|---|---|---|---|---|---|
| `lego_white` | White / 1 | White / 1 | White / 15 | 614101 | verified |
| `lego_bright_bluish_green` | Bright Bluish Green / 107 | Dark Turquoise / 39 | Dark Turquoise / 3 | 6311437 | verified |
| `lego_medium_azur` | Medium Azur / 322 | Medium Azure / 156 | Medium Azure / 322 | 6322819 | verified |
| `lego_bright_yellowish_green` | Bright Yellowish Green / 119 | Lime / 34 | Lime / 27 | 6284583 | verified |
| `lego_brick_yellow` | Brick Yellow / 5 | Tan / 2 | Tan / 19 | 6284573 | verified |
| `lego_bright_green` | Bright Green / 37 | Bright Green / 36 | Bright Green / 10 | 6353793 | verified |
| `lego_bright_orange` | Bright Orange / 106 | Orange / 4 | Orange / 25 | 6284582 | verified |
| `lego_vibrant_coral` | Vibrant Coral / 353 | Coral / 220 | Coral / 1050 | 6311436 | verified |
| `lego_flame_yellowish_orange` | Flame Yellowish Orange / 191 | Bright Light Orange / 110 | Bright Light Orange / 191 | 6322822 | verified |
| `lego_earth_blue` | Earth Blue / 140 | Dark Blue / 63 | Dark Blue / 272 | 6284584 | verified |

All 30 ID mappings were read from the cited sources in this session; none is UNVERIFIED. Each
catalog has an exact equivalent, so no "closest color" notes are needed. Caveats for the table's
notes field:
- The cross-catalog equivalence (LEGO ↔ BrickLink) is asserted by name/ID in LDraw (which follows
  BrickLink naming) and by the BrickLink guide; it is not a LEGO-published crosswalk.
- The table also carries a display RGB per color; use Rebrickable's `rgb` column (cited) rather
  than the existing `palette/lego_colors.json` values, which are uncited.
- `palette/lego_colors.json` lacks Bright Bluish Green (107). It must be added (cited RGB from
  [RB]: `#008F9B`) so `quantize` and `layout` can produce and read it.

**Alternatives considered**: Rebrickable API (needs an API key: rejected by the spec); live
BrickLink scraping at run time (network at run time: rejected).

## R4. Locating the 40 section images

**Decision**: On each section page, take the image XObject whose size is 154×154 or 154×153 px and
whose placement scale is about 36.8 pt. Pages with no such image, or more than one, fail the run.
Non-section images (overview pages 17 and 19, the build renders 706–805 px wide) are excluded by
size.

Measured with pypdf (content-stream walk tracking `q`/`Q`/`cm` and Form XObject matrices): exactly
one section image on each of the 40 listed pages, none elsewhere in pages 20–135.

## R5. Mapping each section to its board position (col, row)

**Finding**: The "locator" in the page's top-left corner is not one image. It is three shared
grey panel images (object IDs 1233, 1234, 1235 on most pages: 154×381, 306×381, 154×381 px, drawn
at x = 13.7, 90.6, 240.2 pt; y = 347.9 pt; heights 182.7 pt), and the colored 154×154 section image
is drawn **on top of the locator at the section's own position**. The panels are 2, 4 and 2
sections wide and 5 sections tall (the kit's three frames: 2 + 4 + 2 columns × 5 rows). The large
706–805 px image on each page is the isometric build render, not a locator.

**Decision**: Position from placement geometry, cross-checked against page order.
- `col` = nearest of the 8 column origins measured from the panels (13.9, 50.2, 90.6, 127.2,
  163.8, 200.4, 240.2, 276.6 pt; residual ≤ 0.6 pt observed); `row` = round((493.5 − y) / 36.4)
  where 493.5 is the top row's y (PDF y grows upward). The extractor derives the column origins
  from the three panel placements on the same page instead of hard-coding them, and fails if a
  section sits more than 3 pt from a grid slot.
- Cross-check: sections appear in column-major build order, five pages per column, two pages
  apart within a column. Both methods give the same answer for all 40:

| col | pages (row 0 → 4) |
|---|---|
| 0 | 22, 24, 26, 28, 30 |
| 1 | 36, 38, 40, 42, 44 |
| 2 | 52, 54, 56, 58, 60 |
| 3 | 66, 68, 70, 72, 74 |
| 4 | 80, 82, 84, 86, 88 |
| 5 | 94, 96, 98, 100, 102 |
| 6 | 110, 112, 114, 116, 118 |
| 7 | 124, 126, 128, 130, 132 |

All 40 (col, row) slots are filled exactly once. The eight 154×153 images are exactly row 2 of
each column. Assembling the 40 sections at these positions produces a correctly oriented world
map (north up, Americas left), confirmed visually.

**Alternatives considered**: page order only (works, but silently wrong if LEGO reorders a
build); matching locator highlight colors in the render (the render is isometric, not top-down).

## R6. Classifying stud colors

**Decision**:
1. For each 16×16 section image, cell (i, j) center = ((i + 0.5)·w/16, (j + 0.5)·h/16) using the
   image's own w and h (handles 154×153). Sample the **median** of a 5×5 px patch at the center
   (studs are ~9.6 px; the center avoids anti-aliased stud edges and JPEG ringing).
2. Classify against 10 **reference render colors** (the kit colors as they appear in these JPEGs,
   which differ from catalog RGB: e.g. White renders ≈ #E9E9E9, Brick Yellow ≈ #DAC890). The
   reference set is committed with the extractor (`cli/tools/kit31203/reference_colors.json`) and
   was derived once by a k-means pass seeded with the page-159 icon colors; at run time
   classification uses the fixed references (deterministic, SC-008).
3. Distance: CIEDE2000 on Lab (reusing `core.color_quantizer.delta_e_2000` and
   `palette.converter.rgb_to_lab`). Confidence = d₁/d₂ (nearest over second nearest).
4. A position is **ambiguous** when d₁/d₂ > 0.6 or d₁ exceeds a maximum distance. Ambiguous
   positions must be resolved in `cli/tools/kit31203/overrides.json` (position, chosen color,
   reason, who/when). The extractor fails, writing nothing, if an ambiguous position has no
   override, if an override names a non-ambiguous position whose classification it contradicts
   without `force: true`, or if any color's used count exceeds the kit supply.

**Measured result** (RGB variant, seeded k-means; CIEDE2000 numbers will differ slightly):

| Color | Used | Supplied | Spare |
|---|---|---|---|
| White (land) | 3062 | 3064 | 2 |
| Bright Bluish Green | 1876 | 1879 | 3 |
| Medium Azur | 1606 | 1607 | 1 |
| Bright Yellowish Green | 1018 | 1060 | 42 |
| Brick Yellow | 724 | 725 | 1 |
| Bright Green | 531 | 601 | 70 |
| Bright Orange | 230 | 601 | 371 |
| Flame Yellowish Orange | 596 | 599 | 3 |
| Vibrant Coral | 203 | 601 | 398 |
| Earth Blue | 394 | 393 | **−1** |

- Ambiguous positions: 58 at ratio > 0.6 (27 at > 0.7). This is the expected size of the manual
  review list; the implementation should report the actual number.
- Earth Blue is over by one. The most doubtful Earth Blue position is (0, 32), sample RGB
  (52, 121, 121), ratio 1.00 vs Bright Bluish Green, at the top-left corner of section (0, 2) (one
  of the 154×153 images). Reclassifying it as Bright Bluish Green gives Earth Blue 393/393 and
  Bright Bluish Green 1877/1879. This is a manual decision to record in `overrides.json`.
- The 888 surplus ocean tiles are concentrated in Bright Orange (371) and Vibrant Coral (398), with
  smaller surpluses in Bright Green (70) and Bright Yellowish Green (42). Nothing in the
  instructions explains them; they are recorded as unexplained spares (spec Edge Cases).
- Land: the 3,062 White positions match the shipped mask **exactly (0 positions change)**. The
  2 spare white plates match the 3,064 − 3,062 difference. The change record is committed anyway
  (empty list) so FR-014 is demonstrably satisfied.

**Alternatives considered**: per-run k-means (non-deterministic across library versions); mean
instead of median (pulled by stud highlights); Euclidean RGB (kept only as a cross-check).

## R7. PDF library and extraction tooling

**Decision**: `pypdf` (BSD-3-Clause, pure Python) in a new optional Poetry group `maintainer`,
used only by `cli/tools/kit31203/`. pypdf provides page images (`page.images`, raw JPEG bytes for
DCT streams, decoded with Pillow), the content stream for placement geometry, and text with
positions. Pillow and NumPy are already runtime dependencies. No poppler or PyMuPDF (AGPL) at any
stage. The package itself never imports pypdf.

**Alternatives considered**: PyMuPDF (AGPL, rejected by the user's guidance); pdfplumber/pdfminer
(MIT, works, but a heavier dependency for text only and no better at images); poppler CLI
(external binary, not pip-installable).

## R8. Download, cache and checksum (FR-001, edge cases)

**Decision**: Standard library only (`urllib.request`, `hashlib`). Cache directory:
`$LEGO_IMAGE_PROCESSOR_CACHE` if set, else `$XDG_CACHE_HOME/lego-image-processor`, else
`~/.cache/lego-image-processor`; file `sources/31203-instructions-6372756.pdf`. Download streams
to `<name>.part`, verifies SHA-256, then renames atomically; a checksum mismatch deletes the
`.part` file and errors with expected and actual values. A cached file is re-hashed before every
use. `--pdf PATH` lets a maintainer supply a local copy (still checksum-verified). No existing
cache convention exists in the repository (checked `cli/src`), so this sets it; feature 004's
dataset cache should reuse the same root.

## R9. Reproducibility (SC-008)

**Decision**: The extractor writes deterministic JSON (sorted keys where order is not meaningful,
fixed indent, `\n` endings). The `generated_on` date is taken from `--date` (default: today) and
is the only field allowed to differ. `python -m kit31203 extract --check` regenerates into a temp
directory and diffs against the committed files ignoring `generated_on`; exit 1 on any
difference.

## R10. Test fixtures without redistributing LEGO artwork (FR-022)

**Decision**: Offline tests use:
- `cli/tests/fixtures/kit31203/page159_words.json`: the page-159 word list (count and element ID
  tokens with coordinates), which is factual data, not artwork.
- `cli/tests/fixtures/kit31203/placements.json`: the measured panel and section placements for a
  few pages, to test (col, row) mapping.
- Synthetic section images generated by a test helper from known color grids using the reference
  render colors plus JPEG compression and noise (154×154 and 154×153), to test sampling and
  ambiguity flagging.
- A tiny synthetic PDF built in the test with pypdf (only in the maintainer test group, skipped if
  pypdf is absent) to test the PDF adapter end to end.

No crops of LEGO's instruction images are committed. This is stricter than the spec's example
("a few section images") and gives the same coverage; see plan ESCALATE E3.

## R11. Layout format 2.0 (FR-008, FR-009)

**Decision**: Changes in the layout JSON/CSV, all under `schema_version: "2.0"`:
- land positions: `part_type: "plate"`, `lego_part_id: "6141"`.
- `metadata.land_positions` unchanged in meaning; statistics key `land_brick_count` →
  `land_plate_count`; `color_frequency_by_part_type` keys `"plate"` and `"tile"`.
- `metadata.disclaimer: "Not affiliated with or endorsed by The LEGO Group."` (also printed by the
  CLI).
- `PositionPlacementGrid.from_json` raises `LayoutSchemaError` when `schema_version` is missing or
  not "2.0", naming the found version and the command to regenerate. CSV layouts have no metadata;
  `validate` keeps accepting only JSON (unchanged), so CSV needs no version check.

## R12. Projection notes for feature 004 (FR-017)

Observations only (determining the projection is out of scope):
- The assembled grid spans the full longitude range in 128 columns (~2.81° per column) with the
  Americas at the left; the left/right edges are both in the Pacific.
- Greenland and the high-latitude land masses are strongly enlarged and Antarctica fills the
  bottom rows as a continuous white band, consistent with a cylindrical projection with a cropped
  southern edge (Miller-like), not an equal-area one.
- The three frames split the map at columns 32 and 96 (2 + 4 + 2 sections).
- These go into `specs/003-kit-reference-data/projection-notes.md` during implementation, with
  the latitudes of identifiable features (e.g., the equator crossing of South America, the
  southern tip of Africa) measured from the committed grid.

Not affiliated with or endorsed by The LEGO Group.

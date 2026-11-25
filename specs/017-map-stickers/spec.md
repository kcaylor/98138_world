# Feature Specification: Map stickers

**Feature Branch**: `017-map-stickers`

**Created**: 2026-11-23

**Status**: Draft (clarified; one owner question open, see Clarifications and `run-state.md`)

**Input**: Owner, 2026-11-23: "I don't think making labels with bricks. I was thinking instead about
a sticker approach on a black plate (like existing lego labels for large kits). For that matter, we
should develop a sticker for each of the existing maps that could be used as a map label (either on
the front or the back, or as a separate item in a display, etc...)" Scoping answers (2026-11-23): a
new feature, separate from 016; two plaque sizes from one design; the content of each; and an
optional plaque in a Winkel margin corner after 016 ships (Clarifications).

## Context

LEGO's large display sets carry their label as a sticker on a smooth black tile, often set on a
black plate. The owner wants the same for 98138.world: a sticker for each map, printed by the maker
and stuck on a black tile, to label the map on the front, on the back of the frame, or as a
separate item in a display. It replaces the brick-built corner labels that feature 016 dropped
(`specs/016-map-templates/plan.md`, 2026-11-23).

Every map is built from a recipe (feature 004): a title, a description, a land layer and an ocean
layer, each classified onto cited plate or tile colors, a land shadow and, for some maps, ice,
override and no-data rules. The build already knows what each color means: the recipe's bounds
(bins), the value boundaries between the built classes (rank methods, as the palette chooser shows,
feature 015), background roles, override names and the shadow. The dataset registry
(`data/datasets.json`) holds each dataset's title, publisher, citation, license and DOI. A sticker
is made from this data, not drawn by hand (constitution III).

Two plaques, one design:

| Plaque | Label tile | Standalone, on | Sticker (about) | Content |
|---|---|---|---|---|
| Small | Black tile 6×6 (10202), 47.8 mm | Black plate 6×6 (3958) | 46 × 46 mm | title, one-line description, disclaimer |
| Large | Black tile 8×16 (4974, smooth), 63.8 × 127.8 mm | Black plate 8×16 (92438) | 62 × 126 mm, landscape | title, one-line description, color legend, data credit, 98138.world, disclaimer |

All four parts are made in Black (pinned Rebrickable elements snapshot); none is in kit 31203.
Planning adds their cited IDs. On a Winkel tripel board (feature 016) the small plaque can also sit
in a margin corner as part of the build: each corner has a clear block of 14 × 14 margin studs
inside the outline ring (016 research R2, R20), so a 6×6 tile fits.

Main and this branch have constitution 2.0.0; feature 016 brings 3.0.0 (Principle I: templates and
margins) when it merges. User stories 1 and 2 need only 2.0.0; user story 3 needs 016 and 3.0.0.

**Terms.** *Sticker*: a printed label cut from sticker paper. *Plaque*: a black tile carrying a
sticker; *standalone* when it sits on a black plate of the same size, *in-margin* when it is built
into a Winkel board's margin. *Sticker set*: the small and large sticker of one map on one
template. *Print sheet*: a printable page with a sticker set at true size, cut marks and notes.
*Cut line*: the sticker's outline. *Bleed*: the black background printed past the cut line so a
slightly off cut shows no white edge. *Clear block*: the largest rectangle of margin studs in a
board corner clear of the outline ring (feature 016). *Sticker line*: the one-line description.

## Clarifications

### Session 2026-11-23 (owner decisions)

- Q: Is this part of feature 016 (map templates)? → A: No. A new feature, 017, separate from 016;
  016 drops its brick-built corner labels. (user)
- Q: What sizes? → A: Two sizes from one design: a small plaque, such as a 6×6 tile, that fits a
  Winkel tripel corner's free 14×14-stud region, and a large display plaque, such as 8×16, to stand
  beside a kit map or go on the back of the frame. A sticker needs a smooth surface, so the label
  piece is a black tile, set on a black plate when it stands alone; planning confirms the parts and
  their black availability from the cited catalogs. (user)
- Q: What goes on a sticker? → A: The map title, a one-line description, the color legend (swatches
  and what they mean), the data credit and 98138.world, plus the required disclaimer "Not
  affiliated with or endorsed by The LEGO Group."; the small plaque keeps the title and description
  (and the disclaimer). (user)
- Q: Can the plaque be part of a build? → A: On a Winkel board the plaque can optionally sit in a
  margin corner as part of the build: the recipe picks a corner, and the layout, preview, parts list
  and sheets swap the square tiles under the plaque for the black tile. This comes after 016 ships.
  (user)

- Q: Where does the sticker's line come from? → A: an optional sticker table in the recipe (a
  line, an optional title and optional no-data labels), falling back to the recipe's title and
  description. The eight bundled recipes each get one, with lines drafted in planning for the
  owner's approval; their recorded recipe checksums change in every output, and nothing else does
  (user).
- Q: Do the stickers for the two kit-design maps say "Official"? → A: no. Their sticker titles
  drop it (for example "World Map, kit 31203 design" and "Kit 31203 look, from bathymetry"); the
  recipes' own titles and the web pages stay as they are (user).

### Session 2026-11-23 (planning)

- Q: How does the command give its JSON output (FR-015, FR-016)? → A: `--format json` alongside
  `pdf` and `svg` (agent decision: the `parts list --format json` pattern; research.md R11).
- Q: What happens to a plaque on the kit template (FR-021)? → A: `--plaque CORNER` on the kit is
  an error; a recipe's `[margin].plaque` on a kit build is ignored with 016's note, so the recipe
  still builds (agent decision: 016's contract ignores `[margin]` on kit builds; research.md).
- Q: The `official-31203` data credit from the registry says "Official LEGO 31203 World Map design
  grid". What does its sticker say? → A: the sticker table may set an optional `credit` line that
  replaces the large sticker's "Data:" lines only; the print sheet keeps every registry citation.
  `official-31203` sets one without "Official", approved with the other texts (agent decision,
  close call: follows the owner's "drop Official" answer; research.md R9).
- Q: What display step keeps A, B and C legends identical for bathymetry? → A: two significant
  digits of the built range (1 °C, 100 m), not 10 m, which fails on the test fixtures (agent
  decision: research.md R8).
- Q: Does FR-004's sticker table list the `credit` line? → A: yes: FR-004 and the Key Entities
  now name the optional credit line decided above, which replaces only the large sticker's data
  credit (agent, planning: aligns the requirement with contracts/recipe-sticker.md and
  data-model.md StickerText; found by analyze).
- Q: FR-018 says "additions only", but the manifest's `total_bytes` grows; is that a change? → A:
  it is the one existing value that changes: `total_bytes` is the site's total size and counts the
  sticker files; every variant entry and file stays as it is (agent, planning: contracts/web.md;
  found by analyze).

### Session 2026-11-23 (autonomous clarify)

- Q: Does anything on a sticker depend on the combination (A, B, C)? → A: Only rank-derived legend
  values, and only slightly: the land shadow covers 392, 390 and 389 ocean studs in A, B and C, and
  rank classes share out the supply left after it, so `ocean-sst`'s third inner bound is 10.97 °C in
  A and 11.01 °C in B and C, and `official-31203-bathymetry`'s first is 801 m against 799 m; bins
  bounds, titles, credits and parts do not change. So there is one sticker set per map and
  template. Legend values come from the recipe's own arrangement (A unless the recipe sets one; B
  for the ENSO maps) and are rounded to a display step at which A, B and C agree (whole °C and 100 m,
  two significant digits of the built range; planning, research.md R8); a test checks that A, B and C give identical sticker sets for
  every bundled map. The command has no `--arrangement` option. (auto-resolved: measured with
  `maps/cells.py` `map_cells` on the cached datasets; `maps/build.py` draws the shadow as hung and
  nets it from the rank supply)
- Q: How is each legend entry labelled? → A: Bins classes by their range in the layer's units, end
  classes open ("below 150 m", "3,000 m and above"), so the outer bounds that only close the list
  are never printed; rank classes by the boundaries between the built classes, as `map_cells`
  derives them; a layer's second legend unit when the recipe gives one (rainfall: mm/yr); `log10`
  layers in the data's units; background classes by role ("land", "offshore", "coast ring");
  override cells by the override's name; the shadow as "land shadow"; a categorical layer
  (`official-31203`) by its colors only, as the official design's colors. Every class of the
  recipe's scale is listed, even with no studs, so the two ENSO maps keep one shared legend.
  (auto-resolved: `maps/classify.py` and 015 FR-013 for open end classes; `maps/cells.py`
  `_derived_bounds` and `_BACKGROUND_LABELS`; recipe comments in `ocean-el-nino.toml` and
  `rainfall.toml`; 013 `[<layer>.legend]`; 012 bins bounds in data units)
- Q: What is the data credit? → A: Each dataset the map uses (layer datasets, a dataset that splits
  land from ocean, override datasets and, on a template, the template's dataset) by its registry
  title and DOI, or its publisher when it has no DOI. Measured at 5 pt Helvetica the widest of
  these lines is 118 mm, inside the large sticker. Each dataset's full citation and license go on
  the print sheet. (auto-resolved: constitution IV; `data/datasets.json`; `Recipe.datasets()`;
  widths from the PDF font metrics)
- Q: The small sticker carries no data credit; does that meet constitution IV ("citation and
  license MUST appear in the map's outputs")? → A: Yes: the output is the print sheet (and SVG
  set), which carries each dataset's full citation and license beside the stickers, and the large
  sticker carries the credit. The small sticker keeps exactly the owner's content. (auto-resolved:
  constitution IV; owner answer on content)
- Q: Which parts make the plaques, and are they made in Black? → A: Small: tile 6×6 (10202),
  standalone on plate 6×6 (3958); large: tile 8×16 (4974), standalone on plate 8×16 (92438). The
  pinned Rebrickable elements snapshot (SHA-256 `dfc8641d…`, already cited in `part_colors.json`)
  has one Black element for each: 6155125, 395826, 6484420 and 6094066. None is in kit 31203.
  (The project owner chose the smooth tile 4974 on 2026-11-24, in place of the textured 90498,
  element 4603646; see Session 2026-11-24.)
  Planning adds them, Black only, to the cited part data with feature 016's method for part 3070b
  (pinned BrickLink catalog pages) and confirms them. (auto-resolved: the snapshot;
  `data/kit_31203_inventory.json`; 016 research R10)
- Q: How does a maker learn which parts to buy for a plaque? → A: The print sheet, the command's
  text and JSON output and the map page list each plaque's parts: the tile and, standalone, the
  plate, with quantity, LEGO element and design IDs, BrickLink item and color, and Rebrickable part
  and color, all cited; they also say the sticker is printed, not a LEGO part. Standalone plaques
  get no price estimate and no marketplace export. (auto-resolved: constitution V; feature 005
  parts lists)
- Q: How does the in-margin plaque count in the parts list, leftovers and price estimates? → A: One
  lot, tile 6×6 in Black, with cited IDs, replaces the 36 square tiles under it; the kit has none,
  so the one-kit top-up buys it; leftovers are unchanged because they count kit map elements only;
  the estimate prices the lot from the snapshot, or is marked incomplete with the lot unpriced.
  (auto-resolved: 014 Clarifications and FR on leftovers; 011 unpriced lots; 016 research R14,
  R15)
- Q: What does the print sheet look like? → A: As the build sheets: Letter by default or A4
  (`--paper`), "Print at 100% (no fit-to-page)", a scale bar, deterministic PDF bytes and
  deterministic SVG text, the PDF standard Helvetica fonts (Latin-1 only; otherwise an error that
  suggests SVG), SVG text in Helvetica or Arial, no images. One page holds the large and the small
  sticker. (auto-resolved: `sheets/compose.py`, `sheets/render_pdf.py`, `sheets/render_svg.py`)
- Q: Does the command read a recipe or a layout? → A: A recipe, like `map cells`: rank-derived
  bounds need the build, and layouts do not record them. It builds from cached data and never
  downloads. (auto-resolved: `cli/map.py` `cells`; 015 FR-002)
- Q: What is the smallest text? → A: 5 pt. The disclaimer at 5 pt is 40.5 mm wide and fits one
  line of the small sticker; every bundled title and line fits by wrapping and shrinking. (agent
  decision: measured with the PDF font metrics)
- Q: Where in the corner does the in-margin plaque go, and how is it chosen? → A: Corners
  `top-left`, `top-right`, `bottom-left`, `bottom-right`, by a recipe key or a `map build` option;
  the option wins, and `none` turns a recipe's plaque off. The tile lies wholly in the corner's
  clear block and in one 16×16 module, with at least one margin stud between it and the outline
  ring; the exact offset is set in planning and shown to the owner on a preview. The kit template
  has no margin, so a plaque there is an error. (auto-resolved: owner answer; 016 research R12
  options win over the recipe, R20 clear block 14 × 14; modules are separate 16×16 sections,
  `sheets/sections.py`)
- Q: How does a layout record the plaque? → A: Only when one is placed: its part, color, corner and
  covered studs; those studs carry no 1×1 piece; layouts without it read as before. (auto-resolved:
  016 Clarifications, `metadata.template` written only for non-kit templates; 007
  `metadata.arrangement`, absent = A)
- Q: Does the web site show the in-margin plaque on its Winkel variants? → A: No. The bundled
  recipes do not name a corner and the plaque is optional, so the site's variants stay as feature
  016 builds them; the site offers each variant's sticker set. (auto-resolved: owner answer on the
  plaque; 016 FR-019)
- Q: How do Winkel stickers name the projection? → A: On a non-kit template the sticker line on
  both stickers ends with the template's projection ("Winkel tripel projection"), and the large
  sticker's credit includes the template's dataset (ETOPO 2022 decided land and ocean). (auto-
  resolved: 016 research R11 citations for template builds)

### Session 2026-11-24 (owner decisions)

- Q: Which 8×16 tile carries the large sticker: the textured 90498 or a smooth one? → A: The smooth
  tile 4974, "Tile 8 x 16 with Bottom Tubes, Polished Surface" (Black element 6484420, in the
  pinned Rebrickable elements snapshot), replaces 90498 "Textured Surface" (element 4603646)
  wherever this spec names the large plaque's tile (the plaque table and FR-014 included). The
  plate 92438, the small plaque (tile 10202 on plate 3958) and the sticker sizes stay. (project
  owner, 2026-11-24)

The sticker line comes from an optional sticker table in the recipe (FR-004; owner, 2026-11-23).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Print the stickers for a map from the command line (Priority: P1)

A maker runs one command for a recipe and gets a print-ready sticker set: a page to print on
sticker paper with the large and the small sticker at true size, cut marks, the parts to buy for a
standalone plaque, and the map's full data credit, or one SVG file per sticker for a print shop or
a cutting machine.

**Why this priority**: it is the outcome the owner asked for, works for every map, and needs
nothing from feature 016 or the web site (constitution VI).

**Independent Test**: from the dataset fixtures, make the sticker set for `ocean-sst`,
`land-elevation`, `rainfall` and `official-31203`; check each sticker's size, text, legend entries
and disclaimer in the page model without rendering, render PDF and SVG, and compare the sets made
for combinations A, B and C.

**Acceptance Scenarios**:

1. **Given** the cached ERSST v5 dataset, **When** the maker runs `map stickers ocean-sst -o
   stickers.pdf`, **Then** the file has one Letter page with the large and the small sticker at
   true size, each with a black bleed and cut marks, the note "Print at 100% (no fit-to-page)", a
   scale bar, the plaque parts, the dataset's full citation and license, and the disclaimer.
2. **Given** that page, **When** the maker reads the large sticker, **Then** it shows the title
   "Ocean temperature", the sticker line, nine ocean swatches each labelled with its °C range from
   the built classes, the White land, the land shadow on the Earth Blue swatch, the data credit
   (ERSST v5 title and DOI), "98138.world" and "Not affiliated with or endorsed by The LEGO Group."
3. **Given** the same page, **When** the maker reads the small sticker, **Then** it shows only the
   title, the sticker line and the disclaimer.
4. **Given** `--paper a4`, **When** the command runs, **Then** the page is A4 and the stickers keep
   their size; **given** `--format svg -o DIR`, **Then** DIR holds one SVG per sticker at true size
   in millimetres with the cut line as a separate, named element.
5. **Given** `land-elevation`, **When** its stickers are made, **Then** the large legend lists ten
   land swatches in metres, the first "below 150 m" and the last "3,000 m and above", the ocean's
   "offshore" and "coast ring" colors and the land shadow.
6. **Given** `rainfall`, **When** its stickers are made, **Then** the legend gives land and ocean
   classes in mm/yr with open end classes, one White land swatch for Antarctica and Greenland, a
   White ocean swatch for sea ice and the Black land shadow with a visible outline, and the credit
   names GPCP v2.3 and the NSIDC sea ice record.
7. **Given** `official-31203` (no download needed), **When** its stickers are made, **Then** the
   legend shows the nine ocean colors as the official design's colors, without values, and the
   credit names the design grid extracted from the kit's building instructions.
8. **Given** any bundled map, **When** its sticker set is made with the map built in A, B and C,
   **Then** the three sets are identical.
9. **Given** a recipe whose dataset is not cached, **When** the command runs, **Then** it stops
   with the dataset's name and the `dataset fetch` command, writes nothing and never downloads.
10. **Given** the command's output, **When** it finishes, **Then** it lists for each plaque the
    tile and, standalone, the plate, with cited LEGO, BrickLink and Rebrickable IDs in Black, notes
    that the sticker is printed, not a LEGO part, and ends with the disclaimer.

---

### User Story 2 - Download the stickers from the web site (Priority: P2)

A visitor to a map page on 98138.world sees the map's stickers and the parts for a plaque, and
downloads a print sheet (Letter or A4) or the SVG files.

**Why this priority**: most people find the maps on the site, but the CLI comes first
(constitution VI).

**Independent Test**: run the web prebuild offline with the fixtures; the manifest lists a sticker
set per map with sizes and checksums, each map page links to it and shows the stickers, and the
other files of every variant are unchanged by the sticker step.

**Acceptance Scenarios**:

1. **Given** the bundled maps, **When** the site is prebuilt, **Then** each map has one sticker set
   (print sheet Letter, print sheet A4, small SVG, large SVG) made with the library and listed in
   the manifest with size, SHA-256 and media type.
2. **Given** a map page in combination A, B or C, **When** the visitor opens it, **Then** the page
   shows both stickers as images with text alternatives, the parts for a standalone plaque with
   their IDs, the note that printed colors only approximate the LEGO colors, and the sticker
   downloads, the same for all three combinations.
3. **Given** JavaScript is off, **When** the visitor opens a map page, **Then** the stickers and
   their downloads work.
4. **Given** feature 016's Winkel variants on the site, **When** the site is prebuilt, **Then** each
   Winkel variant has its own sticker set, which names the projection.

---

### User Story 3 - A plaque in a Winkel margin corner (Priority: P3)

A maker building a map on the Winkel tripel template places the small plaque in one margin corner
as part of the build. The layout, preview, parts list, exports and build sheets put one black 6×6
tile where the square margin tiles would be, and the maker sticks the small sticker on it.

**Why this priority**: the owner wants it as an option, and it needs feature 016 to ship first.

**Independent Test**: with feature 016's fixture template, build `ocean-sst` with the plaque in the
bottom-left corner; the plaque covers 36 margin studs inside the corner's clear block, no land or
ocean stud changes, the parts list has one Black 6×6 tile and 36 fewer square tiles, and the sheets
and preview show it.

**Acceptance Scenarios**:

1. **Given** the confirmed Winkel template, **When** the maker runs `map build ocean-sst --template
   winkel-tripel --plaque bottom-left -o layout.json` (or the recipe names the corner), **Then** the
   layout records the plaque, its 36 studs carry no square tile, and the land, ocean and other
   margin studs equal those of the build without the plaque.
2. **Given** that layout, **When** the maker asks for the parts list and exports, **Then** they
   list one Black 6×6 tile with cited IDs and 36 fewer square tiles; the one-kit top-up buys the
   tile; leftovers are unchanged; the price estimate prices the tile or marks itself incomplete
   with the tile unpriced.
3. **Given** that layout, **When** the maker writes the preview and the build sheets, **Then** the
   preview draws the plaque as one black rectangle, and its section page draws it as one outlined
   rectangle labelled with its part, counted in that section and in the legend.
4. **Given** a Winkel build, **When** the maker makes its stickers with `--template winkel-tripel`,
   **Then** both stickers' lines end with "Winkel tripel projection" and the large sticker's credit
   includes ETOPO 2022.
5. **Given** the plaque on the kit template, an unknown corner, or a plaque that does not fit the
   corner's clear block, **When** the map is built, **Then** the build stops with an error that
   says why (for a misfit, the space needed and the space available).
6. **Given** a recipe that names a corner, **When** it is built with `--plaque none`, **Then** the
   layout has no plaque.

---

### Edge Cases

- The same color twice on one map (in `ocean-sst` Earth Blue is the coldest class and the land
  shadow): one swatch lists both meanings.
- A rank-derived class whose bounds round to the same value (ocean-sst's coldest class sits at
  −1.8 °C): it shows that one value.
- A class with no studs: still listed, so the scale reads whole.
- Black or very dark swatches (the Black land shadow) on the black sticker: every swatch has a thin
  light outline.
- A legend with more entries than the large sticker holds, or a title or line that does not fit at
  5 pt: the command stops, names the layer or field, and gives the space needed and available.
- Text outside Latin-1 in a PDF (the PDF uses the standard Helvetica font): the command stops and
  suggests `--format svg`.
- A home printer cannot print white: the sticker is printed on white sticker paper; the black is
  ink and the text is the paper.
- The palette chooser's custom colors (feature 015) never reach the stickers; stickers use the
  map's built colors.
- A no-data class without a label (a custom recipe): it reads "no data".
- The in-margin plaque on a board whose margin color is not Black: allowed; the plaque stays Black.
- The in-margin plaque never covers outline-ring studs and never crosses a 16×16 module boundary.
- `map cells` for a recipe with an in-margin plaque (or with `--plaque`): its studs are marked, and the chooser never
  recolors them.
- A price snapshot without the 6×6 tile: the Winkel estimate is incomplete with that lot unpriced;
  other estimates are unaffected.

## Requirements *(mandatory)*

### Functional Requirements

**Sticker content**

- **FR-001**: The system MUST make a sticker set (one small and one large sticker) for any recipe
  that builds, on the kit template, and (US3, after 016) on any confirmed template.
- **FR-002**: The large sticker MUST show the map title, the sticker line, the color legend, the
  data credit, "98138.world" and "Not affiliated with or endorsed by The LEGO Group."
- **FR-003**: The small sticker MUST show the map title, the sticker line and the disclaimer, and
  nothing else.
- **FR-004**: The sticker title MUST be the title in the recipe's optional sticker table when it
  sets one, otherwise the recipe's title. The sticker line MUST come from that table (a line, an
  optional title, an optional credit line and optional no-data labels), falling back to the
  recipe's description. A credit line, when set, replaces only the large sticker's data credit;
  the print sheet keeps every dataset's full citation and license. This
  feature adds a sticker table to each of the eight bundled recipes, with lines the owner
  approves; their outputs then differ only in their recorded recipe checksum. Bundled sticker
  titles MUST NOT contain "Official": the two kit-design recipes get sticker titles without it
  (for example "World Map, kit 31203 design" and "Kit 31203 look, from bathymetry"), while their
  recipe titles and web pages stay as they are.
- **FR-005**: The legend MUST be computed from the built map: one swatch per color of each layer and
  the shadow, in the recipe's color order, labelled as the Clarifications set out (ranges in units
  with open end classes, rank boundaries, roles, override names, "land shadow", the categorical
  design colors). A color with two meanings MUST show both on one swatch.
- **FR-006**: There MUST be one sticker set per map and template, identical for A, B and C. Legend
  values come from the recipe's own arrangement and are rounded to a display step at which A, B and
  C agree.
- **FR-007**: The data credit MUST name each dataset the map uses by registry title and DOI (or
  publisher); each dataset's full citation and license MUST appear on the print sheet.
- **FR-008**: Swatches MUST be drawn in each part color's cited sRGB with a thin light outline. The
  look is white text and color swatches on black; stickers MUST NOT contain a LEGO logo, wordmark,
  LEGO label artwork or any image.

**Print files**

- **FR-009**: Each sticker MUST be about 1 mm smaller than its tile on every side: the small
  sticker about 45.8 mm square for a 6×6 tile, the large about 61.8 × 125.8 mm, landscape, for an
  8×16 tile (tile size = studs × 8.0 mm − 0.2 mm; planning fixes the values).
- **FR-010**: The print sheet MUST be a PDF page, Letter (default) or A4, with both stickers at
  true size, about 2 mm of black bleed past each cut line, cut marks outside the bleed, "Print at
  100% (no fit-to-page)", a scale bar, the plaque parts, each dataset's full citation and license, a
  note that printed colors only approximate the LEGO colors, the recipe's id and checksum, the tool
  version and the disclaimer, all outside the cut lines.
- **FR-011**: The SVG output MUST be one file per sticker at true size in millimetres, with the
  bleed, the cut marks, the disclaimer in the file's description, and the cut line as a separate,
  named element.
- **FR-012**: The same input MUST give the same bytes.
- **FR-013**: Text MUST use the PDF standard Helvetica fonts (Latin-1) in PDFs and name Helvetica
  and Arial in SVGs. Each text has a preferred size and a minimum of 5 pt; text wraps, then shrinks;
  text that does not fit at 5 pt MUST stop the command with the field and the space needed.

**Parts for a plaque**

- **FR-014**: The four plaque parts in Black (tile 6×6 10202, plate 6×6 3958, tile 8×16 4974,
  plate 8×16 92438) MUST be added to the packaged part data with cited LEGO, BrickLink and
  Rebrickable IDs from pinned sources, regenerated with the part-data maintainer tools' `--check`.
- **FR-015**: The print sheet, the command's text and JSON output and the map page MUST list each
  plaque's parts: the tile and, standalone, the plate, with quantity and cited IDs, and say that the
  sticker is printed, not a LEGO part.

**Command line**

- **FR-016**: A library function and a CLI command (`map stickers RECIPE -o OUT [--format pdf|svg|json]
  [--paper letter|a4] [--cache-dir DIR]`, and `--template ID` after 016) MUST make the sticker set
  from local files. It builds the map like `map cells`, never downloads, prints a summary, the
  plaque parts and the disclaimer, and fails like `map build` when a dataset is not cached.
- **FR-017**: Making stickers MUST NOT change any layout, parts list, export, sheet, cells file,
  price estimate or report.

**Web (P2)**

- **FR-018**: The web prebuild MUST write each map's sticker set with the library and list its
  files in the manifest (kind, size, SHA-256, media type, file name), as additions only, once per
  map rather than per combination. The one existing value that changes is the manifest's
  `total_bytes` (the site's total size), which counts the sticker files too.
- **FR-019**: Map pages MUST show the stickers as images with text alternatives, the plaque parts
  and the sticker downloads, and MUST work without JavaScript. The service MUST serve the files
  from the built output only and MUST NOT import the CLI library.
- **FR-020**: After feature 016 merges, each template variant on the site MUST get its own sticker
  set; its layout files stay as 016 builds them, with no plaque.

**Plaque in a Winkel margin corner (P3, after 016)**

- **FR-021**: A recipe key and a matching `map build` option (`--plaque`) MUST choose a corner
  (`top-left`, `top-right`, `bottom-left`, `bottom-right`) for the small plaque; the option wins,
  and `none` turns a recipe's plaque off. `--plaque CORNER` on the kit template MUST stop the build
  with an error; a recipe's plaque key on a kit build is ignored with 016's note for `[margin]`
  settings (planning).
- **FR-022**: The plaque's tile MUST lie wholly in the chosen corner's clear block and in one 16×16
  module, with at least one margin stud between it and the outline ring; otherwise the build MUST
  stop with the space needed and available.
- **FR-023**: The layout MUST record the plaque (part, color, corner and covered studs) only when
  one is placed; those studs carry no 1×1 piece; layouts without it MUST read as before.
- **FR-024**: Previews MUST draw the plaque as one black rectangle; build sheets MUST draw it as one
  outlined rectangle labelled with its part and count it in its section and the legend; parts
  lists, exports and the one-kit top-up MUST list one tile 6×6 in Black and 36 fewer square tiles;
  leftovers MUST stay kit map elements only; price estimates MUST price the tile or mark the lot
  unpriced; `map cells` MUST mark its studs; `validate` MUST accept a recorded plaque.
- **FR-025**: Stickers for a map built on a non-kit template MUST end the sticker line with the
  template's projection on both stickers and credit the template's dataset on the large one.

**Compliance**

- **FR-026**: Every sticker, print sheet, command output and web page added by this feature MUST
  carry "Not affiliated with or endorsed by The LEGO Group." and MUST NOT imply endorsement.

### Key Entities

- **Sticker set**: map (recipe id and checksum), template, the small and the large sticker, the
  plaque parts, the credits.
- **Sticker**: size (small or large), cut size, bleed, text blocks (title, line, legend, credit,
  site, disclaimer) with their font sizes.
- **Legend entry**: layer, part, color (cited key and sRGB), meanings (range and units, role or
  name).
- **Plaque**: size, label tile and, standalone, plate, both Black, with cited IDs.
- **In-margin plaque**: template, corner, the studs it covers, its tile.
- **Sticker text (recipe sticker table)**: optional line, title, credit line and no-data labels
  (FR-004).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For each of the eight bundled maps the command makes a sticker set in PDF (Letter and
  A4) and SVG, and every cut line is within 0.1 mm of its stated size in the file.
- **SC-002**: Every bundled map's stickers fit all their content at 5 pt or larger.
- **SC-003**: For every bundled map, the sticker sets made from builds in A, B and C are identical,
  and making a set twice gives identical bytes.
- **SC-004**: Every sticker and print sheet carries the disclaimer and contains no image.
- **SC-005**: Every plaque part has cited LEGO, BrickLink and Rebrickable IDs in Black.
- **SC-006**: Making stickers changes no other output; if the bundled recipes gain sticker lines
  (FR-004), their layouts, parts lists, sheets and cells files differ from before only in the
  recorded recipe checksum, and no stud, part, color or count changes.
- **SC-007**: Making a sticker set takes less than 5 seconds more than building the map.
- **SC-008**: Every map page on the site offers its stickers, and the site output grows by less
  than 2 MB.
- **SC-009**: A Winkel map with the in-margin plaque has 10,204 one-stud pieces and one Black 6×6
  tile, and its land and ocean pieces equal the build without the plaque.
- **SC-010**: All tests run offline.

## Assumptions

- Makers print the stickers themselves on white sticker paper (glossy or matte) or at a print shop,
  and cut them by hand or with a cutting machine. Printed swatches only approximate the cited part
  colors; the print sheet says so.
- The print sheet uses the PDF standard Helvetica fonts without embedding, as the build sheets do
  (feature 006); Arial and other metric-compatible fonts keep the layout. Embedding a font would
  need its license approved first.
- Sticker and tile sizes use the kit's 8.0 mm stud pitch (feature 006, from LDraw).
- The large plaque is landscape, 16 studs wide and 8 high.
- Every bundled recipe gets stickers: `official-31203`, `official-31203-bathymetry`, `ocean-sst`,
  `land-elevation`, `ocean-el-nino`, `ocean-la-nina`, `living-planet`, `rainfall`; after 016, also
  the five Winkel variants.
- Only the small plaque goes in a margin corner; the large one (8×16) does not fit a 14 × 14 clear
  block.
- The in-margin plaque's tile is priced like any other lot once the BrickLink price snapshot has a
  row for it; refreshing the snapshot needs the owner's credentials (feature 011).
- Out of scope: brick-built (stud-lettered) labels; printing, cutting or selling stickers; any
  print-service integration; LEGO logos, wordmarks or label artwork; stickers with the palette
  chooser's custom colors; custom sticker text on the web; the in-margin plaque on the site's
  variants; prices and marketplace exports for standalone plaques; plaque colors other than Black
  and sizes other than the two; stands, frames or mounting hardware; QR codes; a sheet of several
  maps' stickers.

# Feature Specification: Pacific-centred Arrangements D and E

**Feature Branch**: `010-pacific-arrangements`

**Created**: 2026-11-22

**Status**: Draft

**Input**: Design brief `specs/010-pacific-arrangements/design.md` (owner decisions 2026-11-22, in
conversation): add two frame combinations D and E beyond the three in the LEGO 31203 building
instructions, with instructions for assembling them "following the examples given for A, B and C",
in the CLI, the build sheets and the web site; the ENSO maps default to D. Not affiliated with or
endorsed by The LEGO Group.

## Context

The kit 31203 mosaic is 40 section bases (16 × 16 studs each) pegged into eight vertical strips of
five (strips A–H as the kit labels its section columns; 3 connector pegs per base joint,
pp. 134–136), and strips pegged side by side into three frames (p. 137): frame 1 America (strips
A–B, kit columns 0–31), frame 2 Europe & Africa (C–F, 32–95), frame 3 Asia & Australia (G–H,
96–127) (p. 138). The instructions show three combinations (pp. 7–8 and p. 139): A = 1·2·3,
B = 3·1·2, C = 2·3·1, each frame joint drawn with "15x" connector pegs.

A joint inside a frame (strip to strip, p. 137) uses the same 15 connector pegs as a joint between
frames (p. 139), so a frame can be unpegged between any two of its strips with no other parts. The
white border (pp. 140–153) is built once round the finished 8 × 5 board and is the same for any
strip order. The peg budget is 7 strip joints × 15 + 8 strips × 4 × 3 = 201 of the 205 supplied,
for any order. Therefore any cyclic rotation of the eight strips by whole strips (16 kit columns)
is buildable from one kit with no extra parts; A, B and C are rotations by 0, +32 and −32 columns.

This feature adds two such rotations (kit_31203_projection.json: left edge 168.9° W,
2.8125° per column; 180° = kit column 124.05):

| id | name | shift | strips as hung | groups as hung | centre (display col 64) | date line vs centre | outer edge | land rows cut at the edges |
|---|---|---|---|---|---|---|---|---|
| A | europe-africa | 0 | ABCDEFGH | 1·2·3 | 11.1° E | +60 cols | 168.9° W | 0 |
| B | americas | 32 | GHABCDEF | 3·1·2 | 78.9° W | −36 | 101.1° E | 36 |
| C | asia-australia | 96 (−32) | CDEFGHAB | 2·3·1 | 101.1° E | +28 | 78.9° W | 17 |
| **D** | **pacific** | **64** | **EFGHABCD** | **2b·3·1·2a** (frame 2 split between strips D and E) | **168.9° W** | **−4 (date line centred)** | **11.1° E** (Europe, Africa) | **27** |
| **E** | **asia-pacific** | **80** | **DEFGHABC** | **2b·3·1·2a** (frame 2 split between strips C and D) | **146.1° E** | **+12** | **33.9° W** (Atlantic) | **8** |

- D, "Pacific (date line)": the date line is 4 columns (11°) left of centre; the Pacific basin
  (120° E–80° W) spans display columns 39–96. Cost: the board's edges cut Europe and Africa at
  11° E.
- E, "Asia-Pacific (146° E)": the usual Asia-Pacific world map; the edges fall in the mid-Atlantic,
  so only Greenland and Antarctica are cut; the Pacific is whole but right of centre.
- Rejected: a date-line-exact roll (68 columns) is not strip-aligned and could not re-hang a built
  board.
- Frame part names: "2a" is the left part of frame 2 in kit order (the strips with lower kit
  columns), "2b" the right part. D: 2a = strips C–D, 2b = E–F. E: 2a = strip C, 2b = D–F.

The map pipeline is already arrangement-independent: building with a column shift of 64 or 80
works unchanged (previews checked); the land shadow moves only at the seams (387 / 391 cells vs
390 in B).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Hang any map as D or E (Priority: P1)

A builder wants a Pacific-centred board. They build any recipe, or re-hang any existing layout, as
combination D or E with the same options and recipe key that already work for A, B and C, and
every downstream command (check, validate, parts lists, section counts, build sheets) understands
the result.

**Why this priority**: without D and E in the reference data and the CLI nothing else (sheets,
ENSO defaults, web) can exist; on its own it already gives a usable Pacific-centred layout.

**Independent Test**: `map build official-31203 --arrangement D -o d.json` and
`layout arrange a.json --arrangement asia-pacific -o e.json` produce valid layouts whose positions
equal the A layout rolled by 64 and 80 columns; `validate`, `parts list`, `sheets counts` accept
them; A, B and C outputs are unchanged.

**Acceptance Scenarios**:

1. **Given** any recipe, **When** it is built with `--arrangement D` (or `pacific`, any case),
   **Then** the layout's x is the column as hung (display = (kit + 64) mod 128) and
   `metadata.arrangement` records D, its strip order, its frame groups, that it is not among the
   building instructions' combinations, and its citation (pp. 134–139 and 140).
2. **Given** the same with `--arrangement E` (or `asia-pacific`), **Then** the same holds with a
   shift of 80.
3. **Given** a layout hung A, B, C or D, **When** `layout arrange --arrangement E` re-hangs it,
   **Then** every position moves by whole strips and colors and parts are kept; arranging back to
   the original returns the identical layout.
4. **Given** a recipe with `arrangement = "D"` or `"E"`, **When** it is built without
   `--arrangement`, **Then** it hangs in that combination; an explicit `--arrangement` still wins.
5. **Given** a layout hung D or E, **When** `validate`, `parts list`, `sheets counts` and `map
   check` read it, **Then** they accept it and name the combination; the land/sea mask is checked
   as hung.
6. **Given** an unknown value such as `F`, **When** it is passed to `--arrangement` or a recipe,
   **Then** the error lists all valid values A–E and their names.
7. **Given** layouts, sheets and parts lists produced for A, B and C before this feature, **When**
   they are produced again, **Then** they are identical except for the additive assembly content of
   User Story 2.

---

### User Story 2 - Assembly instructions for every combination (Priority: P2)

A builder with a D or E layout needs to know how to put the frames together, since the building
instructions only show A, B and C. Their build sheets (PDF and SVG) include an assembly page drawn
in the style of the instructions' p. 139: the strip groups as hung, which joint of frame 2 to
unpeg (its 15 connector pegs), which joints to make (15 pegs each) and that the border goes round
the whole board as in pp. 140–153. A, B and C get the same style of page for consistency.

**Why this priority**: D and E are only buildable in practice with these steps; it depends on US1.

**Independent Test**: `sheets build` on a D layout writes a PDF with an assembly page whose
content (checked in the page model and in the SVG output) names the groups 2b·3·1·2a, the frame-2
joint between strips D and E to unpeg, the three joints to make, the peg counts, the border and the
citation, and labels D as not among the instructions' combinations.

**Acceptance Scenarios**:

1. **Given** a layout hung D, **When** build sheets are made, **Then** the set has one assembly
   page showing strips E F G H A B C D left to right grouped as 2b·3·1·2a, the unpeg step "frame 2
   between strips D and E (15 connector pegs)", the joints to make (F|G, H|A, B|C, 15 pegs each),
   and the border step.
2. **Given** a layout hung E, **Then** the same with groups 2b·3·1·2a, frame 2 unpegged between
   strips C and D, and joints F|G, H|A, B|C.
3. **Given** a layout hung A, B or C, **Then** the assembly page shows the three frames in its
   order with its frame joints (15 pegs each), no unpeg step, the border step, and cites
   pp. 7–8 and 139.
4. **Given** any assembly page, **Then** it carries the footer, scale bar and the disclaimer like
   every other page, uses only shapes and text drawn from the data (no LEGO artwork), and the
   overview's page list mentions it.
5. **Given** the runbook, **When** a reader looks up D or E, **Then** it documents the assembly
   steps in text.

---

### User Story 3 - ENSO maps date-line-centred by default (Priority: P3)

The owner wants the El Niño and La Niña maps centred on the date line. Both ENSO recipes default
to D; their extra-tile counts in D are re-checked and the documentation updated.

**Why this priority**: a one-key recipe change once US1 exists, with documentation.

**Independent Test**: `map build ocean-el-nino` (no `--arrangement`) records D, "from the recipe";
`map list` shows D for both ENSO recipes; `--arrangement B` still builds the 009 layout.

**Acceptance Scenarios**:

1. **Given** `ocean-el-nino` or `ocean-la-nina`, **When** built without `--arrangement`, **Then**
   the layout is hung D and the build output says the combination came from the recipe.
2. **Given** either recipe with `--arrangement B`, **Then** the output equals the 009 B layout.
3. **Given** the recipes' comments, spec 009 notes and the runbook, **Then** they state the D
   default and the measured extra-tile counts and shadow cells in D.

---

### User Story 4 - D and E on 98138.world (Priority: P4)

A visitor to 98138.world can open every map in all five combinations; the map page's combination
navigation lists A–E, and the about page ("ways to hang the frames") and figure captions describe
D and E honestly: not among the instructions' combinations, why they are possible, and how to
assemble them. The ENSO maps open in D.

**Why this priority**: the public face of the feature; it depends on US1–US3.

**Independent Test**: the web prebuild for a subset (for example `official-31203` and
`ocean-el-nino`, all five combinations) writes a manifest the catalog accepts; the test client
renders `/about` and `/maps/ocean-el-nino/D` with the D text; `/maps/ocean-el-nino` redirects to D.

**Acceptance Scenarios**:

1. **Given** the prebuild, **When** it runs with default options, **Then** it builds 6 maps × 5
   combinations = 30 variants and the manifest lists five arrangements with their strip order,
   groups, official flag, citation and assembly steps.
2. **Given** the catalog, **When** it loads a manifest, **Then** it requires the five combinations
   A–E for every map and rejects a manifest with three.
3. **Given** the map page for D or E, **Then** the combination nav lists A–E, the caption says the
   combination is not among the building instructions' three, why it is possible, and points to
   the assembly steps; the page for A, B or C is unchanged apart from the two extra nav entries and
   any additive assembly text.
4. **Given** the about page, **Then** "ways to hang the frames" covers five combinations, marks D
   and E as unofficial, cites pp. 7–8 for A–C and pp. 134–140 for why D and E are possible, and
   summarises how to assemble them.
5. **Given** the web runtime, **Then** it still never imports `lego_image_processor`.
6. **Given** the deploy docs, **Then** they state 30 variants and the new image size.

---

### Edge Cases

- A layout whose `metadata.arrangement` records an id outside A–E is rejected with the list of
  valid ids.
- A layout written by this version with D or E read by an older tool version: older versions reject
  the unknown id (accepted; no back-port).
- Re-hanging between D and E (shift difference 16) moves whole strips only; sections stay whole.
- Section labels on a D/E sheet are as hung, and each section page names its physical frame part
  (for example "frame 2 of 3 (Europe & Africa), part 2b") and its kit section.
- Build sheets for a subset of sections (`--sections`) still include the assembly page.
- The land shadow, halo and mix are computed on the board as hung, so their cell counts in D and E
  differ from A–C only at the seams.
- The arrangements data file must reject a strip order that is not a rotation of A–H, a shift that
  does not match it, or a group list that does not match the strip order.

## Requirements *(mandatory)*

### Functional Requirements

**Reference data**

- **FR-001**: The arrangements data file MUST define five combinations A–E. Its model MUST be able
  to express a frame split into parts (strip order and frame parts such as 2a/2b). A, B and C MUST
  behave exactly as before (same ids, names, centres, frame order, column shift and layout record).
- **FR-002**: D (`pacific`, shift 64, strips EFGHABCD, groups 2b·3·1·2a, frame 2 split between
  strips D and E) and E (`asia-pacific`, shift 80, strips DEFGHABC, groups 2b·3·1·2a, frame 2 split
  between strips C and D) MUST be present with their centre descriptions.
- **FR-003**: D and E MUST be marked as not among the building instructions' combinations and MUST
  cite pp. 134–139 (joints) and p. 140 (border) for why they are possible; A–C MUST keep their
  pp. 7–8 citation. Every record carries the disclaimer.
- **FR-004**: Loading the data MUST validate that each strip order is a cyclic rotation of A–H,
  that the column shift equals 16 × the display position of strip A (mod 128), and that the frame
  groups follow from the strip order.

**CLI**

- **FR-005**: `--arrangement` MUST accept D and E and the names `pacific` and `asia-pacific` (any
  case) everywhere A–C work: `map build`, `map check`, `layout arrange`, the recipe key
  `arrangement`, and every command that reads a layout's arrangement (sheets, counts, validate,
  parts). Help text and error messages MUST list all five.
- **FR-006**: The layout's `metadata.arrangement` for D and E MUST record id, name, centre, frame
  order, column shift, strip order, frame groups, that it is not in the instructions, and its
  source citation; for A–C the record MUST stay exactly as before.

**Assembly instructions**

- **FR-007**: Build sheets (PDF and SVG) for every layout MUST include one assembly page, placed
  after the section pages (the kit's instructions join the frames after the sections), following
  the p. 139 example: the board's strips as hung grouped into frames or frame parts, joints drawn
  with their peg counts (15 connector pegs each), and numbered steps.
- **FR-008**: For D and E the page MUST state the frame-2 joint to unpeg (between which strips; its
  15 connector pegs, reused for a new joint), the joints to make left to right, the peg budget
  (201 of 205, the same as A–C) and that the border goes round the whole board as in pp. 140–153;
  and MUST label the combination as not among the building instructions' three, with its citation.
- **FR-009**: For A, B and C the page MUST show the same style of block (frames in order, joints to
  make, border step) citing pp. 7–8 and 139. Existing A–C sheet pages MUST be unchanged except for
  the added page, the page count in the footers and overview text that lists the assembly page.
- **FR-010**: The overview page's arrangement text MUST name the groups as hung (e.g. 2b·3·1·2a)
  and, for D and E, say they are not among the instructions' combinations; section pages for D and
  E MUST name the frame part.
- **FR-011**: The runbook MUST document the D and E assembly steps in text.

**ENSO recipes**

- **FR-012**: `ocean-el-nino` and `ocean-la-nina` MUST default to `arrangement = "D"`. Their
  extra-tile counts and land-shadow cells in D MUST be re-measured and recorded in the recipe
  comments, the spec 009 notes and the runbook.

**Web**

- **FR-013**: The web site MUST offer combinations A–E for every map (6 maps × 5 = 30 variants);
  the prebuild, the manifest and the catalog validation MUST use five.
- **FR-014**: The map page's combination nav, the about page ("ways to hang the frames") and figure
  captions MUST describe D and E honestly: unofficial (not among the instructions' three), why they
  are possible (citations), and how to assemble them.
- **FR-015**: The web runtime MUST NOT import `lego_image_processor`; the manifest carries all
  arrangement text the pages show.
- **FR-016**: The deploy docs MUST state the variant count (30) and the new image size.

**General**

- **FR-017**: All tests MUST run offline and be written before the code they test.
- **FR-018**: Every user-facing output (CLI text, sheet pages, web pages) MUST carry "Not affiliated
  with or endorsed by The LEGO Group."

### Out of scope

- Arrangements that are not whole-strip rotations (for example the 68-column date-line-exact
  roll), mirrored boards or rows shifted vertically.
- Changing the building instructions' A–C content or making D or E the default for any recipe other
  than the two ENSO maps.
- Merging and deploying (done by the coordinating agent).

### Key Entities

- **Strip**: one of the eight vertical columns of five section bases, A–H, 16 kit columns each; it
  belongs to one frame.
- **Frame**: a group of strips pegged first (1: A–B, 2: C–F, 3: G–H).
- **Frame group (part)**: a run of strips of one frame that stay pegged together in an arrangement;
  a whole frame ("2") or a part ("2a", "2b").
- **Arrangement**: id, name, centre, strip order as hung, frame groups, column shift, whether it is
  in the building instructions, and its citation.
- **Joint**: the 15 connector pegs between two adjacent strips; a step to make or to unpeg.
- **Assembly page**: a build-sheet page with the strips as hung, joints and steps.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Any bundled recipe builds in D and E, and every layout re-hangs to any of A–E and
  back with an identical result.
- **SC-002**: The full CLI and web test suites pass offline; the outputs for A, B and C are
  identical to before except for the assembly page and page counts.
- **SC-003**: A D build-sheet PDF contains an assembly page a builder can follow to hang the board
  from one kit with no extra parts (unpeg one frame-2 joint, make three joints, 201 pegs in all).
- **SC-004**: The two ENSO maps build in D by default, with their extra-tile counts in D reported.
- **SC-005**: 98138.world serves 30 map variants; the about page and the D and E map pages state
  that D and E are not among the instructions' combinations and cite pp. 134–140.

## Assumptions

- The page facts in the design brief (pp. 7–8, 134–140, 140–153, 159; 205 pegs supplied) were read
  by the owner's agent from the pinned instructions PDF (SHA-256 b593e2f4…3c4c); nothing from the
  PDF is shipped or re-read here.
- Strip letters on the assembly page are the kit's section column letters (kit labels), as on the
  section pages' "kit section" note.
- "2a" names the left part of frame 2 in kit order and "2b" the right part.

## Clarifications

### Session 2026-11-22 (autonomous)

- Q: Where does the assembly page go in a sheet set? → A: Last, after the section pages
  (auto-resolved: the kit's instructions join strips and frames, pp. 134–139, after the section
  pages; placing it last also keeps every existing page number of A–C sheets, FR-009).
- Q: Does a `--sections` subset still get the assembly page? → A: Yes, one assembly page for any
  set (auto-resolved: the page is about the whole board; edge case above).
- Q: What does the CLI's "Wrote … pages (…)" line say? → A: It adds "1 assembly" to the page kinds
  (auto-resolved: follows the existing per-kind count pattern in `cli/sheets.py`).
- Q: Which keys does `metadata.arrangement` gain for D and E? → A: `strips` (strip order as hung,
  e.g. "EFGHABCD"), `groups` (e.g. ["2b", "3", "1", "2a"]), `in_instructions: false`, and a
  `source` block with pages 134–140 and its own citation; `frame_order` is the frame number of each
  group ([2, 3, 1, 2]). A–C records keep exactly their 007 keys (auto-resolved: FR-006 and the
  "A–C unchanged" constraint; the owner approved the format change).
- Q: Does the data file's format version change? → A: Yes, `format_version` "2" (the strip/part
  model); the loader reads only "2" (auto-resolved: the file is package data read only by this
  package; owner approved the format change).
- Q: Which centre texts do D and E use? → A: D "the Pacific (date line)", E "Asia-Pacific (146° E)"
  (auto-resolved: design brief labels; they read as "… in the centre").
- Q: Do 009 tests that pin the ENSO default to B change? → A: Yes, they pin D now; a B build is
  still tested via `--arrangement B` (auto-resolved: FR-012, owner request).
- Q: Which map supplies the about page's five combination thumbnails? → A: The first map, as today,
  now for A–E (auto-resolved: existing about.html pattern).
- Q: Does any recipe other than the ENSO maps change its default? → A: No (auto-resolved: design
  brief, item 4; out of scope).

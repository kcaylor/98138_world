# Feature Specification: Map Arrangements

**Feature Branch**: `007-map-arrangements`

**Created**: 2026-11-22

**Status**: Implemented (design decisions 1–6 made by the coordinating agent for the owner; logged
in `run-state.md` for owner review)

**Input**: Owner: "The kit explains how you can shift the order of the map pixels to have the map
centered differently (this one is centered on prime meridian, but there are two other options).
Make sure you can render any map in any of the three options (requires knowing how the panels come
together)." Facts and design decisions relayed by the coordinating agent on 2026-11-22 (see
`run-state.md`).

## Context

The kit 31203 board is three physical frames hung side by side. The building instructions
(LEGO 31203 building instructions, pp. 7–8) show "1 world – 3 combinations":

| Combination | Frame order (left to right) | Centre | Name |
|---|---|---|---|
| A | 1 · 2 · 3 | Europe and Africa (default; today's grid) | `europe-africa` |
| B | 3 · 1 · 2 | America | `americas` |
| C | 2 · 3 · 1 | Asia and Australia | `asia-australia` |

Frame 1 "America" holds kit columns 0–31 (sections A–B), frame 2 "Europe & Africa" columns 32–95
(C–F), frame 3 "Asia & Australia" columns 96–127 (G–H); every frame has all 80 rows. The kit ships
connector pins to join the frames in any order.

The grid spans exactly 360° of longitude (128 × 2.8125°, left edge 168.9° W;
`data/kit_31203_projection.json`), so each combination is a cyclic column shift by whole frames and
its new seam is geographically continuous:

- B: display column = (kit column + 32) mod 128
- C: display column = (kit column − 32) mod 128 (that is, + 96)

In the official design the wrap seam (kit columns 127 | 0) has one land stud at column 127 (row
13), and column 0 beside it is Bright Yellowish Green, so the physical kit re-hung as B or C has no
land shadow there. That is faithful for the official design.

Terms: **kit coordinates** are the columns of arrangement A (the kit mask, the official design and
the projection are defined in them). **Display coordinates** are columns as hung in the chosen
arrangement. Layout positions always use display coordinates.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build any recipe in any arrangement (Priority: P1)

A maker builds a map from a recipe with `map build <recipe> --arrangement B -o layout.json` and
gets a layout, preview and report for the board hung as Combination B, with the land shadow and
coastal halo correct at the new seam and nothing wrapping across the outer edges.

**Why this priority**: it is the owner's request: render any map in any of the three options.

**Independent Test**: build `official-31203` in A, B and C; each equals the official design
shifted by the arrangement's column shift, cell for cell. Build a recipe with a shadow in B and
check that shadow cells sit east of land in display coordinates and that none sits in display
column 0.

**Acceptance Scenarios**:

1. **Given** the `official-31203` recipe, **When** it is built with `--arrangement B` (or `C`),
   **Then** every position (x, y) has the official design's color at kit column (x − shift) mod 128,
   and the layout passes `validate`.
2. **Given** a recipe with the land shadow enabled, **When** it is built in B, **Then** the shadow
   cells are exactly the ocean cells whose western neighbour in display coordinates is land, no
   cell in display column 0 is shadow, and the count differs from A only at the old and new seams.
3. **Given** a data recipe with a global classification (bins, quantile, rank, rank-to-supply),
   **When** it is built in A, B and C, **Then** each land layer's color counts are equal in all
   three, and per-cell classes equal A's shifted except where a neighbourhood operation (shadow,
   halo, mix) acts or where the shadow changes the ocean layer's cells.
4. **Given** `--arrangement americas` or `--arrangement b`, **When** the build runs, **Then** it is
   the same as `--arrangement B`; an unknown value fails with exit 2 listing the valid values.
5. **Given** any build, **When** it writes the layout, **Then** `metadata.arrangement` records the
   id, name, frame order, column shift and the instructions citation, and the human output names
   the combination.

---

### User Story 2 - Re-hang an existing layout (Priority: P2)

A maker with a layout (from a recipe, from an image, or the official design) runs
`layout arrange LAYOUT --arrangement C -o OUT.json` and gets the same pieces moved frame by frame,
exactly as when moving the physical frames.

**Why this priority**: layouts made before this feature, and image layouts, need the same option
without a rebuild.

**Independent Test**: arrange a layout to B, then back to A; the positions are byte-for-byte the
original positions.

**Acceptance Scenarios**:

1. **Given** a layout in A, **When** it is arranged to B, **Then** each position moves from x to
   (x + 32) mod 128 with all other fields unchanged, and `metadata.arrangement` is B.
2. **Given** a layout already in B, **When** it is arranged to C, **Then** each position moves by
   the difference of the two shifts (−64 mod 128), so the result equals arranging the A layout to C.
3. **Given** a layout without `metadata.arrangement`, **When** it is read, **Then** it is treated
   as A.
4. **Given** the arranged layout, **When** it is arranged back to A, **Then** its `positions` array
   is identical to the original's (row-major order, same fields).
5. **Given** a layout whose width is not 128 or whose positions fall outside the grid, **When** it
   is arranged, **Then** the command fails with exit 1 and a clear message.

---

### User Story 3 - Validate under the layout's arrangement (Priority: P2)

`validate` checks that every position's part (plate on land, tile on ocean) matches the kit's
land/sea mask shifted by the layout's arrangement, as well as the color and quantity checks it
already makes.

**Independent Test**: a B layout validates; the same positions labelled A (arrangement field
removed) fail the mask check.

**Acceptance Scenarios**:

1. **Given** a layout built or arranged in B, **When** validated, **Then** the mask check passes
   and the output names the arrangement.
2. **Given** a layout whose parts do not match the mask under its stated arrangement, **When**
   validated, **Then** the report lists a `mask_mismatch` violation with the number of positions
   and the layout is not buildable.

---

### User Story 4 - Preview, build sheets and counts follow the arrangement (Priority: P3)

Preview PNGs, build sheets and section counts show the board as hung. Sections are labelled A–H ×
1–5 by display position; the overview draws the frame boundaries where they fall in this
arrangement, names each frame and states the combination; each section page says which physical
frame it belongs to and which kit section it is in the instructions.

**Independent Test**: build sheets for a B layout; the overview has frame lines after columns 32
and 64, frame labels "3 Asia & Australia", "1 America", "2 Europe & Africa" in that order, and the
text "Combination B"; section page A1 says frame 3 and kit section G1.

**Acceptance Scenarios**:

1. **Given** a B layout, **When** `sheets build` runs, **Then** frame lines are drawn at display
   columns 32 and 64 (C: 64 and 96; A: 32 and 96 as before), each frame is named, and the
   combination is stated on the overview.
2. **Given** a B layout, **When** `sheets counts` runs, **Then** each section entry carries its
   display label, its physical frame and its kit section label, and per-lot totals equal the parts
   list.
3. **Given** a layout in any arrangement, **When** a parts list is made, **Then** the lots and
   quantities equal those of the same map in A, and the JSON's layout block records the arrangement
   with the note that arrangements use the same pieces.
4. **Given** an A layout, **When** sheets are built, **Then** they are unchanged apart from the
   added frame names and combination line.

### Edge Cases

- `--arrangement A` on `map build` gives the same positions as before this feature.
- `layout arrange` to the arrangement the layout already has: positions unchanged (identity).
- A layout with an unknown `metadata.arrangement.id`: commands that read it fail with exit 1.
- CSV layouts carry no metadata; `layout arrange` reads and writes JSON only.
- Partial layouts (fewer than 10,240 positions) can be arranged; positions keep their fields.
- Recipes with categorical data on the kit grid (the official design) are shifted exactly.
- The `mix` texture's smoothing no longer wraps across the outer left/right edges in any
  arrangement (no bundled recipe uses a multi-color mix).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The three arrangements MUST be packaged reference data
  (`data/kit_31203_arrangements.json`) citing LEGO 31203 building instructions, pp. 7–8 (same
  pinned PDF URL and SHA-256 as `kit_31203_design.json`): id, name, centre, frame order, column
  shift; and the three frames: number, name, kit column range, section columns.
- **FR-002**: The column shift of each arrangement MUST follow from its frame order and the frame
  widths (checked when the data loads): A 0, B +32, C −32 (= +96).
- **FR-003**: `--arrangement` MUST accept `A`, `B`, `C` (any case) or the names `europe-africa`,
  `americas`, `asia-australia` (any case); default A. It is available on `map build`, `map check`
  and `layout arrange` (required there).
- **FR-004**: `map build --arrangement X` MUST compute per-cell values (reprojected data and
  classification) in kit coordinates, as for A, and place them in display coordinates. Ties in
  classification are broken in kit row-major order, so results do not depend on the arrangement.
- **FR-005**: The `blend` texture MUST also run in kit coordinates (it acts in value space; its
  random draws follow kit row-major order), so a land layer's blended classes are identical in all
  arrangements.
- **FR-006**: Every spatial neighbourhood operation (land shadow, halo distance, halo Poisson-disk
  fade, `mix` smoothing) MUST run on the grid as hung (display coordinates) with no wrap at the
  outer left/right edges.
- **FR-007**: The `official-31203` recipe built in any arrangement MUST equal the official design
  shifted by that arrangement, all 10,240 cells.
- **FR-008**: Agreement with the official design (`--compare-official`) MUST compare against the
  official design shifted to the build's arrangement.
- **FR-009**: Layouts MUST record `metadata.arrangement` = {id, name, centre, frame_order,
  column_shift, source {title, url, sha256, pages}}; schema stays 2.0; a layout without the field
  is A. `map build` and `layout arrange` always write it; image layouts (`layout IMAGE`) leave it
  out (A).
- **FR-010**: `layout arrange LAYOUT --arrangement X -o OUT` MUST move each position from x to
  (x + shift(X) − shift(current)) mod 128, keep every other field and the rest of the metadata
  (including `metadata.map`), write positions in row-major order, and never recompute colors.
- **FR-011**: The existing `layout IMAGE -o OUT` usage MUST keep working unchanged.
- **FR-012**: `validate` MUST check each position's part type against the kit land/sea mask in the
  layout's arrangement and report mismatches as a `mask_mismatch` violation; the human output and
  the JSON report name the arrangement.
- **FR-013**: Preview PNGs MUST draw positions at their display coordinates (no change needed
  beyond positions being in display coordinates).
- **FR-014**: Build sheets MUST label sections A–H × 1–5 by display position; draw frame boundary
  lines where they fall in the arrangement; name each frame (1 America, 2 Europe & Africa,
  3 Asia & Australia) over its columns on the overview; state the combination on the overview; and
  on each section page state its physical frame and kit section label (the section's label in the
  instructions). The section-page locator draws the same frame lines.
- **FR-015**: `sheets counts` JSON MUST carry the arrangement id and, per section, the physical
  frame and the kit section label; the format version is bumped only if a field changes meaning
  (added fields: version stays "1").
- **FR-016**: Parts lists MUST be unaffected in lots and quantities; the parts-list JSON layout
  block records the arrangement id and states that every arrangement uses the same pieces.
- **FR-017**: All new user-facing output (CLI text, sheets, data file) MUST carry "Not affiliated
  with or endorsed by The LEGO Group."
- **FR-018**: Documentation: README, `docs/vision.md` roadmap row 007, `docs/runbook.md`
  "Arrangements" step, `scripts/demo.sh` builds one recipe in B and C plus sheets for one.

### Key Entities

- **Frame**: number (1–3), name, kit column range, section columns.
- **Arrangement**: id (A/B/C), name, centre, frame order, column shift; derived: display frame
  spans and frame boundaries.
- **Layout arrangement record**: `metadata.arrangement` in a layout.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `official-31203` in B and C equals the shifted official design in 10,240/10,240 cells.
- **SC-002**: arrange A→B→A and A→C→A give `positions` identical to the original (JSON-equal and
  byte-equal when serialized).
- **SC-003**: `land-elevation` land color counts are equal in A, B and C; `ocean-sst` and
  `land-elevation` layouts validate (mask check passes) in all three.
- **SC-004**: shadow cells in every arrangement are exactly the ocean cells east of land in display
  coordinates; none in display column 0.
- **SC-005**: all 879 earlier tests still pass; new tests run offline.

## Clarifications

### Session 2026-11-22

- Q: How are display and kit coordinates related? → A: display x = (kit x + shift) mod 128 with A 0,
  B +32, C −32; verified against the frame orders (B: display 0–31 = frame 3 = kit 96–127; C:
  display 0–63 = frame 2 = kit 32–95). (auto-resolved: instructions pp. 7–8 as relayed, projection
  data)
- Q: Is `blend` a neighbourhood operation? → A: No: it moves a cell by its value's distance to a
  class boundary, with random draws per cell; it runs in kit coordinates so land layers are
  identical across arrangements and counts of rank methods never change (FR-005). The brief listed
  it among neighbourhood operations; logged for owner review. (agent decision: code in
  `maps/texture.py`)
- Q: Does `mix` keep its column wrap in A? → A: No; no wrap at the outer edges in any arrangement
  (the brief's rule). No bundled recipe uses a multi-color mix, so no bundled output changes.
  (agent decision)
- Q: How is the official design compared in B/C? → A: Shifted to the same arrangement (FR-008).
  (auto-resolved: an arrangement is a frame move)
- Q: Where do the arrangements live? → A: New cited package data file (constitution I: template
  reference data is versioned package data citing its source). (auto-resolved)
- Q: What does `validate` do with the mask today? → A: Nothing; 007 adds a mask check (FR-012) as
  the brief asks. (auto-resolved: `layout/validator.py`)
- Q: How does `layout arrange` fit the existing `layout IMAGE` command? → A: `layout` becomes a
  group whose unknown first argument falls through to the image command, so `layout IMAGE -o OUT`
  keeps working (FR-011). (agent decision: keeps the CLI backward compatible)
- Q: Position order after arrange? → A: Row-major in display coordinates (as `map build` writes),
  so A→X→A is byte-identical for every tool-written layout. (agent decision)
- Q: Section build order on sheets in B/C? → A: Column by column in display order (A1…H5 as hung);
  each page also names its kit section, so a maker can find it in the instructions. (agent decision)

## Assumptions

- The instructions' pages 7–8 were read by the coordinating agent; this feature does not ship or
  draw anything from the PDF.
- Arrangements only move whole frames; the kit's mask, parts and counts are unchanged.

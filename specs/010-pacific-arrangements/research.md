# Research: Pacific-centred Arrangements D and E (010)

Facts from the PDF are those recorded in `design.md` (read by the owner's agent from the pinned
building instructions, SHA-256 b593e2f4…3c4c); nothing from the PDF is shipped or re-read.

## R1. Model: strip order + frame groups

- Decision: each arrangement lists `strips` (kit strip letters left to right as hung) and `groups`
  (frame or frame-part labels left to right, "2a" = left part of frame 2 in kit order). `frame_order`
  stays as the frame number of each group (A–C unchanged; D/E `[2, 3, 1, 2]`); `column_shift` stays
  and is validated as 16 × position of strip A.
- Rationale: expresses split frames, keeps every A–C field and therefore their layout records
  identical; the groups are derivable from the strip order, so the loader cross-checks them.
- Alternatives: strip order only (groups derived): loses the human-readable labels in the data file;
  a list of `(frame, part)` objects: more verbose with no extra information.

## R2. Layout record for D/E

- Decision: A–C records unchanged (007 keys). D/E add `strips`, `groups`, `in_instructions: false`,
  and `source` = the joints source (pp. 134–140) instead of pp. 7–8.
- Rationale: FR-006; old A–C layouts stay byte-identical; readers only look at `id`.

## R3. Joints and the unpeg step

- A board's 7 strip joints as hung are the pairs of neighbouring strips. A joint is "kept" when
  both strips are in the same group (already pegged when the frames were built, p. 137), "make"
  otherwise (p. 139, 15 pegs). The "unpeg" joints are the kit frames' internal joints (A|B, C|D,
  D|E, E|F, G|H) that are not kept: D → D|E, E → C|D; none for A–C.
- Peg budget: 7 × 15 + 8 × 4 × 3 = 201 for every combination; supply 205 is the inventory quantity of
  design 61332 in `kit_31203_inventory.json` (p. 159), read at run time rather than copied.

## R4. Assembly page placement and content

- Decision: last page of every set (after the section pages), kind `assembly`. Drawn with rects,
  lines and text only: step 1 frame 2 as built with the cut joint (D/E only), step 2 the 8 strips as
  hung with group brackets, kept joints thin, joints to make dashed and labelled "15x", then
  numbered text steps from `assembly_steps()` and the citation/status line.
- Rationale: kit order (sections pp. 9–133, joints pp. 134–139, border pp. 140–153); keeps A–C page
  numbers of all existing pages.

## R5. Web

- `COMBINATIONS = A–E`; the prebuild writes per-arrangement `strips`, `groups`, `in_instructions`,
  `citation`, `assembly` (steps) and `note` (why possible) into the manifest; templates render them.
  The catalog requires exactly the five. Image size scales from ~110 MB / 18 variants to an
  estimated ~185 MB / 30 (re-measured if a full prebuild is run).

## R6. ENSO in D

- Measured in implementation with the real ERSST cache (results in run-state.md and recipe
  comments): extra tiles beyond one kit and shadow cells for D (design: shadow 387 or 391 vs 390).

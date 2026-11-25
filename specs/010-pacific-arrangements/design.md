# Design brief: Pacific-centred arrangements D and E (feature 010)

Owner decisions (2026-11-22, in conversation): add two new frame combinations, **D** and **E**,
beyond the three in the LEGO 31203 building instructions; add instructions for assembling D and E
"following the examples given for A, B and C"; ship them in the CLI, the build sheets and the web
site (98138.world), merged into main and deployed. Not affiliated with or endorsed by The LEGO Group.

## Research (read from the pinned instructions PDF, SHA-256 b593e2f4…3c4c; nothing from it is shipped)

- The mosaic is 40 section bases (BRICK 4/3 16X16 W/ 4.85 HOLE, design 65803, inventory p. 159),
  pegged into vertical strips of five (3 connector pegs 61332 per joint, pp. 134-136), and strips
  pegged side by side into frames (p. 137).
- p. 138: the three frames 1 (America, kit section columns A-B), 2 (Europe & Africa, C-F), 3 (Asia
  & Australia, G-H). p. 139: combinations A = 1·2·3, B = 3·1·2, C = 2·3·1, each frame joint drawn as
  a dotted line with "15x" connector pegs.
- A joint inside a frame (strip to strip, p. 137) uses the same 15 connector pegs as a joint
  between frames (p. 139). A frame is a group of strips that were pegged first; it can be unpegged
  between any two strips with no other parts.
- The white border (pp. 140-153) is built once around the finished 8 × 5 board, the same for any
  strip order. Peg budget: 7 strip joints × 15 + 8 strips × 4 × 3 = 201 of the 205 supplied, for
  any order.
- Therefore any cyclic rotation of the 8 strips by whole strips (multiples of 16 kit columns) is
  buildable from one kit with no extra parts. A, B and C are rotations by 0, +32 and -32 columns.

## Geography (kit_31203_projection.json: left edge 168.9° W, 2.8125° per column; 180° = kit col 124.05)

| id | shift | strips as hung | frames as hung | centre lon (display col 64) | date line vs centre | outer edge | land rows cut at edges |
|---|---|---|---|---|---|---|---|
| A | 0 | ABCDEFGH | 1·2·3 | 11.1° E | +60 cols | 168.9° W | 0 |
| B | 32 | GHABCDEF | 3·1·2 | 78.9° W | -36 | 101.1° E | 36 |
| C | 96 | CDEFGHAB | 2·3·1 | 101.1° E | +28 | 78.9° W | 17 |
| **D** | **64** | **EFGHABCD** | **2b·3·1·2a** (frame 2 split between strips D and E) | **168.9° W** | **-4 (date line centred)** | **11.1° E** (Europe, Africa) | **27** |
| **E** | **80** | **DEFGHABC** | **2b·3·1·2a** (frame 2 split between strips C and D) | **146.1° E** | **+12** | **33.9° W** (Atlantic) | **8** |

- D: "Pacific (date line)". The date line is 4 columns (11°) left of centre; the Pacific basin
  (120° E-80° W) spans display columns 39-96. Cost: the board's edges cut Europe and Africa at 11° E.
- E: "Asia-Pacific (146° E)", the usual Asia-Pacific world map; edges in the mid-Atlantic, so only
  Greenland and Antarctica are cut; the Pacific is whole but right of centre.
- A date-line-exact roll (68 columns) is not strip-aligned and could not re-hang a built board:
  rejected.
- Arrangement-independent pipeline already holds: build_map with column_shift 64 or 80 works
  unchanged (previews checked); the land shadow moves only at the seams (387 / 391 cells vs 390 in B).

## What to build

1. Reference data: D and E in `cli/src/lego_image_processor/data/kit_31203_arrangements.json`. The
   current model (`frame_order` + `column_shift`, validated against frame 1's start) cannot express
   a split frame; generalise it (for example a strip order or frame parts such as 2a/2b) while
   keeping A, B, C byte-for-byte equivalent in behaviour. D and E MUST be marked as not among the
   instructions' combinations and cite pp. 134-139 (joints) and 140 (border) for why they are
   possible; A-C keep their pp. 7-8 citation.
2. CLI: `--arrangement D|E` (and names, e.g. `pacific`, `asia-pacific`) everywhere A-C work: `map
   build`, `map check`, `layout arrange`, recipe key `arrangement`, sheets, counts, validate.
3. Assembly instructions for D and E following the instructions' p. 139 example: the build-sheet
   PDF/SVG for a layout hung D or E gets a page (or overview block) showing the strip groups as
   hung, which frame-2 joint to unpeg (its 15 connector pegs), the joints to make (15 pegs each), and
   that the border goes round the whole board as in pp. 140-153. A, B, C get the same style of block
   for consistency. The runbook documents the steps in text.
4. ENSO recipes `ocean-el-nino` and `ocean-la-nina` default to `arrangement = "D"` (owner asked for
   date-line-centred ENSO maps). Re-check their extra-tile counts in D and update docs/spec 009 notes.
5. Web (98138.world, `web/`): COMBINATIONS A-E (6 maps × 5 = 30 variants); the map page's combination
   nav, about page ("ways to hang the frames") and figure captions describe D and E honestly
   (unofficial, why possible, how to assemble); the catalog/manifest validation accepts five. Keep
   the runtime free of CLI imports. Update deploy docs (variant counts, image size).
6. Tests offline, test-first; existing A-C outputs unchanged.
7. Merge to main and deploy with `fly deploy` (docs/deploy.md) — done by the coordinating agent.

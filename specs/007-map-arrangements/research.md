# Research: Map Arrangements (007)

Not affiliated with or endorsed by The LEGO Group.

## R1. Frames and combinations (source)

LEGO 31203 building instructions, pp. 7–8 (the PDF pinned in `kit_31203_design.json`: URL
`https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6372756.pdf`, SHA-256
`b593e2f4…3c4c`), read by the coordinating agent: "1 world – 3 combinations". Frame 1 America
(kit columns 0–31, sections A–B), frame 2 Europe & Africa (32–95, C–F), frame 3 Asia & Australia
(96–127, G–H). Combination A = 1·2·3, B = 3·1·2, C = 2·3·1; connector pins allow any order.
Feature 006 already records the frame split (`sheets/sections.py`, `FRAME_BOUNDARIES = (32, 96)`).

**Decision**: store as `data/kit_31203_arrangements.json` with this citation; derive the shift from
the frame order (the start column of frame 1 in display order). Nothing from the PDF is shipped.

## R2. Shifts

B: display 0–31 = frame 3 (kit 96–127), 32–63 = frame 1 (kit 0–31), 64–127 = frame 2 (kit 32–95);
display = (kit + 32) mod 128. C: display 0–63 = frame 2 (kit 32–95), 64–95 = frame 3, 96–127 =
frame 1; display = (kit − 32) mod 128. With NumPy, `np.roll(a, shift, axis=1)` maps kit to display.
Frame boundaries as hung: A {32, 96}, B {32, 64}, C {64, 96}.

## R3. The seam is continuous

`kit_31203_projection.json`: 128 × 2.8125° = 360°, left edge 168.9° W, so kit column 127's east
edge is kit column 0's west edge. Moving frames therefore gives a geographically continuous map;
the old outer edges (kit 127 | 0) become an interior seam in B and C, and a new pair of outer edges
appears (B: kit 95 | 96; C: kit 31 | 32).

## R4. Which operations depend on position

| Step | Depends on | Runs in |
|---|---|---|
| reprojection (cell mean, nearest fill) | kit cell | kit coordinates (nearest fill may cross the seam; it is per cell and identical to A) |
| classification (bins, quantile, rank, rank-to-supply, categorical) | values; ties by row-major order | kit coordinates (mask mapped back) |
| blend | value distance to class boundary, one random draw per layer cell (row-major) | kit coordinates |
| land shadow | western neighbour | display |
| halo (distance to land, Poisson-disk fade) | neighbourhood | display |
| mix (Gaussian-smoothed noise) | neighbourhood | display, no wrap |

Running blend in kit coordinates keeps land layers identical in every arrangement; the ocean
layer's cell set changes only where the shadow moves.

## R5. CLI shape for `layout arrange`

`layout` is a Click command taking an image. A Click group whose `resolve_command` falls back to
the image command when the first argument is not a sub-command name keeps `layout IMAGE -o OUT`
working and adds `layout arrange`. Alternative rejected: a new top-level command (`arrange`),
because the brief names `layout arrange`.

## R6. Sheets

Sections are labelled by display position. A display section column c holds kit section column
(c − shift/16) mod 8; its frame and instructions page come from that kit column. Frame lines on the
overview and locator come from the arrangement's boundaries.

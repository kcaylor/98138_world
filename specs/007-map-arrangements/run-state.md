# Run state: 007 map arrangements

Source: prompt (owner request relayed with verified facts and design decisions 1–6 by the
coordinating agent, 2026-11-22). Fallback 2B without a question round: the brief settled outcome,
scope, constraints and priority; the decisions are logged below for owner review.
Phase: done
Status: done (committed locally on 007-map-arrangements; awaiting owner review)
Updated: 2026-11-22

## Open questions

(none blocking; see "For owner review")

## Decisions
- specify: branch `007-map-arrangements` created with `git checkout -b` from main bfd11d9 (agent)
- owner-brief decisions (made by the coordinating agent for the owner; FOR OWNER REVIEW):
  1. `--arrangement A|B|C` or `europe-africa|americas|asia-australia`, case-insensitive, default A,
     on `map build` and `map check`
  2. `layout arrange LAYOUT --arrangement X -o OUT`: a pure frame move, no recomputation
  3. `metadata.arrangement` {id, name, centre, frame_order, column_shift, source}; positions in
     display coordinates; schema stays 2.0; absent = A; `validate` checks the mask under it
  4. per-cell values as in A, shifted; neighbourhood operations on the grid as hung, no outer wrap
  5. preview, sheets and counts follow the arrangement; parts lists unaffected
  6. disclaimer on all user-facing output
- clarify: 9 items auto-resolved or decided (spec Clarifications) (auto-resolved / agent)
- clarify: `blend` runs in kit coordinates, not as hung: it is a value-space operation, and this
  keeps land layers identical in every arrangement and the counts of global classifications equal.
  The brief listed blend among neighbourhood operations. CLOSE CALL, FOR OWNER REVIEW (agent)
- clarify: `mix` smoothing loses its column wrap in every arrangement, A included (brief: no wrap
  at outer edges). No bundled recipe uses a multi-color mix (agent)
- clarify: `layout` becomes a Click group whose unknown first argument falls through to the image
  command, so `layout IMAGE -o OUT` is unchanged (agent)
- clarify: arrangements stored as new cited package data `data/kit_31203_arrangements.json`
  (constitution I) (agent)
- clarify: `validate` gains a `mask_mismatch` violation (it had no mask check before) (agent)
- plan: no new dependencies; no constitution violations (agent)
- tasks: 22 tasks (Setup 1, Foundational 5, US1 4, US2 4, US3 2, US4 2, Polish 4) (agent)
- analyze: inline; every FR maps to a task; 0 CRITICAL, 0 HIGH (agent)

- implement: `--arrangement` also has the short flag `-a` (agent)
- implement: `map build` always writes `metadata.arrangement` (A included); image layouts leave it
  out (= A) (agent)
- implement: section counts JSON gains top-level `arrangement` and per-section `kit_label`; format
  version stays "1" (additive); the 006 key-order test was updated for the two keys (agent)
- implement: parts-list JSON layout block gains `arrangement` {id, name, note}; the human parts
  output prints an arrangement line only for B/C, so A output is unchanged (agent)
- implement: sheets in B/C: build order is column by column as hung; section pages say "frame N of
  3 (name) · kit section XY"; overview adds frame labels under the map and a "Combination X" line
  (PDF text uses "pp. 7-8", Latin-1) (agent)
- implement: `validate` reports `mask_mismatch` (positions, first 10 examples) and counts them
  against buildability (agent)
- converge: one pass over FR-001-FR-018 and SC-001-SC-005; nothing further (agent)

## Results (real data, session scratchpad `e2e007/`)
- tests: 965 passed (879 before), offline
- A builds of land-elevation, ocean-sst, official-31203 are position-identical to main (bfd11d9)
- shadow cells: A 392, B 390 (gains kit (13,0) at the old seam, loses kit col 96 rows 36-38 at the
  new outer edge), C 389 (gains (13,0), loses kit col 32 rows 7, 26, 31, 37)
- land color counts identical in A/B/C (land-elevation); ocean-sst all color counts identical;
  land-elevation ocean differs only by shadow/halo seam effects
- official-31203 in B/C = shifted official design; `layout arrange` of the A layout = the B/C builds;
  A->B->A and A->C->A positions byte-identical
- validate: mask check passes for all 11 layouts; official and ocean-sst 100% buildable in all
  arrangements; land-elevation 38.2% in all (beyond-kit plate colors, as before)

## Blocked tasks

## Deferred findings

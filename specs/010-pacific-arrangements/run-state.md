# Run state: Pacific-centred arrangements D and E (010)

Source: specs/010-pacific-arrangements/design.md (owner decisions 2026-11-22; path 2A, spec outside Spec Kit)
Phase: done (specify, clarify, plan, tasks, analyze, implement, converge)
Status: done (not committed; the coordinating agent commits, merges and deploys)
Branch: 010-pacific-arrangements (worktree /Users/kellycaylor/dev/98138_world-009)
Updated: 2026-11-22

## Open questions
(none)

## Decisions
- owner (via coordinator): D, E, their assembly instructions, ENSO default D, web; changes to the
  arrangements data format, --arrangement values, recipe values and web manifest approved (user)
- specify: design.md converted to spec.md; every design item mapped to FR-001-FR-018 (agent)
- clarify: 9 questions auto-resolved (spec Clarifications); none escalated (agent)
- data: kit_31203_arrangements.json format 2 adds per-combination `strips`, `groups`,
  `in_instructions`, a `joints_source` (pp. 134-140) and `assembly` facts; the 205 connector pegs
  are read from kit_31203_inventory.json (design 61332, p. 159), not copied (agent)
- names/centres: D `pacific` "the Pacific (date line)", E `asia-pacific` "Asia-Pacific (146° E)" (agent)
- frame parts: 2a = left part of frame 2 in kit order, 2b = right part (D: 2a C-D, 2b E-F; E: 2a C,
  2b D-F) (agent, from design.md)
- layout record: A-C unchanged byte for byte; D/E add strips, groups, in_instructions=false, and
  cite pp. 134-140 (agent)
- sheets: assembly page is the LAST page of every set (also for --sections subsets), kind
  `assembly`; A-C get the same page citing pp. 7-8 and 139 (agent; follows the kit's order)
- sheets CLI line now "43 pages (1 overview, 1 legend, 40 sections, 1 assembly)" (agent)
- web: map pages of all combinations get a "How to hang the frames" panel (additive); about page
  "Five ways to hang the frames"; manifest rows carry strips, groups, in_instructions, citation,
  note, assembly (steps text from the library); manifest format_version stays "1" (additive) (agent)
- ENSO: recipe description now ends "date line centred (D)." (was "Pacific-centred (B).") (agent)
- spec 009: requirements left as written; a dated feature-010 note added to spec, quickstart and
  run-state (agent)
- deploy docs: ~185 MB / ~75 s for 30 variants, scaled from the measured ~6 MB per variant
  (subset prebuild); not a full-image measurement (agent)

## Results
- Tests: CLI 1109 passed (baseline 1035); web 86 passed (baseline 77); all offline.
- Real data (ERSST cache009), tiles beyond one kit: El Niño D 1,114 (B 1,114, E 1,112); La Niña
  D 1,152 (B 1,155, E 1,158). Land shadow: D 387, E 391 (B 390).
- A-C check vs pre-change outputs: layouts identical; parts identical except the layout checksum
  (timestamp); section pages identical except "of 43"; overview differs only by the assembly sentence.

## Blocked tasks
(none)

## Deferred findings
- analyze LOW: `map check --arrangement D` had no explicit test in the first task list; folded into
  T006 (test_arrange_de_contract.py::test_map_check_d).

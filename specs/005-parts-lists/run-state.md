# Run state: 005 parts lists and ordering

Source: prompt (fallback 2B). Scoping answers taken from `docs/vision.md` and the coordinating
agent's brief of 2026-11-22 (outcome, scope, constraints, priority); no separate four-question
round was held. Planned in one session; implemented in a second session from the user's answers to Q1–Q6.
Phase: done
Status: done (committed locally on 005-parts-lists; awaiting user review)
Updated: 2026-11-22

## Open questions

(Q1–Q6 answered by the user on 2026-11-22, each with the planner's recommendation; see Decisions.)

For user review (agent decisions made during implement, details in Decisions):
1. Metallic and glow colors in the widened part-color table (cited and orderable): keep or restrict.
2. Match a cited row by LEGO color id when a layout's key differs (palette "Dark Red" 154 =
   "New Dark Red" 154): RESOLVED by the user 2026-11-22: match by LEGO ID, not name. FR-005
   updated; `PartColorTable.by_lego_id`; supply and owned parts use the cited row's key.
3. An unverified lot fully covered by owned parts does not block `parts export`.

## Decisions
- user (2026-11-22): Q1 owned parts = `--kits N` plus repeatable `--owned FILE` and `--missing FILE`
  in Rebrickable's documented import CSV (`Part,Color,Quantity` or `Element,Quantity`) (user)
- user (2026-11-22): Q2 colors without cited IDs: `parts export` exits 6 and writes nothing unless
  `--allow-partial` (user)
- user (2026-11-22): Q3 widen `part_colors.json` to every opaque color passing all five join
  rules (measured 44 plate, 40 tile) (user)
- user (2026-11-22): Q4 no disclaimer inside BrickLink XML / Rebrickable CSV; the command output
  and the parts list JSON carry it (user)
- user (2026-11-22): Q5 commands `parts list`, `parts export`, `kit part-numbers` with
  `--kits/--owned/--missing/--spares/--condition/--allow-partial` (user)
- user (2026-11-22): Q6 map pieces only (no frame or section bases) (user)
- user (2026-11-22): also fix the part-blind `KitInventory.supplied()` lookup for the parts list
  with `supplied_for(part, color)` (user, as planned in R11)
- specify: branch `005-parts-lists` created from `004-map-recipes` HEAD (22a468b) with
  `git checkout -b` (the create-new-feature script made the directory without switching) (agent)
- specify: part numbers verified from archived catalog pages (BrickLink offline: redirect to
  maintenance page; Rebrickable live pages HTTP 402): plate BrickLink 4073 (alternate 6141),
  Rebrickable 6141, LEGO 6141; tile 98138/98138, LEGO 98138/35381 (agent, research R1)
- specify: Rebrickable terms confirmed from the archived downloads page (2026-10-29): free for
  personal and commercial use with acknowledgement; closes 004 open question 1 (agent, research R5)
- clarify: 9 items auto-resolved (spec Clarifications), incl. no prices (R8), spares off by
  default with no claimed LEGO rate (R7), BrickLink XML and Rebrickable CSV formats from their help
  pages (R2, R3) (auto-resolved)
- plan: no new dependencies (stdlib csv, xml.sax.saxutils, html.parser) (agent)
- plan: new join rule 5 for part colors (color listed on BrickLink's part page); all 23 current
  rows pass; Medium Blue on 4073 fails (agent, research R1/R4)
- plan: `KitInventory.supplied_for(part, key)` because `supplied(key)` ignores the part and would
  give a Bright Green plate the 601 tile supply (agent, research R11)
- plan: speckit `update-agent-context.sh` not run, to avoid editing CLAUDE.md/AGENTS.md (agent,
  as in 004)
- tasks: 44 tasks (Setup 2, Foundational 12, US1 7, US2 5, US3 7, US4 5, Polish 6) (agent)
- analyze: run inline (no subagents, per brief); 0 CRITICAL, 0 HIGH; findings below (agent)
- implement: pinned pages copied from the planning session's working copies into the maintainer
  cache `<cache>/sources/partnumbers/` (SHA-256 equal to research R1/R5); `partnumbers build`
  downloads a page only when it is missing (never in tests) (agent)
- implement: `part_numbers.json` built by `tools/partnumbers` with six consistency rules (Rebrickable
  part = project ID; project ID is the BrickLink item or an alternate; Rebrickable's BrickLink
  cross-reference names the item; the item is in the kit inventory's part_ids; LEGO design IDs =
  part ID + kit design IDs, each in Rebrickable's LEGO list; BrickLink colors = the page's "All"
  tab). Result: plate BrickLink P 4073 (alternates 6141, 15570, 30057, 34823, 39799, 44325,
  51809, 54003, 113470; 100 colors), Rebrickable 6141, LEGO 6141; tile BrickLink P 98138
  (alternates 35380, 35381, 39797, 118864; 93 colors), Rebrickable 98138, LEGO 98138, 35381.
  `--check`: no differences (agent)
- implement: join rule 5 checks the BrickLink color *id* too (the part page's `data-color` must
  equal the color guide's id), not only the name (agent: stricter than planned, same sources)
- implement: Rebrickable terms recorded in `part_colors.json` `source.terms` after the tool finds
  the quoted text on the pinned downloads page (added as snapshot `rebrickable-terms`), plus
  `source.acknowledgement`; the loader now requires `source.terms` (agent)
- implement: T010 check: with the 004 reviewed list the rebuilt table reproduces all 23 rows
  unchanged; with every listed color (US4) 44 plate / 40 tile rows, all 23 old rows unchanged,
  `--check` no differences. New rows are ordered by Rebrickable color id after the kit rows (agent)
- implement: US4 exclusions (26 plate, 29 tile): transparent, glitter and opal colors (rule 2);
  LDraw code/name disagreements: Dark Purple 85, Yellowish Green 158, Flat Silver 179, Olive
  Green 326, and colors LDraw lacks (Glow in Dark White 1000, Pastel Blue 1051, Pearl Titanium
  1103, Vibrant Yellow 1062, Reddish Orange 1136); Chrome Antique Brass (no LEGOID); Medium Blue
  on the plate (rule 5: not on BrickLink 4073's page) (agent)
- implement: the widened table includes opaque metallic and glow colors that pass all five rules
  (e.g. Metalized Silver/Gold, Silver, Warm Gold, Phosphorescent White). NEEDS USER REVIEW: keep
  them (they are cited and orderable) or restrict recipes/exports to plain solid colors (agent)
- implement: test fixture `wrong_part_color.toml` and two tests used Earth Blue as "not a plate
  color"; Earth Blue is a cited plate color now, so they use Medium Blue (cited tile, excluded
  plate) (agent)
- implement: an unverified lot blocks `parts export` (exit 6) only while it has pieces to buy; an
  unverified lot fully covered by owned kits does not (agent: Q2 is about ordering uncited IDs)
- implement: a lot whose positions carry more than one `lego_color_code` for the same key is
  unverified ("color code mismatch") (agent)
- implement: owned/missing CSV rows that use another catalog's number for a map part (4073,
  30057, 35381, …) fail with the line number and ask for Rebrickable numbers; other parts are
  ignored and counted (agent: spec edge case)
- implement: parts list JSON adds `unverified`, `prices` and totals `lots_to_buy`, `spares`,
  `surplus` to the contract shape; contracts updated (agent)
- implement: `kit part-colors` now prints Rebrickable's terms and the acknowledgement (FR-002) (agent)
- implement: root and cli `.gitignore` ignored every `parts/` directory (Python template entry for
  buildout), which hid the new package from git and from Poetry's wheel; anchored to `/parts/`
  (agent)
- implement: palette names that differ from LDraw's LEGO names do not resolve by key even when the
  LEGO id matches (palette "Dark Red" 154 vs cited "New Dark Red" 154). Matching follows FR-005
  (key, then code). NEEDS USER REVIEW: also accept a cited row by LEGO color id when the key
  differs (would verify image layouts that use Dark Red) (agent)
- implement: 004 docs updated for the project owner's three-blue `land-elevation` ocean (run-state,
  recipe-format contract, spec US4 note, cli/README); 004 open question 1 (Rebrickable license)
  closed (T042) (agent)
- converge: assessed FR-001–FR-019, SC-001–SC-008, edge cases and quickstart against code and
  tests; one gap found and fixed (FR-002 acknowledgement in `kit part-colors`); second round added
  nothing (agent)

## Results (T043, real data in the session scratchpad)
- tests: 767 passed (666 before), offline, ~72 s
- `partnumbers build --check` and `partcolors build --check`: no differences
- official-31203: 10 verified lots, 10,240 pieces; `--kits 1`: nothing to buy, surplus 890 (= kit
  extras, White plate 2); export without kits: BrickLink XML 10 items / 10,240 pieces, Rebrickable
  CSV 10 rows
- land-elevation (three-blue ocean): 13 lots; beyond 1 kit 11 lots / 6,382 pieces (tiles Bright
  Bluish Green 3,145, Earth Blue 325; plates Dark Green 506, Bright Green 528, Bright Yellowish
  Green 515, Brick Yellow 350, Sand Yellow 231, Medium Nougat 311, Reddish Brown 158, Dark Brown
  128, Medium Stone Grey 185); beyond 2 kits 10 / 4,178; beyond 3 kits 9 / 2,912 (SC-003)
- quickstart §5 (1 kit, 1,000 loose Bright Bluish Green, 12 Medium Azur missing, spares 2%):
  Bright Bluish Green 2,145 + 43 = 2,188 to buy; total 5,495 in 11 lots (113 spares)
- image fixture layout (002): 8 lots, all verified after US4; export exit 0 (SC-005)
- XML parsed with ElementTree: no declaration, root INVENTORY, ITEMID 4073 for plates and 98138
  for tiles, COLOR = BrickLink ids from `part_colors.json`
- export of a 10,240-position layout: 0.25 s wall (SC-006)

## Blocked tasks

## Deferred findings
- [MEDIUM] SC-003 is asserted on a synthetic layout with the real counts (T031); the real-data
  figure is only checked in the quickstart run (T043), as in 004.
- [MEDIUM] Archived pages are pinned by SHA-256 of the decoded HTML; the Internet Archive could
  re-serve different bytes. The tool fails loudly and the maintainer re-pins (same policy as 004's
  OPeNDAP subset).
- [RESOLVED] `land-elevation` three-blue ocean: the project owner's change, now recorded in 004's
  run-state and docs; the shortfall is reported as beyond-kit (see Results).
- [LOW] FR-018 (no prices; pointer to marketplace pricing) has no dedicated test; covered by the
  contract text check in T020.
- [LOW] `--all-columns` in contracts/cli.md is a display option not named in the spec (implemented).
- [RESOLVED] Output-directory-missing error (exit 1) has contract tests for both commands.
- [LOW] BrickLink help page carries an "under construction" banner; the format matches the long
  documented one. Quickstart §8 (manual upload to BrickLink and Rebrickable) was not run: it needs
  the user's marketplace accounts.

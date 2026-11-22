# Run state: 005 parts lists and ordering

Source: prompt (fallback 2B). Scoping answers taken from `docs/vision.md` and the coordinating
agent's brief of 2026-11-22 (outcome, scope, constraints, priority); no separate four-question
round was held. Planning only: the brief says stop before implement.
Phase: analyze (planning complete)
Status: waiting on user (reserved decisions Q1–Q6 provisional)
Updated: 2026-11-22

## Open questions (reserved; provisional answers applied in spec, plan, contracts, tasks)
1. Q1 Owned-parts input. Options: (a) `--kits N` + repeatable `--owned FILE` / `--missing FILE`
   in Rebrickable's documented import CSV [recommended]; (b) `--kits N` only; (c) (a) plus
   BrickLink XML as an input format. Reason: covers secondhand incomplete kits and loose parts with
   a format makers can already export.
2. Q2 Unverified lots in exports. Options: (a) exit 6, write nothing, unless `--allow-partial`
   [recommended]; (b) always write verified lots with a warning; (c) refuse to list at all.
3. Q3 Widen `part_colors.json` to every opaque color passing join rules 1–5 (44 plate, 40 tile).
   Options: (a) yes [recommended]; (b) keep 14 + 9; (c) add colors only on request.
4. Q4 Disclaimer inside BrickLink XML / Rebrickable CSV. Options: (a) none in the files, printed by
   the command and in JSON [recommended, follows the user's 003 decision for layout CSV];
   (b) XML comment / extra ignored CSV column (risks import rejection; BrickLink forbids an XML
   declaration and documents no comment support).
5. Q5 CLI surface: `parts list`, `parts export` (`--bricklink`, `--rebrickable`, `--condition`,
   `--allow-partial`), shared `--kits/--owned/--missing/--spares`, `kit part-numbers`; spares off by
   default; exit code 6. Options: (a) as proposed [recommended]; (b) fold into `validate`;
   (c) single `order` command.
6. Q6 Scope: map pieces only (plates and tiles); frame, 40 section bases and other kit elements out
   of scope. Options: (a) map only [recommended: layouts describe only map positions; BrickLink
   numbers for frame parts are not verified]; (b) `--include-kit-frame` from the inventory.

## Decisions
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

## Blocked tasks

## Deferred findings
- [MEDIUM] SC-003 is asserted on a synthetic layout with the real counts (T031); the real-data
  figure is only checked in the quickstart run (T043), as in 004.
- [MEDIUM] Archived pages are pinned by SHA-256 of the decoded HTML; the Internet Archive could
  re-serve different bytes. The tool fails loudly and the maintainer re-pins (same policy as 004's
  OPeNDAP subset).
- [MEDIUM] `land-elevation` recipe (004) uses three blues at 70/20/10 for the ocean, needing 5,024
  Bright Bluish Green tiles (kit 1,879); 004's run-state describes a nine-color background. Not
  changed here; flag for the user (004 recipe look, NEEDS USER REVIEW there).
- [LOW] FR-018 (no prices; pointer to marketplace pricing) has no dedicated test; covered by the
  contract text check in T020.
- [LOW] `--all-columns` in contracts/cli.md is a display option not named in the spec.
- [LOW] Output-directory-missing error (exit 1) is in the contract but only implicitly tested.
- [LOW] BrickLink help page carries an "under construction" banner; the format matches the long
  documented one, and quickstart §8 is a manual upload check.

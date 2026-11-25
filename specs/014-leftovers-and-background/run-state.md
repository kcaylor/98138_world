# Run state: Leftovers in the box, and a light gray page background (014)

Source: owner-approved changes relayed by the coordinating session (2026-11-22). Path 2B with the
scoping questions already answered by the owner, so none were asked.
Phase: done (implement + converge)
Status: done
Branch: 014-leftovers-and-background (from origin/main at f5b9f4c)
Updated: 2026-11-22

## Open questions (owner review; work proceeded with the choice below)
1. Palette chooser (`palette.js`) is not on main (branch `012-palette-chooser` is unmerged); its
   canvas will need the same `--stud-mat` surround when it lands.
2. White (#ffffff) against #e9e9e9 is 1.21:1. That's enough to see the edges of a White area, but
   below the 3:1 WCAG non-text guideline. Every gray in the owner's range is ~1.2:1.
3. Dark mode keeps the dark page; the stud mat is the same light gray there too.

## Decisions
- clarify: "in the box" excludes loose parts (`--owned`), subtracts `--missing` (agent: matches
  `kit_supply`).
- clarify: per-part supply (a Bright Green plate uses no Bright Green tiles; 005 R11) (auto).
- clarify: no leftover table in text output when kits = 0; JSON always lists the ten rows (agent).
- plan: spec/plan/tasks written directly rather than by separate phase subagents (agent: small
  feature, decisions pre-made).
- implement: gray #e9e9e9 (darkest in the owner's range, best White-stud separation; muted text
  4.88:1, AA).

## Blocked tasks
None.

## Deferred findings
None.

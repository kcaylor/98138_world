# Run state: 015-palette-chooser

Source: prompt (owner request relayed by the coordinating agent, 2026-11-22, with owner decisions on JS, scope and disclaimer)
Phase: done
Status: done
Updated: 2026-11-22

## Open questions (for the owner)
1. Sea-ice rule: ERSST v5 1991–2020 warmest-month SST ≤ −1.5 °C, or no value poleward of 60° (796 cells), chosen to avoid a new dataset. The unmerged `013-rainfall` branch pins an NSIDC sea-ice climatology (759 cells); replace this rule with it when 013 merges? (recommended: yes)
2. Cells with no source value under ice (e.g. 206 Arctic cells in `ocean-sst`) show the nearest value in "show the map's data", as the build does, and the panel states the counts. Alternative: show them White even in that mode. (recommended: keep, it matches the build)
3. Feature number: resolved 2026-11-22, renumbered 012 → 015 at merge (012 and 013 went to living planet and rainfall, 014 to leftovers and the gray background).
4. Ice toggle default is "show the map's data" (equal to the built preview); the brief's "stay White as now" does not match the current maps, none of which paint ice White.

## Decisions
- specify: no spec existed; drafted from the relayed brief, whose owner decisions replace the four scoping questions (agent: the brief answered outcome, scope, constraints and priority)
- clarify: editable per recipe role/method (research R3) (agent)
- clarify: default = built classes; custom bins only after a class/bound change, no blend texture (agent)
- clarify: ice regions packaged as `kit_31203_ice.json` with a maintainer `--check` tool; land ice = 013's regions (agent, CLOSE CALL for the sea-ice rule)
- clarify: state in the URL fragment; no cookies, no storage (agent)
- plan: `map cells` CLI command added (agent: brief asked for a CLI command; additive, no existing flag or format changed)
- plan: `reduce="monthly-max"` added to the netCDF-3 reader (agent: additive)
- implement: static asset version now hashes the static files too (agent: script updates bust caches)
- implement: cells.json is not a download kind and is not listed on the page (agent: preview aid only)

## Blocked tasks
- none

## Deferred findings
- No automated test runs `kit31203 ice-mask --check` (it needs the real cached ERSST file); run by hand: "no differences".
- AGENTS.md lags CLAUDE.md for features 009 and 011 (pre-existing); only the 015 paragraph and the JS wording were added.
- ENSO maps' `cells.json` not checked against real data here (their datasets are not cached on this machine); covered by fixture tests.

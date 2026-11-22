# Run state: 003 kit reference data

Source: prompt (fallback 2B) + user answers to 4 scoping questions, 2026-11-21
Phase: done
Status: done
Updated: 2026-11-21 (implement: phases 1-7 done, T001-T075; converge: 1 task appended and built, then converged)

## Open questions
(none; E1–E4 resolved, see Decisions)

## Decisions
- specify: color IDs from a curated, cited, committed table; no runtime API (user)
- specify: land part becomes 6141 / "plate"; layout schema_version bumped (user)
- specify: extractor is a maintainer script in cli/tools/, PDF library dev-only (user)
- specify: PDF extraction wins over the current land/sea mask; changes documented (user)
- clarify: old-schema layouts rejected with a regenerate message (agent decision)
- clarify: all 40 section images verified in PDF; extraction fails loudly if any missing (auto-resolved)
- clarify: nearest-color suggestion uses CIEDE2000 against the part's kit colors (auto-resolved)
- clarify: layout schema_version 1.0 -> 2.0 (auto-resolved)

- plan: section (col,row) from section-image placement on the locator, cross-checked with page order (auto-resolved, measured)
- plan: pypdf in optional maintainer group; stdlib download/cache (agent decision)
- plan: color table 30/30 IDs verified (LDraw, BrickLink archive, Rebrickable CSV, Brickset)
- plan: regenerated mask equals shipped mask (0 changes, measured)

- plan: test fixtures are synthetic section images + the page-159 word list; no crops of LEGO instruction images committed (agent: internal test structure; stricter on rights)
- plan: statistics key land_brick_count → land_plate_count inside the approved 2.0 format change (agent: follows the user-approved format change)

- plan: add read-only `kit inventory` and `kit colors` CLI commands (user)
- plan: layout files use 6141 (land) / 98138 (ocean); inventory also records LEGO design IDs and element IDs (user)

- tasks: 74 tasks; inventory extract stage built in US1 (T027/T030), extended in US2 (T054/T057); source cache + pdf adapter moved to Foundational because US1 needs them (agent: task order)
- analyze: fixed constrained-field citations (T008, T023, T024, T028, T029, T051-T053, T055, T056, T066); data-model DesignGrid.ambiguity -> classification to match contracts/data-files.md; kit_colors.json source block gains pinned url/sha256/pages [159] (FR-003, rule 4); added T074 for FR-002 (agent)

- analyze: the "no 3062b/brick in tests" rule (SC-006, US1-5) exempts only the v1.0 rejection fixture (T019) and the guard test (T034) (agent: rejecting old layouts, which the user approved, cannot be tested otherwise)

- implement: part descriptions copied verbatim from Brickset (e.g. "ROUND PLATE 1X1") rather than the sentence-case example in contracts/data-files.md, so each row matches its citation (agent)
- implement: `role` is curated in tools/kit31203/part_catalog.json; 4121715/4160228 take Brickset's design/description/color for the equivalent line (61332 Black; 44865 Multicombination), `verified: false` with a note. Brickset (fetched 2026-11-21) totals 11,695 (peg 6279875 x206); the PDF's 11,694 wins (agent, follows spec Assumptions)
- implement: kit_colors.json `rgb` values read from Rebrickable colors.csv fetched 2026-11-21 (all 10 names/IDs match research R3) (agent)
- implement: palette entry 107 carries its citation in a per-color `source` field; LegoColor ignores extra keys (agent)
- implement: colormap fixture legend relabeled 1 white, 2 earth_blue, 3 medium_azur, 4 bright_bluish_green, 5 bright_green, 6 bright_yellowish_green, 7 brick_yellow, 8 flame_yellowish_orange ("Orange"), 9 bright_orange ("Orange-red"), 10 vibrant_coral ("Pink/magenta"); grid values kept, with a note that they do not match the design's counts. No code reads this fixture (agent)
- implement: library adds `load_kit_color_table()` (source + colors) and `parse_kit_colors`/`parse_inventory` next to the contract's loaders; `LEGOWorldMapKitSpecification` gains `inventory_lines`/`inventory_page` for the validate summary (agent: additive, inside feature scope)
- implement: `extract --check` already works for the inventory stage (diff ignoring generated_on); `review` exits 1 until US2 (agent)
- implement: SC-006 grep guard also scans cli/tools; tests avoid the literal patterns except the two allowed files (agent)
- implement: `layout -q` prints nothing, so no disclaimer line there; the JSON metadata carries it (agent)
- implement: validator nearest-color suggestion left Euclidean; CIEDE2000 is US3 (agent: task order)
- implement: T001 not confirmed with Poetry (not installed in this environment); `optional = true` groups are skipped by `poetry install` by design. Tests ran in a uv venv with pypdf 7.1.1 (agent)
- implement: `python -m kit31203` resolves only with cli/tools on sys.path (cwd cli/tools, or PYTHONPATH=tools); pytest's `pythonpath` does not apply to `poetry run python -m`. The maintainer run used `cd cli/tools && python -m kit31203 extract --pdf <cached copy>` (agent; quickstart command needs PYTHONPATH=tools)

- implement US2: classification is CIEDE2000 against reference render colours derived by the RGB k-means of research R6 (`tools/kit31203/reference_colors.json`); the k-means reproduces research's RGB counts exactly. Under CIEDE2000 the automatic counts differ (Bright Bluish Green 1884/1879, Brick Yellow 726/725 before overrides; Earth Blue 392/393, so (0,32) is no longer over supply) (agent, measured)
- implement US2: ambiguity "maximum distance" (deferred finding) set to ΔE00 12.0, above the 99.9th percentile (11.5) of nearest distances; it adds 4 darkened edge cells incl. (0,32). Recorded in the design as `classification.max_delta_e00` (additive key) (agent)
- implement US2: 68 flagged positions (64 by ratio > 0.6, 4 by distance), all resolved in `tools/kit31203/overrides.json` with a reason each; 9 change the automatic colour (6 Bright Bluish Green -> Medium Azur by red channel, 2 Brick Yellow -> Flame Yellowish Orange / Bright Yellowish Green, 1 Bright Green -> Bright Yellowish Green). Rules: Medium Azur vs Bright Bluish Green by red channel (ref R 116 vs 39); Bright Green vs Bright Yellowish Green by red channel (midpoint 151); Brick Yellow vs oranges by blue channel; Flame Yellowish Orange vs Bright Orange by green channel; checked against the review sheet. `decided_by` says agent, pending maintainer review (agent)
- implement US2: **coin-flips for user review** (both candidates plausible on the numbers; decided by the review-sheet visual): (32,16) Flame Yellowish Orange vs Bright Yellowish Green (Brick Yellow ruled out); (16,32) Bright Yellowish Green vs Brick Yellow; (21,34) Bright Yellowish Green vs Bright Green; (33,34) Bright Yellowish Green vs Bright Green. None affects land or any supply limit (agent; needs user confirmation)
- implement US2: (0,32) kept Bright Bluish Green (override entry records research R6's Earth Blue question) (agent)
- implement US2: mask change record compares with the mask in `--out-dir`; `previous_mask_sha256` is that file's SHA-256 (the pre-feature mask: 0 changes). Once the shipped mask is itself derived from the design and its land set is unchanged, the committed record is carried forward so `--check` stays reproducible (agent)
- implement US2: overrides contradicting a confident cell without `force`, invalid override rows, and reference/kit colour order mismatch exit 7 (contract table has no separate code) (agent)
- implement US2: `ImagePlacement` gained `height_pt` (drawn height) to derive row pitch from the locator panels; section-image decode size checked against the placement (exit 5) (agent)
- implement US2: `review` writes the PNG sheet and `<name>.overrides-stub.json` under `<cache>/review/` by default; the sheet was produced in the session scratchpad and not committed (agent)
- implement US2: placements fixture holds every placement on pages 22, 26, 66, 132 (measured) and a synthetic 40-page list; extract-pipeline tests monkeypatch `read_pdf_inputs` and `OVERRIDES_PATH` with synthetic images (agent)
- implement US2: colormap fixture `tests/fixtures/lego_world_map_colormap.json` kept as relabeled in US1 (plan lists it as relabeled, not retired) (agent)

- implement US3: validator suggestions use CIEDE2000 between the layout color's palette RGB and the cited `kit_colors.json` RGB of each kit color of the affected part (land: White only; ocean: the 9 tile colors); quantities come from the inventory via `load_kit_specification()` (agent)
- implement US3: T063 "extra Earth Blue cell" uses two extra cells: the design uses 392 of 393 Earth Blue tiles (US2 CIEDE2000 counts), so one extra cell is still within supply; two give exactly one violation (394/393, shortfall 1) (agent, measured)
- implement US3: `DesignGrid.to_layout()` labels White cells plate/6141 and every other cell tile/98138, names and codes from `kit_colors.json`; it imports `layout` inside the method to avoid a kit<->layout import cycle (agent)
- implement US3: generator labels kit colors with `kit_colors.json` LEGO names and IDs (same strings as the palette today); non-kit palette colors keep palette labels so validate can report them (agent)
- implement US3: `validate` re-raises `click.ClickException` unchanged and catches `JSONDecodeError` before `ValueError` (previously the format error was wrapped as "Unexpected error" and invalid JSON reported as a plain ValueError) (agent: bug fix inside the touched command)
- polish: `layout -q` stays silent. Constitution VIII says all user-facing output must carry the disclaimer; the contract (cli.md) puts it on the last line of human output and in the JSON metadata. Quiet mode has no human output, and the JSON file it writes carries `metadata.disclaimer`, so no line is added (agent; see deferred CSV finding)
- polish: offline guard blocks `connect`/`connect_ex` on AF_INET/AF_INET6 sockets for the whole session (AF_UNIX left alone); `tests/integration/test_offline_guard.py` proves it is active (agent)
- polish: suite confirmed without pypdf in a separate venv (432 passed, 1 skipped: `tests/unit/tools/test_pdf_adapter.py`) and with pypdf (436 passed); no test reads the PDF (agent, measured)
- polish: maintainer tool invocation documented as `PYTHONPATH=tools poetry run python -m kit31203 ...` from `cli/` in quickstart.md, cli/README.md, CLAUDE.md and AGENTS.md (agent)
- polish: specs/001-image-processing/tasks.md: 30 tasks marked [X] after checking code/tests (some landed under other names, noted in the file); unbuilt US1/US2 options and all US3 batch tasks left unchecked (agent)
- converge round 1: 1 finding appended as T075 (plan performance goal for loaders had no check; measured 0.6 ms warm-import cold load); built. Round 2: converged; the CSV disclaimer finding is parked (format decision) (agent)

## Quickstart run (T072, 2026-11-21; uv venv in place of `poetry run`)

| Section | Command | Result |
|---|---|---|
| 1 | `pytest` with pypdf / without pypdf | 436 passed / 432 passed, 1 skipped (pypdf adapter) |
| 2 | `kit inventory` | 32 lines, 11,694 pieces; 614101 6141/4073 ROUND PLATE 1X1 White 3064 land 159; disclaimer last |
| 2 | `kit colors --format json \| python -c ...` | `10 1` |
| 2 | `git grep` SC-006 patterns (with `--untracked`) | only the two exempt files and 003 spec documents |
| 3 | design summary | `128 80 10`, all spares >= 0, White 3062/3064, 40 sections |
| 3 | `PYTHONPATH=tools python -m kit31203 extract --check --pdf <pinned copy>` | exit 0, "Check: no differences" |
| 3 | `... extract --pdf wrong.pdf` | exit 4, expected/actual SHA-256, no files written |
| 4 | validate official design | `Buildability: 100.0% (FULLY BUILDABLE)`, `Violations: 0`, disclaimer last |
| 4 | layout + validate `test_128x80_quantized.png` | schema 2.0, plate/6141 + tile/98138; color violations with part, positions, `Suggested alternative: ... (ΔE00 x.x)` from that part's kit colors |
| 4 | validate `legacy_v1_layout.json` | exit 1, schema 1.0 message with the regenerate command |
| quickstart note | the quickstart's original `poetry run python -m kit31203` fails without `PYTHONPATH=tools`; quickstart updated |

## Generated data (T058, extract --check exit 0 "no differences"; wrong PDF exit 4, no files written)

| File | SHA-256 |
|---|---|
| kit_31203_design.json | 9a7b29f203c6381c774bf490e5816c7f556377ed0c6becdd2c6bb24e77c12a2f |
| kit_31203_inventory.json | 2cbf7b8f4b02d03c11895aa5dfef045c320c640689a7ddc05cf7d7c448453284 |
| kit_31203_mask_changes.json | 193b23a84a850f24f044bd09ed17e996302649095d301fce97b72b1d30714cca |
| lego_world_map_land_sea_mask.json | 752a4462fc0929944379369cdb1e19571cad770810474056bc45b66d044e03d6 |
| kit_colors.json (curated, unchanged) | 05bc812db1b61c831917fbecfeff6138f33287f5a6ffc8e45b378c9eb0f6299d |

| Color | Used | Supplied | Spare |
|---|---|---|---|
| White (land) | 3062 | 3064 | 2 |
| Bright Bluish Green | 1878 | 1879 | 1 |
| Medium Azur | 1606 | 1607 | 1 |
| Bright Yellowish Green | 1019 | 1060 | 41 |
| Brick Yellow | 724 | 725 | 1 |
| Bright Green | 529 | 601 | 72 |
| Bright Orange | 230 | 601 | 371 |
| Vibrant Coral | 203 | 601 | 398 |
| Flame Yellowish Orange | 597 | 599 | 2 |
| Earth Blue | 392 | 393 | 1 |

40 sections (order check 40/40); flagged 68 = resolved 68; mask 3062 land / 7178 ocean, 0 changes
vs the previous mask (T059: no test expectations to update).

## Blocked tasks

## Deferred findings
- [MEDIUM, needs user: file format] FR-021 / constitution VIII: `layout -f csv` writes no disclaimer (CSV has only a header and position rows), and with `-q` nothing user-facing carries it. Options: a trailing `# Not affiliated ...` comment row, an extra column, or a sidecar note; each changes a file format other people use, so it is parked.
- [needs user] US2 coin-flip colors at (32,16), (16,32), (21,34), (33,34) still await maintainer review (see Decisions).
- [HIGH, needs user] SC-006/US1-5 require zero occurrences of `3062b`/land "brick" in tests, but US3-4 needs a schema-1.0 fixture (T019 legacy_v1_layout.json) and the grep guard (T034) names the patterns. Tasks exclude those two files; confirm this exception or say how to test rejection otherwise.
- [MEDIUM] Role naming drift: spec FR-005 says "baseplate, frame/other"; data-model uses `section_base`, `frame_other`.
- [MEDIUM, resolved in implement] Ambiguity rule "d1 exceeds a maximum distance" (research R6) has no value; set to ΔE00 12.0 (see Decisions).
- [MEDIUM] Plan performance goal (loaders < 100 ms) has no benchmark task.
- [MEDIUM] Curated tool files (part_catalog.json, reference_colors.json, overrides.json) are not covered by an explicit source-block rule (FR-003 scope).
- [LOW] contracts/cli.md heading still says "pending ESCALATE E1" (resolved).
- [LOW] plan.md phase list puts source cache/pdf adapter in US2; tasks put them in Foundational.
- [LOW] contracts/data-files.md design shape has `coordinate_system`, not listed in data-model DesignGrid.
- [LOW] T034 (grep test) sits after T032/T033 in US1; run it first to respect test-first ordering.

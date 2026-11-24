# Run state: 016-map-templates

Source: prompt (owner, 2026-11-22/23: projection study follow-up, "Do 1-3"; four scoping answers)
Phase: done
Status: done; committed on branch 016-map-templates (not pushed); open for the owner:
T109 (price snapshot refresh) and the deploy
Updated: 2026-11-24 (owner's answers: T039 confirmed as is; margin shade matches pure black;
commit without push)

Paths: `<scratchpad>` is the implementing session's scratch folder, outside the repository (review
sheets, real-data outputs, backups; never committed). The review files for T039 are also in
`~/.cache/lego-image-processor/templates/`.

Worktree: `98138_world-016`, beside the main checkout (branch 016-map-templates). Started from
origin/main f5b9f4c; moved to main af3ce57 on 2026-11-23 after 011, 014 and 015 (the palette
chooser, renumbered from 012) merged; moved to main 6038d9c (round studs on black for map
previews) on 2026-11-23 after Phase 4, with the kit golden re-based on it (Implementation records,
"Sync to main 6038d9c"); the drafts are uncommitted. Feature number 016: 012–015 are taken.

Scope of this run (owner): draft the spec. Stop after clarify and ask before planning or building.
Owner reviewed the spec and said "plan" (2026-11-23): run plan, tasks and analyze; stop before
implement and ask.

## Open questions
- none

## Decisions
- done: owner confirmed the Winkel tripel template as is, no corrections (user, 2026-11-24);
  Black margin studs drawn as the preview background, pure black (user, 2026-11-24); commit on the
  branch without push (user, 2026-11-24); T002 removed the constitution's Sync Impact Report
  comment at that commit
- open for the owner: T109 price snapshot refresh with BrickLink credentials; deploy
- T039: the owner confirms the Winkel tripel template as is, with no corrections; recorded as
  `{"role": "project owner", "date": "2026-11-24"}`, no personal name (user, 2026-11-24)
- margin shade: match pure black: in previews, margin studs in LEGO Black are drawn in the
  preview's background color (pure black, as main 6038d9c draws), so they blend into the
  background; other margin colors and the ring keep their cited colors; the palette chooser canvas
  draws the same; parts lists, exports, sheets and `cells.json` keep LEGO Black's cited color; kit
  outputs unchanged (user, 2026-11-24; research R13 note, spec Clarifications 2026-11-24)
- tests of the refusal to build on an unconfirmed template use an unconfirmed copy of the package
  file, not the package file (user, 2026-11-24)
- implement: owner said "implement 016" (user, 2026-11-23); batches: Phases 0+1, 2, 3, 4, 5, 6,
  7, 9, each in its own subagent; T039 owner review asked when no independent work remains
- constitution: amended to 3.0.0 (Principle I, templates) with the owner's approval of the exact
  text, 2026-11-22 (user)
- specify: path 2B (no spec); four scoping questions answered (user): CLI first and web P2; margin
  background first and labels P3; 1×1 square tile 3070b; one Winkel template centred on 11.1° E,
  error for other arrangements
- specify: board stays 8 × 5; other dimensions on the roadmap in docs/vision.md (user)
- specify: default margin Black, no ring (agent: kit base bricks are black; recipe can override)
- specify: `official-31203` is kit-only on the web and CLI (user, 2026-11-23)
- specify: the web shows Winkel for five maps; none for the ENSO pair (follows the arrangement
  error the owner chose)
- clarify: spec updated for 011/014/015 now on main: palette chooser cells and per-template ice
  regions (FR-020a/b), leftovers and prices include the square tile, price snapshot refresh needs
  the owner's BrickLink credentials (agent: follows the merged features)
- clarify: stop after clarify for owner review (user)
- plan: owner reviewed the spec with no changes and said "plan" (user, 2026-11-23)
- plan: plan.md, research.md (R1-R22), data-model.md, contracts/, quickstart.md written; no
  constitution violations (agent)
- plan: runtime needs no pyproj: numpy forward Winkel formula plus stored stud locations; pyproj
  >=3.7,<3.8 in the maintainer group only (3.8 needs Python 3.12) (agent: R1, run policy allows
  permissive maintainer deps)
- plan: fit uses the exact published extent, not the study's sampled one; spec counts become
  approximate (agent, close call: R2; recorded in spec Clarifications)
- plan: round/square stud shapes on non-kit previews only; kit previews unchanged (agent, close
  call: R13; recorded in spec Clarifications)
- plan: spec note: a corner label fits about 7 characters on one line (R20); kept FR-021's error
  when text does not fit (agent; superseded 2026-11-23, labels moved to 017, below)
- tasks: tasks.md written, 109 tasks; owner stops T011 (3070b page source, only if needed), T039
  (review and confirm the Winkel template), T109 (price snapshot refresh) (agent)
- tasks: kit cells.json guard moved into phase 1 (T016) so adding 3070b colors does not change kit
  outputs; provisional ice file (T076) regenerated after confirmation (T082); tests use a synthetic
  numpy-only template via a patched TEMPLATE_DIR (agent)
- analyze: 0 CRITICAL, 4 HIGH (I1 ice file tied to the template file's SHA-256, so test
  confirmation breaks it; C1 T002 wording vs "do not edit the constitution by hand"; C2 ETOPO
  citation missing from template outputs; D1 missing data-model citations), 16 MEDIUM/LOW, 100 %
  coverage; all sent back to the tasks phase as mechanical fixes (agent)
- analyze: T002 removes only the Sync Impact Report comment, which the derive-constitution workflow
  marks "remove before committing" (the committed 2.0.0 file, 8108f47, has none) (agent)
- analyze: all 20 findings fixed in tasks.md, data-model.md, research.md, quickstart.md and
  contracts/; 111 tasks (T020a/T020b added for the layout digest); the ice file records
  `layout_sha256` (layout content without the confirmation) instead of the file's SHA-256; template
  outputs cite ETOPO 2022; the committed test template fixture is about 170 kB because the loader
  requires 128 x 80 (agent)
- clarify: 5 items auto-resolved (template field absent = kit; additive recipe keys and options;
  corrections and confirmation recorded as role "project owner", no personal name; below-sea-level
  basins follow the study rule and are flagged on the review sheet; 3070b colors via partcolors
  with a pinned BrickLink page) (agent: evidence in spec Clarifications)
- scope: labels out of 016. "I don't think making labels with bricks. I was thinking instead about
  a sticker approach on a black plate (like existing lego labels for large kits)." Labels move to
  a new feature 017 map stickers (`specs/017-map-stickers/`, own branch): a printable sticker for
  every map on a black tile in two sizes (a small plaque such as a 6×6 tile for a Winkel corner's
  free region, a large display plaque such as 8×16) with title, legend and credits; after 016
  ships, an optional plaque in a Winkel margin corner, with layout, preview, parts list and sheets
  swapping the square tiles under it for the black tile. 016's margin is a color with an optional
  outline ring (user, 2026-11-23; answers open question 2, corner labels)
- scope: artifacts updated for the decision: spec (US4 removed with a note, FR-021 a removed
  placeholder, Clarification added), plan (Phase 8 and spec note 3 removed, no stud font),
  research R20 (keeps the corner room facts for 017), data-model, contracts (no label keys,
  options or outputs), tasks (T094-T099 removed; 105 tasks; FR-021 coverage "removed, moved to
  017"), checklist re-checked, docs/vision.md (016 row, new 017 row), projection_study wording
  (corner plaque room) (agent, 2026-11-23)

## Implementation records
- T001 baseline (2026-11-23, code at af3ce57, before any feature 016 code change): CLI
  `cli/.venv/bin/pytest -q` 1555 passed, 1 skipped (93 s; includes the 8 untracked
  projection-study tests); web `web/.venv/bin/pytest -q` 133 passed (51 s). Known flaky (not
  016): `tests/integration/test_map_cells.py::TestDefaultEqualsBuild::test_does_not_change_layout`
  compares two builds' `generated_at` (1 s resolution) and fails when a second boundary falls
  between them.
- T006 kit golden: `cli/tests/fixtures/golden/kit_outputs.json` (+ `.source.json`), 24 variants,
  568 output digests, written with `git diff -- cli/src web/src` empty; the harness takes about
  17 s. T009 web golden: `web/tests/fixtures/kit_variants_golden.json` (small, living-planet and
  rainfall sites: 7 maps x A, B, C), written from unchanged code. Neither file is committed yet
  (run policy: no commits); both are in the working tree.
- T008 real-data digests (before): `<scratchpad>/016/kit-before.json`
  (SHA-256 615c788e4b5b88fb033e29ed54a41bd5dc9ab2356693ebfdb9a36055f666728e; 52 s), from the
  per-user cache `~/.cache/lego-image-processor` with datasets ersst-v5-1988-12,
  ersst-v5-1997-12, ersst-v5-ltm-1991-2020, etopo2022-surface-10m, gpcp-v23-ltm-1991-2020,
  kit31203-design (packaged), mod17a3-npp-mean-2000-2015, modis-aqua-chla-2013-2024,
  nsidc-cdr-v6-seaice-minimum-1991-2020. Compared in T104. Replaced on 2026-11-23 by the digests
  of main 6038d9c (same path, SHA-256 a67b3bd1...; the af3ce57 file is kept as
  `kit-before-af3ce57.json`); see "Sync to main 6038d9c".
- T010 pinned 3070b pages (accessed 2026-11-23, maintainer cache
  `~/.cache/lego-image-processor/sources/partnumbers/`, never in the repo): BrickLink
  `bricklink-3070` = item 3070 "Tile 1 x 1", Internet Archive copy of 2026-01-01 (SHA-256
  946c7d10…); Rebrickable `rebrickable-3070b` = "Tile 1 x 1 with Groove", copy of 2026-03-04
  (SHA-256 8d954b6f…). The earlier partcolors/partnumbers snapshots were copied, checksum-verified,
  from an older session's scratchpad into the same cache. T011 not needed.
- T017: part_colors.json 6141 44, 98138 40 (unchanged), 3070b 48 colors incl. lego_black, all
  `in_kit: false`; `partnumbers build --check` and `partcolors build --check` print "no
  differences"; kit golden (fixtures and real data) unchanged after Phase 1.
- Phase 2 (T020-T032, 2026-11-23): `templates` package (`__init__`, `digest`, `board`, `winkel`,
  `geometry`), `template list/show/locate`, fixtures `synthetic_template` and `confirmed_winkel`.
  CLI suite 1821 passed, 1 skipped (pyproj installed in cli/.venv for the reference test; the
  200,000-point check is skipped without it); kit golden (fixtures) and web golden unchanged.
  Synthetic fixture `cli/tests/fixtures/templates/` (178 kB + ice 7 kB): 2,101 land / 6,143 ocean
  / 1,996 margin, ring 288, modules 18/22/0, corners 14 x 14, so the analytic outline reproduces
  research R2's exact-fit margin counts. Template load: first 11 ms, cached 0.1 ms.

- Phase 3 (T033-T038, 2026-11-23): `maptemplates generate|review|write|build --check`
  (`tools/maptemplates/generate.py`, `review.py`, `document.py`), pyproj `>=3.7,<3.8` in the
  maintainer group (3.7.2 already in cli/.venv; Poetry is not installed, so `poetry install
  --with maintainer` was not run). T036 on the cached pinned ETOPO 2022 file with pyproj 3.7.2 /
  PROJ 9.5.1 and the exact extent: **2,553 land / 5,691 ocean / 1,996 margin, ring 288, modules
  18 / 22 / 0, corners 14 x 14** (top-left at row 0 col 0, top-right row 0 col 114, bottom rows
  66), exactly research R2; flags **194 land share 40-60% (126 land, 68 ocean; 69 land studs are
  8/16 ties) + 97 water not connected to the ocean in 20 groups, largest 33**. Generation takes
  under 1 s. T037: package file `cli/src/lego_image_processor/data/templates/winkel-tripel.json`
  (177,501 bytes, SHA-256 2c0c23f7..., layout SHA-256 389963b5...), unconfirmed, no corrections;
  `build winkel-tripel --check` prints "no differences"; one class changed at row 40 column 31 gives
  exit 1 "classes: row 40, column 31 (section B3): committed O, regenerated L"; restored
  byte-identical. CLI suite 1901 passed, 1 skipped (packaged price snapshot); kit golden (fixtures
  and web) unchanged; real-data kit digests byte-identical to T008's `kit-before.json`.
  `confirmed_winkel` now copies the package file with the test confirmation (same layout digest).
- T039 prepared for the owner (not done): review files in
  `<scratchpad>/016/review/`
  (`winkel-tripel.review.png` 16 px/stud sheet, `winkel-tripel.board-screen.png` 10 px/stud,
  `winkel-tripel.flags.json`, `winkel-tripel.counts.txt`, the candidate `winkel-tripel.json`);
  the same candidate, sheet and flags are in `~/.cache/lego-image-processor/templates/`.

- Phase 4 (T040-T060, 2026-11-23): template resolution, sampling and rules on templates, margin
  and ring, layout format, preview shapes, report blocks, `map build|check --template
  --margin-color --ring-color`. Kit golden unchanged after the build changes and at the end
  (fixture test, `web/tests/test_kit_golden.py`, and real-data `maptemplates kit-golden` byte-identical
  to `kit-before.json`, SHA-256 615c788e...). Real-data Winkel builds on a confirmed scratch copy
  (`ocean-sst`, `land-elevation`, `ocean-sst --ring-color lego_bright_yellow`): 2,553 land / 5,691
  ocean / 1,996 margin each; previews in
  `<scratchpad>/016/previews/`.
  Fixture builds: Winkel about 1.0x the kit build time; cached template load 0.05 ms.

- Sync to main 6038d9c (2026-11-23, after Phase 4, before Phase 5): main moved af3ce57 -> 6038d9c
  ("Round studs on black for map previews; thumbnails stay square", the owner's other session;
  `write_preview(style=, background=)`, `map build --preview-style`, web thumbs `style="square"`,
  palette canvas rounds, spec 008 amended). Base is now **6038d9c**. Backup first, outside the
  repo: `<scratchpad>/016/backup/016-tracked.patch` (`git diff --binary`, 38 files) and
  `<scratchpad>/016/backup/016-untracked.tar` (65 untracked files; list and SHA-256s beside it). Then
  `git stash push -u`, `git merge --ff-only main`, `git stash pop`: conflicts in
  `maps/preview.py` and `cli/map.py` only (`test_preview.py` auto-merged), resolved by hand,
  stash dropped after every untracked file checked byte-identical. Resolution: main's
  `preview.py` is the one code path; in the round style a position of part type `square_tile`
  (`layout.position.MARGIN_PART_TYPE`) gets full coverage, so template margin and ring studs are
  squares and land/ocean studs are main's rounds (diameter 0.9, 8x, background (0, 0, 0));
  `style="square"` squares everything. 016's 0.95 / 4x / cited-Black constants
  (`SUPERSAMPLE`, `BACKGROUND_COLOR`) are gone (research R13 note, spec Clarification).
  `map build` keeps both `--preview-style` and the template options. The 016 preview tests now
  assert main's style (kit: rounds on black; template: the same rounds plus margin squares,
  square style and background option).
- Kit golden re-based on 6038d9c from an unmodified checkout (temporary worktree
  `<scratchpad>/main-6038d9c`, removed afterwards; only 016's harness files copied in; imports checked to
  resolve there): `cli/tests/fixtures/golden/kit_outputs.json` (SHA-256 8a865bb3..., `.source.json`
  code.commit 6038d9c, previous af3ce57 86ba7ab3...) and `web/tests/fixtures/kit_variants_golden.json`
  (SHA-256 1cca6fb9...; 5 maps x A, B, C = 15 variants, not 7 maps as T009 said). Against
  af3ce57 only previews moved: CLI 24 `preview.png`; web 15 `preview.png` and their manifest
  entries (thumbs, cells, parts, pages identical). Real-data digests: `<scratchpad>/016/kit-before.json`
  now 6038d9c's (SHA-256 a67b3bd1...; 24 previews differ from `kit-before-af3ce57.json`); the old
  goldens are kept in `<scratchpad>/016/golden-af3ce57/`. Tests pinning af3ce57 now pin 6038d9c
  (`test_kit_outputs_unchanged`, `test_kit_golden.BASE_COMMIT`).
- After the sync, in this worktree: CLI kit golden and web kit golden pass; real-data
  `maptemplates kit-golden` with 016 code byte-identical to the new `kit-before.json`
  (`<scratchpad>/016/kit-after-sync.json`); CLI suite 2072 passed, 1 skipped (107 s); web suite 139
  passed (42 s). Real-data Winkel previews re-rendered with the merged code on a confirmed
  scratch copy (`ocean-sst`, `land-elevation`, `ocean-sst --ring-color lego_bright_yellow`; counts
  unchanged): `<scratchpad>/016/previews/` (script `<scratchpad>/016/scripts/render_winkel_previews.py`).
- For later phases (sync): main's `palette.js` now draws every chooser cell as a round
  (`STUD_DIAMETER = 0.9`, black canvas); T091/T092 should draw template margin cells as squares
  in that same drawing. Web thumbnails are `style="square"` for every variant. The Black margin
  squares in previews are the cited Black (5, 19, 29), a shade lighter than main's pure-black
  gaps between rounds (main's background, kept; an owner choice if it should match: resolved
  2026-11-24, they now match, see "Owner's answers"). The golden files must only ever be re-written
  from an unmodified main checkout, as above.

- Phase 5 (T061-T073, 2026-11-23): square tiles in parts lists, exports, leftovers, prices, build
  sheets, validation and `layout arrange`. Kit golden unchanged: CLI `test_kit_outputs_unchanged`,
  `web/tests/test_kit_golden.py`, and real-data `maptemplates kit-golden` byte-identical to
  `kit-before.json` (SHA-256 a67b3bd1...; written to `.../scratchpad/016/kit-after-phase5.json`).
  New test fixture `cli/tests/fixtures/prices/bricklink_price_guide_3070b.json` (+ `.source.json`,
  SHA-256 013037b9...): the first fixture plus one 3070b Black lot; the first fixture is
  byte-identical (38f9aea8...). Shared test helper `cli/tests/winkel_layouts.py` (`winkel_grid`:
  a template layout by class, no dataset). Real-data outputs on a confirmed scratch copy
  (`ocean-sst`): `<scratchpad>/016/outputs/`
  (script `.../scratchpad/016/scripts/phase5_outputs.py`): 11 lots, 10,240 pieces, 0 unverified;
  3070b Black 1,996 (BrickLink item 3070, Rebrickable 3070b); one kit buys 1,996 pieces in 1 lot,
  left over 2,886 (White 511, tiles 2,375); fixture estimate incomplete (square tiles unpriced),
  complete with the 3070b fixture; 42-page sheets.

- Phase 6 (T074-T080, 2026-11-23): `maptemplates ice-mask ID [--check] [--dataset FILE]
  [--cache-dir DIR]` (`tools/maptemplates/ice.py`), `maps/ice.py` `load_template_ice`,
  `map cells --template --margin-color --ring-color` and `map_cells` on templates. T076: package
  file `cli/src/lego_image_processor/data/templates/winkel-tripel-ice.json` (7,044 bytes, SHA-256
  1bb42944...) from the committed unconfirmed template (layout SHA-256 389963b5...) and the cached
  pinned ERSST v5 1991-2020 file: **566 land-ice studs, 229 sea-ice studs** (kit: 711 land-ice and
  796 sea-ice cells; the kit's 796 include its 128 polar-row cells beyond 89 N that no ERSST node
  reaches). `ice-mask winkel-tripel --check` prints "no differences"; 2 of the 229 are "no value
  poleward of 60" (all nodes missing); 52 ocean studs get no ERSST node at all, none poleward of
  60, so none of them is sea ice. `confirmed_winkel` copies the ice file with the template
  (`confirmed_copy` already did); the synthetic fixture keeps its own. Kit golden unchanged: CLI
  `test_kit_outputs_unchanged`, `web/tests/test_kit_golden.py`, real-data `maptemplates
  kit-golden` byte-identical to `kit-before.json` (`.../scratchpad/016/kit-after-phase6.json`).
  CLI suite 2182 passed, 1 skipped (one other run had 1 failure, not reproduced in two reruns:
  most likely the known flaky `test_does_not_change_layout`, see T001); web suite 141 passed
  (Node palette tests ran). Real-data Winkel cells on a confirmed scratch copy:
  `.../scratchpad/016/outputs/ocean-sst.winkel.cells.json` and `living-planet.winkel.cells.json`
  (script `.../scratchpad/016/scripts/phase6_cells.py`, summary `outputs/phase6-cells-summary.json`):
  L 2,553 / O 5,421 / S 270 / M 1,996 for both; ocean-sst's default rendering equals its layout;
  living-planet differs only on its 756 no-data studs (class -2, White), as kit cells.json does
  for its 1,440 (feature 015: cells.json carries no no-data color).

- Phase 7 (T084-T093, 2026-11-23): Winkel versions on the web site. The web session builds on a
  confirmed copy of the committed template (conftest `confirmed_template_dir`, autouse, session),
  so the small site has ocean-sst on Winkel, and the living-planet and rainfall sites one each.
  Web suite 209 passed (was 141; Node palette tests ran), including `test_kit_golden.py`, whose
  comparison now allows exactly the Winkel nav item on the eligible maps' kit pages and the
  square-tile label (golden file not re-written; see decisions). T093 in Chromium (Playwright's
  chromium-1248) on a local uvicorn of the real-data scratch site: recolor, every one of the
  1,996 margin studs square in Black on the canvas, ice as White on the template's ice, fragment
  restores the state, JavaScript off: preview and all 9 downloads (SHA-256 checked); report and
  screenshots in `<scratchpad>/016/browser/`.
  CLI suite 2182 passed, 1 skipped (no CLI code changed in Phase 7); real-data `maptemplates
  kit-golden` byte-identical to `kit-before.json` (SHA-256 a67b3bd1...; `.../scratchpad/016/kit-after-phase7.json`).
- Phase 7 real-data prebuild (not T105, which waits for T039): `--no-prices` (no packaged price
  snapshot), confirmed scratch copy of the template via `<scratchpad>/016/scripts/prebuild_confirmed.py`
  (test confirmation, not the owner's): 29 variants (24 kit + 5 Winkel: official-31203-bathymetry,
  ocean-sst, land-elevation, living-planet, rainfall), 179.8 MB, 63.2 s wall
  (`<scratchpad>/016/site/`). `--templates none`: 24 variants, 151.4 MB, 50.6 s (`<scratchpad>/016/site-kit/`); so +25 %
  time and +18.8 % size (plan: about +20 %). Each Winkel variant 5.6-5.8 MB, 12 files, 1.4-5.5 s.
  Plain main 6038d9c prebuild (`git archive` export, same venv with PYTHONPATH): 24 variants,
  151.4 MB, 50.4 s (`<scratchpad>/016/site-main/`). Kit variants of both 016 sites equal main's (manifest
  entries, previews, thumbnails, cells, exports, normalised layouts and parts lists; PDFs skipped
  as in the web golden: they differ by a few bytes between any two builds); only the top-level
  `part_labels` gains 3070b on the Winkel site (`<scratchpad>/016/compare-sites.txt`). The real prebuild with
  the committed unconfirmed template prints "Template winkel-tripel: not confirmed by the project
  owner, so no template variants are built (confirmed templates: kit-31203)" and writes a kit-only
  manifest. The CLI wheel carries `data/templates/`, so the Docker prebuild needs no change.

- Phase 9 (T100-T108, 2026-11-23, base main 6038d9c): docs (README.md, cli/README.md new "Map
  templates" section, web/README.md, docs/deploy.md, docs/vision.md 016 row "built", the projection
  study README, the same 016 paragraph in CLAUDE.md and AGENTS.md); T103 adds the `template` group
  and every Winkel output (layout, report, cells.json, parts list, export, estimate, SVG sheets,
  section counts, validation) to `tests/contract/test_disclaimer.py`, which points to the other
  disclaimer tests (template and maptemplates contracts, review sheet, sheets, web pages).
- T104: real-data `maptemplates kit-golden --cache-dir ~/.cache/lego-image-processor` (52 s)
  byte-identical to `kit-before.json` (SHA-256 a67b3bd1..., 24 variants, 568 outputs;
  `<scratchpad>/016/kit-after.json`). Fixture kit golden (`--fixtures`) byte-identical to the
  committed `cli/tests/fixtures/golden/kit_outputs.json`.
- T106 (quickstart steps 1-11, script `<scratchpad>/016/scripts/phase9_quickstart.py`, outputs
  `<scratchpad>/016/quickstart/`): every step passed; no doc mismatch to fix. Steps 1-2: fixture
  kit golden identical; `partnumbers` and `partcolors build --check` "no differences"; `kit
  part-colors --part 3070b` lists Black (48 colors). Step 4: `generate` 2,553 / 5,691 / 1,996,
  ring 288, flags 194 + 97 (20 groups, largest 33). Step 5 on a scratch copy only: `map build`
  refused (exit 1, "not confirmed by the project owner"), `write --confirmed-on` with a test date,
  `template show` then "project owner, 2026-11-23". Step 6 on that copy: `build --check` "no
  differences"; one class changed gives exit 1 naming row 40, column 21 (B3), plus a
  `confirmation` difference (a changed layout drops the committed confirmation: `write` keeps it
  only while classes and locations are unchanged); restored, "no differences". Step 7: `ice-mask
  --check` "no differences". Step 8, five maps on the confirmed copy (real data): counts equal the
  template's, 10,240 pieces each, 1,996 Black 3070b, 0 unverified lots, ETOPO cited in layout,
  report and cells.json; beyond one kit / left over: ocean-sst 1,996 / 2,886,
  official-31203-bathymetry 1,996 / 2,886, land-elevation 6,916 / 7,806, living-planet 7,245 /
  8,135, rainfall 8,516 / 9,406; `--ring-color lego_white` colors exactly 288 studs. Step 9: the
  four errors exit 1 with the contract messages, nothing written. The package template directory
  was byte-identical before and after.
- T105 checks on a confirmed scratch copy (not T105 itself, which waits on T039): real-data
  prebuild `--no-prices` 29 variants, 179.8 MB, 61.3 s (`<scratchpad>/016/site-phase9/`); served
  with uvicorn: `/healthz` 29 variants; `/maps/<map>/winkel-tripel` 200 for the five eligible maps
  (re-hang note, disclaimer, 9 downloads each, all 200 with the right types), 404 for
  official-31203, ocean-el-nino and ocean-la-nina; the about page names Winkel tripel; ocean-sst/A
  links the Winkel page, ocean-el-nino/B does not. Kit-only timing from Phase 7: 24 variants,
  151.4 MB, 50.6 s.
- T107 (socket guard on): CLI `cli/.venv/bin/pytest -q` **2188 passed, 1 skipped** (113 s; T001
  baseline 1555 passed, 1 skipped); web `web/.venv/bin/pytest -q` with Node on PATH **209 passed**
  (62 s; T001 133). The kit goldens pass in both (`test_kit_outputs_unchanged`, `test_kit_golden`).
- Final checks: `git status` shows only the feature's files (94 modified, 74 untracked, nothing
  staged); no downloaded data, PDF or crop of the kit instructions; scratch outputs are outside the
  repository. Personal-name grep of the diff and untracked files: no emails; the only hits were
  absolute scratch paths in this file, now written as `<scratchpad>` (main's
  `cli/tests/fixtures/images/DOWNLOAD_GUIDE.md` already has one such path; not 016's).

- Converge round 1 (Phase 11, T110-T111, 2026-11-23, base main 6038d9c). T110: owned and missing
  CSVs are read for the layout's map parts (`parts.owned_parts(grid)`: 6141 and 98138, plus 3070b
  when the layout has square tiles), so on a kit layout 3070b rows and rows with 3070b's other
  numbers (3070, 30039, 35403, 39727, 53836, 112412) are ignored and counted again, a 3070b element
  is main's "not listed" error and the numbering error lists "(6141, 98138)"; template layouts
  count loose 3070b and reject its other numbers. Regression fixture
  `cli/tests/fixtures/golden/kit_owned_csv.json` (+ `.source.json`, SHA-256 cf50fd10..., 11 cases
  of `parts list`/`parts export` on the official design with owned/missing/element CSVs) written by
  the harness `cli/tests/kit_owned_csv.py` (SHA-256 88792bfb...) from a `git archive 6038d9c cli`
  export (`<scratchpad>/016/main-6038d9c-t110/`, only the harness added; `PYTHONPATH=<export>/cli/src`
  checked to import main's package), run twice byte-identical; compared by
  `tests/contract/test_kit_owned_csv.py`, which failed before the fix (3070 row: exit 1 instead of
  "11 row(s) for other parts ignored"). T111: the ring = margin error (`ring_rule`, used by
  `resolve_margin` and recipe `margin.ring`) now lists the available 3070b color keys and points
  to `kit part-colors --part 3070b`. Results: CLI suite **2211 passed, 1 skipped** (119 s); web suite
  **209 passed** (66 s, Node on PATH); CLI `test_kit_outputs_unchanged` and web `test_kit_golden`
  pass; real-data `maptemplates kit-golden` byte-identical to `kit-before.json` (SHA-256
  a67b3bd1...; `<scratchpad>/016/kit-after-t110.json`).

- Owner's answers (2026-11-24). T081: `PYTHONPATH=tools .venv/bin/python -m maptemplates write
  winkel-tripel --confirmed-on 2026-11-24 --cache-dir ~/.cache/lego-image-processor` (no
  corrections file): the package file changed only in `confirmation` ({"role": "project owner",
  "date": "2026-11-24"}) and `source.generated_on` (2026-11-24: `write` keeps the committed date
  only when nothing else changed); SHA-256 608072c5... (was 2c0c23f7...), layout SHA-256 389963b5...
  unchanged, 0 corrections. `template show` prints "Status: confirmed" and "Confirmation: project
  owner, 2026-11-24". `build winkel-tripel --check` "no differences" (exit 0); one class changed
  at row 40, column 31 gives exit 1 (classes, and the confirmation a changed layout drops);
  restored byte-identical, "no differences" again. `confirmed_winkel` and the web session's
  `confirmed_template_dir` now use the package file as is. T082: `ice-mask winkel-tripel --check`
  "no differences" (566 land-ice, 229 sea-ice studs); the T076 ice file (1bb42944...) is kept,
  not regenerated. Backups of both files before the change: `<scratchpad>/016/backup-t081/`.
- Tests that assumed an unconfirmed package file now test the refusal on an unconfirmed copy:
  new helper `maptemplates.testing.unconfirmed_copy` and CLI fixture `unconfirmed_winkel`
  (`TEMPLATE_DIR` pointed at the copy): `test_template_resolution` (TestErrors.test_unconfirmed,
  TestCompatibility.test_unconfirmed_template), `test_map_template_contract` (test_unconfirmed_template),
  `test_recipe_template` (unconfirmed parses; an unconfirmed template is not listed in the
  unknown-template error). Their `pytest.skip` guards are gone (the suite had 4 skips after T081,
  now 1: the packaged price snapshot). `test_packaged_winkel` asserts the owner's confirmation, 0
  corrections and layout SHA-256 389963b5.... The web suite already used `unconfirmed_template_dir`.
- Margin shade (owner, 2026-11-24), test first: `maps/preview.py` `write_preview` draws square-tile
  studs in `lego_black` in the `background` color (both styles, so the square web thumbnails agree)
  unless the layout's `metadata.map.margin.ring` is `lego_black` (a Black ring keeps its cited
  color; ring and margin colors always differ); `BACKGROUND_MARGIN_COLOR`. `palette.js`
  `drawStuds` skips margin cells whose key is `lego_black` and the margin color (the `#000`
  canvas shows); 21.8 kB. Tests: 4 new in `tests/unit/maps/test_preview.py` (Black margin = background
  in round, custom background and square styles; Black margin with a yellow ring: ring 288 yellow,
  1,708 background; White margin with a Black ring: ring cited Black (5, 19, 29); parts list still
  1,996 `lego_black` 3070b), Node harness in `web/tests/test_palette.py` (default Black margin: no
  squares drawn; Black margin + ring: only the 7 ring squares; White margin + Black ring: all
  squares, ring in cited Black). Chromium (Playwright) on the real-data site: all 1,996 margin cells
  of the ocean-sst Winkel canvas pure black after a recolor, no page errors
  (`<scratchpad>/016/scripts/browser_margin_check.js`). Web map-page captions are unchanged
  ("square tiles in the margin": the build still uses them).
- T083 (real data, the package file as is, script `<scratchpad>/016/scripts/t083_builds.py`, outputs
  `<scratchpad>/016/t083/`; 44 steps, all as expected; package files byte-identical afterwards):
  for official-31203-bathymetry, ocean-sst, land-elevation, living-planet and rainfall: 2,553 land /
  5,691 ocean / 1,996 margin each = `template show` (SC-002); 10,240 pieces, 3070b Black 1,996, 0
  unverified lots (SC-003); land <= 3,064 and ocean <= 8,066 (SC-004); layout records the owner's
  confirmation; ETOPO 2022 cited in layout, report and cells.json. Beyond one kit / left over:
  official-31203-bathymetry 1,996 / 2,886, ocean-sst 1,996 / 2,886, land-elevation 6,916 / 7,806,
  living-planet 7,245 / 8,135, rainfall 8,516 / 9,406. Preview, sheets, `validate` and `map cells`
  work; every Black margin stud of each preview is pure black; `--ring-color lego_white` colors 288
  studs; the four step 9 errors exit 1 and write nothing. Final preview:
  `<scratchpad>/016/previews/ocean-sst.winkel.final.png`.
- T105 (real data, committed confirmed template): `python -m web98138.prebuild --out
  <scratchpad>/016/site-final --no-prices`: **29 variants (24 kit + 5 Winkel), 179.7 MB, 64.7 s**;
  `--templates none` into `<scratchpad>/016/site-final-kit`: 24 variants, 151.4 MB, 52.6 s (+23 %
  time, +18.7 % size). Served both with uvicorn; `<scratchpad>/016/scripts/t105_web_check.py`, 154
  checks, all pass (`<scratchpad>/016/t105.json`): `/healthz` 29 and 24; manifest `templates`
  source confirmation is the owner's; `/maps/<map>/winkel-tripel` 200 for the five eligible maps
  with the re-hang note, disclaimer, confirmation date, preview `<img>` and 9 downloads (200, type
  and SHA-256 as the manifest: the page works without JavaScript); preview and thumbnail margin
  studs pure black; cells.json and parts keep `lego_black`; 404 for official-31203, ocean-el-nino
  and ocean-la-nina; about page names Winkel tripel; kit pages of all 8 maps x A, B, C equal
  between the two sites after the web kit golden's normalisation and removing the one Winkel nav
  item on the five eligible maps. Kit variants' files equal between the sites; only top-level
  `part_labels` gains 3070b.
- Final checks (2026-11-24): CLI `cli/.venv/bin/pytest -q` **2216 passed, 1 skipped** (122 s; the
  skip is the packaged price snapshot); web `web/.venv/bin/pytest -q` with Node on PATH **209
  passed** (67 s); CLI `test_kit_outputs_unchanged` and web `test_kit_golden` pass; real-data
  `maptemplates kit-golden` byte-identical to `kit-before.json` (SHA-256 a67b3bd1...;
  `<scratchpad>/016/kit-after-final.json`, 55 s). Docs updated for the confirmation (README.md,
  cli/README.md, web/README.md, docs/deploy.md 29 variants and `/healthz` examples, docs/vision.md,
  quickstart steps 5 and 8, CLAUDE.md and AGENTS.md identically).

## Implementation decisions
- T010 (agent, data correctness; follows the 6141 → BrickLink 4073 pattern): BrickLink no longer
  has an item 3070b. Its catalog URL for 3070b has redirected to a not-found page since 2024-02;
  BrickLink files the design as item 3070 with 3070b as an alternate, and Rebrickable's 3070b page
  cross-references BrickLink 3070. So the pinned BrickLink page is item 3070's and
  `part_numbers.json` records `bricklink.item_no` "3070" (alternates incl. 3070b), Rebrickable
  `part_num` "3070b", LEGO design IDs 3070, 112412, 30039, 35403, 39727, 53836 (Rebrickable's list,
  rule R10). Consequence for later batches: BrickLink wanted lists and price lookups for the
  margin must use item 3070 from part_numbers.json (as 6141 uses 4073), not the literal
  "ITEMID 3070b" written in contracts/cli.md and data-model.md (PartsListLot IDs, BrickLink XML).
  Rebrickable CSV keeps 3070b.
- T015/T016: existing source strings and rules are kept byte-identical; new rules are appended
  (partnumbers `rules`, partcolors `join_rules`); the two files' titles now name the square tile.
  `partcolors.build(..., parts=PARTS)` builds a part subset; `reviewed` keeps its meaning and a
  part it does not name tries every listed color.
- T016 side effect (FR-014 direction, not in the kit golden): owned CSVs now count Rebrickable
  3070b rows as loose square tiles instead of ignoring them, and BrickLink/LEGO numbers of 3070b
  (e.g. 3070) in an owned CSV are rejected like 4073 is for the plate.
- T009 (agent): the web golden covers all three session sites (small, living-planet, rainfall),
  so T089 can compare the eligible maps' kit pages; written with `KIT_GOLDEN_WRITE=1`.
- T025 (agent): the synthetic template's locations come from a numpy Newton inverse of the
  forward formula in tools/maptemplates/testing.py (tests only; the package has no inverse, R1),
  and on-globe from the analytic Winkel outline (`winkel.outline_contains`, the edge meridian).
  The template writer lives in tools/maptemplates/document.py (`to_text`, `ice_to_text`,
  `round_location`); T035 extends that module. If the writer's format changes, regenerate the
  fixture (`PYTHONPATH=tools python -m maptemplates.testing tests/fixtures/templates`) and update
  the `sha256` in both `.source.json` files.
- T029 (agent): the loader checks `source.dataset` against the packaged registry
  (`data/datasets.json` by path), not the active `REGISTRY_PATH`, because the test fixture registry
  repoints ETOPO at a fixture with another SHA-256; the template's provenance is the pinned
  dataset. `source.generator` must start with `cli/tools/maptemplates` (the synthetic records
  `.../testing.py (synthetic test template)`). Extra loader rules beyond the contract table, all
  consistent with it: the fit must equal `winkel.fit` (extent, contain scale, centre, 1e-9); the
  last correction of each stud must match `classes`; `frame` must be exactly the contract's
  (arrangements ["A"]); template ids may not end in `-ice` (reserved for ice files) so listing
  skips `<id>-ice.json` and `.source.json` files.
- T029 (agent): API names for later phases: `Template.grid_projection` (KitProjection for the kit,
  `geometry.TemplateProjection` otherwise), `.status` (reference/confirmed/unconfirmed),
  `.buildable`, `.land/.ocean/.margin/.on_globe/.ring` (read-only masks), `.class_at`, `.part_at`,
  `.section_label`, `.summary()`, `.document()`, `.layout_sha256`, `.file_sha256`, `.dataset`
  (TemplateDataset); `UnknownTemplateError(TemplateError)`; `template_ids()`, `kit_template()`,
  `load_template_file(path)`; `TemplateCorrection.class_` (attribute; `to_dict()` writes `class`).
  The kit's in-code projection block is named `kit-31203-equirectangular` (proj, lat_1, lon_0
  null; fit holds the kit projection's four numbers); its layout digest is taken of that in-code
  document.
- T031/T032 (agent): JSON output (`list`, `show`) carries `disclaimer` as its last key; `locate`
  accepts negative numbers as arguments (`ignore_unknown_options`); usage errors (exit 2) are
  printed by Click without the disclaimer, as for `--arrangement`.

- T035 (agent, finding): research R5 calls the 33-stud water group the Caspian Sea. It is the
  Mediterranean, closed at Gibraltar (rows 21-26, cols 60-71, mean 37.1 N 17.6 E); the Caspian is
  a 9-stud group (42.2 N 51.0 E). Others: Hudson Bay 22, Baltic 6, Black Sea 6, Persian Gulf 3, Red
  Sea in three groups of 2, single studs (White, Irish, Adriatic and Bohai Seas, Canadian Arctic,
  Alaska and Chukotka coasts). research.md is not edited; the counts file for the owner names them.
- T035 (agent): `write` and `build --check` also take `--dataset FILE` and `--cache-dir DIR`
  (they regenerate, like `generate`; the kit31203 `fit-projection --check` pattern); `build`
  without `--check` is a usage error (exit 2); an unknown template id is a usage error. Dataset
  missing or checksum mismatch exits 4 for generate, write and build (the dataset is checked before
  pyproj is imported). The tool always uses the packaged registry entry.
- T035 (agent): output names: `generate` writes `<out>/<id>.json` (loadable candidate),
  `<id>.review.png`, `<id>.flags.json`; `review` writes `<id>.committed-review.png` and
  `<id>.committed-flags.json` (dots keep them from looking like template ids). `review` needs no
  pyproj or dataset, so its flags are only "water not connected to the ocean" (land_share null) and
  it marks the corrected studs.
- T035 (agent): ReviewFlag records have the same six keys for both reasons (`group_size` null for
  land share); a stud can carry both reasons (two records). Land share flags use 0.4 <= share <=
  0.6 on on-globe studs only. The flags JSON adds `rules`, `counts` and `groups` (size, rows, cols,
  sections, mean location). Corrections file for `write --corrections`: a JSON list of
  `{row, col, class, reason}`, or an object with that list under `corrections`. A correction is
  stale when the stud already has that class at its turn in the list.
- T035 (agent): `write` keeps the committed `generated_on` when nothing else changed (idempotent);
  it validates the document with the package loader before writing and notes a stale ice file.
  `generate.spherical_mean` duplicates the one in `testing.py`, which stays unchanged so the
  committed synthetic fixture is untouched.

- Phase 4 API for later phases (agent): `maps/margin.py`: `MarginTreatment(color, ring)` with
  `.provenance(cells)`, `resolve_margin(base, margin_color, ring_color)` (raises `MarginError`
  with `.where`), `ring_cells(template)`, `margin_labels`, `margin_cells`, `margin_colors()`,
  `MARGIN_PART_ID`. `Recipe.template` (id or None) and `Recipe.margin` (MarginTreatment or None =
  table absent; bundled recipes have none, so `recipe.margin or MarginTreatment()` gives the
  default Black for T064's `recipe_lots`). `maps.build.resolve_template(recipe, template)` ->
  (Template, source); `build_map/check_recipe(..., template=, margin=)`; `MapResult.template`
  (always set, the kit too) and `MapResult.margin` (None on the kit). `templates.compatibility(
  recipe, template, arrangement=None)` and `templates.confirmed_text()`;
  `Template.layout_record()` (= `metadata.template`) and `Template.report_record()` (= report
  `template`). `layout.position.MARGIN_PART_TYPE` "square_tile", `MARGIN_PART_ID` "3070b";
  `PositionPlacementGrid(..., template=)`, `.template`, `.margin_positions`;
  `LayoutStatistics.margin_tile_count` (None on the kit). `reproject.TEMPLATE_CHUNK`,
  `template_source_cells`, `_is_template`. `preview.STUD_DIAMETER`, `stud_coverage`, `STYLES`,
  `DEFAULT_BACKGROUND` (main's names since the 6038d9c sync; `SUPERSAMPLE` and `BACKGROUND_COLOR`
  are gone). `cli/options.template_options`; `cli/map.template_lines`,
  `resolve_margin_options`, `echo_template` (for `map cells` in T079/T080).
- Phase 4 (agent): `metadata.map.margin.cells` counts per role: `margin` = studs in the margin
  color, `ring` = studs in the ring color (they sum to the template's margin count). Metadata and
  report `template.counts` hold land, ocean, margin and ring only (`template show` has the rest).
  `margin_positions` follows `ocean_positions` in `metadata`, `margin_tile_count` follows
  `ocean_tile_count` in `statistics`; `metadata.template` is the last metadata key; report
  `template`, `template_source`, `margin` follow `arrangement_source`; `metadata.map.margin`
  follows `shadow`.
- Phase 4 (agent): the template's dataset is appended to `citations` as TemplateDataset
  (`{id, version, title, publisher, license, citation, doi}`) unless a citation with that id is
  already there (land-elevation, living-planet, official-31203-bathymetry cite ETOPO already), so
  it is listed once.
- Phase 4 (agent): `[margin]` colors are checked at recipe parse (RecipeError at `margin.color` /
  `margin.ring`); `--margin-color`/`--ring-color` are checked on every build, kit included (exit 1
  naming the option); a kit build with a `[margin]` table or either option prints one note line
  after the arrangement line and changes nothing else. `--ring-color none` (any case) turns a
  recipe ring off; the recipe itself has no `none` value (omit `ring`).
- Phase 4 (agent): unknown `--template` is a Click usage error (exit 2) naming the confirmed
  templates, without the disclaimer, as for `--arrangement` and T031/T032 (contracts/cli.md lists
  exit 2; T058's "disclaimer last" is asserted for the exit-1 errors). Kit builds, including an
  explicit `--template kit-31203`, print no Template/Margin lines.
- Phase 4 (agent): `--compare-official` on a non-kit template is a MapBuildError (exit 1); the
  automatic comparison for `official-31203*` ids is off there. Error order: unconfirmed,
  kit-design dataset, arrangement, compare-official.
- Phase 4 (agent; superseded 2026-11-23 by the 6038d9c sync, research R13 note): the non-kit
  preview background was the cited Black RGB (5, 19, 29), the same as the Black margin tiles. Note
  for merging main: main's 6038d9c ("Round studs on black for map
  previews") makes round studs the default for kit previews too (diameter 0.9, 8x supersample,
  pure black, `style=` and `--preview-style`); `maps/preview.py` and `cli/map.py` will conflict
  and the kit golden's preview digests were taken before that change.
- Phase 4 (agent): template ice regions are not used by builds (research R6, T049); the recipes'
  ice-sheet and sea-ice rules are overrides and no-data rules, which now use stud locations. No
  ice file was needed in Phase 4.

- Phase 5 (agent): BrickLink IDs come from `part_numbers.json` (item 3070 for the square tile);
  data-model.md (PartsListLot IDs, ExportRow, Part 3070b), contracts/cli.md and
  contracts/recipe-and-outputs.md now say `ITEMID 3070`; tasks T061 likewise. spec FR-014 still says
  "a pinned BrickLink catalog page for item 3070b" (not edited; the page pinned is item 3070's).
- Phase 5 (agent): `parts.partslist.PART_TYPE_TEXT` ("square tile") is how tables, sheets count
  lists and estimate text write `square_tile`; JSON keeps `part_type: "square_tile"`. Kit text is
  unchanged (plate, tile). `PartsList.layout.template`, `sheets counts` `template` (after
  `arrangement`) and the validation report `template` ({id, title}, before `disclaimer`) are
  written for non-kit layouts only. `mask_mismatch` gains `template` (after `arrangement`) only
  when checked against a template.
- Phase 5 (agent): `all_cited_lots()` (`parts prices fetch --all-colors`) now includes every cited
  3070b color (84 -> 132 lots), so the estimate's "fetch every cited color" hint covers the square
  tiles; `recipe_lots()` adds each recipe's margin color and ring (`recipe.margin or
  MarginTreatment()`), 25 -> 26 lots. Fetch tests updated (mocked HTTP only).
- Phase 5 (agent): validation loads the layout's template by id (`metadata.template.id`); an
  unknown id is an error (exit 1). It does not compare the layout's recorded `layout_sha256` with
  the loaded template's: a layout from an older template version is checked against the current
  classes and shows as `mask_mismatch` where they differ.
- Phase 5 (agent): sheets for a non-kit layout: subtitle "Template <id>: 128 x 80 studs, 40
  sections of kit 31203; the frames cannot be re-hung"; arrangement sentence names the template
  and the rule; provenance adds "Template: ..." after the layout SHA-256 and "Template land and
  ocean from dataset ..." after the recipe's datasets, shortened to "(above)" when a layer reads the
  same dataset (land-elevation, living-planet, official-31203-bathymetry). Margin studs are 7 mm
  squares on section pages, 1.2 mm squares on the overview; swatches and count discs are squares.
- Phase 5 (agent): the web prebuild's `_part_labels(rows)` lists the parts the variants' lots and
  leftovers use, in `PART_TYPE` order; a kit-only site keeps exactly 6141 and 98138.

- Phase 6 (agent): the template ice derivation lives in the tool (`tools/maptemplates/ice.py`:
  `land_ice_mask(template)`, `sea_ice_mask(warmest, template)`, `derive`, `read_warmest`,
  `source_block`, `ice_document`, `differences`, `generated_on`), reusing `maps/ice.py`'s
  `in_region`, `LAND_ICE_REGIONS`, `SEA_ICE_RULE`, `IceRegions` and `reproject_layer` on the
  template's `TemplateProjection` (forward binning, `filled` = no ERSST value, as the kit). The kit
  functions in `maps/ice.py` are untouched.
- Phase 6 (agent): `ice-mask` takes `--dataset FILE` and `--cache-dir DIR` like the kit31203
  ice-mask and the other maptemplates commands; it reads the ERSST entry from the active registry
  (`get_entry`, the kit31203 ice-mask pattern) so tests can pin a small 12-month file; a missing
  file or checksum mismatch exits 4 (as generate/write/build). It works on any template file but the
  kit (`kit-31203` and unknown ids are usage errors, exit 2; the kit's points to `kit31203
  ice-mask`), confirmed or not. `--check` compares every field but `source.generated_on` and lists
  `difference: <path>` lines (cells as counts only in either file, with the first index); a
  rewrite keeps the committed `generated_on` when nothing else changed. File text: `ice_to_text`
  (each `cells` list on one line, as the synthetic fixture).
- Phase 6 (agent): ice file `source` keys: title, generator `cli/tools/maptemplates ice-mask`,
  generated_on, template_layout_sha256, land_ice {rule, regions, locations}, sea_ice {rule,
  variable, reduce, max_value, unobserved_lat, dataset {id, version, url, sha256, citation,
  license}}, disclaimer. `load_template_ice(template)` (`maps/ice.py`) reads `<id>-ice.json`
  beside the template file (`template_ice_path`), cached by path, mtime and size, and raises
  `TemplateIceError` (a ValueError) naming the file and rule: format_version, template_id, the
  disclaimer, `template_layout_sha256` equal to the template's (message says how to remake it),
  grid size, counts, cells in range and on L (land ice) or O (sea ice). For the kit it returns
  `load_ice_regions()`.
- Phase 6 (agent): template `cells.json` key order: format_version, recipe, arrangement,
  **template**, width, height, cells, layers, shadow, **margin**, ice, palette, note, disclaimer
  (template after arrangement and margin after shadow, as in the report and metadata).
  `template.dataset` holds id, version, citation, license only (data-model.md); `margin.ring` is
  `{color, cells}` with the ring cells (row-major) or null; palette parts are the template's land,
  ocean, margin parts. `map cells` prints the Template and Margin lines after the arrangement line
  and "Ice regions: ... (winkel-tripel-ice.json)"; kit text unchanged. A missing or stale ice file
  is exit 1 ("Cannot write the cells of <recipe>: ..."), nothing written.

- Phase 7 (agent): `web98138.TEMPLATES = {"winkel-tripel": "Winkel tripel"}` (id -> the name on map
  pages, `templates[].projection`); `--templates` takes ids from it or `none`; unknown ids,
  `kit-31203`, an empty list or `none` mixed with ids are usage errors (exit 2). The default
  builds every one the library loads as confirmed. An unconfirmed template (default or named)
  gives no variants and one note line ("Template <id>: not confirmed by the project owner, ..."),
  exit 0; an ineligible map prints "<map> <id>: skipped (<compatibility reason>)". Eligibility is
  `templates.compatibility(recipe, template)` only (`prebuild.template_reason`).
- Phase 7 (agent): manifest: `templates` (keys as contracts/web.md; `rehang` = more than one
  arrangement; `source` = {sha256, confirmation}) and `maps[].template_variants` are written only
  when a template variant was built (a kit-only manifest has neither key). A template variant
  entry has the kit entry's fields plus `template`, `margin` (the report's), and the `layers` and
  `citations` of its own report (the page shows the template's layer counts and cites ETOPO);
  its preview description says "square tiles in the margin". Template variants are built after a
  map's kit variants; the map row's layers and citations stay the kit's.
- Phase 7 (agent): catalog: `all_variants`, `MapEntry.template_ids`, `variant(key)` for both kinds,
  `Catalog.templates`/`template(id)`, `variant_count` counts both (healthz 10 on the test site);
  `templates` entries need the contract's keys, unique ids, never A, B or C.
- Phase 7 (agent): map page: the Winkel item is the last `<li class="combo-template">` of the
  combination list ("Winkel tripel" / "curved map", after a separator); a template page changes
  title, description, preview alt, figcaption (projection, board, counts, "Round studs for land and
  ocean, square tiles in the margin"), adds the re-hang note, "Downloads for the Winkel tripel
  version", the parts note on square tiles, a Margin line, its own layers and citations, and the
  template file's SHA-256 and confirmation. Kit pages gain only the nav item (written so that
  removing it leaves main's HTML). About page: a templates section only when the manifest lists
  templates. The home page is unchanged (no Winkel cards).
- Phase 7 (agent): web kit golden: `kit_golden.strip_template_nav` removes the Winkel nav item from
  kit pages of maps with a template variant (exactly once, else the test fails; maps without one
  must have none) and `compare` allows `part_labels` + {3070b} only when the site has template
  variants. For a site without template variants (main's) it digests as before, so the golden can
  still be written from an unmodified main. `test_routes.py` checks the same per page.
- Phase 7 (agent): palette.js: `drawStuds(ctx, data, keys, rgbOf, px, diameter)` (exported for the
  Node tests) draws rounds on black and `M` cells as full 10 px squares (as preview.png);
  `cellColors` gives `M` the ring color on `margin.ring.cells`, else `margin.color`; ice flags skip
  `M`; the ice note adds that the margin's square tiles keep their color. 21.3 kB (limit 30 kB).

- Phase 9 (agent): AGENTS.md's tools line gains `fixtures011` as well as `maptemplates` and
  `projection_study`, so the two files carry the same `cli/tools/` list; nothing else outside
  the 016 paragraph, the intro sentence on Winkel and the `templates/` Layout entry was changed
  (AGENTS.md still lacks the 011 paragraph and `prices/`, as on main). cli/README.md lot counts
  corrected to the code: the default `parts prices fetch` set is 26 lots (the README said 19, from
  before 012/013) and `--all-colors` 132 (84 before the square tile). docs/deploy.md gets one
  paragraph (Dockerfile unchanged, no new build dependency, 24 variants until a confirmed template
  is committed, then 29, deploy is the owner's step); docs/runbook.md is unchanged.

- T110 (agent): which parts an owned CSV is read for follows the layout's positions (a 3070b
  position adds the square tile), not `metadata.template`; the two coincide (every template
  layout has margin tiles). `parse_owned_csv`/`parse_owned_text(parts=None)` default to the kit's
  two parts, main's behaviour for library callers; an unknown part id is a ValueError. The CLI
  reads the layout first (as before) and passes `owned_parts(layout.grid)`. cli/README.md
  `--owned` gains two lines on 3070b rows. The harness lives in `cli/tests/` (a test helper with a
  `__main__`, like `winkel_layouts.py`), not a new maintainer command.
- T111 (agent): the ring = margin error lists every 3070b color key (as the not-a-color error),
  margin color included; text "the ring color X must differ from the margin color Y (1x1 square
  tile, part 3070b); available: ...; see `kit part-colors --part 3070b`".

## Owner tasks still open
- T002: remove the constitution's Sync Impact Report comment at the branch's first commit.
- T109: refresh the BrickLink price snapshot with the owner's credentials (Winkel estimates are
  incomplete until then).
- Deploy (`fly deploy`) is the owner's, after the commit.

## Blocked tasks
- none

## Deferred findings
- none

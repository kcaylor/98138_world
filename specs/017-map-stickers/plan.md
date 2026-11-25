# Implementation Plan: Map stickers

**Branch**: `017-map-stickers` | **Date**: 2026-11-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/017-map-stickers/spec.md`

## Summary

Add a `stickers` package to the CLI library and a `map stickers` command that build a map from
its recipe (like `map cells`) and make one sticker set: a small sticker (45.8 mm square) for a
Black tile 6×6 and a large one (125.8 × 61.8 mm) for a Black tile 8×16, as a one-page print
sheet (PDF, Letter or A4) with bleed, cut marks, plaque parts and full citations, or one SVG per
sticker. The legend comes from the built classes (recipe bins, rank boundaries from the helper
`map_cells` already uses, background roles, override and no-data names, the shadow), rounded so
combinations A, B and C give the same set. Text comes from an optional recipe `[sticker]` table,
which the eight bundled recipes get after the owner approves the drafted lines. The four plaque
parts get cited IDs in a new package file made by the partcolors maintainer tool. The web
prebuild writes each map's set once and the map pages show and offer it (P2). After feature 016
merges, stickers name the template's projection, template variants get their own sets, and a
Winkel build can place the small plaque in a margin corner (P3).

## Technical Context

**Language/Version**: Python 3.11 (CLI, tools, web); no JavaScript change

**Primary Dependencies**: existing only (reportlab for PDF and font metrics, numpy, Click;
FastAPI, Jinja2 on the web). No new runtime, web, build or maintainer dependency; no font file

**Storage**: package JSON `data/plaque_parts.json` (about 6 kB); bundled recipe TOML files gain a
`[sticker]` table; prebuilt static files on the web

**Testing**: pytest (cli unit, integration, contract; web offline); page-model tests without
rendering; pypdf (existing dev dependency) reads PDFs; golden digests for the refactored
renderers and `cells.json`, taken before any code change

**Target Platform**: CLI on macOS/Linux; Fly.io service; current browsers; home printers on
white sticker paper and print-and-cut machines

**Project Type**: CLI + library + maintainer tool + web service

**Performance Goals**: a sticker set in < 5 s more than the map build (SC-007; measured builds
0.1–4 s, composing and rendering are small vector pages); web output + < 2 MB (SC-008; about
50 kB per map)

**Constraints**: same input, same bytes; PDF standard Helvetica (Latin-1), SVG text in
Helvetica/Arial with `textLength`; no images, logos or LEGO artwork; every other output
unchanged except the recorded recipe checksum (FR-017, SC-006); tests offline; the service never
imports `lego_image_processor`; the 31203 PDF and crops never committed

**Scale/Scope**: 8 bundled maps (+5 Winkel variants after 016), 4 plaque parts, 1 new command
and 1 new option (`--plaque`, P3); about 35 files touched

## Constitution Check

*GATE: checked before Phase 0 and again after Phase 1 design.* US1 and US2 are checked against
constitution 2.0.0 (this branch); US3 against 3.0.0, which arrives with feature 016.

| Principle | How the plan meets it | Status |
|---|---|---|
| I. Kit is a fixed template (2.0.0) / Templates fix the canvas (3.0.0) | Stickers change no grid, mask, part or color of any map. US3 (3.0.0 only): 3.0.0 asks for "one part type per class" and that "within a template the layout and parts MUST NOT change between maps"; it also says "maps vary only the colors in each class and the content of the margin" and "Margin cells SHOULD use square pieces, to set them apart from the round map pieces, and hold labels or a background". The plaque is margin content, a label: it sits on 36 margin cells, the margin class's part type stays 3070b on every other margin cell, the land and ocean classes and the layout do not change, and the plaque is optional per build. The kit template rejects `--plaque`. Plaque part data is versioned package data citing its sources. | Pass (US3: close call, recorded below; no Complexity Tracking entry) |
| II. Maps are layers defined by recipes | `[sticker]` is an optional, declarative, additive table; recipes stay fully reproducible; `official-31203` still reproduces the design exactly (only an appended table). | Pass |
| III. Data in, not pictures | Legends come from the built classes and recipe bounds; stickers contain no image. | Pass |
| IV. Reproducible data acquisition | No new dataset. Large sticker credits each dataset; the print sheet (and JSON) carries each full citation and license, which covers the small sticker. Plaque sources pinned by SHA-256; the one-time fetch of four archived BrickLink pages is a maintainer step; every command works offline. | Pass |
| V. Buildable and honest outputs | Plaque parts in Black with LEGO, BrickLink and Rebrickable IDs from pinned sources, checked with `--check`; "printed, not a LEGO part" and "colors only approximate" notes; legend values never invented (bins from the recipe, rank from the build); US3 tile as a cited lot, unpriced when the snapshot lacks it. | Pass |
| VI. CLI-first, open-source ready | Library `stickers.sticker_set` and `map stickers` first; the web prebuild calls them; the service serves files only. No secrets or endpoints. | Pass |
| VII. Test-first, offline tests | Tests and golden digests first in every phase; fixtures only (synthetic catalog pages); no network. | Pass |
| VIII. LEGO compliance | Disclaimer on both stickers, the print sheet, SVG `<desc>`, JSON, CLI output and the web page; no logo, wordmark or label artwork; part numbers for buyers only. | Pass |
| Technical constraints | Python 3.11+, Poetry, Click; runtime data in `cli/src/lego_image_processor/data/`. | Pass |
| Development workflow | Stories in priority order; P1 (CLI stickers for every map) is a usable MVP; this check is filled in. | Pass |

No violations; Complexity Tracking is empty. Re-check after Phase 1: the design adds no
dependency, keeps `part_colors.json` and `part_numbers.json` untouched, keeps kit outputs
byte-identical except the recipe checksum, and puts no personal data in committed files.
Still Pass.

## Project Structure

### Documentation (this feature)

```text
specs/017-map-stickers/
├── spec.md, run-state.md, checklists/
├── plan.md                         # this file
├── research.md                     # R1–R17 decisions and evidence, R6 drafts for the owner
├── data-model.md
├── contracts/
│   ├── recipe-sticker.md           # [sticker] table; US3 [margin].plaque
│   ├── cli.md                      # map stickers; US3 --plaque; maintainer tool; library
│   ├── sticker-files.md            # geometry, print sheet PDF, SVG, JSON summary
│   ├── plaque-parts-file.md        # data/plaque_parts.json and its rules
│   ├── web.md                      # prebuild, manifest, catalog, routes, page
│   └── in-margin-plaque.md         # US3 additions to 016's outputs
├── quickstart.md
└── tasks.md                        # next phase
```

### Source Code (repository root)

```text
cli/src/lego_image_processor/
├── stickers/                       # new package
│   ├── __init__.py                 # sticker_set, StickerSet, StickerError, print_sheet, render_*
│   ├── geometry.py                 # pitch, tile, cut, bleed, marks, safe area (cited)
│   ├── text.py                     # title/line resolution, number formatting, wrap-and-shrink fit
│   ├── legend.py                   # Swatch/Meaning from a MapResult; display step
│   ├── credits.py                  # data credits and full citations
│   ├── compose.py                  # the two stickers and the print sheet as page models
│   └── render.py                   # PDF (shared item drawing), SVG (textLength, cut line), JSON
├── kit/plaque_parts.py             # new: load_plaque_parts(), Plaque, PlaquePart
├── data/plaque_parts.json          # new: four Black parts, cited
├── maps/recipe.py                  # + [sticker] table, StickerText, Recipe.sticker
├── maps/cells.py                   # derived_bounds(), variable_units() made public; output unchanged
├── maps/recipes/*.toml             # + [sticker] appended after the owner approves (R6)
├── sheets/render_pdf.py, render_svg.py   # item drawing moved into shared helpers; output unchanged
└── cli/map.py                      # + `map stickers`
cli/tools/partcolors/plaque.py, __main__.py   # new subcommand `plaque-parts [--check]`
cli/tests/
├── fixtures/golden/stickers_017_guard.json (+ .source.json)   # taken before code changes (R13 G3)
├── fixtures/plaque/                # synthetic catalog pages, elements.csv excerpt (+ .source.json)
├── unit/stickers/                  # geometry, text, legend, credits, compose, render
├── unit/test_plaque_parts.py, unit/maps/test_recipe_sticker.py, unit/tools/test_plaque_parts_tool.py
├── integration/test_stickers_bundled.py          # 8 maps: fit, A/B/C identity, sizes, no images
├── integration/test_stickers_outputs_unchanged.py  # G1 prefix, G2 checksum-only, G3 golden, G4 palette
└── contract/test_map_stickers_contract.py (+ disclaimer contract)
web/src/web98138/
├── prebuild.py                     # + sticker set per map (and per template variant after 016)
├── catalog.py                      # + sticker kinds and checks
├── app.py                          # + sticker image and download routes
├── templates/map.html, about.html  # + Stickers panel, about paragraph
└── static/style.css                # + sticker figures
web/tests/test_stickers.py          # manifest, routes, page, no-JS, variant files unchanged
README.md, cli/README.md, docs/vision.md, web/README.md   # docs (implement phase)
```

After 016 (US3 and template stickers): `maps/margin.py` (plaque placement in 016's margin
treatment), `cli/options.py` (`--plaque`), `layout/grid.py` and `layout/validator.py`
(`metadata.plaque`, absent positions), `maps/preview.py`, `maps/cells.py` (`P` cells),
`parts/partslist.py` and `parts/export.py` (lot 10202), `prices/lots.py`,
`sheets/compose.py`, `sheets/legend.py`, `sheets/counts.py`.

**Structure Decision**: the existing two-part layout (CLI package `cli/`, web `web/`); stickers
are a new library package beside `sheets/`, reusing its page model, text metrics, furniture and
backends; plaque part data is its own package file made by the existing `partcolors` tool.

## Phases (for tasks.md)

0. **Guards first** (research R13): G1 test of the af3ce57 recipe SHA-256s (passes now); G3
   golden digests of sheets PDF/SVG and `cells.json` from the unchanged code; G4 palette test.
1. **Plaque part data** (US1 prerequisite, test first): fixtures, loader rules, the
   `plaque-parts` tool with `--check`; maintainer pins the four archived BrickLink pages
   (network, once). Stop only if a pinned page is unusable (owner gives another source).
2. **Recipe sticker table** (test first): parser, errors, fallback; recipes without it unchanged.
3. **Legend and text** (test first): public `derived_bounds`/`variable_units` (G3 passes),
   display step, labels, merged swatches, credits, title/line resolution.
4. **Layout** (test first, page model): geometry, wrap-and-shrink fitting, both stickers, print
   sheet on Letter and A4, errors with sizes.
5. **Renderers**: shared PDF item drawing and SVG item serialiser (G3 passes), sticker PDF, SVGs
   with `textLength` and the cut-line group, JSON summary; determinism.
6. **CLI** (contract tests first): `map stickers` with `--format pdf|svg|json`, `--paper`,
   `--cache-dir`; errors; output text.
7. **Stop: owner approves the eight sticker texts** (research R6), shown with sample print
   sheets made outside the repository from cached real data. Then append the tables; G1, G2,
   "no Official in bundled sticker titles", all-maps fit and A/B/C identity tests pass.
8. **Web (US2)**: prebuild, manifest, catalog, routes, page, CSS; web tests (variant files
   unchanged, no-JS, alt text).
9. **After 016 merges**: rebase; re-read 016's merged contracts. (a) `map stickers --template`,
   FR-025 text and credit; (b) template sticker sets on the site (FR-020); (c) US3 in-margin
   plaque: `--plaque` and `[margin].plaque`, placement checks, layout, preview, parts, exports,
   prices, sheets, counts, `validate` and `map cells` (no `palette.js` change: no site variant has
   a plaque). **Stop: owner reviews a
   Winkel preview with the plaque in each corner** before the offset is final. Regenerate 016's
   kit golden if 017 merges second (R13).
10. **Docs and final checks**: README files, vision row, CLAUDE.md/AGENTS.md paragraph;
    quickstart steps; full CLI and web test runs.

## Spec notes and escalations

1. **Decided (agent): JSON output (E1).** FR-015 asks for the command's "text and JSON output", but
   FR-016's signature has `--format pdf|svg` only. Decision: add `json` to `--format` (the
   summary the web also lists, like `parts list --format json`). Alternative: write
   `stickers.json` next to the SVG files.
2. **Decided (agent): a recipe plaque on the kit (E2, US3).** FR-021 says a plaque on the kit template
   stops the build; 016's contract ignores `[margin]` settings on kit builds with a note.
   Decision: `--plaque CORNER` on the kit is an error; the recipe key `[margin].plaque` on a
   kit build is ignored with 016's note, so such a recipe still builds on the kit.
3. **Decided (agent, close call): plaque part data in its own file** (R10). FR-014 says "added
   to the packaged part data"; the plan adds `data/plaque_parts.json`, made and checked by the
   same `partcolors` tool, instead of rows in `part_colors.json`/`part_numbers.json`, because
   those rows would change every `cells.json` palette, loose-parts matching and
   `kit part-colors` output, and would collide with 016's 3070b rows.
4. **Decided: display step 100 m for bathymetry** (R8). The spec's "10 m are enough" holds on
   real data but not on the test fixtures (2,296 vs 2,292 m); two significant digits of the
   built range (1 °C, 100 m) keep A, B and C identical on both.
5. **Decided (agent, close call): the `official-31203` credit** (R9) reads "Official LEGO 31203 World Map design
   grid, Extracted by this project (feature 003)" from the registry (FR-007): it says "Official"
   and names a project feature. Changing the registry title would change kit outputs, so the
   sticker table gets an optional `credit` line that replaces the large sticker's "Data:" lines
   only; the print sheet keeps every registry citation (constitution IV). `official-31203` sets
   one (draft in R6), which follows the owner's "drop Official" decision; the owner approves it
   with the other texts.
6. **Decided: sources** (R1, R10). The 0.1 mm tile clearance is not in LDraw (the 1 mm inset
   absorbs it); Rebrickable part pages are not all archived (10202 is not), so Rebrickable part
   numbers and LEGO design IDs come from the pinned `elements.csv`, BrickLink IDs from four
   archived catalog pages (all available).
7. **Close call: constitution 3.0.0 and US3.** The plaque is read as margin content (a label),
   which 3.0.0 Principle I allows; the margin class's part stays 3070b.
8. **Owner steps** (not escalations): approve the eight sticker texts (phase 7, blocking the
   recipe change); provide another pinned source if a BrickLink copy is unusable (only if
   needed); review the corner offset preview (phase 9); refresh the price snapshot with BrickLink
   credentials to price lot `10202:26` (optional; estimates stay incomplete until then).
9. **Merge order with 016** (R13): whichever merges second regenerates 016's kit and web golden
   digests after G1 and G2 pass.

## Complexity Tracking

None.

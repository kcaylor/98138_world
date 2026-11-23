# Implementation Plan: Palette chooser and ice toggle on the map pages

**Branch**: `015-palette-chooser` | **Date**: 2026-11-22 | **Spec**: [spec.md](spec.md)

## Summary

Add a library function and CLI command (`map cells`) that export, for a built map as hung, the
per-cell classes and values, default bounds, the land shadow, the ice regions and the cited part
colors (with L*). Package the ice regions as cited reference data (`kit_31203_ice.json`) with a
maintainer tool to regenerate and check it. The web prebuild writes `cells.json` per variant and
lists it in the manifest; the service serves it and a hand-written first-party script
(`/static/palette.js`) that recolors a canvas preview, edits classes and bounds, toggles ice, and
keeps its state in the URL fragment. Nothing downloadable or priced changes.

## Technical Context

**Language/Version**: Python 3.11 (CLI and web); browser JavaScript (ES2017, no build step)
**Primary Dependencies**: existing only (numpy, scipy, Click; FastAPI, Jinja2). No new dependency.
**Storage**: static files (prebuild output); packaged JSON reference data
**Testing**: pytest (cli unit/integration/contract; web offline); the script's pure functions are
also exercised by a pytest test that runs Node when available (skipped otherwise)
**Target Platform**: CLI on macOS/Linux; Fly.io service; current browsers
**Project Type**: CLI + web service
**Performance Goals**: recolor 10,240 studs < 100 ms; `cells.json` < 300 kB; script < 30 kB
**Constraints**: works without JS; CSP `script-src 'self'; connect-src 'self'`; no cookies/storage;
service never imports `lego_image_processor`
**Scale/Scope**: 6 maps × 3 combinations = 18 `cells.json`

## Constitution Check

| Principle | Status |
|---|---|
| I. Kit is a fixed template | Pass: grid, mask and parts unchanged; only colors within each class vary, from the part's cited colors |
| II. Layers defined by recipes | Pass: the chooser starts from the recipe's classification and colors; recipes are not changed |
| III. Data in | Pass: custom bins classify the reprojected data values, not pictures |
| IV. Reproducible data | Pass: ice regions are packaged, cited and regenerable with `--check` from the pinned ERSST file; no new dataset |
| V. Buildable and honest | Pass: only cited colors offered; preview-only note; parts/prices/sheets untouched |
| VI. CLI first | Pass: `map cells` and the library function come first; the web only recolors prebuilt values |
| VII. Test-first, offline | Pass: tests written first with existing fixtures; no network |
| VIII. LEGO compliance | Pass: disclaimer on the page, in `cells.json` and CLI output |

No violations; Complexity Tracking empty.

## Project Structure

```text
cli/src/lego_image_processor/
├── data/kit_31203_ice.json          # new: ice regions (kit coordinates), cited
├── maps/ice.py                      # new: ice rules, load/roll the packaged regions
├── maps/cells.py                    # new: map_cells(result) -> dict (FR-001)
├── datasets/readers.py              # + reduce "monthly-max" (warmest month) for the tool
└── cli/map.py                       # + `map cells`
cli/tools/kit31203/__main__.py       # + `ice-mask [--check]`
cli/tests/unit/maps/test_ice.py, test_cells.py; tests/contract/test_map_cells_contract.py;
cli/tests/unit/datasets/ (monthly-max)
web/src/web98138/
├── prebuild.py                      # + cells.json per variant (kind "cells")
├── catalog.py                       # + kind "cells" (not a download)
├── app.py                           # + route cells.json, /static/palette.js, CSP
├── templates/map.html, about.html   # + chooser markup, noscript note, about text
└── static/palette.js, style.css     # new script; chooser styles
web/tests/test_palette.py (+ updates to test_routes/test_security for FR-020)
```

## Phases

1. Ice regions (rules, packaged data, tool, tests).
2. `map_cells` + `map cells` (tests first).
3. Prebuild/catalog/app (tests first).
4. Template, script, CSS; Node-backed script test.
5. Docs (CLAUDE.md, AGENTS.md, vision, web README, 008 FR-009 amendment note, CLI README).

## Complexity Tracking

None.

# Implementation Plan: Web App (pick, preview, download)

**Branch**: `008-web-app` | **Date**: 2026-11-22 | **Spec**: [spec.md](spec.md)

## Summary

A new top-level `web/` project, package `web98138`, with two halves:

1. **Prebuild** (`python -m web98138.prebuild`, wrapped by `web/scripts/prebuild.py`): imports
   `lego_image_processor` and, for each of the 4 bundled recipes × 3 combinations, calls the same
   library functions as the CLI (`load_recipe`, `build_map`, `write_preview`, `build_parts_list`,
   `to_bricklink_xml`, `to_rebrickable_csv`, `build_sheet_set`, `render_pdf`) to write every file
   into an output directory, then writes `manifest.json` (files with size, SHA-256, content type;
   tool versions; recipe and dataset checksums; the page data: descriptions, layers, citations,
   warnings, parts totals and lots). Missing pinned datasets are fetched (verified) only here.
2. **Service** (`web98138.app:create_app`): FastAPI + Jinja2. Loads and checks the manifest at
   start-up, then renders pages from the manifest and serves files listed in it. It does not
   import `lego_image_processor` at all.

The Docker image is multi-stage: the build stage installs the CLI and runs the prebuild; the
runtime stage installs only the web service (FastAPI, Starlette, Jinja2, uvicorn), copies the
output, and runs uvicorn as a non-root user on port 8080.

## Technical Context

**Language/Version**: Python 3.11 (the CLI pins scikit-image 0.21, wheels for ≤3.11)
**Primary Dependencies**: FastAPI (MIT) on Starlette (BSD-3), Jinja2 (BSD-3), uvicorn (BSD-3);
test only: pytest (MIT), httpx (BSD-3), pypdf (BSD-3); build stage: the CLI's existing deps
**Storage**: files only: the prebuilt output directory and its `manifest.json`
**Testing**: pytest in `web/tests/` with Starlette's TestClient, offline; fixture output built by
the prebuild itself from `official-31203` (no dataset) and `ocean-sst` with the CLI's small
dataset fixture
**Target Platform**: Linux container on Fly.io, shared-cpu-1x, 256 MB; local macOS for development
**Project Type**: web service (server-rendered), second project beside `cli/`
**Performance Goals**: pages < 200 ms at the server (template render from in-memory manifest);
static files streamed from disk
**Constraints**: runtime memory ≤ 150 MB (SC-004), no network at runtime, no cookies, no JS
required, no third-party resources
**Scale/Scope**: 4 maps × 3 combinations = 12 variants, ~10 files each (~45 MB output)

## Constitution Check

| Principle | Check |
|---|---|
| I. Kit is a fixed template | Pass: nothing about the template changes; the web shows library outputs |
| II. Recipes | Pass: the bundled recipes are built as-is |
| III. Data in | Pass: no change |
| IV. Reproducible data | Pass: datasets fetched only in the build step, verified by SHA-256; citations and licenses on pages and in the manifest; manifest records dataset checksums |
| V. Buildable and honest | Pass: parts summary and exports come from the 005 library unchanged; suitability warnings shown |
| VI. CLI first, web never duplicates | Pass: every file and number comes from library functions that back existing CLI commands (`map build`, `parts list/export`, `sheets build`); the service only formats manifest data. No CLI-only logic needed refactoring (see research.md R3) |
| VII. Test first, offline | Pass: web tests written first, offline, using the prebuild on fixture data; CLI suite must stay at 965 passing |
| VIII. LEGO compliance | Pass: footer disclaimer on every page; manifest carries it; no LEGO artwork |

Technical Constraints: the constitution defers the web stack to this feature; it is set here
(FastAPI + Jinja2, one service, Fly.io). The CLI remains Poetry/Click; `web/` uses the same
`poetry-core` build backend.

No violations; Complexity Tracking empty.

## Deployment recommendation (owner asked)

- `auto_stop_machines = "stop"`, `auto_start_machines = true`, `min_machines_running = 0`:
  the cheapest option for a hobby site; the first visit after idle waits for the machine to boot
  (about 1–3 s: the runtime image has no NumPy/SciPy, so start-up is fast). Switch to
  `min_machines_running = 1` if cold starts bother you (one always-on shared-cpu-1x 256 MB
  machine).
- Region `sjc`. App name `world-98138`.

## Project Structure

### Documentation (this feature)

```text
specs/008-web-app/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md, tasks.md, run-state.md
├── contracts/routes.md
└── checklists/requirements.md
```

### Source Code

```text
web/
├── pyproject.toml                 # poetry-core; runtime deps only; CLI as a dev path dependency
├── requirements.txt               # pinned runtime deps for the container
├── README.md
├── scripts/prebuild.py            # thin wrapper: python -m web98138.prebuild
├── src/web98138/
│   ├── __init__.py                # version, DISCLAIMER, REPO_URL
│   ├── catalog.py                 # manifest load + start-up check, lookups (no CLI import)
│   ├── app.py                     # create_app(): routes, headers, templates
│   ├── prebuild.py                # build step (imports lego_image_processor)
│   ├── templates/                 # base, home, map, about, error
│   └── static/style.css
└── tests/
    ├── conftest.py                # session fixture: prebuild a small output offline
    ├── test_prebuild.py
    ├── test_catalog.py
    ├── test_routes.py
    └── test_security.py
Dockerfile, .dockerignore, fly.toml   # repository root (build context needs cli/ and web/)
docs/deploy.md
```

**Structure Decision**: `web/` is a separate project so the CLI stays a clean open-source package;
the container build context is the repository root.

## Complexity Tracking

None.

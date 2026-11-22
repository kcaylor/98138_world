# Tasks: Web App (008)

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/routes.md
Tests first: each implementation task follows its failing test.

## Phase 1: Setup

- [x] T001 Record baseline: `cd cli && .venv/bin/pytest -q` (965 pass)
- [x] T002 Create web/pyproject.toml, web/requirements.txt, web/src/web98138/__init__.py, web/README.md, .gitignore entry for web/site-output; venv `web/.venv` with `-e ../cli -e .` and test deps (FR-020)

## Phase 2: Foundational (prebuild + catalog)

- [x] T003 Test fixture in web/tests/conftest.py: session-scoped prebuild of official-31203 (A,B,C) and ocean-sst (A,B,C) with the CLI's small dataset fixtures, offline (FR-016)
- [x] T004 Tests in web/tests/test_prebuild.py: files per variant, manifest fields, sizes and SHA-256 match, tool versions, dataset checksums, nothing-to-buy top-up has no file, bytes reproducible across two runs except generated_at, unknown map/combination is a usage error, missing dataset without --fetch is an error (FR-014, FR-015, FR-016, FR-006)
- [x] T005 Implement web/src/web98138/prebuild.py and web/scripts/prebuild.py using only library functions (FR-011, FR-013, FR-014, FR-015)
- [x] T006 Tests in web/tests/test_catalog.py: load ok; missing manifest, wrong format, missing file, wrong size, path escaping the output, missing combination → CatalogError (FR-018, FR-021)
- [x] T007 Implement web/src/web98138/catalog.py

## Phase 3: US1 + US2 pick, see, switch combination (P1)

- [x] T008 [US1] Tests in web/tests/test_routes.py: home lists the maps with thumbnails and links; map page shows preview, description, layers, citations/licenses, warnings, parts summary, lots table with IDs, Rebrickable acknowledgement; footer on every page; one h1; lang; alt text (FR-002, FR-003, FR-008, FR-010)
- [x] T009 [US2] Tests: A/B/C links, aria-current on the current one, combination description, lowercase redirect, unknown combination 404, /maps/{id} redirect (FR-004, FR-021)
- [x] T010 [US1] Implement web/src/web98138/app.py, templates (base, home, map, error) and static/style.css (responsive, pixelated previews, no JS)

## Phase 4: US3 downloads (P1)

- [x] T011 [US3] Tests: every download kind → 200, content type, attachment filename, bytes match manifest SHA-256; layout parses as schema 2.0 128×80; XML parses with INVENTORY/ITEM; CSV header Part,Color,Quantity; PDF opens with pypdf and ≥42 pages; images inline png; unknown kind 404; nothing-to-buy message (FR-005, FR-006, FR-012)
- [x] T012 [US3] Implement download and image routes in app.py, downloads list in map template

## Phase 5: US4 About (P2)

- [x] T013 [US4] Tests: About explains A/B/C with frame orders and centres, cites pp. 7–8, links the repo, says no cookies/analytics (FR-007)
- [x] T014 [US4] Implement templates/about.html

## Phase 6: US5 deploy and operate (P2)

- [x] T015 [US5] Tests in web/tests/test_security.py: security headers and CSP on pages and files, no Set-Cookie, no third-party URLs in pages (only the repo/citation links as <a>), cache headers, docs routes disabled, www host redirect, healthz JSON, manifest.json, robots.txt, path traversal attempts 404 (FR-009, FR-017, FR-019, FR-021, FR-022; the service modules do not import lego_image_processor)
- [x] T016 [US5] Implement headers middleware, healthz, manifest, robots in app.py
- [x] T017 [US5] Write Dockerfile (multi-stage, pinned base, non-root, prebuild at build), .dockerignore, fly.toml (FR-023, FR-024)
- [x] T018 [US5] Write docs/deploy.md: fly apps create, deploy, certs, Hover DNS records, docker smoke test (FR-024)

## Phase 7: Polish

- [x] T019 Full local check: prebuild all 12 variants from the cached datasets (time, size), run uvicorn, curl every route, parse a downloaded PDF/XML/CSV, measure RSS (SC-002, SC-004, SC-005, SC-006)
- [x] T020 Screenshots of home and one map page with headless Chrome into the session scratchpad e2e008/
- [x] T021 Docs: README (root, web), CLAUDE.md/AGENTS.md project sections, docs/vision.md roadmap row 008, docs/runbook.md web section
- [x] T022 Re-run both test suites; CLI stays at 965 passing

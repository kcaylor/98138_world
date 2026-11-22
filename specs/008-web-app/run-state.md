# Run state: 008 web app

Source: prompt (owner brief with decisions 1–6, relayed by the coordinating agent, 2026-11-22).
Fallback 2B without a question round: the brief settled outcome, scope, constraints and priority;
the owner decisions are recorded as user-confirmed in the spec's Clarifications.
Phase: done
Status: done (committed locally on 008-web-app; not deployed; awaiting owner review)
Updated: 2026-11-22

## Open questions

(none blocking; see decisions marked FOR OWNER REVIEW)

## Decisions
- specify: branch `008-web-app` created with `git checkout -b` from main a5542f3 (agent)
- owner decisions 1–6 (scope, stack, prebuilt outputs, Fly.io, footer/privacy/design, security) (user)
- clarify: URL scheme `/maps/<id>/<A|B|C>`, `/maps/<id>` → 307 to A, lowercase → 301 (agent)
- clarify: build sheets in US Letter AND A4 (two PDFs per variant). CLOSE CALL, FOR OWNER REVIEW:
  the brief named one PDF; adds ~23 MB to the image (agent)
- clarify: `www.98138.world` gets a certificate and is 301-redirected to the apex by the app (agent)
- clarify: `/healthz` JSON; `/manifest.json` public (agent)
- clarify: the runtime image does not contain the CLI library; the build stage runs it and the
  runtime copies the output. Every file and number shown comes from the library (constitution VI)
  (agent)
- clarify: square-per-stud previews from the existing `write_preview` (10 px map pages, 3 px
  thumbnails, CSS pixelated). A round-stud style would need a new CLI option (reserved) (agent)
- plan: FastAPI + Jinja2 + uvicorn (all MIT/BSD); `web/` with poetry-core, package `web98138`;
  no new CLI code or flags; no constitution violations (agent)
- plan: `min_machines_running = 0`, `auto_stop_machines = "stop"`, region `sjc`. FOR OWNER REVIEW:
  set 1 to avoid ~1–3 s cold starts (agent)
- implement: dependencies pinned with hashes: `web/requirements.txt` (runtime, 16 packages incl.
  opentelemetry-api, Apache-2.0, pulled by fastapi 0.165) and `web/requirements-build.txt` (the
  CLI's deps at the versions the CLI venv tests with: numpy 1.26.4, scipy 1.17.1, scikit-image
  0.21.0, Pillow 10.4.0, ReportLab 5.1.0) (agent)
- implement: tests use `httpx2` (Starlette 1.10 deprecates httpx for TestClient; BSD-3) (agent)
- implement: uvicorn access log off (no visitor IPs logged); server header off (agent)
- implement: the manifest carries the lots (`Lot.to_dict()` of the one-kit parts list), totals,
  warnings, citations, layers and part labels (from `PART_TYPE`/`PART_LABEL`), so the service
  formats data and computes nothing (agent)
- implement: "what one kit covers" = needed − to_buy with `--kits 1` (agent)
- implement: suitability warnings are shown verbatim from the library report (they name colors by
  key, e.g. `lego_dark_green`) (agent)
- analyze: inline; every FR mapped to a task; 0 CRITICAL, 0 HIGH (agent)
- converge: one pass over FR-001–FR-024 and SC-001–SC-007; nothing further (agent)

## Results (local, session scratchpad `e2e008/`)
- prebuild of 12 variants from the cached datasets: 26.9 s, 72.6 MB, peak RSS ~384 MB (build stage
  only); 9 variants need no top-up files (one kit covers them), land-elevation has them
- service: ~62 MB RSS after 400 requests; pages 2–6 ms; every route and download checked with curl
- downloaded PDF 42 pages, BrickLink XML parses (13 items, 10,240 pieces for land-elevation),
  Rebrickable CSV header `Part,Color,Quantity`, layout schema 2.0 with the right arrangement
- 360 px: no horizontal scroll on home, map and about pages (lots table scrolls inside its box)
- Docker not available locally: the build was emulated in clean venvs (hashed installs of both
  requirement files, CLI install, wheel of `web/`, prebuild of one variant; runtime venv imports
  neither NumPy nor the CLI)

## Blocked tasks

## Deferred findings
- Fly app name `world-98138` availability not checked (needs login); deploy.md says what to do if
  taken.

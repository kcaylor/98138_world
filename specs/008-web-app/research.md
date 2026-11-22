# Research: Web App (008)

## R1. Framework

**Decision**: FastAPI (MIT) with Jinja2 templates (BSD-3), served by uvicorn (BSD-3).
**Rationale**: owner suggested it; first-class Jinja2 and file responses through Starlette
(BSD-3); TestClient makes offline route tests trivial; small memory footprint (~40–60 MB RSS);
all permissive. Pydantic (MIT) comes along but is barely used.
**Alternatives**: Starlette alone (lighter, but FastAPI adds nothing heavy and is the brief's
suggestion); Flask (BSD, WSGI; would need gunicorn and a separate test client — no advantage);
a static site generator plus a plain file server (no Python process, but the owner chose one
Python service and the same templates would still need a renderer and header control).

## R2. Build ahead of time vs on request

**Decision**: build all 12 variants at image build time; serve files only.
**Rationale**: measured locally: one variant (map build + preview + 2 parts lists + 4 exports +
2 PDFs) takes about 2 s; peak RSS of a build process is ~220 MB (NumPy/SciPy/scikit-image plus the
reprojection), too close to the 256 MB machine for on-demand builds. Serving prebuilt files needs
only FastAPI (~50 MB). Owner decision 3.

## R3. Library functions used; refactors

`load_recipe`, `bundled_recipes` (maps.recipe); `build_map`, `missing_datasets` (maps.build);
`fetch`, `cached_path`, `sha256_file` (datasets.cache); `write_preview(layout, path, scale)`
(maps.preview); `parse_arrangement`, `load_arrangements` (layout.arrangement);
`build_parts_list`, `OwnedInputs`, `to_bricklink_xml`, `to_rebrickable_csv`, `ACKNOWLEDGEMENT`,
`PRICE_NOTE`, `BRICKLINK_UPLOAD_NOTE` (parts); `build_sheet_set`, `render_pdf` (sheets);
`MapResult.report` for citations and warnings; `PositionPlacementGrid.to_json`.

The CLI commands are thin wrappers over these already (features 004–007 were built that way), so
no CLI-only logic needs moving. `to_bricklink_xml` returns `None` when nothing is to buy; the
prebuild records that as "nothing to buy" (FR-006) rather than writing an empty file — the same
rule `parts export` applies.

## R4. Preview resolution

**Decision**: map pages 10 px per stud (1280 × 800 PNG, ~20–40 kB, blocks compress well);
thumbnails 3 px per stud (384 × 240). CSS `image-rendering: pixelated` keeps studs sharp when the
browser scales. `write_preview`'s `scale` argument already exists; the CLI uses 8.

## R5. Container

**Decision**: `python:3.11.18-slim-bookworm` (pushed 2026-11-05) in two stages.
Build stage: `pip install ./cli`, `pip install --no-deps ./web`, `python -m web98138.prebuild
--fetch --out /site` (downloads ~10.5 MB of pinned datasets, verified). Runtime stage:
`pip install -r web/requirements.txt && pip install --no-deps ./web`, `COPY --from=build /site`,
user `app` (uid 10001), `CMD uvicorn web98138.app:app --host 0.0.0.0 --port 8080
--proxy-headers --forwarded-allow-ips='*' --no-server-header`. The runtime image has no NumPy,
SciPy, scikit-image or ReportLab: smaller image, faster cold start, lower memory.
scikit-image 0.21 has manylinux wheels for CPython 3.11 x86_64, so the build stage needs no
compiler. `.dockerignore` keeps `.git`, virtualenvs, tests, specs and outputs out of the context.

## R6. Security headers

`Content-Security-Policy: default-src 'none'; img-src 'self'; style-src 'self'; base-uri 'none';
form-action 'none'; frame-ancestors 'none'`, `X-Content-Type-Options: nosniff`,
`Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, `Permissions-Policy` empty grants,
`Strict-Transport-Security` (Fly terminates TLS; `force_https`). No cookies. FastAPI's `/docs`,
`/redoc` and `/openapi.json` are disabled.

## R7. Cache headers

Built files: `Cache-Control: public, max-age=86400` plus an `ETag` of the manifest SHA-256.
Pages: `public, max-age=300`. CSS: `public, max-age=86400` (a version query string changes per
deploy).

## R8. Canonical host

Requests with `Host: www.98138.world` get 301 to `https://98138.world` + path. Fly's own
`*.fly.dev` host still works (useful before DNS).

# Implementation Plan: Price Estimates for Maps

**Branch**: `011-price-estimates` | **Date**: 2026-11-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/011-price-estimates/spec.md`

## Summary

A new library subpackage `lego_image_processor.prices` and two CLI commands under the existing
`parts` group:

1. **`parts estimate LAYOUT`** (US1, offline): builds the 005 parts lists for the layout (every
   piece, and `OwnedInputs(kits=1)` for the one-kit top-up) with `build_parts_list`, looks each
   verified lot up in a validated price snapshot, and reports two estimates (average, low, high in
   exact `Decimal`, rounded half-up to cents at the end) with per-lot lines, unpriced lots, a
   staleness check against an injectable `--as-of` date, wording, attribution and disclaimer, as a
   table or deterministic JSON.
2. **`parts prices fetch`** (US2, the only network step): reads OAuth 1.0 credentials from four
   environment variables, signs each request with a small stdlib HMAC-SHA1 module (RFC 5849),
   queries the BrickLink price guide (`sold` and `stock`, new, USD, worldwide, VAT excluded) for
   every lot the bundled recipes declare (19 today; `--all-colors` for all 84 cited lots), paces and
   retries with an injectable opener, sleep and clock, saves progress per lot next to the output,
   resumes with `--resume`, and writes `bricklink_price_guide.json` deterministically. The API's
   base URL and documentation URLs live in a new cited reference file `data/bricklink_api.json`,
   not in code.
3. **Web** (US3): `web98138.prebuild.build_site` loads the packaged snapshot (or `prices_path=`),
   calls the estimate library on the `full` and `topup` parts lists it already builds, and writes
   `variants[C].estimates.{full,one_kit}` plus a top-level `prices` block into the manifest;
   `catalog.py` validates them when `prices` is present; `map.html` shows an "Estimated cost"
   panel. The service still reads only the manifest.

## Technical Context

**Language/Version**: Python 3.11 (CLI `^3.11`; web image pinned to 3.11 for scikit-image 0.21)

**Primary Dependencies**: no new ones. Click (CLI); stdlib `urllib.request`, `hmac`, `hashlib`,
`base64`, `secrets`, `urllib.parse`, `decimal`, `json`, `datetime` for fetch, signing and
arithmetic (research R1, R2). Web: FastAPI + Jinja2 unchanged.

**Storage**: files. Packaged reference data `cli/src/lego_image_processor/data/bricklink_api.json`
(new, cited) and `bricklink_price_guide.json` (new, written by the fetch, committed by the owner);
a git-ignored progress file `<output stem>.progress.json` next to the fetch output.

**Testing**: pytest. CLI: `cli/tests/unit/prices/` (oauth1 vectors, snapshot validation, lot set,
estimate arithmetic, fetch loop with mocked opener/sleep/clock), `cli/tests/integration/`
(estimate of the official layout and a `land-elevation` fixture layout; offline; performance),
`cli/tests/contract/test_prices_contract.py` (CLI I/O, exit codes, no-credential-leak). Fixtures
in `cli/tests/fixtures/prices/`. Web: `web/tests/` with the CLI fixture snapshot passed to
`build_site`. The suite-wide socket guard (`cli/tests/conftest.py`) stays on.

**Target Platform**: maintainer laptop (macOS/Linux) for the fetch; any platform for estimates;
the Docker build stage (Linux) for the prebuild.

**Project Type**: CLI library + command (`cli/`) and the existing prebuilt web site (`web/`).

**Performance Goals**: estimate of a 10,240-position layout < 2 s (SC-003; two `build_parts_list`
calls dominate; an integration test times it); default fetch 38 requests at ≤ 1 request/s < 5 min (SC-004).

**Constraints**: no network except `parts prices fetch`; credentials only from env vars, never in
any output or file (FR-006); deterministic bytes for snapshot and estimate JSON (FR-004, FR-015);
service file-only (FR-022).

**Scale/Scope**: 19 default lots (38 queries), 84 with `--all-colors` (168 queries, far below
BrickLink's documented 5,000/day); 18 site variants × 2 estimates.

No NEEDS CLARIFICATION remain: every open technical point is resolved from the repository in
[research.md](research.md).

## Constitution Check

*GATE: checked before Phase 0 and again after Phase 1 design (result unchanged).*

| Principle | Check |
|---|---|
| I. Kit is a fixed template | Pass. Nothing about the grid, mask or parts changes; the one-kit top-up uses the cited inventory through `build_parts_list(owned=OwnedInputs(kits=1))`. |
| II. Recipes | Pass. The default lot set is derived from the bundled recipes' declared colors (and shadow color), not a hand-kept list (research R5). |
| III. Data in | Not affected. |
| IV. Reproducible data acquisition | Pass. Credentials come only from `BRICKLINK_*` environment variables and are never written (FR-006). The snapshot is committed reference data with its retrieval times and every query parameter; estimates record its SHA-256, so every figure is reproducible offline. Only `parts prices fetch` uses the network. Open item for the owner: the BrickLink API terms (license of the derived data) could not be read on 2026-11-22; the user chose to ship assuming they allow it. |
| V. Buildable and honest outputs | Pass. Prices are attached only to verified lots (cited BrickLink item and color IDs); the snapshot is validated against the cited tables on load; unpriced lots are listed with reasons and the estimate is marked incomplete; fallbacks (stock average) are labelled. |
| VI. CLI first; no hardcoded secrets or proprietary endpoints | Pass, **by the user's decision** (spec Clarifications, 2026-11-22: "A publicly documented API with user-supplied credentials is not a proprietary endpoint; its base URL lives in cited reference data, not in code ... No amendment."). The base URL, endpoint path and documentation URLs are in `data/bricklink_api.json` (research R3); code holds no URL and no secret. Both capabilities are library functions and CLI commands before the web uses them; the prebuild calls the library, the service never imports it. |
| VII. Test-first, offline tests | Pass. Fixture snapshot and synthetic API responses; injected opener, sleep, clock and nonce; the socket guard stays on; a test greps every output and written file for the fake credential values and the computed signatures (FR-023, SC-005). |
| VIII. LEGO compliance | Pass. Every estimate output (table, JSON, manifest, page) carries the estimate wording, the BrickLink attribution ("... Not endorsed by BrickLink.") and "Not affiliated with or endorsed by The LEGO Group." The attribution wording is for the owner to check against the terms. |

No violations; Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/011-price-estimates/
├── plan.md              # this file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── cli.md                   # parts estimate, parts prices fetch
│   ├── library-api.md           # lego_image_processor.prices
│   ├── price-snapshot-format.md # bricklink_price_guide.json, bricklink_api.json, progress file
│   ├── estimate-format.md       # parts estimate JSON
│   └── web.md                   # prebuild options, manifest additions, catalog check, page
└── tasks.md             # Phase 2 (speckit-tasks; not created here)
```

### Source Code (repository root)

```text
cli/src/lego_image_processor/
├── prices/                      # NEW (feature 011)
│   ├── __init__.py              # public API (contracts/library-api.md)
│   ├── api_config.py            # load + validate data/bricklink_api.json
│   ├── oauth1.py                # RFC 5849 HMAC-SHA1 Authorization header (stdlib)
│   ├── credentials.py           # env vars -> Credentials (redacted repr)
│   ├── lots.py                  # LotRef; default (recipes) and all-cited lot sets
│   ├── snapshot.py              # PriceSnapshot model, load/validate, deterministic write, diff
│   ├── fetch.py                 # client: request build, response parse, pacing, retry, progress
│   ├── wording.py               # ATTRIBUTION, ESTIMATE_NOTE, BASIS_TEXT, DEFAULT_STALE_DAYS (shared, no cycle)
│   ├── estimate.py              # Estimate, EstimateReport (Decimal)
│   └── text.py                  # human table output shared by the CLI
├── cli/prices.py                # NEW: `parts estimate`, `parts prices fetch` (registered on `parts`)
├── cli/main.py                  # register the two commands on the `parts` group
├── parts/partslist.py           # PRICE_NOTE text and docstring only (FR-019)
└── data/
    ├── bricklink_api.json       # NEW, cited
    └── bricklink_price_guide.json   # NEW, written by the owner's fetch (not by the agent)

cli/tools/fixtures011/make_price_fixture.py   # NEW: maintainer tool that writes the synthetic fixture
cli/tests/
├── fixtures/prices/             # NEW: snapshot fixture + .source.json, synthetic API responses
├── unit/prices/                 # NEW
├── integration/test_prices_estimate.py, test_prices_fetch.py   # NEW
└── contract/test_prices_contract.py                            # NEW; test_parts_contract.py PRICE_NOTE line

web/src/web98138/
├── prebuild.py                  # prices_path / with_prices / allow_partial_prices / today
├── catalog.py                   # estimates check when `prices` present
├── app.py                       # `usd` filter only (formats ints from the manifest)
├── templates/map.html           # "Estimated cost" panel
└── static/style.css             # panel styles
web/tests/conftest.py            # pass the CLI fixture snapshot to build_site
.gitignore, .dockerignore        # ignore *.progress.json
docs/deploy.md                   # snapshot refresh step before deploy
CLAUDE.md                        # feature 011 paragraph
```

**Structure Decision**: a new `prices/` subpackage, as `sheets/` was for 006, keeps the network
client, signing and money arithmetic out of `parts/` (which stays network-free, as its docstring
promises). `prices` depends on `parts`, `kit` and `maps.recipe`; nothing in `parts` imports
`prices`. CLI commands are registered on the existing `parts` group so the names the user approved
(`parts estimate`, `parts prices fetch`) hold.

## Snapshot delivery and the Docker build (agent decision)

No real snapshot exists yet; the owner runs the fetch after implementation. The simplest safe path:

- **Dockerfile unchanged.** The build stage already runs `pip install --no-deps ./cli` (package
  data included) and `python -m web98138.prebuild --fetch --out /site`. With the new default the
  prebuild fails, by design, until `data/bricklink_price_guide.json` is committed: "no price
  snapshot is packaged ... run `parts prices fetch` and commit it, or pass --no-prices". No
  `--no-prices` build arg is added, so a deploy can never silently drop prices (spec US3-7).
- **Merge gate.** The branch merges only after the owner commits a complete snapshot from
  `parts prices fetch` (quickstart §4). Until then the deployed site keeps running the current
  image; `fly deploy` is the owner's step anyway.
- **Tests never need the packaged snapshot.** CLI and web tests use
  `cli/tests/fixtures/prices/` (web passes it as `prices_path`). One test validates the packaged
  snapshot when present and is skipped with the reason "packaged snapshot not committed yet" when
  absent, so the suite stays green before the owner's fetch and checks the real file after.
- **The fixture cannot reach the image**: `.dockerignore` already excludes `cli/tests`; it gains
  `**/*.progress.json` so a local progress file never enters the build context.

## Complexity Tracking

None.

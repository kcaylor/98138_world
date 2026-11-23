---
description: "Task list for feature 011: price estimates for maps"
---

# Tasks: Price Estimates for Maps (011)

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/ (cli.md, library-api.md,
price-snapshot-format.md, estimate-format.md, web.md), quickstart.md, run-state.md

**Tests**: required (constitution VII, spec FR-023). Within each story every implementation task
follows the failing test task it makes pass. All tests are offline: estimates use the synthetic
fixture snapshot in `cli/tests/fixtures/prices/`; the fetch uses an injected opener, sleep, clock,
`now` and nonce with synthetic API responses and fake credentials; the suite-wide socket guard in
`cli/tests/conftest.py` stays on. No task opens the network or needs real BrickLink keys.

**Paths**: under `cli/` unless stated; `src/` = `cli/src/lego_image_processor/`.

**Order (owner priority)**: Phase 2 (shared prices foundations) → US1 (`parts estimate`, a real
number from any snapshot) → US2 (`parts prices fetch`, the real snapshot) → US3 (web). US1 and US2
are each complete and independently testable before any US3 task starts.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1, US2, US3 (spec.md user stories)

---

## Phase 1: Setup

- [X] T001 Record the baseline: `cd cli && poetry run pytest -q` and `cd web && .venv/bin/pytest -q` (see CLAUDE.md for the uv fallback); write both pass counts into specs/011-price-estimates/run-state.md
- [X] T002 [P] Add `*.progress.json` to /.gitignore and `**/*.progress.json` to /.dockerignore (research R9; contracts/web.md Docker)
- [X] T003 [P] Create the empty package src/prices/__init__.py (module docstring: offline estimating, one network function `fetch_snapshot`; `parts` never imports `prices`) and the test package cli/tests/unit/prices/__init__.py

---

## Phase 2: Foundational (blocks US1 and US2)

**Purpose**: the wording constants, the lot key and lot sets, and the validated, deterministic
price snapshot. US1 reads snapshots; US2 writes them. Both depend on this phase only.

- [X] T004 [P] Wording tests in cli/tests/unit/prices/test_wording.py: `ATTRIBUTION`, `ESTIMATE_NOTE`, `DISCLAIMER` (re-exported, "Not affiliated with or endorsed by The LEGO Group."), `BASIS_TEXT` for sold/stock/unpriced, `DEFAULT_STALE_DAYS == 90`, `PACKAGED_SNAPSHOT_PATH` ends with `data/bricklink_price_guide.json`; exact texts as contracts/estimate-format.md and spec Clarifications (attribution names LEGO BrickLink, Inc.; no word "endorsed by BrickLink" without "Not") (FR-018)
- [X] T005 Implement src/prices/wording.py with those constants (kept apart from estimate.py so snapshot.py and estimate.py both import it without a cycle)
- [X] T006 [P] Lot tests in cli/tests/unit/prices/test_lots.py: `lot_ref("6141", "lego_white")` and `lot_ref("98138", <a kit tile key>)` fields come from `part_colors.json`/`part_numbers.json` (BrickLink item `4073` / `98138`, type `P`); `recipe_lots()` gives 19 lots (10 plate, 9 tile) including the shadow color, sorted 6141 then 98138 by LEGO color ID, unique; a recipe list parsed from text with one extra declared color adds exactly that lot; `all_cited_lots()` gives 84 (44 plate, 40 tile); every lot's BrickLink color name is on the part's catalog page; `parse_lot("98138:140")` works, `"98138:9999"`, `"3001:1"`, `"x"` → `ValueError` naming the input (data-model.md LotRef.part_id, LotRef.lego_color_id, LotRef.color_key, LotRef.bricklink_item_type, LotRef.bricklink_item_no, LotRef.bricklink_color_id; FR-007; research R5)
- [X] T007 Implement src/prices/lots.py: `LotRef`, `lot_ref`, `recipe_lots(recipes=None)` from `maps.recipe.bundled_recipes()` land/ocean colors plus enabled shadow color, `all_cited_lots`, `parse_lot` (data-model.md LotRef.part_id, LotRef.lego_color_id, LotRef.color_key, LotRef.lego_color_name, LotRef.bricklink_item_type, LotRef.bricklink_item_no, LotRef.bricklink_color_id, LotRef.bricklink_color_name; research R5)
- [X] T008 [P] Snapshot tests in cli/tests/unit/prices/test_snapshot.py, building snapshot dicts with a helper in cli/tests/unit/prices/conftest.py: a valid dict loads; each rule of contracts/price-snapshot-format.md §1 rejected with `SnapshotError` naming the JSON path: `format_version` ≠ "1", unknown key at top level / in `source` / in a lot / in `sold` (no credential or header field can pass), changed attribution, estimate_note, disclaimer or `source.disclaimer`, price not matching `^\d+(\.\d{1,4})?$` or a JSON number, zero or negative price, `min > qty_avg`, `avg > max`, `unit_quantity` 0, `total_quantity < unit_quantity`, `error: "not found"` with non-null figures, lots unsorted or duplicated, `bricklink.item_no`/`color_id`/names differing from the cited tables, `retrieved_at` outside `[started_at, finished_at]`, `finished_at < started_at`, `complete: true` with `len(lots) != lot_set.count`; a partial snapshot (`complete: false`) loads with `complete == False`; prices load as `Decimal` exactly; the loaded object records `sha256`, `file_name`, `path`, `packaged`; `load_snapshot()` with `PACKAGED_SNAPSHOT_PATH` monkeypatched to a missing file raises `SnapshotMissingError`; unreadable / not-JSON files raise `SnapshotError`; `snapshot_to_json(load(x))` equals the canonical bytes (key order, indent 2, trailing newline) and is stable on rewrite; `largest_changes(old, new, n=5)` orders by absolute percent change of the unit average and skips lots missing on either side (data-model.md GuideFigures.qty_avg_price, GuideFigures.avg_price, GuideFigures.min_price, GuideFigures.max_price, GuideFigures.unit_quantity, GuideFigures.total_quantity, SnapshotLot.error, SnapshotLot.retrieved_at, PriceSnapshot.format_version, PriceSnapshot.source, PriceSnapshot.retrieved, PriceSnapshot.query, PriceSnapshot.statistic, PriceSnapshot.lot_set, PriceSnapshot.complete, PriceSnapshot.lots, PriceSnapshot.attribution; FR-001–FR-004)
- [X] T009 Implement src/prices/snapshot.py: `GuideFigures`, `SnapshotLot` (derived `basis`), `PriceSnapshot`, `SnapshotError`, `SnapshotMissingError`, `load_snapshot(path=None)`, `snapshot_to_json`, `largest_changes` (data-model.md GuideFigures.qty_avg_price, GuideFigures.avg_price, GuideFigures.min_price, GuideFigures.max_price, GuideFigures.unit_quantity, GuideFigures.total_quantity, SnapshotLot.lot, SnapshotLot.sold, SnapshotLot.stock, SnapshotLot.retrieved_at, SnapshotLot.error, PriceSnapshot.format_version, PriceSnapshot.source, PriceSnapshot.retrieved, PriceSnapshot.query, PriceSnapshot.statistic, PriceSnapshot.lot_set, PriceSnapshot.complete, PriceSnapshot.lots, PriceSnapshot.attribution, PriceSnapshot.estimate_note, PriceSnapshot.disclaimer; contracts/price-snapshot-format.md §1; research R4, R10, R11)
- [X] T010 Fixture generator cli/tools/fixtures011/make_price_fixture.py (maintainer tool, not packaged; synthetic values listed in the script, written with `snapshot_to_json`) and its output cli/tests/fixtures/prices/bricklink_price_guide.json plus bricklink_price_guide.source.json (`synthetic: true`, "Synthetic values for tests; not BrickLink data.", generator, sha256, disclaimer): the official layout's 10 lots, the land-elevation fixture build's plate colors except Dark Brown (LEGO 308), one tile lot with `sold: null` and `stock` set; `lot_set.kind: "named"`, `complete: true`, real cited IDs (contracts/price-snapshot-format.md "Test fixture")
- [X] T011 Fixture test in cli/tests/unit/prices/test_snapshot.py: the fixture loads; `.source.json` sha256 matches the file; it has the stock-only lot, lacks Dark Brown, covers every lot of the official layout; rerunning the generator reproduces identical bytes
- [X] T012 Export the Phase 2 names from src/prices/__init__.py (contracts/library-api.md: constants, lots, snapshot)

**Checkpoint**: `pytest -q` passes as at T001 plus the new tests.

---

## Phase 3: User Story 1 — Estimate any layout from a snapshot (P1) 🎯 MVP

**Goal**: `parts estimate LAYOUT [--prices FILE]` gives full and one-kit top-up estimates
(average, low, high) offline, as a table or deterministic JSON, with wording and attribution.

**Independent test**: with the fixture snapshot, estimate the official layout and the
land-elevation fixture layout; totals match hand-computed sums; two JSON runs are byte-identical;
no network.

### Library

- [X] T013 [P] [US1] Estimate tests in cli/tests/unit/prices/test_estimate.py (small layouts from cli/tests/unit/parts/layouts.py, snapshots from the Phase 2 helper): basis sold → unit = sold `qty_avg_price`/`min_price`/`max_price`; sold null → stock figures, basis `stock`; neither or `error: not found` → unpriced "no BrickLink sales or listings"; no entry → "not in the price snapshot"; unverified 005 lot → "no verified BrickLink IDs (<005 reason>)" with `bricklink` null; line values exact (`quantity × unit`, no rounding); totals = exact sums quantized half-up to 0.01 (a case where per-line rounding would differ); `whole_dollars` half-up to $1 as ints; `low ≤ average ≤ high`; `by_basis` lots/pieces; `complete`; `pieces` equals parts-list `needed` (full) and `to_buy` (one_kit); one_kit with nothing to buy → `nothing_to_buy`, totals "0.00", note "One kit covers every piece."; staleness `as_of`, `age_days` from `retrieved.finished_at` date, `stale` iff age > threshold, figures unchanged when stale; partial snapshot note; notes in the order of contracts/estimate-format.md; `estimate_parts_lists` raises `ValueError` when `full.owned.kits != 0`, `one_kit.owned.kits != 1`, owned/missing files or spares present, or layout SHA-256 differs; `estimate_layout(layout, ...)` equals `estimate_parts_lists` on the two lists it builds; `to_json()` twice identical, contains no generation time, money as strings (data-model.md EstimateLine.quantity, EstimateLine.basis, EstimateLine.reason, EstimateLine.unit, EstimateLine.line, Estimate.kind, Estimate.owned_kits, Estimate.totals, Estimate.whole_dollars, Estimate.complete, Estimate.nothing_to_buy, EstimateReport.staleness; FR-012–FR-017; research R10–R13)
- [X] T014 [US1] Implement src/prices/estimate.py: `EstimateLine`, `Estimate`, `EstimateReport` (`to_dict`, `to_json` per contracts/estimate-format.md), `estimate_parts_lists`, `estimate_layout` using `parts.build_parts_list` and `OwnedInputs(kits=1)` (no duplicate lot logic) (data-model.md EstimateLine.lot, EstimateLine.quantity, EstimateLine.basis, EstimateLine.reason, EstimateLine.unit, EstimateLine.line, EstimateLine.figures, Estimate.kind, Estimate.owned_kits, Estimate.lines, Estimate.totals, Estimate.whole_dollars, Estimate.by_basis, Estimate.complete, Estimate.nothing_to_buy, EstimateReport.layout, EstimateReport.snapshot, EstimateReport.staleness, EstimateReport.notes; FR-012–FR-017)
- [X] T015 [P] [US1] Table tests in cli/tests/unit/prices/test_text.py: `echo_estimate(report, lines=False)` prints the header, the Prices line with date, statistic and SHA-256 prefix, the two-row table with thousands separators, "One kit covers every piece" row, stale / partial / incomplete warnings with per-lot unpriced lines and the `--all-colors` hint, stock-fallback line, `--lines` per-lot rows for both estimates, then ESTIMATE_NOTE, ATTRIBUTION and the disclaimer as the last line (contracts/cli.md `parts estimate` human output; FR-018)
- [X] T016 [US1] Implement `echo_estimate` in src/prices/text.py
- [X] T017 [US1] Export the US1 names (`estimate_parts_lists`, `estimate_layout`, `Estimate`, `EstimateLine`, `EstimateReport`) from src/prices/__init__.py; add a test in cli/tests/unit/prices/test_estimate.py that `lego_image_processor.parts` modules do not import `lego_image_processor.prices`

### CLI

- [X] T018 [P] [US1] Contract tests in cli/tests/contract/test_prices_contract.py (CliRunner, `--prices` = fixture, `--as-of 2026-12-05`): `parts estimate official.json` exit 0, both rows, top-up "One kit covers every piece", disclaimer last; `--format json` parses and matches contracts/estimate-format.md keys; `-o e.json` writes JSON and prints one summary line plus the disclaimer; two `-o` runs byte-identical; `--lines` adds lot rows; `-q` prints nothing on success; `--as-of 2027-06-01` warns stale, same figures; `--stale-days 0` → exit 2; no `--prices` with the packaged snapshot monkeypatched absent → exit 1 "no price snapshot is packaged yet; pass --prices FILE or run `lego-image-processor parts prices fetch`"; missing / not-JSON / invalid snapshot → exit 1 with the reason and no output file; output directory missing → exit 1; layout the parts list rejects → exit 1 as `parts list`; `--kits` is not an option (exit 2); no credentials needed (env cleared) (contracts/cli.md; US1-5–US1-8)
- [X] T019 [US1] Implement src/cli/prices.py `estimate` command and register it on the `parts` group (src/cli/parts.py or src/cli/main.py), with `CommandError` exit-code style of 005 (contracts/cli.md `parts estimate`)
- [X] T020 [P] [US1] Disclaimer audit: add `parts estimate` (table and JSON) to cli/tests/contract/test_disclaimer.py (constitution VIII; FR-018)
- [X] T021 [P] [US1] Update the PRICE_NOTE expectation in cli/tests/contract/test_parts_contract.py to the R15 text (test first), then change `PRICE_NOTE` and its docstring in src/parts/partslist.py (FR-019; research R15)

### Integration

- [X] T022 [US1] Integration tests in cli/tests/integration/test_prices_estimate.py: official layout from `load_official_design().to_layout()` with the fixture → full average/low/high equal hand sums over its 10 lots, complete, top-up nothing to buy (US1-1); land-elevation fixture build (`fixture_registry.place_all()`) → top-up prices exactly each lot's `to_buy` from `build_parts_list(owned=OwnedInputs(kits=1))` (US1-2), one tile lot basis `stock` counted in `by_basis` (US1-3), Dark Brown unpriced "not in the price snapshot", estimate incomplete with lot and piece counts and the hint (US1-4); a 10,240-position estimate runs in < 2 s (SC-003); runs under the socket guard (SC-007)

**Checkpoint**: US1 complete and independently testable; `parts estimate` gives a real number
from any valid snapshot. Full CLI suite green.

---

## Phase 4: User Story 2 — Fetch a cited snapshot from BrickLink (P2)

**Goal**: `parts prices fetch -o PATH` signs and paces price-guide requests, resumes, never leaks
credentials, and writes a snapshot that US1 loads.

**Independent test**: with a mocked opener, fetch a few lots and the default 19; check requests,
the written snapshot, retry/stop behaviour, resume, and a credential-leak scan.

### Reference data, signing, credentials

- [X] T023 [P] [US2] OAuth tests in cli/tests/unit/prices/test_oauth1.py: `percent_encode` (RFC 5849 §3.6, UTF-8, reserved chars); `base_string` and parameter normalization on the RFC 5849 §3.4.1 example (expected strings copied from the RFC text); the §1.2 HMAC-SHA1 example signature; a frozen vector for a BrickLink price-guide URL with fixed nonce and timestamp; `authorization_header` field order and quoting (research R2)
- [X] T024 [US2] Implement src/prices/oauth1.py (stdlib only; research R2)
- [X] T025 [P] [US2] API config tests in cli/tests/unit/prices/test_api_config.py: the packaged file loads; rejected with `ValueError` naming the field: non-https or trailing-slash or query `base_url`, path without `{type}`/`{no}`, `item_types` lacking `P → PART`, other OAuth version or method, `daily_request_limit` ≤ 0, source without documentation, `accessed`, `checked` or the disclaimer (data-model.md ApiConfig.base_url, ApiConfig.price_guide_path, ApiConfig.item_types, ApiConfig.oauth, ApiConfig.daily_request_limit, ApiConfig.source)
- [X] T026 [US2] Add src/data/bricklink_api.json exactly as contracts/price-snapshot-format.md §2 (`checked: false`) and implement `load_api_config` in src/prices/api_config.py (data-model.md ApiConfig.base_url, ApiConfig.price_guide_path, ApiConfig.item_types, ApiConfig.oauth, ApiConfig.daily_request_limit, ApiConfig.source; research R3); the existing data-file disclaimer test covers it; in cli/tests/contract/test_disclaimer.py exclude `*.progress.json` from the `DATA_DIR.glob("*.json")` parametrization (a stopped owner fetch leaves one in data/, research R9)
- [X] T027 [P] [US2] Credential tests in cli/tests/unit/prices/test_credentials.py: all four `BRICKLINK_*` set → `Credentials`; any missing or empty → `MissingCredentialsError` whose `.names` and message list only variable names; `repr`/`str` are `Credentials(<redacted>)` and contain no value (data-model.md Credentials; FR-006; research R8)
- [X] T028 [US2] Implement src/prices/credentials.py: `Credentials`, `credentials_from_env(env=os.environ)`, `MissingCredentialsError` (data-model.md Credentials.consumer_key, Credentials.consumer_secret, Credentials.token_value, Credentials.token_secret; FR-006; research R8)

### Fetch loop

- [X] T029 [P] [US2] Synthetic API responses in cli/tests/fixtures/prices/api/ (R4 shape, values synthetic, a `README.source.json` saying so with the disclaimer): `price_<item>_<color>_<guide>.json` for the lots the tests use, `error_401_token_ip.json`, `error_429.json`, `error_daily_limit.json`, `not_found.json`, `no_sales.json` (`unit_quantity: 0`), one response with JSON-number prices (contracts/price-snapshot-format.md "Test fixture")
- [X] T030 [P] [US2] Fetch tests in cli/tests/unit/prices/test_fetch.py (fake opener recording requests; fake `sleep`, monotonic `clock`, `now`, `nonce`): each lot makes two GETs to `{base_url}/items/PART/{item_no}/price` with `color_id`, `guide_type` sold then stock, `new_or_used=N`, `currency_code=USD`, `vat=N`, no `country_code`/`region`, an `Authorization: OAuth …` header whose `oauth_timestamp` is the Unix seconds of the injected `now` (not the monotonic `clock`), `User-Agent`, timeout 30 (FR-008; research R2, R4); prices parsed as exact `Decimal` (also from JSON numbers via `parse_float=Decimal`); `unit_quantity == 0` → `None`; `price_detail` not stored; request starts ≥ `interval` apart; 429/5xx/`URLError` retried after 2, 4, 8, 16 s or `Retry-After` capped at 60, at most `max_attempts`, then `PriceFetchError` (exit 5) with `done`/`total`/`progress_path`; `meta.code` 429 under HTTP 200 retried; 401/403 and `TOKEN_IP_MISMATCHED` → `AuthError` (exit 7) at the first rejection, message from BrickLink's code/message and the token IP setting, no snapshot written; daily-limit message → `DailyLimitError` (exit 5, "try again tomorrow"); 404 / `RESOURCE_NOT_FOUND` → lot `error: "not found"`, run continues; 400 → exit 5; progress file rewritten atomically after each lot with fingerprint (R9), deleted on completion; on a stop the `output` file is untouched unless `write_partial` (then `complete: false`); `resume=True` skips saved lots and makes no request for them; resume with no progress or a different fingerprint → `ProgressMismatchError` (exit 1) naming the difference; without resume an existing progress file is replaced; the written snapshot passes `load_snapshot`, copies the `api` block, records `lot_set` (kind, recipe ids and SHA-256s, count), `retrieved` start/finish and per-lot `retrieved_at`; same responses and times → identical bytes (data-model.md FetchProgress.fingerprint, PriceSnapshot.complete, PriceSnapshot.lot_set, SnapshotLot.error; FR-005, FR-008–FR-010; research R6, R7, R9)
- [X] T031 [US2] Implement src/prices/fetch.py: `fetch_snapshot`, `FetchResult`, `PriceFetchError`, `AuthError`, `DailyLimitError`, `ProgressMismatchError`, error-class strings as data next to the classifier, default opener `urllib.request.urlopen`, progress file per data-model.md FetchProgress.format, FetchProgress.fingerprint, FetchProgress.started_at, FetchProgress.lot_set, FetchProgress.lots (contracts/library-api.md; research R1, R4, R6–R9)
- [X] T032 [US2] Fetch summary text in src/prices/text.py with tests in cli/tests/unit/prices/test_text.py: per-lot progress line format, "Note: BrickLink API details … not yet checked" when `checked` is false, success summary (lots, complete/partial, priced from sales / stock only / unpriced, up to 5 largest changes or "first snapshot", "Review the file, then commit it.", attribution, disclaimer), stop messages with the resume command repeating the options used (contracts/cli.md `parts prices fetch`; FR-011)
- [X] T033 [US2] Export the US2 names from src/prices/__init__.py (`load_api_config`, `Credentials`, `credentials_from_env`, `MissingCredentialsError`, `fetch_snapshot`, `FetchResult`, error classes)

### CLI

- [X] T034 [P] [US2] Fetch contract tests in cli/tests/contract/test_prices_contract.py (opener, sleep and clock monkeypatched in `prices.fetch`; fake credentials via `env=`): missing variable → exit 1 "missing environment variable(s): BRICKLINK_TOKEN_SECRET" before any request; `-o` missing → exit 2; `--lot 98138:140 --lot 6141:1` → `lot_set.kind: named`, 4 requests; `--lot` with `--all-colors` → exit 2; bad `--lot` → exit 1; `--interval 0.4` and `--max-attempts 0`/`11` → exit 2; `--all-colors` → 84 lots, 168 requests; 5xx exhaustion → exit 5 with the resume command; daily limit → exit 5; 401 IP mismatch → exit 7 naming the IP setting; `--resume` mismatch → exit 1; success prints the summary with largest changes against `--compare` (default: existing output if valid); `-q` prints only the summary; disclaimer last on success and error (contracts/cli.md; US2-5–US2-9)
- [X] T035 [US2] Implement the `prices fetch` subgroup command in src/cli/prices.py, registered under `parts` (contracts/cli.md `parts prices fetch`; exit codes 0/1/2/5/7)

### Integration and leak check

- [X] T036 [US2] Integration tests in cli/tests/integration/test_prices_fetch.py: a mocked full default run (19 lots, 38 requests) writes a snapshot that `load_snapshot` accepts and `parts estimate` uses (US2-1, US2-3, US2-4); an interrupted run (opener raising after lot 7) then `--resume` fetches only the rest, ends complete and deletes the progress file (US2-5); a leak scan over every scenario (success, resume, 429, 5xx exhaustion, 401, IP mismatch, network failure, KeyboardInterrupt): captured stdout/stderr, `caplog`, every file under `tmp_path` contain no credential value, no percent-encoded credential, no `Authorization` header and no `oauth_signature` the mock received (FR-006, FR-023, SC-005); the default run makes ≤ 1 request per second of fake clock (SC-004)
- [X] T037 [P] [US2] Packaged snapshot test in cli/tests/unit/prices/test_packaged_snapshot.py: when src/data/bricklink_price_guide.json exists it loads, is complete, its lot set covers `recipe_lots()` and every bundled recipe's lots are priced (SC-001); skipped with "packaged snapshot not committed yet" when absent (plan "Snapshot delivery")

**Checkpoint**: US2 complete and independently testable with mocks; the owner can now run the
real fetch (T051). Full CLI suite green.

---

## Phase 5: User Story 3 — Show estimates on 98138.world (P3)

**Goal**: the prebuild writes both estimates per variant and a `prices` block into the manifest;
map pages show an "Estimated cost" panel; the service stays file-only.

**Independent test**: prebuild the test maps from the CLI fixture snapshot; check manifest,
catalog validation and the map page; the service never imports the CLI library.

- [X] T038 [P] [US3] Library tests in cli/tests/unit/prices/test_manifest_entry.py: `EstimateReport.manifest_entry("full" | "one_kit")` and `prices_block()` produce exactly the keys of contracts/web.md (labels, totals strings, `whole_dollars` ints, pieces, complete, nothing_to_buy, unpriced/stock lots and pieces; snapshot file, sha256, retrieved_at, retrieved_on, complete, lots; source; basis; estimate_note; attribution; staleness) (data-model.md EstimateReport.manifest_entry)
- [X] T039 [US3] Implement `manifest_entry` and `prices_block` in src/prices/estimate.py (data-model.md EstimateReport.manifest_entry; contracts/web.md Manifest additions)
- [X] T040 [US3] Update web/tests/conftest.py and every `build_site`/`main` call in web/tests/test_prebuild.py to pass `prices_path` / `--prices` = cli/tests/fixtures/prices/bricklink_price_guide.json and a fixed `today`
- [X] T041 [P] [US3] Prebuild tests in web/tests/test_prebuild.py: every variant has `estimates.full` and `estimates.one_kit` equal to `estimate_parts_lists` on that variant's parts lists, and one top-level `prices` block (US3-1); default with the packaged snapshot monkeypatched absent → `PrebuildError` with the contracts/web.md message; invalid snapshot → the `SnapshotError` text; partial snapshot refused, accepted with `allow_partial_prices`/`--allow-partial-prices`; `with_prices=False`/`--no-prices` → no `prices`, no `estimates` (US3-7); `today` past the threshold → `prices.staleness.stale` true; no socket opened for prices (contracts/web.md Prebuild; FR-020)
- [X] T042 [US3] Implement `prices_path`, `with_prices`, `allow_partial_prices`, `today` in web/src/web98138/prebuild.py `build_site` (reuse the `full` and `topup` parts lists of `build_variant`) and the `--prices`, `--no-prices`, `--allow-partial-prices` options in its `main` (FR-020; research R14)
- [X] T043 [P] [US3] Catalog tests in web/tests/test_catalog.py: a manifest with `prices` and a variant missing `estimates.one_kit`, a non-int `whole_dollars.low`, a bad `snapshot.sha256` → `CatalogError` naming map, combination and key; `estimates` without `prices` → `CatalogError`; a manifest without either still loads (contracts/web.md Catalog check)
- [X] T044 [US3] Implement the estimates check in web/src/web98138/catalog.py (no import of `lego_image_processor`)
- [X] T045 [P] [US3] Route tests in web/tests/test_routes.py: map page shows "Estimated cost", "Every piece: about $N (range $L–$H)" from the manifest ints with thousands separators, the price date, a plain `<a href="https://www.bricklink.com">`, ESTIMATE_NOTE, ATTRIBUTION, footer disclaimer (US3-2, SC-006); a nothing-to-buy top-up reads "One kit covers every piece" (US3-3); an incomplete estimate (manifest edited in a tmp copy) shows "Incomplete: N pieces in M colors could not be priced" (US3-4); stale and partial notes (US3-5); low == high shows one value; a site built with `--no-prices` has no panel; home page unchanged; the existing no-JS / no-cookie / no-third-party and no-CLI-import tests in web/tests/test_security.py still pass, and a new test there checks the built site directory holds no `bricklink_api.json`, no `BRICKLINK_` string and no snapshot file (US3-6, FR-022)
- [X] T046 [US3] Implement the `usd` Jinja filter in web/src/web98138/app.py, the "Estimated cost" panel in web/src/web98138/templates/map.html and its styles in web/src/web98138/static/style.css (FR-021; contracts/web.md Map page)

**Checkpoint**: web suite green with the fixture snapshot; `docker build` fails at the prebuild
until T051 is done (by design, plan "Snapshot delivery").

---

## Phase 6: Polish and cross-cutting

- [X] T047 [P] docs/deploy.md: snapshot refresh step before a deploy (quickstart §4–5), the merge gate, and that the prebuild fails without a committed snapshot
- [X] T048 [P] CLAUDE.md: feature 011 paragraph (commands, `prices/` subpackage, `bricklink_api.json` with `checked`, snapshot file, env var names, fixture path, the prebuild's price options)
- [X] T049 Run the full suites (`cd cli && poetry run pytest`, `cd web && .venv/bin/pytest`) with the socket guard on; record counts against T001 in run-state.md (SC-007)
- [X] T050 Walk quickstart.md §1–3 with the fixture snapshot (estimate official layout, byte-identical JSON, stale warning with `--as-of 2027-06-01`, local prebuild and page check); fix any mismatch between docs and behaviour

---

## Phase 7: Owner step (not the agent; non-blocking for the agent)

- [ ] T051 **OWNER (not the agent; does not block the agent's completion)**: check src/data/bricklink_api.json against the live BrickLink API pages and Terms of Use and set `checked: true` with the date; then, with the four `BRICKLINK_*` variables set on a machine the token's IP allows, run `poetry run lego-image-processor parts prices fetch -o src/lego_image_processor/data/bricklink_price_guide.json` from `cli/` (rerun with `--resume` if it stops), review, confirm no `*.progress.json` is staged, run `poetry run pytest tests/unit/prices/test_packaged_snapshot.py` (now runs instead of skipping), and commit `bricklink_price_guide.json`. Merge gate for the branch and prerequisite for `docker build` with prices (quickstart §4)

---

## Dependencies and execution order

- Phase 1 → Phase 2 → US1 (Phase 3) → US2 (Phase 4) → US3 (Phase 5) → Polish (Phase 6).
- US1 depends only on Phase 2 (it reads any valid snapshot, e.g. the fixture).
- US2 depends only on Phase 2 (snapshot model and writer, lot sets); it does not need US1, but
  T036 also runs `parts estimate` on the fetched snapshot, so it is scheduled after US1.
- US3 depends on US1 (estimate library) and not on a real snapshot (tests use the fixture).
- T051 (owner) depends on US2 and gates only the merge and the Docker build, not any agent task.

Within phases: test task before the implementation it drives (T004→T005, T006→T007, T008→T009,
T013→T014, T015→T016, T018→T019, T023→T024, T025→T026, T027→T028, T030→T031, T034→T035,
T038→T039, T041→T042, T043→T044, T045→T046). T040 precedes T041.

## Parallel opportunities

- Phase 2: T004, T006, T008 (different test files) together; then T005, T007 together.
- US1: T013, T015, T018, T020, T021 test tasks together.
- US2: T023, T025, T027, T029 together; T024, T026, T028 together; T030 after T029.
- US3: T038, T043, T045 together after T040; T041 after T040.

## Implementation strategy

1. MVP = Phase 2 + US1: `parts estimate` prices any layout from a valid snapshot.
2. US2 makes the real snapshot possible; the owner then runs T051.
3. US3 shows the figures on the site; until T051 the Docker build stops at the prebuild by design.

# Run state: 011 price estimates

Source: prompt (2026-11-22): "Build a pricing tool for maps. The maintainer runs it locally during
map development; it gives an estimated price that is shown on the web site. The tool never runs in
the web app." plus 4 user answers to scoping questions:
1. Price source: official BrickLink API price guide, OAuth 1.0 (consumer key, consumer secret,
   token value, token secret) from environment variables; never committed, logged or written.
   BrickLink IDs from the cited tables (plate 4073 = LEGO 6141, tile 98138).
2. The site shows two estimates per map variant: every map piece (10,240) and only what is needed
   beyond one 31203 kit (the one-kit top-up).
3. Statistic: average price of NEW parts SOLD over the last 6 months, USD, low-high range from min
   and max sold prices; no sales -> current for-sale (stock) average, said so; no price -> unpriced,
   estimate marked incomplete with the unpriced piece count.
4. Delivery: `parts prices fetch` (keys + network) writes a dated, cited price snapshot JSON
   committed as runtime reference data; offline `parts estimate layout.json` (JSON + text, full and
   top-up); the web prebuild reads the snapshot offline via the CLI library into manifest and
   pages; the service stays file-only; tests offline with a fixture snapshot and mocked HTTP.
Phase: converge done (T001-T050 done; T051 is the owner's real fetch and commit)
Status: converged (no gaps, no tasks appended); waiting for owner step T051
Branch: 011-price-estimates
Updated: 2026-11-22

## Open questions
- (owner, after deploy) Check the BrickLink API Terms of Use when bricklink.com is back, and the
  attribution wording.
- (owner, before the first real fetch) Check `data/bricklink_api.json` (base URL, price-guide
  parameters, response shape research R4, error codes R7, daily limit) against the live API docs;
  set `checked: true`. Archived doc pages are JS shells, so nothing could be checked on 2026-11-22.
  Also check: whether errors come as HTTP status or `meta.code` under HTTP 200 (both handled); the
  daily-limit wording (markers in `prices/fetch.py` `DAILY_LIMIT_MARKERS`; if it differs, a 429 is
  retried and stops with exit 5, a 403 would be reported as rejected credentials); that prices are
  4-place strings; `unit_quantity: 0` for no data. Smoke check first: quickstart §4 one-lot fetch.
- (owner, merge gate) Run `parts prices fetch` and commit `data/bricklink_price_guide.json`
  before merging; until then `docker build` fails at the prebuild by design.

## Decisions
- clarify escalations: ship prices now, assuming the terms allow it; qty-weighted average; names as
  proposed; constitution VI satisfied by keeping the documented API's URL in reference data (user)
- scoping: price source = BrickLink API price guide, OAuth 1.0 credentials in env vars, never
  committed/logged/written (user)
- scoping: site shows two estimates per variant, full and one-kit top-up (user)
- scoping: statistic = 6-month new sold average, USD, min-max range; stock-average fallback;
  otherwise unpriced and estimate incomplete (user)
- scoping: delivery = online fetch -> committed snapshot in data/; offline `parts estimate`; web
  prebuild reads snapshot offline; service file-only; offline tests with fixture + mocked HTTP (user)
- specify: branch `011-price-estimates` from main 77e0c6c. Renumbered from 010 because worktree
  `98138_world-009` is actively building `010-pacific-arrangements` (agent)
- specify: default lot set = lots used by bundled recipes in any combination (19 today: 10 plate,
  9 tile), derived from recipes; option adds all cited colors (84) (agent)
- specify: "average" = quantity-weighted `qty_avg_price`; plain `avg_price` recorded too (agent,
  FOR OWNER REVIEW)
- specify: worldwide, VAT excluded, no region filter (agent)
- specify: staleness threshold 90 days, configurable; reference date injectable for tests (agent)
- specify: pacing 1 request/s, backoff on 429/5xx, stop on auth and daily-limit errors, progress
  saved per lot, `--resume`; snapshot marked complete only when every lot fetched (agent)
- specify: decimal arithmetic, round half-up to cents at the end; site shows whole dollars (agent)
- specify: parts list format unchanged (no prices); PRICE_NOTE text points to `parts estimate`
  (supersedes 005 FR-018) (agent)
- specify: prebuild fails without a snapshot or with a partial one unless explicitly allowed (agent)
- specify: proposed names `parts prices fetch`, `parts estimate`, `bricklink_price_guide.json`,
  env vars `BRICKLINK_CONSUMER_KEY/_CONSUMER_SECRET/_TOKEN_VALUE/_TOKEN_SECRET` (agent; CLI flags
  and file formats are reserved, confirm at plan)

- clarify: snapshot reaches the image as CLI package data (build stage `pip install ./cli`);
  fixture excluded by `.dockerignore` (agent; Dockerfile, .dockerignore)
- clarify: manifest = per-variant `estimates.full`/`estimates.one_kit` + top-level `prices` block;
  optional keys, format_version stays "1"; catalog checks both estimates when `prices` present; no
  new file kind (agent; follows prebuild `summary`/`price_note` and catalog validation pattern)
- clarify: one-kit top-up = `build_parts_list(owned=OwnedInputs(kits=1))` lot `to_buy`; estimate
  accepts parts lists so prebuild reuses `full`/`topup`; `parts estimate` has no owned/missing/
  spares options this feature (agent; parts/partslist.py, prebuild.py 157-159)
- clarify: HTTP via stdlib `urllib.request` with injectable opener (agent; datasets/cache.py)
- clarify: OAuth 1.0 HMAC-SHA1 hand-written with stdlib, tested on RFC 5849 vectors;
  requests-oauthlib rejected (new runtime deps + hashed build requirements for ~50 lines) (agent)
- clarify: BrickLink API base URL kept in cited reference data, not code; public documented API
  read as not "proprietary" under constitution VI; plan's Constitution Check records it (agent,
  FOR OWNER REVIEW)
- clarify: fixtures in `cli/tests/fixtures/prices/` (synthetic snapshot + `.source.json` +
  synthetic API responses); web tests pass the fixture path to `build_site` (agent; fixture
  conventions, web/tests/conftest.py)
- clarify: no estimate download file on the site; manifest and pages only (agent; user answer 4)

- plan: new subpackage `lego_image_processor/prices/` (api_config, oauth1, credentials, lots,
  snapshot, fetch, estimate, text); `parts` stays network-free and never imports `prices` (agent;
  follows `sheets/` for 006 and the `parts/__init__` "no network" promise)
- plan: commands registered on the existing `parts` group from new `cli/prices.py` (agent; user-
  approved names `parts estimate`, `parts prices fetch`)
- plan: API base URL, path template, `P -> PART`, OAuth method, daily limit in new cited
  `data/bricklink_api.json` with `checked: false` until the owner verifies (agent; implements the
  user's constitution VI decision; `part_numbers.json` loader pattern)
- plan: default lot set derived from recipes' declared colors + shadow color, no map builds
  (19 lots, 84 all-cited, verified 2026-11-22) (agent; recipe parsing already validates colors)
- plan: new flags beyond the approved names: estimate `--prices`, `--as-of`, `--stale-days`,
  `--format`, `-o`, `--lines`, `-q`; fetch `-o` (required), `--all-colors`, `--lot PART:LEGO_ID`,
  `--resume`, `--write-partial`, `--interval`, `--max-attempts`, `--compare`, `-q`; prebuild
  `--prices`, `--no-prices`, `--allow-partial-prices` (agent; follows 005 option style)
- plan: exit codes 0/1/2 as 005; 5 network/API/rate/daily limit (as 004 FetchError); 7 credentials
  rejected (new) (agent)
- plan: fetch `-o` required (no write into an installed package by default) (agent)
- plan: progress file `<output stem>.progress.json`, atomic rewrite per lot, fingerprint check on
  `--resume`; on a stop the output is untouched unless `--write-partial` (agent; a committed
  complete snapshot is never replaced by a partial one)
- plan: pacing 1 req/s; retries 2/4/8/16 s or Retry-After (cap 60 s), 5 attempts; 401/403 stop
  (exit 7); daily limit stop (exit 5); 404 -> lot "not found" (unpriced), run continues (agent)
- plan: money as Decimal; JSON money as strings; unit/line exact, totals half-up to cents, whole
  dollars computed by the library and written as ints so the service never rounds (agent)
- plan: estimate JSON has no generation time; staleness block records `as_of` (default UTC today);
  output is a pure function of layout, snapshot, as_of, threshold (agent; FR-015 vs FR-017)
- plan: snapshot stores per-lot aggregates only (no `price_detail`), allow-listed keys, unknown
  keys rejected on load (agent; FR-001 no credentials, size)
- plan: Dockerfile unchanged; prebuild requires the packaged snapshot by default and fails until
  the owner commits it; no `--no-prices` build arg; merge gate = committed complete snapshot;
  packaged-snapshot test skips while absent; `.gitignore`/`.dockerignore` add `*.progress.json`
  (agent; simplest safe path, spec US3-7 "never silently drop prices")
- plan: manifest estimates carry totals, whole dollars, counts, complete, nothing_to_buy; no
  per-lot lines in the manifest (agent; FR-020 lists totals only)

- tasks: 51 tasks; order Phase 2 foundations -> US1 -> US2 -> US3 per owner priority; new
  `prices/wording.py` for shared constants (avoids snapshot/estimate import cycle); fixture generator
  `cli/tools/fixtures011/make_price_fixture.py`; packaged-snapshot test
  `cli/tests/unit/prices/test_packaged_snapshot.py`; T051 is the OWNER fetch-and-commit step,
  non-blocking for the agent (agent)
- analyze: snapshot `source` gains `disclaimer` (existing `test_every_data_file_source_has_disclaimer`
  checks every `data/*.json` and would fail on the committed snapshot); that test excludes
  `*.progress.json`; OAuth `oauth_timestamp` comes from wall-clock `now()`, never the monotonic
  pacing clock (research R2 was ambiguous); quickstart packaged-test path aligned; plan tree lists
  `wording.py` and the fixture tool; implementing tasks cite data-model fields; T045 checks the
  built site holds no API config, credentials or snapshot (FR-022) (agent)

- implement T001: baseline before changes: CLI 1035 passed (`.venv/bin/pytest -q`, Poetry not on
  this machine, uv venv used); web 77 passed. After T001-T022: CLI 1137 passed (+102), no failures (agent)
- implement: stock-only fixture tile lot is Medium Azur (LEGO 322), because US1-3 needs it inside
  the land-elevation build (whose tiles are Bright Bluish Green, Medium Azur, Earth Blue); the
  official layout therefore also has one stock lot (US1-1's "all 10 from sales" is not literal for
  the fixture; T022 checks hand sums per basis instead) (agent)
- implement: fixture lot set = 18 lots (official 10 + 8 land-elevation plates without Dark Brown);
  `lot_set.recipes` is always present (`[]` for kinds `named`/`all-cited`, required non-empty for
  `recipes`); `query` and `statistic` values are validated as the fixed constants (agent)
- implement: `load_snapshot` checks `format_version` before the other keys, so a newer file says so;
  unknown keys and missing keys are both rejected with the JSON path (agent)
- implement: estimate notes add the estimate's label to the "Incomplete" note, e.g. "Incomplete: 27
  pieces in 2 colors could not be priced (every piece)." / "(on top of one 31203 kit)", so the
  two notes differ; the table prints the full estimate's unpriced lots once (the top-up's are a
  subset; its count is in the table's unpriced column) (agent; contracts/estimate-format.md notes)
- implement: unverified lots in the estimate JSON carry `lego: {name, id}` with the layout's name
  and code (int when numeric) (agent; contracts/estimate-format.md)
- implement: `parts estimate -o` summary line: "Wrote price estimate PATH: every piece $A ($L-$H);
  on top of one kit: one kit covers every piece" (agent; contracts/cli.md "one summary line")
- implement: `parts estimate` reads the layout before the snapshot, so layout errors print exactly
  as `parts list` does (agent)

- implement T023-T037: CLI 1302 passed, 1 skipped (packaged snapshot absent) (+165 from 1137);
  `.venv/bin/pytest -q` (agent)
- implement: OAuth signing checked against RFC 5849 §1.2 (signature `MdpQcU8iPSUjWoN/UDMsK2sui9I=`)
  and §3.4.1 (normalized parameters and base string); the BrickLink vector is frozen. The §1.2
  example has no `oauth_version`, so `authorization_header` takes `realm=` and `version=None` as
  optional keywords (library extension of contracts/library-api.md; BrickLink requests send
  `oauth_version="1.0"` and `realm=""` from `bricklink_api.json`) (agent)
- implement: BrickLink error text (`meta.description`) can echo the consumer key (e.g.
  `TOKEN_IP_MISMATCHED: consumer: … IP: …`), so every BrickLink-supplied string is passed through a
  redactor that replaces the four credential values and their percent-encoded forms with
  `<redacted>` and is capped at 300 characters; the leak tests use a fixture that echoes the key and
  a mutation check (redactor disabled) makes 6 tests fail (agent; FR-006, SC-005)
- implement: error classification order: daily-limit markers ("daily", "per day", "quota",
  "24 hours" in `meta.message`/`description`) before 401/403 → AuthError, then 404 or
  `RESOURCE_NOT_FOUND` → lot "not found" (the stock request is skipped), 429/5xx → retry, other
  non-200 → exit 5; HTTP 200 with a non-JSON body (a maintenance page) is retried; strings are data
  in `prices/fetch.py` next to `classify` (agent; research R7, to recheck with the live docs)
- implement: auth hints: `TOKEN_IP_MISMATCHED` → the token's IP address setting; otherwise check the
  four variables, the token's IP and the machine clock (agent)
- implement: prices with more than 4 decimal places are rounded half-up to 4; a response with a
  missing field, another currency, a zero price or avg outside min..max stops with exit 5
  "unexpected BrickLink response" (no guessing) (agent)
- implement: Ctrl-C → `FetchInterrupted` (exit 130) with the progress/resume message, raised by
  the command as a `CommandError` (Click's default Abort would exit 1) (agent; contracts/cli.md)
- implement: `--write-partial` applies to retry/daily/unexpected-data stops and Ctrl-C, never to
  AuthError ("no snapshot written" for 401/403) (agent; contracts/cli.md)
- implement: stop message: "<cause>; N of M lots saved in P; no snapshot written. Resume with:
  <command with the same options>"; with 0 lots done: "Run the same command again to retry." (agent)
- implement: no `--dry-run` (not in the contracts); the owner's smoke check is a one-lot fetch,
  `parts prices fetch -o /tmp/smoke.json --lot 98138:140`, added to quickstart §4 (agent)
- implement: snapshot `source.api.documentation` copies all four documentation entries of
  `bricklink_api.json` (the contract example showed one) (agent)
- implement: fetch defaults (`default_opener`, `default_sleep`, `default_clock`, `utc_now`,
  `default_nonce`) are module globals resolved at call time so tests patch them in `prices.fetch`
  (agent; T034)
- implement: Ctrl-C contract test added (closes the T036 deferred finding for exit 130) (agent)

- implement T038-T050: CLI 1308 passed, 1 skipped (+6 from 1302; +273 from the T001 baseline of
  1035); web 109 passed (+32 from 77). `cli/.venv/bin/pytest -q`, `web/.venv/bin/pytest -q` (agent)
- implement: `EstimateReport.manifest_entry(kind)` returns exactly the contracts/web.md keys (label,
  totals strings, `whole_dollars` ints, pieces, complete, nothing_to_buy, unpriced, stock);
  `prices_block()` has `snapshot.lots` = lots in the file (None for a parsed, unloaded snapshot);
  an unknown kind is a ValueError (agent)
- implement: the prebuild loads the snapshot before building anything (missing, invalid or partial
  -> `PrebuildError`, no manifest written); the partial message names the lot counts and both
  `parts prices fetch --resume` and `--allow-partial-prices`; `--prices` and `--no-prices` are
  mutually exclusive (argparse exit 2) (agent)
- implement: catalog errors read "<map> <C>: estimates.full.whole_dollars.low: must be an integer,
  found '12'" / "...: missing"; bools are not accepted as integers; `estimates` without `prices`
  -> "estimates present but the manifest has no prices block" (agent)
- implement: the map page uses the manifest label "On top of one 31203 kit" (contracts/web.md sketch
  showed "On top of one kit"); the panel sits after the Downloads/Parts columns, full width, before
  Lots; a range with low == high reads "(range $7)"; Jinja filters `usd` and `plural` only format
  integers from the manifest (agent)
- implement: docs: CLAUDE.md feature 011 paragraph and `prices/`, `fixtures011` in Layout;
  `docs/vision.md` roadmap row 011; `cli/README.md` feature bullet and "Price estimates" section
  (replaces "No prices are estimated"); `docs/deploy.md` intro note, "Before you start" merge gate
  and a "Refreshing prices" section (agent)
- implement T050: quickstart §2 (table, byte-identical JSON, stale warning at 2027-06-01) and §3
  (prebuild fails without `--prices` with the contract message; with the fixture the page shows the
  panel) match; no doc changes needed (agent)

## Blocked tasks
(none)

## Deferred findings
- MEDIUM: SC-004 (default fetch < 5 min) is checked with a fake clock only (T036); the real
  duration is observed at the owner's fetch (T051).
- MEDIUM: FR-022 "runtime image MUST NOT contain credentials or fetch configuration" is checked on
  the built site directory (T045), not on the Docker runtime stage itself.
- LOW: single-sale range collapse (min == max) is tested on the web page (T045) but not in the CLI
  table (T015).
- LOW: the web page does not name which lots were priced from for-sale listings (the basis sentence
  says the fallback exists; the manifest carries only `stock` counts, per contracts/web.md).
- LOW: phone-width layout checked by CSS review (auto-fit grid, 16px gutter), not by a rendered
  screenshot.
- LOW: spec US3 "Why this priority" still mentions "the open terms-of-use question", which the
  user has since decided (ship now); wording only.
- LOW: while a stopped fetch's `*.progress.json` sits in `data/`, it is package data on disk; it
  is git- and docker-ignored (T002) but a local `pip install ./cli` would include it.

## Converge (2026-11-22)
- Checked FR-001..FR-023, SC-001..SC-007, US1-US3 acceptance scenarios, edge cases, plan and
  contracts/ (cli, library-api, snapshot, estimate, web) and constitution MUSTs against the code.
  No missing, partial, contradicting or unrequested work found; tasks.md unchanged.
- Not counted as gaps (owner/live API): T051, the packaged snapshot (its test skips until then),
  `bricklink_api.json` `checked: false`, Docker prebuild failing without a snapshot (by design).
- Suites: CLI 1308 passed, 1 skipped (packaged-snapshot test); web 109 passed. Offline.

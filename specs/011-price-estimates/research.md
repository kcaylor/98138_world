# Research: Price Estimates for Maps (011)

Each item: decision, rationale (with the repository evidence), alternatives. Decisions made by the
user are marked (user); all others are agent decisions logged in `run-state.md`.

## R1. HTTP client

**Decision**: stdlib `urllib.request` with an injectable `opener(request, timeout) -> response`,
as `datasets/cache.py` does (`_default_opener`, `opener=` parameter, `FakeResponse` in
`cli/tests/conftest.py`). The client builds a `urllib.request.Request` with the `Authorization`
header and `User-Agent: lego-image-processor (parts prices fetch)`; timeout 30 s per request.
`urllib.error.HTTPError` is caught and its status and body parsed like a normal response (BrickLink
also reports errors in the JSON `meta` block; R7).

**Rationale**: `cli/pyproject.toml` has no HTTP library; the existing fetch pattern is tested with
injected openers and the suite-wide socket guard.

**Alternatives**: `requests` + `requests-oauthlib` (rejected at clarify: new runtime deps and new
hashed entries in `web/requirements-build.txt` for about 50 lines).

## R2. OAuth 1.0 signing (RFC 5849)

**Decision**: `prices/oauth1.py`, pure functions:

- `percent_encode(s)`: RFC 5849 §3.6 (`urllib.parse.quote(s, safe="-._~")` on UTF-8).
- `base_string(method, url, params)`: §3.4.1: uppercase method, base URI (scheme and host
  lowercased, default port dropped, no query), normalized parameters (§3.4.1.3.2: encode names and
  values, sort by name then value, join `=` and `&`) over the query parameters plus the `oauth_*`
  protocol parameters (without `oauth_signature`).
- `hmac_sha1(base, consumer_secret, token_secret)`: key `enc(cs) & enc(ts)`, base64 digest.
- `authorization_header(method, url, query, credentials, *, nonce, timestamp)`:
  `OAuth realm="", oauth_consumer_key="…", oauth_token="…", oauth_signature_method="HMAC-SHA1",
  oauth_timestamp="…", oauth_nonce="…", oauth_version="1.0", oauth_signature="…"` with each value
  percent-encoded. Nonce from `secrets.token_hex(16)` and timestamp = Unix seconds of the
  injectable wall-clock `now()` (UTC), never the monotonic pacing `clock`; both injectable for tests.

Tests: the RFC 5849 §1.2 worked example (HMAC-SHA1 over a GET with query parameters, consumer
`dpf43f3p2l4k3l03`, token `nnch734d00sl2jdk`) and the §3.4.1 example (base string and parameter
normalization with repeated and encoded names), with expected strings copied from the RFC text
during implementation; plus fixed-nonce/timestamp vectors for a BrickLink price-guide URL whose
expected header is computed once and frozen.

**Rationale**: about 50 lines with the stdlib; the RFC gives published vectors.

**Alternatives**: `oauthlib` (dependency, rejected at clarify).

## R3. Where the BrickLink API URL lives (constitution VI)

**Decision (user)**: a publicly documented API is not a proprietary endpoint; its URL lives in
cited reference data, not in code. **Agent design**: a new packaged file
`data/bricklink_api.json` (contracts/price-snapshot-format.md §2) with the base URL
`https://api.bricklink.com/api/store/v1`, the price-guide path template
`/items/{type}/{no}/price`, the item-type map `P → PART`, the OAuth method, the documented daily
limit, and a `source` block citing the documentation pages (`https://www.bricklink.com/v3/api.page`,
`?page=get-price-guide`, `?page=auth`, `?page=error-handling`) with an `accessed` date and a
`checked` flag. Loader `prices/api_config.py` validates it (https base URL, path placeholders,
disclaimer) like `kit/part_numbers.py` does. The fetch copies the `api` block into the snapshot.

**Finding (2026-11-22)**: bricklink.com was in maintenance. The Internet Archive has captures of
the documentation pages (for example `web.archive.org/web/20260124001504/https://www.bricklink.com/v3/api.page?page=get-price-guide`,
`…/20251109104636/…?page=auth`, `…/20220412111838/…?page=error-handling`), but each is a 5 kB
JavaScript shell (`Api.build.js` renders the content) and the bundle itself is not archived, so the
response shape below could not be checked against an archived copy. The file therefore ships
with `"checked": false` and the owner checks the URL, parameters and error codes against the live
pages before the first real fetch (run-state open question). `parts prices fetch` prints one line
when `checked` is false ("API details not yet checked against the live documentation").

**Alternatives**: constant in `prices/fetch.py` (rejected by the user's decision); environment
variable for the URL (needless setup; the URL is public).

## R4. BrickLink price guide request and response (from the documented API; verify live)

Request, one per lot and guide type:

```
GET {base_url}/items/PART/{item_no}/price?color_id={bl_color_id}&guide_type={sold|stock}
    &new_or_used=N&currency_code=USD&vat=N
```

No `country_code` or `region` (worldwide). Parameters in that fixed order in the URL; the
signature uses normalized order anyway.

Response (documented shape, from knowledge of the API; **to be verified against the live docs**):

```json
{"meta": {"description": "OK", "message": "OK", "code": 200},
 "data": {"item": {"no": "98138", "type": "PART"}, "new_or_used": "N", "currency_code": "USD",
          "min_price": "0.0100", "max_price": "1.5000", "avg_price": "0.0812",
          "qty_avg_price": "0.0431", "unit_quantity": 812, "total_quantity": 90412,
          "price_detail": [{"quantity": 100, "unit_price": "0.0400", "...": "..."}]}}
```

Prices are fixed-point decimal strings (up to 4 places) and are parsed with `Decimal(str)`, never
float; if the live API returns JSON numbers, they are parsed with `json.loads(...,
parse_float=Decimal)` so no binary rounding occurs. `unit_quantity` is the number of sales
(`sold`) or lots listed (`stock`); `total_quantity` the number of pieces. `price_detail` is not
stored (size; and the snapshot is per-lot aggregates only). A response with `unit_quantity == 0`
is "no data" for that guide type (`null` in the snapshot). Statistic used (user): `qty_avg_price`;
`avg_price` recorded too; range `min_price`–`max_price`.

## R5. Default lot set "every lot any bundled recipe uses in any combination"

**Decision**: derive from the recipes without building maps: for each recipe in
`maps.recipe.bundled_recipes()`, every color key in `land.colors` (part 6141) and `ocean.colors`
(part 98138), plus `shadow.color` on 98138 when `shadow.enabled`; resolve each through
`load_part_colors().get(part, key)` to the cited row (LEGO color ID, BrickLink color ID and
name), check the BrickLink name is on the part's catalog page (`part_numbers.bricklink_colors`,
the same rule as `parts/resolve.py`). Arrangements move whole frames and never change colors
(feature 007), so the union over recipes covers A, B and C. Checked on 2026-11-22: 19 lots
(10 plate, 9 tile); all cited colors: 84 (44 plate, 40 tile), all on the BrickLink part pages.

**Rationale**: no dataset or build is needed to know the lot set; recipe parsing already
validates every color key against `part_colors.json`. A declared but unused color costs two
requests and never under-covers (SC-001).

**Alternatives**: build all 18 variants and collect lots (needs every dataset, minutes of work,
for the same answer); hand list (rejected by FR-007).

## R6. Pacing, retry and stopping

**Decision**: one request at a time; at least `--interval` seconds (default 1.0) between request
starts, measured with an injectable monotonic `clock`; `sleep` injectable. Retry on HTTP 429, HTTP
5xx, BrickLink `meta.code` 429/5xx, and network errors (`URLError`, timeouts, connection reset):
delays 2, 4, 8, 16 s (or `Retry-After` seconds when given, capped at 60 s), at most
`--max-attempts` (default 5) attempts per request. Stop immediately (no retry) on HTTP or
`meta.code` 401/403 (authentication; exit 7) and on the daily-limit error (exit 5). After the
attempts run out: stop, keep progress, exit 5, print the resume command.

**Rationale**: FR-009; delays keep a default run under 5 min (38 requests ≈ 38 s plus latency).

**Alternatives**: concurrency (pointless at this size, impolite).

## R7. Error classification (verify live)

BrickLink reports errors in `meta` (`code`, `message`, `description`), sometimes with HTTP 200.
The client checks the HTTP status first, then `meta.code`. Known messages (from the documented
error-handling page, to verify): `BAD_OAUTH_REQUEST`, `TOKEN_IP_MISMATCHED` (token bound to
another IP; the error names BrickLink's "IP address" token setting), `INVALID_URI`,
`RESOURCE_NOT_FOUND`, `INVALID_REQUEST_BODY`, `PARAMETER_MISSING_OR_INVALID`, and a request-limit
message. Mapping: 401/403 → `AuthError` (exit 7; message = BrickLink code + message, never the
request headers); 404 or `RESOURCE_NOT_FOUND` → the lot gets `"error": "not found"` and no data
(unpriced), the run continues; 400 → `ApiError` exit 5 (a bad request is a tool bug, not a lot
property); a message containing the daily limit → `DailyLimitError` exit 5 with "resume tomorrow".
The exact strings live as data next to the classifier with a test per class, and are rechecked
with the docs.

## R8. Credentials and leak prevention

**Decision**: `Credentials` frozen dataclass read by `credentials_from_env(env=os.environ)` from
`BRICKLINK_CONSUMER_KEY`, `BRICKLINK_CONSUMER_SECRET`, `BRICKLINK_TOKEN_VALUE`,
`BRICKLINK_TOKEN_SECRET` (user). Missing or empty → `MissingCredentialsError` naming only the
variables, raised before any request (exit 1). `__repr__`/`__str__` return
`Credentials(<redacted>)`. The header is built inside the opener call and never stored, logged,
echoed or put in an exception message; error messages are built from BrickLink's `meta` and the
lot key only. The snapshot and progress file are built from parsed `data` fields only (allow-list
serialization), so no header or token can be copied in by accident.

**Test**: distinctive fake values (e.g. `CK-leakcheck-7f3a…`) for all four variables; every fetch
scenario (success, resume, 429, 5xx exhaustion, 401, IP mismatch, network failure, Ctrl-C) runs
with captured stdout/stderr, `caplog`, and a scan of every file under `tmp_path`; none may contain
any credential value, its percent-encoded form, or any `oauth_signature` value the mock opener
received (SC-005).

## R9. Progress and resume

**Decision**: progress file `<output stem>.progress.json` next to `--output` (for the packaged path:
`data/bricklink_price_guide.progress.json`), rewritten atomically (temp file + `os.replace`)
after each lot. It holds a `fingerprint` (SHA-256 of the canonical JSON of the API block, query
parameters and the ordered lot keys), `started_at`, and the finished lot entries in snapshot
format. `--resume` requires a progress file with the same fingerprint (else exit 1 naming the
difference) and skips its lots; without `--resume` an existing progress file is replaced (one
line says so). On completion the snapshot is written with `complete: true` and the progress file
deleted. On any stop the output file is left untouched (a committed complete snapshot is never
replaced by a partial one) unless `--write-partial`, which writes `complete: false` with the
lots fetched so far. `*.progress.json` is added to `.gitignore` and `.dockerignore`.

## R10. Money arithmetic

**Decision**: `decimal.Decimal` everywhere, in a local context (`prec=28`); unit prices exactly as
BrickLink returns them; line values `quantity × unit` are exact (≤ 4 places); totals are exact
sums, quantized to `0.01` with `ROUND_HALF_UP` only at the end; whole dollars for the site are
`total.quantize(Decimal(1), ROUND_HALF_UP)` computed by the library and written to the manifest as
integers, so the service never rounds money. JSON carries money as strings (`"412.35"`), never
floats. A rounded line total is not shown in JSON; lines carry the exact value.

## R11. Determinism and staleness

**Decision**: snapshot JSON: fixed key order, lots sorted by (part order 6141 then 98138, LEGO
color ID), `indent=2`, `ensure_ascii=False`, trailing newline, as `PartsList.to_json`. Estimate JSON:
no generation time; it records the snapshot's own retrieval time and a `staleness` block with the
`as_of` date used, `age_days`, `threshold_days` and `stale`. The output is a pure function of
(layout bytes, snapshot bytes, `as_of`, threshold); `--as-of` defaults to today's UTC date.
Staleness is measured from the snapshot's `retrieved.finished_at` date. Same-day reruns are
byte-identical; tests pass `--as-of`.

## R12. One-kit top-up and library inputs

**Decision**: as clarified: `estimate_parts_lists(full, one_kit, snapshot, …)` takes the two
`PartsList` objects (quantities `needed` and `to_buy` respectively); `estimate_layout(layout, …)`
builds them with `build_parts_list(layout)` and `build_parts_list(layout,
owned=OwnedInputs(kits=1))`. The prebuild passes the `full` and `topup` lists it already builds
(`prebuild.py` `build_variant`). The function checks `full.owned.kits == 0` and
`one_kit.owned.kits == 1` with no owned/missing files or spares, and that both lists come from the
same layout (same `layout.sha256`), else `ValueError`.

## R13. Unpriced reasons

`no verified BrickLink IDs` (the 005 lot is unverified: `Lot.ids is None`; its 005 reason is
appended), `not in the price snapshot` (no entry for (part, LEGO color ID); the hint suggests
`parts prices fetch --all-colors`), `no BrickLink sales or listings` (entry with `sold` and
`stock` both null, or `error: not found`).

## R14. Web prebuild options and page

**Decision**: `build_site(..., prices_path=None, with_prices=True, allow_partial_prices=False,
today=None)`; CLI `--prices PATH`, `--no-prices`, `--allow-partial-prices`. Default loads the
packaged snapshot; absent → `PrebuildError` (exit 1) with the fix; partial without the flag →
`PrebuildError`. `with_prices=False` omits `prices` and `estimates` entirely (pages show no price
section). Display: whole dollars from the manifest integers, formatted with a thousands separator
by a Jinja filter (formatting only). The page links to `https://www.bricklink.com` (plain `<a>`,
allowed by `test_no_third_party_resources`).

## R15. PRICE_NOTE (FR-019)

New text: "Prices: none in this file. Estimate them offline with `lego-image-processor parts
estimate LAYOUT` (BrickLink price guide snapshot), or upload the list to BrickLink or Rebrickable
to price it." The parts-list format is unchanged otherwise; `test_parts_contract.py` line 43
changes to the new text. The site's download panel keeps showing `manifest.price_note`.

## R16. Packaged snapshot before the owner's fetch

See plan.md "Snapshot delivery and the Docker build": Dockerfile unchanged; the prebuild fails
until the snapshot is committed; merge gate; the packaged-snapshot validity test skips while the
file is absent. `parts estimate` without `--prices` and with no packaged snapshot exits 1: "no
price snapshot is packaged yet; pass --prices FILE or run `parts prices fetch`".

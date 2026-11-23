# Quickstart: Price Estimates for Maps (011)

Validation guide. Formats: [contracts/](contracts/). Run from `cli/` unless noted; the CLI is
`poetry run lego-image-processor` (or `.venv/bin/lego-image-processor`).

## 1. Tests (offline)

```bash
cd cli && poetry run pytest tests/unit/prices tests/integration/test_prices_estimate.py \
  tests/integration/test_prices_fetch.py tests/contract/test_prices_contract.py
poetry run pytest                      # whole CLI suite, socket guard on (SC-007)
cd ../web && .venv/bin/pytest          # web suite; prebuild uses the CLI fixture snapshot
```

Expected: all pass with no network; the packaged-snapshot test is skipped with "packaged snapshot
not committed yet" until §4 is done.

## 2. Estimate a layout from the fixture snapshot (US1)

```bash
FIX=tests/fixtures/prices/bricklink_price_guide.json
poetry run lego-image-processor map build official-31203 -o /tmp/official.json
poetry run lego-image-processor parts estimate /tmp/official.json --prices $FIX --as-of 2026-12-05
poetry run lego-image-processor parts estimate /tmp/official.json --prices $FIX --as-of 2026-12-05 -o /tmp/e1.json
poetry run lego-image-processor parts estimate /tmp/official.json --prices $FIX --as-of 2026-12-05 -o /tmp/e2.json
cmp /tmp/e1.json /tmp/e2.json && echo identical
```

Expected: "Every piece" with average/low/high, complete; "On top of one kit: One kit covers every
piece"; the estimate wording, BrickLink attribution and LEGO disclaimer last; identical files.
With `--as-of 2027-06-01` a staleness warning appears and the figures are unchanged.

A layout needing pieces beyond one kit (the land-elevation fixture build used by the integration
tests) shows a non-zero top-up, the Dark Brown lot as unpriced "not in the price snapshot" with the
`--all-colors` hint, and one tile lot "priced from current for-sale listings".

## 3. Web (US3)

```bash
cd web && .venv/bin/python -m web98138.prebuild --out /tmp/site --maps official-31203,ocean-sst \
  --prices ../cli/tests/fixtures/prices/bricklink_price_guide.json
WEB98138_SITE_DIR=/tmp/site .venv/bin/uvicorn web98138.app:app --port 8080
```

Open `http://localhost:8080/maps/ocean-sst/A`: the "Estimated cost" panel shows both estimates in
whole dollars, the price date, the BrickLink link, the estimate wording and attribution. Without
`--prices` the prebuild fails ("no price snapshot is packaged …") until §4; with `--no-prices` the
page has no price panel.

## 4. Owner: fetch and commit the real snapshot (US2; merge gate)

Before the first run, check `src/lego_image_processor/data/bricklink_api.json` against the live
BrickLink API pages (base URL, price-guide parameters, error codes, daily limit) and the API Terms
of Use; set `"checked": true` and the date. Then, on a machine whose IP the BrickLink token allows:

First a one-lot smoke check (2 requests, written outside the package): it confirms the
credentials, the token's IP setting and the response shape before the full run.

```bash
export BRICKLINK_CONSUMER_KEY=… BRICKLINK_CONSUMER_SECRET=… BRICKLINK_TOKEN_VALUE=… BRICKLINK_TOKEN_SECRET=…
poetry run lego-image-processor parts prices fetch -o /tmp/smoke.json --lot 98138:140
# expect: "[1/1] tile 98138 Earth Blue (BrickLink 98138 / Dark Blue, color 63): sold N sales, stock N lots"
# exit 7: credentials rejected (the message names the cause, e.g. the token's IP address setting)
# exit 5 "unexpected BrickLink response" or "not JSON": the API details need checking (R4, R7)
cat /tmp/smoke.json; rm /tmp/smoke.json /tmp/smoke.progress.json 2>/dev/null
```

Then the full run:

```bash
poetry run lego-image-processor parts prices fetch -o src/lego_image_processor/data/bricklink_price_guide.json
# if it stops: rerun the same command with --resume
git diff --stat; git status   # snapshot only; no *.progress.json
poetry run pytest tests/unit/prices/test_packaged_snapshot.py   # now runs instead of skipping, and passes
git add src/lego_image_processor/data/bricklink_price_guide.json && git commit
```

Expected: 19 lots (complete), a summary of lots priced from sales/stock/unpriced; the command
never prints the keys. Then `docker build .` succeeds again with prices on every page. Deploying
(`fly deploy`) is the owner's step (docs/deploy.md).

## 5. Refreshing prices later

Rerun §4; the summary lists the largest unit-price changes since the committed snapshot; review
and commit; redeploy. Pages warn once the snapshot is older than 90 days at build time.

# Contract: price data files (011)

Three files. All JSON is UTF-8, `indent=2`, keys in the order shown, trailing newline. Unknown
keys are rejected on load.

## 1. `data/bricklink_price_guide.json` (snapshot, format_version "1")

Written by `parts prices fetch`, committed by the owner, packaged with the CLI. Values below are
illustrative.

```json
{
  "format_version": "1",
  "source": {
    "title": "BrickLink price guide (BrickLink API)",
    "publisher": "LEGO BrickLink, Inc.",
    "url": "https://www.bricklink.com",
    "api": {
      "base_url": "https://api.bricklink.com/api/store/v1",
      "endpoint": "GET /items/{type}/{no}/price",
      "documentation": [
        {"id": "bricklink-api-price-guide", "title": "BrickLink API: Get Price Guide",
         "url": "https://www.bricklink.com/v3/api.page?page=get-price-guide"}
      ],
      "checked": false
    },
    "tool": {"name": "lego-image-processor", "version": "0.1.0", "command": "parts prices fetch"},
    "disclaimer": "Not affiliated with or endorsed by The LEGO Group."
  },
  "retrieved": {"started_at": "2026-12-01T18:02:10Z", "finished_at": "2026-12-01T18:03:05Z"},
  "query": {
    "new_or_used": "N", "currency_code": "USD", "vat": "N", "country_code": null, "region": null,
    "guide_types": {"sold": "sales in the last 6 months (BrickLink's fixed period)",
                    "stock": "items for sale at retrieval time"}
  },
  "statistic": {"average": "qty_avg_price", "low": "min_price", "high": "max_price",
                "also_recorded": ["avg_price"],
                "fallback": "stock when sold has no data; unpriced when neither has data"},
  "lot_set": {"kind": "recipes",
              "recipes": [{"id": "land-elevation", "sha256": "…"}, {"id": "ocean-sst", "sha256": "…"}],
              "count": 19},
  "complete": true,
  "lots": [
    {
      "part_id": "6141",
      "lego_color_id": 1,
      "color_key": "lego_white",
      "lego_color_name": "White",
      "bricklink": {"item_type": "P", "item_no": "4073", "color_id": 1, "color_name": "White"},
      "retrieved_at": "2026-12-01T18:02:11Z",
      "sold": {"qty_avg_price": "0.0385", "avg_price": "0.0612", "min_price": "0.0100",
               "max_price": "0.5000", "unit_quantity": 1204, "total_quantity": 380211},
      "stock": {"qty_avg_price": "0.0450", "avg_price": "0.0790", "min_price": "0.0100",
                "max_price": "2.0000", "unit_quantity": 3110, "total_quantity": 2104455},
      "error": null
    }
  ],
  "attribution": "Price data: BrickLink price guide (bricklink.com). BrickLink is a trademark of LEGO BrickLink, Inc. Not endorsed by BrickLink.",
  "estimate_note": "Estimate only; excludes shipping, fees and taxes; prices vary by seller and over time.",
  "disclaimer": "Not affiliated with or endorsed by The LEGO Group."
}
```

Rules (validated by `load_snapshot`, `SnapshotError` names the JSON path):

- `format_version == "1"`; `disclaimer`, `source.disclaimer`, `attribution`, `estimate_note` equal the
  library constants (`source.disclaimer` is what `test_every_data_file_source_has_disclaimer` checks
  for every `data/*.json`).
- `lots` sorted by (6141 before 98138, `lego_color_id`), keys unique; each lot's `color_key`,
  names, `bricklink.item_no` and `bricklink.color_id` equal the cited tables
  (`part_colors.json`, `part_numbers.json`).
- `sold` / `stock`: an object or `null`. Prices are decimal strings matching
  `^\d+(\.\d{1,4})?$`, each `> 0`; `min_price ≤ qty_avg_price ≤ max_price` and
  `min_price ≤ avg_price ≤ max_price`; `unit_quantity ≥ 1`, `total_quantity ≥ unit_quantity`.
- `error`: `null` or `"not found"` (then `sold` and `stock` are `null`).
- `retrieved_at` in `[started_at, finished_at]`; timestamps `YYYY-MM-DDTHH:MM:SSZ`.
- `complete` is true iff `len(lots) == lot_set.count`; for `kind: "recipes"`, the recipe list and
  hashes are those of the bundled recipes at fetch time (a later recipe change does not invalidate
  the file; `parts estimate` reports any lot not covered as unpriced).
- No field holds credentials, headers or signatures (allow-listed keys only).

## 2. `data/bricklink_api.json` (cited reference data, format_version "1")

Written by hand at implementation from the documentation (R3), not by a tool.

```json
{
  "format_version": "1",
  "source": {
    "title": "BrickLink Store API v1 documentation",
    "documentation": [
      {"id": "bricklink-api-price-guide", "title": "BrickLink API: Get Price Guide",
       "url": "https://www.bricklink.com/v3/api.page?page=get-price-guide"},
      {"id": "bricklink-api-auth", "title": "BrickLink API: Authorization",
       "url": "https://www.bricklink.com/v3/api.page?page=auth"},
      {"id": "bricklink-api-errors", "title": "BrickLink API: Error handling",
       "url": "https://www.bricklink.com/v3/api.page?page=error-handling"},
      {"id": "bricklink-api-terms", "title": "BrickLink API Terms of Use",
       "url": "https://www.bricklink.com/v3/api.page?page=terms"}
    ],
    "accessed": "2026-11-22",
    "checked": false,
    "note": "bricklink.com was in maintenance on 2026-11-22; values from the documented API, to be checked against the live pages before the first fetch.",
    "disclaimer": "Not affiliated with or endorsed by The LEGO Group."
  },
  "base_url": "https://api.bricklink.com/api/store/v1",
  "price_guide_path": "/items/{type}/{no}/price",
  "item_types": {"P": "PART"},
  "oauth": {"version": "1.0", "signature_method": "HMAC-SHA1", "realm": ""},
  "daily_request_limit": 5000
}
```

When the owner has checked the pages, `checked` becomes `true` and `accessed` the check date (a
one-line edit, reviewed in the PR).

## 3. `<output stem>.progress.json` (fetch progress; git- and docker-ignored)

```json
{
  "format": "price-progress-1",
  "fingerprint": "<sha256 of canonical JSON of {api, query, lot keys in order}>",
  "started_at": "2026-12-01T18:02:10Z",
  "lot_set": {"kind": "recipes", "recipes": [], "count": 19},
  "lots": ["<SnapshotLot objects as in §1>"]
}
```

Rewritten atomically after each lot; deleted when the snapshot is written complete.

## Test fixture: `cli/tests/fixtures/prices/`

- `bricklink_price_guide.json`: a valid snapshot with synthetic prices for the official layout's
  10 lots (White plate, 9 kit tile colors) and the `land-elevation` plate colors except one
  (Dark Brown: missing → "not in the price snapshot"), with one tile lot `sold: null` and `stock`
  present (stock fallback). `lot_set.kind: "named"`, `complete: true`. Real cited IDs.
- `bricklink_price_guide.source.json`: `{"fixture": …, "synthetic": true, "note": "Synthetic
  values for tests; not BrickLink data.", "generator": …, "disclaimer": …, "sha256": …}`.
- `api/price_<item>_<color>_<guide>.json`: synthetic responses in the R4 shape, plus
  `api/error_401_token_ip.json`, `api/error_429.json`, `api/error_daily_limit.json`,
  `api/not_found.json`, `api/no_sales.json` (`unit_quantity: 0`).

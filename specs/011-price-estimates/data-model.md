# Data Model: Price Estimates for Maps (011)

Python names are in `lego_image_processor.prices` unless noted. Money is `decimal.Decimal`
throughout; JSON forms are in [contracts/price-snapshot-format.md](contracts/price-snapshot-format.md)
and [contracts/estimate-format.md](contracts/estimate-format.md).

## ApiConfig (`data/bricklink_api.json`, loader `load_api_config()`)

| Field | Type | Rule |
|---|---|---|
| `base_url` | str | `https://` URL, no trailing slash, no query |
| `price_guide_path` | str | contains `{type}` and `{no}` |
| `item_types` | dict[str, str] | must map `P` → `PART` (005 `bricklink.item_type` is `P`) |
| `oauth` | dict | `version == "1.0"`, `signature_method == "HMAC-SHA1"` |
| `daily_request_limit` | int > 0 | documented limit (5,000) |
| `source` | dict | `title`, `documentation` list of `{id, title, url}`, `accessed` YYYY-MM-DD, `checked` bool, `disclaimer` == DISCLAIMER |

## Credentials

`consumer_key`, `consumer_secret`, `token_value`, `token_secret`: non-empty str from the four
`BRICKLINK_*` variables. Redacted `repr`. Never serialized. `MissingCredentialsError.names` lists
missing variable names.

## LotRef (lot key)

| Field | From |
|---|---|
| `part_id` | `"6141"` or `"98138"` (project part ID, as in 005 lots) |
| `lego_color_id` | int, `PartColor.lego.id` |
| `color_key` | `PartColor.key` (e.g. `lego_white`) |
| `lego_color_name` | `PartColor.lego.name` |
| `bricklink_item_type` / `bricklink_item_no` | `PartNumbers` (`P`, `4073` or `98138`) |
| `bricklink_color_id` / `bricklink_color_name` | `PartColor.bricklink` |

Identity: `(part_id, lego_color_id)`. Order: part (6141, 98138), then LEGO color ID.
Built only from the cited tables (`lot_ref(part_id, color_key)`), never typed in.

**Lot sets**: `recipe_lots()` (R5; 19 today), `all_cited_lots()` (84), `named_lots(["98138:140",
…])` (`PART:LEGO_COLOR_ID`; unknown → `ValueError`).

## GuideFigures (one lot, one guide type)

| Field | Type | Rule |
|---|---|---|
| `qty_avg_price` | Decimal | > 0; `min ≤ qty_avg ≤ max` |
| `avg_price` | Decimal | > 0; `min ≤ avg ≤ max` |
| `min_price`, `max_price` | Decimal | > 0, `min ≤ max` |
| `unit_quantity` | int ≥ 1 | sales (sold) or lots listed (stock) |
| `total_quantity` | int ≥ `unit_quantity` | pieces |

`None` in place of a GuideFigures means "no data returned" (`unit_quantity == 0` in the API).

## SnapshotLot

`lot: LotRef`, `sold: GuideFigures | None`, `stock: GuideFigures | None`, `retrieved_at` (UTC
`YYYY-MM-DDTHH:MM:SSZ`), `error: None | "not found"`.

Derived: `basis` = `sold` if `sold` else `stock` if `stock` else `unpriced`.

## PriceSnapshot (`bricklink_price_guide.json`)

| Field | Rule |
|---|---|
| `format_version` | `"1"` |
| `source` | title, publisher, url, `api` (copied ApiConfig: base_url, path, documentation URLs, checked), `tool` {name, version, command}, `disclaimer` == DISCLAIMER |
| `retrieved` | `started_at`, `finished_at` (UTC); `finished_at ≥ started_at`; every lot's `retrieved_at` within them |
| `query` | `new_or_used: "N"`, `currency_code: "USD"`, `vat: "N"`, `country_code: null`, `region: null`, `guide_types` {sold, stock} with period text |
| `statistic` | `average: "qty_avg_price"`, `low: "min_price"`, `high: "max_price"`, `also_recorded: ["avg_price"]` |
| `lot_set` | `kind` (`recipes`, `all-cited`, `named`), `recipes` [{id, sha256}] for `recipes`, `count` |
| `complete` | bool; true iff every lot of the lot set has an entry |
| `lots` | SnapshotLot list, sorted, unique keys, `len == lot_set.count` when complete |
| `attribution`, `estimate_note`, `disclaimer` | fixed texts (ATTRIBUTION, ESTIMATE_NOTE, DISCLAIMER) |

Load-time validation (FR-003; `SnapshotError` with the JSON path): the rules above; each lot's
BrickLink item number and color ID equal `lot_ref(part_id, ...)` from the cited tables; no
unknown keys anywhere (so no credential or header field can be present); the file's SHA-256 is
recorded on the loaded object (`sha256`, `file_name`, `path`, `packaged`).

State: `(no file) → in progress (progress file only) → complete` or `→ partial (complete=false,
only with --write-partial)`. A partial snapshot loads, with `complete == false`.

## FetchProgress (`<output stem>.progress.json`)

`format: "price-progress-1"`, `fingerprint` (R9), `started_at`, `lot_set`, `lots` (finished
SnapshotLot entries). Never contains credentials. Deleted on completion.

## EstimateLine

| Field | Rule |
|---|---|
| `lot` | the 005 `Lot` (verified or not) |
| `quantity` | `needed` (full) or `to_buy` (one-kit); lines exist only for quantity > 0 |
| `basis` | `sold`, `stock`, `unpriced` |
| `reason` | for `unpriced`: R13 text; else None |
| `unit` | (average, low, high) from the basis's GuideFigures, or None |
| `line` | `quantity × unit` for each, exact, or None |
| `figures` | the GuideFigures used (for counts in output) |

## Estimate (one of `full`, `one_kit`)

`kind` (`full` | `one_kit`), `owned_kits` (0 | 1), `lines`, and derived: `totals` (average, low,
high: exact sums quantized half-up to cents), `whole_dollars` (half-up to $1), `pieces`,
`lots`, `by_basis` {sold, stock, unpriced}: {lots, pieces}, `complete` (no unpriced line),
`nothing_to_buy` (no lines; then totals are 0.00 and the text is "One kit covers every piece").

Invariants: `low ≤ average ≤ high`; `pieces == sum(quantity)`; for `full`, `pieces` equals the
parts list `needed` total; for `one_kit`, the parts list `to_buy` total.

## EstimateReport

`layout` (the 005 `PartsList.layout` block, unchanged), `snapshot` reference (file name, path or
`packaged`, SHA-256, retrieved finished_at, complete, source title and URL, statistic, query),
`staleness` {as_of, age_days, threshold_days, stale}, `estimates` {full, one_kit}, `notes` (stale,
partial, unpriced hint, stock fallback count), `estimate_note`, `attribution`, `disclaimer`.
`to_dict()`, `to_json()`, `manifest_entry(kind)` (web subset, contracts/web.md).

## Relationships

```
recipes ──R5──▶ LotRef* ──fetch──▶ PriceSnapshot ◀── load_snapshot (validated vs cited tables)
layout ──005 build_parts_list──▶ PartsList(full), PartsList(kits=1)
PartsLists + PriceSnapshot ──estimate──▶ EstimateReport ──▶ table / JSON / manifest
```

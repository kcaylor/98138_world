# Contract: web additions (011)

Extends `specs/008-web-app/contracts/routes.md` and the 008 manifest (data-model.md). Routes,
download kinds (`KINDS`) and manifest `format_version` ("1") are unchanged.

## Prebuild

`python -m web98138.prebuild --out DIR [--fetch] [--prices FILE | --no-prices] [--allow-partial-prices]`

| Option | Meaning |
|---|---|
| (default) | load the packaged snapshot through `lego_image_processor.prices.load_snapshot()` |
| `--prices FILE` | another snapshot (tests pass `cli/tests/fixtures/prices/bricklink_price_guide.json`) |
| `--no-prices` | build without estimates: no `prices` block, no `estimates` keys, no price panel |
| `--allow-partial-prices` | accept a snapshot with `complete: false` (its pages say it is partial) |

Library: `build_site(out, maps=None, combinations=None, *, cache_dir=None, fetch=False,
echo=print, prices_path=None, with_prices=True, allow_partial_prices=False, today=None)`.
`today` (a `date`) is the staleness reference (default: UTC today).

Errors (exit 1, `PrebuildError`, nothing served is changed): no packaged snapshot ("no price
snapshot is packaged (lego_image_processor/data/bricklink_price_guide.json); run `parts prices
fetch` and commit it, or build with --no-prices"); invalid snapshot (the `SnapshotError` text);
partial snapshot without `--allow-partial-prices`.

Never opens the network for prices; `--fetch` is still datasets only.

## Manifest additions

Top level, once (present iff built with prices):

```json
"prices": {
  "snapshot": {"file": "bricklink_price_guide.json", "sha256": "1a2b…",
               "retrieved_at": "2026-12-01T18:03:05Z", "retrieved_on": "2026-12-01",
               "complete": true, "lots": 19},
  "source": {"title": "BrickLink price guide (BrickLink API)", "url": "https://www.bricklink.com"},
  "basis": "Average price of new parts sold on BrickLink in the last 6 months (quantity-weighted), US dollars; range from the lowest to the highest sale. Lots with no sales use the current for-sale average.",
  "estimate_note": "Estimate only; excludes shipping, fees and taxes; prices vary by seller and over time.",
  "attribution": "Price data: BrickLink price guide (bricklink.com). BrickLink is a trademark of LEGO BrickLink, Inc. Not endorsed by BrickLink.",
  "staleness": {"as_of": "2026-12-05", "age_days": 4, "threshold_days": 90, "stale": false}
}
```

Per variant, next to `summary`, in `maps[].variants[C]`:

```json
"estimates": {
  "full":    {"label": "Every piece", "totals": {"average": "412.35", "low": "260.10", "high": "1150.00"},
              "whole_dollars": {"average": 412, "low": 260, "high": 1150},
              "pieces": 10240, "complete": true, "nothing_to_buy": false,
              "unpriced": {"lots": 0, "pieces": 0}, "stock": {"lots": 1, "pieces": 312}},
  "one_kit": {"label": "On top of one 31203 kit", "...": "same keys"}
}
```

Produced by `EstimateReport.manifest_entry("full" | "one_kit")` (the prebuild only copies it).
Per-lot lines are not in the manifest (the CLI's JSON has them).

## Catalog check (`catalog.py`, at start-up)

When `prices` is present: it has `snapshot.sha256` (64 hex), `snapshot.retrieved_on`,
`source.url`, `estimate_note`, `attribution`; every variant of every map has `estimates.full` and
`estimates.one_kit`, each with `whole_dollars.{average,low,high}` integers, `complete` and
`nothing_to_buy` booleans and `unpriced.pieces`/`unpriced.lots` integers. Any failure →
`CatalogError` naming map, combination and key. When `prices` is absent, `estimates` keys must be
absent too. The catalog still never imports `lego_image_processor`.

## Map page (`/maps/{id}/{C}`)

A panel "Estimated cost" after the Parts panel, only when `manifest.prices` is present:

```
Estimated cost
  Every piece           about $412   (range $260–$1,150)
  On top of one kit     about $96    (range $55–$310)        | "One kit covers every piece"
  Incomplete: 312 pieces in 1 color could not be priced.       (per estimate, when not complete)
  Prices from 2026-12-01: <basis>. Source: <a href="https://www.bricklink.com">BrickLink price guide</a>.
  These prices are from 2026-12-01 and may be out of date.     (when staleness.stale)
  The price snapshot is partial.                               (when snapshot.complete is false)
  Estimate only; excludes shipping, fees and taxes; prices vary by seller and over time.
  Price data: BrickLink price guide (bricklink.com). BrickLink is a trademark of LEGO BrickLink, Inc. Not endorsed by BrickLink.
```

Whole dollars come from the manifest integers; a Jinja filter `usd` only adds `$` and thousands
separators. A range whose low equals its high shows one value. The footer disclaimer is unchanged.
No JavaScript, no cookies, no third-party resources (the BrickLink link is a plain `<a>`).

The home page is unchanged (no prices on cards).

## Docker

`Dockerfile` unchanged (plan.md "Snapshot delivery"): the build stage's `pip install ./cli`
installs the snapshot as package data and the default prebuild requires it. `.dockerignore` adds
`**/*.progress.json`. The runtime stage gets only `/site` and the web wheel: no CLI, no
`bricklink_api.json`, no credentials.

# Contract: library API (011)

```python
from lego_image_processor.prices import (
    # reference data and constants
    load_api_config,        # (path=None) -> ApiConfig; raises ValueError on an invalid file
    ATTRIBUTION, ESTIMATE_NOTE, BASIS_TEXT, DEFAULT_STALE_DAYS,  # 90
    PACKAGED_SNAPSHOT_PATH, # data/bricklink_price_guide.json

    # lots
    LotRef, lot_ref,        # (part_id, color_key) -> LotRef from the cited tables
    recipe_lots,            # (recipes=None) -> tuple[LotRef, ...]   bundled recipes' colors (R5)
    all_cited_lots,         # () -> tuple[LotRef, ...]               84 today
    parse_lot,              # ("98138:140") -> LotRef; ValueError if not cited

    # snapshot
    PriceSnapshot, SnapshotLot, GuideFigures,
    load_snapshot,          # (path=None) -> PriceSnapshot; raises SnapshotMissingError (packaged absent),
                            #   SnapshotError (unreadable/invalid; message names the JSON path)
    snapshot_to_json,       # (PriceSnapshot) -> str, deterministic
    largest_changes,        # (old, new, n=5) -> list of (LotRef, old_avg, new_avg, pct)

    # estimating (offline)
    estimate_parts_lists,   # (full: PartsList, one_kit: PartsList, snapshot, *, as_of: date,
                            #   stale_days=90) -> EstimateReport; ValueError if the lists don't match R12
    estimate_layout,        # (layout: LayoutInput | PositionPlacementGrid, snapshot, *, as_of, stale_days=90,
                            #   layout_path=None, layout_sha256=None) -> EstimateReport
    Estimate, EstimateLine, EstimateReport,  # .to_dict(), .to_json(), .manifest_entry(kind), .prices_block()

    # fetching (online; only the CLI's `parts prices fetch` calls this)
    Credentials, credentials_from_env, MissingCredentialsError,
    fetch_snapshot,         # (lots, credentials, *, output: Path, lot_set: dict, resume=False,
                            #   write_partial=False, interval=1.0, max_attempts=5, api=None,
                            #   opener=None, sleep=time.sleep, clock=time.monotonic,
                            #   now=utc_now, nonce=secrets.token_hex, echo=None) -> FetchResult
    FetchResult,            # snapshot, fetched, reused, path, progress_path
    PriceFetchError,        # base; .exit_code 5; .progress_path, .done, .total
    AuthError,              # exit_code 7
    DailyLimitError,        # exit_code 5
    ProgressMismatchError,  # exit_code 1
)
from lego_image_processor.prices.oauth1 import (
    percent_encode, base_string, hmac_sha1_signature,
    authorization_header,   # (method, url, query: list[tuple[str,str]], credentials, *, nonce, timestamp) -> str
)
```

- `opener(request: urllib.request.Request, timeout: float)` returns an object with `.status`
  (or `.getcode()`), `.headers` and `.read()`; it may raise `urllib.error.HTTPError` (parsed as a
  response) or `URLError`/`OSError` (retried). Default: `urllib.request.urlopen`.
- `echo(line: str)` receives progress lines; nothing passed to it contains secrets.
- No function outside `fetch_snapshot` and the default opener touches the network.
- `parts` does not import `prices`; `prices` imports `parts.build_parts_list`, `parts.OwnedInputs`,
  `kit` loaders and `maps.recipe.bundled_recipes/load_recipe`.
- `EstimateReport.prices_block()` returns the manifest's top-level `prices` block;
  `manifest_entry(kind)` the per-variant `estimates[kind]` (contracts/web.md).

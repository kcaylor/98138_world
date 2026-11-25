# Contract: CLI (011)

Both commands are registered on the existing `parts` group. All human output ends with
`Not affiliated with or endorsed by The LEGO Group.`; JSON carries `"disclaimer"`. `-q` suppresses
human output (errors still go to stderr, followed by the disclaimer, as `CommandError` does).

Exit codes (extending 004/005): 0 ok; 1 input error (layout, snapshot, output directory, missing
credential variable, bad `--lot`, progress mismatch); 2 Click usage; 5 network or API failure
after retries, rate or daily limit (progress kept); 7 credentials rejected by BrickLink
(401/403, IP mismatch).

## `parts estimate LAYOUT` (offline)

| Option | Meaning |
|---|---|
| `--prices FILE` | price snapshot (default: the packaged `bricklink_price_guide.json`) |
| `--as-of YYYY-MM-DD` | date staleness is judged against (default: today, UTC) |
| `--stale-days N` | staleness threshold, integer ≥ 1, default 90 |
| `--format table\|json` | default table (stdout) |
| `-o, --output PATH` | write JSON (implies json); prints one summary line and the disclaimer |
| `--lines` | table also lists every lot line for both estimates (default: totals, unpriced and fallback lots only) |
| `-q` | quiet |

No `--kits`, `--owned`, `--missing`, `--spares` (spec Q: always full and one-kit top-up).
Never opens the network; needs no credentials.

Human output, in order:

```
Price estimate for layout.json (recipe land-elevation; 10,240 positions; map pieces only)
Prices: BrickLink price guide, retrieved 2026-12-01 (6-month average of new parts sold, USD,
quantity-weighted; range from lowest to highest sale). Snapshot bricklink_price_guide.json
(SHA-256 1a2b3c4d…), complete.

                       average      low      high   pieces  lots  priced from stock  unpriced
Every piece            $412.35   $260.10  $1,150.00  10,240    19   1 lot, 312 pcs      0
On top of one kit       $96.40    $55.22    $310.75   2,104     8   0                   0

Warning: prices are from 2026-12-01, 120 days before 2027-03-31; they may be out of date.   (when stale)
Warning: the snapshot is partial (17 of 19 lots).                                            (when partial)
Incomplete: 312 pieces in 1 color could not be priced:                                       (when unpriced)
  plate 6141 Dark Brown (LEGO 308): not in the price snapshot; 312 pieces
  Hint: fetch every cited color with: lego-image-processor parts prices fetch --all-colors
Priced from current for-sale listings (no sales in 6 months): tile Vibrant Coral (LEGO 353)
Estimate only; excludes shipping, fees and taxes; prices vary by seller and over time.
Price data: BrickLink price guide (bricklink.com). BrickLink is a trademark of LEGO BrickLink, Inc.
Not endorsed by BrickLink.
Not affiliated with or endorsed by The LEGO Group.
```

A top-up with nothing to buy prints `On top of one kit   One kit covers every piece`.
Exit 0 for incomplete, stale or partial estimates (they are warnings).

Errors (exit 1, nothing written): layout errors as `parts list`; snapshot missing ("no price
snapshot is packaged yet; pass --prices FILE or run `lego-image-processor parts prices fetch`"),
unreadable, not JSON, or invalid (`SnapshotError` with the JSON path and rule); output directory
missing.

## `parts prices fetch` (online, maintainer)

| Option | Meaning |
|---|---|
| `-o, --output PATH` | required; the snapshot to write (the maintainer passes `src/lego_image_processor/data/bricklink_price_guide.json` from `cli/`) |
| `--all-colors` | every cited plate and tile color (84 lots) instead of the recipes' lots (19) |
| `--lot PART:LEGO_COLOR_ID` | repeatable; fetch only these lots (lot set kind `named`); excludes `--all-colors` |
| `--resume` | reuse lots in `<output stem>.progress.json` fetched with the same parameters |
| `--write-partial` | on a stop, also write the snapshot with `complete: false` from the lots fetched |
| `--interval SECONDS` | minimum time between request starts, default 1.0, ≥ 0.5 |
| `--max-attempts N` | attempts per request on 429/5xx/network errors, default 5, 1–10 |
| `--compare FILE` | previous snapshot for the change summary (default: the existing `--output` file if valid, else the packaged snapshot if any) |
| `-q` | quiet (summary and errors only) |

Credentials: `BRICKLINK_CONSUMER_KEY`, `BRICKLINK_CONSUMER_SECRET`, `BRICKLINK_TOKEN_VALUE`,
`BRICKLINK_TOKEN_SECRET`. Missing or empty → exit 1 before any request:
`Error: missing environment variable(s): BRICKLINK_TOKEN_SECRET` (names only).

Progress lines (one per lot, not with `-q`):
`[ 3/19] tile 98138 Earth Blue (BrickLink 98138 / Dark Blue, color 63): sold 812 sales, stock 140 lots`.
When the API reference data is not yet checked: one line
`Note: BrickLink API details in bricklink_api.json are not yet checked against the live documentation.`

Stops:

- 429/5xx/network after `--max-attempts` → exit 5: `Error: BrickLink API … after 5 attempts;
  12 of 19 lots saved in …progress.json. Resume with: lego-image-processor parts prices fetch
  -o PATH --resume` (plus the same options used).
- Daily limit → exit 5, same progress message, "try again tomorrow".
- 401/403 → exit 7: `Error: BrickLink rejected the credentials (TOKEN_IP_MISMATCHED: …). Check
  the token's IP address setting on BrickLink's API registration page.` No snapshot written;
  progress kept.
- Ctrl-C → exit 130 (Click default), progress kept, resume message.
- `--resume` with no progress file or a different fingerprint → exit 1 naming the difference.

Success summary (also with `-q`):

```
Wrote price snapshot PATH: 19 lots (complete); priced from sales 18, from stock only 1, unpriced 0.
Largest changes in unit average since 2026-09-01:
  tile 98138 Vibrant Coral (353): $0.0712 -> $0.0950 (+33.4%)
  ...                                                   (up to 5 lines; "first snapshot" when none)
Review the file, then commit it.
Price data: BrickLink price guide (bricklink.com). BrickLink is a trademark of LEGO BrickLink, Inc.
Not endorsed by BrickLink.
Not affiliated with or endorsed by The LEGO Group.
```

No output, error message, log record or file ever contains a credential value, an
`Authorization` header or an `oauth_signature` (FR-006, SC-005).

## Changed

- `parts list` / `parts export`: the price note line now reads the new `PRICE_NOTE` (R15).
  Nothing else changes; parts-list JSON `"prices"` carries the new text.

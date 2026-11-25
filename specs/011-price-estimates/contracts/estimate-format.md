# Contract: estimate report JSON (011, format_version "1")

Written by `parts estimate LAYOUT --format json` / `-o`. Deterministic: a pure function of the
layout bytes, the snapshot bytes, `as_of` and the threshold (no generation time). Money values are
decimal strings: unit and line values exact (up to 4 places), totals at 2 places (half-up).

```json
{
  "format_version": "1",
  "kind": "price-estimate",
  "kit": "31203",
  "layout": "<PartsList.layout block of feature 005, unchanged: path, sha256, schema_version, source_image, positions, map, arrangement>",
  "snapshot": {
    "file": "bricklink_price_guide.json",
    "path": null,
    "packaged": true,
    "sha256": "1a2b…",
    "retrieved_at": "2026-12-01T18:03:05Z",
    "complete": true,
    "source": {"title": "BrickLink price guide (BrickLink API)", "url": "https://www.bricklink.com"},
    "statistic": {"average": "qty_avg_price", "low": "min_price", "high": "max_price"},
    "query": {"new_or_used": "N", "currency_code": "USD", "vat": "N", "country_code": null, "region": null}
  },
  "staleness": {"as_of": "2026-12-05", "age_days": 4, "threshold_days": 90, "stale": false},
  "estimates": {
    "full": {
      "kind": "full",
      "label": "Every piece",
      "owned_kits": 0,
      "totals": {"average": "412.35", "low": "260.10", "high": "1150.00"},
      "whole_dollars": {"average": 412, "low": 260, "high": 1150},
      "pieces": 10240,
      "lots": 19,
      "by_basis": {"sold": {"lots": 18, "pieces": 9928}, "stock": {"lots": 1, "pieces": 312},
                   "unpriced": {"lots": 0, "pieces": 0}},
      "complete": true,
      "nothing_to_buy": false,
      "lines": [
        {"part_id": "6141", "part_type": "plate", "color_key": "lego_white",
         "lego": {"name": "White", "id": 1},
         "bricklink": {"item_no": "4073", "color_id": 1, "color_name": "White"},
         "quantity": 3062, "basis": "sold", "reason": null,
         "unit": {"average": "0.0385", "low": "0.0100", "high": "0.5000"},
         "line": {"average": "117.8870", "low": "30.6200", "high": "1531.0000"},
         "count": {"unit_quantity": 1204, "total_quantity": 380211}}
      ],
      "unpriced": []
    },
    "one_kit": {
      "kind": "one_kit", "label": "On top of one 31203 kit", "owned_kits": 1,
      "totals": {"average": "0.00", "low": "0.00", "high": "0.00"},
      "whole_dollars": {"average": 0, "low": 0, "high": 0},
      "pieces": 0, "lots": 0,
      "by_basis": {"sold": {"lots": 0, "pieces": 0}, "stock": {"lots": 0, "pieces": 0},
                   "unpriced": {"lots": 0, "pieces": 0}},
      "complete": true, "nothing_to_buy": true, "lines": [], "unpriced": []
    }
  },
  "notes": ["One kit covers every piece."],
  "estimate_note": "Estimate only; excludes shipping, fees and taxes; prices vary by seller and over time.",
  "attribution": "Price data: BrickLink price guide (bricklink.com). BrickLink is a trademark of LEGO BrickLink, Inc. Not endorsed by BrickLink.",
  "disclaimer": "Not affiliated with or endorsed by The LEGO Group."
}
```

Rules:

- `snapshot.path` is the `--prices` path as given, or `null` with `packaged: true`.
- `lines`: lots with quantity > 0, in parts-list lot order; `full` quantities are `needed`,
  `one_kit` quantities are the `kits=1` parts list's `to_buy`.
- Unpriced line: `basis: "unpriced"`, `reason` one of `no verified BrickLink IDs (<005 reason>)`,
  `not in the price snapshot`, `no BrickLink sales or listings`; `unit`, `line`, `count` are `null`;
  `bricklink` is `null` for unverified lots (and `lego` holds the layout's color name and code).
  Each also appears in `unpriced` as `{part_id, part_type, color_key, name, quantity, reason}`.
- Stock line: `basis: "stock"`; `count` from the stock figures.
- `totals.x` = sum of `line.x` over priced lines, quantized to 0.01 half-up; `whole_dollars.x` =
  the exact sum quantized to 1 half-up (integers). `low ≤ average ≤ high`.
- `complete` = no unpriced line. `nothing_to_buy` = no lines.
- `notes`, in this order when they apply: stale ("Prices are from YYYY-MM-DD, N days before
  YYYY-MM-DD; they may be out of date."), partial snapshot ("The price snapshot is partial: M of N
  lots."), per estimate "Incomplete: P pieces in L colors could not be priced." (full first), the
  `--all-colors` hint when any reason is "not in the price snapshot", "Priced from current for-sale
  listings (no sales in 6 months): …", "One kit covers every piece.".

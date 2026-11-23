# Contract: parts list JSON (005)

```json
{
  "format_version": "1",
  "kit": "31203",
  "layout": {
    "path": "land-elevation.json",
    "sha256": "…",
    "schema_version": "2.0",
    "source_image": "recipe:land-elevation",
    "positions": 10240,
    "map": {"recipe": {"id": "land-elevation", "format": "1", "sha256": "…"},
            "datasets": [{"id": "etopo2022-surface-10m", "version": "…", "citation": "…", "license": "…"}]}
  },
  "owned": {"kits": 1, "owned_files": [{"path": "loose.csv", "sha256": "…"}],
            "missing_files": [], "ignored_rows": 0, "spares_percent": "0"},
  "lots": [
    {"part_id": "6141", "part_type": "plate", "color_key": "lego_brick_yellow", "verified": true,
     "lego": {"name": "Brick Yellow", "id": 5, "element_id": "…"},
     "bricklink": {"item_type": "P", "item_no": "4073", "color_name": "Tan", "color_id": 2},
     "rebrickable": {"part_num": "6141", "color_name": "Tan", "color_id": 19},
     "rgb": [228, 205, 158],
     "needed": 350, "kit_supply": 0, "loose": 0, "owned": 0, "shortfall": 350, "spares": 0,
     "to_buy": 350, "surplus": 0},
    {"part_id": "6141", "part_type": "plate", "color_key": "lego_bright_red", "verified": false,
     "reason": "no cited color for part", "layout_color": {"name": "Bright Red", "code": "21"},
     "needed": 618, "kit_supply": 0, "loose": 0, "owned": 0, "shortfall": 618, "spares": 0,
     "to_buy": 618, "surplus": 0}
  ],
  "totals": {"lots": 2, "needed": 968, "owned": 0, "to_buy": 968, "lots_to_buy": 2, "spares": 0,
             "surplus": 0, "verified_lots": 1, "unverified_lots": 1},
  "unverified": [{"part_id": "6141", "color_key": "lego_bright_red", "reason": "no cited color for part", "needed": 618}],
  "citations": [{"id": "kit-31203-instructions", "title": "…", "url": "…", "sha256": "…", "pages": [159], "used_for": "kit supply (parts inventory page)"},
                {"id": "bricklink-4073", "title": "…", "url": "…", "sha256": "…", "accessed": "…"}, "…",
                {"id": "rebrickable-terms", "title": "Rebrickable catalog terms", "url": "…", "sha256": "…", "accessed": "…", "text": "Free for personal and commercial use, …"}],
  "acknowledgement": "Catalog data: Rebrickable (rebrickable.com), BrickLink, LDraw, Brickset; kit inventory from the LEGO 31203 building instructions.",
  "prices": "Prices: none are estimated. Upload the list to BrickLink or Rebrickable to price it; both price an imported list.",
  "disclaimer": "Not affiliated with or endorsed by The LEGO Group."
}
```

Rules: key order as shown; no timestamps; `map` is null for image-derived layouts; unverified lots
carry `layout_color` and `reason` and no `lego`/`bricklink`/`rebrickable` keys; `spares_percent` is
a decimal string; lots ordered plate → tile, LEGO color ID, unverified last (plate → tile, then key).
(The example's Bright Red plate lot was unverified before US4; it is cited now. Implemented totals
add `lots_to_buy`, `spares` and `surplus`, and the file adds `unverified` and `prices`.)

## Addendum (feature 014): leftovers

Additive, `format_version` stays "1": a `leftovers` array (after `lots`) and `totals.leftover`.
See `specs/014-leftovers-and-background/contracts/parts-list-leftovers.md`.

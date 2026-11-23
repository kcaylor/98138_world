# Contract: leftovers in the parts list JSON (format_version "1", additive)

```json
"leftovers": [
  {"part_id": "6141", "part_type": "plate", "color_key": "lego_white",
   "lego": {"name": "White", "id": 1, "element_id": "614101"}, "rgb": [255, 255, 255],
   "kit_supply": 3064, "used": 3062, "leftover": 2},
  ...
],
"totals": {..., "leftover": 890}
```

- One row per kit map element (1 land + 9 ocean), plates first then tiles, by LEGO color id.
- `kit_supply` = kits × inventory quantity − missing (never below 0); `used` = layout positions of
  that part in that cited color; `leftover` = max(0, kit_supply − used).
- With `--kits 0` every `kit_supply` and `leftover` is 0.
- Table output (kits ≥ 1): a "Left over in the box" table (part, color (LEGO id), kit, used,
  left over) and `Left over in the box: N pieces`.
- Web manifest: `variants[].leftovers` (the rows above, one kit) and
  `variants[].summary.left_over_with_kit`.

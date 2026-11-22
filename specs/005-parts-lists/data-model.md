# Data Model: Parts Lists and Ordering (005)

Python dataclasses (frozen). File shapes are in `contracts/`.

## PartNumbers (`kit/part_numbers.py`, from `data/part_numbers.json`)

| Field | Type | Rules |
|---|---|---|
| `part_id` | str | project part ID used in layouts: `6141` or `98138` |
| `name` | str | BrickLink catalog name ("Plate, Round 1 x 1", "Tile, Round 1 x 1") |
| `lego_design_ids` | tuple[str] | from the Rebrickable "External Sites: LEGO" list and the kit inventory |
| `bricklink_item_type` | str | `P` |
| `bricklink_item_no` | str | `4073` / `98138` |
| `bricklink_alternates` | tuple[str] | as listed on the catalog page |
| `bricklink_colors` | tuple[str] | BrickLink color names in the page's color list (opaque and others, as listed) |
| `rebrickable_part_num` | str | `6141` / `98138` |
| `citations` | dict[str, Citation] | keys `bricklink`, `rebrickable`; each URL, SHA-256, accessed |

Validation: both parts present; item numbers non-empty; every citation has a SHA-256; the
plate's BrickLink alternates include `6141` (consistency check against 003's `part_ids`).

## ResolvedColor

Wraps a `PartColor` (004) and the part's `PartNumbers`: LEGO color name/ID, element ID, BrickLink
item no, color name/ID, Rebrickable part, color name/ID, RGB, citation IDs.

## Lot

| Field | Type | Rules |
|---|---|---|
| `part_id` | str | `6141` \| `98138` |
| `part_type` | str | `plate` \| `tile` |
| `color_key` | str | layout `color_id` |
| `layout_color_name`, `layout_color_code` | str | as in the layout |
| `verified` | bool | |
| `reason` | str \| None | when unverified: `no cited color for part` \| `color code mismatch` |
| `ids` | ResolvedColor \| None | None when unverified |
| `needed` | int | ≥ 1 |
| `kit_supply` | int | N × supplied_for(part, key) − missing, floor 0 |
| `loose` | int | from `--owned` |
| `owned` | int | kit_supply + loose |
| `shortfall` | int | max(0, needed − owned) |
| `spares` | int | ceil(shortfall × p / 100) if shortfall > 0 else 0 |
| `to_buy` | int | shortfall + spares |
| `surplus` | int | max(0, owned − needed) |

## OwnedInputs

| Field | Type | Rules |
|---|---|---|
| `kits` | int | ≥ 0, default 0 |
| `owned_files` | tuple[(path, sha256)] | parsed with the owned-CSV rules |
| `missing_files` | tuple[(path, sha256)] | same rules |
| `ignored_rows` | int | rows for non-map parts |
| `spares_percent` | Fraction | 0–100, default 0 |

## OwnedRow (parsing)

`Part,Color,Quantity` or `Element,Quantity` (case-insensitive headers, any order, extra columns
ignored, BOM and CRLF accepted). Quantity: integer ≥ 0. Errors carry file and line number.

## PartsList

| Field | Type |
|---|---|
| `format_version` | `"1"` |
| `layout` | path, sha256, source_image, schema_version, positions, map provenance (recipe id/version/sha256, dataset ids/versions/citations/licenses) or None |
| `kit` | `"31203"` |
| `owned` | OwnedInputs |
| `lots` | tuple[Lot] (order: plate, tile; LEGO color ID; unverified last) |
| `totals` | lots, needed, owned, to_buy, verified_lots, unverified_lots |
| `citations` | ordered list of citations used (kit inventory, color tables, part numbers, Rebrickable acknowledgement) |
| `disclaimer` | constant |

## State and flow

```text
layout.json ──load──▶ positions ──group──▶ lots(needed)
                                             │ resolve (PartColorTable + PartNumbers)
OwnedInputs (kits, owned.csv, missing.csv) ──▶ owned, shortfall, spares, to_buy
                                             ▼
                                         PartsList ──▶ table | JSON | BrickLink XML | Rebrickable CSV
```

# Data Model: Kit Reference Data for LEGO World Map 31203

**Feature**: 003-kit-reference-data | **Plan**: [plan.md](plan.md) | **Research**: [research.md](research.md)

File shapes are in [contracts/data-files.md](contracts/data-files.md); this document defines the
entities, their fields, relationships and validation rules.

## SourceDocument (provenance block)

Embedded as `source` in every generated or curated reference file.

| Field | Type | Rule |
|---|---|---|
| `title` | str | "LEGO 31203 World Map building instructions" |
| `url` | str | pinned URL |
| `sha256` | str | 64 hex chars; equals the pinned value |
| `pages` | list[int] | pages the file's facts come from (e.g. `[159]`, or the 40 section pages) |
| `generated_on` | str (YYYY-MM-DD) | the only field allowed to differ on regeneration |
| `generator` | str | e.g. `cli/tools/kit31203 extract` or `curated by hand` |
| `citations` | list[Citation] | non-PDF sources (Brickset, LDraw, BrickLink, Rebrickable) |
| `disclaimer` | str | "Not affiliated with or endorsed by The LEGO Group." |

**Citation**: `{id, title, url, accessed}`; rows refer to citations by `id`.

## KitColor (curated table, 10 rows)

| Field | Type | Rule |
|---|---|---|
| `key` | str | `lego_<snake LEGO name>`; unique; equals layout `color_id` |
| `lego` | `{name, id}` | from LDraw `LEGOID` comments |
| `bricklink` | `{name, id}` | from BrickLink color guide |
| `rebrickable` | `{name, id}` | from Rebrickable colors.csv |
| `rgb` | `[r,g,b]` | display RGB, from Rebrickable `rgb` (cited) |
| `role` | `"land"` \| `"ocean"` | exactly 1 land, 9 ocean |
| `element_id` | str | the kit element in this color (FK → KitElement) |
| `citations` | `{lego, bricklink, rebrickable, element}` | each a citation id; all required |
| `notes` | str | e.g. "closest catalog color" when not exact (none today) |

Validation: 10 rows; keys unique; every ID field non-null; every citation id resolves; no row
marked estimate/placeholder (US1-3); `lego.id` values unique.

## KitElement (inventory line, 32 rows)

| Field | Type | Rule |
|---|---|---|
| `element_id` | str | from page 159; unique |
| `quantity` | int > 0 | from page 159 |
| `source_page` | int | 159 |
| `design_id` | str \| null | LEGO design number (e.g. "6141", "35381") |
| `part_ids` | list[str] | all known part numbers (e.g. `["6141","4073"]`, `["98138","35381"]`) |
| `description` | str | from part catalog |
| `color` | str | LEGO color name from part catalog; for map elements must equal a KitColor's `lego.name` |
| `color_key` | str \| null | FK → KitColor.key for map elements; null otherwise |
| `role` | `"land"` \| `"ocean"` \| `"section_base"` \| `"frame_other"` | |
| `metadata_verified` | bool | false only where the part catalog could not confirm (4121715, 4160228) |
| `citation` | str | citation id for part metadata |

Validation: exactly one `land` element (614101, part 6141, White, qty 3064); exactly nine `ocean`
elements, all part 98138, nine distinct colors; one `section_base` (6302092, qty 40); sum of
quantities = 11,694; every map element has `metadata_verified: true`.

**KitInventory**: `{kit_id: "31203", source, elements: [KitElement]}`, with helpers
`land_element()`, `ocean_elements()`, `supplied(color_key) -> int`.

## Section

| Field | Type | Rule |
|---|---|---|
| `col` | int 0–7 | |
| `row` | int 0–4 | |
| `page` | int | one of the 40 listed pages |
| `image_size` | `[w,h]` | `[154,154]` or `[154,153]` |
| `placement` | `{x, y, scale}` (pt) | from the content stream, for audit |
| `order_check` | bool | true when page-order position equals placement position |

Validation: 40 sections; (col,row) pairs unique and complete; pages unique; `order_check` true
for all (extraction fails otherwise).

## DesignGrid (official design)

| Field | Type | Rule |
|---|---|---|
| `width`, `height` | int | 128, 80 |
| `palette` | list[str] | the 10 KitColor keys, index = code |
| `rows` | list[str] (80) | each 128 chars, one base-36 digit per position indexing `palette` (compact, diffable) |
| `sections` | list[Section] | 40 |
| `overrides` | list[Override] | manual decisions applied |
| `counts` | list[ColorCount] | per color |
| `classification` | `{method, ambiguity_ratio_threshold, flagged, resolved}` | flagged == resolved (key names as in contracts/data-files.md) |

**Override**: `{x, y, auto: key, chosen: key, ratio, reason, decided_by, decided_on}`.

**ColorCount**: `{key, used, supplied, spare}`; `spare = supplied − used ≥ 0` (SC-003);
`spare_note` = "unexplained" unless the instructions show a use.

Validation: 10,240 positions, exactly 10 distinct keys; land positions (key `lego_white`) are the
only positions whose `role` is land; Σused = 10,240.

Derived: `color_at(x, y) -> KitColor`, `to_layout() -> PositionPlacementGrid` (schema 2.0, used by
SC-005).

## LandSeaMask (regenerated)

Existing shape kept (`dimensions`, `land_positions`, `ocean_positions`, `coordinate_system`,
`land_coordinates`, `mask_2d`), plus a `source` block (pages = the 40 section pages) and
`derived_from: "kit_31203_design.json"`. `land_positions` = count of `lego_white` in the design =
inventory land quantity − spares (3,062 today).

## MaskChangeRecord

`{source, previous_mask_sha256, changes: [{x, y, old: "land"|"ocean", new: ...}], count}`.
Empty `changes` today (research R6); committed regardless.

## Layout (schema 2.0)

`PositionPlacement`: `part_type ∈ {"plate","tile"}`, `lego_part_id ∈ {"6141","98138"}`, with the
invariant plate ↔ 6141, tile ↔ 98138. `color_id` must be a palette color id; for buildability it
must be a KitColor key of the matching role.

`PositionPlacementGrid` metadata: `schema_version: "2.0"`, `disclaimer`. Statistics:
`land_plate_count`, `ocean_tile_count`, `color_frequency_by_part_type: {plate, tile}`.

State transition: a JSON layout with `schema_version` ≠ "2.0" (or missing) → `LayoutSchemaError`
("Layout schema version 1.0 is no longer supported (land is now part 6141, a 1x1 round plate).
Regenerate it with: lego-image-processor layout <image> -o <layout.json>").

## KitSpecification (rebuilt, `layout/kit_spec.py`)

Built from KitInventory + KitColor: `land_part_id "6141"`, `ocean_part_id "98138"`,
`available_colors_plate` (1 key), `available_colors_tile` (9 keys), `plate_quantities`,
`tile_quantities` from the inventory; `land_positions`/`ocean_positions` from the mask. No
quantities are stored in kit_spec itself.

## Relationships

```
SourceDocument ─┬─ KitInventory ── KitElement (map roles) ──1:1── KitColor
                ├─ KitColor table
                └─ DesignGrid ── Section ×40
                      │  └─ cells → KitColor.key
                      ├─→ LandSeaMask (white = land)
                      └─→ MaskChangeRecord (vs previous mask)
KitSpecification ← KitInventory + KitColor + LandSeaMask → LayoutValidator
```

## Cross-file consistency rules (FR-023, test_reference_consistency.py)

1. Each KitColor.element_id exists in the inventory, with matching color name and role.
2. For each color: design used ≤ inventory supplied; DesignGrid.counts agree with both.
3. Mask land count = design white count; mask land coordinates = design white coordinates.
4. All files carry the same `source.sha256`.
5. Palette (`lego_colors.json`) contains every KitColor `lego.id` with a unique RGB.

Not affiliated with or endorsed by The LEGO Group.

# Contract: Shipped reference data files

Location: `cli/src/lego_image_processor/data/`. All files: UTF-8 JSON, 2-space indent, trailing
newline, written deterministically. Every file has a top-level `source` block (see data-model
SourceDocument) and `"format_version": "1"`.

## kit_colors.json (curated by hand)

```json
{
  "format_version": "1",
  "source": {
    "title": "LEGO 31203 World Map building instructions",
    "url": "https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6372756.pdf",
    "sha256": "b593e2f4befbc227c5b12fec9b58a1bd6141d19b54de5f5336dcc8cc9eb43c4c",
    "pages": [159],
    "generator": "curated by hand",
    "generated_on": "2026-11-21",
    "citations": [
      {"id": "ldraw", "title": "LDraw LDConfig.ldr (update 2026-11-09)", "url": "https://library.ldraw.org/library/official/LDConfig.ldr", "accessed": "2026-11-21"},
      {"id": "bricklink", "title": "BrickLink Color Guide (archived 2025-10-02)", "url": "http://web.archive.org/web/20251002182704/https://www.bricklink.com/catalogColors.asp", "accessed": "2026-11-21"},
      {"id": "rebrickable", "title": "Rebrickable colors.csv", "url": "https://cdn.rebrickable.com/media/downloads/colors.csv.gz", "accessed": "2026-11-21"},
      {"id": "brickset", "title": "Brickset inventory 31203-1", "url": "https://brickset.com/inventories/31203-1", "accessed": "2026-11-21"}
    ],
    "disclaimer": "Not affiliated with or endorsed by The LEGO Group."
  },
  "colors": [
    {
      "key": "lego_bright_bluish_green",
      "role": "ocean",
      "element_id": "6311437",
      "lego": {"name": "Bright Bluish Green", "id": 107},
      "bricklink": {"name": "Dark Turquoise", "id": 39},
      "rebrickable": {"name": "Dark Turquoise", "id": 3},
      "rgb": [0, 143, 155],
      "citations": {"lego": "ldraw", "bricklink": "bricklink", "rebrickable": "rebrickable", "element": "brickset"},
      "notes": ""
    }
  ]
}
```

Ten entries, values as in research R3. Order: land first, then ocean by descending kit quantity.

## kit_31203_inventory.json (generated)

```json
{
  "format_version": "1",
  "kit_id": "31203",
  "source": {"title": "...", "url": "...", "sha256": "b593e2f4...", "pages": [159],
             "generator": "cli/tools/kit31203 extract", "generated_on": "YYYY-MM-DD",
             "citations": [{"id": "brickset", "...": "..."}], "disclaimer": "..."},
  "totals": {"lines": 32, "pieces": 11694},
  "elements": [
    {"element_id": "614101", "quantity": 3064, "source_page": 159,
     "design_id": "6141", "part_ids": ["6141", "4073"],
     "description": "Round plate 1x1", "color": "White", "color_key": "lego_white",
     "role": "land", "metadata_verified": true, "citation": "brickset"}
  ]
}
```

Element order: as on page 159, column by column, top to bottom.

## kit_31203_design.json (generated)

```json
{
  "format_version": "1",
  "source": {"...": "...", "pages": [22, 24, "... 40 pages ...", 132]},
  "width": 128, "height": 80, "coordinate_system": "top_left_origin",
  "palette": ["lego_white", "lego_bright_bluish_green", "..."],
  "rows": ["0011...128 chars...", "... 80 rows ..."],
  "sections": [{"col": 0, "row": 0, "page": 22, "image_size": [154, 154],
                "placement": {"x": 13.9, "y": 493.5, "scale": 36.9}, "order_check": true}],
  "classification": {"method": "median 5x5 at cell centre; CIEDE2000 to reference render colours",
                     "ambiguity_ratio_threshold": 0.6, "flagged": 0, "resolved": 0},
  "overrides": [{"x": 0, "y": 32, "auto": "lego_earth_blue", "chosen": "lego_bright_bluish_green",
                 "ratio": 1.0, "reason": "...", "decided_by": "...", "decided_on": "YYYY-MM-DD"}],
  "counts": [{"key": "lego_white", "used": 3062, "supplied": 3064, "spare": 2, "spare_note": "unexplained"}]
}
```

`rows[y][x]` is a base-36 digit indexing `palette`.

## lego_world_map_land_sea_mask.json (regenerated)

Existing keys kept (readers unchanged), plus `source` and `"derived_from": "kit_31203_design.json"`.
`source` replaces the old free-text `source`/`detection_method` strings; the loader reads
`source.url`/`source.generated_on` and still accepts the old string form only for the date field
during the transition (tests pin the new form).

## kit_31203_mask_changes.json (generated)

```json
{"format_version": "1", "source": {"...": "..."}, "previous_mask_sha256": "<sha of old file>",
 "count": 0, "changes": []}
```

## Removed

`lego_world_map_kit.json` (uncited 25-color lists and invented quantities, FR-010).

Not affiliated with or endorsed by The LEGO Group.

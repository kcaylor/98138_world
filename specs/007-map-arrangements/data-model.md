# Data Model: Map Arrangements (007)

## `data/kit_31203_arrangements.json` (package data, format_version "1")

```json
{
  "format_version": "1",
  "kit": "31203",
  "width": 128,
  "frames": [
    {"number": 1, "name": "America", "columns": [0, 31], "section_columns": "A-B"},
    {"number": 2, "name": "Europe & Africa", "columns": [32, 95], "section_columns": "C-F"},
    {"number": 3, "name": "Asia & Australia", "columns": [96, 127], "section_columns": "G-H"}
  ],
  "arrangements": [
    {"id": "A", "name": "europe-africa", "centre": "Europe and Africa", "frame_order": [1, 2, 3], "column_shift": 0, "default": true},
    {"id": "B", "name": "americas", "centre": "America", "frame_order": [3, 1, 2], "column_shift": 32},
    {"id": "C", "name": "asia-australia", "centre": "Asia and Australia", "frame_order": [2, 3, 1], "column_shift": -32}
  ],
  "source": {"title": "LEGO 31203 World Map building instructions", "url": "...", "sha256": "...",
             "pages": [7, 8], "citation": "LEGO 31203 building instructions, pp. 7–8", "disclaimer": "..."}
}
```

Load checks: frames tile 0–127 in order; each arrangement's frame order is a permutation of 1–3;
`column_shift` ≡ display start column of frame 1 (mod 128), computed from the frame order and
frame widths; ids and names unique.

## `Arrangement` (Python, `layout/arrangement.py`)

- `id`, `name`, `centre`, `frame_order`, `column_shift`
- `to_display(x) = (x + shift) mod 128`, `to_kit(x) = (x − shift) mod 128`
- `roll(a)` kit → display array; `unroll(a)` display → kit
- `frame_spans()` → [(frame, display_start, display_end)] in display order
- `boundaries()` → display columns where a frame starts (excluding 0)
- `record()` → the `metadata.arrangement` dict
- `parse_arrangement(value)` accepts ids and names, case-insensitive

## `metadata.arrangement` in a layout (schema 2.0, optional; absent = A)

```json
{"id": "B", "name": "americas", "centre": "America", "frame_order": [3, 1, 2], "column_shift": 32,
 "source": {"title": "...", "url": "...", "sha256": "...", "pages": [7, 8]}}
```

## Sheets and counts

- `Section` gains `kit_label` (label of the kit section in the instructions) and keeps `frame`
  (physical frame) and `instruction_page` (of the kit section).
- Counts JSON: top-level `arrangement` (id); per section `frame` (physical) and `kit_label`.
- Parts list JSON layout block: `arrangement` {id, name, note: "Every arrangement uses the same
  pieces."}.

## Validation report

- New violation `mask_mismatch`: {type, arrangement, positions, examples: first 10 [x, y, part_type,
  expected]}.
- Report adds `arrangement` (id).

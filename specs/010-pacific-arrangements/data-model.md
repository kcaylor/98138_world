# Data model: Pacific-centred Arrangements D and E (010)

## kit_31203_arrangements.json (format_version "2")

```json
{
  "format_version": "2", "kit": "31203", "width": 128, "height": 80, "strip_width": 16,
  "frames": [{"number": 1, "name": "America", "columns": [0, 31], "section_columns": "A-B"}, "..."],
  "arrangements": [
    {"id": "A", "name": "europe-africa", "centre": "Europe and Africa", "frame_order": [1, 2, 3],
     "column_shift": 0, "strips": "ABCDEFGH", "groups": ["1", "2", "3"], "in_instructions": true,
     "default": true},
    {"id": "D", "name": "pacific", "centre": "the Pacific (date line)", "frame_order": [2, 3, 1, 2],
     "column_shift": 64, "strips": "EFGHABCD", "groups": ["2b", "3", "1", "2a"],
     "in_instructions": false}
  ],
  "source": {"...": "pp. 7-8 (unchanged)"},
  "joints_source": {"title", "url", "sha256", "pages": [134, 135, 136, 137, 138, 139, 140],
                    "citation", "read_on", "method", "disclaimer"},
  "assembly": {"pegs_per_joint": 15, "pegs_per_base_joint": 3, "peg_design_id": "61332",
               "joint_pages": "134-139", "border_pages": "140-153", "note": "why D/E are possible"}
}
```

Validation (loader): frames tile 0–127 in 16-column strips; each `strips` is a rotation of
ABCDEFGH; `column_shift ≡ 16 × strips.index("A") (mod 128)`; `groups`/`frame_order` equal the
run-length grouping of `strips` by frame (split parts labelled a = lower kit columns, b = higher);
ids exactly A–E; `in_instructions` true for A–C only; disclaimer present on both sources.

## Python (layout/arrangement.py)

- `Frame(number, name, columns, section_columns)` + `strips` property ("AB").
- `Group(label, frame, strips, start, end)`: a run as hung, display columns.
- `Joint(left, right, x, kind)`: strip letters, display column of the joint, kind `kept`/`make`.
- `Arrangement(id, name, centre, frame_order, column_shift, width, strips, groups, in_instructions)`:
  `group_spans()`, `group_at(x)`, `joints()`, `unpeg()` (kit joints broken), `is_split`,
  `order_text` ("2b·3·1·2a"), `source` (pp. 7–8 or joints source), `record()`, `describe()`.
- `assembly_steps(arrangement) -> list[str]`, `assembly_note(arrangement) -> str` (status/why).

## Layout `metadata.arrangement`

A–C: `{id, name, centre, frame_order, column_shift, source{title,url,sha256,pages,citation}}`
(unchanged). D/E: the same keys plus `strips`, `groups`, `in_instructions: false`; `source` is the
joints source.

## Web manifest `arrangements[]`

Existing `{id, name, centre, frame_order, column_shift, frames, description}` plus `strips`,
`groups`, `in_instructions`, `citation`, `note`, `assembly` (list of step strings);
`joints_source` beside `arrangement_source`.

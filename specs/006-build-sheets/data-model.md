# Data Model: Build Sheets (006)

## Section

| Field | Type | Rules |
|---|---|---|
| `label` | str | column letter A–H + row 1–5 |
| `col`, `row` | int | 0–7, 0–4 |
| `x_range`, `y_range` | (int, int) | inclusive: 16·col … 16·col+15; 16·row … 16·row+15 |
| `frame` | int | 1 for col 0–1, 2 for col 2–5, 3 for col 6–7 |
| `instruction_page` | int | from 003 `sections[].page` (cited order only) |

`sections()` returns 40 in order A1…A5, B1…H5; validation: covers 128 × 80 exactly, order equals
ascending `instruction_page`.

## LegendEntry

| Field | Type |
|---|---|
| `number` | int (1-based, 005 lot order) |
| `lot` | 005 `Lot` (needed = total count) |
| `rgb` | (int, int, int): cited RGB, or the layout palette RGB for unverified lots, else mid grey |
| `text_color` | black or white by relative luminance |
| `label_lines` | tuple[str], Latin-1 |

## Page model

`PageSize(name, width_mm, height_mm)`: letter 215.9 × 279.4, a4 210 × 297.
`Page(size, items, number, total, kind, label)` (kind overview | legend | section; label = section
label); items: `Rect(x, y, w, h, fill, stroke, stroke_w)`, `Circle(cx, cy, r, fill, stroke,
stroke_w)`, `Line(x1, y1, x2, y2, stroke, w)`, `Text(x, y, text, size_pt, align, bold, color)`, each
with `tag` and `data` (key/value pairs, e.g. a stud's x, y and lot; written as SVG `class` and
`data-*`). Origin top-left, mm, text `y` is the baseline. Colors as RGB tuples.

## SheetSet

| Field | Type |
|---|---|
| `title` | str |
| `layout` | path, SHA-256, source image, map provenance (from 005 PartsList.layout) |
| `legend` | tuple[LegendEntry] |
| `pages` | tuple[Page] (overview, legend…, sections…) |
| `options` | paper, sections subset, format |

## SectionCounts

Per section label: ranges, `counts` {lot number: n}, total 256; plus legend (number, color key,
part, names) and layout SHA-256.

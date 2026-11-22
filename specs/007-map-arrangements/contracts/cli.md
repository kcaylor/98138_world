# CLI contract: Map Arrangements (007)

All commands end their output (and their error output) with "Not affiliated with or endorsed by
The LEGO Group."

## `--arrangement`

Values: `A`, `B`, `C`, `europe-africa`, `americas`, `asia-australia` (case-insensitive). Unknown
value: exit 2, message lists the valid values.

## `map build RECIPE -o OUT [--arrangement X] [...]`

Default A. Output adds a line `Arrangement: B (americas, frames 3·1·2, America in the centre)`.
The layout carries `metadata.arrangement`; the report JSON carries `arrangement` (the record).

## `map check RECIPE [--arrangement X] [...]`

As build, without writing a layout.

## `layout arrange LAYOUT --arrangement X -o OUT [-q]`

- Reads a schema 2.0 JSON layout (absent `metadata.arrangement` = A), writes a JSON layout with
  every position moved by shift(X) − shift(current) (mod 128), row-major order, other fields and
  metadata kept, `metadata.arrangement` = X.
- Output: `Arranged LAYOUT from A to B (column shift +32): OUT (N positions)` + disclaimer.
- Exit 1: unreadable file, not schema 2.0, width ≠ 128, a position outside the grid, unknown
  recorded arrangement. Exit 2: usage error (missing option, bad value).

## `layout IMAGE -o OUT [...]`

Unchanged.

## `validate LAYOUT`

Adds `Arrangement: B (americas)` and a line `Checking land/sea mask (arrangement B)...` with ✓ or ✗
N positions; report JSON adds `arrangement` and `mask_mismatch` violations.

## `sheets build` / `sheets counts`

Follow `metadata.arrangement`; no new options.

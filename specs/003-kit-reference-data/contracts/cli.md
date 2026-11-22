# Contract: CLI changes (`lego-image-processor`)

Every command touched here prints, as its last line of human output,
`Not affiliated with or endorsed by The LEGO Group.` (FR-021). JSON outputs carry a `disclaimer`
field.

## NEW `kit` group (approved by user 2026-11-21)

```
lego-image-processor kit inventory [--kit 31203] [--format table|json] [--role land|ocean|section_base|frame_other]
lego-image-processor kit colors    [--kit 31203] [--format table|json]
```

- `inventory --format table`: columns `element  part(s)  description  color  qty  role  page`,
  footer with line and piece totals and the source URL + SHA-256.
- `colors --format table`: columns `key  LEGO (id)  BrickLink (id)  Rebrickable (id)  role  element  qty`.
- `--format json`: the corresponding package data file content (stable, documented in
  data-files.md), to stdout.
- Exit codes: 0 success; 2 usage error (Click); 1 for unsupported kit
  (`Error: Kit ID '999' not supported. Currently only '31203' (LEGO World Map) is supported.`).
- Works offline.

## CHANGED `layout`

- Summary lines: `Land plates (6141): 3,062 (29.9%)`, `Ocean tiles (98138): 7,178 (70.1%)`.
- Written JSON has `metadata.schema_version: "2.0"` and `metadata.disclaimer`; CSV rows use
  `plate,6141` for land.
- Flags unchanged.

## CHANGED `validate`

- Input JSON with `schema_version` ≠ "2.0" → exit 1:
  `Error: Layout schema version 1.0 is no longer supported (land is now part 6141, a 1x1 round
  plate). Regenerate it with: lego-image-processor layout <image> -o <layout.json>`
- Loading summary: `Land plates`, `Ocean tiles`; kit summary: `Plate colors: 1`, `Tile colors: 9`,
  `Inventory: 32 lines, cited from instructions page 159`.
- Color-unavailable detail: color name and id, part (`plate (6141)` / `tile (98138)`), positions,
  `Suggested alternative: <kit color> (ΔE00 x.x)` chosen among that part's kit colors only.
- Quantity detail unchanged: `Required: N, Available: M`, `Shortfall: K`.
- Report JSON (`-o`) adds `disclaimer`; `part_type` values `plate`/`tile`.
- Exit code stays 0 for a valid but not fully buildable layout (unchanged behavior).

Not affiliated with or endorsed by The LEGO Group.

# Data model: Palette chooser

## IceRegions (`maps/ice.py`, `data/kit_31203_ice.json`)
- `land`, `sea`: 80 × 128 boolean masks in kit (A) coordinates; `rolled(arrangement)` gives them as hung.
- File: `format_version "1"`, `grid`, `source` (title, generator, generated_on, `land_ice` rule and
  regions, `sea_ice` rule, threshold and pinned dataset id/version/url/sha256/citation/license,
  disclaimer), `land_ice` and `sea_ice` (`count`, `cells`: row-major indices). Validation: counts
  match, land ice only on land, sea ice only on ocean, disclaimer present.

## Map cells (`maps/cells.py`, `cells.json`; contracts/cells-json.md)
- Header: format, recipe (id, title, sha256), arrangement, width, height, note, disclaimer.
- `cells`: 10,240 characters, `L` land, `O` ocean layer, `S` land shadow.
- `layers.land|ocean`: role, part, method, texture, colors, classes (per cell, −1 outside), and for
  data layers values, units, decimals, range, bounds (+source), no-value cells and their ice count;
  categories (categorical) or class labels (background); `editable_classes`.
- `shadow`, `ice`, `palette` (per part, light → dark, with L*).

## Chooser state (browser only)
`{ice: "data"|"white", shadow: key, layers: {land|ocean: {colors: [key…], bounds: null | [inner…]}}}`;
fragment `#palette=<URI-encoded JSON {m, i, s, land: {c, b}, ocean: {c, b}}>`.

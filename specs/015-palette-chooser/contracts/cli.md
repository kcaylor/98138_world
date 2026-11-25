# Contract: `map cells`

`lego-image-processor map cells RECIPE -o FILE [--arrangement A|B|C|name] [--cache-dir DIR]`

- Exit 0: writes FILE (contracts/cells-json.md); prints recipe, arrangement, one line per layer
  (role, method, cells, colors, bounds source and units), no-value counts, shadow, ice counts,
  `Cells: FILE (N bytes)`, the preview-only note, citations, and the disclaimer last.
- Dataset not cached: exit as `map build` (names the dataset; suggests `--fetch` on `map build`),
  no file. Unknown recipe: exit 1. The disclaimer is the last line on errors too.
- Never uses the network.

Maintainer: `PYTHONPATH=tools python -m kit31203 ice-mask [--dataset FILE] [--cache-dir DIR]
[--check] [--date YYYY-MM-DD]` — `--check` exits 0 with "no differences" when
`kit_31203_ice.json` is reproducible.

# Contract: web additions

- `GET /maps/<map>/<C>/cells.json` → 200 `application/json` (inline, cacheable, ETag), 404 for
  unknown map/combination or when the variant has no `cells` file. Not under `/download/`.
- `GET /static/palette.js` → `text/javascript`.
- CSP: `default-src 'none'; img-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self';
  base-uri 'none'; form-action 'none'; frame-ancestors 'none'`.
- Manifest: `variants.<C>.files.cells` with path, bytes, sha256, media_type, description, filename.

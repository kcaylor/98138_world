# Contract: recipe sticker table (recipe format "1", additive)

A recipe without `[sticker]` parses, builds and records exactly as before. The table changes no
layout, report, parts list, cells file, sheet or price estimate; only the recipe's own SHA-256
(of its bytes) changes when the table is added. Not affiliated with or endorsed by The LEGO Group.

## Table

```toml
[sticker]
title = "World Map, kit 31203 design"           # optional; default: the recipe's title
line = "White land and the kit's ocean pattern in nine tile colors, cell for cell from its building instructions."
no_data = { land = "ice", ocean = "sea ice" }   # optional
```

| Key | Type | Rule | Default |
|---|---|---|---|
| `sticker.title` | string | non-empty, one line | `title` |
| `sticker.line` | string | required in the table; non-empty, one line | (`description` when the table is absent) |
| `sticker.credit` | string | non-empty, one line; replaces the large sticker's "Data:" lines only (the print sheet keeps every registry citation) | the registry credit lines (research R9) |
| `sticker.no_data.land`, `.ocean` | string | non-empty, one line; the layer must have a `[<layer>.no_data]` rule | "no data" |

Errors (`RecipeError`, exit 1, key path first, the `_check_keys` style):

| Case | Message |
|---|---|
| unknown key in `[sticker]` or `[sticker.no_data]` | `sticker.<key>: unknown key (allowed: credit, line, no_data, title)` |
| `line` missing | `sticker.line: is required` |
| empty or multi-line string | `sticker.<key>: must be a non-empty single-line string` |
| `no_data` for a layer without a rule | `sticker.no_data.<layer>: the <layer> layer has no no_data rule` |

Text outside Latin-1 parses; `map stickers --format pdf` then stops (contracts/cli.md).

## Bundled recipes

The eight bundled recipes get a table at the end of the file after one comment line
(`# Map stickers (feature 017): ...`), with the texts the owner approves (research R6). The bytes
before that comment equal the af3ce57 file (research R13, G1). Bundled sticker titles do not
contain "Official"; the recipes' `title` and `description` keys do not change.

## US3 (after 016): `[margin].plaque`

```toml
[margin]               # feature 016's table
plaque = "bottom-left" # optional: top-left, top-right, bottom-left, bottom-right
```

Used only on non-kit templates (016: `[margin]` on a kit build is ignored with a note). An
unknown corner is `margin.plaque: must be one of top-left, top-right, bottom-left, bottom-right`.
`--plaque` overrides it (contracts/cli.md).

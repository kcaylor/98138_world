# Contract: CLI additions

Every existing command, flag and output keeps its meaning and bytes. Errors print `Error: …`
and the disclaimer last. No command here uses the network. Not affiliated with or endorsed by
The LEGO Group.

## `map stickers`

```
lego-image-processor map stickers RECIPE -o OUT [--format pdf|svg|json] [--paper letter|a4]
    [--cache-dir DIR] [--template ID]          # --template after feature 016
```

| Option | Value | Default |
|---|---|---|
| `RECIPE` | bundled id or recipe file | required |
| `-o, --output OUT` | PDF file (`pdf`), directory (`svg`), JSON file (`json`) | required |
| `--format` | `pdf`, `svg`, `json` (`json`: research R11, E1) | `pdf` |
| `--paper` | `letter`, `a4` (PDF only; ignored with a note otherwise) | `letter` |
| `--cache-dir DIR` | dataset cache root | as `map build` |
| `--template ID` | after 016: a confirmed template | recipe `template`, else the kit |

No `--arrangement`: the map is built in the recipe's own arrangement (A, or the recipe's
`arrangement` key), with `compare_official=False`, like `map cells`.

Writes:

- `pdf`: one page, the print sheet (contracts/sticker-files.md).
- `svg`: `OUT/sticker-small.svg` and `OUT/sticker-large.svg` (OUT is created; only these two
  names are replaced; OUT must not be a file).
- `json`: the sticker-set summary (contracts/sticker-files.md, "JSON summary").

Everything is composed in memory first; on any error nothing is written.

Output (exit 0):

```
Recipe: ocean-sst - Ocean temperature (format 1, SHA-256 <hex>)
Legend values from the build hung as A (default); the stickers are the same for A, B and C.
Sticker title: Ocean temperature (recipe title)
Sticker line: Annual mean sea surface temperature, ... (sticker table)
Large sticker: 125.8 x 61.8 mm for a Black tile 8 x 16; 10 swatches (land 1, ocean 9); text 5.5-14 pt
Small sticker: 45.8 x 45.8 mm for a Black tile 6 x 6; text 5-11 pt
Parts for a standalone plaque (the sticker is printed, not a LEGO part):
  Large: 1 Tile 8 x 16 ... Black - LEGO element 6484420, design 4974; BrickLink <item no>, Black (11); Rebrickable 4974, Black (0)
         1 Plate 8 x 16 Black - LEGO element 6094066, design 92438; BrickLink <item no>, Black (11); Rebrickable 92438, Black (0)
  Small: 1 Tile 6 x 6 ... Black - LEGO element 6155125, design 10202; ...
         1 Plate 6 x 6 Black - LEGO element 395826, design 3958; ...
Stickers: stickers.pdf (Letter, 1 page, N bytes)
Printed colors only approximate the LEGO colors.
Data citations and licenses:
  - ersst-v5-ltm-1991-2020 (v5-ltm-1991-2020): ... https://doi.org/...
    License: ...
Not affiliated with or endorsed by The LEGO Group.
```

Item names and BrickLink item numbers come from the pinned BrickLink pages (`bricklink.item_no`
in `plaque_parts.json`, which can differ from the part ID, as 6141 is item 4073); the lines
above show the form, not the text. The large tile is the smooth 4974, chosen by the project owner
on 2026-11-24 in place of the textured 90498 (element 4603646).
On a non-kit template a `Template:` line follows the recipe line (016's wording).

| Case | Exit | Message names |
|---|---|---|
| unknown recipe or recipe error | 1 | as `map build` |
| a dataset not cached | as `map build` (`DatasetNotCachedError`, 3) | the dataset and `dataset fetch ID`; never downloads |
| checksum mismatch | as `map build` (4) | the file |
| map cannot build | 1 | `Cannot build <id>: …` |
| no sticker line (no `[sticker] line` and no `description`) | 1 | "add a [sticker] line" |
| text does not fit at 5 pt | 1 | sticker, field, space needed and available (mm) |
| a print-sheet block does not fit | 1 | the block and paper |
| PDF and a field outside Latin-1 | 1 | the field; "use --format svg" |
| `--format svg` and OUT is a file | 1 | OUT |
| cannot write | 1 | the OS error |
| unknown `--template` (after 016) | 2 | the confirmed templates |

## `map build`, `map check`, `map cells` (US3, after 016)

| Option | Value | Default |
|---|---|---|
| `--plaque CORNER\|none` | `top-left`, `top-right`, `bottom-left`, `bottom-right`, `none` | recipe `[margin].plaque`, else none |

| Case | Exit | Message names |
|---|---|---|
| unknown corner | 2 (Click choice) | the corners |
| `--plaque CORNER` on the kit template | 1 | "the kit template has no margin"; the templates with one |
| recipe `[margin].plaque` on a kit build | 0 | 016's note that margin settings are not used on the kit |
| the tile does not fit the corner | 1 | the corner, "needs 6 x 6 studs plus one stud from the outline ring", the clear block's size |

Output adds, after 016's `Margin:` line: `Plaque: tile 6x6 (part 10202), Black, bottom-left,
rows 73-78, columns 1-6 - from --plaque|from the recipe`; the `Layout:` line counts 10,204
pieces and 1 plaque tile.

## Maintainer tool (`cli/`, `PYTHONPATH=tools`)

```
python -m partcolors plaque-parts [--snapshots DIR] [--check]
```

Writes `src/lego_image_processor/data/plaque_parts.json` from the pinned snapshots (the
partcolors set plus the four pinned BrickLink catalog pages; contracts/plaque-parts-file.md).
`--check` exits 0 with "no differences" when the committed file is reproducible, else lists the
differences and exits 1; a missing or changed snapshot exits 4 (`SnapshotError`). Disclaimer
last.

## Library

```python
from lego_image_processor.stickers import (StickerError, StickerSet, print_sheet,
                                           render_sticker_pdf, render_sticker_svgs, sticker_set)
s = sticker_set(result)                      # result: MapResult; after 016 also a template build
s.to_dict()                                  # JSON summary
render_sticker_pdf(s, paper="letter")        # bytes
render_sticker_svgs(s)                       # [("sticker-small.svg", text), ("sticker-large.svg", text)]
from lego_image_processor.kit.plaque_parts import load_plaque_parts   # .plaques["small"|"large"]
```

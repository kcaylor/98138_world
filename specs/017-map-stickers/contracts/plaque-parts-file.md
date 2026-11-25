# Contract: plaque part data (`data/plaque_parts.json`, format "1")

Written by `PYTHONPATH=tools python -m partcolors plaque-parts` (`tools/partcolors/plaque.py`),
read by `kit/plaque_parts.py` `load_plaque_parts()`. Package data; no network at run time.
`part_colors.json` and `part_numbers.json` are not changed. Not affiliated with or endorsed by
The LEGO Group.

```json
{
  "format_version": "1",
  "source": {
    "title": "Black tiles and plates for map sticker plaques",
    "generator": "tools/partcolors plaque-parts",
    "generated_on": "YYYY-MM-DD",
    "snapshots": [
      {"id": "rebrickable-elements", "title": "…", "url": "…", "sha256": "dfc8641d…", "accessed": "2026-11-22"},
      {"id": "rebrickable-colors", "…": "…"}, {"id": "ldraw", "…": "…"}, {"id": "bricklink", "…": "…"},
      {"id": "bricklink-10202", "title": "BrickLink catalog item 10202, … (Internet Archive copy of 2025-09-03)",
       "url": "http://web.archive.org/web/<timestamp>id_/https://www.bricklink.com/v2/catalog/catalogitem.page?P=10202",
       "sha256": "…", "accessed": "YYYY-MM-DD"},
      {"id": "bricklink-3958", "…": "…"}, {"id": "bricklink-4974", "…": "…"}, {"id": "bricklink-92438", "…": "…"}
    ],
    "rules": ["…"],
    "terms": {"…": "Rebrickable's terms, as in part_colors.json"},
    "disclaimer": "Not affiliated with or endorsed by The LEGO Group."
  },
  "plaques": {
    "small": {"studs": [6, 6], "tile": "10202", "plate": "3958"},
    "large": {"studs": [16, 8], "tile": "4974", "plate": "92438"}
  },
  "parts": {
    "10202": {
      "kind": "tile", "studs": [6, 6], "name": "<BrickLink item name>",
      "lego_design_ids": ["10202"],
      "bricklink": {"item_type": "P", "item_no": "10202", "alternates": [], "colors": ["…", "Black", "…"],
                    "citation": "bricklink-10202"},
      "rebrickable": {"part_num": "10202", "citation": "rebrickable-elements"},
      "color": {"key": "lego_black", "element_id": "6155125", "element_ids": ["6155125"],
                "lego": {"name": "Black", "id": 26}, "bricklink": {"name": "Black", "id": 11},
                "rebrickable": {"name": "Black", "id": 0}, "rgb": [5, 19, 29],
                "citations": {"lego": "ldraw", "bricklink": "bricklink",
                              "rebrickable": "rebrickable-colors", "element": "rebrickable-elements"}}
    },
    "3958": {"kind": "plate", "studs": [6, 6], "…": "element 395826"},
    "4974": {"kind": "tile", "studs": [16, 8], "…": "element 6484420"},
    "92438": {"kind": "plate", "studs": [16, 8], "…": "element 6094066"}
  },
  "disclaimer": "Not affiliated with or endorsed by The LEGO Group."
}
```

Element IDs above are the ones the pinned `elements.csv` gives for Rebrickable color 0
(research R10); names, item numbers, alternates and color lists come from the pinned pages when
the tool runs. The large plaque's tile is the smooth 4974, chosen by the project owner on
2026-11-24 in place of the textured 90498 (element 4603646). The `item_no` shown for 10202 is
illustrative: BrickLink's item number can differ from the part ID (6141 is item 4073; 016's 3070b
is item 3070, with 3070b as an alternate), so outputs and tests read it from this file and never
assume it equals the part ID.

## Rules (the tool keeps a row only when all hold; the loader re-checks 3, 5–9)

1. `elements.csv` lists at least one element of the part in Rebrickable color 0; the element ID
   is the lowest whose `design_id` equals the part number (partcolors rule 1); all are kept.
2. `colors.csv`, LDraw `LDConfig.ldr` and the BrickLink color guide give the Rebrickable, LEGO
   and BrickLink names and IDs of Black and its RGB (partcolors rules 2–4); they must equal the
   `lego_black` row of `part_colors.json`.
3. Rebrickable `part_num` equals the part ID (`elements.csv`).
4. LEGO design IDs are the `design_id` values of the part's Black elements in `elements.csv`.
5. The part ID is the BrickLink item number or one of its alternates (pinned BrickLink page).
6. The pinned BrickLink page lists Black (BrickLink id 11) among the item's colors.
7. No part is in `kit_31203_inventory.json`; every plaque's tile and plate have the same studs;
   `kind` matches the slot (`tile` / `plate`).
8. Every citation id resolves to `source.snapshots`; SHA-256s are 64 hex characters; dates are
   `YYYY-MM-DD`.
9. Only the color key `lego_black`; both disclaimers present.

Loader errors are `ValueError("plaque_parts.json: <rule>")`.

## Tool

`plaque-parts [--snapshots DIR] [--check]`: snapshots are read from the maintainer cache
(`<cache>/sources/partcolors/`, the BrickLink pages in `<cache>/sources/partnumbers/`, as for
`bricklink-4073`), never from the repository. Fetching the four archived pages is a one-time
maintainer step. `--check` regenerates in memory and compares everything but `generated_on`.
Tests use small synthetic HTML pages in the structure `partnumbers.build.parse_bricklink_part`
reads and a synthetic `elements.csv` excerpt (`cli/tests/fixtures/plaque/`); no copy of a catalog
page is committed.

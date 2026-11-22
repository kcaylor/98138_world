# Contract: data files (005)

## `data/part_numbers.json` (new)

```json
{
  "format_version": "1",
  "source": {
    "title": "Marketplace part numbers for the kit's map parts",
    "generator": "tools/partnumbers build",
    "generated_on": "YYYY-MM-DD",
    "pages": [
      {"id": "bricklink-4073", "url": "http://web.archive.org/web/20261104074336id_/https://www.bricklink.com/v2/catalog/catalogitem.page?P=4073",
       "sha256": "957f23bd90a68006f3cbf7f1f4461a6d5de89f2b9b6ed67b5b14533db0b2c146", "accessed": "2026-11-22"},
      {"id": "bricklink-98138", "url": "http://web.archive.org/web/20260901170641id_/https://www.bricklink.com/v2/catalog/catalogitem.page?P=98138",
       "sha256": "d1683255e9ecb05ade31884614beb278526aed13efb5725cbc53f74f9e7ffeb0", "accessed": "2026-11-22"},
      {"id": "rebrickable-6141", "url": "http://web.archive.org/web/20260407093646id_/https://rebrickable.com/parts/6141/",
       "sha256": "d7e3a955add1e5080be58ab58bfc5e5719e4499950cdae7a0c186fcfa00e51f7", "accessed": "2026-11-22"},
      {"id": "rebrickable-98138", "url": "http://web.archive.org/web/20250303234033id_/https://rebrickable.com/parts/98138/",
       "sha256": "4195c1bd0c0b0b5b01384f397e45be2737739a4b34d13dc942eeb9f1475a2fac", "accessed": "2026-11-22"}
    ],
    "notes": "SHA-256 of the decoded HTML of the Internet Archive raw copy.",
    "disclaimer": "Not affiliated with or endorsed by The LEGO Group."
  },
  "parts": {
    "6141": {"name": "Plate, Round 1 x 1", "lego_design_ids": ["6141"],
             "bricklink": {"item_type": "P", "item_no": "4073", "alternates": ["6141", "15570", "30057", "34823", "39799", "44325", "51809", "54003", "113470"],
                           "colors": ["Black", "Blue", "…"], "citation": "bricklink-4073"},
             "rebrickable": {"part_num": "6141", "name": "Plate Round 1 x 1 with Solid Stud", "citation": "rebrickable-6141"}},
    "98138": {"name": "Tile, Round 1 x 1", "lego_design_ids": ["98138", "35381"],
              "bricklink": {"item_type": "P", "item_no": "98138", "alternates": ["35380", "35381", "39797", "118864"],
                            "colors": ["Aqua", "Black", "…"], "citation": "bricklink-98138"},
              "rebrickable": {"part_num": "98138", "name": "Tile Round 1 x 1", "citation": "rebrickable-98138"}}
  }
}
```

`lego_design_ids`: 6141 from the kit inventory's design ID and Rebrickable's LEGO list; for the
tile, 98138 and 35381 (the kit elements' design ID) — both listed by Rebrickable. `--check`
regenerates and must report "no differences". As built, each page also has a `title`, `source.rules`
lists the six consistency rules the tool enforces, and `bricklink.colors` is the BrickLink color
names of the catalog page's "All" tab (100 for 4073, 93 for 98138).

## `data/part_colors.json` (changed)

- `source.license_note` → `source.terms`: `{"text": "Free for personal and commercial use, provided
  you acknowledge Rebrickable as your data source.", "url": "http://web.archive.org/web/20261029125803id_/https://rebrickable.com/downloads/",
  "sha256": "1c514a79f8cb70a0faacccf7174ee4329a307a6d91221b8c318b6982a7b91b75", "accessed": "2026-11-22"}`.
- `source.join_rules` gains rule 5 (BrickLink part page lists the color with the same BrickLink
  id); `source.snapshots` gains the two BrickLink part pages and the Rebrickable downloads page
  (`rebrickable-terms`; the tool checks the quoted terms text on it); `source.acknowledgement`
  is added.
- US4 (Q3): rows for every opaque color passing rules 1–5 (measured 44 plate, 40 tile); existing
  rows byte-identical in content; `in_kit` unchanged. The loader's forbidden-word and kit-equality
  checks stay.

# Contract: web additions (P2)

The service only serves prebuilt files and never imports `lego_image_processor`. No new runtime
or build dependency; no JavaScript needed. Every existing variant entry and file is unchanged.
Not affiliated with or endorsed by The LEGO Group.

## Prebuild

`python -m web98138.prebuild --out DIR …` (options unchanged). Per map, one sticker set from the
build in the recipe's default combination (an extra build only if that combination is not being
built), written with `stickers.render_sticker_pdf` (Letter, A4) and `render_sticker_svgs`:

```
maps/<map>/stickers/kit-31203/stickers-letter.pdf
maps/<map>/stickers/kit-31203/stickers-a4.pdf
maps/<map>/stickers/kit-31203/sticker-small.svg
maps/<map>/stickers/kit-31203/sticker-large.svg
```

After 016: `maps/<map>/stickers/<template-id>/…` for each template variant (FR-020).

## Manifest (`format_version` "1", additive)

```json
"maps": [{"…": "as today",
  "stickers": {"kit-31203": {
    "files": {
      "stickers-letter": {"path": "maps/ocean-sst/stickers/kit-31203/stickers-letter.pdf", "bytes": 0,
                          "sha256": "…", "media_type": "application/pdf",
                          "description": "Sticker print sheet, US Letter: both stickers at true size",
                          "filename": "98138-world_ocean-sst_stickers-letter.pdf"},
      "stickers-a4": {"…": "A4"},
      "sticker-small": {"media_type": "image/svg+xml", "description": "Small sticker (SVG, 45.8 x 45.8 mm)", "…": "…"},
      "sticker-large": {"media_type": "image/svg+xml", "description": "Large sticker (SVG, 125.8 x 61.8 mm)", "…": "…"}},
    "title": "Ocean temperature", "line": "…",
    "alt": {"small": "Small sticker: Ocean temperature. …", "large": "Large sticker: Ocean temperature. …"},
    "legend": [{"label": "-2 °C; land shadow", "color": "Earth Blue", "part": "98138"}],
    "plaques": [{"size": "large", "sticker_mm": [125.8, 61.8], "parts": ["… as the JSON summary"]}],
    "notes": {"printed": "The sticker is printed, not a LEGO part.",
              "colors": "Printed colors only approximate the LEGO colors."}}}}]
```

`total_bytes` counts every listed file, stickers included. Template sets after 016 have file
names `98138-world_<map>_<template-id>_<kind>.<ext>`.

## Catalog check

`stickers` is optional per map. When present: keys are `kit-31203` or (after 016) a listed
template id; file kinds are `stickers-letter`, `stickers-a4`, `sticker-small`,
`sticker-large`; each file is inside the root, present, and of the recorded size (the variant
file rule).

## Routes (registered before the combination routes)

| Route | Response |
|---|---|
| `GET /maps/<map>/stickers/<template>/sticker-small.svg`, `…/sticker-large.svg` | 200 `image/svg+xml`, inline, cacheable, ETag |
| `GET /maps/<map>/stickers/<template>/download/<kind>` | 200 attachment with the manifest file name |
| unknown map, template, file or kind | 404 |

CSP unchanged (`img-src 'self'` covers the SVGs; they contain no script).

## Map page

A "Stickers" panel (heading "Stickers for a plaque"), the same for A, B and C (and, after 016,
the template's own set on a template page; since the merge of feature 010 on 2026-11-25, the same
on all five kit combinations A-E, from the build in the recipe's own combination, D for the ENSO
maps):

- both stickers as `<img src=".../sticker-large.svg" alt="<alt.large>">` and the small one, in
  `<figure>`s with captions (size, tile part, "printed, not a LEGO part");
- a `<details>` "What the large sticker says": title, line, the legend labels with their color
  names, the data credit;
- "Parts for a standalone plaque": per size, the tile and the plate with LEGO element and design,
  BrickLink item and color, Rebrickable part and color;
- the note "Printed colors only approximate the LEGO colors.";
- downloads: print sheet Letter (PDF), A4 (PDF), small and large sticker (SVG), with sizes.

Works without JavaScript; the page footer keeps the disclaimer; `about.html` gains a short
paragraph on stickers.

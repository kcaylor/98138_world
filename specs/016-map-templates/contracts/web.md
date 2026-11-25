# Contract: web additions (P2)

The service still only serves prebuilt files and never imports `lego_image_processor`. No new
runtime or build dependency. Not affiliated with or endorsed by The LEGO Group.

## Prebuild

`python -m web98138.prebuild --out DIR [--templates LIST|none] …` (existing options unchanged).
`--templates` defaults to every confirmed template; `none` builds kit variants only. For each map
and template, `templates.compatibility(recipe, template)` decides; with the bundled maps and
`winkel-tripel`: `official-31203-bathymetry`, `ocean-sst`, `land-elevation`, `living-planet`,
`rainfall`. Files go to `maps/<map>/<template-id>/` with the same kinds as kit variants; download
names `98138-world_<map>_<template-id>_<stem>.<ext>`.

## Manifest (`format_version` "1", additive)

```json
"templates": [{"id": "winkel-tripel", "title": "…", "projection": "Winkel tripel",
               "board": {"modules": [8, 5], "width": 128, "height": 80},
               "counts": {"land": 2553, "ocean": 5691, "margin": 1996, "ring": 288},
               "rehang": false, "description": "…", "source": {"sha256": "…", "confirmation": {…}}}],
"maps": [{"…": "as today", "variants": {"A": …, "B": …, "C": …},
          "template_variants": {"winkel-tripel": {"…": "same fields as a kit variant",
                                                   "template": "winkel-tripel"}}}],
"part_labels": {"6141": "plate 1x1 round", "98138": "tile 1x1 round", "3070b": "tile 1x1 square"}
```

Counts are example values (exact fit, research R2); the manifest copies the loaded template's.
`part_labels` lists only the parts the site's variants use. A kit-only site (`--templates none`,
or no confirmed template) writes exactly the 6141 and 98138 labels, as today. `3070b` is added
only when a template variant exists. A template variant's page data cites the template's
dataset (ETOPO 2022) in its citations, from the report.

`variants` stays exactly A, B, C. Every kit variant entry and file is unchanged.

## Catalog check

`template_variants` keys must be listed in `templates` and must not be A, B or C; their files are
checked like kit files (inside the root, present, size matches); estimates as for kit variants.
`variant_count` counts both.

## Routes

- `GET /maps/<map>/<template-id>` → the map page for that variant; 404 if the map has none.
- `GET /maps/<map>/<template-id>/preview.png`, `thumb.png`, `cells.json`,
  `download/<kind>` → as for kit variants.
- `/maps/<map>` still redirects to the recipe's default combination.

## Map page

- The variant nav lists A, B, C ("Hang the frames as") and, when present, "Winkel tripel".
- A template page: the figcaption names the projection and board and says "Round studs for land
  and ocean, square tiles in the margin"; a note says the frames of a curved map cannot be
  re-hung; the parts note says square tiles fill the margin and one kit supplies none.
- Parts, leftovers, estimate (incomplete while the snapshot has no 3070b rows), lots table and
  downloads as on kit pages. The palette chooser works with `M` cells (contracts/
  recipe-and-outputs.md). Without JavaScript every preview and download works.
- The disclaimer stays in the page footer; `about.html` gains a short paragraph on templates.

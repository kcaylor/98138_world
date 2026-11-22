# Data model: Web App (008)

## Output directory

```text
<out>/
├── manifest.json
├── static/                      # nothing; CSS ships with the package
└── maps/<map-id>/<A|B|C>/
    ├── layout.json              # PositionPlacementGrid.to_json() (schema 2.0)
    ├── preview.png              # write_preview scale 10
    ├── thumb.png                # write_preview scale 3
    ├── parts.json               # build_parts_list(...).to_json(), kits 0
    ├── parts-1kit.json          # kits 1
    ├── bricklink.xml            # to_bricklink_xml(kits 0)
    ├── rebrickable.csv          # to_rebrickable_csv(kits 0)
    ├── bricklink-1kit.xml       # only when one kit leaves something to buy
    ├── rebrickable-1kit.csv     # ditto
    ├── sheets-letter.pdf        # render_pdf(build_sheet_set(paper="letter"))
    └── sheets-a4.pdf
```

## manifest.json (format_version "1")

```json
{
  "format_version": "1",
  "generated_at": "2026-11-22T12:00:00Z",
  "build_seconds": 25.1,
  "tools": {"lego_image_processor": "0.1.0", "web98138": "0.1.0", "python": "3.11.18",
            "git_commit": "a5542f3… or null"},
  "disclaimer": "Not affiliated with or endorsed by The LEGO Group.",
  "acknowledgement": "<parts.ACKNOWLEDGEMENT>", "price_note": "<parts.PRICE_NOTE>",
  "bricklink_note": "<BRICKLINK_UPLOAD_NOTE>",
  "arrangements": [{"id": "A", "name": "europe-africa", "centre": "Europe and Africa",
                     "frame_order": [1,2,3], "description": "frames 1·2·3, …"}],
  "arrangement_source": {"title": "...", "url": "...", "pages": [7, 8]},
  "frames": [{"number": 1, "name": "America"}],
  "maps": [{
    "id": "ocean-sst", "title": "Ocean temperature", "description": "...",
    "recipe": {"format": "1", "sha256": "..."},
    "layers": [{"class": "land", "role": "background", "part_id": "6141", "cells": 3062,
                "dataset": null}],
    "datasets": [{"id": "...", "version": "...", "sha256": "...", "url": "..."}],
    "citations": [{"id": "...", "title": "...", "citation": "...", "license": "...",
                   "doi": "...", "acknowledgement": "..."}],
    "variants": {"A": {
      "warnings": ["..."],
      "summary": {"lots": 10, "pieces": 10240, "one_kit_covers": 10240, "to_buy_with_kit": 0,
                  "lots_to_buy_with_kit": 0, "unverified_lots": 0},
      "lots": [ "<Lot.to_dict() of the kits=1 parts list>" ],
      "files": {"layout": {"path": "maps/ocean-sst/A/layout.json", "bytes": 1, "sha256": "...",
                           "media_type": "application/json",
                           "filename": "98138-world_ocean-sst_A_layout.json"}}
    }}
  }]
}
```

Download kinds (fixed set, FR-012): `layout`, `parts`, `parts-1kit`, `bricklink`, `rebrickable`,
`bricklink-1kit`, `rebrickable-1kit`, `sheets-letter`, `sheets-a4`; images `preview`, `thumb`
are served inline (not attachments).

Validation at start-up (FR-018): `format_version == "1"`; every map has variants A, B, C; every
listed file exists under `<out>` with the listed byte size; paths are relative and stay inside
`<out>`.

# web98138: the 98138.world web site

Pick one of the eight bundled maps and a frame combination (A–E; D and E are not in the building
instructions, feature 010), see the stud preview, and
download everything to build it: layout JSON, parts lists (full and topped up from one 31203 kit),
BrickLink wanted list, Rebrickable CSV and build-sheet PDFs (US Letter and A4). Feature 008; see
`specs/008-web-app/`. Five maps also come in a Winkel tripel version, a curved map on the same
board, on the template the project owner confirmed on 2026-11-24 (feature 016,
`specs/016-map-templates/`). Every map page also offers two stickers for a Black plaque tile, as a
print sheet and SVG files (feature 017, `specs/017-map-stickers/`).

Not affiliated with or endorsed by The LEGO Group.

## How it works

- **Build step** (`python -m web98138.prebuild --out DIR [--fetch] [--maps ...] [--combinations ...]
  [--cache-dir ...] [--templates ...]`): calls the CLI library (`lego_image_processor`, in `../cli`)
  for every map × combination and writes the files plus `manifest.json` (size, SHA-256, content
  type of every file; tool, recipe and dataset versions; the data shown on the pages). Only
  `--fetch` uses the network, to download missing pinned datasets.
- **Template variants** (feature 016): `--templates LIST` names the templates to build beside the
  kit (`winkel-tripel`), `--templates none` builds the kit only, and the default builds every
  template the project owner has confirmed. A map gets a template variant only when the library
  says it can be built on that template: on Winkel tripel `official-31203-bathymetry`,
  `ocean-sst`, `land-elevation`, `living-planet` and `rainfall`, not `official-31203` (LEGO's design
  on the kit grid) or the ENSO pair (hung as B). Its files go to `maps/<map>/<template-id>/`, and
  the manifest lists them in `templates` and `maps[].template_variants`. An unconfirmed template
  gives no variants and one note line. The committed `winkel-tripel` was confirmed by the project
  owner on 2026-11-24, so the site builds 29 variants: the 24 kit variants and 5 Winkel versions.
  Kit variants and their files do not change.
- **Stickers** (feature 017): per map, one sticker set from the build in the recipe's own
  combination (the same for A–E; D for the ENSO maps), in `maps/<map>/stickers/kit-31203/`, and one per template
  variant in `maps/<map>/stickers/<template-id>/`: `stickers-letter.pdf` and `stickers-a4.pdf` (the
  print sheet), `sticker-small.svg` and `sticker-large.svg`. The manifest lists them in
  `maps[].stickers.<template-id>`: `files` (path, size, SHA-256, media type, description, download
  name `98138-world_<map>_<kind>.<ext>`, with `_<template-id>` after the map for a template set),
  then the texts the page shows: `title`, `line`, `alt`, `legend`, `credit` (the large sticker's
  "Data:" lines, for "What the large sticker says"), `plaques` (the plaque parts with cited IDs)
  and `notes`. `total_bytes` counts the sticker files. No site variant has an in-margin plaque.
- **Service** (`web98138.app`, FastAPI + Jinja2): checks the output at start-up and serves pages and
  files from it. It never imports the CLI library, builds maps or downloads data. Every page works
  without JavaScript; map pages load one hand-written first-party script, `static/palette.js`
  (feature 015), the "Try other colors" palette chooser, which recolors the prebuilt
  `cells.json` in the browser (preview only). No cookies, no storage, nothing loaded from other
  sites.

Routes: `/`, `/about`, `/maps/<map>/<A|B|C|template-id>`, `.../preview.png`, `.../thumb.png`, `.../cells.json`,
`.../download/<kind>` (`layout`, `parts`, `parts-1kit`, `bricklink`, `rebrickable`,
`bricklink-1kit`, `rebrickable-1kit`, `sheets-letter`, `sheets-a4`),
`/maps/<map>/stickers/<kit-31203|template-id>/sticker-small.svg` and `.../sticker-large.svg`
(inline, for the page's images), `/maps/<map>/stickers/<kit-31203|template-id>/download/<kind>`
(`stickers-letter`, `stickers-a4`, `sticker-small`, `sticker-large`), `/manifest.json`,
`/healthz`, `/robots.txt`. Contract: `specs/008-web-app/contracts/routes.md`; template variants:
`specs/016-map-templates/contracts/web.md`; stickers: `specs/017-map-stickers/contracts/web.md`.
A template page (for example `/maps/ocean-sst/winkel-tripel`) says its frames cannot be re-hung
and that square tiles fill the margin, and offers the same nine downloads. Each map page has a
"Stickers for a plaque" panel, without JavaScript: both stickers with alt text, what the large
one says, the plaque parts, the color note and the four sticker downloads; a kit page shows the
kit set, a template page its template's set.

## Develop

```bash
uv venv --python 3.11 && uv pip install -e ../cli -e . pytest httpx2 pypdf
.venv/bin/pytest                                           # offline
.venv/bin/python -m web98138.prebuild --out site-output    # datasets from ~/.cache/lego-image-processor
WEB98138_SITE_DIR=site-output .venv/bin/uvicorn web98138.app:app --port 8080
```

Python 3.11 (the CLI pins scikit-image 0.21). Dependencies are permissive (FastAPI MIT, Starlette,
Jinja2 and uvicorn BSD-3). `requirements.txt` (runtime) and `requirements-build.txt` (the CLI's
dependencies for the image build) are pinned with hashes; regenerate them with the `uv pip compile`
lines at the top of the `.in` files.

## Deploy

`Dockerfile`, `fly.toml` and `.dockerignore` are at the repository root; see `docs/deploy.md`.

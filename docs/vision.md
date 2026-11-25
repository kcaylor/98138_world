# 98138.world: vision

LEGO's World Map kit (31203) gives us a grid scale and a land/sea mask. This project treats them as
the reference **template** and builds a general way to turn *any suitable* gridded map into a
buildable mosaic of the same bricks. The rules that govern this work are in
`.specify/memory/constitution.md`.

## The model

**Template.** Every map is built on a template: a projection; a rectangular board of whole 16×16
modules; a layout that assigns each stud to land, ocean or margin (off the globe); one part type per
class; and a frame. Within a template nothing changes between maps.

- **The kit template (the reference; never changes).** A 128×80 grid of 10,240 positions; the kit's
  land/sea mask (3,062 land, 7,178 ocean); the kit's projection (equidistant cylindrical, standard
  parallels about ±39°) and frame, hung as combination A, B or C.
- **Other templates** reproject the world onto the same studs, for example Winkel tripel on the
  kit's own 8 × 5 modules. Where the projection's outline leaves the rectangle, margin studs are
  built from square pieces, which set the round map pieces off as a background; a printed plaque
  can carry the map's title and legend.
  Each template's layout is generated from cited data by a maintainer tool and confirmed by the
  owner before it ships.

**Map = land layer + ocean layer.** Each layer plays one of two roles:

| Role | What it shows | Examples |
|---|---|---|
| Data-driven | A gridded field, classified onto an ordered LEGO color scale | Ocean: sea surface temperature, chlorophyll/productivity, bathymetry. Land: elevation, land cover, LAI, temperature |
| Background | A fixed treatment that frames the data layer | Official white land with its shading; a general ocean color with subtle shading |

The official kit is itself one such map: an **ocean map** of bathymetry on a white-land background.
Reproducing it from a recipe is the reference test for the whole system.

**Shading** is a texture rule, not a fixed pattern: it mixes neighbouring shades so a uniform area
does not look flat, and it can soften the steps of a data-driven color scale.

**Recipe.** A small declarative file fully describes a map: the dataset, which layer is
data-driven, the classification (bins or categories), the color scale, and the texture rule.

## Pipeline

```
download & cache dataset  →  reproject to the template grid  →  apply its land/sea layout
  →  classify each layer  →  map classes to LEGO colors  →  apply texture
  →  suitability check  →  layout  →  parts list / wanted list  →  build sheets
```

## What makes a map suitable

At this scale one stud is about 2.8° of longitude (roughly 300 km at the equator). Good candidates
vary smoothly over large areas: temperature, elevation, broad biomes, ocean productivity. Poor
candidates depend on fine detail or arbitrary boundaries, such as political maps, road networks,
and fine-grained land cover. Every map gets a suitability check that says how much survives
downsampling and whether the colors available for each part can carry the pattern.

## Building one for real

- **Parts lists** use verified part and color IDs, export as a BrickLink wanted list (XML with
  `MINQTY`) and a Rebrickable CSV, and can be limited to the pieces needed beyond an existing 31203
  kit (the kit is retired, so expect secondhand sources).
- **Build sheets** are printable, section-by-section, paint-by-number pages with per-section color
  counts.

## Roadmap

| Feature | Scope |
|---|---|
| 001 | Image quantization CLI (built) |
| 002 | Layout generation and kit validation (built; its "shadowing" story is replaced by the texture rule in 004) |
| 003 | Kit reference data: verified part IDs and inventory, color ID mappings, the official design as named colors (built; projection findings recorded as notes for 004) |
| 004 | Map recipes and canonical datasets: download/cache, reprojection, classification, color scales, texture, suitability (built). Examples: the official design as a recipe (exact), the official look from bathymetry (derived, 26.7% ocean cell agreement), an ocean temperature map, a land elevation map |
| 005 | Parts lists and ordering (built): parts list with cited LEGO, BrickLink and Rebrickable IDs from any layout (plate = BrickLink 4073 / Rebrickable 6141, tile = 98138), kit top-up from `--kits`, loose and missing parts, BrickLink wanted-list XML and Rebrickable CSV; 44 plate and 40 tile colors cited |
| 006 | Build sheets (built): overview, legend and 40 section pages (A1–H5, 16 × 16 at true scale, 8.0 mm pitch) with numbered studs and per-section counts, as PDF (ReportLab) or SVG pages, plus per-section counts JSON (`sheets build`, `sheets counts`) |
| 007 | Map arrangements (built): the kit's three frames hung as combination A (Europe and Africa in the centre), B (America) or C (Asia and Australia), from the instructions pp. 7–8; `map build --arrangement`, `layout arrange` (pure frame move, exact round trip), mask check in `validate`, sheets and counts labelled as hung with frame names |
| 008 | Web app (built): 98138.world shows the four bundled maps in combinations A, B and C with crisp stud previews, descriptions, citations and parts summaries, and offers the layout, parts lists (full and one-kit top-up), BrickLink XML, Rebrickable CSV and build-sheet PDFs (Letter and A4). All 12 variants are prebuilt with the CLI library at image build time, with a checksummed manifest; the FastAPI + Jinja2 service only serves files (no JS, no cookies, no trackers) on Fly.io |
| 009 | ENSO maps (built): sea surface temperature anomaly of a strong El Niño (December 1997) and La Niña (December 1988) on one shared °C legend, Pacific-centred by the recipe key `arrangement` |
| 010 | Pacific-centred arrangements (built): combinations D (`pacific`, the date line centred) and E (`asia-pacific`, 146° E), both 2b·3·1·2a with frame 2 split between two strips; not among the building instructions' three combinations, possible because strip and frame joints both take 15 connector pegs and the border goes round the finished board (pp. 134–140). Every build-sheet set ends with an assembly page; the ENSO maps default to D; the web site shows all six maps in A–E (30 variants) |
| 011 | Price estimates (built): an estimated cost per map for every piece and on top of one 31203 kit, offline from a dated, cited BrickLink price guide snapshot (6-month new sold average, USD, low–high range; `parts estimate`); the maintainer refreshes the snapshot with the BrickLink API (`parts prices fetch`, credentials from environment variables); 98138.world shows both estimates in whole dollars with the date, source and attribution |
| 012 | Living planet (built): plant productivity (MOD17A3 NPP 2000–2015) on land and ocean chlorophyll-a (MODIS-Aqua 2013–2024 climatology) at sea, with ice in White and a Black land shadow; adds a strip GeoTIFF reader, climatology means with valid-step counts, content checksums for files built on request, a land/ocean split from another dataset, a `log10` transform and per-layer `no_data` rules |
| 013 | Rainfall (built): GPCP v2.3 annual mean precipitation 1991–2020 on land and sea, White ice sheets and NSIDC sea ice, Black land shadow; adds a netCDF-4 reader (h5py) with polar-stereographic coordinates, multi-file datasets, bilinear sampling, region and dataset `override` rules and two-unit legends |
| 015 | Palette chooser (built): each map page's "Try other colors" panel recolors the map from the cited plate and tile colors, changes the number of classes and their bounds, recolors the land shadow, and shows ice-covered regions (packaged `kit_31203_ice.json`) as White ice or with the data; `map cells` exports the per-cell data; one hand-written first-party script, pages still work without JS; preview only (parts, prices, sheets unchanged) |
| 016 | Map templates (built): a template model (projection, board of whole modules, land/ocean/margin layout, parts, frame) with the kit as the reference and default, its outputs unchanged; Winkel tripel on the kit's 8 × 5 board as the first other template (2,553 land, 5,691 ocean and 1,996 margin studs, frames hung as A only), confirmed by the project owner on 2026-11-24; margin studs in 1×1 square tiles (3070b) in one color with an optional outline ring, in parts lists, prices and build sheets; `template` commands, `map build --template` and a recipe `[margin]` table; a maintainer tool that generates each layout from cited data, with a review sheet and `--check`; Winkel versions of five maps on the web site |
| 017 | Map stickers (planned): a printable sticker for every map on a black tile, in two sizes (a small plaque such as a 6×6 tile that fits a Winkel corner's free region, and a large display plaque such as 8×16), with the title, legend and credits taken from the map's data; after 016 ships, an optional plaque in a Winkel margin corner, where the layout, preview, parts list and sheets swap the square tiles under it for the black tile |
| later | Other board dimensions: Equal Earth, Mollweide or Robinson on 8 × 4 or 10 × 5 modules (equal-area data maps), Spilhaus on 6 × 6 (ocean maps), Patterson on 9 × 5; each needs a frame bill of materials from cited data |
| later | Projection as a map-planner choice, from the owner-confirmed templates |
| later | Custom recipes and uploads on the web, more datasets |

Not affiliated with or endorsed by The LEGO Group.

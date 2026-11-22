# 98138.world: vision

LEGO's World Map kit (31203) gives us a grid scale and a land/sea mask. This project treats them as
a **template** and builds a general way to turn *any suitable* gridded map into a buildable mosaic
of the same size. The rules that govern this work are in `.specify/memory/constitution.md`.

## The model

**Template (never changes).** A 128×80 grid of 10,240 positions; the kit's land/sea mask (3,062
land, 7,178 ocean); one part type per class; the kit's projection and frame.

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
download & cache dataset  →  reproject to kit grid  →  apply land/sea mask
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
| later | Web app at 98138.world on top of the CLI |

Not affiliated with or endorsed by The LEGO Group.

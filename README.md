# 98138.world

LEGO World Map-style mosaics of real data. The World Map kit (31203) is the reference template, a
128 × 80 grid of 10,240 studs with the kit's coastline, and any suitable gridded map (ocean
temperature, elevation, bathymetry, plant productivity, ocean chlorophyll, rainfall, ...) becomes a
buildable mosaic with a cited parts list, marketplace wanted lists and printable build sheets.
Every map also gets two printable stickers for a Black plaque tile that name it, the large one with
its color legend and data credit. Winkel tripel on the kit's own board is the first other
template: a curved world map of the same round pieces, with a margin of square tiles where the
board is off the globe, which can hold the small plaque's tile in a corner. The project owner
confirmed its layout on 2026-11-24.

Not affiliated with or endorsed by The LEGO Group.

- `cli/`: the command-line tool and library (`lego-image-processor`): recipes, datasets, maps,
  map templates, parts lists, build sheets, map stickers, frame arrangements. See `cli/README.md`.
- `web/`: the site at https://98138.world, built from the CLI library. See `web/README.md` and
  `docs/deploy.md`.
- `docs/vision.md` (the model and roadmap), `docs/runbook.md` (try everything locally),
  `specs/` (one Spec Kit directory per feature).

Data citations and licenses are shown with every map and recorded in its outputs. Catalog data:
Rebrickable, BrickLink, LDraw, Brickset.

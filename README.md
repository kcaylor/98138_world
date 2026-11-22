# 98138.world

LEGO World Map-style mosaics of real data. The World Map kit (31203) is used as a fixed template,
a 128 × 80 grid of 10,240 studs with the kit's coastline, and any suitable gridded map (ocean
temperature, elevation, bathymetry, ...) becomes a buildable mosaic with a cited parts list,
marketplace wanted lists and printable build sheets.

Not affiliated with or endorsed by The LEGO Group.

- `cli/`: the command-line tool and library (`lego-image-processor`): recipes, datasets, maps,
  parts lists, build sheets, frame arrangements. See `cli/README.md`.
- `web/`: the site at https://98138.world, built from the CLI library. See `web/README.md` and
  `docs/deploy.md`.
- `docs/vision.md` (the model and roadmap), `docs/runbook.md` (try everything locally),
  `specs/` (one Spec Kit directory per feature).

Data citations and licenses are shown with every map and recorded in its outputs. Catalog data:
Rebrickable, BrickLink, LDraw, Brickset.

# Runbook: trying out 98138.world

This walks through everything built so far (features 001–006): the kit reference data, maps from
recipes, parts lists and marketplace exports, and printable build sheets. Allow about 15 minutes.
Not affiliated with or endorsed by The LEGO Group.

## Quick start: run the whole demo

You need [uv](https://docs.astral.sh/uv/) and a network connection for the first run.

```bash
cd ~/dev/98138_world
scripts/demo.sh                 # writes everything to ./demo-output (git-ignored)
open demo-output                # macOS: look at the PNGs, PDFs and exports
```

The script installs the CLI into `cli/.venv` with Python 3.11 (uv downloads it if needed),
downloads two public datasets (about 10.5 MB, once, into `~/.cache/lego-image-processor/`), and
runs every step below. Every later run works offline.

To run commands yourself afterwards:

```bash
source cli/.venv/bin/activate
lego-image-processor --help
```

## Step by step: what to look at

### 1. Kit reference data

```bash
lego-image-processor kit inventory
lego-image-processor kit colors
```

Look for the inventory from the instructions' page 159: 3,064 white round plates (part 6141) for
land and 8,066 round tiles (part 98138) in nine colors for the ocean. `kit colors` shows each
color's LEGO, BrickLink and Rebrickable name and ID, with sources.

### 2. Maps from recipes

```bash
lego-image-processor map recipes
lego-image-processor map build official-31203 -o official.json --preview official.png
lego-image-processor map build ocean-sst -o sst.json --preview sst.png --fetch
lego-image-processor map build land-elevation -o elev.json --preview elev.png --fetch
lego-image-processor map build official-31203-bathymetry -o bathy.json --preview bathy.png
```

- `official.png` is the kit's own design, rebuilt exactly (10,240 of 10,240 studs match).
- `sst.png` is ocean temperature (blue = cold, coral = warm) on white land. It uses only the kit's
  tiles, so one kit builds it.
- `elev.png` is land elevation on ten plate colors (green, then tan and brown, then grey and
  white) with a quiet blue ocean.
- `bathy.png` is the official design's colors re-ordered by real ocean depth. About 27% of ocean
  studs land on the same color as LEGO's, because the official ocean is an artistic texture, not
  a strict depth map.
- `--fetch` downloads a recipe's dataset only if it is not cached; without it a build never uses
  the network and tells you what to fetch.
- Each build prints a suitability report: how much detail is lost at stud scale, how many cells
  were filled from neighbours, and the dataset's citation and license.

### 3. Check a layout against the kit

```bash
lego-image-processor validate official.json   # 100% buildable from one kit
lego-image-processor validate elev.json       # flags the plate colors the kit doesn't have
```

### 4. Parts lists and kit top-up

```bash
lego-image-processor parts list elev.json            # every piece
lego-image-processor parts list elev.json --kits 1   # only what one kit doesn't cover
lego-image-processor parts list elev.json --kits 3
```

With one kit the elevation map needs 6,382 more pieces; with three, 2,912. You can also describe
an incomplete secondhand kit with `--missing missing.csv`, or loose parts you own with
`--owned owned.csv`. Both take Rebrickable's import CSV (`Part,Color,Quantity`).

### 5. Marketplace exports

```bash
lego-image-processor parts export elev.json --kits 1 \
  --bricklink elev-bricklink.xml --rebrickable elev-rebrickable.csv
```

The BrickLink file uses BrickLink's own numbers (plate 4073, tile 98138, BrickLink color IDs); the
Rebrickable file uses Rebrickable's (plate 6141). No prices are estimated. The marketplaces price
an uploaded list.

### 6. Build sheets

```bash
lego-image-processor sheets build official.json -o official-sheets.pdf
lego-image-processor sheets build elev.json -o elev-sheets.pdf --paper a4 --sections B2,C2
lego-image-processor sheets build sst.json -o sst-svg --format svg
lego-image-processor sheets counts official.json
```

The PDF has an overview page, a legend with every color's IDs, and one true-scale page per
16×16 section (A1–H5), with numbered studs and per-section counts.

### 7. Make your own map

```bash
lego-image-processor map recipes --copy ocean-sst my-map.toml
# edit my-map.toml: change the title, reorder or swap colors, change the classification
lego-image-processor map check my-map.toml
lego-image-processor map build my-map.toml -o my-map.json --preview my-map.png
```

`lego-image-processor kit part-colors --part 98138` lists the tile colors a recipe can use, and
`--part 6141` lists the plate colors. A recipe can also point to your own gridded data file, if it
declares the file's checksum, citation and license (see `specs/004-map-recipes/quickstart.md`).

### 8. From an image (the original feature 001/002 path)

```bash
lego-image-processor quantize photo.jpg -o photo_lego.png    # snap colors to LEGO colors
lego-image-processor layout cli/tests/fixtures/images/test_128x80_quantized.png -o image.json
lego-image-processor parts list image.json
```

`layout` needs a 128×80 image whose colors are already LEGO colors.

## Checks that need you

These can't be automated:

1. **Print scale.** Print one section page at 100% (turn off "fit to page"). Measure the scale bar
   at the bottom: it should be 100 mm, and a row of 16 studs should be 128 mm.
2. **BrickLink upload.** On BrickLink, go to Wanted → Upload, paste the contents of
   `elev-bricklink.xml`, and check that every item is found with the right color. Then price it.
3. **Rebrickable import.** On Rebrickable, go to My LEGO → Parts Lists → Import, and upload
   `elev-rebrickable.csv`. Check that all 11 lots import with the right colors.

Tell me what you find, especially any part or color that fails to match.

## Troubleshooting

- **Install fails building scikit-image:** the CLI pins scikit-image 0.21, which has prebuilt
  packages only up to Python 3.11. Use `uv venv --python 3.11` (the demo script does this).
- **`map build` exits 3:** the dataset isn't cached. Add `--fetch`, or run
  `lego-image-processor dataset fetch --recipe <recipe>`.
- **Exit 4:** a download didn't match its pinned checksum. Delete the cached file and fetch again;
  if it keeps failing, the source changed and the pin needs updating.
- **Exit 6 from `parts export`:** some colors in the layout have no cited IDs. `parts list` shows
  which; `--allow-partial` exports the rest.
- **Run the test suite:** `cd cli && uv pip install pytest pytest-cov pytest-benchmark pypdf`,
  then `.venv/bin/pytest -q` (about 850 tests, 1–2 minutes). Tests never use the network.

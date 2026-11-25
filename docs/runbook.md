# Runbook: trying out 98138.world

This walks through everything built so far (features 001–007): the kit reference data, maps from
recipes, parts lists and marketplace exports, printable build sheets, and the three ways to hang
the map. Allow about 15 minutes.
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

- Every map except `official.png` gets a one-stud land shadow: the 392 ocean studs just east of
  land are Earth Blue, as on the official design. A recipe can turn it off or recolor it with a
  `[shadow]` table.
- `official.png` is the kit's own design, rebuilt exactly (10,240 of 10,240 studs match). Its
  recipe turns the shadow off because the design grid already contains it.
- `sst.png` is ocean temperature (blue = cold, coral = warm) on white land, with the shadow. It
  uses only the kit's tiles, so one kit builds it.
- `elev.png` is land elevation on ten plate colors (green, then tan and brown, then grey and
  white). The ocean is calm Dark Turquoise (Bright Bluish Green) with a Medium Azure halo along the
  coasts that fades evenly offshore, plus the Earth Blue shadow.
- `bathy.png` is the official design's colors re-ordered by real ocean depth, with the shadow
  drawing the official Earth Blue. About 32% of ocean studs land on the same color as LEGO's
  (27% before the shadow), because the official ocean is an artistic texture, not a strict depth
  map.
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

With one kit the elevation map needs 6,330 more pieces (3,418 of them Bright Bluish Green tiles);
with three, 2,912. You can also describe
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

### 7. Arrangements: hang the map three ways

```bash
lego-image-processor map build land-elevation --arrangement B -o elev-B.json --preview elev-B.png
lego-image-processor map build land-elevation --arrangement C -o elev-C.json --preview elev-C.png
lego-image-processor layout arrange official.json --arrangement B -o official-B.json
lego-image-processor validate official-B.json
lego-image-processor sheets build elev-B.json -o elev-B-sheets.pdf
```

The kit's three frames (1 America, 2 Europe & Africa, 3 Asia & Australia) can be hung as A
(1·2·3, the default), B (3·1·2, America in the centre) or C (2·3·1, Asia and Australia in the
centre). Look at `elev-B.png`: the Pacific is now whole, and the shadow and halo follow the coasts
across the old edge. `layout arrange` just moves frames, so any layout can be re-hung. The B sheets
draw the frame lines after columns 32 and 64 and name each frame.

### 8. ENSO maps: El Niño and La Niña

Four commands from nothing to both layouts and their top-up lists (the first two fetch the two
pinned NOAA ERSST v5 per-month files, 134,832 bytes each, checked by SHA-256):

```bash
lego-image-processor map build ocean-el-nino --fetch -o el-nino.json --preview el-nino.png --report el-nino-report.json
lego-image-processor map build ocean-la-nina --fetch -o la-nina.json --preview la-nina.png --report la-nina-report.json
lego-image-processor parts list el-nino.json --kits 1
lego-image-processor parts list la-nina.json --kits 1
```

What to look for:

- each build prints `Arrangement: B (americas, frames 3·1·2, America in the centre) - from the
  recipe`: the recipes set `arrangement = "B"` so the Pacific is whole;
- a `Legend (°C):` block with nine lines from `below -1.5` (Earth Blue) to `+1 and above`
  (Vibrant Coral), the same in both maps; in `el-nino.png` the eastern equatorial Pacific is
  orange and coral, in `la-nina.png` it is blue-green;
- `Tiles beyond one kit: 1,114` (El Niño) and `1,155` (La Niña) under the ocean table, with an
  `over_supply` warning naming the colors;
- the ERSST v5 citation (doi 10.1175/JCLI-D-16-0836.1 and dataset doi 10.7289/V5T72FNM) and the
  license;
- `parts list --kits 1` lists only ocean tiles to buy, totalling the same 1,114 and 1,155; no
  land plates. `parts export el-nino.json --kits 1 --bricklink wanted.xml` writes them as a
  BrickLink wanted list.

To hang either map another way, pass `--arrangement A` (or C): the flag wins over the recipe and
the output says `- from --arrangement`; `layout arrange el-nino.json --arrangement A -o
el-nino-A.json` re-hangs a built layout without rebuilding.

The El Niño map is meant to move to the 2026-27 event once it peaks. NCEI's per-month files from
2010 on are netCDF-4; feature 013's `netcdf4` format reads them (size-1 `time`/`lev` axes dropped,
packing decoded, as the netCDF-3 files), so the swap is a new dataset entry with
`"format": "netcdf4"` and a changed `dataset` line and title in `ocean-el-nino`.

### 9. Living planet: plant productivity and ocean chlorophyll

One command fetches the three datasets (MOD17A3 NPP, 385 MB over HTTP, checked by SHA-256; the
MODIS-Aqua chlorophyll climatology from ERDDAP, 147 MB, checked by a content SHA-256; ETOPO 2022 for
the land/ocean split) and builds the map:

```bash
lego-image-processor map build living-planet --fetch -o living.json --preview living.png --report living-report.json
lego-image-processor parts list living.json --kits 1
```

What to look for:

- `No data (share): 702 cells of lego_white` under the land layer (ice: Greenland, Antarctica, the
  high Arctic) and `No data (unobserved): 738 cells of lego_white` under the ocean layer (sea ice);
- `Land shadow (cast east): 392 cells of lego_black`;
- a `Legend (g C m-2 yr-1):` block from `below 100` (Brick Yellow) to `850 and above` (Dark Green)
  and a `Legend (mg m-3):` block from `below 0.08` (Bright Blue) to `1 and above` (Earth Green);
- three citations (Zhao et al. 2005 for NPP, ETOPO 2022, NASA OBPG R2022.0 for chlorophyll);
- about 6,600 pieces beyond one kit (most land colors and Bright Blue, Dark Azur, Earth Green,
  White and Black tiles are not in the kit).

The build reads the 43200 × 16800 GeoTIFF strip by strip (12 × 12 pixel means) and needs about
600 MB of memory.

### 10. Rainfall: precipitation on land and sea

One command fetches GPCP v2.3 (0.7 MB, netCDF-4) and 60 NSIDC sea-ice files (17.8 MB, each checked
by SHA-256) and builds the map:

```bash
lego-image-processor map build rainfall --fetch -o rain.json --preview rain.png --report rain-report.json
lego-image-processor parts list rain.json --kits 1
```

What to look for:

- `Override Antarctica (region): 595 cells` and `Override Greenland (region): 116 cells` of
  `lego_white` under the land layer, `Override sea ice (dataset): 759 cells of lego_white` under the
  ocean layer, and `Land shadow (cast east): 392 cells of lego_black`;
- `Legend (mm/day; mm/yr):` blocks, e.g. `0.5 to 1 (182.5 to 365 mm/yr)` (Sand Yellow) and
  `5 and above (1825 mm/yr and above)` (Earth Blue);
- `filled from neighbours: 0 cells` (bilinear sampling needs no fill);
- two citations (Adler et al. 2018 for GPCP; Meier et al. 2026 for NSIDC sea ice);
- about 8,160 pieces beyond one kit (Earth Blue 567, the kit has 393).

The sea-ice rule, its comparison with the approved prototype and the choice of 60 files are in
`specs/013-rainfall/research.md` (R2). `dataset info nsidc-cdr-v6-seaice-minimum-1991-2020` shows
the file count and a manifest checksum; a revised NSIDC file fails its checksum and needs a new
pinned version.

### 11. Stickers for a plaque (feature 017)

Every map gets two printed labels, white on black, made from the built map: a large sticker for a
Black tile 8×16 (part 4974) and a small one for a Black tile 6×6 (part 10202). They build the map
from cached data, like `map cells`, and never download:

```bash
lego-image-processor map stickers ocean-sst -o sst-stickers.pdf                 # print sheet, Letter
lego-image-processor map stickers ocean-sst -o sst-stickers-a4.pdf --paper a4   # A4, same sizes
lego-image-processor map stickers rainfall -o rain-stickers-svg --format svg    # one SVG per sticker
lego-image-processor map stickers official-31203 -o official-stickers.json --format json
```

What to look for:

- `sst-stickers.pdf` is one page: the large sticker (125.8 × 61.8 mm) and the small one (45.8 mm
  square) at true size, with a black bleed and cut marks, the 100 mm scale bar, "Print at 100% (no
  fit-to-page)", the parts for a standalone plaque, the ERSST v5 citation and license, and the
  disclaimer.
- The large sticker reads "Ocean temperature", the sticker line, nine ocean swatches from "-2 °C;
  land shadow" to "28 to 30 °C", White "land", the ERSST v5 credit with its DOI, "98138.world" and
  the disclaimer; the small one only the title, the line and the disclaimer.
- The output lists each plaque's tile and, to stand it alone, a Black plate of the same size (3958
  for 6×6, 92438 for 8×16), with LEGO element, BrickLink and Rebrickable IDs, and says the sticker
  is printed, not a LEGO part. The stickers are the same for A, B and C, and making them writes
  nothing but the file you name.
- `rain-stickers-svg/` holds `sticker-small.svg` and `sticker-large.svg` in millimetres, each with
  its cut line as `<g id="cut-line">` for a cutting machine. `rainfall`'s legend is in mm/yr, with
  one White swatch for Antarctica and Greenland and one for sea ice.

The title and line come from the recipe's optional `[sticker]` table (`title`, `line`, `credit`,
`no_data`), else from its `title` and `description`; see `cli/README.md`.

On the Winkel tripel template (feature 016) the stickers name the projection, and the small
plaque's tile can go into a margin corner as part of the build:

```bash
lego-image-processor map stickers ocean-sst --template winkel-tripel -o sst-winkel-stickers.pdf
lego-image-processor map build ocean-sst --template winkel-tripel --plaque bottom-left \
  -o sst-plaque.json --preview sst-plaque.png
lego-image-processor parts list sst-plaque.json --kits 1
lego-image-processor sheets build sst-plaque.json -o sst-plaque-sheets.pdf --sections A5
```

- The Winkel stickers' line ends with "Winkel tripel projection." and the large one also credits
  ETOPO 2022, which decided land and ocean.
- `--plaque bottom-left` puts one Black tile 6×6 at rows 73–78, columns 1–6 (one stud in from the
  board edges), in place of 36 square margin tiles: the `Plaque:` line says where, and `Layout:`
  counts 10,204 positions and 1 plaque tile. Land and ocean are the same as without it.
- The parts list has the tile to buy (BrickLink 10202, Black) and 1,960 square tiles instead of
  1,996; section A5 of the sheets draws the tile as one outlined rectangle "tile 6x6 (10202)".
- A recipe can name the corner with `plaque = "bottom-left"` in its `[margin]` table;
  `--plaque none` turns it off, and `--plaque` on the kit template is an error (it has no margin).

### 12. Make your own map

```bash
lego-image-processor map recipes --copy ocean-sst my-map.toml
# edit my-map.toml: change the title, reorder or swap colors, change the classification
lego-image-processor map check my-map.toml
lego-image-processor map build my-map.toml -o my-map.json --preview my-map.png
```

`lego-image-processor kit part-colors --part 98138` lists the tile colors a recipe can use, and
`--part 6141` lists the plate colors. A recipe can also point to your own gridded data file, if it
declares the file's checksum, citation and license (see `specs/004-map-recipes/quickstart.md`).

### 13. From an image (the original feature 001/002 path)

```bash
lego-image-processor quantize photo.jpg -o photo_lego.png    # snap colors to LEGO colors
lego-image-processor layout cli/tests/fixtures/images/test_128x80_quantized.png -o image.json
lego-image-processor parts list image.json
```

`layout` needs a 128×80 image whose colors are already LEGO colors.

## The web site locally (feature 008)

The site at 98138.world is the same outputs, prebuilt and served. To run it on your machine:

```bash
cd ~/dev/98138_world/web
uv venv --python 3.11 && uv pip install -e ../cli -e . pytest httpx2 pypdf
.venv/bin/python -m web98138.prebuild --out site-output      # ~30 s; add --fetch if datasets aren't cached
WEB98138_SITE_DIR=site-output .venv/bin/uvicorn web98138.app:app --port 8080
open http://127.0.0.1:8080/
```

Look for: the gallery of four maps; on a map page the A/B/C switch (the preview shifts by whole
frames), the parts summary (official, bathymetry and ocean temperature say one kit covers every
piece; land elevation needs about 6,300 more), the lots table with BrickLink and Rebrickable IDs,
the downloads list (top-up files only appear when one kit is not enough), and the citations. The
"Stickers for a plaque" panel shows both stickers, what the large one says, the plaque parts with
their IDs and four downloads (print sheet Letter and A4, both SVGs), the same for A, B and C and
without JavaScript; a Winkel tripel page shows its own set. Try it at phone width. `.venv/bin/pytest` runs the web tests offline. Deploying: `docs/deploy.md`.

## Checks that need you

These can't be automated:

1. **Print scale.** Print one section page at 100% (turn off "fit to page"). Measure the scale bar
   at the bottom: it should be 100 mm, and a row of 16 studs should be 128 mm.
2. **BrickLink upload.** On BrickLink, go to Wanted → Upload, paste the contents of
   `elev-bricklink.xml`, and check that every item is found with the right color. Then price it.
3. **Rebrickable import.** On Rebrickable, go to My LEGO → Parts Lists → Import, and upload
   `elev-rebrickable.csv`. Check that all 11 lots import with the right colors.
4. **Sticker print.** Print `sst-stickers.pdf` at 100% on white sticker paper. The scale bar should
   measure 100 mm, the large sticker's cut line 125.8 × 61.8 mm and the small one's 45.8 mm. Cut
   one out along its marks and lay it on its Black tile: about 1 mm of tile should show on every
   side.

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
- **`map stickers` stops on a text:** a title, line or legend that does not fit at 5 pt names the
  field or layer and the space needed and available; shorten it in the recipe's `[sticker]` table. Text
  outside Latin-1 cannot go in the PDF (standard Helvetica): use `--format svg`.
- **Run the test suite:** `cd cli && uv pip install pytest pytest-cov pytest-benchmark pypdf`,
  then `.venv/bin/pytest -q` (about 970 tests, 1–2 minutes). Tests never use the network.

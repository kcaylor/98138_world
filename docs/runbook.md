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

The PDF has an overview page, a legend with every color's IDs, one true-scale page per
16×16 section (A1–H5), with numbered studs and per-section counts, and a last page showing how to
hang the frames (assembly).

### 7. Arrangements: hang the map five ways

```bash
lego-image-processor map build land-elevation --arrangement B -o elev-B.json --preview elev-B.png
lego-image-processor map build land-elevation --arrangement C -o elev-C.json --preview elev-C.png
lego-image-processor map build land-elevation --arrangement pacific -o elev-D.json --preview elev-D.png
lego-image-processor layout arrange official.json --arrangement B -o official-B.json
lego-image-processor layout arrange official.json --arrangement E -o official-E.json
lego-image-processor validate official-B.json
lego-image-processor sheets build elev-B.json -o elev-B-sheets.pdf
lego-image-processor sheets build elev-D.json -o elev-D-sheets.pdf
```

The kit's three frames (1 America, 2 Europe & Africa, 3 Asia & Australia) can be hung as A
(1·2·3, the default), B (3·1·2, America in the centre) or C (2·3·1, Asia and Australia in the
centre), the three combinations in the building instructions (pp. 7–8). Look at `elev-B.png`: the
Pacific is now whole, and the shadow and halo follow the coasts across the old edge. `layout
arrange` just moves strips, so any layout can be re-hung. The B sheets draw the frame lines after
columns 32 and 64 and name each frame.

Two more combinations are **not** in the building instructions (feature 010):

- D (`pacific`, 2b·3·1·2a, strips E F G H A B C D): the date line 11° left of centre, the whole
  Pacific in the middle; the board's edges cut Europe and Africa at 11° E.
- E (`asia-pacific`, 2b·3·1·2a, strips D E F G H A B C): 146° E in the centre, the usual
  Asia-Pacific world map; the edges fall in the mid-Atlantic.

They are possible because the board is 8 strips of five section bases (A–H, the kit's section
columns), and a joint between two strips inside a frame uses the same 15 connector pegs as a joint
between frames (building instructions, pp. 134–139); the white border is built once round the
finished board (p. 140). So the 8 strips can be hung in any rotation with one kit's parts: 7 strip
joints × 15 + 8 strips × 4 × 3 = 201 of the 205 connector pegs, for every combination. Every
sheet set ends with an assembly page for its combination (A–C too); for D and E it reads:

1. Build the 40 section bases, peg them into 8 strips of five, then the strips into the three
   frames, as in the building instructions (pp. 134–138): frame 1 = strips A–B, frame 2 = C–F,
   frame 3 = G–H.
2. Unpeg frame 2 between strips D and E (for E: between C and D): take out that joint's 15
   connector pegs and keep them. Frame 2 is now part 2a (strips C–D; for E, strip C) and part 2b
   (strips E–F; for E, D–F).
3. Lay the groups face up, left to right: 2b · 3 · 1 · 2a.
4. Peg the groups together at F|G, H|A and B|C, 15 connector pegs per joint, as for the frame
   joints on p. 139.
5. Build the white border round the whole board as in pp. 140–153; it is the same for every
   combination.

`--arrangement` and the recipe key `arrangement` accept `A`–`E` or the names `europe-africa`,
`americas`, `asia-australia`, `pacific`, `asia-pacific`. A D or E layout records
`"in_instructions": false`, its strip order and groups, and cites pp. 134–140.

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

- each build prints `Arrangement: D (pacific, frames 2b·3·1·2a, the Pacific (date line) in the
  centre; not in the building instructions) - from the recipe`: the recipes set `arrangement =
  "D"` (feature 010; it was B in feature 009) so the date line is in the centre; the land shadow
  takes 387 Earth Blue tiles;
- a `Legend (°C):` block with nine lines from `below -1.5` (Earth Blue) to `+1 and above`
  (Vibrant Coral), the same in both maps; in `el-nino.png` the eastern equatorial Pacific is
  orange and coral, in `la-nina.png` it is blue-green;
- `Tiles beyond one kit: 1,114` (El Niño) and `1,152` (La Niña) under the ocean table (in B:
  1,114 and 1,155; in E: 1,112 and 1,158), with an
  `over_supply` warning naming the colors;
- the ERSST v5 citation (doi 10.1175/JCLI-D-16-0836.1 and dataset doi 10.7289/V5T72FNM) and the
  license;
- `parts list --kits 1` lists only ocean tiles to buy, totalling the same 1,114 and 1,152; no
  land plates. `parts export el-nino.json --kits 1 --bricklink wanted.xml` writes them as a
  BrickLink wanted list.

To hang either map another way, pass `--arrangement B` (or A, C, E): the flag wins over the recipe and
the output says `- from --arrangement`; `layout arrange el-nino.json --arrangement A -o
el-nino-A.json` re-hangs a built layout without rebuilding.

The El Niño map is meant to move to the 2026-27 event once it peaks. NCEI's per-month files from
2010 on are netCDF-4, which needs a new reader first; the swap is then a new dataset entry and a
changed `dataset` line and title in `ocean-el-nino`.

### 9. Make your own map

```bash
lego-image-processor map recipes --copy ocean-sst my-map.toml
# edit my-map.toml: change the title, reorder or swap colors, change the classification
lego-image-processor map check my-map.toml
lego-image-processor map build my-map.toml -o my-map.json --preview my-map.png
```

`lego-image-processor kit part-colors --part 98138` lists the tile colors a recipe can use, and
`--part 6141` lists the plate colors. A recipe can also point to your own gridded data file, if it
declares the file's checksum, citation and license (see `specs/004-map-recipes/quickstart.md`).

### 10. From an image (the original feature 001/002 path)

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
the downloads list (top-up files only appear when one kit is not enough), and the citations. Try it
at phone width. `.venv/bin/pytest` runs the web tests offline. Deploying: `docs/deploy.md`.

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
  then `.venv/bin/pytest -q` (about 970 tests, 1–2 minutes). Tests never use the network.

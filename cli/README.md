# LEGO Image Processor

A CLI tool that converts images to LEGO-compatible color palettes and generates buildable LEGO World Map layouts.

## Features

- Convert images to use only official LEGO brick colors
- Delta E 2000 (CIEDE2000) color matching algorithm for accurate color reproduction
- Support for PNG, JPEG, and TIFF image formats
- Color statistics and analysis
- **LEGO World Map Layout Generation** (128×80 grid = 10,240 positions)
- **Kit Inventory Validation** against LEGO World Map kit 31203
- **Cited kit reference data**: the 31203 parts inventory and its 10 map colors (`kit` commands)
- **Maps from recipes** (feature 004): a TOML recipe names a land layer and an ocean layer; data
  layers read pinned, cached public datasets (ETOPO 2022, NOAA ERSST v5), reprojected to the kit
  grid, classified onto ordered LEGO color scales and textured (`map`, `dataset` commands)
- **Parts lists and ordering** (feature 005): a parts list with cited LEGO, BrickLink and
  Rebrickable IDs from any layout, kit top-up (only what you do not own), a BrickLink wanted list
  and a Rebrickable parts CSV (`parts` commands, `kit part-numbers`)
- **Build sheets** (feature 006): printable section-by-section pages at true scale with numbered
  studs and per-section counts, as a PDF or SVG pages, plus per-section counts JSON (`sheets`
  commands)
- **Map arrangements** (features 007, 010): the kit's three frames can be hung in three orders
  (combination A Europe and Africa in the centre, B America, C Asia and Australia), plus two
  Pacific-centred combinations that are not in the building instructions (D the date line, E
  146° E; frame 2 split in two); build any map in any of them (`map build --arrangement`) or
  re-hang an existing layout (`layout arrange`); build sheets end with an assembly page
- **Price estimates** (feature 011): an estimated cost for any layout, for every piece and for
  what one 31203 kit does not cover, from a dated, cited BrickLink price guide snapshot, offline
  (`parts estimate`); the maintainer refreshes the snapshot with the BrickLink API
  (`parts prices fetch`)
- **ENSO maps** (feature 009): sea surface temperature anomaly of a strong El Niño (December 1997)
  and a strong La Niña (December 1988) on one shared °C legend, date line centred (D; recipes
  `ocean-el-nino`, `ocean-la-nina`; recipe key `arrangement`)
- **Living planet** (feature 012): plant productivity (MODIS MOD17A3 net primary production,
  2000-2015) on land and ocean chlorophyll-a (MODIS-Aqua, 2013-2024) at sea, with ice in White and a
  Black land shadow (recipe `living-planet`; strip GeoTIFF reader, climatology means, `log10`
  transform, `no_data` rules)
- **Rainfall** (feature 013): annual mean precipitation 1991-2020 (GPCP v2.3) on land and sea,
  with White ice sheets, NSIDC sea ice and a Black land shadow (recipe `rainfall`; netCDF-4 reader
  with h5py, multi-file datasets, bilinear sampling, `override` rules, two-unit legends)
- **Map templates** (feature 016): the kit grid is the reference template; Winkel tripel on the
  kit's 8 × 5 board is the first other one, a curved world map with a margin of 1×1 square tiles
  (part 3070b) in one color and an optional outline ring (`template` commands, `map build
  --template`, recipe keys `template` and `[margin]`); maps build on it once the project owner
  confirms its layout

## Installation

```bash
cd cli
poetry install
# without Poetry: uv venv --python 3.11 && uv pip install -e . pytest pytest-cov pytest-benchmark
```

## Usage

### Image Quantization

```bash
# Quantize a single image to LEGO colors
lego-image-processor quantize input.png -o output.png

# Get color statistics
lego-image-processor stats output.png
```

Batch processing of a whole directory is planned (spec 001, user story 3) but not built yet.

### Layout Generation

Generate LEGO World Map layouts from quantized images:

```bash
# Generate JSON layout from quantized image
lego-image-processor layout quantized.png -o layout.json

# Generate CSV layout
lego-image-processor layout quantized.png -o layout.csv -f csv

# Quiet mode (no console output; the JSON file still carries the disclaimer)
lego-image-processor layout quantized.png -o layout.json -q
```

The layout command:
- Requires a 128×80 pixel quantized image
- Uses the official LEGO World Map land/sea mask
- Outputs position-by-position placement instructions
- Distinguishes land positions (1×1 round plates, part 6141, white) from ocean positions (1×1 round tiles, part 98138)
- Writes layout format **schema version 2.0** (see below)

#### Layout format 2.0

Layout files carry `metadata.schema_version: "2.0"` and `metadata.disclaimer`. Version 2.0 changed
the land part: land positions use `part_type: "plate"` and `lego_part_id: "6141"` (1x1 round plate;
Rebrickable files it as 6141, BrickLink numbers it 4073); ocean positions use `part_type: "tile"` and
`lego_part_id: "98138"`. The statistics block uses `land_plate_count` and
`color_frequency_by_part_type` keys `plate` and `tile`.

Layouts built from a recipe (`map build`) add a `metadata.map` block with the recipe id, format
and SHA-256, each layer's role, dataset, citation and license, the texture seed and the
disclaimer; `source_image` is `recipe:<id>`. The schema version stays 2.0 and older readers ignore
the block.

Layouts built on a non-kit template (feature 016, see "Map templates") add `metadata.template` and
`metadata.margin_positions`, margin positions with `part_type: "square_tile"` and
`lego_part_id: "3070b"`, and `statistics.margin_tile_count`. The schema version stays 2.0; a
layout without `metadata.template` is on the kit.

Layout files written with an earlier schema version (1.0) are rejected, not upgraded. Regenerate
them with `lego-image-processor layout <image> -o <layout.json>`.

### Layout Validation

Validate layouts (schema 2.0) against the cited kit 31203 inventory:

```bash
# Validate a layout
lego-image-processor validate layout.json

# Save validation report to file
lego-image-processor validate layout.json -o report.json

# Validate against specific kit
lego-image-processor validate layout.json --kit 31203
```

The validate command checks:
- Color availability per part: land positions may use only White (1x1 round plate, 6141); ocean
  positions only the kit's 9 tile colors (1x1 round tile, 98138). Each unavailable color is
  reported with its part, position count, and the nearest kit color of that part by CIEDE2000
  (`Suggested alternative: <color> (ΔE00 x.x)`)
- Quantity limits from the instructions' parts inventory (page 159): required, available, shortfall
- Provides buildability score (percentage of positions buildable)
- Rejects layout files written with schema 1.0 (exit 1, with the command to regenerate them)

The report JSON (`-o`) carries a `disclaimer` field. The official design itself validates as
100% buildable:

```bash
python -c "from lego_image_processor.kit import load_official_design; \
open('official.json','w').write(load_official_design().to_layout().to_json())"
lego-image-processor validate official.json   # Buildability: 100.0% (FULLY BUILDABLE)
```

### Kit reference data

Read-only, offline views of the kit 31203 reference data shipped with the package:

```bash
# Every element on the instructions' parts inventory page (page 159): 32 lines, 11,694 pieces
lego-image-processor kit inventory
lego-image-processor kit inventory --role ocean
lego-image-processor kit inventory --format json

# The 10 map colors with LEGO, BrickLink and Rebrickable names and IDs
lego-image-processor kit colors
lego-image-processor kit colors --format json
```

Element IDs and quantities come from page 159 of the official building instructions (pinned by URL
and SHA-256 in each data file's `source` block). Part numbers, descriptions and color mappings come
from the catalogs cited in the same files (Brickset, LDraw, BrickLink, Rebrickable). The data is
regenerated by a maintainer tool in `tools/kit31203`, which is not part of the package; end users
never need the PDF or network access. The tool is found only with `tools` on the module path, so
run it from `cli/` with `PYTHONPATH=tools`:

```bash
poetry install --with maintainer
PYTHONPATH=tools poetry run python -m kit31203 extract --check              # downloads and caches the pinned PDF once
PYTHONPATH=tools poetry run python -m kit31203 extract --check --pdf 31203.pdf   # or use a local copy (checksum-verified)
```

`--check` regenerates into a temporary directory and exits 0 with "no differences" when the
committed data is reproducible. Never commit the PDF or crops of its pages.

Feature 004 adds two maintainer commands (they read cached files and never commit them):

```bash
PYTHONPATH=tools poetry run python -m kit31203 fit-projection --check   # refits the kit projection from cached ETOPO
PYTHONPATH=tools poetry run python -m partcolors build --check          # rebuilds part_colors.json from pinned snapshots
PYTHONPATH=tools poetry run python -m fixtures004.make_fixtures          # rewrites the small derived test fixtures
```

The part-color snapshots live in `<cache>/sources/partcolors/` (`elements.csv.gz`,
`colors.csv.gz`, `LDConfig.ldr`, `catalogColors.html`); their SHA-256s are pinned in
`tools/partcolors/build.py`.

### Maps from recipes

A map is a land layer plus an ocean layer on a template: by default the kit 31203 grid (128×80,
the kit's land/sea mask), or a confirmed template such as Winkel tripel (see "Map templates"
below). Each layer is **data** (a gridded field classified onto an ordered color scale) or
**background** (fixed colors: mixed by weight, or a coastal halo). Every map also gets a one-stud
**land shadow**: the ocean cells just east of land, in Earth Blue, as on the official design (391
of its 392 Earth Blue tiles sit there). The shadow is drawn first, uses 392 of the kit's 393 Earth
Blue tiles, and the ocean layer covers the other 6,786 ocean cells. Eight recipes are bundled:

| Recipe | Land | Ocean | Data needed |
|---|---|---|---|
| `official-31203` | White | the official design grid, one-to-one (exact: 10,240/10,240; shadow off, the design already has it) | none (packaged) |
| `official-31203-bathymetry` | White | shadow in Earth Blue; depth ranked into the official counts and color order of the other eight colors, blended | ETOPO 2022 |
| `ocean-sst` | White | shadow; annual mean SST 1991-2020, cold to warm, counts within one kit's supply net of the shadow | ERSST v5 |
| `ocean-el-nino` | White | shadow; SST anomaly of December 1997 (strong El Niño) on the shared ENSO legend below; hung as B | ERSST v5 December 1997 |
| `ocean-la-nina` | White | shadow; SST anomaly of December 1988 (strong La Niña) on the same legend; hung as B | ERSST v5 December 1988 |
| `living-planet` | net primary production 2000-2015 on six plate colors (Tan to Green), ice White | chlorophyll-a 2013-2024 on five tile colors (Blue to Dark Green), sea ice White, shadow Black | MOD17A3 NPP, MODIS-Aqua chl-a, ETOPO 2022 |
| `rainfall` | precipitation 1991-2020 on six plate colors (Tan to Green), ice sheets White | precipitation on five tile colors (Bright Light Blue to Dark Blue), sea ice White, shadow Black | GPCP v2.3, NSIDC sea ice CDR v6 |
| `land-elevation` | elevation on 10 plate colors (green to brown to grey to white) | shadow; Bright Bluish Green (Dark Turquoise) with a Medium Azur coastal halo that fades evenly offshore; needs more Bright Bluish Green tiles than one kit holds (reported as beyond-kit) | ETOPO 2022 |

```bash
lego-image-processor map recipes                                   # list (and whether data is cached)
lego-image-processor map build official-31203 -o official.json --preview official.png
lego-image-processor map build ocean-sst -o sst.json --fetch       # --fetch downloads missing pinned data
lego-image-processor map build land-elevation -o elev.json --report elev-report.json
lego-image-processor map check land-elevation                      # suitability report only
lego-image-processor map cells land-elevation -o cells.json        # per-cell classes/values for recoloring (015)
lego-image-processor map recipes --copy ocean-sst my-map.toml      # start a new recipe
lego-image-processor validate sst.json
```

Builds never use the network unless you pass `--fetch`. Without it, a recipe whose dataset is not
cached fails (exit 3) with `dataset fetch <id>` and the `--fetch` option, and writes nothing.
Every build prints a suitability report: share of the data's variance lost below grid scale,
cells filled from neighbours, cells per class, the closest neighbouring colors (CIEDE2000) and
color counts against one kit's supply, with warnings above 50% variance lost, 5% filled, an empty
class or ΔE00 below 5. `--preview` writes a PNG (8×8 pixels per stud, cited RGB; not a build
sheet). The texture rule of a recipe (`blend` for data layers, `mix` or `halo` for backgrounds)
replaces the "shadowing" idea of feature 002. The land shadow is set by an optional top-level
`[shadow]` table:

```toml
[shadow]                    # optional; this is the default
enabled = true              # false turns it off (official-31203 does, its grid already has it)
color = "lego_earth_blue"   # any 98138 tile color
direction = "east"          # the only direction for now

[ocean]                     # a calm ocean background with a coastal halo
role = "background"
colors = ["lego_bright_bluish_green", "lego_medium_azur"]   # offshore base, coast ring
[ocean.texture]
kind = "halo"
inner = 1.5                 # studs from land (Euclidean): all ring color
outer = 3.0                 # up to here: ring color on an even Poisson-disk subset, seeded
spacing = 2.0               # minimum distance between those fade cells
```

#### ENSO maps

`ocean-el-nino` and `ocean-la-nina` show the NOAA ERSST v5 sea surface temperature anomaly
(`ssta`, °C against the 1971-2000 climatology) of December 1997, a strong El Niño, and December
1988, a strong La Niña. Both read the per-month NCEI files (`ersst-v5-1997-12`,
`ersst-v5-1988-12`, 134,832 bytes each, pinned by SHA-256) and share one fixed legend, so the two
boards compare tile for tile. The legend reads cold to warm with zero in the middle class, uses
only the kit's nine ocean colors, and its bounds were chosen to keep the tiles beyond one kit to a
minimum (no `blend` texture, so every tile states its class exactly):

| Color | Anomaly (°C) |
|---|---|
| Earth Blue | below -1.5 |
| Bright Bluish Green | -1.5 to -0.5 |
| Medium Azur | -0.5 to -0.25 |
| Bright Green | -0.25 to -0.1 |
| Bright Yellowish Green | -0.1 to +0.1 |
| Brick Yellow | +0.1 to +0.3 |
| Flame Yellowish Orange | +0.3 to +0.5 |
| Bright Orange | +0.5 to +1.0 |
| Vibrant Coral | +1.0 and above |

A value on a bound takes the upper class. Both maps are hung as combination D (the date line in
the centre, so the Pacific is whole; feature 010, not among the building instructions'
combinations) by the recipe key `arrangement = "D"`; `--arrangement` on the
command line wins, and the build output says where the arrangement came from (`- from the recipe`,
`- from --arrangement`, `- default`; the report JSON has `arrangement_source`). A recipe without
the key is hung as A, as before.

One kit is not quite enough: the El Niño map needs 1,114 ocean tiles beyond one kit's supply and
the La Niña map 1,152 in D (the shadow's 387 Earth Blue tiles counted; in B 1,114 and 1,155, in E
1,112 and 1,158). The build prints the °C range
and cells of each color and `Tiles beyond one kit: N`; `parts list <layout> --kits 1` lists the
same tiles per color and `parts export <layout> --kits 1 --bricklink wanted.xml` writes them as a
wanted list.

```bash
lego-image-processor map build ocean-el-nino --fetch -o el-nino.json --preview el-nino.png
lego-image-processor map build ocean-la-nina --fetch -o la-nina.json --preview la-nina.png
lego-image-processor parts list el-nino.json --kits 1
lego-image-processor map build ocean-el-nino --arrangement B -o el-nino-B.json   # override
```

The El Niño map is meant to move to the 2026-27 event once it peaks. NCEI's per-month files from
2010 on are netCDF-4, which this reader does not read yet (it rejects them with a clear message),
so that swap needs a netCDF-4 reader first; it will then be a new dataset entry and a changed
`dataset` line and title in `ocean-el-nino`, with the same id and legend.

#### Living planet

`living-planet` shows where the planet is green. Land: MODIS MOD17A3 annual net primary production,
mean of 2000-2015 (NTSG, University of Montana, Collection 5.5), in g C m⁻² yr⁻¹: Brick Yellow
[BrickLink Tan] below 100, Sand Yellow [Dark Tan] 100-250, Sand Green 250-400, Bright Yellowish
Green [Lime] 400-600, Bright Green 600-850, Dark Green [Green] 850 and above, with a light blend.
Land with no NPP value (deserts, rock, ice) counts as 0; a land cell whose land is mostly
unvegetated and poleward of 55° is White (ice). Ocean: MODIS-Aqua chlorophyll-a (NASA OBPG
R2022.0 via NOAA CoastWatch ERDDAP), the mean of every valid month of 2013-2024 per pixel, on
log10: Bright Blue [Blue] below 0.08 mg m⁻³, Dark Azur [Dark Azure] 0.08-0.15, Medium Azur 0.15-0.3,
Bright Bluish Green [Dark Turquoise] 0.3-1, Earth Green [Dark Green] 1 and above. Polar ocean the
satellite never saw (poleward of 60°), or saw in fewer than 12 months (poleward of 70°), is White
(sea ice). The land shadow is Black. Expect about 6,600 pieces beyond one kit.

The map uses these general recipe and dataset options (full contract in
`specs/012-living-planet/contracts/recipe-and-datasets.md`):

```toml
[ocean]
transform = "log10"          # none | negate | log10 (values <= 0 become missing)
[ocean.classification]
method = "bins"
bounds = [0.001, 0.08, 0.15, 0.3, 1.0, 1000]   # with log10: in the variable's units, compared on log10

[ocean.no_data]              # optional, data layers
color = "lego_white"         # any color of the layer's part
rule = "unobserved"          # no valid source value and poleward of min_lat ...
min_lat = 60
sparse_lat = 70              # ... or poleward of sparse_lat with < min_steps valid steps
min_steps = 12               #     (needs a dataset with reduce = "climatology-mean")

[land.no_data]
value = 0                    # class pixels without a value take this (needs a land/ocean split)
color = "lego_white"
rule = "share"               # share of the cell's pixels without a value and poleward of min_lat
min_lat = 55
min_share = 0.5              # ... above this
```

No-data cells are assigned before the layer is classified (the land shadow still wins), are
counted in the layer's supply table, and are printed as `No data (<rule>): N cells of <color>`.

#### Rainfall

`rainfall` shows global annual mean precipitation: GPCP v2.3 monthly long-term mean 1991-2020
(NOAA PSL; Adler et al. 2018), the mean of the 12 months, sampled bilinearly at each kit cell
centre. Land, mm/day (mm/yr): Brick Yellow [Tan] below 0.5 (182.5), Sand Yellow [Dark Tan] 0.5-1,
Sand Green 1-1.5, Bright Yellowish Green [Lime] 1.5-2.5, Bright Green 2.5-4, Dark Green [Green] 4
and above (1460); Antarctica (south of 60° S) and Greenland are White. Ocean: Light Royal Blue
[Bright Light Blue] below 0.75, Medium Azur 0.75-1.5, Dark Azur 1.5-3, Bright Blue [Blue] 3-5, Earth
Blue [Dark Blue] 5 and above (1825 mm/yr). Sea ice is White: the NOAA/NSIDC sea ice concentration
CDR v6, the 1991-2020 mean of each hemisphere's minimum month (September north, February south), at
least 0.7 over the cell, or no NSIDC ocean pixel poleward of 60° (coasts, ice shelves). The land
shadow is Black (weak against Dark Blue on wet coasts: an accepted trade-off). Expect about 8,160
pieces beyond one kit.

General options it uses (full contract in `specs/013-rainfall/contracts/recipe-and-datasets.md`):

```toml
[land]
sampling = "bilinear"        # mean (default: cell mean, nearest fill) | bilinear (at cell centres)

[land.legend]                # optional: print the bins in a second unit too
units = "mm/yr"
factor = 365                 # "0.5 to 1 (182.5 to 365 mm/yr)"

[[land.override]]            # repeatable; cells take color and leave the classification
name = "Greenland"
color = "lego_white"
lat_min = 59                 # region: cell centre strictly inside the bounds ...
lon_min = -75
lon_max = -10
exclude = [{ lat_max = 67, lon_min = -26 }]   # ... and outside every excluded box

[[ocean.override]]
name = "sea ice"
color = "lego_white"
dataset = "nsidc-cdr-v6-seaice-minimum-1991-2020"   # dataset rule: the cell's mean value ...
variable = "cdr_seaice_conc_monthly"
min_value = 0.7              # ... is at least this,
unobserved_lat = 60          # or the cell has no value and lies poleward of this
```

Overrides are applied in order after any `no_data` rule (the land shadow still wins), are counted
in the supply table, and are printed as `Override <name> (<kind>): N cells of <color>`.

A recipe is a TOML file (format "1"). A minimal data layer:

```toml
# Not affiliated with or endorsed by The LEGO Group.
format = "1"
id = "my-map"
title = "My map"
arrangement = "A"                    # optional: A-E (or europe-africa, americas, asia-australia, pacific, asia-pacific)

[land]
role = "background"
colors = ["lego_white"]

[ocean]
role = "data"
dataset = "ersst-v5-ltm-1991-2020"   # or a [ocean.local] table with path, format, sha256,
variable = "sst"                     #   variable, citation and license (npy also lat/lon)
colors = ["lego_earth_blue", "lego_medium_azur", "lego_bright_yellowish_green", "lego_bright_orange"]

[ocean.classification]
method = "quantile"                  # bins | quantile | rank | rank-to-supply | categorical

[ocean.texture]
kind = "blend"
width = 0.25
```

Errors name the key path and the rule, for example
`ocean.classification.bounds: must be strictly increasing`. Colors must be available for the
layer's part: the kit's colors, or a color in `part_colors.json` (`kit part-colors`). The full
format is in `specs/004-map-recipes/contracts/recipe-format.md`.

The kit grid's projection (`data/kit_31203_projection.json`) is equirectangular with its left edge
at 168.9° W, 2.8125° per column, the equator at row 42.2 and 26.3 rows per radian, fitted to the
kit mask (94.2% agreement; Miller 90.9%, Mercator 87.0%). On the kit template the kit mask always
decides land and ocean; on another template its own layout does.

### Datasets

```bash
lego-image-processor dataset list                     # id, version, size, license, cached
lego-image-processor dataset info etopo2022-surface-10m
lego-image-processor dataset fetch ersst-v5-ltm-1991-2020
lego-image-processor dataset fetch --recipe land-elevation
```

| Dataset | Size | License | Citation |
|---|---|---|---|
| `etopo2022-surface-10m`: ETOPO 2022 surface elevation, 10-arc-minute OPeNDAP subset of the 60-arc-second grid (NOAA NCEI) | 9,357,398 B | Public domain (U.S. Government work) | NOAA National Centers for Environmental Information. 2022: ETOPO 2022 15 Arc-Second Global Relief Model. https://doi.org/10.25921/fd45-gt74 |
| `ersst-v5-ltm-1991-2020`: NOAA ERSST v5 monthly long-term mean SST, 1991-2020 (NOAA PSL) | 1,160,004 B | Public domain (NOAA) | Huang, B., et al., 2017: Extended Reconstructed Sea Surface Temperature, Version 5 (ERSSTv5). J. Climate, 30, 8179-8205. https://doi.org/10.1175/JCLI-D-16-0836.1. NOAA ERSST V5 data provided by the NOAA PSL, Boulder, Colorado, USA, from their website at https://psl.noaa.gov |
| `mod17a3-npp-mean-2000-2015`: MODIS MOD17A3 annual NPP, mean of 2000-2015, 30-arc-second GeoTIFF (NTSG, University of Montana) | 384,939,658 B | NASA-funded open data, no stated restrictions | Zhao, M., Heinsch, F. A., Nemani, R. R., & Running, S. W. (2005). Remote Sensing of Environment, 95, 164-176. https://doi.org/10.1016/j.rse.2004.12.011 |
| `modis-aqua-chla-2013-2024`: MODIS-Aqua chlorophyll-a, monthly 2013-2024, every 12th 4 km pixel (NASA OBPG R2022.0 via NOAA CoastWatch ERDDAP) | 147,236,600 B | NASA Earth Science data policy (open) | NASA OBPG (2022), MODIS-Aqua Level-3 Mapped Chlorophyll Data, R2022.0. https://doi.org/10.5067/AQUA/MODIS/L3M/CHL/2022 |
| `gpcp-v23-ltm-1991-2020`: GPCP v2.3 monthly long-term mean precipitation, 1991-2020, netCDF-4 (NOAA PSL) | 677,810 B | Public domain (U.S. Government work, NOAA PSL) | Adler, R. F., et al., 2018: The Global Precipitation Climatology Project (GPCP) Monthly Analysis (New Version 2.3) and a Review of 2017 Global Precipitation. Atmosphere, 9(4), 138. https://doi.org/10.3390/atmos9040138. GPCP Precipitation data provided by the NOAA PSL |
| `nsidc-cdr-v6-seaice-minimum-1991-2020`: NOAA/NSIDC sea ice concentration CDR v6, September (north) and February (south) of 1991-2020, 60 netCDF-4 files | 17,826,152 B | No constraints on data access or use | Meier, W. N., et al., 2026: NOAA/NSIDC Climate Data Record of Passive Microwave Sea Ice Concentration, Version 6 (G02202). NSIDC. https://doi.org/10.7265/b18j-z797 |
| `kit31203-design`: the official design grid | packaged | facts from the official instructions | see `kit_31203_design.json` |

Each download is pinned by URL, exact size and SHA-256, downloaded to a temporary file, verified
and then moved into the per-user cache. Two exceptions (feature 012): the ERDDAP chlorophyll file
is built by the server on each request and carries the request time in its header, so it is
pinned by `content_sha256`, a SHA-256 over its decoded data and coordinates; and the NTSG host
serves the NPP GeoTIFF over plain HTTP only, so that entry states why (`http_only`) and is pinned
by its file SHA-256. GeoTIFF files are read strip by strip and averaged in `grid.block` × `grid.block`
pixel blocks (12 for NPP, 0.1°), so the 43200 × 16800 image is never decoded whole. Feature 013
adds `format = "netcdf4"` (netCDF-4/HDF5, read with h5py; CF fill, valid range and packing; CF
polar-stereographic x/y become latitude/longitude) and multi-file entries: a `files` list (each URL
pinned by size and SHA-256; the entry's `size` is their total), cached together in the entry's
version directory and averaged per pixel with `reduce = "climatology-mean"`. Files go into
the per-user cache (`$LEGO_IMAGE_PROCESSOR_CACHE`, else
`$XDG_CACHE_HOME/lego-image-processor`, else `~/.cache/lego-image-processor`; `--cache-dir`
overrides it). Cached files are re-verified on every use. Citations and licenses are written into
every layout and report. Exit codes: 3 dataset not cached, 4 checksum or size mismatch, 5 network
or write error.

### Plate and tile colors beyond the kit

```bash
lego-image-processor kit part-colors --part 6141      # 44 plate colors (White is the kit's)
lego-image-processor kit part-colors --part 98138     # 40 tile colors (9 are the kit's)
lego-image-processor kit part-colors --part 3070b     # 48 square tile colors for template margins (none in the kit)
lego-image-processor kit part-colors --format json
```

`data/part_colors.json` lists every opaque color in which the map parts are made that passes the
join rules, with LEGO, BrickLink and Rebrickable names and IDs, element IDs and citations. It is
built by a maintainer tool from checksum-pinned snapshots of Rebrickable `elements.csv`/`colors.csv`,
LDraw `LDConfig.ldr`, the archived BrickLink color guide and the archived BrickLink catalog pages
of the three parts; a row is kept only when every ID resolves and BrickLink lists the color for the
part (rules in the file's `source.join_rules`; excluded colors and reasons in `source.excluded`).
Kit colors are copied from `kit_colors.json`. Rebrickable's catalog is "free for personal and
commercial use, provided you acknowledge Rebrickable as your data source" (archived downloads page,
recorded in `source.terms`); this project acknowledges Rebrickable wherever its IDs appear. A layout that uses plate
colors outside the kit loads in `validate`, which lists them as parts beyond the kit.

### Parts lists and ordering

Each marketplace numbers the land plate differently, so every output uses the marketplace's own
number (`kit part-numbers`; values from pinned archived catalog pages in `data/part_numbers.json`):

| Part | LEGO design | BrickLink item | Rebrickable part |
|---|---|---|---|
| 1×1 round plate (land) | 6141 (element 614101 in White) | **4073** (6141 is an alternate number) | **6141** |
| 1×1 round tile (ocean) | 98138, 35381 (the kit's elements) | **98138** | **98138** |
| 1×1 square tile (template margin) | 3070 (not in the kit) | **3070** (3070b is an alternate number) | **3070b** |

Colors also differ (for example LEGO Brick Yellow = BrickLink Tan 2 = Rebrickable Tan 19); every
lot is matched to a cited row of `part_colors.json` by its color key and LEGO color ID. A lot that
cannot be matched is listed as unverified, with the reason, and gets no marketplace IDs.

```bash
lego-image-processor parts list elev.json                        # what the layout needs
lego-image-processor parts list elev.json --kits 1               # top-up beyond one 31203 kit
lego-image-processor parts list elev.json --kits 1 --owned loose.csv --missing lost.csv --spares 2
lego-image-processor parts list elev.json --kits 1 -o elev-parts.json   # JSON (no timestamps)
lego-image-processor parts export elev.json --kits 1 --condition used \
    --bricklink elev-wanted.xml --rebrickable elev-parts.csv
```

- `--kits N`: whole kits owned (the kit's map pieces from the instructions' inventory page count
  as owned; a Bright Green *plate* gets nothing from the kit's Bright Green *tiles*).
- `--owned FILE` (loose parts) and `--missing FILE` (pieces missing from secondhand kits) use
  Rebrickable's import CSV: `Part,Color,Quantity` with Rebrickable numbers, or `Element,Quantity`.
  Rows for other parts are ignored and counted, so a full Rebrickable set inventory can be passed.
  On a template layout, which has square tiles, `3070b` rows count as loose square tiles (and
  3070b's other catalog numbers, such as 3070, are an error); on a kit layout they are rows for
  other parts.
- `--spares PCT` adds `ceil(shortfall × PCT/100)` to each lot with a shortfall; off by default
  (no LEGO spare rate is assumed).
- Map pieces only: the frame, the 40 section bases and other kit parts are not listed.

`parts export` writes only verified lots with something to buy: a BrickLink wanted list (XML, no
declaration, `ITEMTYPE`/`ITEMID`/`COLOR`/`MINQTY`, `CONDITION` only with `--condition`) and a
Rebrickable `Part,Color,Quantity` CSV. With unverified lots it exits 6 and writes nothing unless
`--allow-partial`. When nothing is to buy it writes no file. Uploading to an existing BrickLink
wanted list adds to the quantities already there. The marketplace files carry no disclaimer (they
are fixed import formats); the command output and the JSON parts list carry it. Parts lists carry
no prices; `parts estimate` (below) estimates them offline, and BrickLink and Rebrickable both price
an imported list.

Example (land-elevation from the real datasets): 6,330 pieces in 10 lots beyond one kit (3,418
Bright Bluish Green tiles plus nine plate colors), 4,451 beyond two kits, 2,912 beyond three. The official design needs nothing beyond one kit.

### Price estimates

`parts estimate` prices a layout offline from a price snapshot: the packaged
`data/bricklink_price_guide.json` by default, or `--prices FILE`. It gives two estimates: **every
piece** (the parts list with no kit) and **on top of one 31203 kit** (each lot's `to_buy` with one
kit). Each lot is priced at the BrickLink price guide's 6-month average of new parts sold
(quantity-weighted, USD, VAT excluded, worldwide), with a range from the lowest to the highest sale;
a lot with no sales uses the current for-sale average (said so); a lot with neither, or not in the
snapshot, is unpriced and the estimate is marked incomplete with the unpriced piece count. Totals
are exact sums rounded half-up to cents; whole dollars are rounded once from the exact sum.

```bash
lego-image-processor parts estimate elev.json                                # table
lego-image-processor parts estimate elev.json --lines                        # every lot line
lego-image-processor parts estimate elev.json --as-of 2027-06-01 --stale-days 90
lego-image-processor parts estimate elev.json -o elev-estimate.json          # JSON (no timestamps)
lego-image-processor parts estimate elev.json --prices tests/fixtures/prices/bricklink_price_guide.json
```

Prices older than `--stale-days` (default 90) at `--as-of` (default today, UTC) print a warning;
incomplete, stale or partial estimates still exit 0. The JSON is a pure function of the layout,
the snapshot, `--as-of` and `--stale-days` (format: `specs/011-price-estimates/contracts/
estimate-format.md`). Estimate only; excludes shipping, fees and taxes; prices vary by seller and
over time. Price data: BrickLink price guide (bricklink.com). BrickLink is a trademark of LEGO
BrickLink, Inc. Not endorsed by BrickLink.

**Refreshing the snapshot (maintainer, online).** `parts prices fetch` is the only command that
calls BrickLink. It reads OAuth 1.0 credentials from `BRICKLINK_CONSUMER_KEY`,
`BRICKLINK_CONSUMER_SECRET`, `BRICKLINK_TOKEN_VALUE` and `BRICKLINK_TOKEN_SECRET` (never printed,
logged or written) and makes two price-guide requests (sold, stock) per lot, one per second. The
API base URL and parameters are cited reference data (`data/bricklink_api.json`, `checked: false`
until the owner verifies them against the live documentation).

```bash
lego-image-processor parts prices fetch -o /tmp/smoke.json --lot 98138:140      # one-lot smoke check
lego-image-processor parts prices fetch -o src/lego_image_processor/data/bricklink_price_guide.json
lego-image-processor parts prices fetch -o PATH --resume                         # after a stop
lego-image-processor parts prices fetch -o PATH --all-colors                     # all 132 cited lots
```

The default lot set is every lot the bundled recipes can use (26, with the template margin's Black
square tile); `--all-colors` takes every cited plate, tile and square tile color, `--lot PART:LEGO_COLOR_ID` (repeatable) only the named ones. Progress is
saved per lot to `<output stem>.progress.json` (git- and docker-ignored); on a stop the output is
untouched unless `--write-partial`, and `--resume` fetches only the rest. Exit codes: 1 input or
missing variable, 5 network/API failure after retries or the daily limit, 7 credentials rejected
(for example the token's IP address setting), 130 Ctrl-C. The summary lists the largest unit-price
changes since the previous snapshot; review the file, then commit it.

### Build sheets

A printable guide for placing the 10,240 pieces: an overview page (whole map, the 8 × 5 section
grid, frame boundaries, totals, provenance), legend pages (each lot's number, swatch, LEGO,
BrickLink and Rebrickable names and IDs, total) and one page per section base, 40 in all.

```bash
lego-image-processor sheets build elev.json -o elev-sheets.pdf                # PDF, Letter
lego-image-processor sheets build elev.json -o elev-sheets.pdf --paper a4     # A4
lego-image-processor sheets build elev.json -o two.pdf --sections B2,C2       # reprint two sections
lego-image-processor sheets build elev.json -o elev-svg --format svg          # page-01.svg ...
lego-image-processor sheets counts elev.json                                  # pieces per section
lego-image-processor sheets counts elev.json -o elev-counts.json              # as JSON
```

- **Sections** are labelled by column letter A–H (west to east) and row number 1–5 (north to
  south), so `C2` is columns 32–47, rows 16–31. Pages run column by column (A1 … A5, B1 … H5),
  the order of the kit's section instructions. Frames: columns A–B, C–F, G–H. North is up.
- **Studs** are drawn at true scale (8.0 mm pitch, from LDraw's approximation 1 stud = 20 LDU =
  8 mm), each in its lot's cited color with the lot number on it (black or white, whichever
  contrasts more), so the sheet also works in black and white. Land plates have a ring; ocean
  tiles are plain. Lot numbers follow the parts list's lot order and are the same on every page.
- **Print at 100% (no fit-to-page).** Every page has a 100 mm scale bar: measure it. A 16 × 16
  base laid on a printed section should match the grid.
- Each section page lists the section's pieces per lot (they sum to 256); `sheets counts` gives the
  same numbers for sorting pieces into 40 bags.
- Unverified lots (colors without cited IDs) are marked "no cited IDs" and the overview warns.
- PDF text is Latin-1 (standard Helvetica, not embedded): a `--title` with other characters fails
  for PDF and works for SVG. Output is deterministic: the same layout and options give identical
  bytes.
- The pages are drawn from the layout data with circles, lines and text only; no LEGO artwork,
  logo, instruction image or crop is used. Every page carries "Not affiliated with or endorsed
  by The LEGO Group."

### Map arrangements

The kit's board is three frames: 1 America (columns 0–31, sections A–B), 2 Europe & Africa
(32–95, C–F) and 3 Asia & Australia (96–127, G–H). The instructions show "1 world – 3
combinations" (LEGO 31203 building instructions, pp. 7–8), and the kit's connector pins join the
frames in any order:

| Arrangement | Frames, left to right | Centre | Column shift |
|---|---|---|---|
| `A` / `europe-africa` (default) | 1 · 2 · 3 | Europe and Africa | 0 |
| `B` / `americas` | 3 · 1 · 2 | America | +32 |
| `C` / `asia-australia` | 2 · 3 · 1 | Asia and Australia | −32 |
| `D` / `pacific` (not in the instructions) | 2b · 3 · 1 · 2a (strips E F G H A B C D) | the Pacific (date line) | +64 |
| `E` / `asia-pacific` (not in the instructions) | 2b · 3 · 1 · 2a (strips D E F G H A B C) | Asia-Pacific (146° E) | +80 |

D and E (feature 010) are not among the building instructions' combinations. The board is 8
strips of five section bases (the kit's section columns A–H); a joint between strips inside a
frame uses the same 15 connector pegs as a joint between frames (pp. 134–139) and the white border
is built round the finished board (p. 140), so any rotation of the strips by whole strips is
buildable from one kit (201 of the 205 connector pegs). D unpegs frame 2 between strips D and E,
E between C and D; the build sheets' assembly page and `docs/runbook.md` give the steps.

```bash
lego-image-processor map build land-elevation --arrangement B -o elev-B.json --preview elev-B.png
lego-image-processor map check ocean-sst --arrangement asia-australia
lego-image-processor layout arrange official.json --arrangement C -o official-C.json   # re-hang, no rebuild
lego-image-processor validate official-C.json        # checks the mask under arrangement C
lego-image-processor sheets build elev-B.json -o elev-B.pdf
```

- The grid spans exactly 360° of longitude, so every arrangement is a cyclic shift of whole
  strips and its seams are geographically continuous.
- A layout's x is the column as hung; `metadata.arrangement` records the arrangement (schema stays
  2.0; a layout without it is A). `layout arrange` only moves positions, so arranging back to A
  restores the original positions exactly.
- `map build` computes data values and classes as in A and moves them; the land shadow, the
  coastal halo and `mix` shading are computed on the board as hung, with no wrap at the outer
  edges, so the shadow is right at the new seam. The `official-31203` recipe in B or C is the
  official design moved frame by frame.
- Build sheets label sections A1–H5 as hung, draw the frame boundaries where they fall, name the
  frames and the combination; each section page names its physical frame and its kit section
  (the label in the instructions). The last page shows how to hang the frames (for D and E: the
  frame-2 joint to unpeg and the joints to make). Parts lists are the same in every arrangement.

### Map templates

A template fixes the canvas: a projection, a board of whole 16 × 16 modules, a layout that makes
each stud land, ocean or margin (off the globe), one part per class and a frame. Two ship:

| Template | Projection | Studs: land / ocean / margin | Arrangements | Status |
|---|---|---|---|---|
| `kit-31203` (default) | the kit grid (equirectangular, above) | 3,062 / 7,178 / 0 | A, B, C | reference |
| `winkel-tripel` | Winkel tripel, standard parallel 50.4598°, central meridian 11.1° E, fitted inside the kit's 8 × 5 modules | 2,553 / 5,691 / 1,996 (outline ring 288) | A | confirmed (project owner, 2026-11-24) |

The kit template never changes: maps built on it are byte for byte what they were before
templates existed. Maps are built only on the kit and on templates the project owner has
confirmed. The project owner confirmed `winkel-tripel` as generated, with no corrections, on
2026-11-24; a build on a template that is not confirmed stops with "not confirmed by the project
owner" (exit 1).

```bash
lego-image-processor template list                              # id, title, status, counts, arrangements
lego-image-processor template show winkel-tripel                # projection, board, parts, counts, source, confirmation
lego-image-processor template locate winkel-tripel 48.86 2.35   # the stud that holds a location (row 18, column 61, D2)
lego-image-processor template locate winkel-tripel --stud 0 0   # a stud's location and class (margin)
lego-image-processor map build ocean-sst --template winkel-tripel -o w.json --preview w.png
lego-image-processor map build ocean-sst --template winkel-tripel --ring-color lego_white -o w.json
lego-image-processor map check land-elevation --template winkel-tripel
lego-image-processor map cells rainfall --template winkel-tripel -o cells.json
```

Recipe keys (optional; `--template`, `--margin-color` and `--ring-color` win over them):

```toml
template = "winkel-tripel"        # absent = kit-31203

[margin]                          # used only on non-kit templates
color = "lego_black"              # a square tile (3070b) color; default lego_black
ring = "lego_bright_yellow"       # optional: the outline ring, margin studs touching the globe
```

- Data are sampled at each stud's location on the globe; margin studs take no data. The land
  shadow, halo, mix, `no_data` and `override` rules work on the template's studs.
- Margin studs are 1×1 square tiles, part 3070b (`part_type: "square_tile"`; BrickLink item 3070,
  Rebrickable 3070b), in the margin color, and the ring color on the ring if one is set. The ring
  must differ from the margin color; `--ring-color none` turns a recipe's ring off. A 31203 kit
  supplies no square tiles, so every one is bought beyond the kit.
- The build prints a `Template:` and a `Margin:` line. The layout's `metadata.template` records the
  template (id, projection, board, parts, counts, the template file's SHA-256 and confirmation)
  and the dataset that decided its land and ocean (ETOPO 2022), which the report, the build sheets
  and `cells.json` (cells `M` for the margin) cite as well.
- Previews draw land and ocean as round studs and the margin as squares; margin studs in LEGO
  Black are drawn in the preview's background color (pure black by default), so a Black margin
  blends into it, while other margin colors and the ring keep their cited colors. Build sheets draw
  the margin as 7 mm squares. Parts lists, exports, estimates and `sheets counts` include the square
  tiles; leftovers list kit elements only. `validate` checks the layout against the template's
  land/ocean layout and reports the square tiles as unavailable in the kit (`ocean-sst` on Winkel:
  80.5% buildable from the kit).
- The frames of a curved map cannot be re-hung: on `winkel-tripel` an arrangement other than A
  (from `--arrangement` or the recipe, as for the ENSO maps) is an error, and so is `layout
  arrange` on its layouts. `official-31203` copies LEGO's design cell for cell from the kit grid,
  so it cannot be built on another template; build `official-31203-bathymetry` for the official
  look from data. `--compare-official` works on the kit only.

Example (`ocean-sst` on a confirmed copy of `winkel-tripel`, real data): 10,240 pieces in 11 lots,
2,553 White plates, 5,691 tiles and 1,996 Black square tiles. One kit covers everything but the
square tiles and leaves 2,886 of its map pieces over.

**Making a template (maintainer).** `tools/maptemplates` (not packaged) builds each template from
the pinned ETOPO 2022 file (land where the elevation is above 0 m) and the published projection.
`generate`, `write` and `build` need pyproj `>=3.7,<3.8` (`poetry install --with maintainer`; the
package itself never imports it). From `cli/`:

```bash
PYTHONPATH=tools poetry run python -m maptemplates generate winkel-tripel      # candidate, review sheet, flags in <cache>/templates/
PYTHONPATH=tools poetry run python -m maptemplates review winkel-tripel        # review sheet of the committed file (no pyproj)
PYTHONPATH=tools poetry run python -m maptemplates write winkel-tripel --corrections FILE --confirmed-on YYYY-MM-DD
PYTHONPATH=tools poetry run python -m maptemplates build winkel-tripel --check # "no differences": the committed file is reproducible
PYTHONPATH=tools poetry run python -m maptemplates ice-mask winkel-tripel --check   # ice studs (ERSST v5) for map cells
PYTHONPATH=tools poetry run python -m maptemplates kit-golden --out kit.json   # digests of every kit output, A, B and C
```

The review sheet shows every stud's class, the ring, the modules and sections, and flags studs
with a land share of 40-60% and water not connected to the ocean. The project owner reviews it.
Hand corrections (a JSON list of `{row, col, class, reason}`) are recorded in the template file,
and `write --confirmed-on` records the confirmation as the role "project owner" and the date,
with no name. A rewrite keeps the confirmation only while the layout stays the same. Files:
`data/templates/<id>.json` and its ice studs `<id>-ice.json`, whose `template_layout_sha256`
must equal the template's layout digest. Formats: `specs/016-map-templates/contracts/`.

### Python library

```python
from lego_image_processor.kit import load_kit_inventory, load_kit_colors, load_official_design

inventory = load_kit_inventory()          # 32 elements; inventory.land_element(), .ocean_elements()
colors = load_kit_colors()                # 10 KitColor records with LEGO/BrickLink/Rebrickable IDs
design = load_official_design()           # 128x80 grid of kit color keys; design.to_layout()

from lego_image_processor.maps import load_recipe, build_map, write_preview
from lego_image_processor.datasets import get_entry, fetch

result = build_map(load_recipe("official-31203"))   # never downloads
result.layout.to_json(); result.report; result.agreement
fetch(get_entry("ersst-v5-ltm-1991-2020"))           # the only function that uses the network

from lego_image_processor.parts import (OwnedInputs, build_parts_list, read_layout,
                                        resolve_color, to_bricklink_xml, to_rebrickable_csv)

pl = build_parts_list(read_layout("elev.json"), owned=OwnedInputs(kits=1))
pl.totals(); pl.to_json(); to_bricklink_xml(pl, condition="U"); to_rebrickable_csv(pl)
resolve_color("6141", "lego_brick_yellow", "5")      # cited IDs, or Unresolved(reason)

from lego_image_processor.sheets import build_sheet_set, render_pdf, render_svg, section_counts

sheet_set = build_sheet_set(read_layout("elev.json"), paper="letter", sections="B2,C2")
pdf_bytes = render_pdf(sheet_set); svg_pages = render_svg(sheet_set)   # [(name, text), ...]
section_counts(read_layout("elev.json")).to_json()

from lego_image_processor.templates import load_template, list_templates, confirmed_templates

t = load_template("winkel-tripel")    # t.status, t.counts, t.class_at(row, col)
t.stud_at(48.86, 2.35)                 # (18, 61): the stud that holds a location, or None
t.location(0, 0)                       # None: a margin stud is off the globe
build_map(load_recipe("ocean-sst"), template="winkel-tripel")   # confirmed templates only
```

Maintainer tools (from `cli/`, need the pinned sources in the cache; `--check` must report
"no differences"): `PYTHONPATH=tools python -m partnumbers build --check`,
`PYTHONPATH=tools python -m partcolors build --check` and
`PYTHONPATH=tools python -m maptemplates build winkel-tripel --check`.

## Development

```bash
# Run tests (offline: network sockets are blocked for the whole suite)
poetry run pytest

# Run with coverage
poetry run pytest --cov=src/lego_image_processor
```

---

Not affiliated with or endorsed by The LEGO Group.

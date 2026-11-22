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

## Installation

```bash
cd cli
poetry install
# without Poetry: uv venv && uv pip install -e . pytest pytest-cov pytest-benchmark
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

A map is a land layer plus an ocean layer on the fixed kit 31203 template (128×80 grid, the kit's
land/sea mask). Each layer is **data** (a gridded field classified onto an ordered color scale) or
**background** (fixed colors, mixed by weight). Four recipes are bundled:

| Recipe | Land | Ocean | Data needed |
|---|---|---|---|
| `official-31203` | White | the official design grid, one-to-one (exact: 10,240/10,240) | none (packaged) |
| `official-31203-bathymetry` | White | depth ranked into the official counts and color order, blended | ETOPO 2022 |
| `ocean-sst` | White | annual mean SST 1991-2020, cold to warm, counts within one kit's supply | ERSST v5 |
| `land-elevation` | elevation on 10 plate colors (green to brown to grey to white) | three kit blues (Bright Bluish Green, Medium Azur, Earth Blue at 70/20/10), mixed; needs more blue tiles than one kit holds (reported as beyond-kit) | ETOPO 2022 |

```bash
lego-image-processor map recipes                                   # list (and whether data is cached)
lego-image-processor map build official-31203 -o official.json --preview official.png
lego-image-processor map build ocean-sst -o sst.json --fetch       # --fetch downloads missing pinned data
lego-image-processor map build land-elevation -o elev.json --report elev-report.json
lego-image-processor map check land-elevation                      # suitability report only
lego-image-processor map recipes --copy ocean-sst my-map.toml      # start a new recipe
lego-image-processor validate sst.json
```

Builds never use the network unless you pass `--fetch`. Without it, a recipe whose dataset is not
cached fails (exit 3) with `dataset fetch <id>` and the `--fetch` option, and writes nothing.
Every build prints a suitability report: share of the data's variance lost below grid scale,
cells filled from neighbours, cells per class, the closest neighbouring colors (CIEDE2000) and
color counts against one kit's supply, with warnings above 50% variance lost, 5% filled, an empty
class or ΔE00 below 5. `--preview` writes a PNG (8×8 pixels per stud, cited RGB; not a build
sheet). The texture rule of a recipe (`blend` for data layers, `mix` for backgrounds) replaces the
"shadowing" idea of feature 002; there is no separate shadowing option.

A recipe is a TOML file (format "1"). A minimal data layer:

```toml
# Not affiliated with or endorsed by The LEGO Group.
format = "1"
id = "my-map"
title = "My map"

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
kit mask (94.2% agreement; Miller 90.9%, Mercator 87.0%). The kit mask always decides land and
ocean.

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
| `kit31203-design`: the official design grid | packaged | facts from the official instructions | see `kit_31203_design.json` |

Each download is pinned by URL, exact size and SHA-256, downloaded to a temporary file, verified
and then moved into the per-user cache (`$LEGO_IMAGE_PROCESSOR_CACHE`, else
`$XDG_CACHE_HOME/lego-image-processor`, else `~/.cache/lego-image-processor`; `--cache-dir`
overrides it). Cached files are re-verified on every use. Citations and licenses are written into
every layout and report. Exit codes: 3 dataset not cached, 4 checksum or size mismatch, 5 network
or write error.

### Plate and tile colors beyond the kit

```bash
lego-image-processor kit part-colors --part 6141      # 44 plate colors (White is the kit's)
lego-image-processor kit part-colors --part 98138     # 40 tile colors (9 are the kit's)
lego-image-processor kit part-colors --format json
```

`data/part_colors.json` lists every opaque color in which the map parts are made that passes the
join rules, with LEGO, BrickLink and Rebrickable names and IDs, element IDs and citations. It is
built by a maintainer tool from checksum-pinned snapshots of Rebrickable `elements.csv`/`colors.csv`,
LDraw `LDConfig.ldr`, the archived BrickLink color guide and the archived BrickLink catalog pages
of the two parts; a row is kept only when every ID resolves and BrickLink lists the color for the
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
- `--spares PCT` adds `ceil(shortfall × PCT/100)` to each lot with a shortfall; off by default
  (no LEGO spare rate is assumed).
- Map pieces only: the frame, the 40 section bases and other kit parts are not listed.

`parts export` writes only verified lots with something to buy: a BrickLink wanted list (XML, no
declaration, `ITEMTYPE`/`ITEMID`/`COLOR`/`MINQTY`, `CONDITION` only with `--condition`) and a
Rebrickable `Part,Color,Quantity` CSV. With unverified lots it exits 6 and writes nothing unless
`--allow-partial`. When nothing is to buy it writes no file. Uploading to an existing BrickLink
wanted list adds to the quantities already there. The marketplace files carry no disclaimer (they
are fixed import formats); the command output and the JSON parts list carry it. No prices are
estimated: BrickLink and Rebrickable both price an imported list.

Example (land-elevation from the real datasets): 6,382 pieces in 11 lots beyond one kit (3,145
Bright Bluish Green and 325 Earth Blue tiles plus nine plate colors), 4,178 beyond two kits,
2,912 beyond three. The official design needs nothing beyond one kit.

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
```

Maintainer tools (from `cli/`, need the pinned sources in the cache; `--check` must report
"no differences"): `PYTHONPATH=tools python -m partnumbers build --check` and
`PYTHONPATH=tools python -m partcolors build --check`.

## Development

```bash
# Run tests (offline: network sockets are blocked for the whole suite)
poetry run pytest

# Run with coverage
poetry run pytest --cov=src/lego_image_processor
```

---

Not affiliated with or endorsed by The LEGO Group.

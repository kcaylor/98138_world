<!-- speckit-harness:start (managed by speckit-harness 1.1.0; edits inside this block are overwritten) -->
## Spec-driven development (Spec Kit harness)

This repository uses GitHub Spec Kit with the speckit-harness workflow. These instructions apply to
every coding agent, whatever tool or model runs it.

**Before any spec, planning, or feature work**, run this from the repository root, replacing
`<agent>` with your Spec Kit integration key (`claude`, `codex`, `gemini`, `cursor-agent`,
`opencode`, and so on; `speckit-harness agents` lists them):

    speckit-harness ensure --agent <agent>

It checks for harness updates, installs or refreshes the workflow for your agent, and prints any
action you need to take. If the command is not found, install the harness on this machine with:

    git clone https://github.com/ecohydro/speckit-harness.git ~/.local/share/speckit-harness && bash ~/.local/share/speckit-harness/bootstrap.sh

**To build a feature**, use the `speckit-run` skill. If your agent does not load skills, read
`.specify/harness/skills/speckit-run/SKILL.md` and follow it. Its input is an existing
specification (`specs/<NNN-name>/spec.md` or a design document). With no specification, it drafts
one after asking the user up to four questions.

Paired Claude/Codex runs: `speckit-pair` (opt-in).

**For the constitution**, use `speckit-derive-constitution`
(`.specify/harness/skills/speckit-derive-constitution/SKILL.md`). Do not edit
`.specify/memory/constitution.md` by hand.

- Spec Kit phase instructions for any agent: `.specify/harness/commands/speckit.<phase>.md`
- Decisions reserved for the user: `.specify/memory/run-policy.md`
- Progress for a feature in flight: `specs/<NNN-name>/run-state.md` (read it before resuming)
<!-- speckit-harness:end -->

## Project: 98138.world

98138.world uses the LEGO World Map kit (31203) as its reference template (a 128×80 grid of 10,240
positions and the kit's land/sea mask) and builds a general way to turn any suitable gridded map
into a buildable mosaic. Since constitution 3.0.0 other templates (a projection on a rectangular
board of 16×16 modules, with margin studs off the globe) are allowed once the owner confirms their
layout; the kit template never changes. The first, Winkel tripel on the kit's board, was
confirmed by the project owner on 2026-11-24 (feature 016, below). A map is a land layer plus an ocean layer, each either
data-driven or a shaded background, described by a recipe file. Read `docs/vision.md` before
planning a feature; the rules are in `.specify/memory/constitution.md`.

The kit reference data in `cli/src/lego_image_processor/data/` is cited (feature 003, see
`specs/003-kit-reference-data/` and each data file's `source` block). Land is the white 1×1 round
plate, part 6141 (element 614101); ocean is the 1×1 round tile, part 98138, in 9 colors. The parts
inventory (`kit_31203_inventory.json`, page 159) and the official design
(`kit_31203_design.json`, 40 section pages) are extracted from the official building instructions
PDF pinned by URL and SHA-256; the 10 colors' LEGO, BrickLink and Rebrickable names and IDs
(`kit_colors.json`) come from the cited catalogs. Never commit the PDF or crops of it. To
regenerate or check the data, from `cli/`: `poetry install --with maintainer`, then
`PYTHONPATH=tools poetry run python -m kit31203 extract --check` (add `--pdf <local copy>` to skip
the download; exit 0 and "no differences" means the committed data is reproducible).

Maps are built from recipes (feature 004, see `specs/004-map-recipes/`): TOML files in
`cli/src/lego_image_processor/maps/recipes/` (`official-31203`, `official-31203-bathymetry`,
`ocean-sst`, `land-elevation`, `ocean-el-nino`, `ocean-la-nina`, `living-planet`, `rainfall`), built with `map build <recipe> -o layout.json`. Datasets are
pinned in `data/datasets.json` (URL, size, SHA-256, citation, license) and cached per user; only
`dataset fetch` and `map build --fetch` use the network. The kit projection
(`kit_31203_projection.json`) and the plate/tile colors beyond the kit (`part_colors.json`, from
checksum-pinned Rebrickable, LDraw and BrickLink snapshots) are regenerated with
`PYTHONPATH=tools python -m kit31203 fit-projection --check` and
`PYTHONPATH=tools python -m partcolors build --check`. Tests use small derived fixtures in
`cli/tests/fixtures/datasets/` (each with a `.source.json`); never commit downloaded datasets.

The kit's three frames can be hung three ways (feature 007, see `specs/007-map-arrangements/`;
LEGO 31203 building instructions, pp. 7–8; `data/kit_31203_arrangements.json`): A 1·2·3 (default),
B 3·1·2 (America centre), C 2·3·1 (Asia and Australia centre), each a cyclic shift of whole frames.
Feature 010 (`specs/010-pacific-arrangements/`) adds D `pacific` (date line centre) and E
`asia-pacific` (146° E), both 2b·3·1·2a with frame 2 split between two strips: not among the
instructions' combinations, possible because strip and frame joints both take 15 connector pegs
(pp. 134–139) and the border goes round the finished board (p. 140). The data file (format 2)
lists each combination's strip order and groups; every build-sheet set ends with an assembly page;
the ENSO recipes default to D.
Layout positions use columns as hung and record `metadata.arrangement` (absent = A). `map build
--arrangement` computes per-cell values in kit (A) columns and the shadow, halo and mix on the board
as hung; `layout arrange` re-hangs any layout without recomputing.

The web site (feature 008, see `specs/008-web-app/` and `docs/deploy.md`) shows the eight bundled
maps in combinations A–E (D and E from feature 010) and offers every build file. `web/` (package `web98138`, FastAPI +
Jinja2, no cookies; works without JS, one first-party script since 015) has two halves: `python -m web98138.prebuild --out DIR [--fetch]` builds
all 40 kit variants (8 maps × 5 combinations) (and, since 016, 5 Winkel tripel versions) with the CLI library (`build_map`, `write_preview`, `build_parts_list`, exports,
`build_sheet_set`/`render_pdf`) plus `manifest.json` (sizes, SHA-256, tool and dataset versions,
page data); the service (`web98138.app`, `WEB98138_SITE_DIR=DIR uvicorn web98138.app:app`) only
serves that output and never imports `lego_image_processor`. The `Dockerfile` (two stages) runs the
prebuild at image build time; `fly.toml` deploys app `world-98138`.

ENSO maps (feature 009, see `specs/009-enso-sst-maps/`): recipes `ocean-el-nino` (ERSST v5 `ssta`,
Dec 1997) and `ocean-la-nina` (Dec 1988) share one °C `bins` legend on the kit's nine ocean colors
and set the optional recipe key `arrangement = "B"` (an explicit `--arrangement` wins; the report
records `arrangement_source`). The netCDF-3 reader drops size-1 leading axes and rejects netCDF-4
(read those with `format = "netcdf4"`, feature 013).

Living planet (feature 012, see `specs/012-living-planet/`): recipe `living-planet`, MOD17A3 NPP
2000–2015 (NTSG GeoTIFF, 385 MB, pinned by SHA-256 over HTTP: `http_only`) on six plate colors and
MODIS-Aqua chlorophyll-a 2013–2024 (one ERDDAP request, 147 MB) on five tile colors, White ice on
both, Black shadow. General additions: `datasets/geotiff.py` (strip reader, `grid.block` means, no
full decode), netCDF-3 `latitude`/`longitude`, `reduce = "climatology-mean"` (mean of valid steps +
`counts`), `content_sha256` (checksum of the decoded data, for files a server builds on request),
`class_rule.land_from` (land/ocean split from another dataset), recipe `transform = "log10"` (bins
bounds in data units) and `[<layer>.no_data]` (`value`, `color`, `rule` unobserved | share;
`maps/nodata.py`). Contract: `specs/012-living-planet/contracts/recipe-and-datasets.md`.

Rainfall (feature 013, see `specs/013-rainfall/`): recipe `rainfall`, GPCP v2.3 LTM 1991–2020
(NOAA PSL netCDF-4, annual mean, bilinear at cell centres) on six plate and five tile colors, White
ice sheets (region overrides: Antarctica, Greenland) and sea ice (NSIDC CDR v6, September/February
1991–2020, 60 files, 17.8 MB; mean ≥ 0.7 or no pixel poleward of 60°), Black shadow; 99.2% of cells
match the approved prototype 3A. General additions: `datasets/netcdf4.py` (h5py 3.16, a CLI
dependency and in `web/requirements-build.txt` only; CF decoding, polar-stereographic x/y →
lat/lon, points grids), registry `files` (multi-file entries, cached in the version directory),
recipe `sampling = "bilinear"`, `[[<layer>.override]]` (region or dataset rule; `maps/overrides.py`)
and `[<layer>.legend]` (second unit). Contract: `specs/013-rainfall/contracts/recipe-and-datasets.md`.

Palette chooser (feature 015, see `specs/015-palette-chooser/`): `map cells <recipe> -o
cells.json [--arrangement]` (library `maps/cells.py`, `map_cells(result)`) exports per cell, as
hung, each layer's built class and data value, default bounds (recipe `bins`, or boundaries between
built rank classes), the shadow, the ice regions and both parts' cited colors with CIE L*. Ice
regions are packaged in `data/kit_31203_ice.json` (`maps/ice.py`; land ice: Antarctica south of
60° S and a Greenland box without Iceland; sea ice: ERSST v5 1991–2020 warmest month ≤ −1.5 °C or
no value poleward of 60°), regenerated with `PYTHONPATH=tools python -m kit31203 ice-mask --check`.
The prebuild writes `cells.json` per variant (manifest kind `cells`, served at
`/maps/<id>/<C>/cells.json`, not a download); map pages load the hand-written first-party
`web/src/web98138/static/palette.js` (CSP `script-src 'self'; connect-src 'self'`) to recolor a
canvas, edit classes and bounds, show ice as White, and keep the state in the URL fragment. Preview
only: parts lists, prices, sheets and downloads never change. Pages still work without JS (008
FR-009 as amended by 015 FR-020). Web tests run the script's pure functions under Node when it
is installed.

Leftovers and page background (feature 014, see `specs/014-leftovers-and-background/`): every
parts list carries `leftovers`, one row per kit map element (White plate and the nine ocean tiles,
supplies read from `kit_31203_inventory.json`): `kit_supply` (kits × quantity − missing; loose
parts are not in the box), `used`, `leftover` = max(0, supply − used), plus `totals.leftover`.
`parts list --kits N` (N ≥ 1) prints a "Left over in the box" table; marketplace exports are
unchanged. The web prebuild writes `variants[].leftovers` and `summary.left_over_with_kit` (one
kit) and the map page shows them. Site background `--bg: #e9e9e9`; every stud preview sits on a
`--stud-mat` of the same gray, so White studs show.

Map templates (feature 016, see `specs/016-map-templates/`): a template is a projection, a board of
whole 16×16 modules, a layout of land (L), ocean (O) and margin (M, off the globe) studs, one part
per class and a frame. Code: `templates/` (`load_template`, `list_templates`, `confirmed_templates`,
`compatibility`). The kit, `kit-31203`, is defined in code and is the default; its outputs stay
byte-for-byte the same, checked by the kit golden (`cli/tests/fixtures/golden/kit_outputs.json`,
`web/tests/fixtures/kit_variants_golden.json`; rewrite them only from an unmodified `main`). Other
templates are package data, `data/templates/<id>.json` (projection, fit, classes, stud locations,
source dataset, corrections, confirmation) with `<id>-ice.json` (ice studs for `map cells`).
`winkel-tripel`: Winkel tripel (φ1 50.4598°, λ0 11.1° E) fitted in the kit's 8 × 5 modules, land
and ocean from ETOPO 2022: 2,553 land, 5,691 ocean, 1,996 margin studs (outline ring 288),
arrangement A only. The project owner confirmed it as generated, with no corrections, on
2026-11-24; the confirmation is recorded as the role "project owner" and the date, never a name.
Commands: `template list|show|locate`; `map build|check|cells --template ID --margin-color KEY
--ring-color KEY|none`; recipe keys `template` and `[margin]` (`color`, default `lego_black`;
optional `ring`). Margin studs are the 1×1 square tile 3070b (`part_type` `square_tile`; BrickLink
item 3070, Rebrickable 3070b; 48 cited colors in `part_colors.json`), drawn square in previews (Black
margin studs take the preview's pure-black background, in `preview.png` and the palette chooser) and
sheets and counted in parts lists, exports and estimates (one kit supplies none; leftovers list kit
elements only). Layouts record `metadata.template` (absent = kit). `layout arrange`, arrangements B
and C, and `official-31203` (the kit design) are errors on a non-kit template. Maintainer tool,
from `cli/` (pyproj `>=3.7,<3.8`, maintainer group only): `PYTHONPATH=tools python -m
maptemplates` with `generate ID` (candidate, review sheet and flags in `<cache>/templates/`),
`review ID`, `write ID [--corrections FILE] [--confirmed-on DATE]`, `build ID --check`, `ice-mask
ID [--check]`, `kit-golden [--fixtures] --out FILE`. Tests build on `confirmed_winkel` (the package file), test
the refusal on `unconfirmed_winkel` (a copy without the confirmation) and use the synthetic fixture
`cli/tests/fixtures/templates/`. The web prebuild's
`--templates LIST|none` (default: every confirmed template) adds a Winkel version of five maps
(`official-31203-bathymetry`, `ocean-sst`, `land-elevation`, `living-planet`, `rainfall`) at
`/maps/<map>/winkel-tripel` (manifest `templates`, `maps[].template_variants`); kit variants are
unchanged. Contracts: `specs/016-map-templates/contracts/`.

Map stickers (feature 017, see `specs/017-map-stickers/`): `map stickers <recipe> -o OUT
[--format pdf|svg|json] [--paper letter|a4] [--template ID]` makes two white-on-black stickers from
the built map (never downloads; no `--arrangement`, one set serves A–E, its legend values from the
recipe's own combination, D for the ENSO maps): a small one for a
Black 6×6 tile with the title, a line and the disclaimer, and a large one for a Black 8×16 tile that
adds "98138.world", the color legend and the data credit; as the print sheet (one page at true
size: bleed, cut marks, plaque parts, citations, provenance), `sticker-small.svg` and
`sticker-large.svg` (disclaimer in `<desc>`, citations in `<metadata>`) or a JSON summary. Code:
`stickers/` (`sticker_set`, `render_sticker_pdf`, `render_sticker_svgs`). Texts come from the
optional recipe table `[sticker]` (`title`, `line`, `credit`, `no_data`; without it, the recipe's
title and description); the eight bundled recipes end with one (texts approved by the project
owner on 2026-11-24; no sticker title says "Official"). Plaque parts, all Black, are cited in
`data/plaque_parts.json` (`kit/plaque_parts.py`, `load_plaque_parts`): small tile 10202 and plate
3958; the large plaque is the smooth tile 4974 (not the textured 90498) on plate 92438. Regenerate
or check with `PYTHONPATH=tools python -m partcolors plaque-parts --check`. On a template the line
ends with its projection ("Winkel tripel projection.") and the credit adds the template's dataset.
In-margin plaque: `map build|check|cells --plaque CORNER|none` or `[margin].plaque` puts the 10202
tile in a Winkel margin corner, one stud in from both board edges (rows 1–6 or 73–78, columns 1–6 or
121–126; confirmed by the project owner on 2026-11-25); `--plaque` on the kit is an error. The
layout records `metadata.plaque` and lacks its 36 studs (10,204 positions, 1,960 square tiles);
parts lists and exports add one `plaque_tile` lot 10202 (estimate lot `10202:26`), sheets draw one
outlined rectangle in its section, `map cells` marks its studs `P`, and `validate` accepts them and
reports the tile as not in the kit. The web prebuild writes each map's kit set to
`maps/<map>/stickers/kit-31203/` and one per template variant to `maps/<map>/stickers/<template-id>/`
(manifest `maps[].stickers.<template-id>`: `files`, `title`, `line`, `alt`, `legend`, `credit`,
`plaques`, `notes`), served at `/maps/<map>/stickers/<template>/sticker-small.svg|sticker-large.svg`
and `.../download/<kind>`; every kit map page (A–E) shows the same "Stickers for a plaque" panel;
no site variant has a plaque. Kit outputs differ only in the recipe checksum, held by
`cli/tests/integration/test_stickers_outputs_unchanged.py` (G1 pins main 6f300dc's recipe
checksums; golden `cli/tests/fixtures/golden/stickers_017_guard.json`, A–E, written from an
unmodified export of main 6f300dc, re-based once from 6038d9c with the project owner's approval of
2026-11-25, never from 017 code); the kit goldens (`kit_outputs.json`, `kit_variants_golden.json`)
were regenerated on each merge of main into 017 (T054's proof, in their tests' docstrings).
Contracts: `specs/017-map-stickers/contracts/`.

1. **Python CLI** (`cli/`, package `lego_image_processor`), written to be released as open source.
2. **Web application** (`web/`) on Fly.io at 98138.world. It calls the CLI library at build time and
   never duplicates its logic; the runtime image has no CLI dependencies.

### Layout

- `cli/src/lego_image_processor/`: `core/` (image I/O, quantization), `palette/` (LEGO colors,
  CIEDE2000 matching), `analysis/`, `layout/` (grid, land/sea mask, kit spec, validator, frame arrangements; feature 007), `kit/`
  (kit reference data, part colors, plaque parts `plaque_parts.py`; feature 017), `datasets/` (registry, verified cache, readers), `maps/`
  (recipes, projection, reprojection, classification, texture, suitability, build, preview, ice regions and chooser cells; feature 015),
  `parts/` (parts lists, cited IDs, marketplace exports; feature 005), `sheets/` (build sheets:
  sections, page model, PDF and SVG backends, per-section counts; feature 006), `templates/` (map templates: the kit
  grid, Winkel tripel, boards, stud locations; feature 016), `stickers/` (map stickers: texts, legend,
  credits, print sheet, SVG and JSON; feature 017), `cli/` (Click commands), `data/` (runtime reference data, shipped with the package).
- `cli/tools/`: maintainer-only tools (`kit31203` incl. `ice-mask`, `partcolors`, `fixtures004`, `fixtures011`, `maptemplates`, `projection_study`), not packaged.
- `cli/tests/`: `unit/`, `integration/`, `contract/` (CLI I/O), `fixtures/`.
- `web/`: `src/web98138/` (`prebuild.py`, `catalog.py`, `app.py`, `templates/`, `static/`, incl. `palette.js`),
  `scripts/prebuild.py`, `tests/` (offline; a session fixture prebuilds `official-31203` and
  `ocean-sst` from the CLI's dataset fixtures), pinned `requirements.txt` (runtime) and
  `requirements-build.txt` (CLI deps for the image build). `web/site-output/` is git-ignored.
- `Dockerfile`, `.dockerignore`, `fly.toml` at the root (the build context needs `cli/` and `web/`).
- `specs/NNN-name/`: Spec Kit artifacts for each feature.

### Working rules

- CLI first: every capability works as a CLI command on local files before any web feature uses it.
- Test first for core logic (unit, integration, contract tests under `cli/tests/`).
- Reference data the code reads at run time belongs in `cli/src/lego_image_processor/data/`, not in
  `tests/fixtures/`.
- Anything user-facing must say: "Not affiliated with or endorsed by The LEGO Group." Never imply
  endorsement or partnership.
- Run tests: `cd cli && poetry run pytest` (without Poetry: `uv venv --python 3.11 && uv pip install -e . pytest pytest-cov pytest-benchmark`, then `.venv/bin/pytest`).
- Web tests: `cd web && uv venv --python 3.11 && uv pip install -e ../cli -e . pytest httpx2 pypdf`, then
  `.venv/bin/pytest`. Never run `fly` commands that change the deployed app without the owner.

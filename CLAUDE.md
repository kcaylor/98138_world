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

98138.world uses the LEGO World Map kit (31203) as a fixed template (a 128×80 grid of 10,240
positions and the kit's land/sea mask) and builds a general way to turn any suitable gridded map
into a buildable mosaic. A map is a land layer plus an ocean layer, each either data-driven or a
shaded background, described by a recipe file. Read `docs/vision.md` before planning a feature; the
rules are in `.specify/memory/constitution.md`.

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
`ocean-sst`, `land-elevation`, `ocean-el-nino`, `ocean-la-nina`, `living-planet`), built with `map build <recipe> -o layout.json`. Datasets are
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
Layout positions use columns as hung and record `metadata.arrangement` (absent = A). `map build
--arrangement` computes per-cell values in kit (A) columns and the shadow, halo and mix on the board
as hung; `layout arrange` re-hangs any layout without recomputing.

The web site (feature 008, see `specs/008-web-app/` and `docs/deploy.md`) shows the seven bundled
maps in combinations A, B and C and offers every build file. `web/` (package `web98138`, FastAPI +
Jinja2, no JS, no cookies) has two halves: `python -m web98138.prebuild --out DIR [--fetch]` builds
all 21 variants with the CLI library (`build_map`, `write_preview`, `build_parts_list`, exports,
`build_sheet_set`/`render_pdf`) plus `manifest.json` (sizes, SHA-256, tool and dataset versions,
page data); the service (`web98138.app`, `WEB98138_SITE_DIR=DIR uvicorn web98138.app:app`) only
serves that output and never imports `lego_image_processor`. The `Dockerfile` (two stages) runs the
prebuild at image build time; `fly.toml` deploys app `world-98138`.

ENSO maps (feature 009, see `specs/009-enso-sst-maps/`): recipes `ocean-el-nino` (ERSST v5 `ssta`,
Dec 1997) and `ocean-la-nina` (Dec 1988) share one °C `bins` legend on the kit's nine ocean colors
and set the optional recipe key `arrangement = "B"` (an explicit `--arrangement` wins; the report
records `arrangement_source`). The netCDF-3 reader drops size-1 leading axes and rejects netCDF-4.

Living planet (feature 012, see `specs/012-living-planet/`): recipe `living-planet`, MOD17A3 NPP
2000–2015 (NTSG GeoTIFF, 385 MB, pinned by SHA-256 over HTTP: `http_only`) on six plate colors and
MODIS-Aqua chlorophyll-a 2013–2024 (one ERDDAP request, 147 MB) on five tile colors, White ice on
both, Black shadow. General additions: `datasets/geotiff.py` (strip reader, `grid.block` means, no
full decode), netCDF-3 `latitude`/`longitude`, `reduce = "climatology-mean"` (mean of valid steps +
`counts`), `content_sha256` (checksum of the decoded data, for files a server builds on request),
`class_rule.land_from` (land/ocean split from another dataset), recipe `transform = "log10"` (bins
bounds in data units) and `[<layer>.no_data]` (`value`, `color`, `rule` unobserved | share;
`maps/nodata.py`). Contract: `specs/012-living-planet/contracts/recipe-and-datasets.md`.

1. **Python CLI** (`cli/`, package `lego_image_processor`), written to be released as open source.
2. **Web application** (`web/`) on Fly.io at 98138.world. It calls the CLI library at build time and
   never duplicates its logic; the runtime image has no CLI dependencies.

### Layout

- `cli/src/lego_image_processor/`: `core/` (image I/O, quantization), `palette/` (LEGO colors,
  CIEDE2000 matching), `analysis/`, `layout/` (grid, land/sea mask, kit spec, validator, frame arrangements; feature 007), `kit/`
  (kit reference data, part colors), `datasets/` (registry, verified cache, readers), `maps/`
  (recipes, projection, reprojection, classification, texture, suitability, build, preview),
  `parts/` (parts lists, cited IDs, marketplace exports; feature 005), `sheets/` (build sheets:
  sections, page model, PDF and SVG backends, per-section counts; feature 006), `cli/` (Click commands), `data/` (runtime reference data, shipped with the package).
- `cli/tools/`: maintainer-only tools (`kit31203`, `partcolors`, `fixtures004`), not packaged.
- `cli/tests/`: `unit/`, `integration/`, `contract/` (CLI I/O), `fixtures/`.
- `web/`: `src/web98138/` (`prebuild.py`, `catalog.py`, `app.py`, `templates/`, `static/`),
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

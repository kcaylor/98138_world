# Quickstart: Map templates (016)

Validation run for the feature. Formats: `contracts/`. Not affiliated with or endorsed by The
LEGO Group.

## Prerequisites

- From `cli/`: `poetry install --with maintainer` (adds pyproj 3.7 for the template tool only).
- Cached pinned datasets for the real-data steps (`lego-image-processor dataset fetch …`, or
  `map build --fetch`). Steps 4–6 need ETOPO 2022; step 7 needs ERSST v5 1991–2020.

## Steps

1. **Kit golden, before any code change** (fixtures; committed):
   `PYTHONPATH=tools poetry run python -m maptemplates kit-golden --fixtures --out
   tests/fixtures/golden/kit_outputs.json`. Real data, outside the repo:
   `… kit-golden --out ~/kit-before.json` (on `main`, or on this branch before code changes).
2. **Part 3070b data**: `PYTHONPATH=tools poetry run python -m partnumbers build --check` and
   `… -m partcolors build --check` → "no differences". `poetry run lego-image-processor kit
   part-colors --part 3070b` lists Black among the colors.
3. **Unit and contract tests**: `poetry run pytest` (offline; the one Winkel end-to-end tool test
   runs only with pyproj installed).
4. **Generate and review**: `PYTHONPATH=tools poetry run python -m maptemplates generate
   winkel-tripel` → candidate, review sheet and flags in `<cache>/templates/`; counts about
   2,553 land / 5,691 ocean / 1,996 margin, ring 288 (research R2); about 194 + 97 flags.
5. **Owner review** (blocking): the owner looks at the sheet and gives corrections and a yes.
   Then `… maptemplates write winkel-tripel --corrections FILE --confirmed-on YYYY-MM-DD`
   (without `--corrections` when there are none). `poetry run lego-image-processor template show
   winkel-tripel` shows the confirmation (role "project owner", the date). Done 2026-11-24: the
   owner confirmed `winkel-tripel` as generated, with no corrections.
6. **Reproducible**: `… maptemplates build winkel-tripel --check` → exit 0, "no differences".
   Change one character of `classes` in the package file → exit 1 naming the stud; restore it.
7. **Ice regions**: `… maptemplates ice-mask winkel-tripel` then `--check` → "no differences".
8. **Build on Winkel** (SC-002, SC-003):
   ```bash
   poetry run lego-image-processor map build ocean-sst --template winkel-tripel -o w.json --preview w.png
   poetry run lego-image-processor parts list w.json --kits 1
   poetry run lego-image-processor parts export w.json --bricklink w.xml --rebrickable w.csv
   poetry run lego-image-processor sheets build w.json -o w.pdf
   poetry run lego-image-processor validate w.json
   poetry run lego-image-processor map cells ocean-sst --template winkel-tripel -o cells.json
   ```
   Expect: counts equal `template show`; the parts total 10,240 with 3070b Black for every margin
   stud, all needed beyond one kit; the preview shows rounds, with the Black margin drawn in its
   black background (another margin or ring color shows as squares); sheets draw squares;
   `--ring-color lego_white` colors exactly the template's ring studs (the `ring` count in
   `template show`; 288 with the exact fit, an example, not a value to test against); layout,
   report, sheets and `cells.json` cite ETOPO 2022 as the template's dataset. Repeat for
   `official-31203-bathymetry`, `land-elevation`, `living-planet`, `rainfall`.
9. **Errors**: `map build official-31203 --template winkel-tripel` (suggests the bathymetry
   recipe), `map build ocean-el-nino --template winkel-tripel` (arrangement B), `layout arrange
   w.json --arrangement B -o x.json`, `--margin-color lego_black --ring-color lego_black`: each
   exits 1 with the message in `contracts/cli.md`.
10. **Kit unchanged on real data** (SC-001): `… maptemplates kit-golden --out ~/kit-after.json`
    and `diff ~/kit-before.json ~/kit-after.json` → no output.
11. **Web** (P2, SC-006): from `web/`, `python -m web98138.prebuild --out site --no-prices`, then
    `WEB98138_SITE_DIR=site uvicorn web98138.app:app --port 8080`; open
    `/maps/ocean-sst/winkel-tripel` (preview, parts, downloads; "cannot be re-hung" note; works
    with JavaScript off) and check that `official-31203`, `ocean-el-nino` and `ocean-la-nina`
    offer no Winkel version. `cd web && .venv/bin/pytest` passes, including the kit golden.
12. **Prices** (owner, later): after `parts prices fetch` with the BrickLink environment
    variables, a Winkel estimate is complete; before it, the page and `parts estimate` say
    incomplete with the square tile colors unpriced.

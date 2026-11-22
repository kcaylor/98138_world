# Quickstart: validate feature 006

Run from `cli/`. Requires feature 005. Contracts: [cli.md](contracts/cli.md),
[page-layout.md](contracts/page-layout.md). Offline.

## 1. Tests

```bash
poetry run pytest -q
```

## 2. Official design (SC-001)

```bash
poetry run lego-image-processor map build official-31203 -o /tmp/official.json
poetry run lego-image-processor sheets build /tmp/official.json -o /tmp/official-sheets.pdf
poetry run lego-image-processor sheets counts /tmp/official.json --format json -o /tmp/counts.json
poetry run lego-image-processor parts list /tmp/official.json --format json -o /tmp/parts.json
```
Expect: 42 pages (overview, 1 legend page, 40 sections A1…H5); every section total 256; counts per
lot summed over sections equal `parts.json` needed; disclaimer on every page; rebuild gives an
identical file (`shasum -a 256`).

## 3. Print check

Print one section page at 100% on Letter and on A4 (`--paper a4`); measure the 100 mm bar and 10
studs (80 mm). Lay a 16 x 16 base on the grid.

## 4. SVG and subsets

```bash
poetry run lego-image-processor sheets build /tmp/official.json --format svg -o /tmp/sheets-svg
poetry run lego-image-processor sheets build /tmp/official.json --sections B2,C2 --paper a4 -o /tmp/two.pdf
```
Expect: `page-01.svg` … `page-42.svg`; the subset PDF has overview, legend and 2 section pages.

## 5. Recipe and image layouts

```bash
poetry run lego-image-processor map build land-elevation -o /tmp/elev.json   # needs cached datasets
poetry run lego-image-processor sheets build /tmp/elev.json -o /tmp/elev.pdf
poetry run lego-image-processor layout tests/fixtures/images/test_128x80_quantized.png -o /tmp/img.json -q
poetry run lego-image-processor sheets build /tmp/img.json -o /tmp/img.pdf
```
Expect: land-elevation legend 13 lots with dataset citation on the overview; image set shows
provenance from `source_image` (and, before 005 US4, unverified lots marked "no cited IDs").

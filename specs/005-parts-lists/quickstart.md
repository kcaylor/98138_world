# Quickstart: validate feature 005

Run from `cli/` (`poetry run` or the project venv). Contracts: [cli.md](contracts/cli.md),
[export-formats.md](contracts/export-formats.md). Everything is offline.

## 1. Tests

```bash
poetry run pytest -q        # all pass, no network
```

## 2. Part numbers and colors

```bash
poetry run lego-image-processor kit part-numbers
poetry run lego-image-processor kit part-colors --part 6141
```
Expect: plate = BrickLink 4073 (alternate 6141) / Rebrickable 6141; tile = 98138 on both; sources
with SHA-256; Rebrickable terms and acknowledgement; disclaimer last.

## 3. Official design (SC-001)

```bash
poetry run lego-image-processor map build official-31203 -o /tmp/official.json
poetry run lego-image-processor parts list /tmp/official.json
poetry run lego-image-processor parts list /tmp/official.json --kits 1
poetry run lego-image-processor parts export /tmp/official.json --bricklink /tmp/o.xml --rebrickable /tmp/o.csv
```
Expect: 10 verified lots, 10,240 pieces; with one kit nothing to buy, surplus = kit extras
(e.g. White plate 2); the export writes both files with 10 items.

## 4. Top-up for land elevation (SC-003; needs cached datasets from 004)

```bash
poetry run lego-image-processor map build land-elevation -o /tmp/elev.json
for n in 1 2 3; do poetry run lego-image-processor parts list /tmp/elev.json --kits $n | grep -i "to buy"; done
poetry run lego-image-processor parts export /tmp/elev.json --kits 1 --condition used \
    --bricklink /tmp/elev.xml --rebrickable /tmp/elev.csv
```
Expect: 6,382 / 4,178 / 2,912 pieces to buy; XML items use ITEMID 4073 for plates and 98138 for
tiles with BrickLink color IDs; CSV uses 6141/98138 with Rebrickable color IDs.

## 5. Loose and missing parts, spares

```bash
printf 'Part,Color,Quantity\n98138,3,1000\n' > /tmp/loose.csv
printf 'Element,Quantity\n6322819,12\n' > /tmp/missing.csv
poetry run lego-image-processor parts list /tmp/elev.json --kits 1 --owned /tmp/loose.csv \
    --missing /tmp/missing.csv --spares 2
```
Expect: Bright Bluish Green tile shortfall 2,145 + spares 43 = 2,188 to buy; Medium Azur owned
reduced by 12.

## 6. Image-derived layout (US1 scenario 3, SC-005)

```bash
poetry run lego-image-processor layout tests/fixtures/images/test_128x80_quantized.png -o /tmp/img.json -q
poetry run lego-image-processor parts list /tmp/img.json
poetry run lego-image-processor parts export /tmp/img.json --rebrickable /tmp/img.csv; echo "exit $?"
```
Before US4: Bright Red (plate, tile) and White/Nougat tiles unverified, export exit 6. After US4:
all lots verified, export exit 0.

## 7. Maintainer checks

```bash
PYTHONPATH=tools poetry run python -m partnumbers build --check
PYTHONPATH=tools poetry run python -m partcolors build --check
```
Expect: "no differences" for both.

## 8. Upload (manual, optional)

Upload `/tmp/elev.xml` at BrickLink "Upload to Wanted List" (BrickLink XML format) and `/tmp/elev.csv`
in a Rebrickable Part List "Import/Delete Parts" dialog; both should import without errors.

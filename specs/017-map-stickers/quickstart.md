# Quickstart: Map stickers (017)

Validation steps for the finished feature. Formats are in `contracts/`, entities in
`data-model.md`. Steps 1–9 need only this branch; 10–12 need feature 016 merged. Not affiliated
with or endorsed by The LEGO Group.

## Prerequisites

```bash
cd cli && poetry install            # or: uv venv --python 3.11 && uv pip install -e . pytest pypdf
lego-image-processor dataset list   # ERSST v5 LTM, ETOPO 2022, GPCP, NSIDC cached for steps 2-5
```

## Steps

1. **Tests, offline.** `cd cli && poetry run pytest` and `cd web && .venv/bin/pytest` pass with
   no network (SC-010). They include: every bundled map's sticker set from the fixtures in A, B
   and C is identical (`to_dict()` without `arrangement`, SVG bytes) and fits at 5 pt or more on
   Letter and A4 (SC-002, SC-003); cut lines within 0.1 mm (SC-001); no image in any file and
   the disclaimer in each (SC-004); outputs unchanged but for the recipe checksum, and the map
   parts' blocks of the part data unchanged (research R13 G1–G4; SC-006).

2. **Print sheet.** `lego-image-processor map stickers ocean-sst -o sst.pdf` → one Letter page:
   large and small stickers at true size with Black bleed and cut marks, "Print at 100% (no
   fit-to-page)", the 100 mm scale bar, the plaque parts with IDs, the ERSST v5 citation and
   license, and the disclaimer (US1-1). Print it at 100%: the scale bar measures 100 mm, the large
   cut line 125.8 × 61.8 mm and the small one 45.8 mm square. The large sticker reads "Ocean
   temperature", the line, nine ocean swatches from "-2 °C; land shadow" to "28 to 30 °C", White
   "land", the ERSST credit, "98138.world" and the disclaimer (US1-2); the small one only title,
   line and disclaimer (US1-3).

3. **Paper and SVG.** `map stickers ocean-sst -o sst-a4.pdf --paper a4` (A4, same sticker
   sizes); `map stickers ocean-sst -o sst-svg --format svg` → `sticker-small.svg` (59.8 mm
   canvas) and `sticker-large.svg` (139.8 × 75.8 mm), each with `<g id="cut-line">`, the
   disclaimer in `<desc>` and the datasets' citations and licenses in `<metadata>` (US1-4). Open one in a browser and in Inkscape: text stays inside the
   safe area. `map stickers ocean-sst -o sst.json --format json` writes the summary.

4. **Same for A, B, C (real data).** In Python, build each bundled map in A, B and C with
   `build_map` and compare `sticker_set(result).to_dict()` without its `arrangement` field and
   the two SVG files: identical (SC-003). The print sheet names the arrangement ("legend values
   from the build hung as <C>"), so compare PDF bytes only within one arrangement: run
   `map stickers ocean-sst -o x.pdf` twice, identical bytes (FR-012). Since main gained feature
   010 (merged 2026-11-25), build in A, B, C, D and E: all five are identical.

5. **Other maps.** `land-elevation`: ten land swatches "below 150 m" … "3,000 m and above",
   "offshore", "coast ring", "land shadow" (US1-5). `rainfall`: mm/yr classes with open ends, one
   White land swatch "Antarctica; Greenland", White "sea ice", Black "land shadow" with a visible
   outline, credits GPCP v2.3 and NSIDC (US1-6). `official-31203` (no download): nine ocean
   colors by name, no values; credit the design grid (US1-7). `living-planet`: White "ice" and
   "sea ice".

6. **Errors.** `map stickers ocean-sst -o x.pdf --cache-dir /tmp/empty` → the dataset and
   `dataset fetch` command, no file, no download (US1-9). A copied recipe with
   `line = "Δ temperature"` → PDF stops and suggests `--format svg`; SVG works. A recipe with a
   very long `line` → the field and the space needed and available.

7. **Plaque parts.** The command's output lists, per plaque, the tile and the plate in Black with
   LEGO element and design, BrickLink and Rebrickable IDs, says the sticker is printed, not a LEGO
   part, and ends with the disclaimer (US1-10, SC-005). Maintainer:
   `PYTHONPATH=tools poetry run python -m partcolors plaque-parts --check` → "no differences".

8. **Nothing else changed.** `map build ocean-sst -o a.json` on this branch and on 6038d9c (the
   branch's base; its recipe files equal af3ce57's, and af3ce57's previews predate 6038d9c's round
   studs on black) give layouts that differ only in the recipe SHA-256 (and its derived
   checksums); parts lists, exports, estimates (with `--prices`), sheets and `cells.json`
   likewise (SC-006, FR-017).

9. **Web (P2).**
   ```bash
   cd web && python -m web98138.prebuild --out site --no-prices
   WEB98138_SITE_DIR=site uvicorn web98138.app:app --port 8080
   ```
   The manifest has `maps[].stickers.kit-31203` with four files, sizes and SHA-256 for every map;
   `/maps/ocean-sst/A`, `/B` and `/C` show the same two sticker images with alt text, the plaque
   parts, the color note and four downloads, also with JavaScript off (US2-1 to US2-3). Site
   output grows by less than 2 MB (SC-008).

## After feature 016

10. **Winkel stickers.** `map stickers ocean-sst --template winkel-tripel -o w.pdf`: both lines
    end with "Winkel tripel projection.", the credit includes ETOPO 2022 (US3-4, FR-025); the
    prebuild writes `stickers.winkel-tripel` for each Winkel variant (US2-4, FR-020).

11. **Plaque in a corner.**
    `map build ocean-sst --template winkel-tripel --plaque bottom-left -o p.json --preview p.png`:
    `metadata.plaque` at rows 73–78, columns 1–6; 10,204 positions; land and ocean positions equal
    the build without `--plaque` (US3-1, SC-009). `parts list p.json --kits 1`: one Black tile 6x6
    (10202) to buy, 36 fewer square tiles, leftovers unchanged; `parts estimate p.json --prices
    FILE` prices the tile or is incomplete with it unpriced (US3-2): no snapshot is packaged until
    the owner's refresh (T091), so use `tests/fixtures/prices/bricklink_price_guide_3070b.json`
    (no 10202 row: incomplete, the tile unpriced, a `--lot 10202:26` hint) and
    `tests/fixtures/prices/bricklink_price_guide_plaque.json` (complete). `sheets build p.json -o
    p-sheets.pdf`: section A5 shows one outlined rectangle "tile 6x6 (10202)", counted there and
    in the legend (US3-3). `validate p.json` finds no mask mismatch and reports the square tiles
    and the plaque tile as beyond the kit (80.5% buildable from the kit, as without the plaque);
    `map cells … --plaque bottom-left` marks `P` studs.

12. **Plaque errors.** `--plaque bottom-left` without `--template` → "the kit template has no
    margin"; a corner that does not fit → the space needed and available (every corner of the
    packaged Winkel template fits, so this needs a template copy with a smaller clear block, as in
    `tests/contract/test_map_plaque_contract.py`); a recipe naming a corner built with `--plaque
    none` → no plaque (US3-5, US3-6).

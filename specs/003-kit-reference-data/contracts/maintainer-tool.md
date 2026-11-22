# Contract: maintainer extraction tool (`cli/tools/kit31203`)

Not shipped in the package. Requires the optional Poetry group: `poetry install --with maintainer`.

```
cd cli
poetry run python -m kit31203 extract [--pdf PATH] [--cache-dir DIR] [--out-dir DIR]
                                      [--date YYYY-MM-DD] [--check] [--report PATH]
poetry run python -m kit31203 review  [--pdf PATH] [--out PATH]     # ambiguous-position sheet
```

(`python -m` resolves because the command runs with `cli/tools` on `PYTHONPATH`; the tool's
`__main__` also inserts it.)

## `extract`

Steps, all-or-nothing (outputs are written to a temp dir and moved into `--out-dir`, default
`src/lego_image_processor/data/`, only if every step passes):

1. Resolve PDF: `--pdf`, else cache, else download from the pinned URL to `<cache>/sources/` via a
   `.part` file. Verify SHA-256 before any parsing.
2. Inventory: words on page 159 → 32 (element, qty) pairs → join `part_catalog.json` → inventory.
3. Sections: find exactly one 154×154/154×153 image on each of the 40 pinned pages; compute
   (col,row) from placement and from page order; both must agree.
4. Classify 10,240 cells; apply `overrides.json`; check supply limits.
5. Write design, mask, mask change record, inventory (colors file is curated, only validated).

Exit codes and messages (stderr):

| Code | Condition | Message contains |
|---|---|---|
| 0 | success (or `--check` with no diff) | summary: lines, pieces, sections, flagged/resolved, per-color used/supplied/spare, mask changes |
| 3 | download failed / interrupted | URL, reason; no file left marked complete |
| 4 | checksum mismatch | `expected b593e2f4…` and `actual …` |
| 5 | section images missing/extra | the page numbers missing or duplicated |
| 6 | placement and page order disagree / slot collision | page, both positions |
| 7 | unresolved ambiguous positions | count and first 20 `(x,y) auto/second ratio`; hint to run `review` |
| 8 | supply exceeded | color, used, supplied |
| 9 | inventory pairing failed or not 32 lines / part catalog missing an element | element/count tokens |
| 1 | `--check` found differences | file and first differing keys/rows |

## `review`

Writes a PNG contact sheet (to a path outside the repo by default) of each ambiguous cell
enlarged with its neighbors, its sample RGB and its two candidate colors, plus a JSON stub to
paste into `overrides.json`. The sheet contains LEGO artwork and must not be committed.

## `overrides.json`

```json
{"format_version": "1", "overrides": [
  {"x": 0, "y": 32, "chosen": "lego_bright_bluish_green",
   "reason": "corner of 154x153 section (0,2); sample between Earth Blue and Bright Bluish Green; Earth Blue would exceed supply",
   "decided_by": "<maintainer>", "decided_on": "YYYY-MM-DD"}
]}
```

Not affiliated with or endorsed by The LEGO Group.

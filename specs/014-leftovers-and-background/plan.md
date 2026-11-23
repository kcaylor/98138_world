# Implementation Plan: Leftovers in the box, and a light gray page background (014)

## Technical Context

Python 3.11, existing packages only (Click, Jinja2, FastAPI). No new dependencies, no data files.

## Constitution Check

CLI first (library + `parts list` before the web page), test first, offline tests, cited kit data
read at run time, disclaimer kept on every page. No violations.

## Design

- `parts/partslist.py`: new frozen dataclass `Leftover` (part_id, color_key, lego name/id/element,
  rgb, kit_supply, used; property `leftover`; `to_dict`). `build_parts_list` builds one row per
  inventory map element (land, then ocean, in inventory order sorted like lots) with supply
  `kits × qty − missing` and `used` = positions whose resolved color key and part match.
  `PartsList.leftovers` (tuple, default empty), `totals()["leftover"]`, JSON `leftovers` after
  `lots`. Exported from `parts/__init__.py`.
- `cli/parts.py`: table "Left over in the box (N kit(s))" with part, color, kit, used, left over,
  and a total line, shown when kits ≥ 1.
- `web/prebuild.py`: variant entry gains `leftovers` (list of dicts from the one-kit parts list)
  and `summary.left_over_with_kit`. `map.html`: a stat tile "Left over in the box" and a
  "Left over in the box (one kit)" table. `home.html` unchanged.
- `style.css`: `--bg: #e9e9e9`, `--stud-mat: #e9e9e9`; `.stud-img` gets padding and the mat
  background; card thumbnails get a mat; swatch stroke darker.

See `contracts/parts-list-leftovers.md` for the JSON shape.

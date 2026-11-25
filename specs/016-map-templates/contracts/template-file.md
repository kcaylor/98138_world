# Contract: template data file (format "1")

`cli/src/lego_image_processor/data/templates/<id>.json`, written by
`PYTHONPATH=tools python -m maptemplates write|build`, read by `templates.load_template(id)`.
UTF-8 JSON. Rows of `classes`, `locations.lat` and `locations.lon` are written one board row per
line. Not affiliated with or endorsed by The LEGO Group.

| Field | Type | Rule |
|---|---|---|
| `format_version` | `"1"` | |
| `id` | string | `^[a-z0-9][a-z0-9-]{1,63}$`, equals the file stem; not `kit-31203` |
| `title`, `description` | string | non-empty |
| `projection.name` | `"winkel-tripel"` | the run-time forward formula to use |
| `projection.proj` | string | `+proj=wintri +lat_1=50.4598 +lon_0=11.1 +R=1` |
| `projection.lat_1`, `projection.lon_0` | number | degrees; used by the formula |
| `projection.citation` | string | Winkel (1921); Snyder (1993); PROJ `wintri` documentation URL |
| `projection.fit` | `{mode: "contain", extent: [x0, x1, y0, y1], scale, centre: [x, y]}` | exact extent; studs per projected unit |
| `projection.check_points` | `[[lon, lat, x, y], …]` (24) | pyproj values; the loader recomputes x, y and requires \|Δ\| < 1e-9 |
| `board` | `{modules: [8, 5], module: 16, width: 128, height: 80, pitch_mm: 8.0}` | whole modules; 128 × 80 for now |
| `parts` | `{land: "6141", ocean: "98138", margin: "3070b"}` | exactly these |
| `frame` | `{kit: "31203", arrangements: ["A"], source: "kit_31203_arrangements.json"}` | |
| `classes` | string[80], each 128 of `L` `O` `M` | after corrections |
| `locations.lat`, `locations.lon` | (number｜null)[80][128] | 4 decimals; non-null exactly on `L`/`O`; lon in −180..180 |
| `counts` | `{land, ocean, margin, ring, modules: {full, partial, empty}, corners: {<corner>: {row, col, height, width}}}` | must equal what the loader derives |
| `source.generator` | `"cli/tools/maptemplates"` | |
| `source.generated_on` | date | ignored by `--check` |
| `source.dataset` | `{id, version, url, sha256, citation, license}` | the pinned ETOPO 2022 entry |
| `source.method` | `{supersample: 4, on_globe_share: 0.5, land_share: 0.5, land_rule: "elevation > 0 m", round_trip_tolerance: 1e-6, location_rule}` | |
| `source.software` | `{pyproj, proj}` | versions used |
| `source.disclaimer` | string | the LEGO disclaimer |
| `corrections` | `[{row, col, class, reason}]` | `class` in land, ocean, margin; reasons non-empty |
| `confirmation` | `{role: "project owner", date}` or `null` | null: not buildable |
| `disclaimer` | string | the LEGO disclaimer |

Loader errors (`TemplateError`, a `ValueError`) name the file and the rule. A template with
`confirmation: null` loads (for `template list/show` and the tool) but `map build` refuses it.

## Layout digest (`Template.layout_sha256`)

The loader computes `layout_sha256`, the SHA-256 of the canonical JSON (UTF-8, `sort_keys=True`,
`separators=(",", ":")`, `ensure_ascii=False`) of:

```json
{"id": …, "board": …, "parts": …,
 "projection": {"name": …, "proj": …, "lat_1": …, "lon_0": …, "fit": …},
 "classes": […], "locations": {"lat": […], "lon": […]}}
```

It leaves out `title`, `description`, `check_points`, `counts`, `source`, `corrections`,
`confirmation` and `disclaimer`; corrections count only through `classes`. Writing the
confirmation therefore does not change it, and neither does a test copy with a test confirmation.
Any change to classes, locations, fit, board or parts does change it. Files that depend on the
layout record this digest; layouts also record the file's SHA-256 as provenance
(data-model.md TemplateLayoutDigest).

## Dataset provenance

`source.dataset.id` names a registry entry in `data/datasets.json` (`etopo2022-surface-10m`).
The entry's `version`, `sha256`, `citation` and `license` must equal the file's
`source.dataset`. Non-kit outputs copy `{id, version, title, publisher, license, citation, doi}`
from the entry (data-model.md TemplateDataset).

## Ice file `data/templates/<id>-ice.json`

As `data/kit_31203_ice.json` (feature 015 `contracts/cells-json.md` family):

- `format_version`: "1".
- `template_id`.
- `grid`: `{width: 128, height: 80, coordinates: "board, row-major index = row * 128 + column"}`.
- `source`: rules, ERSST dataset, `template_layout_sha256` (the template's layout digest, above;
  not the file's SHA-256), generator, generated_on, disclaimer.
- `land_ice` and `sea_ice`: `{count, cells}`. Land ice only on `L`, sea ice only on `O`.

`load_template_ice` refuses a file whose `template_layout_sha256` differs from the loaded
template's `layout_sha256`. Confirming a template leaves its ice file valid; it needs
regenerating only when corrections or a regeneration change classes or locations
(`ice-mask --check` reports it).

## Maintainer tool `python -m maptemplates` (run from `cli/`, `PYTHONPATH=tools`)

| Command | Does | Exit |
|---|---|---|
| `generate ID [--dataset FILE] [--cache-dir DIR] [--out DIR]` | writes the candidate JSON, review sheet PNG and flags JSON to `--out` (default `<cache>/templates/`) | 0; 4 dataset missing or checksum mismatch |
| `review ID [--out DIR]` | review sheet of the committed file with its corrections | 0 |
| `write ID [--corrections FILE] [--confirmed-on DATE]` | regenerates, applies corrections (from FILE or the committed file), writes the package file; sets confirmation only with `--confirmed-on`; clears it if classes or locations changed | 0 |
| `build ID --check` | regenerates and compares with the committed file (all but `generated_on`) | 0 "no differences"; 1 differences listed |
| `ice-mask ID [--check]` | writes or checks `<id>-ice.json` (no pyproj needed) | 0 / 1 |
| `kit-golden --out FILE [--cache-dir DIR \| --fixtures]` | digests of every kit output (R9 of research.md) | 0 |

`generate`, `write` and `build` need pyproj (`poetry install --with maintainer`). Every command
prints the disclaimer last.

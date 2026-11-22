# Contract: CLI (004, Q2)

All human output ends with the line `Not affiliated with or endorsed by The LEGO Group.`; JSON
files carry `"disclaimer"`. `-q` suppresses human output. Exit codes: 0 ok; 1 usage or recipe
error (Click); 2 Click usage; 3 dataset not cached; 4 checksum or size mismatch; 5 network or
I/O error during fetch. No command opens the network except `dataset fetch` and `map build --fetch`.

## `map build RECIPE`

`RECIPE` is a path or a bundled recipe id.

| Option | Meaning |
|---|---|
| `-o, --output PATH` | layout JSON (required) |
| `--preview PATH` | PNG preview, 8×8 px per stud |
| `--report PATH` | suitability report JSON |
| `--cache-dir PATH` | cache root override |
| `--fetch` | download the recipe's missing pinned datasets (verified size and SHA-256) before building; exit 4/5 on checksum/network failure, nothing written |
| `--compare-official` | print ocean/land cell agreement with the official design |
| `-q` | quiet |

Output (human): recipe id and title; per layer: role, dataset id/version, classes and counts;
warnings; supply table; agreement if requested (always for `official-31203*`); output paths;
citations and licenses; disclaimer. Missing dataset without `--fetch` → exit 3 with
`Dataset <id> is not cached. Fetch it with: lego-image-processor dataset fetch <id> (or rerun with --fetch)`;
nothing written, no network use.

## `map check RECIPE`

Same inputs as build without `-o`, `--preview` and `--fetch` (a missing dataset exits 3 naming
`dataset fetch <id>`); prints the suitability report; `--report PATH` writes JSON.
Exit 0 even with warnings.

## `map recipes`

Lists bundled recipes (id, title, layers, datasets needed, cached yes/no). `--copy ID DEST` writes
the bundled file to `DEST` (refuses to overwrite without `--force`).

## `dataset list`

Table: id, version, size, license, cached. `--format json`.

## `dataset fetch ID... | --recipe RECIPE`

Downloads each missing dataset (or those a recipe needs), verifies size and SHA-256, stores it.
Prints path and citation. Already cached and valid → "already cached". `--cache-dir`.

## `dataset info ID`

Full entry: title, publisher, version, URL, size, SHA-256, format, variables, grid, license,
citation, DOI, acknowledgement, notes, cache path and status.

## `kit part-colors [--part 6141|98138] [--format table|json]`

Colors each part is made in (kit colors marked), with LEGO, BrickLink and Rebrickable names and
IDs, element ID, and source.

## Unchanged

`quantize`, `stats`, `layout`, `validate`, `kit inventory`, `kit colors`. `validate` accepts
recipe layouts (schema 2.0; `metadata.map` ignored for validation).

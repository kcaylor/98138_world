# Contract: recipe key `arrangement` and its CLI/library behaviour (009)

All commands end their output (and error output) with "Not affiliated with or endorsed by The LEGO
Group."

## Recipe key (format "1", optional)

```toml
format = "1"
id = "ocean-el-nino"
arrangement = "B"     # optional; A | B | C (any case) | europe-africa | americas | asia-australia
```

| Case | Result |
|---|---|
| key absent | `Recipe.arrangement = None`; builds as A unless `--arrangement` is given (unchanged behaviour) |
| valid string | parsed with `parse_arrangement`; `"b"`, `"B"`, `"americas"` are the same |
| invalid string (`"D"`) or non-string (`2`, `true`, table) | `RecipeError` at load: `arrangement: must be one of A, B, C, europe-africa, americas, asia-australia`; `map build`/`map check` exit 1 with `Recipe error in <file>: arrangement: …` |
| read by a tool from before 009 | rejected as an unknown key (strict validation); format stays "1" (as for `[shadow]`) |

## Precedence (FR-011)

1. `--arrangement X` on the command line, or `build_map(recipe, arrangement=X)` /
   `check_recipe(recipe, arrangement=X)` → X, source `option`.
2. Else the recipe's `arrangement` → source `recipe`.
3. Else A → source `default`.

`maps.build.resolve_arrangement(recipe, arrangement=None) -> tuple[Arrangement, str]` implements
this; `build_map` and `check_recipe` call it when `arrangement` is None.

## `map build RECIPE -o OUT [--arrangement X] [...]`

- `--arrangement`/`-a`: as feature 007 (values, case, exit 2 on an unknown value), but its default
  is now "not given". Help: "… Default: the recipe's `arrangement`, else A."
- Output line (replaces the 007 line):
  - `Arrangement: B (americas, frames 3·1·2, America in the centre) - from the recipe`
  - `Arrangement: A (europe-africa, frames 1·2·3, Europe and Africa in the centre) - from --arrangement`
  - `Arrangement: A (europe-africa, …) - default`
- Report JSON (`--report`): existing `arrangement` record plus `"arrangement_source": "recipe" |
  "option" | "default"`.
- Layout: `metadata.arrangement` as feature 007 (absent/A rules unchanged). No source recorded.
  Existing recipes built without `--arrangement` give byte-identical layouts to 008 (timestamps
  aside, SC-006).

## `map check RECIPE [--arrangement X] [...]`

Same precedence, output line and report field as `map build`.

## `map build` / `map check` legend and extra tiles (FR-015, FR-016)

For a layer classified with `bins`, after the supply table:

```text
  Legend (°C):
    lego_earth_blue               below -1.5        14
    lego_bright_bluish_green      -1.5 to -0.5     976
    ...
    lego_bright_yellowish_green   -0.1 to +0.1   1,747
    ...
    lego_vibrant_coral            +1 and above     533
```

Range text: first class `below b1`, last class `b(n-1) and above`, others `b(i) to b(i+1)`; numbers
with sign (except 0), up to 2 decimals, trailing zeros removed; header units from the recipe
layer's registry variable `units` (`degC`, `degree_C` → `°C`; none → no unit). Membership is [lower, upper).

For every layer, after its table: `  Tiles beyond one kit: N` (N = `extra_tiles(layer supply rows)`, thousands
separator). Existing warnings (`over_supply`, `beyond_kit`, `empty_class`) are unchanged.

## `map recipes`

Columns become `id, title, arrangement, layers, datasets, cached`; `arrangement` is the recipe's
arrangement id, or `A` when the key is absent.

## `layout arrange`

Unchanged (`--arrangement` still required there).

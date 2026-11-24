# Contract: CLI additions

All additions are optional; every existing command, flag and output keeps its meaning and, for
kit builds, its bytes. Errors print `Error: …` and the disclaimer last. Not affiliated with or
endorsed by The LEGO Group.

## `map build`, `map check`, `map cells`

New options:

| Option | Value | Default |
|---|---|---|
| `--template ID` | a known template id (`kit-31203`, `winkel-tripel`) | recipe `template`, else `kit-31203` |
| `--margin-color KEY` | a cited 3070b color | recipe `[margin].color`, else `lego_black` |
| `--ring-color KEY｜none` | a cited 3070b color, or `none` | recipe `[margin].ring`, else no ring |

Output for a non-kit build adds, after the arrangement line:
`Template: winkel-tripel (Winkel tripel …) - from --template|from the recipe`, and
`Margin: <margin> square tiles (part 3070b): <color>; ring <ring> <ring color>` before the layer
report. Here `<margin>` and `<ring>` are the template's counts (for example 1,996 and 288 with
the exact fit, research R2); tests take them from the loaded template and must not copy the
example numbers. The `Layout:` line adds `, N margin tiles`. Kit builds print exactly as today.

| Case | Exit | Message names |
|---|---|---|
| unknown `--template` | 2 | the confirmed templates |
| unknown recipe `template` | 1 | key path `template`, the confirmed templates |
| template not confirmed | 1 | the template, "not confirmed by the project owner", the confirmed templates |
| resolved arrangement ≠ A on a non-kit template | 1 | "the frames of a curved map cannot be re-hung"; where the arrangement came from |
| a layer reads a dataset whose registry entry has `format = "kit-design"` (`kit31203-design`, used by `official-31203`) | 1 | suggests `official-31203-bathymetry` |
| margin or ring color not a 3070b color, or ring = margin | 1 | the option or key path; the available 3070b color keys; `kit part-colors --part 3070b` |
| `--compare-official` on a non-kit template | 1 | the official design is on the kit grid |
| `[margin]` on a kit build | 0 | stdout note: margin settings are not used on the kit template |

## `template` (new group)

- `template list [--format table|json]`: id, title, status (`reference`, `confirmed`,
  `unconfirmed`), land/ocean/margin counts, arrangements. Exit 0.
- `template show ID [--format table|json]`: projection, board, parts, counts, ring, module counts,
  corner blocks, source dataset, corrections count, confirmation. Exit 0; unknown ID exit 1.
- `template locate ID LAT LON`: the stud (row, column, section label, class) containing the
  location, or "off the globe (margin)". `template locate ID --stud ROW COL`: the stud's
  location and class. Exit 0; out-of-range input exit 2.

## Other commands

- `layout arrange` on a layout with `metadata.template`: exit 1, "the frames of a curved map
  cannot be re-hung (template winkel-tripel)".
- `validate`: for a non-kit layout the mask check uses the template; square tiles are reported as
  `color_unavailable` for part 3070b (no kit supplies them). Kit layouts unchanged.
- `parts list`, `parts export`, `parts estimate`, `sheets build`, `sheets counts`: accept non-kit
  layouts; square tiles appear as part 3070b, type "square tile", in tables, JSON, BrickLink XML
  (`ITEMID 3070`: the BrickLink item in `part_numbers.json`, which files 3070b as an alternate of
  item 3070) and Rebrickable CSV (`3070b`). Leftovers list kit elements only.
- `kit part-colors --part 3070b`: the cited square-tile colors.
- `parts prices fetch --lot 3070b:26` is accepted (owner only; needs the BrickLink environment
  variables).

## Library

- `templates.load_template(id)`, `templates.list_templates()`, `templates.confirmed_templates()`,
  `templates.KIT_TEMPLATE_ID`, `templates.TemplateError`.
- `templates.compatibility(recipe, template, arrangement=None)` → None or the reason it cannot be
  built (used by the web prebuild).
- `build_map(recipe, *, cache_dir=None, compare_official=None, arrangement=None, template=None,
  margin=None)`; `MapResult.template`.
- `Template.stud_at(lat, lon)` → (row, col) or None; `Template.location(row, col)` → (lat, lon)
  or None (FR-005).

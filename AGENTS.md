<!-- speckit-harness:start (managed by speckit-harness 1.1.0; edits inside this block are overwritten) -->
## Spec-driven development (Spec Kit harness)

This repository uses GitHub Spec Kit with the speckit-harness workflow. These instructions apply to
every coding agent, whatever tool or model runs it.

**Before any spec, planning, or feature work**, run this from the repository root, replacing
`<agent>` with your Spec Kit integration key (`claude`, `codex`, `gemini`, `cursor-agent`,
`opencode`, and so on; `speckit-harness agents` lists them):

    speckit-harness ensure --agent <agent>

It checks for harness updates, installs or refreshes the workflow for your agent, and prints any
action you need to take. If the command is not found, install the harness on this machine with:

    git clone https://github.com/ecohydro/speckit-harness.git ~/.local/share/speckit-harness && bash ~/.local/share/speckit-harness/bootstrap.sh

**To build a feature**, use the `speckit-run` skill. If your agent does not load skills, read
`.specify/harness/skills/speckit-run/SKILL.md` and follow it. Its input is an existing
specification (`specs/<NNN-name>/spec.md` or a design document). With no specification, it drafts
one after asking the user up to four questions.

Paired Claude/Codex runs: `speckit-pair` (opt-in).

**For the constitution**, use `speckit-derive-constitution`
(`.specify/harness/skills/speckit-derive-constitution/SKILL.md`). Do not edit
`.specify/memory/constitution.md` by hand.

- Spec Kit phase instructions for any agent: `.specify/harness/commands/speckit.<phase>.md`
- Decisions reserved for the user: `.specify/memory/run-policy.md`
- Progress for a feature in flight: `specs/<NNN-name>/run-state.md` (read it before resuming)
<!-- speckit-harness:end -->

## Project: 98138.world

98138.world uses the LEGO World Map kit (31203) as a fixed template (a 128×80 grid of 10,240
positions and the kit's land/sea mask) and builds a general way to turn any suitable gridded map
into a buildable mosaic. A map is a land layer plus an ocean layer, each either data-driven or a
shaded background, described by a recipe file. Read `docs/vision.md` before planning a feature; the
rules are in `.specify/memory/constitution.md`.

The kit reference data in `cli/src/lego_image_processor/data/` is cited (feature 003, see
`specs/003-kit-reference-data/` and each data file's `source` block). Land is the white 1×1 round
plate, part 6141 (element 614101); ocean is the 1×1 round tile, part 98138, in 9 colors. The parts
inventory (`kit_31203_inventory.json`, page 159) and the official design
(`kit_31203_design.json`, 40 section pages) are extracted from the official building instructions
PDF pinned by URL and SHA-256; the 10 colors' LEGO, BrickLink and Rebrickable names and IDs
(`kit_colors.json`) come from the cited catalogs. Never commit the PDF or crops of it. To
regenerate or check the data, from `cli/`: `poetry install --with maintainer`, then
`PYTHONPATH=tools poetry run python -m kit31203 extract --check` (add `--pdf <local copy>` to skip
the download; exit 0 and "no differences" means the committed data is reproducible).

1. **Python CLI** (`cli/`, package `lego_image_processor`), written to be released as open source.
   This is the only part that exists today.
2. **Web application** on Fly.io at 98138.world, planned. It must call the CLI as a library or
   subprocess and never duplicate its logic.

### Layout

- `cli/src/lego_image_processor/`: `core/` (image I/O, quantization), `palette/` (LEGO colors,
  CIEDE2000 matching), `analysis/`, `layout/` (grid, land/sea mask, kit spec, validator), `cli/`
  (Click commands), `data/` (runtime reference data, shipped with the package).
- `cli/tests/`: `unit/`, `integration/`, `contract/` (CLI I/O), `fixtures/`.
- `specs/NNN-name/`: Spec Kit artifacts for each feature.

### Working rules

- CLI first: every capability works as a CLI command on local files before any web feature uses it.
- Test first for core logic (unit, integration, contract tests under `cli/tests/`).
- Reference data the code reads at run time belongs in `cli/src/lego_image_processor/data/`, not in
  `tests/fixtures/`.
- Anything user-facing must say: "Not affiliated with or endorsed by The LEGO Group." Never imply
  endorsement or partnership.
- Run tests: `cd cli && poetry run pytest` (without Poetry: `uv venv && uv pip install -e . pytest pytest-cov pytest-benchmark`, then `.venv/bin/pytest`).

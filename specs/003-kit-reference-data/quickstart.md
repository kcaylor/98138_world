# Quickstart: validating feature 003

Run from `cli/`. Without Poetry: `uv venv && uv pip install -e . pytest pytest-cov pytest-benchmark`
and use `.venv/bin/...` in place of `poetry run`.

## 1. Offline test suite (SC-007)

```bash
cd cli
poetry install
poetry run pytest                          # no network, no PDF; maintainer tests skip without pypdf
poetry install --with maintainer && poetry run pytest   # also runs pypdf adapter tests (synthetic PDF)
```

Expected: all pass, including `tests/integration/test_reference_consistency.py`.

## 2. Inventory and colors (US1)

```bash
poetry run lego-image-processor kit inventory
poetry run lego-image-processor kit colors --format json | python -c \
  "import json,sys; d=json.load(sys.stdin); print(len(d['colors']), sorted(c['role'] for c in d['colors']).count('land'))"
```

Expected: 32 lines, 11,694 pieces; land = 614101, part 6141, White, 3,064; nine ocean tiles
(98138); `10 1`; each table row shows LEGO, BrickLink and Rebrickable IDs; last line is the
disclaimer.

```bash
cd .. && git grep -n -E "3062b|\"brick\"|'brick'|land_brick" -- . ':!specs/001-*' ':!specs/002-*'
```

Expected: no matches outside historical spec documents (SC-006; the 003 spec text describing the
old value is the only allowed hit).

## 3. Official design and mask (US2)

```bash
cd cli
poetry run python -c "
from lego_image_processor.kit import load_official_design, load_kit_inventory
d = load_official_design(); inv = load_kit_inventory()
print(d.width, d.height, len({d.color_at(x,y) for x in range(128) for y in range(80)}))
for c in d.counts: print(c.key, c.used, c.supplied, c.spare)
print(len(d.sections))"
```

Expected: `128 80 10`; every `spare ≥ 0`; White used 3,062 / supplied 3,064; 40 sections.

Maintainer regeneration (needs network once, or `--pdf`). The tool lives in `cli/tools/kit31203`
and is not part of the package, so `python -m kit31203` resolves only with `cli/tools` on the
module path: run it from `cli/` with `PYTHONPATH=tools` (or from `cli/tools`). pytest's
`pythonpath` setting does not apply to `poetry run python -m`.

```bash
poetry install --with maintainer
PYTHONPATH=tools poetry run python -m kit31203 extract --check        # SC-008: exit 0, "no differences"
PYTHONPATH=tools poetry run python -m kit31203 extract --check --pdf /path/to/31203.pdf   # same, from a local copy
PYTHONPATH=tools poetry run python -m kit31203 extract --pdf /path/to/wrong.pdf   # exit 4, expected/actual checksums, no files written
```

## 4. Validation and layout (US3)

```bash
poetry run python -c "
from lego_image_processor.kit import load_official_design
open('/tmp/official.json','w').write(load_official_design().to_layout().to_json())"
poetry run lego-image-processor validate /tmp/official.json
```

Expected: `Buildability: 100.0% (FULLY BUILDABLE)`, `Violations: 0` (SC-005), disclaimer printed.

```bash
poetry run lego-image-processor layout tests/fixtures/images/test_128x80_quantized.png -o /tmp/l.json
poetry run lego-image-processor validate /tmp/l.json
```

Expected: JSON has `schema_version "2.0"`, land rows `plate`/`6141`; any non-kit ocean color is
reported with part `tile (98138)`, positions, and a CIEDE2000 suggestion among the 9 ocean colors;
any overuse shows required / available / shortfall.

```bash
poetry run lego-image-processor validate tests/fixtures/layouts/legacy_v1_layout.json
```

Expected: exit 1, message names schema version 1.0 and the `layout` command to regenerate.

Not affiliated with or endorsed by The LEGO Group.

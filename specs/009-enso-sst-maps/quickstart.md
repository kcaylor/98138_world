# Quickstart: validate the ENSO maps (009)

Run from `cli/`. Formats are in [contracts/](contracts/); legend and numbers in
[research.md](research.md) R1. Not affiliated with or endorsed by The LEGO Group.

## 1. Offline test suite (SC-001, SC-003, SC-006)

```bash
poetry run pytest -q            # or .venv/bin/pytest -q
poetry run pytest -q tests/integration/test_map_enso.py tests/contract/test_map_enso_contract.py
```

Expected: all pass with the network blocked (suite-wide guard); the ENSO tests use the derived
fixtures `tests/fixtures/datasets/ersst_v5_19{97,88}12_ssta.nc`.

## 2. Real data, four commands (SC-007)

```bash
lego-image-processor map build ocean-el-nino --fetch -o el-nino.json --report el-nino-report.json
lego-image-processor map build ocean-la-nina --fetch -o la-nina.json --report la-nina-report.json
lego-image-processor parts list el-nino.json --kits 1
lego-image-processor parts list la-nina.json --kits 1
```

Expected:
- each build prints `Arrangement: B (americas, frames 3·1·2, America in the centre) - from the
  recipe`, the °C legend block (9 lines, `below -1.5` … `+1 and above`), `Tiles beyond one kit:
  1,114` (El Niño) / `1,155` (La Niña), the ERSST v5 citation with doi 10.1175/JCLI-D-16-0836.1 and
  10.7289/V5T72FNM, the license, and the disclaimer;
- `parts list --kits 1` lists only ocean tiles to buy, totalling the same 1,114 / 1,155; no land
  plates;
- `jq .arrangement_source el-nino-report.json` → `"recipe"`.

## 3. Precedence and errors

```bash
lego-image-processor map build ocean-el-nino --arrangement A -o a.json   # "- from --arrangement", metadata.arrangement A
lego-image-processor map build ocean-sst -o sst.json                      # "- default", layout as before 009
lego-image-processor map recipes                                          # arrangement column: B for both ENSO recipes, A otherwise
LEGO_IMAGE_PROCESSOR_CACHE=$(mktemp -d) lego-image-processor map build ocean-la-nina -o x.json   # exit 3, names `dataset fetch ersst-v5-1988-12`
lego-image-processor parts export el-nino.json --kits 1 --bricklink wanted.xml                # only the extra tiles
lego-image-processor layout arrange el-nino.json --arrangement A -o el-nino-A.json            # re-hang without rebuilding
```

## 4. Fixture regeneration (maintainers, needs the cached real files)

```bash
PYTHONPATH=tools poetry run python -m fixtures004.make_fixtures --only ersst-v5-1997-12 --only ersst-v5-1988-12
git diff --stat tests/fixtures/datasets/   # no change when reproducible
```

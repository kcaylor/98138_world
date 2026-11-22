# Quickstart: validate feature 004

Run from `cli/`. Use `poetry run` or the project venv (`.venv/bin/`). Cache is the per-user cache
unless `--cache-dir` is given. Contracts: [cli.md](contracts/cli.md),
[recipe-format.md](contracts/recipe-format.md).

## 1. Tests (offline)

```bash
poetry run pytest -q            # all pass; no network, no downloaded files
```

## 2. Official design, exact tier (no download)

```bash
poetry run lego-image-processor map recipes
poetry run lego-image-processor map build official-31203 -o /tmp/official.json --preview /tmp/official.png
poetry run lego-image-processor validate /tmp/official.json
```
Expect: agreement 10,240/10,240; `Buildability: 100.0% (FULLY BUILDABLE)`; disclaimer last.

## 3. Datasets

```bash
poetry run lego-image-processor dataset list
poetry run lego-image-processor dataset fetch --recipe official-31203-bathymetry
poetry run lego-image-processor dataset fetch ersst-v5-ltm-1991-2020
poetry run lego-image-processor dataset info etopo2022-surface-10m
```
Expect: two files, 9,357,398 and 1,160,004 bytes, checksums verified, citations shown.
Missing-dataset check: with an empty `--cache-dir`, `map build ocean-sst -o x.json` exits 3 with the
fetch command and writes nothing.

## 4. Data maps (offline after step 3)

```bash
poetry run lego-image-processor map build official-31203-bathymetry -o /tmp/bathy.json --report /tmp/bathy-report.json
poetry run lego-image-processor map build ocean-sst -o /tmp/sst.json --preview /tmp/sst.png
poetry run lego-image-processor map build land-elevation -o /tmp/elev.json --preview /tmp/elev.png
for f in bathy sst elev; do poetry run lego-image-processor validate /tmp/$f.json; done
```
Expect: bathymetry land 3,062 identical, ocean agreement ≥ 24% printed, FULLY BUILDABLE; SST FULLY
BUILDABLE (rank-to-supply); elevation accepted, non-kit plate colors listed as beyond the kit.
Each build < 30 s.

## 5. Suitability

```bash
poetry run lego-image-processor map check land-elevation --report /tmp/elev-check.json
```
Expect: variance lost ~8%, no detail warning; neighbouring colors ΔE00 ≥ 5.

## 6. Maintainer checks

```bash
PYTHONPATH=tools poetry run python -m kit31203 fit-projection --check   # uses cached ETOPO
PYTHONPATH=tools poetry run python -m partcolors build --check          # uses pinned snapshots
```
Expect: "no differences".

Not affiliated with or endorsed by The LEGO Group.

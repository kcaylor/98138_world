# Implementation Plan: Rainfall map (013)

**Branch**: `013-rainfall` | **Date**: 2026-11-22 | **Spec**: `spec.md`

## Summary

A bundled recipe `rainfall` (GPCP v2.3 1991–2020 annual mean precipitation on six plate and five
tile colors, White ice sheets and NSIDC sea ice, Black shadow), plus the general pieces it needs:
a netCDF-4 reader (h5py) with CF polar-stereographic coordinates, multi-file registry entries,
bilinear sampling, region/dataset overrides, and a secondary-units legend. Web prebuild lists the
map (24 variants).

## Technical Context

- Python 3.11, Click, numpy, scipy, Pillow; **new**: h5py 3.16.0 (BSD-3-Clause; owner decision 1).
- Storage: registry JSON, per-user cache; tests offline with derived fixtures.
- Performance: GPCP 0.7 MB, NSIDC 60 × ~300 KB; build in seconds, memory < 200 MB.

## Constitution Check

- I (fixed template), II (recipe-defined layers): the map is a recipe; overrides are recipe rules. ✓
- III (data in): gridded data, ordered bins. ✓
- IV (pinned, cached, cited, offline): every file pinned by SHA-256; citations in outputs. ✓
- V (buildable, honest): colors checked per part; suitability report unchanged. ✓
- VI (CLI first): all features in the library and CLI; the web calls the library. ✓
- VII (test first, offline): unit/integration/contract tests with fixtures. ✓
- VIII (disclaimer): recipe, docs, fixtures, outputs. ✓

No violations; no Complexity Tracking entries.

## Project Structure (changes)

```
cli/pyproject.toml                         h5py dependency
cli/src/lego_image_processor/
  datasets/netcdf4.py                      new: read_netcdf4, polar stereographic inverse, multi-file
  datasets/grid.py                         SourceGrid.points
  datasets/registry.py                     netcdf4, files
  datasets/cache.py                        multi-file cached_path/is_cached/verify/resolve/fetch
  datasets/readers.py                      route netcdf4
  maps/recipe.py                           sampling, Override, Legend
  maps/reproject.py                        points grids; bilinear
  maps/overrides.py                        new: override cells
  maps/build.py                            wire sampling/overrides/legend; report/provenance
  cli/map.py, cli/dataset.py               legend in two units; overrides line; multi-file rows
  data/datasets.json                       gpcp-v23-ltm-1991-2020, nsidc-cdr-v6-seaice-minimum-1991-2020
  maps/recipes/rainfall.toml               new
cli/tools/fixtures004/make_fixtures.py     GPCP and NSIDC fixtures
cli/tests/...                              unit, integration, contract tests; fixtures
web/src/web98138/__init__.py               MAP_IDS + rainfall
web/requirements-build.txt                 h5py==3.16.0
docs/runbook.md, CLAUDE.md, AGENTS.md, cli/README.md, docs/deploy.md
```

## Design notes

- Per-cell work (sampling, overrides) runs in kit coordinates (combination A) and is rolled.
- Override cells are coded in the class array as `OVERRIDE_CLASS_BASE - i` (−10, −11, …) so the
  build loop labels them; no-data keeps −2.
- The netCDF-3 path is untouched; `read_dataset` routes `netcdf4` to `read_netcdf4`.

Not affiliated with or endorsed by The LEGO Group.

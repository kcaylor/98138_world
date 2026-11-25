# Implementation Plan: Living planet map (012)

**Branch**: `012-living-planet` | **Date**: 2026-11-22 | **Spec**: `spec.md`

## Summary

Add the bundled recipe `living-planet` (MOD17A3 NPP on land, MODIS-Aqua chlorophyll-a climatology
at sea, White ice on both, Black shadow) and the general machinery it needs: a strip-reading
GeoTIFF reader with block averaging, ERDDAP netCDF-3 names and a climatology-mean reducer with
valid-step counts, content checksums for generated-on-request files, an HTTP exception for
checksum-pinned files, a land/ocean split taken from another dataset, a `log10` transform, and a
`no_data` table per data layer. Then add the map to the web prebuild and docs.

## Technical Context

**Language/Version**: Python 3.11 (CLI, web)
**Primary Dependencies**: existing only: NumPy, SciPy (`netcdf_file`, `ndimage`), Pillow (TIFF
strip decoding through its bundled libtiff), Click; no new dependency.
**Storage**: per-user dataset cache (`<root>/datasets/<id>/<version>/<file>`).
**Testing**: pytest, offline (socket guard), fixtures in `cli/tests/fixtures/datasets/`.
**Target Platform**: macOS/Linux CLI; Fly.io image build (prebuild).
**Performance Goals**: `map build living-planet` < 60 s, peak RSS ≤ 1 GB on real data (SC-002).
**Constraints**: no committed downloads; reads stream (strip/step at a time).
**Scale/Scope**: 2 new registry entries, 1 recipe, ~6 library modules touched, 3 web variants.

## Constitution Check

| Principle | Check |
|---|---|
| I Fixed template | Grid, mask, parts unchanged; only colors vary (White and Black are 98138/6141 colors in `part_colors.json`). Pass |
| II Recipes | Map fully described by `living-planet.toml`; new keys are declarative (`transform`, `no_data`). Pass |
| III Data in | Gridded NPP and chlorophyll, reprojected and classified. Pass |
| IV Reproducible data | Both datasets pinned (URL, version, size, checksum) and cached; ERDDAP by content checksum (R2), NTSG over HTTP with SHA-256 (R3); citations and licenses in outputs; offline once cached. Pass (two documented registry extensions; owner review logged) |
| V Honest outputs | Every color exists for its part; suitability report keeps the ΔE warning; extras reported. Pass |
| VI CLI first | All in the library + `map build`; the web only prebuilds with the library. Pass |
| VII Test first, offline | Tests written before each change; derived fixtures with `.source.json`. Pass |
| VIII LEGO compliance | Disclaimer in recipe, outputs, docs. Pass |

No violations; Complexity Tracking empty.

## Project Structure

```
cli/src/lego_image_processor/
  datasets/geotiff.py      (new) strip reader + block mean
  datasets/readers.py      latitude/longitude, climatology-mean, content checksum, log10, land_from
  datasets/registry.py     geotiff, block, http_only, content_sha256, land_from, climatology-mean
  datasets/cache.py        content verification
  datasets/grid.py         SourceGrid.counts/steps/missing, extend_latitudes
  maps/recipe.py           transform log10, no_data table, bounds in data units
  maps/nodata.py           (new) no-data rules on the kit grid
  maps/reproject.py        cell aggregation helper (max / mean of an indicator)
  maps/build.py            no-data cells, provenance, report
  cli/map.py               print no-data block
  maps/recipes/living-planet.toml (new)
  data/datasets.json       two rows
cli/tools/fixtures004/make_fixtures.py   make_npp, make_chla
cli/tests/...             unit, integration, contract
web/src/web98138/__init__.py   MAP_IDS
docs, README, CLAUDE.md, AGENTS.md
```

## Phases

0. Research (`research.md`): R1 GeoTIFF strip decoding, R2 ERDDAP pinning, R3 HTTP exception, R4
   land split, R5 no-data rules vs prototype, R6 fixtures.
1. Design: `data-model.md`, `contracts/recipe-format-012.md`, `contracts/datasets-012.md`,
   `quickstart.md`.
2. Tasks: `tasks.md`.

## Complexity Tracking

(none)

Not affiliated with or endorsed by The LEGO Group.

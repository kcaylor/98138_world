# Data model: Rainfall map (013)

Not affiliated with or endorsed by The LEGO Group.

- **DatasetFile** (`datasets/registry.py`): `url`, `size`, `sha256`; `name` = URL basename.
- **DatasetEntry** gains `files: Tuple[DatasetFile, ...]` (empty for single-file entries) and
  `files_sha256` (SHA-256 of `"<sha256>  <name>\n"` lines). `size` is the total for multi-file
  entries; `format` may be `netcdf4`. Provenance adds `files` and `files_sha256`.
- **SourceGrid** gains `points: bool`. A points grid has 1-D `values`, `lat`, `lon` of one length
  (and optional `counts`); regular grids are unchanged.
- **Region** (`maps/recipe.py`): optional `lat_min`, `lat_max`, `lon_min`, `lon_max` (strict).
- **Override**: `name`, `color`, and either `region` + `exclude` (regions) or `dataset`,
  `variable`, `min_value`, optional `unobserved_lat`. `kind` = region | dataset.
- **Legend**: `units`, `factor` (> 0).
- **Layer** gains `sampling` (mean | bilinear), `overrides`, `legend`.
- Build classes: override *i* is coded `-10 - i` (`override_class(i)`); no-data stays −2.
- Report layer gains `overrides` (name, kind, color, rule fields, cells), `legend`, and `sampling`
  when not mean; layout metadata layers gain the same.

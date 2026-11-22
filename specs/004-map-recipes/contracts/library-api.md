# Contract: library API (004)

```python
from lego_image_processor.datasets import (
    DatasetEntry, load_registry, get_entry,            # registry
    cache_root, cached_path, is_cached, fetch, verify,  # cache (fetch(entry, *, cache_dir=None, opener=None))
    SourceGrid, read_dataset,                           # read_dataset(entry, path, variable) -> SourceGrid
    DatasetNotCachedError, ChecksumMismatchError,
)
from lego_image_processor.maps import (
    Recipe, Layer, load_recipe, parse_recipe, bundled_recipes, RecipeError,
    KitProjection, load_kit_projection,
    reproject_layer,        # (grid, projection, mask, cls) -> LayerField
    classify,               # (field_values, classification, colors, part_id) -> class index array
    apply_texture,          # (classes, values, layer, seed) -> class index array
    SuitabilityReport, check_recipe,
    MapResult, build_map,   # build_map(recipe, *, cache_dir=None) -> MapResult
    write_preview,          # (layout, path)
    agreement_with_official,
)
from lego_image_processor.kit import PartColor, load_part_colors, colors_for_part
```

- `fetch` is the only function that opens the network; `opener` is injectable (tests pass a fake).
- `build_map` never fetches; it raises `DatasetNotCachedError(entry_id)`. The CLI's
  `map build --fetch` calls `fetch` for each missing entry (`missing_datasets(recipe)`) first.
- `RecipeError` carries `path` (key path) and `rule`.
- `build_map` output layout passes `PositionPlacementGrid.from_json(layout.to_json())` round trip
  with `metadata.map` preserved.

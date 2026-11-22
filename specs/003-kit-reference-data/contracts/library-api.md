# Contract: Python library API

## New module `lego_image_processor.kit`

```python
from lego_image_processor.kit import (
    SourceDocument, Citation,
    KitColor, load_kit_colors,            # -> list[KitColor] (cached)
    KitElement, KitInventory, load_kit_inventory,   # (kit_id="31203") -> KitInventory
    Section, DesignGrid, load_official_design,      # (kit_id="31203") -> DesignGrid
    UnsupportedKitError,
)
```

- All loaders read package data only (`importlib.resources`), no network (FR-007), and are
  `functools.cache`d. Any `kit_id` other than "31203" raises `UnsupportedKitError` (subclass of
  `ValueError`, same message style as today).
- Loaders validate the rules in data-model.md on load and raise `ValueError` naming the file and
  rule on failure.
- `KitInventory.elements`, `.land_element()`, `.ocean_elements()`, `.by_role(role)`,
  `.supplied(color_key) -> int`, `.source`.
- `KitColor.key`, `.lego`, `.bricklink`, `.rebrickable` (`CatalogColor(name, id)`), `.rgb`,
  `.role`, `.element_id`, `.citations` (resolved `Citation` objects).
- `DesignGrid.color_at(x, y) -> str` (key), `.counts`, `.sections`, `.land_positions() -> set`,
  `.to_layout() -> PositionPlacementGrid` (schema 2.0, `source_image="official-31203-design"`).

## Changed: `lego_image_processor.layout`

| Item | Before | After |
|---|---|---|
| `PositionPlacement.part_type` | `"brick"`/`"tile"` | `"plate"`/`"tile"` |
| `PositionPlacement.lego_part_id` | `"3062b"`/`"98138"` | `"6141"`/`"98138"` |
| `PositionPlacementGrid(schema_version=)` default | `"1.0"` | `"2.0"` (`CURRENT_SCHEMA_VERSION`) |
| `PositionPlacementGrid.from_json` | accepts any | raises `LayoutSchemaError(ValueError)` unless `"2.0"`; message names found version and the regenerate command |
| `LayoutStatistics.land_brick_count` | | renamed `land_plate_count` |
| `LandSeaMask.get_part_type/get_lego_part_id` | brick/3062b | plate/6141 |
| `LEGOWorldMapKitSpecification` | brick fields, JSON-loaded | `available_colors_plate`, `available_colors_tile`, `plate_quantities`, `tile_quantities`; `is_plate_color_available`, `get_plate_quantity`; built by `load_kit_specification()` from inventory + colors |
| `LayoutValidator._find_nearest_color` | Euclidean RGB, all palette | CIEDE2000 (`core.color_quantizer.delta_e_2000`) against the kit colors of the affected part only; distance reported as ΔE00 |
| `ValidationReport.to_dict()` | | adds `"disclaimer"` |
| `ColorUnavailableViolation` / `QuantityExceededViolation` | | unchanged fields; `part_type` values plate/tile |

`QuantityExceededViolation` already carries needed (`positions_required`), supplied
(`kit_quantity`) and `shortfall` (FR-019).

## Changed: palette

`palette/lego_colors.json` gains `{"id": 107, "name": "Bright Bluish Green", "rgb": [0,143,155],
"hex": "#008F9B"}` (Rebrickable RGB, cited in the file's notes). RGBs of the other nine kit
colors are not changed by this feature (changing them would invalidate existing quantized images);
`kit_colors.json` carries the cited display RGBs separately.

Not affiliated with or endorsed by The LEGO Group.

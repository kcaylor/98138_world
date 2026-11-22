# Contract: library API (005)

```python
from lego_image_processor.kit.part_numbers import load_part_numbers, PartNumbers
from lego_image_processor.parts import (
    resolve_color,          # (part_id, color_key, lego_color_code) -> ResolvedColor | Unresolved(reason)
    parse_owned_csv,        # (path) -> OwnedFile(rows, ignored_rows, sha256); raises OwnedFileError(path, line, msg)
    OwnedInputs,            # kits, owned_files, missing_files, spares_percent (Fraction)
    build_parts_list,       # (layout: PositionPlacementGrid, layout_path, owned: OwnedInputs, kit_id="31203") -> PartsList
    to_bricklink_xml,       # (parts_list, condition: Optional["N"|"U"]=None, allow_partial=False) -> Optional[str]
    to_rebrickable_csv,     # (parts_list, allow_partial=False) -> Optional[str]
    UnverifiedLotsError,    # raised by exporters when unverified lots exist and allow_partial is False
)
PartsList.to_json() -> str  # contracts/parts-list-format.md
KitInventory.supplied_for(part_id, color_key) -> int   # research R11
```

Exporters return `None` when nothing is to buy. Feature 006 uses `resolve_color` for its legend.

# Contract: library API (006)

```python
from lego_image_processor.sheets import (
    sections,            # () -> tuple[Section, ...]  (40, A1..H5)
    section_counts,      # (layout, parts_list=None, layout_path=None, layout_sha256=None) -> SectionCounts; .to_json()
    build_legend,        # (parts_list) -> tuple[LegendEntry, ...]
    build_sheet_set,     # (layout, layout_path=None, paper="letter", sections=None, title=None,
                         #  layout_sha256=None) -> SheetSet; raises SheetError (ValueError)
    render_pdf,          # (sheet_set) -> bytes  (ReportLab, invariant); ValueError if the title is not Latin-1
    render_svg,          # (sheet_set) -> list[tuple[str, str]]  (filename, svg text)
)
```

`layout` is a 005 `LayoutInput` (from `read_layout`) or a `PositionPlacementGrid`; it must hold all
10,240 positions. `build_sheet_set` calls 005 `build_parts_list(layout, layout_path, OwnedInputs())` for lot order and
IDs.

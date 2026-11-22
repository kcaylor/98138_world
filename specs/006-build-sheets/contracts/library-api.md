# Contract: library API (006)

```python
from lego_image_processor.sheets import (
    sections,            # () -> tuple[Section, ...]  (40, A1..H5)
    section_counts,      # (layout, parts_list) -> SectionCounts; .to_json()
    build_legend,        # (parts_list) -> tuple[LegendEntry, ...]
    build_sheet_set,     # (layout, layout_path, paper="letter", sections=None, title=None) -> SheetSet
    render_pdf,          # (sheet_set) -> bytes  (ReportLab, invariant)
    render_svg,          # (sheet_set) -> list[tuple[str, str]]  (filename, svg text)
)
```

`build_sheet_set` calls 005 `build_parts_list(layout, layout_path, OwnedInputs())` for lot order and
IDs.

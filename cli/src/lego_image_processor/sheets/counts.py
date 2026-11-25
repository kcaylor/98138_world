"""Per-section piece counts (006 FR-013, contracts/counts-format.md).

For each of the 40 sections: the count per lot number (005 lot order). Used by the section pages,
``sheets counts`` and the planned web app (for example to sort pieces into 40 bags). A layout on a
non-kit template (feature 016) counts its margin's square tiles like any lot and names the template.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from ..kit.source import DISCLAIMER
from ..layout.grid import PositionPlacementGrid
from ..parts import LayoutInput, PartsList, build_parts_list
from .legend import LegendEntry, build_legend, lot_numbers
from ..layout.arrangement import arrangement_of
from .sections import Section, arranged_sections, section_for

FORMAT_VERSION = "1"


@dataclass(frozen=True)
class SectionCount:
    section: Section
    counts: Dict[int, int]

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    def to_dict(self) -> Dict[str, Any]:
        s = self.section
        return {"label": s.label, "col": s.col, "row": s.row, "x": list(s.x_range),
                "y": list(s.y_range), "frame": s.frame, "kit_label": s.kit_label,
                "counts": {str(k): v for k, v in self.counts.items()}, "total": self.total}


@dataclass(frozen=True)
class SectionCounts:
    layout: Dict[str, Any]
    legend: Tuple[LegendEntry, ...]
    sections: Tuple[SectionCount, ...]
    kit_id: str = "31203"
    arrangement: str = "A"

    @property
    def template(self) -> Optional[Dict[str, Any]]:
        """``{id, title}`` of a non-kit layout's template (feature 016); None on the kit."""
        return self.layout.get("template")

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "format_version": FORMAT_VERSION,
            "kit": self.kit_id,
            "arrangement": self.arrangement,
        }
        if self.template is not None:  # feature 016: non-kit layouts only (kit JSON unchanged)
            out["template"] = dict(self.template)
        out.update({
            "layout": {"path": self.layout.get("path"), "sha256": self.layout.get("sha256"),
                       "source_image": self.layout.get("source_image")},
            "legend": [{"number": e.number, "part_id": e.lot.part_id, "part_type": e.lot.part_type,
                        "color_key": e.lot.color_key, "name": e.name, "verified": e.verified,
                        "total": e.lot.needed} for e in self.legend],
            "sections": [s.to_dict() for s in self.sections],
            "disclaimer": DISCLAIMER,
        })
        return out

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n"


def count_sections(grid: PositionPlacementGrid,
                   legend: Tuple[LegendEntry, ...]) -> Tuple[SectionCount, ...]:
    """Counts per section as hung in the layout's arrangement (feature 007)."""
    arrangement = arrangement_of(grid)
    numbers = lot_numbers(legend)
    secs = arranged_sections(arrangement)
    per: Dict[str, Counter] = {s.label: Counter() for s in secs}
    for p in grid.positions:
        per[section_for(p.x, p.y, arrangement).label][numbers[(p.lego_part_id, p.color_id)]] += 1
    return tuple(SectionCount(section=s, counts=dict(sorted(per[s.label].items()))) for s in secs)


def section_counts(layout: Union[LayoutInput, PositionPlacementGrid],
                   parts_list: Optional[PartsList] = None,
                   layout_path: Optional[Union[str, Path]] = None,
                   layout_sha256: Optional[str] = None) -> SectionCounts:
    """Counts per section and lot for a layout (lot numbers from the 005 parts list)."""
    if parts_list is None:
        parts_list = build_parts_list(layout, layout_path, layout_sha256=layout_sha256)
    grid = layout.grid if isinstance(layout, LayoutInput) else layout
    legend = build_legend(parts_list)
    lay = dict(parts_list.layout)
    if layout_path is not None:
        lay["path"] = str(layout_path)
    if layout_sha256 is not None:
        lay["sha256"] = layout_sha256
    return SectionCounts(layout=lay, legend=legend, sections=count_sections(grid, legend),
                         kit_id=parts_list.kit_id, arrangement=arrangement_of(grid).id)

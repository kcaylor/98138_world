"""The kit's 40 section bases: 8 columns x 5 rows of 16 x 16 positions (006 FR-001).

Labels are a column letter A-H (west to east) and a row number 1-5 (north to south). Sections are
ordered column by column (A1 ... A5, B1 ... H5), the order of the kit's section instruction pages
recorded by feature 003 in ``kit_31203_design.json``. The instructions' page numbers are used only
to cite that order; nothing from the instructions is drawn.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Optional, Tuple, Union

from ..kit.design import SECTION_SIZE, load_official_design

COLUMNS = "ABCDEFGH"
N_COLS, N_ROWS = 8, 5
GRID_WIDTH, GRID_HEIGHT = N_COLS * SECTION_SIZE, N_ROWS * SECTION_SIZE
# The three frames split the board after section columns B and F (003 projection notes).
FRAME_COLUMNS = ((0, 1), (2, 3, 4, 5), (6, 7))
FRAME_BOUNDARIES = (32, 96)
VALID_RANGE = "A1-H5 (columns A-H, rows 1-5)"


@dataclass(frozen=True)
class Section:
    label: str
    col: int
    row: int
    x_range: Tuple[int, int]
    y_range: Tuple[int, int]
    frame: int
    instruction_page: int
    order: int

    def contains(self, x: int, y: int) -> bool:
        return self.x_range[0] <= x <= self.x_range[1] and self.y_range[0] <= y <= self.y_range[1]


def frame_for_column(col: int) -> int:
    for i, cols in enumerate(FRAME_COLUMNS, start=1):
        if col in cols:
            return i
    raise ValueError(f"section column {col} is outside 0-{N_COLS - 1}")


@lru_cache(maxsize=None)
def sections() -> Tuple[Section, ...]:
    """The 40 sections in build order A1 ... H5 (validated against the 128 x 80 grid)."""
    design = load_official_design()
    raw = sorted(design.sections, key=lambda s: s.page)
    out = []
    for i, s in enumerate(raw, start=1):
        out.append(Section(label=f"{COLUMNS[s.col]}{s.row + 1}", col=s.col, row=s.row,
                           x_range=(SECTION_SIZE * s.col, SECTION_SIZE * s.col + SECTION_SIZE - 1),
                           y_range=(SECTION_SIZE * s.row, SECTION_SIZE * s.row + SECTION_SIZE - 1),
                           frame=frame_for_column(s.col), instruction_page=s.page, order=i))
    if [(s.col, s.row) for s in out] != [(c, r) for c in range(N_COLS) for r in range(N_ROWS)]:
        raise ValueError("kit_31203_design.json: section pages do not run column by column")
    if (design.width, design.height) != (GRID_WIDTH, GRID_HEIGHT):
        raise ValueError("kit_31203_design.json: grid is not 128 x 80")
    return tuple(out)


def section_for(x: int, y: int) -> Section:
    if not (0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT):
        raise ValueError(f"position ({x}, {y}) is outside the {GRID_WIDTH} x {GRID_HEIGHT} grid")
    col, row = x // SECTION_SIZE, y // SECTION_SIZE
    return sections()[col * N_ROWS + row]


def parse_section_labels(value: Optional[Union[str, Iterable[str]]]) -> Tuple[Section, ...]:
    """Sections named in ``value`` (comma-separated text or labels), in board order; None = all."""
    if value is None:
        return sections()
    parts = value.split(",") if isinstance(value, str) else list(value)
    labels = [p.strip().upper() for p in parts if p and p.strip()]
    if not labels:
        raise ValueError(f"no section labels given; valid labels are {VALID_RANGE}")
    by_label = {s.label: s for s in sections()}
    unknown = [l for l in dict.fromkeys(labels) if l not in by_label]
    if unknown:
        raise ValueError(f"unknown section label(s) {', '.join(unknown)}; valid labels are {VALID_RANGE}")
    wanted = set(labels)
    return tuple(s for s in sections() if s.label in wanted)

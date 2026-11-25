"""Compose a build-sheet set as page models (006 US1, US2, US4; contracts/page-layout.md).

A set is an overview page, legend pages and one page per section, all portrait with 12 mm
margins. Section grids are drawn at true scale: 8.0 mm stud pitch (LDraw: 1 brick width = 20 LDU,
1 LDU = 0.4 mm, both stated there as approximations). Every page carries a 100 mm scale bar, the
footer "Page n of N" and the disclaimer. Pages are built only from the layout and cited data with
circles, rectangles, lines and text: no image, artwork, logo or crop from LEGO instructions.
A layout on a non-kit template (feature 016, ``metadata.template``) uses the same 40 sections and
frames, hung as A; its margin studs, 1x1 square tiles, are drawn as squares, and the overview names
the template, says the frames cannot be re-hung and cites the template's file and dataset. Kit
layouts are drawn exactly as before.
A layout with an in-margin plaque (feature 017, ``metadata.plaque``; contracts/in-margin-plaque.md
"Build sheets and counts") lacks exactly the plaque's studs: its section page draws one Black
rectangle outlined 0.4 mm over them, labelled with the tile and its lot number, and counts the lot
once; the legend gives it a square swatch, the overview map draws the rectangle and the totals line
names the tile. Layouts without a plaque are drawn as before.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from reportlab.pdfbase.pdfmetrics import stringWidth

from .. import __version__
from ..kit.source import DISCLAIMER
from ..layout.grid import PositionPlacementGrid
from ..parts import ACKNOWLEDGEMENT, LayoutInput, LayoutInputError, PartsList, build_parts_list
from ..parts.partslist import PART_TYPE_TEXT, PLAQUE_PART_TYPE, check_grid
from ..templates import REHANG_RULE
from .counts import SectionCount, count_sections, plaque_section
from .legend import LegendEntry, build_legend, lot_numbers, text_color
from .model import (BLACK, GREY, OUTLINE, PT_MM, RGB, WHITE, Circle, Item, Line, Page, PageSize,
                    Rect, Text, latin1_safe, paper_size)
from ..layout.arrangement import Arrangement, arrangement_of, load_arrangements, parse_arrangement
from .sections import (COLUMNS, GRID_HEIGHT, GRID_WIDTH, N_COLS, N_ROWS, Section,
                       arranged_sections, parse_section_labels)

MARGIN = 12.0
PITCH = 8.0
STUD_D = 7.0
RING_RATIO = 0.6
MAP_PITCH = 1.4
SCALE_BAR_MM = 100.0
PRINT_NOTE = "Print at 100% (no fit-to-page)"
SUBTITLE = "LEGO World Map 31203 template: 128 x 80 studs, 40 sections"
# Feature 016: a non-kit template's subtitle (it names the template; the frames are not re-hung).
TEMPLATE_SUBTITLE = "Template {id}: 128 x 80 studs, 40 sections of kit 31203; the frames cannot be re-hung"
LEGEND_NOTE = ("Lot numbers are printed on the studs. Plates (land) have a ring, tiles (ocean) are "
               "plain. Totals are for the whole map.")
LEGEND_NOTE_SQUARES = ("Lot numbers are on the studs. Plates (land) have a ring, tiles (ocean) are "
                       "plain, margin tiles are square. Totals are for the whole map.")
TOOL = "lego-image-processor"
FULL_POSITIONS = GRID_WIDTH * GRID_HEIGHT
DARK: RGB = (60, 60, 60)
SOFT: RGB = (90, 90, 90)
FAINT: RGB = (200, 200, 200)
MAP_BG: RGB = (225, 225, 225)
WARN: RGB = (200, 30, 30)
CONTENT_BOTTOM = 24.0  # mm above the page's bottom edge: scale bar and footer live below
LEGEND_TOP = 37.0
LEGEND_ROW = 9.0
COUNT_ROW = 5.5
PLAQUE_OUTLINE = 0.4  # mm, the in-margin plaque's outline on a section page (feature 017)
MAP_STUD_R = 0.6


class SheetError(ValueError):
    """The layout or options cannot make a sheet set (CLI exit 1)."""


@dataclass(frozen=True)
class SheetSet:
    title: str
    layout: Dict[str, Any]
    legend: Tuple[LegendEntry, ...]
    pages: Tuple[Page, ...]
    paper: PageSize
    sections: Tuple[Section, ...]
    counts: Tuple[SectionCount, ...]
    parts_list: PartsList
    map_metadata: Optional[Dict[str, Any]] = None
    plaque: Optional["PlaqueMark"] = None  # feature 017: the in-margin plaque, when the layout has one

    @property
    def page_kinds(self) -> Dict[str, int]:
        out = {"overview": 0, "legend": 0, "section": 0}
        for p in self.pages:
            out[p.kind] += 1
        return out


# --- text helpers -------------------------------------------------------------------------------

def text_width(text: str, size_pt: float, bold: bool = False) -> float:
    """Width in mm of ``text`` in Helvetica (standard font metrics; no font file needed)."""
    font = "Helvetica-Bold" if bold else "Helvetica"
    return stringWidth(latin1_safe(text), font, size_pt) * PT_MM


def fit(text: str, size_pt: float, width_mm: float, bold: bool = False) -> str:
    """``text`` shortened with "..." to fit ``width_mm``."""
    if text_width(text, size_pt, bold) <= width_mm:
        return text
    while text and text_width(text + "...", size_pt, bold) > width_mm:
        text = text[:-1]
    return text.rstrip() + "..."


def wrap(text: str, size_pt: float, width_mm: float, bold: bool = False) -> List[str]:
    lines: List[str] = []
    line = ""
    for word in text.split(" "):
        trial = word if not line else f"{line} {word}"
        if line and text_width(trial, size_pt, bold) > width_mm:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return [fit(l, size_pt, width_mm, bold) for l in lines] or [""]


def cap_offset(size_pt: float) -> float:
    """Baseline offset (mm) that centres Helvetica digits on a point (cap height 0.718 em)."""
    return 0.718 * size_pt * PT_MM / 2


def d(**kw: Any) -> Tuple[Tuple[str, str], ...]:
    return tuple((k, str(v)) for k, v in kw.items())


# --- shared page furniture ----------------------------------------------------------------------

def furniture(size: PageSize, title: str, number: int, total: int) -> List[Item]:
    """Scale bar, print note and footer, on every page (FR-006, FR-008)."""
    W, H = size.width_mm, size.height_mm
    x0, y = MARGIN, H - 18.0
    items: List[Item] = [Line(x0, y, x0 + SCALE_BAR_MM, y, BLACK, 0.35, tag="scale-bar")]
    for i in range(11):
        tall = i in (0, 5, 10)
        items.append(Line(x0 + 10 * i, y, x0 + 10 * i, y - (2.4 if tall else 1.3), BLACK, 0.25,
                          tag="scale-tick"))
    for i, label in ((0, "0"), (5, "50"), (10, "100 mm")):
        items.append(Text(x0 + 10 * i, y + 3.2, label, 6.5, "center", tag="scale-label"))
    items.append(Text(x0 + SCALE_BAR_MM + 6, y - 0.6, PRINT_NOTE, 8.5, bold=True, tag="print-note"))
    items.append(Text(x0 + SCALE_BAR_MM + 6, y + 3.2, "The bar should measure 100 mm.", 7,
                      color=SOFT, tag="print-note"))
    half = (W - 2 * MARGIN) / 2 - 4
    items.append(Line(MARGIN, H - 13.6, W - MARGIN, H - 13.6, FAINT, 0.2, tag="footer-rule"))
    items.append(Text(MARGIN, H - 10.0, fit(title, 7.5, half), 7.5, tag="footer-title"))
    items.append(Text(W - MARGIN, H - 10.0, f"Page {number} of {total}", 7.5, "right",
                      tag="footer-page"))
    items.append(Text(W / 2, H - 6.5, DISCLAIMER, 7.5, "center", tag="disclaimer"))
    return items


def is_square(entry: LegendEntry) -> bool:
    """A 1x1 square tile (a template's margin, feature 016): drawn as a square, not a circle."""
    return entry.lot.part_type == "square_tile"


def is_plaque(entry: LegendEntry) -> bool:
    """The in-margin plaque's tile (feature 017): one rectangle over its studs, a square swatch."""
    return entry.lot.part_type == PLAQUE_PART_TYPE


@dataclass(frozen=True)
class PlaqueMark:
    """The in-margin plaque on the sheets (feature 017): its studs (top-left ``row``/``col`` in
    0-based board coordinates as hung, ``height`` x ``width``), its legend entry and its section."""

    row: int
    col: int
    height: int
    width: int
    entry: LegendEntry
    section: str

    @property
    def label(self) -> str:
        """``tile 6x6 (10202)``: the part label (``PART_LABEL``) and the part."""
        return f"{self.entry.part_label} ({self.entry.lot.part_id})"


def plaque_items(mark: PlaqueMark, x: float, y: float) -> List[Item]:
    """The plaque at true scale with its top-left stud's cell at (``x``, ``y``): one rectangle 6
    pitches minus the stud gap wide (as the preview), outlined, with its lot number and label."""
    gap = PITCH - STUD_D
    e = mark.entry
    rx, ry = x + gap / 2, y + gap / 2
    w, h = mark.width * PITCH - gap, mark.height * PITCH - gap
    cx, cy = rx + w / 2, ry + h / 2
    return [Rect(rx, ry, w, h, e.rgb, OUTLINE, PLAQUE_OUTLINE, tag="plaque",
                 data=d(x=mark.col, y=mark.row, width=mark.width, height=mark.height, lot=e.number)),
            Text(cx, cy - 1.0, str(e.number), 16, "center", True, e.text_color, tag="plaque-number",
                 data=d(lot=e.number)),
            Text(cx, cy + 5.0, mark.label, 9, "center", False, e.text_color, tag="plaque-label",
                 data=d(lot=e.number))]


def stud(cx: float, cy: float, entry: LegendEntry, r: float, number_size: float,
         x: int, y: int) -> List[Item]:
    if is_square(entry):
        out: List[Item] = [Rect(cx - r, cy - r, 2 * r, 2 * r, entry.rgb, OUTLINE, 0.2, tag="stud",
                                data=d(x=x, y=y, lot=entry.number))]
    else:
        out = [Circle(cx, cy, r, entry.rgb, OUTLINE, 0.2, tag="stud", data=d(x=x, y=y, lot=entry.number))]
    if entry.lot.part_type == "plate":
        out.append(Circle(cx, cy, r * RING_RATIO, None, entry.text_color, 0.25, tag="ring",
                          data=d(x=x, y=y)))
    size = number_size if entry.number < 100 else number_size * 0.75
    out.append(Text(cx, cy + cap_offset(size), str(entry.number), size, "center", True,
                    entry.text_color, tag="stud-number", data=d(x=x, y=y)))
    return out


def disc(cx: float, cy: float, r: float, entry: LegendEntry, size: float, tag: str) -> List[Item]:
    """A lot's swatch with its number: a disc, or a square for a square tile or the plaque tile."""
    if is_square(entry) or is_plaque(entry):
        out: List[Item] = [Rect(cx - r, cy - r, 2 * r, 2 * r, entry.rgb, OUTLINE, 0.2, tag=tag,
                                data=d(lot=entry.number))]
    else:
        out = [Circle(cx, cy, r, entry.rgb, OUTLINE, 0.2, tag=tag, data=d(lot=entry.number))]
    if entry.lot.part_type == "plate":
        out.append(Circle(cx, cy, r * RING_RATIO, None, entry.text_color, 0.2, tag=tag + "-ring"))
    if entry.number >= 100:
        size *= 0.75
    out.append(Text(cx, cy + cap_offset(size), str(entry.number), size, "center", True,
                    entry.text_color, tag=tag + "-number"))
    return out


def frame_names() -> Dict[int, str]:
    return {f.number: f.name for f in load_arrangements().frames}


def locator(x0: float, y0: float, current: Section, cell: float = 4.0,
            arrangement: Optional[Arrangement] = None) -> List[Item]:
    arrangement = arrangement or parse_arrangement(None)
    items: List[Item] = []
    for s in arranged_sections(arrangement):
        on = s.label == current.label
        items.append(Rect(x0 + s.col * cell, y0 + s.row * cell, cell, cell, DARK if on else WHITE,
                          SOFT, 0.15, tag="locator", data=d(label=s.label, on=int(on))))
    for c in range(N_COLS):
        items.append(Text(x0 + (c + 0.5) * cell, y0 - 0.9, COLUMNS[c], 5.5, "center",
                          tag="locator-label"))
    for r in range(N_ROWS):
        items.append(Text(x0 - 1.0, y0 + (r + 0.5) * cell + cap_offset(5.5), str(r + 1), 5.5,
                          "right", tag="locator-label"))
    for b in arrangement.boundaries():
        xb = x0 + (b // 16) * cell
        items.append(Line(xb, y0, xb, y0 + N_ROWS * cell, BLACK, 0.6, tag="locator-frame"))
    return items


# --- section page (US1) -------------------------------------------------------------------------

def section_page(size: PageSize, section: Section, grid_cells: Dict[Tuple[int, int], LegendEntry],
                 count: SectionCount, legend: Sequence[LegendEntry], title: str, number: int,
                 total: int, arrangement: Optional[Arrangement] = None,
                 plaque: Optional[PlaqueMark] = None) -> Page:
    """One section at true scale; ``plaque`` (feature 017) when it holds the in-margin plaque,
    whose studs have no cell."""
    arrangement = arrangement or parse_arrangement(None)
    W, H = size.width_mm, size.height_mm
    items: List[Item] = []
    s = section
    items.append(Text(MARGIN, 21.0, f"Section {s.label}", 20, bold=True, tag="section-title"))
    where = (f"columns {s.x_range[0]}-{s.x_range[1]}, rows {s.y_range[0]}-{s.y_range[1]} · "
             f"frame {s.frame} of 3 ({frame_names()[s.frame]})")
    if s.kit_label and s.kit_label != s.label:
        where += f" · kit section {s.kit_label}"
    items.append(Text(MARGIN, 28.0, fit(where, 9.5, W - 2 * MARGIN - 40.0), 9.5, tag="section-range"))
    order = (f"Base {s.order} of 40 in build order (column by column, as in the kit's "
             "instructions). North is up.")
    if arrangement.column_shift:
        order = (f"Base {s.order} of 40 as hung in combination {arrangement.id} (column by column). "
                 "North is up.")
    items.append(Text(MARGIN, 33.0, fit(order, 7.5, W - 2 * MARGIN - 40.0), 7.5, color=SOFT,
                      tag="section-order"))
    items += locator(W - MARGIN - 32.0, 15.0, s, arrangement=arrangement)

    x0 = (W - 16 * PITCH) / 2
    y0 = 44.0
    items.append(Rect(x0, y0, 16 * PITCH, 16 * PITCH, None, FAINT, 0.2, tag="grid-border"))
    for i in range(16):
        x = s.x_range[0] + i
        items.append(Text(x0 + (i + 0.5) * PITCH, y0 - 1.6, str(x), 6, "center", tag="col-coord"))
        y = s.y_range[0] + i
        items.append(Text(x0 - 1.6, y0 + (i + 0.5) * PITCH + cap_offset(6), str(y), 6, "right",
                          tag="row-coord"))
    for j in range(16):
        for i in range(16):
            x, y = s.x_range[0] + i, s.y_range[0] + j
            e = grid_cells.get((x, y))
            if e is None:  # under the in-margin plaque (feature 017; build_sheet_set checks it)
                continue
            items += stud(x0 + (i + 0.5) * PITCH, y0 + (j + 0.5) * PITCH, e, STUD_D / 2, 8.0, x, y)
    if plaque is not None:
        items += plaque_items(plaque, x0 + (plaque.col - s.x_range[0]) * PITCH,
                              y0 + (plaque.row - s.y_range[0]) * PITCH)

    # Count table: the section's lots in lot order, column-major.
    by_number = {e.number: e for e in legend}
    ty = y0 + 16 * PITCH + 9.0
    items.append(Text(MARGIN, ty, f"Pieces in section {s.label}", 10, bold=True, tag="count-title"))
    items.append(Text(W - MARGIN, ty, f"Total {count.total}", 10, "right", True, tag="count-total"))
    items.append(Line(MARGIN, ty + 1.5, W - MARGIN, ty + 1.5, FAINT, 0.2, tag="count-rule"))
    top = ty + 3.0
    rows = max(1, int((H - CONTENT_BOTTOM - top) // COUNT_ROW))
    lots = list(count.counts.items())
    cols = max(2, math.ceil(len(lots) / rows))
    col_w = (W - 2 * MARGIN) / cols
    for k, (num, n) in enumerate(lots):
        e = by_number[num]
        cx = MARGIN + (k // rows) * col_w
        ry = top + (k % rows) * COUNT_ROW
        items += disc(cx + 2.5, ry + 2.6, 2.3, e, 6.5, "count-disc")
        name = fit(f"{e.name} ({PART_TYPE_TEXT[e.lot.part_type]})", 8, col_w - 6.5 - 12)
        items.append(Text(cx + 6.5, ry + 3.6, name, 8, tag="count-name", data=d(lot=num)))
        items.append(Text(cx + col_w - 4, ry + 3.6, str(n), 8, "right", True, tag="count",
                          data=d(lot=num)))
    items += furniture(size, title, number, total)
    return Page(size=size, items=tuple(items), number=number, total=total, kind="section",
                label=s.label)


# --- overview page (US2) ------------------------------------------------------------------------

class Flow:
    """Wrapped text lines placed downwards from ``y`` until ``bottom``."""

    def __init__(self, x: float, y: float, width: float, bottom: float):
        self.x, self.y, self.width, self.bottom = x, y, width, bottom
        self.items: List[Item] = []
        self.full = False

    def para(self, text: str, size: float = 8.5, bold: bool = False, color: RGB = BLACK,
             tag: str = "text", gap: float = 0.8) -> None:
        step = size * PT_MM * 1.3
        for line in wrap(text, size, self.width, bold):
            if self.y + step > self.bottom:
                if not self.full:
                    self.items.append(Text(self.x, self.y, "(more in the parts list JSON)", 7,
                                           color=SOFT, tag="text"))
                self.full = True
                return
            self.y += step
            self.items.append(Text(self.x, self.y, line, size, bold=bold, color=color, tag=tag))
        self.y += gap


def overview_page(size: PageSize, title: str, grid: PositionPlacementGrid,
                  cells: Dict[Tuple[int, int], LegendEntry], legend: Sequence[LegendEntry],
                  layout: Dict[str, Any], map_meta: Optional[Dict[str, Any]], n_legend_pages: int,
                  chosen: Sequence[Section], total: int,
                  arrangement: Optional[Arrangement] = None, plaque: Optional[PlaqueMark] = None) -> Page:
    arrangement = arrangement or parse_arrangement(None)
    template = getattr(grid, "template", None)  # feature 016: None on the kit template
    bounds = arrangement.boundaries()
    W, H = size.width_mm, size.height_mm
    items: List[Item] = []
    for i, line in enumerate(wrap(title, 18, W - 2 * MARGIN, True)[:2]):
        items.append(Text(MARGIN, 21.0 + i * 7.0, line, 18, bold=True, tag="title"))
    shift = 7.0 if len(wrap(title, 18, W - 2 * MARGIN, True)) > 1 else 0.0
    subtitle = SUBTITLE if template is None else fit(TEMPLATE_SUBTITLE.format(id=template.get("id")),
                                                     9.5, W - 2 * MARGIN)
    items.append(Text(MARGIN, 27.5 + shift, subtitle, 9.5, tag="subtitle"))

    mw, mh = GRID_WIDTH * MAP_PITCH, GRID_HEIGHT * MAP_PITCH
    x0, y0 = (W - mw) / 2, 38.0 + shift
    items.append(Rect(x0, y0, mw, mh, MAP_BG, None, 0, tag="map-bg"))
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            e = cells.get((x, y))
            if e is None:  # under the in-margin plaque (feature 017)
                continue
            cx, cy = x0 + (x + 0.5) * MAP_PITCH, y0 + (y + 0.5) * MAP_PITCH
            if is_square(e):
                items.append(Rect(cx - MAP_STUD_R, cy - MAP_STUD_R, 2 * MAP_STUD_R, 2 * MAP_STUD_R, e.rgb, None, 0,
                                  tag="map-stud"))
            else:
                items.append(Circle(cx, cy, MAP_STUD_R, e.rgb, None, 0, tag="map-stud"))
            if e.lot.part_type == "plate":
                items.append(Circle(cx, cy, 0.33, None, GREY, 0.1, tag="map-ring"))
    if plaque is not None:  # one rectangle, as on its section page (stud gap as between map studs)
        gap = MAP_PITCH - 2 * MAP_STUD_R
        items.append(Rect(x0 + plaque.col * MAP_PITCH + gap / 2, y0 + plaque.row * MAP_PITCH + gap / 2,
                          plaque.width * MAP_PITCH - gap, plaque.height * MAP_PITCH - gap, plaque.entry.rgb,
                          None, 0, tag="map-plaque", data=d(lot=plaque.entry.number)))
    sec = 16 * MAP_PITCH
    for c in range(1, N_COLS):
        if c * 16 not in bounds:
            items.append(Line(x0 + c * sec, y0, x0 + c * sec, y0 + mh, SOFT, 0.2, tag="section-line"))
    for r in range(1, N_ROWS):
        items.append(Line(x0, y0 + r * sec, x0 + mw, y0 + r * sec, SOFT, 0.2, tag="section-line"))
    for b in bounds:
        items.append(Line(x0 + b * MAP_PITCH, y0, x0 + b * MAP_PITCH, y0 + mh, BLACK, 0.8,
                          tag="frame-line"))
    items.append(Rect(x0, y0, mw, mh, None, BLACK, 0.4, tag="map-border"))
    for c in range(N_COLS):
        items.append(Text(x0 + (c + 0.5) * sec, y0 - 1.5, COLUMNS[c], 8, "center", True,
                          tag="map-col-label"))
    for r in range(N_ROWS):
        items.append(Text(x0 - 1.5, y0 + (r + 0.5) * sec + cap_offset(8), str(r + 1), 8, "right",
                          True, tag="map-row-label"))

    for f, start, end in arrangement.frame_spans():
        items.append(Text(x0 + (start + end + 1) / 2 * MAP_PITCH, y0 + mh + 3.6,
                          f"Frame {f.number}: {f.name}", 7.5, "center", True, tag="frame-label",
                          data=d(frame=f.number)))

    flow = Flow(MARGIN, y0 + mh + 5.0, W - 2 * MARGIN, H - CONTENT_BOTTOM)
    plates = sum(e.lot.needed for e in legend if e.lot.part_type == "plate")
    tiles = sum(e.lot.needed for e in legend if e.lot.part_type == "tile")
    unverified = [e for e in legend if not e.verified]
    lots = f"{len(legend)} lots ({len(legend) - len(unverified)} verified"
    lots += f", {len(unverified)} unverified)" if unverified else ")"
    if unverified:
        warn = (f"Warning: {len(unverified)} lot(s) without cited IDs (no verified LEGO, BrickLink "
                "or Rebrickable numbers); they are marked \"no cited IDs\" in the legend. Check "
                "them before ordering.")
        lines = wrap(warn, 8.5, W - 2 * MARGIN - 4, True)
        h = len(lines) * 8.5 * PT_MM * 1.3 + 3.0
        items.append(Rect(MARGIN, flow.y + 1.0, W - 2 * MARGIN, h, None, WARN, 0.6, tag="warning"))
        flow.x += 2.0
        flow.width -= 4.0
        flow.y += 1.5
        for line in lines:
            flow.para(line, 8.5, True, WARN, tag="warning-text", gap=0)
        flow.x -= 2.0
        flow.width += 4.0
        flow.y += 3.5
    squares = sum(e.lot.needed for e in legend if is_square(e))
    plaques = [e for e in legend if is_plaque(e)]  # feature 017: the in-margin plaque's tile
    pieces = (f"{plates + tiles + squares + sum(e.lot.needed for e in plaques):,} pieces: {plates:,} plates "
              f"1x1 round (land, part 6141), {tiles:,} tiles 1x1 round (ocean, part 98138)")
    if template is not None or squares:
        pieces += f", {squares:,} tiles 1x1 square (margin, part 3070b)"
    for e in plaques:
        pieces += f", {e.lot.needed:,} {e.part_label} (plaque, part {e.lot.part_id})"
    flow.para(f"{pieces}; {lots}.", 8.5, tag="totals")
    drawn = "Plates (land) are drawn with a ring, tiles (ocean) plain"
    if template is not None or squares:
        drawn += ", square tiles (margin) as squares"
    if plaques:
        drawn += ", the plaque tile as one outlined rectangle"
    labels = [s.label for s in chosen]
    which = "A1 to H5" if len(chosen) == 40 else ", ".join(labels)
    flow.para(f"This set: 1 overview page, {n_legend_pages} legend page(s), {len(chosen)} section "
              f"page(s) ({which}), column by column "
              + ("as in the kit's section instructions" if not arrangement.column_shift else "as hung")
              + ". Each "
              "section page is one 16 x 16 base at true size; the number on each stud is its lot "
              f"in the legend. {drawn}. Frames: "
              + ", ".join(f"{COLUMNS[s // 16]}-{COLUMNS[e // 16]} frame {f.number}"
                          for f, s, e in arrangement.frame_spans()) + ".", 8.5, tag="howto")
    order = "·".join(str(n) for n in arrangement.frame_order)
    src = load_arrangements().source
    citation = latin1_safe(src['citation'].replace('–', '-'))
    if template is None:
        flow.para(f"Combination {arrangement.id} ({arrangement.name}): frames {order} from left to right, "
                  f"{arrangement.centre} in the centre ({citation}). Sections are labelled as hung"
                  + ("." if not arrangement.column_shift else
                     "; each section page names its physical frame and its kit section in the instructions.")
                  + " Every combination uses the same pieces.", 8.5, tag="arrangement")
    else:  # feature 016 (FR-011): a curved map is hung one way only
        flow.para(f"Template {template.get('id')} ({template.get('title')}): frames {order} from left to "
                  f"right as combination {arrangement.id} ({arrangement.name}), {arrangement.centre} in the "
                  f"centre ({citation}); {REHANG_RULE}, so this map has no other combination. Sections "
                  "are labelled as in the kit's instructions.", 8.5, tag="arrangement")
    flow.para("Provenance", 9, True, tag="heading", gap=0.3)
    flow.para(f"Layout: {layout.get('path') or '(in memory)'}", 8, tag="provenance")
    if layout.get("sha256"):
        flow.para(f"Layout SHA-256: {layout['sha256']}", 8, tag="provenance")
    if template is not None:
        flow.para(template_line(template), 8, tag="provenance")
    recipe = (map_meta or {}).get("recipe") or {}
    if recipe.get("id"):
        flow.para(f"Map recipe: {recipe['id']}" + (f" - {recipe['title']}" if recipe.get("title")
                                                   else ""), 8, tag="provenance")
        for ds in _datasets(map_meta):
            flow.para(dataset_line(ds), 8, tag="provenance")
    else:
        flow.para(f"Source image: {layout.get('source_image')}", 8, tag="provenance")
    if template is not None and template.get("dataset"):
        flow.para(template_dataset_line(template["dataset"], [x.get("id") for x in _datasets(map_meta)]),
                  8, tag="provenance")
    made = f"Made with {TOOL} {__version__}"
    tv = (map_meta or {}).get("tool_version")
    if tv and tv != __version__:
        made += f" (map built with {tv})"
    flow.para(made + ". Drawn from the layout data only; no LEGO artwork or instruction images.",
              8, tag="provenance")
    items += flow.items
    items += furniture(size, title, 1, total)
    return Page(size=size, items=tuple(items), number=1, total=total, kind="overview")


def dataset_line(ds: Dict[str, Any]) -> str:
    return (f"Dataset {ds.get('id')} {ds.get('version') or ''}: {ds.get('title') or ''}. "
            f"License: {ds.get('license')}. Citation: {ds.get('citation')}")


def template_line(rec: Dict[str, Any]) -> str:
    """The provenance line of a non-kit layout's template (``metadata.template``; feature 016,
    data-model.md SheetProvenance.template): id, title, projection, file SHA-256, confirmation."""
    src = rec.get("source") or {}
    conf = src.get("confirmation")
    when = (f"confirmed by the {conf.get('role')} on {conf.get('date')}" if conf
            else "not confirmed by the project owner")
    file = f"file {src['file']} " if src.get("file") else "file "
    return (f"Template: {rec.get('id')} ({rec.get('title')}), projection "
            f"{(rec.get('projection') or {}).get('proj')}; {file}SHA-256 {src.get('sha256')}; {when}.")


def template_dataset_line(ds: Dict[str, Any], listed: Sequence[Optional[str]]) -> str:
    """The dataset that decided the template's land and ocean, cited once: in full, or pointing to
    the layer's dataset line above when a layer reads the same dataset."""
    head = f"Template land and ocean from dataset {ds.get('id')} {ds.get('version') or ''}"
    if ds.get("id") in listed:
        return head + " (above)."
    return (f"{head}: {ds.get('title') or ''}. License: {ds.get('license')}. "
            f"Citation: {ds.get('citation')}")


def _datasets(meta: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for layer in (meta or {}).get("layers") or []:
        ds = layer.get("dataset")
        if ds and ds.get("id") not in [x.get("id") for x in out]:
            out.append(ds)
    return out


# --- legend pages (US2) -------------------------------------------------------------------------

def legend_rows_per_page(size: PageSize) -> int:
    ack = len(wrap(ACKNOWLEDGEMENT, 7, size.width_mm - 2 * MARGIN)) + 1
    bottom = size.height_mm - CONTENT_BOTTOM - ack * 7 * PT_MM * 1.3 - 2.0
    return max(1, int((bottom - LEGEND_TOP) // LEGEND_ROW))


def legend_pages(size: PageSize, legend: Sequence[LegendEntry], title: str, first_number: int,
                 total: int) -> List[Page]:
    W, H = size.width_mm, size.height_mm
    per = legend_rows_per_page(size)
    chunks = [legend[i:i + per] for i in range(0, len(legend), per)] or [[]]
    pages = []
    for k, chunk in enumerate(chunks):
        items: List[Item] = []
        head = "Legend" if len(chunks) == 1 else f"Legend ({k + 1} of {len(chunks)})"
        items.append(Text(MARGIN, 21.0, head, 16, bold=True, tag="legend-title"))
        note = LEGEND_NOTE_SQUARES if any(is_square(e) for e in legend) else LEGEND_NOTE
        items.append(Text(MARGIN, 27.0, fit(note, 8.5, W - 2 * MARGIN), 8.5, tag="legend-note"))
        items.append(Text(MARGIN, 33.5, "Lot", 8, bold=True, tag="legend-head"))
        items.append(Text(MARGIN + 9, 33.5, "Color (LEGO id), part, element; BrickLink item / "
                          "color (id); Rebrickable part / color (id)", 8, bold=True, tag="legend-head"))
        items.append(Text(W - MARGIN, 33.5, "Total", 8, "right", True, tag="legend-head"))
        items.append(Line(MARGIN, 35.0, W - MARGIN, 35.0, SOFT, 0.3, tag="legend-rule"))
        text_w = W - 2 * MARGIN - 9 - 16
        for j, e in enumerate(chunk):
            y = LEGEND_TOP + j * LEGEND_ROW
            items += disc(MARGIN + 3.5, y + 4.5, 3.2, e, 7.5, "swatch")
            l1, l2 = e.label_lines
            items.append(Text(MARGIN + 9, y + 3.9, fit(l1, 8, text_w, True), 8, bold=True,
                              tag="legend-line", data=d(lot=e.number)))
            items.append(Text(MARGIN + 9, y + 7.6, fit(l2, 7, text_w), 7, color=SOFT,
                              tag="legend-line", data=d(lot=e.number)))
            items.append(Text(W - MARGIN, y + 3.9, f"{e.lot.needed:,}", 8.5, "right", True,
                              tag="legend-total", data=d(lot=e.number)))
            items.append(Line(MARGIN, y + LEGEND_ROW, W - MARGIN, y + LEGEND_ROW, FAINT, 0.15,
                              tag="legend-rule"))
        ack = wrap(ACKNOWLEDGEMENT, 7, W - 2 * MARGIN)
        lines = ack + ["Full citations: parts list LAYOUT --format json."]
        y = H - CONTENT_BOTTOM - (len(lines) - 1) * 7 * PT_MM * 1.3
        for line in lines:
            items.append(Text(MARGIN, y, line, 7, color=SOFT, tag="acknowledgement"))
            y += 7 * PT_MM * 1.3
        number = first_number + k
        items += furniture(size, title, number, total)
        pages.append(Page(size=size, items=tuple(items), number=number, total=total, kind="legend"))
    return pages


# --- the set ------------------------------------------------------------------------------------

def default_title(grid: PositionPlacementGrid, layout_path: Optional[Union[str, Path]]) -> str:
    recipe = (grid.map_metadata or {}).get("recipe") or {}
    if recipe.get("title"):
        return str(recipe["title"])
    if layout_path is not None:
        return Path(layout_path).name
    return grid.source_image or "Build sheets"


def build_sheet_set(layout: Union[LayoutInput, PositionPlacementGrid],
                    layout_path: Optional[Union[str, Path]] = None, paper: str = "letter",
                    sections: Optional[Union[str, Iterable[str]]] = None,
                    title: Optional[str] = None, layout_sha256: Optional[str] = None) -> SheetSet:
    """The overview, legend and section pages for a full 128 x 80 layout (feature 017: all but the
    studs under a recorded in-margin plaque)."""
    try:
        size = paper_size(paper)
    except ValueError as exc:
        raise SheetError(str(exc))
    if isinstance(layout, LayoutInput):
        grid, layout_path = layout.grid, layout.path
        pl = build_parts_list(layout)
    else:
        grid = layout
        try:
            check_grid(grid)
        except LayoutInputError as exc:
            raise SheetError(str(exc))
        pl = build_parts_list(grid, layout_path, layout_sha256=layout_sha256)
    try:
        arrangement = arrangement_of(grid)
        chosen = parse_section_labels(sections, arrangement)
    except ValueError as exc:
        raise SheetError(str(exc))
    try:
        holder = plaque_section(grid, arrangement)  # feature 017: the in-margin plaque, in one section
    except ValueError as exc:
        raise SheetError(str(exc))
    covered = grid.plaque_positions if holder is not None else frozenset()
    under = sorted({(p.x, p.y) for p in grid.positions} & covered, key=lambda c: (c[1], c[0]))
    if under:
        raise SheetError(f"layout has {len(under):,} position(s) under the plaque recorded in metadata.plaque, "
                         f"first ({under[0][0]}, {under[0][1]}); the plaque's studs carry no piece")
    if len(grid.positions) != FULL_POSITIONS - len(covered):
        message = (f"layout has {len(grid.positions):,} of {FULL_POSITIONS:,} positions; build sheets need "
                   "every position of the 128 x 80 grid")
        if covered:
            message += f" but the {len(covered):,} studs under the plaque recorded in metadata.plaque"
        raise SheetError(message)
    legend = build_legend(pl)
    numbers = lot_numbers(legend)
    by_number = {e.number: e for e in legend}
    cells = {(p.x, p.y): by_number[numbers[(p.lego_part_id, p.color_id)]] for p in grid.positions}
    mark = None
    if holder is not None:
        rec, st = grid.plaque, grid.plaque["studs"]
        mark = PlaqueMark(row=st["row"], col=st["col"], height=st["height"], width=st["width"],
                          entry=by_number[numbers[(str(rec.get("part_id")), str(rec.get("color")))]],
                          section=holder.label)
    counts = count_sections(grid, legend)
    count_by_label = {c.section.label: c for c in counts}
    title = title if title is not None and title.strip() else default_title(grid, layout_path)
    n_legend = max(1, math.ceil(len(legend) / legend_rows_per_page(size)))
    total = 1 + n_legend + len(chosen)
    pages: List[Page] = [overview_page(size, title, grid, cells, legend, pl.layout,
                                       grid.map_metadata, n_legend, chosen, total, arrangement, mark)]
    pages += legend_pages(size, legend, title, 2, total)
    for i, s in enumerate(chosen):
        pages.append(section_page(size, s, cells, count_by_label[s.label], legend, title,
                                  2 + n_legend + i, total, arrangement,
                                  mark if mark is not None and mark.section == s.label else None))
    return SheetSet(title=title, layout=pl.layout, legend=legend, pages=tuple(pages), paper=size,
                    sections=chosen, counts=counts, parts_list=pl, map_metadata=grid.map_metadata,
                    plaque=mark)

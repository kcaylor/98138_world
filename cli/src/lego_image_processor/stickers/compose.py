"""The two stickers and the print sheet as page models (feature 017, FR-001 - FR-003, FR-008 -
FR-010, FR-012, FR-013, FR-015; research R2 - R4; data-model.md Sticker, StickerSet, PrintSheet;
contracts/sticker-files.md).

``sticker_set(result)`` makes the small and the large sticker of a built map (``MapResult``)
from its recipe's sticker text, the legend of the built map, the data credits and the packaged
plaque parts. Each sticker is a list of ``sheets.model`` items in its own cut coordinates (origin
at the cut line's top-left corner): the bleed, the background and the content, white on the
label tile's cited Black. Cut marks and the cut line are added where a sticker is placed
(``Sticker.drawing``, ``StickerGeometry.cut_line``), so the print sheet and the SVG writer draw
the same sticker with the build sheets' drawing code.

``print_sheet(sticker_set, paper)`` lays both stickers out at true size on one Letter or A4
page (research R2): header, the stickers with bleed and marks, captions, the plaque parts, how
to make them, the color note, every dataset's full citation and license, the provenance and the
build sheets' ``furniture()``. Every block must fit its area; one that does not raises
``StickerError`` naming the block and the paper (the citations must appear, constitution IV).

Same input, same set: nothing depends on the time or the machine. Sets made from builds in
combinations A, B and C are equal but for ``arrangement`` (SC-003); the print sheet's line
"legend values from the build hung as <C>" is the only text that depends on it.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .. import __version__
from ..kit.plaque_parts import Plaque, PlaquePart, load_plaque_parts
from ..kit.source import DISCLAIMER
from ..layout.arrangement import parse_arrangement
from ..maps.build import MapResult
from ..sheets.compose import CONTENT_BOTTOM, MARGIN, RING_RATIO, cap_offset, furniture, text_width
from ..sheets.legend import text_color
from ..sheets.model import (PT_MM, RGB, WHITE, Circle, Item, Line, Page, PageSize, Rect, Text,
                            paper_size)
from ..templates import KIT_TEMPLATE_ID  # feature 016's kit template id (re-exported here)
from . import StickerError
from .credits import Credit, credit_lines, credits_for
from .geometry import StickerGeometry, geometry_for
from .legend import Legend, Swatch, map_legend
from .text import (CAP_HEIGHT, MIN_PT, STEP_PT, ResolvedText, TextBlock, TextSpec,
                   fit_block, fit_stack, line_pitch, resolve_text, wrap_words)

FORMAT_VERSION = "1"
TOOL = "lego-image-processor"
SITE = "98138.world"
PRINTED_NOTE = "The sticker is printed, not a LEGO part."
COLORS_NOTE = "Printed colors only approximate the LEGO colors."
DATA_PREFIX = "Data: "
SIZES = ("small", "large")
_EPS = 1e-9

# sticker content (contracts/sticker-files.md "Sticker content"; research R3, R4)
TEXT_COLOR: RGB = WHITE
SWATCH_D_MM = 2.8
SWATCH_OUTLINE: RGB = (210, 210, 210)
SWATCH_OUTLINE_MM = 0.15
RING_MM = 0.15
ROW_PITCH_MM = 3.4         # legend rows; the first row of a column holds the group heading
LABEL_GAP_MM = 1.0         # swatch to its label
COLUMN_GAP_MM = 3.0        # columns of one group
GROUP_GAP_MM = 5.0         # land group to ocean group
LEGEND_PT = 6.0
HEADING_TOP_MM = 0.1       # legend area top to the heading's cap height

SMALL_TITLE = TextSpec("title", "", 11.0, 3, bold=True, align="center")
SMALL_LINE = TextSpec("line", "", 7.0, 5, align="center")
SMALL_DISCLAIMER = TextSpec("disclaimer", DISCLAIMER, 5.0, 2, align="center")
SMALL_STACK_GAP_MM = 2.0          # title to line
SMALL_DISCLAIMER_GAP_MM = 2.0     # the title and line area to the disclaimer

LARGE_TITLE = TextSpec("title", "", 14.0, 2, bold=True)
LARGE_SITE_PT = 7.0
LARGE_LINE = TextSpec("line", "", 7.0, 2)
LARGE_CREDIT = TextSpec("credit", "", 5.5, 6)
LARGE_DISCLAIMER = TextSpec("disclaimer", DISCLAIMER, 5.5, 2)
TITLE_SITE_GAP_MM = 3.0
TITLE_LINE_GAP_MM = 1.0
LEGEND_GAP_MM = 2.0               # top blocks to the legend, the legend to the credit
CREDIT_DISCLAIMER_GAP_MM = 1.0

# print sheet (research R2; contracts/sticker-files.md "Print sheet")
SHEET_MARGIN = MARGIN                      # 12 mm
LARGE_CUT_AT = (19.0, 41.0)
SMALL_CUT_AT = (19.0, 118.8)
HEADER_BASELINE, SUBTITLE_BASELINE = 21.0, 27.5
HEADER_PT, SUBTITLE_PT = 16.0, 8.5
SUBTITLE = ("Two stickers for Black tiles: print on white sticker paper at 100%, cut along the "
            "marks.")
CAPTION_X = 152.0
CAPTION_PT = 8.0
PARTS_X, PARTS_TOP, PARTS_BOTTOM = 77.8, 115.0, 172.0
NOTES_TOP = 178.0
SHEET_HEADING_PT = 8.0
SHEET_BODY_PT = 7.0
PARTS_HEADING = "Parts for a standalone plaque"
HOWTO = ("Print this page at 100% on white sticker paper (no fit-to-page) and check that the "
         "scale bar measures 100 mm. Cut each sticker out along its cut line, where the marks at "
         "its corners point; the black bleed past the line hides small cutting errors. Place each "
         "sticker on its Black tile so that about 1 mm of tile shows on every side, and press it "
         "flat from the middle out. For a standalone plaque, press the tile onto a Black plate of "
         "the same size.")
MADE_WITH = ("Made with {tool} {version}. Drawn from the recipe and the map's data; no LEGO "
             "artwork, logo or image.")


# --- small value types ------------------------------------------------------------------------

@dataclass(frozen=True)
class RecipeRef:
    """The recipe a set was made from (JSON ``recipe``)."""

    id: str
    title: str
    sha256: str
    format: str = "1"

    def to_dict(self) -> Dict[str, str]:
        return {"id": self.id, "title": self.title, "sha256": self.sha256}


@dataclass(frozen=True)
class TemplateRef:
    """The board template (JSON ``template``): the kit until feature 016 adds others."""

    id: str = KIT_TEMPLATE_ID

    def to_dict(self) -> Dict[str, str]:
        return {"id": self.id}


@dataclass(frozen=True)
class Notes:
    printed: str = PRINTED_NOTE
    colors: str = COLORS_NOTE

    def to_dict(self) -> Dict[str, str]:
        return {"printed": self.printed, "colors": self.colors}


@dataclass(frozen=True)
class PlacedSwatch:
    """A legend swatch as drawn on the large sticker: its circle (centre, radius) and label."""

    swatch: Swatch
    cx: float
    cy: float
    r: float
    label: Text
    column: int


# --- items ------------------------------------------------------------------------------------

def translate(items: Sequence[Item], dx: float, dy: float) -> List[Item]:
    """``items`` moved by (dx, dy) mm."""
    out: List[Item] = []
    for it in items:
        if isinstance(it, Rect):
            out.append(dataclasses.replace(it, x=it.x + dx, y=it.y + dy))
        elif isinstance(it, Circle):
            out.append(dataclasses.replace(it, cx=it.cx + dx, cy=it.cy + dy))
        elif isinstance(it, Line):
            out.append(dataclasses.replace(it, x1=it.x1 + dx, y1=it.y1 + dy, x2=it.x2 + dx,
                                           y2=it.y2 + dy))
        elif isinstance(it, Text):
            out.append(dataclasses.replace(it, x=it.x + dx, y=it.y + dy))
        else:  # pragma: no cover
            raise TypeError(f"not a page item: {it!r}")
    return out


def _tag_data(size: str) -> Tuple[Tuple[str, str], ...]:
    return (("sticker", size),)


def _background(geometry: StickerGeometry, black: RGB, size: str) -> List[Item]:
    bx, by, bw, bh = geometry.bleed_box
    w, h = geometry.cut_mm
    return [Rect(bx, by, bw, bh, fill=black, stroke=None, tag="bleed", data=_tag_data(size)),
            Rect(0.0, 0.0, w, h, fill=black, stroke=None, tag="sticker-bg", data=_tag_data(size))]


def _moved(block: TextBlock, y: float) -> TextBlock:
    x, _, w, h = block.box
    return dataclasses.replace(block, box=(x, y, w, h))


def _bottom(block: TextBlock) -> float:
    return block.box[1] + block.box[3]


# --- the sticker ------------------------------------------------------------------------------

@dataclass(frozen=True)
class Sticker:
    """One sticker (data-model.md Sticker). ``items`` are in cut coordinates: the bleed, the
    background, then the content; marks and the cut line come from ``geometry`` where the sticker
    is placed."""

    size: str
    plaque: Plaque
    geometry: StickerGeometry
    blocks: Tuple[TextBlock, ...]
    legend: Tuple[PlacedSwatch, ...]
    items: Tuple[Item, ...]

    def block(self, field: str) -> TextBlock:
        for b in self.blocks:
            if b.field == field:
                return b
        raise KeyError(f"the {self.size} sticker has no {field} block")

    @property
    def text_sizes(self) -> Tuple[float, float]:
        """The smallest and largest text size chosen (pt)."""
        sizes = [b.size_pt for b in self.blocks]
        return (min(sizes), max(sizes))

    def content_items(self, x0: float, y0: float) -> List[Item]:
        """The sticker's items with its cut line's top-left corner at (x0, y0)."""
        return translate(self.items, x0, y0)

    def drawing(self, x0: float, y0: float) -> List[Item]:
        """What a page draws for this sticker, cut line at (x0, y0): the bleed, the cut marks,
        then the background and content. The cut line itself is ``cut_line`` (drawn last)."""
        placed = self.content_items(x0, y0)
        return [placed[0], *self.geometry.marks(x0, y0, data=_tag_data(self.size)), *placed[1:]]

    def cut_line(self, x0: float, y0: float, stroke: Optional[RGB] = None,
                 stroke_w: float = 0.1) -> Rect:
        return self.geometry.cut_line(x0, y0, stroke=stroke, stroke_w=stroke_w,
                                      data=_tag_data(self.size))

    def to_dict(self) -> Dict[str, Any]:
        g = self.geometry
        return {"plaque": self.size, "tile_mm": list(g.tile_mm), "cut_mm": list(g.cut_mm),
                "bleed_mm": g.bleed_mm, "safe_mm": g.safe_mm,
                "blocks": [{"field": b.field, "lines": list(b.lines), "size_pt": b.size_pt}
                           for b in self.blocks]}


def _spec(base: TextSpec, text: str = "", paragraphs: Sequence[str] = ()) -> TextSpec:
    return dataclasses.replace(base, text=text or base.text, paragraphs=tuple(paragraphs))


def small_sticker(text: ResolvedText, plaque: Plaque) -> Sticker:
    """Title, line and disclaimer only (FR-003), centred; the title and line pair centred
    vertically above the disclaimer at the bottom of the safe area (research R3)."""
    g = geometry_for(plaque)
    sx, sy, sw, sh = g.safe_box
    disc = fit_block(SMALL_DISCLAIMER, sticker="small", x=sx, y=sy, width_mm=sw)
    disc = _moved(disc, sy + sh - disc.box[3])
    avail = disc.box[1] - SMALL_DISCLAIMER_GAP_MM - sy
    stack = fit_stack([_spec(SMALL_TITLE, text.title), _spec(SMALL_LINE, text.line)],
                      sticker="small", x=sx, y=sy, width_mm=sw, height_mm=avail,
                      gap_mm=SMALL_STACK_GAP_MM)
    used = _bottom(stack[-1]) - sy
    off = (avail - used) / 2
    blocks = tuple(_moved(b, b.box[1] + off) for b in stack) + (disc,)
    items: List[Item] = _background(g, plaque.tile.color.rgb, "small")
    for b in blocks:
        items += b.items(TEXT_COLOR)
    return Sticker(size="small", plaque=plaque, geometry=g, blocks=blocks, legend=(),
                   items=tuple(items))


# --- the legend on the large sticker ----------------------------------------------------------

@dataclass(frozen=True)
class _Column:
    group: int
    swatches: Tuple[Swatch, ...]
    width: float


def _legend_columns(legend: Legend, size: float, height: float):
    """Columns at label size ``size`` within ``height``: each group starts a new column with
    its heading, its swatches spread evenly over as few columns as the rows allow. Returns
    (columns, group widths, rows per column) or None when not even one row fits."""
    rows = int(math.floor((height - SWATCH_D_MM) / ROW_PITCH_MM + 1e-6))
    if rows < 1:
        return None
    columns: List[_Column] = []
    widths: List[float] = []
    for gi, group in enumerate(legend.groups):
        sw = group.swatches
        n_cols = max(1, math.ceil(len(sw) / rows))
        per = max(1, math.ceil(len(sw) / n_cols))
        cols = []
        for c in range(n_cols):
            chunk = sw[c * per:(c + 1) * per]
            if not chunk:
                continue
            label_w = max(text_width(s.label, size) for s in chunk)
            cols.append(_Column(gi, tuple(chunk), SWATCH_D_MM + LABEL_GAP_MM + label_w))
        heading_w = text_width(group.heading, size, True)
        group_w = sum(c.width for c in cols) + COLUMN_GAP_MM * (len(cols) - 1)
        widths.append(max(group_w, heading_w))
        columns += cols
    return columns, widths, rows


def _legend_total(widths: Sequence[float]) -> float:
    return sum(widths) + GROUP_GAP_MM * (len(widths) - 1)


def _legend_error(legend: Legend, width: float, height: float) -> StickerError:
    laid = _legend_columns(legend, MIN_PT, height)
    if laid is None:
        layer = legend.groups[0].layer if legend.groups else "land"
        return StickerError.does_not_fit("large", f"legend: {layer}", ROW_PITCH_MM + SWATCH_D_MM,
                                         max(0.0, height))
    _, widths, _ = laid
    right = 0.0
    layer = legend.groups[-1].layer
    for i, (group, w) in enumerate(zip(legend.groups, widths)):
        right += w + (GROUP_GAP_MM if i else 0.0)
        if right > width + _EPS:
            layer = group.layer
            break
    return StickerError.does_not_fit("large", f"legend: {layer}", _legend_total(widths), width)


def place_legend(legend: Legend, *, x: float, y: float, width: float,
                 height: float) -> Tuple[TextBlock, Tuple[PlacedSwatch, ...], List[Item]]:
    """The legend in the area (x, y, width, height): labels from 6 pt down to 5 pt in 0.25 pt
    steps, at the largest size whose columns fit the width. Swatches Ø 2.8 mm in the cited sRGB
    with a light outline, plates with the inner ring; labels white, centred on their swatch."""
    size = LEGEND_PT
    while True:
        laid = _legend_columns(legend, size, height)
        if laid is not None and _legend_total(laid[1]) <= width + _EPS:
            break
        if size <= MIN_PT + _EPS:
            raise _legend_error(legend, width, height)
        size = max(MIN_PT, size - STEP_PT)
    columns, widths, rows = laid
    r = SWATCH_D_MM / 2
    em = size * PT_MM
    items: List[Item] = []
    placed: List[PlacedSwatch] = []
    lines: List[str] = []
    gx = x
    col_index = 0
    for gi, group in enumerate(legend.groups):
        items.append(Text(gx, y + HEADING_TOP_MM + CAP_HEIGHT * em, group.heading, size,
                          bold=True, color=TEXT_COLOR, tag="legend-heading"))
        lines.append(group.heading)
        cx0 = gx
        for col in (c for c in columns if c.group == gi):
            for i, sw in enumerate(col.swatches):
                cx = cx0 + r
                cy = y + ROW_PITCH_MM * (i + 1) + r
                items.append(Circle(cx, cy, r, fill=tuple(sw.rgb), stroke=SWATCH_OUTLINE,
                                    stroke_w=SWATCH_OUTLINE_MM, tag="swatch",
                                    data=(("layer", sw.layer), ("color", sw.color),
                                          ("part", sw.part_id))))
                if sw.layer == "land":   # land is the 1x1 round plate: drawn with a ring
                    items.append(Circle(cx, cy, r * RING_RATIO, fill=None,
                                        stroke=text_color(tuple(sw.rgb)), stroke_w=RING_MM,
                                        tag="swatch-ring"))
                label = Text(cx0 + SWATCH_D_MM + LABEL_GAP_MM, cy + cap_offset(size), sw.label,
                             size, color=TEXT_COLOR, tag="legend-label")
                items.append(label)
                lines.append(sw.label)
                placed.append(PlacedSwatch(swatch=sw, cx=cx, cy=cy, r=r, label=label,
                                           column=col_index))
            cx0 += col.width + COLUMN_GAP_MM
            col_index += 1
        gx += widths[gi] + GROUP_GAP_MM
    used_rows = max(len(c.swatches) for c in columns)
    block = TextBlock(field="legend", lines=tuple(lines), size_pt=size, preferred_pt=LEGEND_PT,
                      min_pt=MIN_PT, bold=False, align="left",
                      box=(x, y, _legend_total(widths), ROW_PITCH_MM * used_rows + SWATCH_D_MM))
    return block, tuple(placed), items


# --- the large sticker ------------------------------------------------------------------------

def _capped(spec: TextSpec, cap_pt: Optional[float], **kw) -> TextBlock:
    """``fit_block`` starting at no more than ``cap_pt``; the block keeps the spec's preferred
    size."""
    spec_k = spec
    if cap_pt is not None:
        start = max(spec.min_pt, min(spec.preferred_pt, cap_pt))
        spec_k = dataclasses.replace(spec, preferred_pt=start)
    return dataclasses.replace(fit_block(spec_k, **kw), preferred_pt=spec.preferred_pt)


def large_sticker(text: ResolvedText, credits: Sequence[str], legend: Legend,
                  plaque: Plaque) -> Sticker:
    """Title and "98138.world" on its first baseline, the line, the legend, the "Data:" credit
    and the disclaimer (FR-002). Top blocks are set from the top down, bottom blocks from the
    bottom up, and the legend takes what is left, shrinking first; when it does not fit at 5 pt
    the other blocks shrink a quarter point at a time (research R3)."""
    g = geometry_for(plaque)
    sx, sy, sw, sh = g.safe_box
    site_w = text_width(SITE, LARGE_SITE_PT, True)
    title_spec = _spec(LARGE_TITLE, text.title)
    line_spec = _spec(LARGE_LINE, text.line)
    credit_spec = _spec(LARGE_CREDIT, paragraphs=[DATA_PREFIX + credits[0], *credits[1:]])
    own: Dict[str, float] = {}
    k = 0
    while True:
        def cap(field: str) -> Optional[float]:
            return None if k == 0 else own[field] - k * STEP_PT

        title = _capped(title_spec, cap("title"), sticker="large", x=sx, y=sy,
                        width_mm=sw - site_w - TITLE_SITE_GAP_MM)
        # "98138.world" sits on the title's first baseline, right-aligned
        site_pitch = line_pitch(LARGE_SITE_PT)
        site_off = (site_pitch + CAP_HEIGHT * LARGE_SITE_PT * PT_MM) / 2
        site_y = title.baselines()[0] - site_off
        if site_y < sy:            # a title smaller than the site name moves down
            title = _moved(title, title.box[1] + sy - site_y)
            site_y = sy
        site = TextBlock(field="site", lines=(SITE,), size_pt=LARGE_SITE_PT,
                         preferred_pt=LARGE_SITE_PT, min_pt=MIN_PT, bold=True, align="right",
                         box=(sx + sw - site_w, site_y, site_w, site_pitch))
        top = max(_bottom(title), _bottom(site)) + TITLE_LINE_GAP_MM
        line = _capped(line_spec, cap("line"), sticker="large", x=sx, y=top, width_mm=sw)
        disc = _capped(LARGE_DISCLAIMER, cap("disclaimer"), sticker="large", x=sx, y=sy,
                       width_mm=sw)
        disc = _moved(disc, sy + sh - disc.box[3])
        credit = _capped(credit_spec, cap("credit"), sticker="large", x=sx, y=sy, width_mm=sw)
        credit = _moved(credit, disc.box[1] - CREDIT_DISCLAIMER_GAP_MM - credit.box[3])
        if k == 0:
            own = {b.field: b.size_pt for b in (title, line, credit, disc)}
        legend_top = _bottom(line) + LEGEND_GAP_MM
        legend_h = credit.box[1] - LEGEND_GAP_MM - legend_top
        try:
            legend_block, placed, legend_items = place_legend(legend, x=sx, y=legend_top,
                                                              width=sw, height=legend_h)
            break
        except StickerError:
            if all(b.size_pt <= b.min_pt + _EPS for b in (title, line, credit, disc)):
                raise
            k += 1
    blocks = (title, site, line, legend_block, credit, disc)
    items: List[Item] = _background(g, plaque.tile.color.rgb, "large")
    items += title.items(TEXT_COLOR) + site.items(TEXT_COLOR) + line.items(TEXT_COLOR)
    items += legend_items
    items += credit.items(TEXT_COLOR) + disc.items(TEXT_COLOR)
    return Sticker(size="large", plaque=plaque, geometry=g, blocks=blocks, legend=placed,
                   items=tuple(items))


# --- the set ----------------------------------------------------------------------------------

def tile_label(plaque: Plaque) -> str:
    """"8 x 16", "6 x 6": the tile's size as LEGO and BrickLink name it (short side first)."""
    a, b = sorted(plaque.studs)
    return f"{a} x {b}"


def part_line(part: PlaquePart, quantity: int = 1) -> str:
    """One plaque part with its cited IDs, as the print sheet and the command print it:
    "1 Plate 8 x 16, Black - LEGO element 6094066, design 92438; BrickLink 92438, Black (11);
    Rebrickable 92438, Black (0)". The BrickLink item number is the pinned page's, which can
    differ from the part ID."""
    c, n = part.color, part.numbers
    return (f"{quantity} {part.name}, {c.lego.name} - LEGO element {c.element_id}, design "
            f"{', '.join(n.lego_design_ids)}; BrickLink {n.bricklink_item_no}, {c.bricklink.name} "
            f"({c.bricklink.id}); Rebrickable {n.rebrickable_part_num}, {c.rebrickable.name} "
            f"({c.rebrickable.id})")


def part_to_dict(part: PlaquePart, quantity: int = 1) -> Dict[str, Any]:
    c, n = part.color, part.numbers
    cites = [x.id for x in c.citations.values()] + [p.id for p in n.citations.values()]
    return {"role": part.kind, "quantity": quantity, "part_id": part.part_id, "name": part.name,
            "color": {"key": c.key, "lego": {"name": c.lego.name, "id": c.lego.id},
                      "bricklink": {"name": c.bricklink.name, "id": c.bricklink.id},
                      "rebrickable": {"name": c.rebrickable.name, "id": c.rebrickable.id}},
            "element_id": c.element_id, "lego_design_ids": list(n.lego_design_ids),
            "bricklink_item": n.bricklink_item_no, "rebrickable_part": n.rebrickable_part_num,
            "citations": list(dict.fromkeys(cites))}


def plaque_to_dict(plaque: Plaque) -> Dict[str, Any]:
    """A standalone plaque in the JSON summary: 1 tile and 1 plate with cited IDs."""
    g = geometry_for(plaque)
    return {"size": plaque.size, "studs": list(plaque.studs), "sticker_mm": list(g.cut_mm),
            "parts": [part_to_dict(p) for p in plaque.parts]}


@dataclass(frozen=True)
class StickerSet:
    """The small and the large sticker of one map (data-model.md StickerSet). No timestamps:
    the same built map gives an equal set; ``arrangement`` records the build the legend values
    come from and is the only field that differs between sets made in A, B and C."""

    recipe: RecipeRef
    template: TemplateRef
    arrangement: str
    text: ResolvedText
    small: Sticker
    large: Sticker
    legend: Legend
    credits: Tuple[Credit, ...]
    plaques: Tuple[Plaque, Plaque]
    notes: Notes
    tool_version: str
    disclaimer: str

    @property
    def stickers(self) -> Tuple[Sticker, Sticker]:
        return (self.small, self.large)

    def to_dict(self) -> Dict[str, Any]:
        """The JSON summary, format "1", keys in the contract's order
        (contracts/sticker-files.md "JSON summary")."""
        return {
            "format_version": FORMAT_VERSION,
            "recipe": self.recipe.to_dict(),
            "template": self.template.to_dict(),
            "arrangement": self.arrangement,
            "text": self.text.to_dict(),
            "stickers": {"small": self.small.to_dict(), "large": self.large.to_dict()},
            "legend": self.legend.to_list(),
            "credits": [c.to_dict() for c in self.credits],
            "plaques": [plaque_to_dict(p) for p in self.plaques],
            "notes": self.notes.to_dict(),
            "tool_version": self.tool_version,
            "disclaimer": self.disclaimer,
        }


def sticker_set(result: MapResult) -> StickerSet:
    """Both stickers of a built map on the kit template. Raises ``StickerError`` when the recipe
    has no sticker line or a text does not fit at 5 pt (naming the sticker, the field and the
    space needed and available)."""
    recipe = result.recipe
    tpl = getattr(result, "template", None)
    if tpl is not None and not tpl.is_kit:   # feature 016 merge (T053); T056 makes template sets
        raise StickerError(f"sticker sets are made on the kit template {KIT_TEMPLATE_ID} only; "
                           f"{recipe.id} is built on {tpl.id}")
    text = resolve_text(recipe)
    legend = map_legend(result)
    credits = credits_for(recipe)
    table = load_plaque_parts()
    small_p, large_p = table.plaques["small"], table.plaques["large"]
    small = small_sticker(text, small_p)
    large = large_sticker(text, credit_lines(recipe, credits), legend, large_p)
    arrangement = (result.arrangement or parse_arrangement(None)).id
    return StickerSet(recipe=RecipeRef(id=recipe.id, title=recipe.title, sha256=recipe.sha256,
                                       format=recipe.format),
                      template=TemplateRef(), arrangement=arrangement, text=text, small=small,
                      large=large, legend=legend, credits=tuple(credits),
                      plaques=(small_p, large_p), notes=Notes(), tool_version=__version__,
                      disclaimer=DISCLAIMER)


# --- the print sheet --------------------------------------------------------------------------

@dataclass(frozen=True)
class PrintSheet:
    """One page with both stickers at true size (data-model.md PrintSheet)."""

    paper: PageSize
    page: Page

    @property
    def items(self) -> Tuple[Item, ...]:
        return self.page.items


@dataclass(frozen=True)
class _Para:
    text: str
    size: float
    tag: str
    block: str
    bold: bool = False
    gap: float = 0.0       # mm after the paragraph


def _sheet_error(block: str, paper: PageSize, needed: float, available: float) -> StickerError:
    need = math.ceil(needed * 10 - 1e-6) / 10
    have = math.floor(max(0.0, available) * 10 + 1e-6) / 10
    return StickerError(f"print sheet ({paper.label}): the {block} block does not fit at "
                        f"{MIN_PT:g} pt (needs {need:.1f} mm, {have:.1f} mm available)",
                        field=block, needed_mm=needed, available_mm=available)


def _flow(paras: Sequence[_Para], *, x: float, top: float, width: float, bottom: float,
          paper: PageSize) -> List[Item]:
    """Paragraphs set top-down from ``top``; while they run past ``bottom`` every paragraph drops
    a quarter point (none below 5 pt). Still too long at 5 pt: ``StickerError`` naming the first
    block that runs past the bottom."""
    k = 0
    while True:
        items: List[Item] = []
        y = top
        over: Optional[str] = None
        wide: Optional[Tuple[str, float]] = None
        for p in paras:
            size = max(MIN_PT, p.size - k * STEP_PT)
            for word in p.text.split():
                ww = text_width(word, size, p.bold)
                if ww > width + _EPS and wide is None:
                    wide = (p.block, ww)
            pitch = line_pitch(size)
            off = (pitch + CAP_HEIGHT * size * PT_MM) / 2
            for ln in wrap_words(p.text, size, width, p.bold):
                items.append(Text(x, y + off, ln, size, bold=p.bold, tag=p.tag))
                y += pitch
            if y > bottom + _EPS and over is None:
                over = p.block
            y += p.gap
        if over is None and wide is None:
            return items
        if all(p.size - k * STEP_PT <= MIN_PT + _EPS for p in paras):
            if wide is not None:
                raise _sheet_error(wide[0], paper, wide[1], width)
            raise _sheet_error(over, paper, y - top, bottom - top)
        k += 1


def _mm(v: float) -> str:
    return f"{v:.1f}"


def _caption(st: Sticker, label: str) -> str:
    g = st.geometry
    return (f"{label} sticker {_mm(g.cut_mm[0])} x {_mm(g.cut_mm[1])} mm, for a Black tile "
            f"{tile_label(st.plaque)} (about {_mm(g.tile_mm[0])} x {_mm(g.tile_mm[1])} mm)")


def citation_text(c: Credit) -> str:
    """A dataset's full citation as the print sheet and the SVG metadata give it: "<id>
    (<version>): <title>. <citation> License: <license>." and the acknowledgement."""
    out = f"{c.dataset} ({c.version}): {c.title}. {c.citation} License: {c.license}."
    if c.acknowledgement:
        out += f" {c.acknowledgement}"
    return out


def _one_line(text: str, size_pt: float, tag: str, baseline: float, right: float,
              paper: PageSize, bold: bool = False) -> Text:
    """A header line at ``baseline``: one line, shrunk to the width if needed (5 pt at least)."""
    spec = TextSpec("header", text, size_pt, 1, bold=bold)
    try:
        b = fit_block(spec, sticker="sheet", x=SHEET_MARGIN, y=0.0, width_mm=right - SHEET_MARGIN)
    except StickerError as exc:
        raise _sheet_error("header", paper, exc.needed_mm or 0.0, exc.available_mm or 0.0)
    return Text(SHEET_MARGIN, baseline, b.lines[0], b.size_pt, bold=bold, tag=tag)


def print_sheet(stickers: StickerSet, paper: str = "letter") -> PrintSheet:
    """The print sheet on ``paper`` (``letter`` or ``a4``): research R2's blocks at the same
    positions on both papers. Raises ``StickerError`` naming the block and the paper when a
    block does not fit its area at 5 pt."""
    size = paper_size(paper)
    W, H = size.width_mm, size.height_mm
    right = W - SHEET_MARGIN
    s = stickers
    items: List[Item] = []

    title = f"Map stickers: {s.text.title}"
    items.append(_one_line(title, HEADER_PT, "sheet-title", HEADER_BASELINE, right, size, bold=True))
    items.append(_one_line(SUBTITLE, SUBTITLE_PT, "sheet-subtitle", SUBTITLE_BASELINE, right, size))

    items += s.large.drawing(*LARGE_CUT_AT)
    items += s.small.drawing(*SMALL_CUT_AT)

    lx, ly = LARGE_CUT_AT
    items += _flow([_Para(_caption(s.large, "Large"), CAPTION_PT, "caption", "large sticker",
                          gap=1.2),
                    _Para("For the front, the back of the frame or a display.", CAPTION_PT,
                          "caption", "large sticker")],
                   x=CAPTION_X, top=ly, width=right - CAPTION_X,
                   bottom=ly + s.large.geometry.cut_mm[1], paper=size)

    parts: List[_Para] = [_Para(_caption(s.small, "Small"), CAPTION_PT, "caption", "small sticker",
                                gap=2.5),
                          _Para(PARTS_HEADING, 8.5, "parts-heading", "plaque parts", bold=True,
                                gap=0.8)]
    for st in (s.large, s.small):
        plaque = st.plaque
        parts.append(_Para(f"{st.size.capitalize()} plaque (Black, {tile_label(plaque)})",
                           SHEET_BODY_PT, "parts-plaque", "plaque parts", bold=True, gap=0.3))
        for i, part in enumerate(plaque.parts):
            parts.append(_Para(part_line(part), SHEET_BODY_PT, "part", "plaque parts",
                               gap=1.2 if i == len(plaque.parts) - 1 else 0.3))
    parts.append(_Para(s.notes.printed, SHEET_BODY_PT, "printed-note", "plaque parts", bold=True))
    items += _flow(parts, x=PARTS_X, top=PARTS_TOP, width=right - PARTS_X, bottom=PARTS_BOTTOM,
                   paper=size)

    notes: List[_Para] = [
        _Para("How to make it", SHEET_HEADING_PT, "notes-heading", "notes", bold=True, gap=0.3),
        _Para(HOWTO, SHEET_BODY_PT, "howto", "notes", gap=0.6),
        _Para(s.notes.colors, SHEET_BODY_PT, "color-note", "notes", gap=1.5),
        _Para("Data", SHEET_HEADING_PT, "notes-heading", "data", bold=True, gap=0.3),
    ]
    notes += [_Para(citation_text(c), SHEET_BODY_PT, "citation", "data", gap=0.6) for c in s.credits]
    notes[-1] = dataclasses.replace(notes[-1], gap=1.5)
    notes += [
        _Para("Provenance", SHEET_HEADING_PT, "notes-heading", "provenance", bold=True, gap=0.3),
        _Para(f"Recipe {s.recipe.id}, SHA-256 {s.recipe.sha256}; legend values from the build "
              f"hung as {s.arrangement}.", SHEET_BODY_PT, "provenance", "provenance", gap=0.3),
        _Para(MADE_WITH.format(tool=TOOL, version=s.tool_version), SHEET_BODY_PT, "provenance",
              "provenance"),
    ]
    items += _flow(notes, x=SHEET_MARGIN, top=NOTES_TOP, width=right - SHEET_MARGIN,
                   bottom=H - CONTENT_BOTTOM, paper=size)

    items += furniture(size, title, 1, 1)
    items += [s.large.cut_line(*LARGE_CUT_AT), s.small.cut_line(*SMALL_CUT_AT)]
    page = Page(size=size, items=tuple(items), number=1, total=1, kind="stickers",
                label="stickers")
    return PrintSheet(paper=size, page=page)

"""Sticker files (feature 017, FR-007, FR-011 - FR-013, FR-015, FR-026; research R4;
contracts/sticker-files.md; data-model.md "Sticker files").

- ``render_sticker_pdf(set, paper)``: the print sheet (``compose.print_sheet``) as one PDF page,
  drawn with the build sheets' item drawing (``sheets.render_pdf.draw_items``), ReportLab
  ``invariant=1`` and ``pageCompression=1``. Standard Helvetica fonts, not embedded, so every
  text must be Latin-1; a field that is not stops with "use --format svg". The two cut lines are
  unpainted rectangles (``re n``): in the file, not printed.
- ``render_sticker_svgs(set)``: ``sticker-small.svg`` and ``sticker-large.svg``, each on a canvas
  of the cut plus 7 mm: white paper, the bleed, the cut marks, the sticker, and last a group
  ``<g id="cut-line">`` with the cut line as a magenta hairline. Items are written by the build
  sheets' serialiser (``sheets.render_svg.item_svg``); every text carries ``textLength`` (its
  Helvetica width) so a substitute font keeps the measured width. ``<metadata>`` holds the
  recipe, a non-kit template's line (016), every dataset's full citation and license and the
  tool version, nothing that depends on the arrangement, so the SVGs of A, B and C builds are
  byte-identical.
- ``render_sticker_json(set)``: the JSON summary (``StickerSet.to_dict()``), UTF-8, indent 2.

Same input, same bytes: no timestamps, fixed attribute order, two-decimal numbers, ``\\n``.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import io
import json
from typing import Iterator, List, Optional, Tuple
from xml.sax.saxutils import escape

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from ..kit.source import DISCLAIMER
from ..sheets.compose import text_width
from ..sheets.model import RGB, Page, Text, is_latin1
from ..sheets.render_pdf import draw_items
from ..sheets.render_svg import FONT, item_svg, svg_number
from . import StickerError
from .compose import SITE, TOOL, Sticker, StickerSet, citation_text, print_sheet

AUTHOR = SITE
SUBJECT = f"Map stickers for {SITE}. {DISCLAIMER}"
CUT_STROKE: RGB = (255, 0, 255)     # a magenta hairline cutting software can select
CUT_STROKE_MM = 0.1
SVG_NAMES = {"small": "sticker-small.svg", "large": "sticker-large.svg"}


# --- PDF ----------------------------------------------------------------------------------------

def _set_fields(s: StickerSet) -> Iterator[Tuple[str, str]]:
    """The set's texts by field, in the order a Latin-1 error names them."""
    yield "title", s.text.title
    yield "line", s.text.line
    for group in s.legend.groups:
        yield f"legend: {group.layer}", group.heading
        for sw in group.swatches:
            yield f"legend: {group.layer}", sw.label
    for line in s.large.block("credit").lines:
        yield "credit", line
    for c in s.credits:
        yield f"data: {c.dataset}", citation_text(c)


def _not_latin1(text: str) -> Optional[str]:
    for ch in text:
        if not is_latin1(ch):
            return ch
    return None


def check_latin1(s: StickerSet, page: Optional[Page] = None) -> None:
    """``StickerError`` naming the first field (then any page text, by its tag) that is not
    Latin-1 text, which the PDF's standard Helvetica fonts need."""
    fields = list(_set_fields(s))
    if page is not None:
        fields += [(it.tag or "text", it.text) for it in page.items if isinstance(it, Text)]
    for field, text in fields:
        ch = _not_latin1(text)
        if ch is not None:
            raise StickerError(f"the sticker {field} is not Latin-1 text ({ch!r} in {text!r}), "
                               "which the PDF's standard Helvetica fonts need; use --format svg",
                               field=field)


def render_sticker_pdf(stickers: StickerSet, paper: str = "letter") -> bytes:
    """The print sheet on ``paper`` (``letter`` or ``a4``) as one PDF page (bytes). Raises
    ``StickerError`` for text outside Latin-1 or a block that does not fit the paper."""
    check_latin1(stickers)
    sheet = print_sheet(stickers, paper)
    page = sheet.page
    check_latin1(stickers, page)
    W, H = page.size.width_mm, page.size.height_mm
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(W * mm, H * mm), invariant=1, pageCompression=1)
    c.setTitle(f"Map stickers: {stickers.text.title}")
    c.setAuthor(AUTHOR)
    c.setSubject(SUBJECT)
    c.setCreator(f"{TOOL} {stickers.tool_version}")
    draw_items(c, page.items, H)
    c.showPage()
    c.save()
    return buf.getvalue()


# --- SVG ----------------------------------------------------------------------------------------

def svg_metadata(s: StickerSet) -> str:
    """The citations block of both SVGs: recipe id and SHA-256, on a non-kit template 016's
    template line, every dataset's id, version, title, full citation and license (and
    acknowledgement), and the tool version."""
    data = " ".join(citation_text(c) for c in s.credits)
    out = f"Recipe {s.recipe.id} (SHA-256 {s.recipe.sha256})."
    if s.template.line:
        out += f" {s.template.line}"
    if data:
        out += f" Data: {data}"
    return out + f" Made with {TOOL} {s.tool_version}."


def _item(it) -> Optional[str]:
    if isinstance(it, Text):
        return item_svg(it, text_length=text_width(it.text, it.size_pt, it.bold))
    return item_svg(it)


def sticker_svg(sticker: Sticker, stickers: StickerSet) -> str:
    """One sticker on its canvas (cut + 7 mm on every side), cut line last."""
    W, H = sticker.geometry.canvas_mm
    m = sticker.geometry.margin_mm
    n = svg_number
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{n(W)}mm" height="{n(H)}mm" '
        f'viewBox="0 0 {n(W)} {n(H)}" font-family="{FONT}">',
        f"<title>{escape(sticker.size.capitalize())} sticker: {escape(stickers.text.title)} "
        f"({SITE})</title>",
        f"<desc>{escape(DISCLAIMER)}</desc>",
        f"<metadata>{escape(svg_metadata(stickers))}</metadata>",
        f'<rect x="0" y="0" width="{n(W)}" height="{n(H)}" fill="#ffffff"/>',
    ]
    for it in sticker.drawing(m, m):
        line = _item(it)
        if line is not None:
            lines.append(line)
    cut = sticker.cut_line(m, m, stroke=CUT_STROKE, stroke_w=CUT_STROKE_MM)
    lines.append(f'<g id="cut-line">{item_svg(cut)}</g>')
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def render_sticker_svgs(stickers: StickerSet) -> List[Tuple[str, str]]:
    """``[("sticker-small.svg", text), ("sticker-large.svg", text)]``. Any Unicode text."""
    return [(SVG_NAMES[st.size], sticker_svg(st, stickers)) for st in stickers.stickers]


# --- JSON ---------------------------------------------------------------------------------------

def render_sticker_json(stickers: StickerSet) -> str:
    """The JSON summary (format "1"), ``ensure_ascii=False``, indent 2, ending in a newline."""
    return json.dumps(stickers.to_dict(), ensure_ascii=False, indent=2) + "\n"

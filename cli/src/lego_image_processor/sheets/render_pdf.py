"""PDF backend for build sheets (006 FR-009, FR-014, FR-015): ReportLab, deterministic.

``invariant=1`` fixes the creation date and document ID so the same sheet set gives the same
bytes. Text uses the standard Helvetica fonts (not embedded, Latin-1 only); no raster images.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import io
from typing import Iterable

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .. import __version__
from ..kit.source import DISCLAIMER
from .compose import SheetSet
from .model import Circle, Item, Line, Rect, Text, is_latin1, latin1_safe

AUTHOR = "98138.world"


def _rgb(c, rgb) -> None:
    c.setFillColorRGB(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)


def _stroke(c, rgb) -> None:
    c.setStrokeColorRGB(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)


def draw_items(c, items: Iterable[Item], height_mm: float) -> None:
    """Draw page-model ``items`` on the ReportLab canvas ``c`` for a page ``height_mm`` tall
    (y flipped: the model's origin is top-left). The build sheets and the sticker print sheet
    (feature 017, research R4) draw with this one function. A ``Rect`` with neither fill nor
    stroke becomes an unpainted path (``re n``)."""
    H = height_mm
    for it in items:
        if isinstance(it, Circle):
            if it.fill is not None:
                _rgb(c, it.fill)
            if it.stroke is not None:
                _stroke(c, it.stroke)
                c.setLineWidth(it.stroke_w * mm)
            c.circle(it.cx * mm, (H - it.cy) * mm, it.r * mm, stroke=int(it.stroke is not None),
                     fill=int(it.fill is not None))
        elif isinstance(it, Rect):
            if it.fill is not None:
                _rgb(c, it.fill)
            if it.stroke is not None:
                _stroke(c, it.stroke)
                c.setLineWidth(it.stroke_w * mm)
            c.rect(it.x * mm, (H - it.y - it.h) * mm, it.w * mm, it.h * mm,
                   stroke=int(it.stroke is not None), fill=int(it.fill is not None))
        elif isinstance(it, Line):
            _stroke(c, it.stroke)
            c.setLineWidth(it.w * mm)
            c.line(it.x1 * mm, (H - it.y1) * mm, it.x2 * mm, (H - it.y2) * mm)
        elif isinstance(it, Text):
            c.setFont("Helvetica-Bold" if it.bold else "Helvetica", it.size_pt)
            _rgb(c, it.color)
            x, y, s = it.x * mm, (H - it.y) * mm, latin1_safe(it.text)
            if it.align == "center":
                c.drawCentredString(x, y, s)
            elif it.align == "right":
                c.drawRightString(x, y, s)
            else:
                c.drawString(x, y, s)


def render_pdf(sheet_set: SheetSet) -> bytes:
    """The sheet set as one PDF (bytes). Raises ValueError if the title is not Latin-1."""
    if not is_latin1(sheet_set.title):
        raise ValueError("the title must be Latin-1 text for PDF output (the PDF uses the standard "
                         "Helvetica font); use --format svg for other characters")
    buf = io.BytesIO()
    first = sheet_set.pages[0].size
    c = canvas.Canvas(buf, pagesize=(first.width_mm * mm, first.height_mm * mm), invariant=1,
                      pageCompression=1)
    c.setTitle(latin1_safe(sheet_set.title))
    c.setAuthor(AUTHOR)
    c.setSubject(f"Build sheets for the 31203 template. {DISCLAIMER}")
    c.setCreator(f"lego-image-processor {__version__}")
    for page in sheet_set.pages:
        c.setPageSize((page.size.width_mm * mm, page.size.height_mm * mm))
        draw_items(c, page.items, page.size.height_mm)
        c.showPage()
    c.save()
    return buf.getvalue()

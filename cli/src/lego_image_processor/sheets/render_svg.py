"""SVG backend for build sheets (006 US3, FR-009, FR-014): one file per page, standard library.

Coordinates are millimetres (``viewBox`` = page size), numbers written with two decimals, fixed
attribute order and ``\\n`` line endings, no timestamps: identical input gives identical files.
Each item's ``tag`` and ``data`` become ``class`` and ``data-*`` attributes so the planned web app
and tests can read studs back. No ``<image>`` elements.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from typing import List, Optional, Tuple
from xml.sax.saxutils import escape

from ..kit.source import DISCLAIMER
from .compose import SheetSet
from .model import PT_MM, RGB, Circle, Line, Page, Rect, Text

ANCHOR = {"left": "start", "center": "middle", "right": "end"}
FONT = "Helvetica, Arial, sans-serif"


def _n(v: float) -> str:
    s = f"{v:.2f}"
    return "0.00" if s == "-0.00" else s


def _hex(rgb: Optional[RGB]) -> str:
    return "none" if rgb is None else "#%02x%02x%02x" % tuple(rgb)


def _attr(v: str) -> str:
    return escape(v, {'"': "&quot;"})


def _meta(it) -> str:
    out = f' class="{_attr(it.tag)}"' if it.tag else ""
    for k, v in it.data:
        out += f' data-{k}="{_attr(v)}"'
    return out


def _stroke(rgb: Optional[RGB], w: float) -> str:
    return ' stroke="none"' if rgb is None else f' stroke="{_hex(rgb)}" stroke-width="{_n(w)}"'


def page_svg(page: Page, title: str) -> str:
    W, H = page.size.width_mm, page.size.height_mm
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_n(W)}mm" height="{_n(H)}mm" '
        f'viewBox="0 0 {_n(W)} {_n(H)}" font-family="{FONT}">',
        f"<title>{escape(title)} - page {page.number} of {page.total}</title>",
        f"<desc>{escape(DISCLAIMER)}</desc>",
        f'<rect x="0" y="0" width="{_n(W)}" height="{_n(H)}" fill="#ffffff"/>',
    ]
    for it in page.items:
        if isinstance(it, Circle):
            lines.append(f'<circle cx="{_n(it.cx)}" cy="{_n(it.cy)}" r="{_n(it.r)}" '
                         f'fill="{_hex(it.fill)}"{_stroke(it.stroke, it.stroke_w)}{_meta(it)}/>')
        elif isinstance(it, Rect):
            lines.append(f'<rect x="{_n(it.x)}" y="{_n(it.y)}" width="{_n(it.w)}" '
                         f'height="{_n(it.h)}" fill="{_hex(it.fill)}"'
                         f'{_stroke(it.stroke, it.stroke_w)}{_meta(it)}/>')
        elif isinstance(it, Line):
            lines.append(f'<line x1="{_n(it.x1)}" y1="{_n(it.y1)}" x2="{_n(it.x2)}" '
                         f'y2="{_n(it.y2)}"{_stroke(it.stroke, it.w)}{_meta(it)}/>')
        elif isinstance(it, Text):
            weight = ' font-weight="bold"' if it.bold else ""
            lines.append(f'<text x="{_n(it.x)}" y="{_n(it.y)}" font-size="{_n(it.size_pt * PT_MM)}" '
                         f'text-anchor="{ANCHOR[it.align]}"{weight} fill="{_hex(it.color)}"'
                         f'{_meta(it)}>{escape(it.text)}</text>')
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def render_svg(sheet_set: SheetSet) -> List[Tuple[str, str]]:
    """One ``(page-NN.svg, text)`` per page, in page order."""
    width = max(2, len(str(len(sheet_set.pages))))
    return [(f"page-{p.number:0{width}d}.svg", page_svg(p, sheet_set.title)) for p in sheet_set.pages]

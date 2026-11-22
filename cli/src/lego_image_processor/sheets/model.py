"""Backend-neutral page model for build sheets (006): shapes and text in millimetres.

Origin top-left, y down. Colors are RGB tuples (0-255). The PDF and SVG backends draw exactly
these items, so tests can check a page without rendering it. ``tag`` and ``data`` name what an
item shows (for example a stud and its position); the SVG backend writes them as ``class`` and
``data-*`` attributes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Union

RGB = Tuple[int, int, int]
Data = Tuple[Tuple[str, str], ...]
BLACK: RGB = (0, 0, 0)
WHITE: RGB = (255, 255, 255)
GREY: RGB = (128, 128, 128)
OUTLINE: RGB = (150, 150, 150)
PT_MM = 25.4 / 72


@dataclass(frozen=True)
class PageSize:
    name: str
    label: str
    width_mm: float
    height_mm: float


PAPERS = {
    "letter": PageSize("letter", "Letter", 215.9, 279.4),
    "a4": PageSize("a4", "A4", 210.0, 297.0),
}


def paper_size(name: str) -> PageSize:
    try:
        return PAPERS[str(name).lower()]
    except KeyError:
        raise ValueError(f"unknown paper {name!r}; choose letter or a4")


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float
    fill: Optional[RGB] = None
    stroke: Optional[RGB] = None
    stroke_w: float = 0.2
    tag: str = ""
    data: Data = ()


@dataclass(frozen=True)
class Circle:
    cx: float
    cy: float
    r: float
    fill: Optional[RGB] = None
    stroke: Optional[RGB] = None
    stroke_w: float = 0.2
    tag: str = ""
    data: Data = ()


@dataclass(frozen=True)
class Line:
    x1: float
    y1: float
    x2: float
    y2: float
    stroke: RGB = BLACK
    w: float = 0.2
    tag: str = ""
    data: Data = ()


@dataclass(frozen=True)
class Text:
    """``y`` is the baseline; ``align`` is left, center or right; ``size_pt`` in points."""

    x: float
    y: float
    text: str
    size_pt: float
    align: str = "left"
    bold: bool = False
    color: RGB = BLACK
    tag: str = ""
    data: Data = ()


Item = Union[Rect, Circle, Line, Text]


@dataclass(frozen=True)
class Page:
    size: PageSize
    items: Tuple[Item, ...]
    number: int
    total: int
    kind: str
    label: str = ""


def is_latin1(text: str) -> bool:
    try:
        text.encode("latin-1")
    except UnicodeEncodeError:
        return False
    return True


def latin1_safe(text: str) -> str:
    """Replace characters outside Latin-1 with '?' (PDF standard fonts are Latin-1 only)."""
    return text.encode("latin-1", "replace").decode("latin-1")

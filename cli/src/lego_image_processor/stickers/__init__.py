"""Map stickers (feature 017): a small and a large printed sticker for a Black LEGO tile plaque,
made from a built map (``maps.build.MapResult``) and its recipe.

- ``text``: the sticker title and line with their sources, legend numbers and the display step,
  and the wrap-then-shrink fit of text blocks (research R3, R7, R8).
- ``credits``: one data credit per dataset the map uses (research R9).
- ``legend``: the color legend, computed from the built map only (research R7).
- ``geometry``: true-size tile, cut line, bleed, cut marks and safe area (research R1).
- ``compose``: ``sticker_set(result)`` (both stickers as page models), ``StickerSet.to_dict()``
  (the JSON summary) and ``print_sheet(set, paper)`` (one Letter or A4 page; research R2-R4).
- ``render``: ``render_sticker_pdf(set, paper)`` (the print sheet, bytes),
  ``render_sticker_svgs(set)`` (``sticker-small.svg``, ``sticker-large.svg``) and
  ``render_sticker_json(set)`` (the JSON summary), with the build sheets' drawing code.

Nothing outside this package reads a recipe's ``[sticker]`` table, and nothing here changes a
layout, report, parts list, cells file, sheet or price estimate (FR-017).
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import math
from typing import Optional


class StickerError(ValueError):
    """A sticker set cannot be made: no sticker line, or text that does not fit at 5 pt.

    A fit error names the sticker (``small`` or ``large``), the field (``title``, ``line``,
    ``legend: ocean``, ``credit``, ``disclaimer``, or several joined with " + " for a stack) and
    the space needed and available in mm (data-model.md TextBlock)."""

    def __init__(self, message: str, *, sticker: Optional[str] = None, field: Optional[str] = None,
                 needed_mm: Optional[float] = None, available_mm: Optional[float] = None):
        super().__init__(message)
        self.sticker, self.field = sticker, field
        self.needed_mm, self.available_mm = needed_mm, available_mm

    @classmethod
    def does_not_fit(cls, sticker: str, field: str, needed_mm: float, available_mm: float,
                     min_pt: float = 5.0) -> "StickerError":
        # needed rounded up and available rounded down, so the two printed values always differ
        need = math.ceil(needed_mm * 10 - 1e-6) / 10
        have = math.floor(available_mm * 10 + 1e-6) / 10
        return cls(f"{sticker} sticker: {field} does not fit at {min_pt:g} pt "
                   f"(needs {need:.1f} mm, {have:.1f} mm available)",
                   sticker=sticker, field=field, needed_mm=needed_mm, available_mm=available_mm)


from .compose import (KIT_TEMPLATE_ID, PrintSheet, Sticker, StickerSet,  # noqa: E402
                      print_sheet, sticker_set)
from .geometry import StickerGeometry, sticker_geometry  # noqa: E402
from .render import render_sticker_json, render_sticker_pdf, render_sticker_svgs  # noqa: E402

__all__ = ["StickerError", "KIT_TEMPLATE_ID", "Sticker", "StickerSet", "PrintSheet",
           "sticker_set", "print_sheet", "render_sticker_pdf", "render_sticker_svgs",
           "render_sticker_json", "StickerGeometry", "sticker_geometry"]

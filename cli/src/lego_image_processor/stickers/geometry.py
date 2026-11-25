"""True-size sticker geometry (feature 017, FR-009; research R1; data-model.md StickerGeometry).

Lengths in millimetres. Sources:

- Stud pitch 8.0 mm: the LDraw file format specification, "1 brick width/depth = 20 LDU" and
  "1 LDU = 0.4 mm" (https://www.ldraw.org/article/218.html; both stated there as
  approximations), already the build sheets' pitch (``sheets.compose.PITCH``, feature 006 R4).
- Tile outer size = studs x 8.0 mm - 0.2 mm: LDraw gives no clearance; the LUGNET FAQ "What are
  the dimensions of LEGO brick?" (https://www.lugnet.com/~330/FAQ/Build/dimensions) gives a
  measured pitch of 7.986 mm and "a small gap" between bricks; 0.1 mm per side is the
  conventional figure. With the measured pitch a 6 x 6 tile is about 47.7 mm, so the print sheet
  says "about" for tile sizes and the 1 mm inset absorbs either value.

The sticker (cut line) is the tile less 1.0 mm on every side; 2.0 mm of background bleeds past
the cut; outside the bleed, after a 1.0 mm gap, a 4.0 mm cut mark 0.25 mm wide extends each cut
edge at each corner (8 per sticker); text stays 2.5 mm inside the cut. One sticker with its marks
needs the cut plus 7 mm on every side (the SVG canvas). The plaque sizes in studs (width x height
as the sticker is read) come from ``data/plaque_parts.json`` (``kit.plaque_parts``).

Coordinates: a geometry's boxes are in the sticker's cut coordinates (origin at the cut line's
top-left corner, y down); ``marks`` and ``cut_line`` take where that corner is placed.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from ..kit.plaque_parts import Plaque, PlaquePartTable, load_plaque_parts
from ..sheets.compose import PITCH
from ..sheets.model import BLACK, RGB, Line, Rect

PITCH_MM = PITCH          # 8.0 mm (LDraw), the build sheets' stud pitch
CLEARANCE_MM = 0.2        # tile = studs x pitch - clearance (LUGNET FAQ: "a small gap")
INSET_MM = 1.0            # cut line inside the tile edge, every side
BLEED_MM = 2.0            # background past the cut line
MARK_GAP_MM = 1.0         # bleed edge to cut mark
MARK_LENGTH_MM = 4.0
MARK_WIDTH_MM = 0.25
MARKS_PER_STICKER = 8     # two per corner, on the extensions of the cut edges
SAFE_MM = 2.5             # text safe area inside the cut line
MARGIN_MM = BLEED_MM + MARK_GAP_MM + MARK_LENGTH_MM   # cut line to canvas edge: 7.0 mm
MARK_COLOR: RGB = BLACK

Box = Tuple[float, float, float, float]   # x, y, width, height


def _mm(v: float) -> float:
    """A length rounded to 1/10000 mm, so 6 x 8.0 - 0.2 prints as 47.8."""
    return round(v, 4)


def tile_mm(studs: Tuple[int, int]) -> Tuple[float, float]:
    """The nominal outer size of a tile ``studs`` = (width, height) studs."""
    return tuple(_mm(n * PITCH_MM - CLEARANCE_MM) for n in studs)  # type: ignore[return-value]


@dataclass(frozen=True)
class StickerGeometry:
    """Sizes of one sticker (data-model.md StickerGeometry): the tile, the cut line inside it,
    the bleed, the cut marks, the text safe area and the canvas that holds it all."""

    size: str
    studs: Tuple[int, int]
    tile_mm: Tuple[float, float]
    cut_mm: Tuple[float, float]
    canvas_mm: Tuple[float, float]
    bleed_mm: float = BLEED_MM
    mark_gap_mm: float = MARK_GAP_MM
    mark_length_mm: float = MARK_LENGTH_MM
    mark_width_mm: float = MARK_WIDTH_MM
    safe_mm: float = SAFE_MM

    @classmethod
    def for_studs(cls, size: str, studs: Tuple[int, int]) -> "StickerGeometry":
        studs = (int(studs[0]), int(studs[1]))
        tile = tile_mm(studs)
        cut = tuple(_mm(t - 2 * INSET_MM) for t in tile)
        canvas = tuple(_mm(c + 2 * MARGIN_MM) for c in cut)
        return cls(size=size, studs=studs, tile_mm=tile, cut_mm=cut,  # type: ignore[arg-type]
                   canvas_mm=canvas)

    @property
    def margin_mm(self) -> float:
        """Cut line to canvas edge: bleed + gap + mark (7.0 mm)."""
        return _mm(self.bleed_mm + self.mark_gap_mm + self.mark_length_mm)

    @property
    def safe_box(self) -> Box:
        """The text safe area in cut coordinates."""
        w, h = self.cut_mm
        s = self.safe_mm
        return (s, s, _mm(w - 2 * s), _mm(h - 2 * s))

    @property
    def bleed_box(self) -> Box:
        """The printed background, past the cut line by the bleed on every side."""
        w, h = self.cut_mm
        b = self.bleed_mm
        return (-b, -b, _mm(w + 2 * b), _mm(h + 2 * b))

    def mark_segments(self) -> Tuple[Tuple[Tuple[float, float], Tuple[float, float]], ...]:
        """The 8 cut marks in cut coordinates: at each corner (top-left, top-right, bottom-left,
        bottom-right) one on the horizontal cut edge's extension, then one on the vertical's."""
        w, h = self.cut_mm
        near = self.bleed_mm + self.mark_gap_mm
        far = near + self.mark_length_mm
        out = []
        for cy, sy in ((0.0, -1.0), (h, 1.0)):
            for cx, sx in ((0.0, -1.0), (w, 1.0)):
                out.append(((cx + sx * far, cy), (cx + sx * near, cy)))
                out.append(((cx, cy + sy * far), (cx, cy + sy * near)))
        return tuple(out)

    def marks(self, x0: float, y0: float, data=()) -> List[Line]:
        """The cut marks as ``sheets.model`` lines, the cut line's top-left corner at (x0, y0)."""
        return [Line(_mm(x0 + a[0]), _mm(y0 + a[1]), _mm(x0 + b[0]), _mm(y0 + b[1]), MARK_COLOR,
                     self.mark_width_mm, tag="cut-mark", data=tuple(data))
                for a, b in self.mark_segments()]

    def cut_line(self, x0: float, y0: float, stroke: Optional[RGB] = None, stroke_w: float = 0.1,
                 data=()) -> Rect:
        """The cut line, a rectangle of the cut size. Unpainted by default (the PDF's ``re n``);
        the SVG writer gives it a hairline stroke."""
        w, h = self.cut_mm
        return Rect(x0, y0, w, h, fill=None, stroke=stroke, stroke_w=stroke_w, tag="cut-line",
                    data=tuple(data))


def geometry_for(plaque: Plaque) -> StickerGeometry:
    """The geometry of the sticker for ``plaque`` (its tile's studs)."""
    return StickerGeometry.for_studs(plaque.size, plaque.studs)


def sticker_geometry(size: str, plaque_parts: Optional[PlaquePartTable] = None) -> StickerGeometry:
    """The ``small`` or ``large`` sticker, sized from the packaged plaque parts."""
    table = plaque_parts if plaque_parts is not None else load_plaque_parts()
    if size not in table.plaques:
        raise KeyError(f"no plaque {size!r} (known: {', '.join(table.plaques)})")
    return geometry_for(table.plaques[size])

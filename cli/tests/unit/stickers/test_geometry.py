"""True-size sticker geometry (feature 017, T028; FR-009; research R1; data-model.md
StickerGeometry; contracts/sticker-files.md "Geometry").

Tile = studs x 8.0 - 0.2 mm, cut = tile - 2 x 1.0 mm, bleed 2.0 mm, cut marks (1.0 mm gap,
4.0 mm long, 0.25 mm wide, 8 per sticker), safe area 2.5 mm inside the cut, canvas = cut + 14 mm.
The plaque studs come from src/data/plaque_parts.json.
Not affiliated with or endorsed by The LEGO Group.
"""

import copy
import json

import pytest

from lego_image_processor.kit.plaque_parts import (PLAQUE_PARTS_PATH, load_plaque_parts,
                                                   parse_plaque_parts)
from lego_image_processor.sheets.compose import PITCH
from lego_image_processor.sheets.model import Line, Rect
from lego_image_processor.stickers import geometry as g
from lego_image_processor.stickers.geometry import StickerGeometry, geometry_for, sticker_geometry

TOL = 1e-9


def close(a, b, tol=TOL):
    return all(abs(x - y) <= tol for x, y in zip(a, b)) and len(a) == len(b)


class TestConstants:
    def test_values(self):
        assert g.PITCH_MM == 8.0 == PITCH           # the build sheets' stud pitch (LDraw)
        assert g.CLEARANCE_MM == 0.2
        assert g.INSET_MM == 1.0
        assert g.BLEED_MM == 2.0
        assert (g.MARK_GAP_MM, g.MARK_LENGTH_MM, g.MARK_WIDTH_MM) == (1.0, 4.0, 0.25)
        assert g.MARKS_PER_STICKER == 8
        assert g.SAFE_MM == 2.5
        assert g.MARGIN_MM == 7.0                    # bleed + gap + mark: cut line to canvas edge

    def test_docstring_cites_ldraw_and_lugnet(self):
        doc = g.__doc__
        assert "LDraw" in doc and "LUGNET" in doc
        assert "https://www.lugnet.com/~330/FAQ/Build/dimensions" in doc
        assert "Not affiliated with or endorsed by The LEGO Group." in doc

    def test_tile_formula(self):
        assert close(g.tile_mm((6, 6)), (47.8, 47.8))
        assert close(g.tile_mm((16, 8)), (127.8, 63.8))
        assert close(g.tile_mm((1, 2)), (7.8, 15.8))


class TestSizes:
    def test_small(self):
        s = sticker_geometry("small")
        assert s.size == "small" and s.studs == (6, 6)
        assert close(s.tile_mm, (47.8, 47.8))
        assert close(s.cut_mm, (45.8, 45.8))
        assert close(s.canvas_mm, (59.8, 59.8))
        assert s.bleed_mm == 2.0 and s.safe_mm == 2.5
        assert close(s.safe_box, (2.5, 2.5, 40.8, 40.8))

    def test_large_landscape(self):
        s = sticker_geometry("large")
        assert s.size == "large" and s.studs == (16, 8)
        assert close(s.tile_mm, (127.8, 63.8))
        assert close(s.cut_mm, (125.8, 61.8))
        assert close(s.canvas_mm, (139.8, 75.8))
        assert close(s.safe_box, (2.5, 2.5, 120.8, 56.8))

    def test_formulas_hold(self):
        for size in ("small", "large"):
            s = sticker_geometry(size)
            for i in (0, 1):
                assert abs(s.tile_mm[i] - (s.studs[i] * 8.0 - 0.2)) <= TOL
                assert abs(s.cut_mm[i] - (s.tile_mm[i] - 2 * 1.0)) <= TOL
                assert abs(s.canvas_mm[i] - (s.cut_mm[i] + 14.0)) <= TOL

    def test_values_are_rounded_for_output(self):
        # JSON and SVG print these: no float noise such as 47.800000000000004
        s = sticker_geometry("small")
        assert [repr(v) for v in s.tile_mm + s.cut_mm + s.canvas_mm] == [
            "47.8", "47.8", "45.8", "45.8", "59.8", "59.8"]

    def test_unknown_size(self):
        with pytest.raises(KeyError, match="medium"):
            sticker_geometry("medium")


class TestFromPlaqueParts:
    def test_studs_read_from_the_packaged_file(self):
        table = load_plaque_parts()
        for size in ("small", "large"):
            assert sticker_geometry(size).studs == table.plaques[size].studs
            assert geometry_for(table.plaques[size]) == sticker_geometry(size)

    def test_other_studs_in_the_file_give_other_sizes(self):
        data = json.loads(PLAQUE_PARTS_PATH.read_text(encoding="utf-8"))
        changed = copy.deepcopy(data)
        changed["plaques"]["small"]["studs"] = [4, 4]
        for pid in (changed["plaques"]["small"]["tile"], changed["plaques"]["small"]["plate"]):
            changed["parts"][pid]["studs"] = [4, 4]
        table = parse_plaque_parts(changed)
        s = sticker_geometry("small", table)
        assert s.studs == (4, 4)
        assert close(s.tile_mm, (31.8, 31.8)) and close(s.cut_mm, (29.8, 29.8))
        assert close(s.canvas_mm, (43.8, 43.8))


class TestBoxesAndMarks:
    @pytest.mark.parametrize("size", ["small", "large"])
    def test_bleed_box(self, size):
        s = sticker_geometry(size)
        w, h = s.cut_mm
        assert close(s.bleed_box, (-2.0, -2.0, w + 4.0, h + 4.0))

    @pytest.mark.parametrize("size", ["small", "large"])
    def test_eight_marks_outside_the_bleed(self, size):
        s = sticker_geometry(size)
        w, h = s.cut_mm
        x0, y0 = 19.0, 41.0
        marks = s.marks(x0, y0)
        assert len(marks) == 8
        assert all(isinstance(m, Line) and m.tag == "cut-mark" for m in marks)
        assert all(m.w == 0.25 for m in marks)
        horizontal = [m for m in marks if m.y1 == m.y2]
        vertical = [m for m in marks if m.x1 == m.x2]
        assert len(horizontal) == 4 and len(vertical) == 4
        for m in marks:
            length = abs(m.x2 - m.x1) + abs(m.y2 - m.y1)
            assert abs(length - 4.0) <= TOL
        # each mark lies on the extension of a cut edge, starting 3 mm (bleed 2 + gap 1) past
        # the cut line and ending 7 mm past it
        for m in horizontal:
            assert m.y1 in (y0, y0 + h)
            xs = sorted((m.x1 - x0, m.x2 - x0))
            assert close(xs, (-7.0, -3.0)) or close(xs, (w + 3.0, w + 7.0))
        for m in vertical:
            assert m.x1 in (x0, x0 + w)
            ys = sorted((m.y1 - y0, m.y2 - y0))
            assert close(ys, (-7.0, -3.0)) or close(ys, (h + 3.0, h + 7.0))
        # two marks at every corner
        corners = {(x0 + cx, y0 + cy) for cx in (0, w) for cy in (0, h)}
        for cx, cy in corners:
            near = [m for m in marks if (m.y1 == cy and min(abs(m.x1 - cx), abs(m.x2 - cx)) <= 3.0 + TOL)
                    or (m.x1 == cx and min(abs(m.y1 - cy), abs(m.y2 - cy)) <= 3.0 + TOL)]
            assert len(near) == 2
        # the marks stay inside the canvas
        cw, ch = s.canvas_mm
        for m in marks:
            for x, y in ((m.x1, m.y1), (m.x2, m.y2)):
                assert x0 - 7.0 - TOL <= x <= x0 - 7.0 + cw + TOL
                assert y0 - 7.0 - TOL <= y <= y0 - 7.0 + ch + TOL

    @pytest.mark.parametrize("size", ["small", "large"])
    def test_cut_line(self, size):
        s = sticker_geometry(size)
        r = s.cut_line(7.0, 7.0)
        assert isinstance(r, Rect) and r.tag == "cut-line"
        assert (r.x, r.y) == (7.0, 7.0)
        assert abs(r.w - s.cut_mm[0]) <= 0.1 and abs(r.h - s.cut_mm[1]) <= 0.1   # SC-001
        assert r.fill is None and r.stroke is None          # unpainted in the PDF (re n)
        svg = s.cut_line(7.0, 7.0, stroke=(255, 0, 255), stroke_w=0.1)
        assert svg.stroke == (255, 0, 255) and svg.stroke_w == 0.1 and svg.fill is None

    def test_geometry_is_a_value(self):
        assert sticker_geometry("small") == sticker_geometry("small")
        assert isinstance(sticker_geometry("large"), StickerGeometry)
        assert hash(sticker_geometry("large")) == hash(sticker_geometry("large"))

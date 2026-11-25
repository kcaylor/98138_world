"""In-margin plaque: placement (feature 017 T063; FR-022; research R15; contracts/in-margin-plaque.md
"Placement"; data-model.md InMarginPlaque).

The small plaque's tile (``load_plaque_parts().plaques["small"].tile``: 6 x 6 studs, Black) sits one
stud in from both board edges of its corner. The checks, in order: the template is not the kit; all
36 studs are margin studs inside the corner's clear block (the loaded template's ``counts.corners``,
never hard-coded here); they lie in one 16 x 16 module; no outline-ring stud is within one stud
(Chebyshev distance 1). Run on ``confirmed_winkel`` and 016's ``synthetic_template``.
Not affiliated with or endorsed by The LEGO Group.
"""

import json

import numpy as np
import pytest

from lego_image_processor.kit.plaque_parts import load_plaque_parts
from lego_image_processor.maps.margin import (InMarginPlaque, MarginTreatment, PlaqueError, margin_cells,
                                              place_plaque, plaque_for, plaque_misfit, plaque_studs,
                                              ring_cells)
from lego_image_processor.templates import kit_template, parse_template
from lego_image_processor.templates.board import MODULE, board_counts

# contracts/in-margin-plaque.md "Placement": rows, columns (0-based, as 016's), module
TABLE = {"top-left": ((1, 6), (1, 6), "A1"), "top-right": ((1, 6), (121, 126), "H1"),
         "bottom-left": ((73, 78), (1, 6), "A5"), "bottom-right": ((73, 78), (121, 126), "H5")}
NEEDS = "needs 6 x 6 studs plus one stud from the outline ring"


def _tile():
    return load_plaque_parts().plaques["small"].tile


@pytest.fixture(params=["confirmed_winkel", "synthetic_template"])
def template(request):
    return request.getfixturevalue(request.param)


def _inside(studs, block):
    return (block["row"] <= studs["row"] and studs["row"] + studs["height"] <= block["row"] + block["height"]
            and block["col"] <= studs["col"] and studs["col"] + studs["width"] <= block["col"] + block["width"])


class TestPlacementTable:
    @pytest.mark.parametrize("corner", list(TABLE))
    def test_one_stud_in_from_both_board_edges(self, template, corner):
        (r0, r1), (c0, c1), module = TABLE[corner]
        p = place_plaque(template, corner, "option")
        assert isinstance(p, InMarginPlaque)
        assert p.studs == {"row": r0, "col": c0, "height": r1 - r0 + 1, "width": c1 - c0 + 1}
        assert plaque_studs(template, corner) == p.studs
        assert template.section_label(r0, c0) == module == template.section_label(r1, c1)
        top, left = corner.split("-")
        assert (r0 == 1) if top == "top" else (r1 == template.height - 2)
        assert (c0 == 1) if left == "left" else (c1 == template.width - 2)

    @pytest.mark.parametrize("corner", list(TABLE))
    def test_inside_the_loaded_clear_block(self, template, corner):
        p = place_plaque(template, corner, "option")
        block = template.counts["corners"][corner]
        assert _inside(p.studs, block)
        m = p.mask((template.height, template.width))
        assert m.sum() == p.cells == 36
        assert np.asarray(template.margin)[m].all() and not ring_cells(template)[m].any()
        r, c = p.studs["row"], p.studs["col"]
        assert len({(y // MODULE, x // MODULE) for y in range(r, r + 6) for x in range(c, c + 6)}) == 1
        near = np.zeros_like(m)
        near[max(r - 1, 0):r + 7, max(c - 1, 0):c + 7] = True
        assert not ring_cells(template)[near].any()

    def test_ids_from_plaque_parts(self, template):
        tile = _tile()
        p = place_plaque(template, "bottom-left", "recipe")
        assert (p.part_id, p.color) == (tile.part_id, tile.color.key) == ("10202", "lego_black")
        assert (p.studs["width"], p.studs["height"]) == tile.studs
        assert (p.corner, p.source) == ("bottom-left", "recipe")

    def test_records(self, template):
        p = place_plaque(template, "bottom-left", "option")
        studs = {"row": 73, "col": 1, "height": 6, "width": 6}
        assert p.layout_record() == {"part_id": "10202", "color": "lego_black", "corner": "bottom-left",
                                     "studs": studs, "cells": 36}
        assert list(p.layout_record()) == ["part_id", "color", "corner", "studs", "cells"]
        assert p.report_record() == {"corner": "bottom-left", "source": "option", "studs": studs,
                                     "part_id": "10202"}
        assert p.positions() == frozenset((x, y) for y in range(73, 79) for x in range(1, 7))


class TestChecks:
    def test_kit_first(self, confirmed_winkel):
        with pytest.raises(PlaqueError) as e:
            place_plaque(kit_template(), "bottom-left", "option")
        msg = str(e.value)
        assert e.value.where == "--plaque" and "the kit template has no margin" in msg
        assert "winkel-tripel" in msg  # the templates with a margin

    def test_unknown_corner(self, template):
        with pytest.raises(PlaqueError):
            place_plaque(template, "middle", "option")

    def test_misfit_in_a_smaller_corner_block(self, tmp_path):
        """A temporary template copy whose bottom-left corner has an ocean stud near the plaque."""
        from lego_image_processor.templates import TEMPLATE_DIR

        doc = json.loads((TEMPLATE_DIR / "winkel-tripel.json").read_text(encoding="utf-8"))
        rows = [list(r) for r in doc["classes"]]
        rows[75][7] = "O"
        doc["classes"] = ["".join(r) for r in rows]
        doc["locations"]["lat"][75][7] = -55.0
        doc["locations"]["lon"][75][7] = -170.0
        doc["counts"] = board_counts(doc["classes"])
        t = parse_template(doc, "winkel-tripel.json")
        block = t.counts["corners"]["bottom-left"]
        assert not _inside({"row": 73, "col": 1, "height": 6, "width": 6}, block)
        for source, where in (("option", "--plaque"), ("recipe", "margin.plaque")):
            with pytest.raises(PlaqueError) as e:
                place_plaque(t, "bottom-left", source)
            msg = str(e.value)
            assert e.value.where == where and msg.startswith(where)
            assert "bottom-left" in msg and NEEDS in msg
            assert f"{block['height']} x {block['width']} studs" in msg  # the block's size
        # the other corners still fit
        assert place_plaque(t, "top-right", "option").corner == "top-right"

    def test_module_check(self, confirmed_winkel):
        """A 6 x 6 block that crosses a module boundary is refused even inside a clear block."""
        t = confirmed_winkel
        studs = {"row": 13, "col": 1, "height": 6, "width": 6}  # rows 13-18 cross row 16
        why = plaque_misfit(t, "top-left", studs, block={"row": 0, "col": 0, "height": 80, "width": 128},
                            margin=np.ones((t.height, t.width), dtype=bool),
                            ring=np.zeros((t.height, t.width), dtype=bool))
        assert why is not None and "16 x 16 module" in why

    def test_ring_check(self, confirmed_winkel):
        """A ring stud one stud (diagonally) from the tile is refused."""
        t = confirmed_winkel
        studs = {"row": 1, "col": 1, "height": 6, "width": 6}
        ring = np.zeros((t.height, t.width), dtype=bool)
        ring[7, 7] = True  # Chebyshev distance 1 from (6, 6)
        why = plaque_misfit(t, "top-left", studs, block={"row": 0, "col": 0, "height": 14, "width": 14},
                            margin=np.ones((t.height, t.width), dtype=bool), ring=ring)
        assert why is not None and "outline ring" in why
        ring[7, 7], ring[8, 8] = False, True  # distance 2: fits
        assert plaque_misfit(t, "top-left", studs, block={"row": 0, "col": 0, "height": 14, "width": 14},
                             margin=np.ones((t.height, t.width), dtype=bool), ring=ring) is None

    def test_margin_check(self, confirmed_winkel):
        t = confirmed_winkel
        studs = {"row": 1, "col": 1, "height": 6, "width": 6}
        margin = np.ones((t.height, t.width), dtype=bool)
        margin[3, 3] = False  # an on-globe stud under the tile
        why = plaque_misfit(t, "top-left", studs, block={"row": 0, "col": 0, "height": 14, "width": 14},
                            margin=margin, ring=np.zeros_like(margin))
        assert why is not None and "margin" in why


class TestTreatment:
    """The plaque is part of 016's margin treatment; it never covers ring studs and does not change
    the margin or ring colors."""

    def test_plaque_for(self, confirmed_winkel):
        assert plaque_for(confirmed_winkel, MarginTreatment()) is None
        p = plaque_for(confirmed_winkel, MarginTreatment(plaque="top-right", plaque_source="recipe"))
        assert (p.corner, p.source) == ("top-right", "recipe")

    def test_kit_ignores_a_recipe_corner_and_refuses_an_option(self, confirmed_winkel):
        kit = kit_template()
        assert plaque_for(kit, MarginTreatment(plaque="top-left", plaque_source="recipe")) is None
        with pytest.raises(PlaqueError, match="the kit template has no margin"):
            plaque_for(kit, MarginTreatment(plaque="top-left", plaque_source="option"))

    @pytest.mark.parametrize("ring", [None, "lego_bright_yellow"])
    def test_margin_cells_leave_the_plaque_out(self, template, ring):
        c = template.counts
        plain = margin_cells(template, MarginTreatment(ring=ring))
        with_plaque = margin_cells(template, MarginTreatment(ring=ring, plaque="bottom-left", plaque_source="option"))
        assert plain["margin"] + plain["ring"] == c["margin"]
        assert with_plaque == {"margin": plain["margin"] - 36, "ring": plain["ring"]}

    def test_any_margin_or_ring_color(self, template):
        for t in (MarginTreatment(color="lego_white", plaque="top-left", plaque_source="option"),
                  MarginTreatment(color="lego_black", ring="lego_white", plaque="top-left", plaque_source="option")):
            p = plaque_for(template, t)
            assert p.color == "lego_black"  # Black regardless of --margin-color

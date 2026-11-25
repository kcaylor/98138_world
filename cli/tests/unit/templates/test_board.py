"""Board helpers of the templates package (feature 016, T021): moved from the projection study
(``tools/projection_study/raster.py``), plus the corner free regions and the derived counts."""

import numpy as np
import pytest

from lego_image_processor.templates.board import (CORNERS, board_counts, corner_blocks,
                                                  corner_free_regions, largest_rectangle,
                                                  module_stats, rim_cells)


# --- moved from tests/unit/tools/test_projection_study.py -------------------------------------

def test_module_stats_counts_full_partial_empty():
    on = np.zeros((16, 48), dtype=bool)
    on[:, :16] = True          # full
    on[0, 20] = True           # partial
    assert module_stats(on) == (1, 1, 1)


def test_module_stats_rejects_partial_modules():
    with pytest.raises(ValueError):
        module_stats(np.ones((16, 20), dtype=bool))


def test_rim_is_the_four_neighbour_ring():
    on = np.zeros((5, 5), dtype=bool)
    on[2, 2] = True
    rim = rim_cells(on)
    assert rim.sum() == 4
    assert rim[1, 2] and rim[3, 2] and rim[2, 1] and rim[2, 3]
    assert not rim[1, 1]


def test_largest_rectangle():
    free = np.zeros((6, 8), dtype=bool)
    free[1:4, 2:7] = True      # 3 × 5
    free[5, :] = True          # 1 × 8
    assert largest_rectangle(free) == (1, 2, 3, 5)


# --- corner free regions (margin minus the outline ring, per board quadrant) --------------------

def _ellipse(h=80, w=128, ry=36.0, rx=58.0):
    r, c = np.mgrid[0:h, 0:w]
    return ((r + 0.5 - h / 2) / ry) ** 2 + ((c + 0.5 - w / 2) / rx) ** 2 <= 1.0


def test_rim_never_on_the_globe_and_board_edge_counts_as_off():
    on = np.ones((4, 4), dtype=bool)
    assert not rim_cells(on).any()          # no margin, no ring
    on[0, 0] = False
    rim = rim_cells(on)
    assert rim.tolist()[0][0] and rim.sum() == 1


def test_corner_free_regions_are_margin_minus_ring_per_quadrant():
    on = _ellipse()
    regions = corner_free_regions(on)
    assert tuple(regions) == CORNERS == ("top-left", "top-right", "bottom-left", "bottom-right")
    free = ~on & ~rim_cells(on)
    union = np.zeros_like(on)
    for name, mask in regions.items():
        assert mask.shape == on.shape
        assert not (mask & on).any() and not (mask & rim_cells(on)).any()
        assert not (union & mask).any()     # quadrants do not overlap
        union |= mask
    assert (union == free).all()
    assert regions["top-left"][:40, :64].sum() == regions["top-left"].sum()
    assert regions["bottom-right"][40:, 64:].sum() == regions["bottom-right"].sum()


def test_corner_blocks_are_board_coordinates_inside_their_quadrant():
    on = _ellipse()
    blocks = corner_blocks(on)
    assert tuple(blocks) == CORNERS
    free = ~on & ~rim_cells(on)
    for name, b in blocks.items():
        assert set(b) == {"row", "col", "height", "width"}
        assert b["height"] > 0 and b["width"] > 0
        assert free[b["row"]:b["row"] + b["height"], b["col"]:b["col"] + b["width"]].all()
    tl, br = blocks["top-left"], blocks["bottom-right"]
    assert tl["row"] + tl["height"] <= 40 and tl["col"] + tl["width"] <= 64
    assert br["row"] >= 40 and br["col"] >= 64
    # The ellipse is symmetric, so the four blocks have the same size.
    assert len({(b["height"], b["width"]) for b in blocks.values()}) == 1


def test_corner_blocks_on_a_full_board_are_empty():
    blocks = corner_blocks(np.ones((80, 128), dtype=bool))
    assert all(b["height"] == 0 and b["width"] == 0 for b in blocks.values())


def test_board_counts_from_classes():
    on = _ellipse()
    land = on & (np.arange(128)[None, :] < 50)
    classes = np.where(land, "L", np.where(on, "O", "M"))
    counts = board_counts(classes)
    assert list(counts) == ["land", "ocean", "margin", "ring", "modules", "corners"]
    assert counts["land"] == int(land.sum())
    assert counts["ocean"] == int((on & ~land).sum())
    assert counts["margin"] == int((~on).sum())
    assert counts["land"] + counts["ocean"] + counts["margin"] == 10240
    assert counts["ring"] == int(rim_cells(on).sum())
    full, partial, empty = module_stats(on)
    assert counts["modules"] == {"full": full, "partial": partial, "empty": empty}
    assert counts["corners"] == corner_blocks(on)


def test_board_counts_accepts_row_strings():
    rows = ["L" * 64 + "O" * 64] * 80
    counts = board_counts(rows)
    assert (counts["land"], counts["ocean"], counts["margin"], counts["ring"]) == (5120, 5120, 0, 0)
    assert counts["modules"] == {"full": 40, "partial": 0, "empty": 0}

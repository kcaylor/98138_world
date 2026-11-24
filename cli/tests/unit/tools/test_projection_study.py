"""Offline tests for the projection study's pure helpers (no pyproj, no dataset)."""

import numpy as np
import pytest

from projection_study.candidates import KIT_ASPECT, LON0, WINKEL, cea_standard_parallel
from projection_study.raster import classify, largest_rectangle, module_stats, rim_cells


def test_kit_centre_meridian_is_11_1_east():
    assert LON0 == pytest.approx(11.1)


def test_winkel_sets_standard_parallel_explicitly():
    # PROJ's wintri defaults to lat_1 = 0; the study depends on Winkel's 50.4598°.
    assert "+lat_1=50.4598" in WINKEL


def test_equal_area_cylindrical_parallel_for_kit_aspect():
    # width/height = π cos²φ  ⇒  φ = arccos(sqrt(aspect/π))
    phi = cea_standard_parallel(KIT_ASPECT)
    assert np.pi * np.cos(np.radians(phi)) ** 2 == pytest.approx(KIT_ASPECT)


def test_classify_thresholds():
    cover = np.array([[1.0, 0.5, 0.49]])
    landfrac = np.array([[0.5, 0.2, 1.0]])
    on, land, ocean = classify(cover, landfrac)
    assert on.tolist() == [[True, True, False]]
    assert land.tolist() == [[True, False, False]]
    assert ocean.tolist() == [[False, True, False]]


def test_board_helpers_come_from_the_package():
    # Moved to lego_image_processor.templates.board in feature 016; their tests are in
    # tests/unit/templates/test_board.py.
    from lego_image_processor.templates import board

    assert (module_stats, rim_cells, largest_rectangle) == (board.module_stats, board.rim_cells,
                                                            board.largest_rectangle)

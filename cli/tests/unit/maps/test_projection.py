"""Kit projection (FR-013; data-model.md KitProjection)."""

import numpy as np

from lego_image_processor.maps.projection import load_kit_projection


def test_shipped_file():
    p = load_kit_projection()
    assert p.model == "equirectangular"
    assert (p.width, p.height) == (128, 80)
    assert p.deg_per_col == 2.8125
    assert p.agreement["equirectangular"] > p.agreement["miller"] > p.agreement["mercator"]
    assert p.source["disclaimer"] == "Not affiliated with or endorsed by The LEGO Group."


def test_columns():
    p = load_kit_projection()
    left = p.left_edge_lon
    cols = p.cols_for_lon(np.array([left + 0.01, left + 2.8125 + 0.01, left - 0.01, left + 360.01, 180.0]))
    assert cols[:4].tolist() == [0, 1, 127, 0]
    assert 0 <= cols[4] < 128


def test_rows():
    p = load_kit_projection()
    rows = p.rows_for_lat(np.array([0.0, 89.8, -82.0, 1.0, -1.0]))
    assert rows[0] == 42
    assert rows[1] == 0
    assert rows[2] == 79
    assert rows[3] < rows[0] <= rows[4]


def test_outside_rows_dropped():
    p = load_kit_projection()
    rows = p.rows_for_lat(np.array([-89.0, 90.0 + 5]))
    assert rows.tolist() == [-1, -1]


def test_cell_centers_round_trip():
    p = load_kit_projection()
    lat, lon = p.cell_center(10, 20)
    assert p.rows_for_lat(np.array([lat]))[0] == 10
    assert p.cols_for_lon(np.array([lon]))[0] == 20

"""Forward Winkel tripel in numpy (feature 016, research R1; T023).

Reference values below were computed with pyproj 3.7.2 (PROJ 9.5.1) for
``+proj=wintri +lat_1=50.4598 +lon_0=11.1 +R=1`` from ``+proj=longlat +R=1 +no_defs``
(``always_xy=True``) on 2026-11-23. The 200,000-point comparison runs only when pyproj is
installed (``poetry install --with maintainer``); the run time never needs it.
"""

import math

import numpy as np
import pytest

from lego_image_processor.templates import winkel

PHI1 = math.radians(50.4598)
X_EDGE = (math.pi / 2) * (1 + math.cos(PHI1))

# (lon, lat, x, y) from pyproj 3.7.2 / PROJ 9.5.1
PYPROJ_REFERENCE = [
    (11.1, 0.0, 0.0, 0.0),
    (-168.9, 0.0, -2.5707958247119955, 0.0),
    (-168.9, 45.0, -2.1107202324566905, 0.9480594489685199),
    (0.0, 51.5, -0.13089669852581207, 0.8993767387999227),
    (-74.0, 40.7, -1.077364847965164, 0.739677224123964),
    (151.2, -33.9, 1.8226066505562195, -0.6690938023343065),
    (18.4, -33.9, 0.09664317589945971, -0.5918471239634847),
    (139.7, 35.7, 1.6611781901861968, 0.689032568376136),
    (-58.4, -34.6, -0.9135331094495076, -0.6211053515789078),
    (37.6, 55.8, 0.2998803419296587, 0.9769759350118563),
    (-150.0, 61.2, -1.6060670814710973, 1.1896813929987975),
    (100.0, -89.0, 0.5129356292637807, -1.5557820126541837),
    (-45.0, 89.5, -0.3180809889242094, 1.562575637091611),
    (179.9, 10.0, 2.3897125716872685, 0.21588800247215312),
    (-179.9, -10.0, 2.392523398927813, -0.2160167369878413),
    (-170.0, 70.0, 1.5299876724018433, 1.3473595073864377),
]


def test_parameters_and_proj_string():
    assert winkel.NAME == "winkel-tripel"
    assert winkel.LAT_1 == 50.4598 and winkel.LON_0 == 11.1
    assert winkel.proj_string() == "+proj=wintri +lat_1=50.4598 +lon_0=11.1 +R=1"
    assert winkel.proj_string(40.0, -150.0) == "+proj=wintri +lat_1=40 +lon_0=-150 +R=1"
    assert "Winkel" in winkel.CITATION and "Snyder" in winkel.CITATION and "proj.org" in winkel.CITATION


def test_exact_extent():
    x0, x1, y0, y1 = winkel.extent()
    assert x0 == pytest.approx(-X_EDGE, abs=1e-15) and x1 == pytest.approx(X_EDGE, abs=1e-15)
    assert y0 == -math.pi / 2 and y1 == math.pi / 2
    assert (x1 - x0) / (y1 - y0) == pytest.approx(1.6366, abs=1e-4)


def test_centre_maps_to_origin():
    x, y = winkel.forward(11.1, 0.0)
    assert float(x) == 0.0 and float(y) == 0.0


def test_antimeridian_edges():
    x, y = winkel.forward(-168.9, 0.0)                     # lon_0 - 180: the left edge
    assert float(x) == pytest.approx(-X_EDGE, abs=1e-12) and abs(float(y)) < 1e-15
    x, y = winkel.forward(-168.9 - 1e-9, 0.0)              # just past it: the right edge
    assert float(x) == pytest.approx(X_EDGE, abs=1e-9)
    x, y = winkel.forward(-168.9 + 1e-9, 0.0)
    assert float(x) == pytest.approx(-X_EDGE, abs=1e-9)


def test_poles_are_lines():
    lon = np.array([-168.9, -100.0, 11.1, 100.0])
    x, y = winkel.forward(lon, np.full(4, 90.0))
    assert np.allclose(y, math.pi / 2, atol=1e-15)
    dl = np.radians(lon - 11.1)
    assert np.allclose(x, 0.5 * dl * math.cos(PHI1), atol=1e-12)
    x, y = winkel.forward(lon, np.full(4, -90.0))
    assert np.allclose(y, -math.pi / 2, atol=1e-15)


def test_left_right_and_top_bottom_symmetry():
    rng = np.random.default_rng(16)
    d = rng.uniform(0, 180, 1000)
    lat = rng.uniform(-90, 90, 1000)
    xe, ye = winkel.forward(11.1 + d, lat)
    xw, yw = winkel.forward(11.1 - d, lat)
    assert np.allclose(xe, -xw, atol=1e-12) and np.allclose(ye, yw, atol=1e-12)
    xs, ys = winkel.forward(11.1 + d, -lat)
    assert np.allclose(xs, xe, atol=1e-12) and np.allclose(ys, -ye, atol=1e-12)


@pytest.mark.parametrize("lon,lat,x,y", PYPROJ_REFERENCE)
def test_matches_pyproj_reference_values(lon, lat, x, y):
    fx, fy = winkel.forward(lon, lat)
    assert abs(float(fx) - x) < 1e-9 and abs(float(fy) - y) < 1e-9


def test_vectorised_shapes_and_broadcasting():
    lat = np.array([[-30.0], [0.0], [30.0]])
    lon = np.array([[-90.0, 0.0, 90.0, 170.0]])
    x, y = winkel.forward(lon, lat)
    assert x.shape == y.shape == (3, 4)
    for i in range(3):
        for j in range(4):
            sx, sy = winkel.forward(float(lon[0, j]), float(lat[i, 0]))
            assert x[i, j] == float(sx) and y[i, j] == float(sy)


def test_chunks_give_the_same_result(monkeypatch):
    rng = np.random.default_rng(3)
    lon, lat = rng.uniform(-180, 180, 2501), rng.uniform(-90, 90, 2501)
    whole = winkel.forward(lon, lat)
    monkeypatch.setattr(winkel, "CHUNK", 1000)
    parts = winkel.forward(lon, lat)
    assert np.array_equal(whole[0], parts[0]) and np.array_equal(whole[1], parts[1])
    assert winkel.CHUNK == 1000


def test_default_chunk_is_a_million_points():
    assert winkel.CHUNK == 1_000_000


def test_invalid_input_is_nan():
    x, y = winkel.forward(np.array([0.0, 0.0, np.nan, 0.0]), np.array([90.5, -91.0, 0.0, np.inf]))
    assert np.isnan(x).all() and np.isnan(y).all()
    x, y = winkel.forward(0.0, 90.0 + 1e-14)                  # within PROJ's tolerance: clamped
    assert float(y) == pytest.approx(math.pi / 2, abs=1e-12)


def test_outline_is_the_image_of_the_edge_meridian():
    lat = np.linspace(-90, 90, 721)
    x, y = winkel.forward(np.full(lat.size, -168.9), lat)
    assert np.allclose(winkel.edge_x(y), -x, atol=1e-12)
    assert winkel.edge_x(0.0) == pytest.approx(X_EDGE, abs=1e-15)
    assert winkel.edge_x(math.pi / 2) == pytest.approx((math.pi / 2) * math.cos(PHI1), abs=1e-12)
    assert np.isnan(winkel.edge_x(1.6))


def test_every_projected_point_lies_in_the_outline():
    rng = np.random.default_rng(7)
    x, y = winkel.forward(rng.uniform(-180, 180, 20000), rng.uniform(-90, 90, 20000))
    assert winkel.outline_contains(x, y, tol=1e-12).all()
    assert not winkel.outline_contains(np.array([X_EDGE + 1e-6, 0.0]), np.array([0.0, math.pi / 2 + 1e-6])).any()
    assert winkel.outline_contains(np.array([0.0]), np.array([0.0])).all()


def test_fit_contains_the_extent_on_the_board():
    f = winkel.fit(128, 80)
    x0, x1, y0, y1 = winkel.extent()
    assert f["mode"] == "contain"
    assert f["extent"] == [x0, x1, y0, y1]
    assert f["scale"] == min(128 / (x1 - x0), 80 / (y1 - y0)) == 128 / (x1 - x0)
    assert f["centre"] == [0.0, 0.0]


def test_check_points():
    assert len(winkel.CHECK_POINTS) == 24
    assert len(set(winkel.CHECK_POINTS)) == 24
    pts = winkel.check_points()
    assert len(pts) == 24 and all(len(p) == 4 for p in pts)
    for lon, lat, x, y in pts:
        assert -180 <= lon <= 180 and -90 <= lat <= 90
        fx, fy = winkel.forward(lon, lat)
        assert (float(fx), float(fy)) == (x, y)


def test_200000_points_against_pyproj():
    pyproj = pytest.importorskip("pyproj")
    t = pyproj.Transformer.from_crs("+proj=longlat +R=1 +no_defs", winkel.proj_string(), always_xy=True)
    rng = np.random.default_rng(2026)
    lon = rng.uniform(-180, 180, 200_000)
    lat = np.degrees(np.arcsin(rng.uniform(-1, 1, 200_000)))
    lon[:8] = [-168.9, -168.9, -168.9, 11.1, 11.1, 180.0, -180.0, 0.0]
    lat[:8] = [0.0, 89.9, -89.9, 90.0, -90.0, 0.0, 0.0, 0.0]
    px, py = t.transform(lon, lat)
    fx, fy = winkel.forward(lon, lat)
    assert np.max(np.abs(fx - px)) < 1e-9 and np.max(np.abs(fy - py)) < 1e-9
    for lon_, lat_ in winkel.CHECK_POINTS:
        x, y = t.transform(lon_, lat_)
        fx_, fy_ = winkel.forward(lon_, lat_)
        assert abs(float(fx_) - x) < 1e-9 and abs(float(fy_) - y) < 1e-9

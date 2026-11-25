"""Stud ↔ location lookups (feature 016, T028; FR-005; data-model.md TemplateProjection).

Non-kit lookups use the committed synthetic template (``synthetic_template`` fixture, T030).
"""

import numpy as np
import pytest

from lego_image_processor.maps.projection import load_kit_projection
from lego_image_processor.templates import KIT_TEMPLATE_ID, load_template, winkel
from lego_image_processor.templates.geometry import TemplateProjection, from_board, to_board


@pytest.fixture
def proj(synthetic_template):
    return synthetic_template.grid_projection


def _centres(t):
    cc, rr = np.meshgrid(np.arange(t.width) + 0.5, np.arange(t.height) + 0.5)
    return from_board(cc, rr, t.projection["fit"], t.width, t.height)


def test_projection_size_and_type(proj):
    assert isinstance(proj, TemplateProjection)
    assert (proj.height, proj.width) == (80, 128)


def test_board_round_trip():
    fit = winkel.fit(128, 80)
    cx, ry = np.array([0.0, 64.0, 127.9]), np.array([0.0, 40.0, 79.9])
    x, y = from_board(cx, ry, fit, 128, 80)
    bx, by = to_board(x, y, fit, 128, 80)
    assert np.allclose(bx, cx, atol=1e-12) and np.allclose(by, ry, atol=1e-12)
    assert from_board(64.0, 40.0, fit, 128, 80) == (0.0, 0.0)


def test_locations_nan_exactly_on_margin(synthetic_template, proj):
    lat, lon = proj.locations()
    assert lat.shape == lon.shape == (80, 128)
    m = synthetic_template.margin
    assert np.isnan(lat[m]).all() and np.isnan(lon[m]).all()
    assert np.isfinite(lat[~m]).all() and np.isfinite(lon[~m]).all()
    tlat, tlon = synthetic_template.locations()
    assert np.array_equal(lat, tlat, equal_nan=True) and np.array_equal(lon, tlon, equal_nan=True)
    lat[0, 0] = 1.0  # a copy
    assert np.isnan(proj.locations()[0][0, 0])


def test_abs_lat(proj):
    lat, _ = proj.locations()
    assert np.array_equal(proj.abs_lat(), np.abs(lat), equal_nan=True)


def test_cells_for_on_globe_studs(synthetic_template, proj):
    lat, lon = proj.locations()
    on = synthetic_template.on_globe
    idx = proj.cells_for(lat, lon)
    assert idx.shape == (80, 128)
    assert (idx[~on] == -1).all()                       # NaN locations (margin) are off
    flat = np.arange(80 * 128).reshape(80, 128)
    x, y = _centres(synthetic_template)
    inside = winkel.outline_contains(x, y)
    assert (idx[on & inside] == flat[on & inside]).all()


def test_cells_for_is_minus_one_on_a_margin_stud(synthetic_template, proj):
    # Points on the globe whose stud is a margin stud (less than half of it on the globe).
    lat = np.linspace(-89.5, 89.5, 359)
    lon = np.full(lat.size, -168.9 + 0.2)
    x, y = winkel.forward(lon, lat)
    bx, by = to_board(x, y, synthetic_template.projection["fit"], 128, 80)
    r, c = np.floor(by).astype(int), np.floor(bx).astype(int)
    in_margin = synthetic_template.margin[r, c]
    assert in_margin.any() and (~in_margin).any()
    idx = proj.cells_for(lat, lon)
    assert (idx[in_margin] == -1).all()
    assert (idx[~in_margin] == (r * 128 + c)[~in_margin]).all()


def test_cells_for_invalid_and_broadcast(proj):
    assert proj.cells_for(np.array([95.0, np.nan, -91.0]), np.array([0.0, 0.0, 0.0])).tolist() == [-1, -1, -1]
    idx = proj.cells_for(np.array([-30.0, 0.0, 30.0])[:, None], np.array([-100.0, 0.0, 100.0, 150.0])[None, :])
    assert idx.shape == (3, 4) and (idx >= 0).all()
    assert idx[1, 1] == proj.cells_for(0.0, 0.0)


def test_cells_for_in_chunks(proj, monkeypatch):
    rng = np.random.default_rng(1)
    lat, lon = rng.uniform(-90, 90, 3001), rng.uniform(-180, 180, 3001)
    whole = proj.cells_for(lat, lon)
    monkeypatch.setattr(winkel, "CHUNK", 500)
    assert np.array_equal(proj.cells_for(lat, lon), whole)


def test_stud_location_round_trip(synthetic_template):
    t = synthetic_template
    x, y = _centres(t)
    inside = winkel.outline_contains(x, y)
    n = 0
    for r, c in zip(*np.nonzero(t.on_globe & inside)):
        loc = t.location(int(r), int(c))
        assert t.stud_at(*loc) == (r, c)
        n += 1
    assert n == int((t.on_globe & inside).sum()) > 8000


def test_location_and_stud_at_on_margin(synthetic_template):
    t = synthetic_template
    r, c = map(int, np.argwhere(t.margin)[0])
    assert t.location(r, c) is None
    assert t.class_at(r, c) == "margin"
    assert t.stud_at(95.0, 0.0) is None
    lat = np.linspace(-89.5, 89.5, 359)
    hits = [t.stud_at(float(la), -168.7) for la in lat]
    assert None in hits                                  # some land in margin studs


def test_location_out_of_range(synthetic_template):
    for r, c in ((80, 0), (0, 128), (-1, 5)):
        with pytest.raises(ValueError):
            synthetic_template.location(r, c)
        with pytest.raises(ValueError):
            synthetic_template.class_at(r, c)


def test_class_and_part_at(synthetic_template):
    t = synthetic_template
    lr, lc = map(int, np.argwhere(t.land)[0])
    orow, oc = map(int, np.argwhere(t.ocean)[0])
    assert t.class_at(lr, lc) == "land" and t.part_at(lr, lc) == "6141"
    assert t.class_at(orow, oc) == "ocean" and t.part_at(orow, oc) == "98138"
    mr, mc = map(int, np.argwhere(t.margin)[0])
    assert t.part_at(mr, mc) == "3070b"


def test_section_labels(synthetic_template):
    t = synthetic_template
    assert t.section_label(0, 0) == "A1"
    assert t.section_label(79, 127) == "H5"
    assert t.section_label(17, 33) == "C2"


# --- the kit -------------------------------------------------------------------------------

def test_kit_stud_at_agrees_with_the_kit_projection():
    kit = load_template(KIT_TEMPLATE_ID)
    p = load_kit_projection()
    rng = np.random.default_rng(11)
    for lat, lon in zip(rng.uniform(-90, 90, 500), rng.uniform(-180, 180, 500)):
        r = int(p.rows_for_lat(np.array([lat]))[0])
        c = int(p.cols_for_lon(np.array([lon]))[0])
        assert kit.stud_at(float(lat), float(lon)) == (None if r < 0 else (r, c))


def test_kit_stud_location_round_trip():
    kit = load_template(KIT_TEMPLATE_ID)
    for r in range(80):
        for c in range(0, 128, 7):
            assert kit.stud_at(*kit.location(r, c)) == (r, c)
    assert kit.stud_at(-89.0, 0.0) is None               # south of the kit's bottom row
    assert kit.class_at(0, 0) in ("land", "ocean")

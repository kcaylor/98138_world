"""Reprojection onto the kit grid (FR-014; data-model.md LayerField)."""

import numpy as np

from lego_image_processor.datasets.grid import SourceGrid
from lego_image_processor.maps.projection import load_kit_projection
from lego_image_processor.maps.reproject import reproject_layer


def _grid(values, land=None, step=0.5):
    lat = np.arange(-90 + step / 2, 90, step)
    lon = np.arange(-180 + step / 2, 180, step)
    v = values(lat[:, None], lon[None, :]) * np.ones((len(lat), len(lon)))
    return SourceGrid(values=v, lat=lat, lon=lon,
                      land=None if land is None else land(lat[:, None], lon[None, :]) & np.ones(v.shape, bool))


def _all(value=True):
    return np.full((80, 128), value)


def test_cell_means_follow_the_field():
    proj = load_kit_projection()
    f = reproject_layer(_grid(lambda la, lo: la), proj, _all(), "ocean")
    for row in (5, 30, 42, 60):
        lat, _ = proj.cell_center(row, 10)
        assert abs(f.values[row, 10] - lat) < 1.5
    assert (f.samples[f.samples > 0] >= 1).all()


def test_only_same_class_values_are_averaged():
    proj = load_kit_projection()
    # land west of 0 deg longitude has value 1000; ocean has 5
    g = _grid(lambda la, lo: np.where(lo < 0, 1000.0, 5.0), land=lambda la, lo: lo < 0)
    ocean = reproject_layer(g, proj, _all(), "ocean")
    land = reproject_layer(g, proj, _all(), "land")
    assert np.nanmax(ocean.values) == 5.0
    assert np.nanmin(land.values) == 1000.0


def test_cells_without_values_are_nearest_filled_and_flagged():
    proj = load_kit_projection()
    g = _grid(lambda la, lo: np.where(la > 0, 1.0, np.nan))
    f = reproject_layer(g, proj, _all(), "ocean")
    assert f.filled[79].all() and not f.filled[5:40].any()
    assert np.isfinite(f.values).all()
    assert f.filled_count == int(f.filled.sum()) > 0


def test_outside_layer_is_nan():
    proj = load_kit_projection()
    mask = np.zeros((80, 128), bool)
    mask[10:20, 10:20] = True
    f = reproject_layer(_grid(lambda la, lo: la), proj, mask, "ocean")
    assert np.isnan(f.values[~mask]).all() and np.isfinite(f.values[mask]).all()


def test_variance_terms():
    proj = load_kit_projection()
    smooth = reproject_layer(_grid(lambda la, lo: la), proj, _all(), "ocean")
    assert smooth.variance_lost < 0.01
    checker = reproject_layer(_grid(lambda la, lo: ((np.floor(la * 2) + np.floor(lo * 2)) % 2) * 1.0),
                              proj, _all(), "ocean")
    assert checker.variance_lost > 0.9


def test_categorical_mode():
    proj = load_kit_projection()
    g = _grid(lambda la, lo: np.where(lo < 0, 1.0, 2.0))
    f = reproject_layer(g, proj, _all(), "ocean", categorical=True)
    assert set(np.unique(f.values)) == {1.0, 2.0}


def test_on_kit_grid_passthrough():
    proj = load_kit_projection()
    v = np.arange(80 * 128, dtype=float).reshape(80, 128)
    g = SourceGrid(values=v, lat=np.array([]), lon=np.array([]), on_kit_grid=True)
    mask = _all()
    mask[0, 0] = False
    f = reproject_layer(g, proj, mask, "ocean")
    assert f.values[1, 1] == v[1, 1] and np.isnan(f.values[0, 0])
    assert f.filled_count == 0 and f.variance_lost is None

"""Sampling data on a non-kit template (T046; FR-007; research R6; data-model.md
TemplateProjection.cells_for, .locations).

``mean`` bins every source pixel into the stud that contains it (forward projection); ``bilinear``
interpolates at the stored stud locations; points grids bin by forward projection. Margin studs
never take data. Not affiliated with or endorsed by The LEGO Group.
"""

import numpy as np
import pytest

from lego_image_processor.datasets.grid import SourceGrid
from lego_image_processor.maps import reproject
from lego_image_processor.maps.reproject import (cell_centres, cell_means, reproject_layer,
                                                 source_cells)


def _grid(step, fn=lambda lat, lon: lat + 0.0 * lon, **kw):
    lat = np.arange(-90 + step / 2, 90, step)
    lon = np.arange(-180 + step / 2, 180, step)
    return SourceGrid(values=fn(lat[:, None], lon[None, :]).astype(float), lat=lat, lon=lon, **kw)


@pytest.fixture
def tp(confirmed_winkel):
    return confirmed_winkel.grid_projection


@pytest.fixture
def on(confirmed_winkel):
    return np.array(confirmed_winkel.on_globe)


class TestSourceCells:
    def test_forward_binning(self, tp):
        g = _grid(1.0)
        cell = source_cells(g, tp)
        assert cell.shape == g.values.shape
        expect = tp.cells_for(g.lat[:, None], g.lon[None, :])
        assert (cell == expect).all()

    def test_margin_and_off_board_dropped(self, tp, on):
        cell = source_cells(_grid(0.5), tp)
        got = cell[cell >= 0]
        assert on.ravel()[got].all()  # no pixel lands on a margin stud
        assert (cell == -1).any()  # globe pixels inside margin studs near the outline are dropped
        bad = SourceGrid(values=np.zeros(3), lat=np.array([95.0, np.nan, 0.0]), lon=np.array([0.0, 0.0, 11.1]),
                         points=True)
        c = source_cells(bad, tp)
        assert c[0] == -1 and c[1] == -1 and c[2] >= 0  # invalid locations are off the board

    def test_points(self, tp):
        rng = np.random.default_rng(1)
        lat, lon = rng.uniform(-90, 90, 5000), rng.uniform(-180, 180, 5000)
        g = SourceGrid(values=lat.copy(), lat=lat, lon=lon, points=True)
        assert (source_cells(g, tp) == tp.cells_for(lat, lon)).all()

    def test_chunking_bounds_memory(self, tp, monkeypatch):
        g = _grid(1.0)
        full = source_cells(g, tp)
        sizes = []
        real = tp.cells_for

        class Spy:
            def __getattr__(self, name):
                return getattr(tp, name)

            def cells_for(self, lat, lon):
                sizes.append(np.broadcast(lat, lon).size)
                return real(lat, lon)

        monkeypatch.setattr(reproject, "TEMPLATE_CHUNK", 5000)
        spy = Spy()
        monkeypatch.setattr(reproject, "_is_template", lambda p: True)
        chunked = source_cells(g, spy)
        assert (chunked == full).all()
        assert len(sizes) > 1 and max(sizes) <= 5000
        rng = np.random.default_rng(2)
        lat, lon = rng.uniform(-90, 90, 12000), rng.uniform(-180, 180, 12000)
        sizes.clear()
        pts = source_cells(SourceGrid(values=lat.copy(), lat=lat, lon=lon, points=True), spy)
        assert (pts == real(lat, lon)).all() and max(sizes) <= 5000

    def test_default_chunk(self):
        assert reproject.TEMPLATE_CHUNK == 1_000_000


class TestMean:
    def test_studs_take_the_mean_of_their_pixels(self, tp, on):
        g = _grid(0.5, lambda lat, lon: lat + 0.01 * lon)
        f = reproject_layer(g, tp, on, "ocean")
        cell = source_cells(g, tp)
        ok = cell >= 0
        n = np.bincount(cell[ok], minlength=tp.height * tp.width).reshape(tp.height, tp.width)
        s = np.bincount(cell[ok], weights=g.values[ok], minlength=tp.height * tp.width).reshape(n.shape)
        have = n > 0
        assert np.allclose(f.values[have], s[have] / n[have])
        assert (f.samples == n).all()

    def test_margin_studs_receive_nothing(self, tp, on):
        f = reproject_layer(_grid(0.5), tp, on, "ocean")
        assert np.isnan(f.values[~on]).all() and (f.samples[~on] == 0).all() and not f.filled[~on].any()
        assert np.isfinite(f.values[on]).all()

    def test_only_layer_studs(self, tp, confirmed_winkel):
        land = np.array(confirmed_winkel.land)
        f = reproject_layer(_grid(0.5), tp, land, "land")
        assert np.isfinite(f.values[land]).all() and np.isnan(f.values[~land]).all()
        assert (f.samples[~land] == 0).all()

    def test_studs_without_a_pixel_take_the_nearest_value(self, tp, on):
        g = _grid(10.0)
        f = reproject_layer(g, tp, on, "ocean")
        empty = on & (f.samples == 0)
        assert empty.any() and (f.filled == empty).all() and f.filled_count == int(empty.sum())
        have = on & (f.samples > 0)
        assert np.isin(f.values[empty], f.values[have]).all()  # every filled value is a sampled stud's

    def test_variance_lost_over_the_template_studs(self, tp, confirmed_winkel):
        mask = np.array(confirmed_winkel.ocean)
        g = _grid(1.0, lambda lat, lon: np.sin(np.radians(lon) * 3) + lat / 30)
        f = reproject_layer(g, tp, mask, "ocean")
        cell = source_cells(g, tp)
        ok = cell >= 0
        c, x = cell[ok], g.values[ok]
        inside = mask.ravel()[c]
        c, x = c[inside], x[inside]
        n = np.bincount(c, minlength=mask.size)
        mean = np.bincount(c, weights=x, minlength=mask.size) / np.maximum(n, 1)
        within = ((x - mean[c]) ** 2).sum() / x.size
        assert f.variance_lost == pytest.approx(within / x.var())
        assert f.total_variance == pytest.approx(x.var())

    def test_categorical(self, tp, on):
        g = _grid(1.0, lambda lat, lon: np.where(lat > 0, 1.0, 2.0) + 0 * lon)
        f = reproject_layer(g, tp, on, "ocean", categorical=True)
        assert set(np.unique(f.values[on])) <= {1.0, 2.0} and np.isnan(f.values[~on]).all()

    def test_cell_means(self, tp, on):
        mean, n = cell_means(_grid(1.0), tp)
        assert (n[~on] == 0).all() and np.isnan(mean[~on]).all()
        assert (n[on] > 0).sum() > 0.9 * on.sum()

    def test_kit_grid_source_refused(self, tp, on):
        g = SourceGrid(values=np.zeros((80, 128)), lat=np.zeros(80), lon=np.zeros(128), on_kit_grid=True)
        with pytest.raises(ValueError, match="kit grid"):
            reproject_layer(g, tp, on, "ocean")


class TestBilinear:
    def test_cell_centres_are_the_stud_locations(self, tp, confirmed_winkel):
        lat, lon = cell_centres(tp)
        tlat, tlon = confirmed_winkel.locations()
        assert np.array_equal(lat, tlat, equal_nan=True) and np.array_equal(lon, tlon, equal_nan=True)

    def test_at_the_stored_stud_locations(self, tp, confirmed_winkel, on):
        g = _grid(0.5)  # values = latitude: bilinear reproduces it between the outermost rows
        f = reproject_layer(g, tp, on, "ocean", sampling="bilinear")
        lat, _ = confirmed_winkel.locations()
        inner = on & (np.abs(np.nan_to_num(lat)) < 89.7)
        assert np.allclose(f.values[inner], lat[inner], atol=1e-9)
        assert np.isnan(f.values[~on]).all()
        assert not f.filled.any()

    def test_margin_studs_skipped(self, tp, confirmed_winkel):
        mask = np.array(confirmed_winkel.ocean)
        f = reproject_layer(_grid(2.0), tp, mask, "ocean", sampling="bilinear")
        assert np.isnan(f.values[~mask]).all() and np.isfinite(f.values[mask]).all()

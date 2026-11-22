"""Classification (FR-015; data-model.md Classification) and background fill (Layer.weights)."""

import numpy as np
import pytest

from lego_image_processor.maps.classify import MapBuildError, classify, largest_remainder
from lego_image_processor.maps.recipe import Classification
from lego_image_processor.maps.texture import fill_background

H, W = 80, 128


def _mask(n=None):
    m = np.zeros((H, W), bool)
    m[:40, :] = True
    return m


class TestCategorical:
    def test_one_to_one(self):
        cats = ["a", "b", "c"]
        values = np.zeros((H, W))
        values[:, 64:] = 2
        cl = Classification(method="categorical", categories={"a": "lego_x", "c": "lego_z"})
        r = classify(values, _mask(), cl, ("lego_x", "lego_z"), categories=cats)
        assert set(np.unique(r.classes[_mask()])) == {0, 1}
        assert (r.classes[:40, :64] == 0).all() and (r.classes[:40, 64:] == 1).all()
        assert (r.classes[40:] == -1).all()

    def test_unmapped_category_fails(self):
        values = np.ones((H, W))
        cl = Classification(method="categorical", categories={"a": "lego_x"})
        with pytest.raises(MapBuildError, match="'b'"):
            classify(values, _mask(), cl, ("lego_x",), categories=["a", "b"])

    def test_numeric_categories(self):
        values = np.where(np.arange(W)[None, :] < 10, 1.0, 3.0) * np.ones((H, 1))
        cl = Classification(method="categorical", categories={"1": "lego_x", "3": "lego_y"})
        r = classify(values, _mask(), cl, ("lego_x", "lego_y"))
        assert (r.classes[:40, :10] == 0).all() and (r.classes[:40, 10:] == 1).all()


class TestBackground:
    def test_single_color(self):
        c = fill_background(_mask(), (1.0,), cluster=0.0, seed=1)
        assert (c[_mask()] == 0).all() and (c[~_mask()] == -1).all()

    def test_exact_counts_by_weight(self):
        m = _mask()
        c = fill_background(m, (1.0, 3.0), cluster=0.0, seed=1)
        n = m.sum()
        assert (c[m] == 0).sum() == round(n / 4) and (c[m] == 1).sum() == n - round(n / 4)


def _gradient():
    return np.tile(np.linspace(0, 100, W), (H, 1)) + np.arange(H)[:, None] * 1e-3


class TestOrdered:
    def test_bins_and_clamp(self):
        v = _gradient()
        m = _mask()
        v[0, 0] = -50
        v[0, 1] = 500
        cl = Classification(method="bins", bounds=(0, 25, 50, 101))
        r = classify(v, m, cl, ("a", "b", "c"))
        assert r.classes[0, 0] == 0 and r.classes[0, 1] == 2
        assert r.below == 1 and r.above == 1
        assert r.classes[5, 10] == 0 and r.classes[5, 50] == 1 and r.classes[5, 100] == 2

    def test_quantile_equal_counts(self):
        r = classify(_gradient(), _mask(), Classification(method="quantile"), ("a", "b", "c", "d"))
        assert r.counts == [1280, 1280, 1280, 1280]

    def test_rank_shares(self):
        r = classify(_gradient(), _mask(), Classification(method="rank", shares=(1, 1, 2)), ("a", "b", "c"))
        assert r.counts == [1280, 1280, 2560]

    def test_largest_remainder(self):
        assert largest_remainder([1, 1, 1], 10) == [4, 3, 3]
        assert sum(largest_remainder([392, 724, 597], 1000)) == 1000

    def test_rank_to_supply_within_supply(self):
        supply = {"a": 1000, "b": 3000, "c": 2000}
        r = classify(_gradient(), _mask(), Classification(method="rank-to-supply"), ("a", "b", "c"),
                     supply=supply)
        assert sum(r.counts) == 5120
        for k, n in zip("abc", r.counts):
            assert n <= supply[k]

    def test_rank_to_supply_too_many_cells(self):
        with pytest.raises(MapBuildError, match="by 120"):
            classify(_gradient(), _mask(), Classification(method="rank-to-supply"), ("a", "b"),
                     supply={"a": 2000, "b": 3000})

    @pytest.mark.parametrize("cl", [Classification(method="quantile"),
                                    Classification(method="rank", shares=(3, 1, 2)),
                                    Classification(method="bins", bounds=(10, 30, 60, 90))])
    def test_monotonic(self, cl):
        rng = np.random.default_rng(0)
        v = rng.normal(size=(H, W))
        v = (v - v.min()) / (v.max() - v.min()) * 100
        m = _mask()
        r = classify(v, m, cl, ("a", "b", "c"))
        vals, cls = v[m], r.classes[m]
        order = np.argsort(vals)
        assert (np.diff(cls[order]) >= 0).all()

    def test_ties_broken_row_major(self):
        v = np.zeros((H, W))
        m = _mask()
        r = classify(v, m, Classification(method="quantile"), ("a", "b"))
        flat = r.classes[m]
        assert (flat[:2560] == 0).all() and (flat[2560:] == 1).all()

    def test_missing_values_fail(self):
        v = _gradient()
        v[3, 3] = np.nan
        with pytest.raises(MapBuildError, match="missing"):
            classify(v, _mask(), Classification(method="quantile"), ("a", "b"))


class TestEnsoBinsMembership:
    """The ENSO legend (feature 009, data-model.md Shared legend.class membership): [lower, upper),
    end classes open."""

    BOUNDS = (-9, -1.5, -0.5, -0.25, -0.1, 0.1, 0.3, 0.5, 1.0, 9)
    COLORS = tuple(f"lego_c{i}" for i in range(9))

    def test_bound_values_take_the_upper_class(self):
        values = np.zeros((H, W))
        row = [-4.76, -1.5, -0.1, -0.0999, 0.0, 0.0999, 0.1, 0.5, 1.0, 4.93]
        values[0, :len(row)] = row
        r = classify(values, _mask(), Classification(method="bins", bounds=self.BOUNDS), self.COLORS)
        assert r.classes[0, :len(row)].tolist() == [0, 1, 4, 4, 4, 4, 5, 7, 8, 8]
        assert r.below == 0 and r.above == 0

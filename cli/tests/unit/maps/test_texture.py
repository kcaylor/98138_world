"""Texture rules (FR-017; data-model.md Texture)."""

import numpy as np
from scipy import ndimage

from lego_image_processor.maps.classify import classify
from lego_image_processor.maps.recipe import Classification
from lego_image_processor.maps.texture import apply_blend, fill_background

H, W = 80, 128


def _setup(method="quantile", **kw):
    v = np.tile(np.linspace(0, 100, W), (H, 1)) + np.arange(H)[:, None] * 1e-3
    m = np.ones((H, W), bool)
    m[:5] = False
    cl = Classification(method=method, **kw)
    return v, m, classify(v, m, cl, ("a", "b", "c", "d"))


def test_same_seed_identical():
    v, m, r = _setup()
    a = apply_blend(r, v, m, width=0.25, seed=3)
    b = apply_blend(r, v, m, width=0.25, seed=3)
    assert (a == b).all()


def test_new_seed_changes_only_blend_zone():
    v, m, r = _setup()
    a = apply_blend(r, v, m, width=0.2, seed=1)
    b = apply_blend(r, v, m, width=0.2, seed=2)
    changed = (a != b)
    assert changed.any()
    assert not (changed & ~r.blend_zone(0.2)).any()


def test_moves_at_most_one_class():
    for method, kw in (("quantile", {}), ("bins", {"bounds": (0, 10, 50, 60, 100)})):
        v, m, r = _setup(method, **kw)
        t = apply_blend(r, v, m, width=0.5, seed=5)
        assert (np.abs(t[m] - r.classes[m]) <= 1).all()
        assert (t[~m] == -1).all()


def test_rank_methods_keep_counts():
    for method, kw in (("quantile", {}), ("rank", {"shares": (1, 2, 3, 4)})):
        v, m, r = _setup(method, **kw)
        t = apply_blend(r, v, m, width=0.3, seed=9)
        assert [int((t[m] == k).sum()) for k in range(4)] == r.counts
        assert (t != r.classes).any()


def test_mix_exact_counts_and_clustering():
    m = np.ones((H, W), bool)
    weights = (2.0, 1.0, 1.0)
    flat = fill_background(m, weights, cluster=0.0, seed=4)
    lumpy = fill_background(m, weights, cluster=3.0, seed=4)
    for c in (flat, lumpy):
        assert [(c == k).sum() for k in range(3)] == [5120, 2560, 2560]
    # larger cluster -> fewer, larger same-color patches
    n_flat = sum(ndimage.label(flat == k)[1] for k in range(3))
    n_lumpy = sum(ndimage.label(lumpy == k)[1] for k in range(3))
    assert n_lumpy < n_flat / 3
    assert (fill_background(m, weights, cluster=3.0, seed=4) == lumpy).all()

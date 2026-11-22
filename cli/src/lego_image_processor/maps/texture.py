"""Texture rules (FR-017; research R7); they replace feature 002's "shadowing" (FR-018).

- ``blend`` (data layers): a cell within ``width`` of a class boundary (as a fraction of its
  class) moves to the neighbouring class with probability falling linearly from 0.5 at the
  boundary to 0 at the edge of the zone. Rank methods swap cells in pairs across the boundary, so
  class counts never change. No cell moves more than one class.
- ``mix`` (background layers): Gaussian-smoothed white noise (sigma = ``cluster`` studs) ranked
  into the colors by weight, giving exact counts and soft patches.

Randomness comes from ``numpy.random.default_rng(seed)``, drawn in row-major order.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from .classify import ClassResult, largest_remainder


def apply_blend(result: ClassResult, values: np.ndarray, mask: np.ndarray, *, width: float,
                seed: int) -> np.ndarray:
    """Blend the classes of ``result``; returns a new class array."""
    classes = result.classes.copy()
    n = len(result.counts)
    if n < 2:
        return classes
    rng = np.random.default_rng(seed)
    u = np.full(classes.shape, np.inf)
    u[mask] = rng.random(int(mask.sum()))  # one draw per layer cell, row-major
    d_up, d_lo = result.boundary_distance()
    p_up = np.where(d_up < width, 0.5 * (1.0 - d_up / width), 0.0)
    p_lo = np.where(d_lo < width, 0.5 * (1.0 - d_lo / width), 0.0)
    go_up = u < p_up
    go_lo = (u < p_lo) & ~go_up
    if not result.is_rank:
        classes[go_up] += 1
        classes[go_lo] -= 1
        return classes
    k = result.classes
    for b in range(n - 1):  # boundary between class b and b+1
        lower = np.flatnonzero((go_up & (k == b)).ravel())
        upper = np.flatnonzero((go_lo & (k == b + 1)).ravel())
        m = min(len(lower), len(upper))
        if m == 0:
            continue
        lower = rng.permutation(lower)[:m]
        upper = rng.permutation(upper)[:m]
        flat = classes.reshape(-1)
        flat[lower] = b + 1
        flat[upper] = b
    return classes


def fill_background(mask: np.ndarray, weights: Sequence[float], *, cluster: float, seed: int) -> np.ndarray:
    """Background classes by weight: exact counts, clustered by smoothed noise."""
    mask = np.asarray(mask, dtype=bool)
    classes = np.full(mask.shape, -1, dtype=int)
    if len(weights) == 1:
        classes[mask] = 0
        return classes
    from scipy import ndimage

    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(mask.shape)
    if cluster > 0:
        noise = ndimage.gaussian_filter(noise, sigma=cluster, mode=("nearest", "wrap"))
    idx = np.flatnonzero(mask.ravel())
    order = np.argsort(noise.ravel()[idx], kind="stable")
    counts = largest_remainder(weights, len(idx))
    flat = classes.reshape(-1)
    flat[idx[order]] = np.repeat(np.arange(len(weights)), counts)
    return classes

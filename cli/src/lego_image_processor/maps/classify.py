"""Classification of a layer's cell values onto its ordered color scale (FR-015; research R7).

Ordered methods never give a higher value a lower class (before texture); ties are broken in
row-major cell order. Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence

import numpy as np

from .recipe import RANK_METHODS, Classification


class MapBuildError(ValueError):
    """A recipe cannot be built from its data (for example more cells than supply)."""


def largest_remainder(shares: Sequence[float], total: int, caps: Optional[Sequence[int]] = None) -> List[int]:
    """Integer counts proportional to ``shares`` summing to ``total`` (ties: lower index first).

    With ``caps`` no count exceeds its cap (excess goes to the next-largest remainders).
    """
    s = np.asarray(shares, dtype=float)
    exact = s / s.sum() * total
    counts = np.floor(exact).astype(int)
    if caps is not None:
        counts = np.minimum(counts, np.asarray(caps, dtype=int))
    rem = exact - counts
    left = total - int(counts.sum())
    order = sorted(range(len(s)), key=lambda i: (-rem[i], i))
    while left > 0:
        progressed = False
        for i in order:
            if left == 0:
                break
            if caps is None or counts[i] < caps[i]:
                counts[i] += 1
                left -= 1
                progressed = True
        if not progressed:
            raise MapBuildError("counts cannot fit within the caps")
    return [int(c) for c in counts]


@dataclass
class ClassResult:
    """Classes per kit cell (-1 outside the layer) plus what texture and reports need."""

    classes: np.ndarray
    counts: List[int]
    method: str
    mask: np.ndarray
    values: np.ndarray
    below: int = 0
    above: int = 0
    bounds: tuple = ()
    rank_pos: Optional[np.ndarray] = None   # 0..N-1 within the layer, -1 outside
    starts: List[int] = field(default_factory=list)  # first rank position of each class

    @property
    def is_rank(self) -> bool:
        return self.method in RANK_METHODS

    def boundary_distance(self):
        """Per cell: (distance to the upper boundary, to the lower one) as a fraction of the class
        width; inf where there is no such boundary. Used by the blend texture."""
        up = np.full(self.classes.shape, np.inf)
        lo = np.full(self.classes.shape, np.inf)
        n = len(self.counts)
        m = self.mask
        k = self.classes
        if self.is_rank:
            p = self.rank_pos.astype(float)
            starts = np.asarray(self.starts + [sum(self.counts)], dtype=float)
            sizes = np.maximum(np.diff(starts), 1)
            kk = np.where(m, k, 0)
            d_up = (starts[kk + 1] - p - 0.5) / sizes[kk]
            d_lo = (p + 0.5 - starts[kk]) / sizes[kk]
        elif self.method == "bins":
            b = np.asarray(self.bounds, dtype=float)
            kk = np.where(m, k, 0)
            widths = np.diff(b)
            v = np.where(m, self.values, 0.0)
            d_up = (b[kk + 1] - v) / widths[kk]
            d_lo = (v - b[kk]) / widths[kk]
        else:
            return up, lo
        up = np.where(m & (k < n - 1), d_up, np.inf)
        lo = np.where(m & (k > 0), d_lo, np.inf)
        return up, lo

    def blend_zone(self, width: float) -> np.ndarray:
        up, lo = self.boundary_distance()
        return (up < width) | (lo < width)


def _rank_classes(values: np.ndarray, mask: np.ndarray, counts: List[int], method: str) -> ClassResult:
    flat_idx = np.flatnonzero(mask.ravel())
    vals = values.ravel()[flat_idx]
    order = np.argsort(vals, kind="stable")  # stable: ties keep row-major order
    cls_sorted = np.repeat(np.arange(len(counts)), counts)
    classes = np.full(values.size, -1, dtype=int)
    classes[flat_idx[order]] = cls_sorted
    rank_pos = np.full(values.size, -1, dtype=int)
    rank_pos[flat_idx[order]] = np.arange(len(flat_idx))
    starts = list(np.concatenate([[0], np.cumsum(counts)[:-1]]).astype(int))
    return ClassResult(classes=classes.reshape(values.shape), counts=list(counts), method=method,
                       mask=mask, values=values, rank_pos=rank_pos.reshape(values.shape),
                       starts=[int(s) for s in starts])


def classify(values: np.ndarray, mask: np.ndarray, classification: Classification,
             colors: Sequence[str], *, categories: Optional[Sequence[str]] = None,
             supply: Optional[Mapping[str, int]] = None) -> ClassResult:
    """Classes 0..len(colors)-1 for the layer cells in ``mask``; -1 elsewhere."""
    values = np.asarray(values, dtype=float)
    mask = np.asarray(mask, dtype=bool)
    n = len(colors)
    method = classification.method
    layer_vals = values[mask]
    if not np.isfinite(layer_vals).all():
        raise MapBuildError(f"{int((~np.isfinite(layer_vals)).sum())} layer cells have missing values")
    N = int(mask.sum())

    if method == "categorical":
        index = {c: i for i, c in enumerate(colors)}
        classes = np.full(values.shape, -1, dtype=int)
        present = np.unique(layer_vals)
        for v in present:
            name = categories[int(v)] if categories is not None else _num_key(v)
            if name not in classification.categories:
                raise MapBuildError(f"source category {name!r} is not mapped in classification.categories")
            classes[mask & (values == v)] = index[classification.categories[name]]
        counts = [int((classes == i).sum()) for i in range(n)]
        return ClassResult(classes=classes, counts=counts, method=method, mask=mask, values=values)

    if method == "bins":
        b = np.asarray(classification.bounds, dtype=float)
        k = np.searchsorted(b[1:-1], values, side="right")
        classes = np.where(mask, k, -1).astype(int)
        counts = [int((classes == i).sum()) for i in range(n)]
        return ClassResult(classes=classes, counts=counts, method=method, mask=mask, values=values,
                           below=int((layer_vals < b[0]).sum()), above=int((layer_vals > b[-1]).sum()),
                           bounds=tuple(b))

    if method == "quantile":
        counts = largest_remainder([1.0] * n, N)
    elif method == "rank":
        counts = largest_remainder(classification.shares, N)
    elif method == "rank-to-supply":
        if supply is None:
            raise MapBuildError("rank-to-supply needs the kit supply")
        caps = [int(supply.get(c, 0)) for c in colors]
        if N > sum(caps):
            raise MapBuildError(f"the layer has {N} cells but its colors' kit supply totals {sum(caps)}; "
                                f"short by {N - sum(caps)} cells")
        counts = largest_remainder(caps, N, caps=caps)
    else:  # pragma: no cover - recipe validation rejects other methods
        raise MapBuildError(f"unknown method {method}")
    return _rank_classes(values, mask, counts, method)


def _num_key(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else repr(float(v))

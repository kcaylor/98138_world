"""Board helpers for templates: modules, the outline ring and the corner free regions.

``module_stats``, ``rim_cells`` and ``largest_rectangle`` moved here from the projection study
(``cli/tools/projection_study/raster.py``, which imports them from this module). A board is whole
16 x 16 modules; ``on`` is the boolean on-globe mask (land or ocean) of the board, rows north to
south. The outline ring is the margin studs that touch an on-globe stud along an edge; a corner
free region is the margin minus the ring in one board quadrant (research R20, kept for feature
017's corner plaque). Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from typing import Dict, Iterable, Tuple, Union

import numpy as np

MODULE = 16
CORNERS = ("top-left", "top-right", "bottom-left", "bottom-right")
CLASS_CODES = ("L", "O", "M")


def module_stats(on: np.ndarray) -> Tuple[int, int, int]:
    """Count 16×16 modules that are fully on the globe, partly on it, and entirely off it."""
    H, W = on.shape
    if H % MODULE or W % MODULE:
        raise ValueError("board must be whole 16×16 modules")
    n = on.reshape(H // MODULE, MODULE, W // MODULE, MODULE).sum(axis=(1, 3))
    full = int((n == MODULE * MODULE).sum())
    empty = int((n == 0).sum())
    return full, int(n.size - full - empty), empty


def rim_cells(on: np.ndarray) -> np.ndarray:
    """Off-globe studs that touch an on-globe stud (4-neighbour): a one-stud outline ring."""
    pad = np.pad(on, 1, constant_values=False)
    nb = pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]
    return ~on & nb


def largest_rectangle(free: np.ndarray) -> Tuple[int, int, int, int]:
    """Largest axis-aligned all-True rectangle in ``free``: (row, col, height, width).

    Used to size a corner plaque: how big a block of margin studs fits in a corner.
    """
    H, W = free.shape
    heights = np.zeros(W, dtype=int)
    best = (0, 0, 0, 0)
    for r in range(H):
        heights = np.where(free[r], heights + 1, 0)
        stack: list = []
        for c in range(W + 1):
            h = heights[c] if c < W else 0
            start = c
            while stack and stack[-1][1] >= h:
                start, sh = stack.pop()
                if sh * (c - start) > best[2] * best[3]:
                    best = (int(r - sh + 1), int(start), int(sh), int(c - start))
            stack.append((start, h))
    return best


def _quadrants(H: int, W: int):
    return (("top-left", slice(0, H // 2), slice(0, W // 2)),
            ("top-right", slice(0, H // 2), slice(W // 2, W)),
            ("bottom-left", slice(H // 2, H), slice(0, W // 2)),
            ("bottom-right", slice(H // 2, H), slice(W // 2, W)))


def corner_free_regions(on: np.ndarray) -> Dict[str, np.ndarray]:
    """Per board quadrant (``CORNERS``), the margin studs inside the outline ring (board-shaped
    masks that do not overlap; their union is the margin minus the ring)."""
    on = np.asarray(on, dtype=bool)
    free = ~on & ~rim_cells(on)
    out = {}
    for name, rs, cs in _quadrants(*on.shape):
        m = np.zeros_like(free)
        m[rs, cs] = free[rs, cs]
        out[name] = m
    return out


def corner_blocks(on: np.ndarray) -> Dict[str, Dict[str, int]]:
    """The largest clear block of each corner free region, in board coordinates:
    ``{corner: {row, col, height, width}}`` (height and width 0 when the corner has none)."""
    on = np.asarray(on, dtype=bool)
    free = ~on & ~rim_cells(on)
    out = {}
    for name, rs, cs in _quadrants(*on.shape):
        row, col, h, w = largest_rectangle(free[rs, cs])
        out[name] = {"row": int(row + rs.start), "col": int(col + cs.start), "height": int(h), "width": int(w)}
    return out


def class_array(classes: Union[np.ndarray, Iterable[str]]) -> np.ndarray:
    """Classes as an array of ``L``/``O``/``M`` characters (rows of strings are split)."""
    if isinstance(classes, np.ndarray):
        return classes.astype("U1")
    return np.array([list(row) for row in classes], dtype="U1")


def board_counts(classes: Union[np.ndarray, Iterable[str]]) -> Dict[str, object]:
    """The counts a template records (contracts/template-file.md ``counts``): land, ocean, margin,
    ring, modules (full, partial, empty) and the corner blocks."""
    a = class_array(classes)
    on = a != "M"
    full, partial, empty = module_stats(on)
    return {"land": int((a == "L").sum()), "ocean": int((a == "O").sum()), "margin": int((a == "M").sum()),
            "ring": int(rim_cells(on).sum()),
            "modules": {"full": full, "partial": partial, "empty": empty},
            "corners": corner_blocks(on)}

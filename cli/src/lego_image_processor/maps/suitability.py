"""Suitability check run on every build and by ``map check`` (FR-019; research R8).

Per layer: share of variance lost below grid scale, share of cells filled from neighbours, cells
per class, smallest CIEDE2000 difference between neighbouring scale colors, and color counts
against one kit's supply. Thresholds are agent defaults recorded in every report.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

THRESHOLDS = {"variance_lost": 0.5, "filled_share": 0.05, "min_delta_e00": 5.0}


@lru_cache(maxsize=None)
def kit_supply() -> Dict[str, Dict[str, int]]:
    """One kit's supply per part and color key (inventory page 159)."""
    from ..layout.kit_spec import load_kit_specification

    spec = load_kit_specification()
    return {spec.land_part_id: dict(spec.plate_quantities), spec.ocean_part_id: dict(spec.tile_quantities)}


def _rgb_table() -> Dict[str, Tuple[int, int, int]]:
    from .preview import color_rgb

    return {k: v for (_, k), v in color_rgb().items()}


def min_neighbour_delta_e(colors: Sequence[str], rgb: Optional[Mapping[str, Tuple[int, int, int]]] = None):
    """The closest neighbouring pair on the scale and its ΔE00 (None for fewer than 2 colors)."""
    from ..core.color_quantizer import delta_e_2000
    from ..palette.converter import rgb_to_lab

    if len(colors) < 2:
        return None, None
    rgb = rgb or _rgb_table()
    best = (None, float("inf"))
    for a, b in zip(colors, colors[1:]):
        la = rgb_to_lab(np.array(rgb[a], dtype=np.float64))
        lb = rgb_to_lab(np.array(rgb[b], dtype=np.float64))
        d = float(delta_e_2000(la, lb))
        if d < best[1]:
            best = ((a, b), d)
    return best


def layer_report(*, cls: str, role: str, part_id: str, colors: Sequence[str], field, classes: np.ndarray,
                 ordered: bool, layer_cells: int, rgb: Optional[Mapping[str, Tuple[int, int, int]]] = None,
                 below: int = 0, above: int = 0, bounds: Sequence[float] = (),
                 dataset: Optional[Mapping[str, Any]] = None, method: Optional[str] = None,
                 extra_use: Optional[Mapping[str, int]] = None) -> Dict[str, Any]:
    """``extra_use``: tiles of the layer's part used outside the layer (the land shadow); they
    count against one kit's supply in the ``supply`` rows."""
    warnings: List[Dict[str, str]] = []
    counts = [int((classes == i).sum()) for i in range(len(colors))]
    rep: Dict[str, Any] = {"class": cls, "role": role, "part_id": part_id, "cells": int(layer_cells)}
    if method:
        rep["classification"] = method
    if dataset:
        rep["dataset"] = dict(dataset)
    if role == "data" and field is not None:
        vl = field.variance_lost
        rep["variance_lost"] = None if vl is None else round(float(vl), 4)
        filled = int(field.filled.sum())
        rep["filled_cells"] = filled
        rep["filled_share"] = round(filled / layer_cells, 4) if layer_cells else 0.0
        if vl is not None and vl > THRESHOLDS["variance_lost"]:
            warnings.append({"code": "detail_lost", "message":
                             f"{cls}: {vl * 100:.0f}% of the data's variance is finer than one grid cell "
                             f"and is lost (threshold {THRESHOLDS['variance_lost'] * 100:.0f}%)"})
        if layer_cells and filled / layer_cells > THRESHOLDS["filled_share"]:
            warnings.append({"code": "filled", "message":
                             f"{cls}: {filled} cells ({filled / layer_cells * 100:.1f}%) had no data and were "
                             f"filled from the nearest cell (threshold {THRESHOLDS['filled_share'] * 100:.0f}%)"})
        if below or above:
            rep["outside_bounds"] = {"below": int(below), "above": int(above)}
        if bounds:
            rep["class_bounds"] = [float(b) for b in bounds]
        for key, n in zip(colors, counts):
            if n == 0:
                warnings.append({"code": "empty_class", "message": f"{cls}: class {key} gets no cells"})
        if ordered:
            pair, de = min_neighbour_delta_e(colors, rgb)
            if pair is not None:
                rep["min_neighbour_delta_e00"] = {"pair": list(pair), "delta_e00": round(de, 2)}
                if de < THRESHOLDS["min_delta_e00"]:
                    warnings.append({"code": "colors_close", "message":
                                     f"{cls}: neighbouring colors {pair[0]} and {pair[1]} differ by only "
                                     f"ΔE00 {de:.1f} (threshold {THRESHOLDS['min_delta_e00']:.0f})"})
    rep["class_counts"] = [{"key": k, "cells": n} for k, n in zip(colors, counts)]
    supply = kit_supply().get(part_id, {})
    rows = []
    extra = dict(extra_use or {})
    use = [(k, n + int(extra.pop(k, 0))) for k, n in zip(colors, counts)] + list(extra.items())
    for k, n in use:
        s = int(supply.get(k, 0))
        rows.append({"key": k, "used": n, "supplied": s, "within": n <= s, "in_kit": k in supply})
    rep["supply"] = rows
    over = [r for r in rows if not r["within"] and r["in_kit"]]
    beyond = [r for r in rows if not r["in_kit"] and r["used"] > 0]
    if over:
        warnings.append({"code": "over_supply", "message": f"{cls}: " + ", ".join(
            f"{r['key']} {r['used']} > {r['supplied']}" for r in over) + " (one kit's supply)"})
    if beyond:
        warnings.append({"code": "beyond_kit", "message": f"{cls}: colors not in kit 31203 for part "
                         f"{part_id}: " + ", ".join(f"{r['key']} ({r['used']})" for r in beyond)})
    rep["warnings"] = warnings
    rep["thresholds"] = dict(THRESHOLDS)
    return rep

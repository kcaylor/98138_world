"""Per-cell data for the palette chooser (feature 012, FR-001; contracts/cells-json.md).

``map_cells(result)`` turns a built map (``build_map``) into a JSON-ready dict for the board as
hung: each layer's built class per cell and (data layers) value per cell, the default class
bounds, the land shadow, the ice regions and the cited colors of both parts with CIE L*. A
browser can then recolor the map, try other class bounds, or show ice as White without
recomputing anything else. It is a preview aid only: layouts, parts lists, prices and build
sheets never read it (FR-004). Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from ..kit.part_colors import load_part_colors
from ..kit.source import DISCLAIMER
from ..palette.converter import rgb_to_lab
from .ice import IceRegions, load_ice_regions
from .recipe import RANK_METHODS, Layer
from .texture import shadow_mask

CELLS_FORMAT = "1"
PREVIEW_NOTE = ("Preview only: parts lists, prices, build sheets and downloads use the map's "
                "default colors.")
_UNITS = {"degc": "°C", "degree_c": "°C", "degrees_c": "°C", "celsius": "°C"}
_BACKGROUND_LABELS = {"halo": ["offshore", "coast ring"]}


def lightness(rgb) -> int:
    """CIE L* (D65) of an sRGB triple, rounded to a whole number."""
    return int(round(float(rgb_to_lab(np.asarray(rgb, dtype=float))[0])))


def part_palette() -> Dict[str, List[Dict[str, Any]]]:
    """The cited colors of each map part, light to dark (ties by LEGO name)."""
    table = load_part_colors()
    out = {}
    for part, rows in table.parts.items():
        items = [{"key": c.key, "lego": {"name": c.lego.name, "id": c.lego.id},
                  "bricklink": {"name": c.bricklink.name, "id": c.bricklink.id},
                  "rgb": [int(v) for v in c.rgb], "in_kit": bool(c.in_kit),
                  "lightness": lightness(c.rgb)} for c in rows]
        items.sort(key=lambda r: (-r["lightness"], r["lego"]["name"]))
        out[part] = items
    return out


def _units(layer: Layer) -> str:
    u = str(((layer.dataset.variables or {}).get(layer.variable, {}) or {}).get("units", "") or "")
    return _UNITS.get(u.lower(), u)


def _decimals(values: np.ndarray) -> int:
    finite = values[np.isfinite(values)]
    return 2 if finite.size == 0 or float(np.abs(finite).max()) < 100 else 0


def _round(v: float, d: int):
    return int(round(v)) if d == 0 else round(float(v), d)


def _derived_bounds(values: np.ndarray, classes: np.ndarray, n: int, d: int) -> List[float]:
    """Value boundaries between the built classes of a rank-based layer: the midpoint between the
    last value of one class and the first of the next in sorted order (the blend texture swaps
    cells in pairs, so class counts are those of the ranking)."""
    sv = np.sort(values)
    counts = [int((classes == i).sum()) for i in range(n)]
    cum = np.cumsum(counts)[:-1]
    inner = []
    for c in cum:
        c = int(min(max(c, 1), len(sv) - 1))
        inner.append(_round((sv[c - 1] + sv[c]) / 2.0, d))
    return [_round(sv[0], d)] + inner + [_round(sv[-1], d)]


def _layer_block(layer: Layer, classes: np.ndarray, mask: np.ndarray, fld, ice_cells: set) -> Dict[str, Any]:
    n = len(layer.colors)
    cls_flat = np.where(mask, classes, -1).ravel()
    block: Dict[str, Any] = {
        "class": layer.cls, "role": layer.role, "part_id": layer.part_id,
        "texture": layer.texture.kind, "colors": list(layer.colors),
        "classes": [int(c) for c in cls_flat], "cells": int(mask.sum()),
    }
    if layer.role == "background":
        block.update(method="background", editable_classes=False, values=None,
                     class_labels=_BACKGROUND_LABELS.get(layer.texture.kind,
                                                         [layer.cls] if n == 1 else
                                                         [f"background {i + 1}" for i in range(n)]))
        return block
    method = layer.classification.method
    block.update(method=method, dataset=layer.dataset.id, variable=layer.variable,
                 transform=layer.transform)
    if method == "categorical":
        block.update(editable_classes=False, values=None, categories=list(layer.colors),
                     units="category")
        return block
    vals = np.where(mask, fld.values, np.nan)
    d = _decimals(vals)
    layer_vals = vals[mask]
    flat = vals.ravel()
    block["values"] = [None if not np.isfinite(v) else _round(v, d) for v in flat]
    block["units"] = _units(layer)
    block["decimals"] = d
    block["range"] = [_round(layer_vals.min(), d), _round(layer_vals.max(), d)]
    if method == "bins":
        block["bounds"] = [int(b) if float(b).is_integer() else float(b)
                           for b in layer.classification.bounds]
        block["bounds_source"] = "recipe"
    elif method in RANK_METHODS:
        block["bounds"] = _derived_bounds(layer_vals, classes[mask], n, d)
        block["bounds_source"] = "built classes"
    block["editable_classes"] = method == "bins" or method in RANK_METHODS
    no_value = [int(i) for i in np.flatnonzero((fld.filled & mask).ravel())]
    block["no_value"] = no_value
    block["no_value_ice"] = len(set(no_value) & ice_cells)
    return block


def map_cells(result, *, ice: Optional[IceRegions] = None) -> Dict[str, Any]:
    """The chooser data for ``result`` (a ``MapResult``) on the board as hung."""
    from .build import land_mask_array

    recipe = result.recipe
    arrangement = result.arrangement
    land = arrangement.roll(land_mask_array())
    ice = (ice or load_ice_regions()).rolled(arrangement)
    shadow = (shadow_mask(land, recipe.shadow.direction) if recipe.shadow.enabled
              else np.zeros_like(land))
    kinds = np.where(land, "L", np.where(shadow, "S", "O"))
    ice_land = [int(i) for i in np.flatnonzero(ice.land.ravel())]
    ice_sea = [int(i) for i in np.flatnonzero(ice.sea.ravel())]
    layers = {}
    for layer in recipe.layers:
        mask = land if layer.cls == "land" else ~land & ~shadow
        ice_cells = set(ice_land if layer.cls == "land" else ice_sea)
        layers[layer.cls] = _layer_block(layer, result.classes[layer.cls], mask,
                                         result.fields.get(layer.cls), ice_cells)
    return {
        "format_version": CELLS_FORMAT,
        "recipe": {"id": recipe.id, "title": recipe.title, "sha256": recipe.sha256},
        "arrangement": arrangement.id,
        "width": int(land.shape[1]), "height": int(land.shape[0]),
        "cells": "".join(kinds.ravel().tolist()),
        "layers": layers,
        "shadow": {"enabled": bool(recipe.shadow.enabled), "color": recipe.shadow.color,
                   "cells": int(shadow.sum())},
        "ice": {"land": ice_land, "sea": ice_sea, "color": "lego_white",
                "source": {k: ice.source[k] for k in ("land_ice", "sea_ice") if k in ice.source}},
        "palette": part_palette(),
        "note": PREVIEW_NOTE,
        "disclaimer": DISCLAIMER,
    }

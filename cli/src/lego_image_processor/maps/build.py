"""Build a map from a recipe: per layer read, reproject, classify, texture; then a schema 2.0
layout with ``metadata.map`` provenance and a suitability report (FR-004-FR-006, FR-019).

``build_map`` never downloads: a missing dataset raises ``DatasetNotCachedError``.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np

from .. import __version__
from ..datasets.cache import is_cached, resolve
from ..datasets.readers import read_dataset
from ..datasets.registry import DatasetEntry
from ..kit.part_colors import load_part_colors
from ..kit.source import DISCLAIMER
from ..layout.grid import CURRENT_SCHEMA_VERSION, PositionPlacementGrid
from ..layout.land_sea_mask import load_land_sea_mask
from ..layout.position import (LAND_PART_ID, LAND_PART_TYPE, OCEAN_PART_ID, OCEAN_PART_TYPE,
                               PositionPlacement)
from .classify import MapBuildError, classify
from .projection import load_kit_projection
from .recipe import Layer, Recipe
from .reproject import LayerField, reproject_layer
from .suitability import THRESHOLDS, kit_supply, layer_report
from .texture import apply_blend, fill_background, fill_halo, shadow_mask

_LAYER_SEED = {"land": 0, "ocean": 1}


@dataclass
class MapResult:
    recipe: Recipe
    layout: PositionPlacementGrid
    report: Dict[str, Any]
    classes: Dict[str, np.ndarray] = field(default_factory=dict)
    fields: Dict[str, Optional[LayerField]] = field(default_factory=dict)
    agreement: Optional[Dict[str, Any]] = None


def land_mask_array() -> np.ndarray:
    m = load_land_sea_mask()
    a = np.zeros((m.height, m.width), dtype=bool)
    for y in range(m.height):
        for x in range(m.width):
            a[y, x] = m.is_land(x, y)
    return a


def missing_datasets(recipe: Recipe, cache_dir=None) -> List[DatasetEntry]:
    """Download entries the recipe needs that are not in the cache (for ``--fetch``)."""
    return [e for e in recipe.datasets() if e.kind == "download" and not is_cached(e, cache_dir)]


def _layer_classes(layer: Layer, mask: np.ndarray, seed: int, cache_dir, *, land=None, supply=None):
    """Classes for ``layer`` on the cells in ``mask``. ``land`` is the kit land mask (for the halo);
    ``supply`` overrides one kit's supply (the build passes it net of the shadow)."""
    seq = (seed, _LAYER_SEED[layer.cls])
    if layer.role == "background":
        if layer.texture.kind == "halo":
            land = land_mask_array() if land is None else land
            t = layer.texture
            classes = fill_halo(mask, land, inner=t.inner, outer=t.outer, spacing=t.spacing, seed=seq)
        else:
            classes = fill_background(mask, layer.weights, cluster=layer.texture.cluster, seed=seq)
        return classes, None, None
    entry = layer.dataset
    path = None if entry.kind == "packaged" else resolve(entry, cache_dir)
    grid = read_dataset(entry, path, layer.variable, transform=layer.transform)
    categorical = layer.classification.method == "categorical"
    fld = reproject_layer(grid, load_kit_projection(), mask, layer.cls, categorical=categorical)
    cr = classify(fld.values, mask, layer.classification, layer.colors, categories=grid.categories,
                  supply=kit_supply().get(layer.part_id, {}) if supply is None else supply)
    classes = cr.classes
    if layer.texture.kind == "blend":
        classes = apply_blend(cr, fld.values, mask, width=layer.texture.width, seed=seq)
    return classes, fld, cr


def _medians(values: np.ndarray, classes: np.ndarray, colors) -> List[Dict[str, Any]]:
    out = []
    for i, k in enumerate(colors):
        v = values[classes == i]
        out.append({"key": k, "median": None if v.size == 0 else round(float(np.median(v)), 3)})
    return out


def agreement_with_official(layout: PositionPlacementGrid) -> Dict[str, Any]:
    """Cell agreement of a layout with the official design (color key per position)."""
    from ..kit import load_official_design

    d = load_official_design()
    land = ocean = land_ok = ocean_ok = 0
    for p in layout.positions:
        official = d.color_at(p.x, p.y)
        if official == "lego_white":
            land += 1
            land_ok += p.color_id == official
        else:
            ocean += 1
            ocean_ok += p.color_id == official
    return {"land": {"agree": land_ok, "cells": land, "share": round(land_ok / land, 4) if land else None},
            "ocean": {"agree": ocean_ok, "cells": ocean, "share": round(ocean_ok / ocean, 4) if ocean else None},
            "total": {"agree": land_ok + ocean_ok, "cells": land + ocean}}


def _layer_provenance(layer: Layer) -> Dict[str, Any]:
    out: Dict[str, Any] = {"class": layer.cls, "role": layer.role, "part_id": layer.part_id,
                           "colors": list(layer.colors)}
    if layer.role == "background":
        if layer.weights:
            out["weights"] = list(layer.weights)
    else:
        out["variable"] = layer.variable
        out["transform"] = layer.transform
        out["classification"] = layer.classification.method
        out["dataset"] = layer.dataset.provenance()
    out["texture"] = {"kind": layer.texture.kind}
    if layer.texture.kind == "blend":
        out["texture"]["width"] = layer.texture.width
    elif layer.texture.kind == "mix":
        out["texture"]["cluster"] = layer.texture.cluster
    elif layer.texture.kind == "halo":
        t = layer.texture
        out["texture"].update(inner=t.inner, outer=t.outer, spacing=t.spacing)
    return out


def build_map(recipe: Recipe, *, cache_dir=None, compare_official: Optional[bool] = None) -> MapResult:
    """Build ``recipe`` from packaged or cached data. Raises ``DatasetNotCachedError`` (never
    downloads), ``ChecksumMismatchError`` or ``MapBuildError``."""
    land = land_mask_array()
    table = load_part_colors()
    H, W = land.shape
    labels = np.empty((H, W), dtype=object)
    classes: Dict[str, np.ndarray] = {}
    fields: Dict[str, Optional[LayerField]] = {}
    layer_reports = []
    # The land shadow is assigned first; the ocean layer covers the remaining ocean cells and a
    # supply-capped classification gets one kit's supply net of the shadow (amendment FR-027).
    shadow = shadow_mask(land, recipe.shadow.direction) if recipe.shadow.enabled else np.zeros_like(land)
    n_shadow = int(shadow.sum())
    labels[shadow] = recipe.shadow.color
    shadow_use = {recipe.shadow.color: n_shadow} if n_shadow else {}
    ocean_supply = dict(kit_supply().get(OCEAN_PART_ID, {}))
    for k, n in shadow_use.items():
        if k in ocean_supply:
            ocean_supply[k] = max(0, ocean_supply[k] - n)
    for layer in recipe.layers:
        mask = land if layer.cls == "land" else ~land & ~shadow
        cl, fld, cr = _layer_classes(layer, mask, recipe.seed, cache_dir, land=land,
                                     supply=ocean_supply if layer.cls == "ocean" else None)
        if (cl[mask] < 0).any():  # pragma: no cover - guarded by classify
            raise MapBuildError(f"{layer.cls}: some cells got no class")
        classes[layer.cls], fields[layer.cls] = cl, fld
        for i, key in enumerate(layer.colors):
            labels[mask & (cl == i)] = key
        rep = layer_report(cls=layer.cls, role=layer.role, part_id=layer.part_id, colors=layer.colors,
                           field=fld, classes=np.where(mask, cl, -1),
                           ordered=bool(layer.classification and layer.classification.ordered),
                           layer_cells=int(mask.sum()), below=getattr(cr, "below", 0),
                           above=getattr(cr, "above", 0), bounds=getattr(cr, "bounds", ()),
                           dataset=layer.dataset.provenance() if layer.dataset else None,
                           method=layer.classification.method if layer.classification else None,
                           extra_use=shadow_use if layer.cls == "ocean" else None)
        if fld is not None and layer.classification.ordered:
            rep["median_by_color"] = _medians(fld.values, np.where(mask, cl, -1), layer.colors)
        layer_reports.append(rep)

    positions = []
    for y in range(H):
        for x in range(W):
            is_land = bool(land[y, x])
            part = LAND_PART_ID if is_land else OCEAN_PART_ID
            c = table.get(part, labels[y, x])
            positions.append(PositionPlacement(
                x=x, y=y, color_id=c.key, color_name=c.lego.name, lego_color_code=str(c.lego.id),
                part_type=LAND_PART_TYPE if is_land else OCEAN_PART_TYPE, lego_part_id=part))
    citations = [e.provenance() for e in recipe.datasets()]
    provenance = {
        "recipe": {"id": recipe.id, "format": recipe.format, "title": recipe.title, "sha256": recipe.sha256},
        "layers": [_layer_provenance(layer) for layer in recipe.layers],
        "shadow": recipe.shadow.provenance(n_shadow),
        "seed": recipe.seed,
        "tool_version": __version__,
        "disclaimer": DISCLAIMER,
    }
    layout = PositionPlacementGrid(width=W, height=H, positions=positions, source_image=f"recipe:{recipe.id}",
                                   schema_version=CURRENT_SCHEMA_VERSION, map_metadata=provenance)
    if compare_official is None:
        compare_official = recipe.id.startswith("official-31203")
    agreement = agreement_with_official(layout) if compare_official else None
    report = {
        "recipe_id": recipe.id, "recipe_title": recipe.title, "recipe_sha256": recipe.sha256,
        "seed": recipe.seed, "shadow": recipe.shadow.provenance(n_shadow), "layers": layer_reports, "thresholds": dict(THRESHOLDS),
        "citations": citations,
        "warnings": [w for r in layer_reports for w in r["warnings"]],
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tool_version": __version__,
        "disclaimer": DISCLAIMER,
    }
    if agreement is not None:
        report["agreement_with_official"] = agreement
    return MapResult(recipe=recipe, layout=layout, report=report, classes=classes, fields=fields,
                     agreement=agreement)


def check_recipe(recipe: Recipe, *, cache_dir=None) -> Dict[str, Any]:
    """The suitability report of ``recipe`` without writing a layout (``map check``)."""
    return build_map(recipe, cache_dir=cache_dir).report

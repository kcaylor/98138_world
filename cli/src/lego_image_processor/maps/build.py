"""Build a map from a recipe: per layer read, reproject, classify, texture; then a schema 2.0
layout with ``metadata.map`` provenance and a suitability report (FR-004-FR-006, FR-019).

``build_map`` never downloads: a missing dataset raises ``DatasetNotCachedError``.

Arrangements (feature 007): per-cell work (reprojection, classification, the value-space ``blend``
texture) runs in kit coordinates, exactly as for combination A, and is then placed as hung; the
spatial neighbourhood work (land shadow, halo, ``mix``) runs on the grid as hung, with no wrap at
the outer left and right edges.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .. import __version__
from ..datasets.cache import is_cached, resolve
from ..datasets.readers import read_dataset
from ..datasets.registry import DatasetEntry
from ..kit.part_colors import load_part_colors
from ..kit.source import DISCLAIMER
from ..layout.grid import CURRENT_SCHEMA_VERSION, PositionPlacementGrid
from ..layout.arrangement import Arrangement, parse_arrangement
from ..layout.land_sea_mask import load_land_sea_mask
from ..layout.position import (LAND_PART_ID, LAND_PART_TYPE, OCEAN_PART_ID, OCEAN_PART_TYPE,
                               PositionPlacement)
from .classify import MapBuildError, classify
from .projection import load_kit_projection
from .recipe import Layer, Recipe
from .nodata import apply_value, no_data_cells
from .overrides import override_cells
from .reproject import LayerField, reproject_layer
from .suitability import THRESHOLDS, kit_supply, layer_report
from .texture import apply_blend, fill_background, fill_halo, shadow_mask

_LAYER_SEED = {"land": 0, "ocean": 1}
NO_DATA_CLASS = -2  # feature 012: class of a layer's no-data cells (they take no_data.color)
OVERRIDE_CLASS_BASE = -10  # feature 013: override i has class OVERRIDE_CLASS_BASE - i


def override_class(i: int) -> int:
    return OVERRIDE_CLASS_BASE - i


@dataclass
class MapResult:
    recipe: Recipe
    layout: PositionPlacementGrid
    report: Dict[str, Any]
    classes: Dict[str, np.ndarray] = field(default_factory=dict)
    fields: Dict[str, Optional[LayerField]] = field(default_factory=dict)
    agreement: Optional[Dict[str, Any]] = None
    arrangement: Optional[Arrangement] = None  # as hung (feature 009: resolved by resolve_arrangement)


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


def resolve_arrangement(recipe: Recipe,
                        arrangement: Optional[Arrangement] = None) -> Tuple[Arrangement, str]:
    """The arrangement to hang ``recipe`` and where it came from (feature 009, FR-011):
    a passed ``arrangement`` (CLI ``--arrangement`` or a library argument) -> ``"option"``; else the
    recipe's ``arrangement`` key -> ``"recipe"``; else A -> ``"default"``."""
    if arrangement is not None:
        return arrangement, "option"
    if recipe.arrangement is not None:
        return recipe.arrangement, "recipe"
    return parse_arrangement(None), "default"


def _rolled_field(fld: LayerField, arrangement: Arrangement) -> LayerField:
    return LayerField(values=arrangement.roll(fld.values), samples=arrangement.roll(fld.samples),
                      filled=arrangement.roll(fld.filled), variance_lost=fld.variance_lost,
                      total_variance=fld.total_variance)


def _layer_classes(layer: Layer, mask: np.ndarray, seed: int, cache_dir, *, land=None, supply=None,
                   arrangement: Optional[Arrangement] = None):
    """Classes for ``layer`` on the cells in ``mask`` (display coordinates, as hung); no-data cells
    (feature 012) get ``NO_DATA_CLASS``. ``land`` is
    the land mask as hung (for the halo); ``supply`` overrides one kit's supply (the build passes
    it net of the shadow). Data layers are reprojected, classified and blended in kit coordinates
    and returned as hung."""
    arrangement = arrangement or parse_arrangement(None)
    seq = (seed, _LAYER_SEED[layer.cls])
    if layer.role == "background":
        if layer.texture.kind == "halo":
            land = arrangement.roll(land_mask_array()) if land is None else land
            t = layer.texture
            classes = fill_halo(mask, land, inner=t.inner, outer=t.outer, spacing=t.spacing, seed=seq)
        else:
            classes = fill_background(mask, layer.weights, cluster=layer.texture.cluster, seed=seq)
        return classes, None, None
    entry = layer.dataset
    path = None if entry.kind == "packaged" else resolve(entry, cache_dir)
    try:
        grid = read_dataset(entry, path, layer.variable, transform=layer.transform, cache_dir=cache_dir)
    except ValueError as exc:  # unreadable file (e.g. netCDF-4 given as netcdf3): exit 1, no traceback
        raise MapBuildError(f"{layer.cls}: cannot read {entry.id}: {exc}") from exc
    grid = apply_value(grid, layer.no_data, layer.cls, layer.transform)
    categorical = layer.classification.method == "categorical"
    kit_mask = arrangement.unroll(mask)
    projection = load_kit_projection()
    try:
        fld = reproject_layer(grid, projection, kit_mask, layer.cls, categorical=categorical,
                              sampling=layer.sampling)
    except ValueError as exc:
        if layer.sampling == "mean":
            raise
        raise MapBuildError(f"{layer.cls}: {exc}") from exc
    # feature 012: no-data cells take the rule's color and are left out of the classification
    try:
        nod = no_data_cells(layer.no_data, grid, fld, kit_mask, projection, layer.cls)
    except ValueError as exc:
        raise MapBuildError(f"{layer.cls}: {exc}") from exc
    # feature 013: override cells likewise (after no-data; earlier overrides win)
    ovr = []
    if layer.overrides:
        try:
            ovr = override_cells(layer.overrides, kit_mask, nod, projection, layer.cls, cache_dir)
        except ValueError as exc:
            raise MapBuildError(f"{layer.cls}: override: {exc}") from exc
    excluded = nod.copy()
    for m in ovr:
        excluded |= m
    cmask = kit_mask & ~excluded
    if excluded.any():
        if not cmask.any():
            what = "the no_data rule" if not ovr else "the no_data and override rules"
            raise MapBuildError(f"{layer.cls}: {what} leave no cells to classify")
        fld = LayerField(values=np.where(cmask, fld.values, np.nan), samples=fld.samples,
                         filled=fld.filled & cmask, variance_lost=fld.variance_lost,
                         total_variance=fld.total_variance)
    supply = dict(kit_supply().get(layer.part_id, {}) if supply is None else supply)
    n_nod = int(nod.sum())
    if n_nod and layer.no_data.color in supply:
        supply[layer.no_data.color] = max(0, supply[layer.no_data.color] - n_nod)
    for o, m in zip(layer.overrides, ovr):
        if m.any() and o.color in supply:
            supply[o.color] = max(0, supply[o.color] - int(m.sum()))
    cr = classify(fld.values, cmask, layer.classification, layer.colors, categories=grid.categories,
                  supply=supply)
    classes = cr.classes
    if layer.texture.kind == "blend":
        classes = apply_blend(cr, fld.values, cmask, width=layer.texture.width, seed=seq)
    classes = np.where(nod, NO_DATA_CLASS, classes)
    for i, m in enumerate(ovr):
        classes = np.where(m, override_class(i), classes)
    return arrangement.roll(classes), _rolled_field(fld, arrangement), cr


def _medians(values: np.ndarray, classes: np.ndarray, colors) -> List[Dict[str, Any]]:
    out = []
    for i, k in enumerate(colors):
        v = values[classes == i]
        out.append({"key": k, "median": None if v.size == 0 else round(float(np.median(v)), 3)})
    return out


def agreement_with_official(layout: PositionPlacementGrid,
                            arrangement: Optional[Arrangement] = None) -> Dict[str, Any]:
    """Cell agreement of a layout with the official design hung the same way (color key per
    position)."""
    from ..kit import load_official_design

    arrangement = arrangement or parse_arrangement(None)
    d = load_official_design()
    land = ocean = land_ok = ocean_ok = 0
    for p in layout.positions:
        official = d.color_at(arrangement.to_kit(p.x), p.y)
        if official == "lego_white":
            land += 1
            land_ok += p.color_id == official
        else:
            ocean += 1
            ocean_ok += p.color_id == official
    return {"land": {"agree": land_ok, "cells": land, "share": round(land_ok / land, 4) if land else None},
            "ocean": {"agree": ocean_ok, "cells": ocean, "share": round(ocean_ok / ocean, 4) if ocean else None},
            "total": {"agree": land_ok + ocean_ok, "cells": land + ocean}}


def _layer_provenance(layer: Layer, no_data_cells: int = 0,
                      override_counts: Optional[List[int]] = None) -> Dict[str, Any]:
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
        if layer.dataset.mask_dataset_id:
            out["land_from"] = dict(layer.dataset.class_rule["land_from"])
        if layer.no_data is not None:
            out["no_data"] = layer.no_data.provenance(no_data_cells)
        if layer.sampling != "mean":  # feature 013 (absent = mean, so existing layouts are unchanged)
            out["sampling"] = layer.sampling
        if layer.overrides:
            counts = override_counts or [0] * len(layer.overrides)
            out["overrides"] = [o.provenance(n) for o, n in zip(layer.overrides, counts)]
        if layer.legend is not None:
            out["legend"] = layer.legend.to_dict()
    out["texture"] = {"kind": layer.texture.kind}
    if layer.texture.kind == "blend":
        out["texture"]["width"] = layer.texture.width
    elif layer.texture.kind == "mix":
        out["texture"]["cluster"] = layer.texture.cluster
    elif layer.texture.kind == "halo":
        t = layer.texture
        out["texture"].update(inner=t.inner, outer=t.outer, spacing=t.spacing)
    return out


def build_map(recipe: Recipe, *, cache_dir=None, compare_official: Optional[bool] = None,
              arrangement: Optional[Arrangement] = None) -> MapResult:
    """Build ``recipe`` from packaged or cached data, hung as ``arrangement`` (default: the
    recipe's ``arrangement``, else A; see ``resolve_arrangement``). Raises
    ``DatasetNotCachedError`` (never downloads), ``ChecksumMismatchError`` or ``MapBuildError``."""
    arrangement, arrangement_source = resolve_arrangement(recipe, arrangement)
    land = arrangement.roll(land_mask_array())  # as hung
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
    no_data_cells_by_layer: Dict[str, int] = {}
    override_counts_by_layer: Dict[str, List[int]] = {}
    for layer in recipe.layers:
        mask = land if layer.cls == "land" else ~land & ~shadow
        cl, fld, cr = _layer_classes(layer, mask, recipe.seed, cache_dir, land=land,
                                     supply=ocean_supply if layer.cls == "ocean" else None,
                                     arrangement=arrangement)
        nod = mask & (cl == NO_DATA_CLASS)
        ovr = [mask & (cl == override_class(i)) for i in range(len(layer.overrides))]
        data_mask = mask & ~nod
        for m in ovr:
            data_mask &= ~m
        if (cl[data_mask] < 0).any():  # pragma: no cover - guarded by classify
            raise MapBuildError(f"{layer.cls}: some cells got no class")
        classes[layer.cls], fields[layer.cls] = cl, fld
        for i, key in enumerate(layer.colors):
            labels[data_mask & (cl == i)] = key
        extra = dict(shadow_use) if layer.cls == "ocean" else {}
        n_nod = int(nod.sum())
        if layer.no_data is not None:
            no_data_cells_by_layer[layer.cls] = n_nod
            if n_nod:
                labels[nod] = layer.no_data.color
                extra[layer.no_data.color] = extra.get(layer.no_data.color, 0) + n_nod
        for o, m in zip(layer.overrides, ovr):  # feature 013
            n = int(m.sum())
            if n:
                labels[m] = o.color
                extra[o.color] = extra.get(o.color, 0) + n
        if layer.overrides:
            override_counts_by_layer[layer.cls] = [int(m.sum()) for m in ovr]
        bounds = getattr(cr, "bounds", ())
        if bounds and layer.transform == "log10":  # report bounds in the variable's units (012)
            bounds = tuple(float(10 ** b) for b in bounds)
        rep = layer_report(cls=layer.cls, role=layer.role, part_id=layer.part_id, colors=layer.colors,
                           field=fld, classes=np.where(data_mask, cl, -1),
                           ordered=bool(layer.classification and layer.classification.ordered),
                           layer_cells=int(data_mask.sum()), below=getattr(cr, "below", 0),
                           above=getattr(cr, "above", 0), bounds=bounds,
                           dataset=layer.dataset.provenance() if layer.dataset else None,
                           method=layer.classification.method if layer.classification else None,
                           extra_use=extra or None)
        if layer.no_data is not None:
            rep["no_data"] = layer.no_data.provenance(n_nod)
        if layer.overrides:  # feature 013
            rep["overrides"] = [o.provenance(n) for o, n in
                                zip(layer.overrides, override_counts_by_layer[layer.cls])]
        if layer.legend is not None:
            rep["legend"] = layer.legend.to_dict()
        if layer.role == "data" and layer.sampling != "mean":
            rep["sampling"] = layer.sampling
        if layer.role == "data" and layer.transform == "log10":  # bounds and medians in data units
            rep["transform"] = layer.transform
        if fld is not None and layer.classification.ordered:
            med = _medians(fld.values, np.where(data_mask, cl, -1), layer.colors)
            if layer.transform == "log10":
                for m in med:
                    if m["median"] is not None:
                        m["median"] = round(float(10 ** m["median"]), 3)
            rep["median_by_color"] = med
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
        "layers": [_layer_provenance(layer, no_data_cells_by_layer.get(layer.cls, 0),
                                     override_counts_by_layer.get(layer.cls))
                   for layer in recipe.layers],
        "shadow": recipe.shadow.provenance(n_shadow),
        "seed": recipe.seed,
        "tool_version": __version__,
        "disclaimer": DISCLAIMER,
    }
    layout = PositionPlacementGrid(width=W, height=H, positions=positions, source_image=f"recipe:{recipe.id}",
                                   schema_version=CURRENT_SCHEMA_VERSION, map_metadata=provenance,
                                   arrangement=arrangement.record())
    if compare_official is None:
        compare_official = recipe.id.startswith("official-31203")
    agreement = agreement_with_official(layout, arrangement) if compare_official else None
    report = {
        "recipe_id": recipe.id, "recipe_title": recipe.title, "recipe_sha256": recipe.sha256,
        "seed": recipe.seed, "arrangement": arrangement.record(),
        "arrangement_source": arrangement_source, "shadow": recipe.shadow.provenance(n_shadow), "layers": layer_reports, "thresholds": dict(THRESHOLDS),
        "citations": citations,
        "warnings": [w for r in layer_reports for w in r["warnings"]],
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tool_version": __version__,
        "disclaimer": DISCLAIMER,
    }
    if agreement is not None:
        report["agreement_with_official"] = agreement
    return MapResult(recipe=recipe, layout=layout, report=report, classes=classes, fields=fields,
                     agreement=agreement, arrangement=arrangement)


def check_recipe(recipe: Recipe, *, cache_dir=None, arrangement: Optional[Arrangement] = None) -> Dict[str, Any]:
    """The suitability report of ``recipe`` without writing a layout (``map check``)."""
    return build_map(recipe, cache_dir=cache_dir, arrangement=arrangement).report

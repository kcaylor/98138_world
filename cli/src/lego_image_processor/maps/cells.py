"""Per-cell data for the palette chooser (feature 015, FR-001; contracts/cells-json.md).

``map_cells(result)`` turns a built map (``build_map``) into a JSON-ready dict for the board as
hung: each layer's built class per cell and (data layers) value per cell, the default class
bounds, the land shadow, the ice regions and the cited colors of both parts with CIE L*. A
browser can then recolor the map, try other class bounds, or show ice as White without
recomputing anything else. It is a preview aid only: layouts, parts lists, prices and build
sheets never read it (FR-004).

Feature 016 (FR-020a; research R18; contracts/recipe-and-outputs.md ``cells.json``): on a non-kit
template ``cells`` also holds ``M`` (margin studs, which belong to no layer), the shadow falls on
ocean studs only, ``ice`` comes from the template's own ice file (``load_template_ice``), and three
blocks are added: ``template`` (id, title and the dataset that decided land and ocean: id, version,
citation, license), ``margin`` (part 3070b, the margin color and the ring with its cells, or null)
and ``palette["3070b"]``. The default rendering takes the ring color on ``margin.ring.cells``, the
margin color on the other ``M`` cells, and equals the layout. Kit files are unchanged.

Feature 017 (contracts/in-margin-plaque.md ``cells.json``): with an in-margin plaque
(``MapResult.plaque``) its studs are ``P`` instead of ``M`` and a ``plaque`` block follows
``margin``: ``{part_id, color, rgb, corner, cells}`` (the tile's cited Black from
plaque_parts.json; ``cells`` are the board indices). The default rendering takes the plaque's color
on ``P`` cells. Files without a plaque are unchanged, and the site's chooser (``palette.js``) never
receives one (no site variant has a plaque). Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from ..kit.part_colors import KIT_PARTS, load_part_colors
from ..kit.source import DISCLAIMER
from ..palette.converter import rgb_to_lab
from .ice import IceRegions, load_ice_regions, load_template_ice
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


def part_palette(parts: Sequence[str] = KIT_PARTS) -> Dict[str, List[Dict[str, Any]]]:
    """The cited colors of each of ``parts`` (the template's parts; default the kit's 6141 and
    98138, so the 3070b rows never reach a kit ``cells.json``), light to dark (ties by LEGO name)."""
    table = load_part_colors()
    out = {}
    for part in parts:
        rows = table.for_part(part)
        items = [{"key": c.key, "lego": {"name": c.lego.name, "id": c.lego.id},
                  "bricklink": {"name": c.bricklink.name, "id": c.bricklink.id},
                  "rgb": [int(v) for v in c.rgb], "in_kit": bool(c.in_kit),
                  "lightness": lightness(c.rgb)} for c in rows]
        items.sort(key=lambda r: (-r["lightness"], r["lego"]["name"]))
        out[part] = items
    return out


def variable_units(layer: Layer) -> str:
    """The units of a data layer's variable as the registry spells them, "°C" for its Celsius
    spellings; no ``log10`` prefix (the sticker legend prints log10 layers in data units, feature
    017). A layer without a dataset (background) has none."""
    if layer.dataset is None:
        return ""
    u = str(((layer.dataset.variables or {}).get(layer.variable, {}) or {}).get("units", "") or "")
    return _UNITS.get(u.lower(), u)


def _units(layer: Layer) -> str:
    u = variable_units(layer)
    # values and bounds are exported after the recipe transform (feature 012 ``log10``)
    return f"log10 {u}".strip() if getattr(layer, "transform", None) == "log10" else u


def _decimals(values: np.ndarray) -> int:
    finite = values[np.isfinite(values)]
    return 2 if finite.size == 0 or float(np.abs(finite).max()) < 100 else 0


def _round(v: float, d: int):
    return int(round(v)) if d == 0 else round(float(v), d)


def derived_bounds(values: np.ndarray, classes: np.ndarray, n: int) -> List[float]:
    """Value boundaries between the ``n`` built classes of a rank-based layer, unrounded: the
    smallest value, the midpoint between the last value of one class and the first of the next in
    sorted order, and the largest value (the blend texture swaps cells in pairs, so class counts
    are those of the ranking). ``map cells`` rounds them; the sticker legend (feature 017) rounds
    them to its display step."""
    sv = np.sort(values)
    counts = [int((classes == i).sum()) for i in range(n)]
    cum = np.cumsum(counts)[:-1]
    inner = []
    for c in cum:
        c = int(min(max(c, 1), len(sv) - 1))
        inner.append(float((sv[c - 1] + sv[c]) / 2.0))
    return [float(sv[0])] + inner + [float(sv[-1])]


def background_labels(layer: Layer) -> List[str]:
    """The role of each color of a background layer: "offshore" and "coast ring" for a halo, the
    layer's name for one color, else "background 1", "background 2", ... (shared with the
    sticker legend, feature 017)."""
    n = len(layer.colors)
    return list(_BACKGROUND_LABELS.get(layer.texture.kind,
                                       [layer.cls] if n == 1 else
                                       [f"background {i + 1}" for i in range(n)]))


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
                     class_labels=background_labels(layer))
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
    # cells left without a value (a recipe ``no_data`` rule, feature 012 living planet) are
    # skipped for the range and the derived bounds; they keep their built class
    ok = mask & np.isfinite(vals)
    layer_vals = vals[ok]
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
        block["bounds"] = [_round(b, d) for b in derived_bounds(layer_vals, classes[ok], n)]
        block["bounds_source"] = "built classes"
    block["editable_classes"] = method == "bins" or method in RANK_METHODS
    no_value = [int(i) for i in np.flatnonzero((fld.filled & mask).ravel())]
    block["no_value"] = no_value
    block["no_value_ice"] = len(set(no_value) & ice_cells)
    return block


def _template_block(template) -> Dict[str, Any]:
    """``template`` of a non-kit ``cells.json``: id, title and its dataset (id, version, citation,
    license)."""
    ds = template.dataset
    return {"id": template.id, "title": template.title,
            "dataset": None if ds is None else {"id": ds.id, "version": ds.version, "citation": ds.citation,
                                                "license": ds.license}}


def _margin_block(template, treatment) -> Dict[str, Any]:
    """``margin`` of a non-kit ``cells.json``: the square tile, its color and the ring (or null)."""
    from .margin import MARGIN_PART_ID, MarginTreatment, ring_cells

    treatment = treatment or MarginTreatment()
    ring = None
    if treatment.ring is not None:
        ring = {"color": treatment.ring, "cells": [int(i) for i in np.flatnonzero(ring_cells(template).ravel())]}
    return {"part_id": MARGIN_PART_ID, "color": treatment.color, "ring": ring}


def _plaque_block(plaque, shape) -> Dict[str, Any]:
    """``plaque`` of a ``cells.json`` with an in-margin plaque (feature 017): its tile, cited color
    and the board indices of its studs."""
    from .margin import plaque_tile

    tile = plaque_tile()
    return {"part_id": plaque.part_id, "color": plaque.color, "rgb": [int(v) for v in tile.color.rgb],
            "corner": plaque.corner, "cells": [int(i) for i in np.flatnonzero(plaque.mask(shape).ravel())]}


def _template_cells(result, ice: Optional[IceRegions]) -> Dict[str, Any]:
    """``map_cells`` on a non-kit template (feature 016): board coordinates, arrangement A; the
    in-margin plaque's studs ``P`` (feature 017)."""
    recipe, tpl = result.recipe, result.template
    land, ocean, margin = np.array(tpl.land), np.array(tpl.ocean), np.array(tpl.margin)
    ice = ice or load_template_ice(tpl)
    shadow = (shadow_mask(land, recipe.shadow.direction, ocean=ocean) if recipe.shadow.enabled
              else np.zeros_like(land))
    kinds = np.where(land, "L", np.where(margin, "M", np.where(shadow, "S", "O")))
    plaque = getattr(result, "plaque", None)
    if plaque is not None:
        kinds = np.where(plaque.mask(land.shape), "P", kinds)
    ice_land = [int(i) for i in np.flatnonzero(ice.land.ravel())]
    ice_sea = [int(i) for i in np.flatnonzero(ice.sea.ravel())]
    layers = {}
    for layer in recipe.layers:
        mask = land if layer.cls == "land" else ocean & ~shadow
        ice_cells = set(ice_land if layer.cls == "land" else ice_sea)
        layers[layer.cls] = _layer_block(layer, result.classes[layer.cls], mask,
                                         result.fields.get(layer.cls), ice_cells)
    out = {
        "format_version": CELLS_FORMAT,
        "recipe": {"id": recipe.id, "title": recipe.title, "sha256": recipe.sha256},
        "arrangement": result.arrangement.id,
        "template": _template_block(tpl),
        "width": int(land.shape[1]), "height": int(land.shape[0]),
        "cells": "".join(kinds.ravel().tolist()),
        "layers": layers,
        "shadow": {"enabled": bool(recipe.shadow.enabled), "color": recipe.shadow.color,
                   "cells": int(shadow.sum())},
        "margin": _margin_block(tpl, result.margin),
    }
    if plaque is not None:  # feature 017: only when one is placed
        out["plaque"] = _plaque_block(plaque, land.shape)
    out.update({
        "ice": {"land": ice_land, "sea": ice_sea, "color": "lego_white",
                "source": {k: ice.source[k] for k in ("land_ice", "sea_ice") if k in ice.source}},
        "palette": part_palette(tuple(tpl.parts[k] for k in ("land", "ocean", "margin"))),
        "note": PREVIEW_NOTE,
        "disclaimer": DISCLAIMER,
    })
    return out


def map_cells(result, *, ice: Optional[IceRegions] = None) -> Dict[str, Any]:
    """The chooser data for ``result`` (a ``MapResult``) on the board as hung. On a non-kit
    template (feature 016) ``ice`` defaults to the template's ice file (``TemplateIceError`` when it
    is missing or made for another layout)."""
    from .build import land_mask_array

    if result.template is not None and not result.template.is_kit:
        return _template_cells(result, ice)
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

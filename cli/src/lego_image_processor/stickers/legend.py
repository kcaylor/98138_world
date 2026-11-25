"""The large sticker's color legend, computed from a built map (feature 017, FR-005, FR-006;
research R7, R8; data-model.md Swatch, Meaning).

``map_legend(result)`` reads a ``MapResult`` only: its recipe, built classes, layer values and
arrangement. It never reads, reprojects or classifies data. One swatch per (part, color), the
land group before the ocean group; per layer its colors in recipe order, then its no-data
color, its overrides and (ocean) the land shadow. A color met again adds its meaning to the
earlier swatch ("-2 °C; land shadow", "Antarctica; Greenland"). Every class of the scale is
listed, even with no studs; no-data, override and shadow entries only when they cover a stud.

Labels: bins classes by the recipe bounds with open end classes (the outer bounds never
printed), ``log10`` layers back in data units, a ``[<layer>.legend]`` layer in its second unit
only; rank classes by the boundaries ``maps.cells.derived_bounds`` gives (outer bounds
included), rounded to the display step at which combinations A-E agree (research R8);
categorical colors by their cited LEGO names; background colors by role (``maps.cells``);
no-data by the ``[sticker] no_data`` label or "no data"; overrides by name; the shadow as "land
shadow". Swatch colors are the parts' cited sRGB (``part_colors.json``).

On a non-kit template (feature 016) the land and ocean studs are the template's own and the
shadow falls on its ocean studs only, as ``build_map`` and ``map_cells`` place them; the margin
belongs to no layer and has no swatch.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple, Union

import numpy as np

from ..kit.part_colors import load_part_colors
from ..layout.arrangement import parse_arrangement
from ..maps.build import NO_DATA_CLASS, MapResult, land_mask_array, override_class
from ..maps.cells import background_labels, derived_bounds, variable_units
from ..maps.recipe import RANK_METHODS, Layer
from ..maps.texture import shadow_mask
from .text import (display_step, format_number, number_value, round_significant, round_to_step,
                   to_decimal)

KINDS = ("class", "background", "category", "no_data", "override", "shadow")
SOURCE_BINS = "recipe bins"
SOURCE_BUILT = "built classes"
NO_DATA_LABEL = "no data"
SHADOW_LABEL = "land shadow"
HEADINGS = {"land": "Land", "ocean": "Ocean"}
KIT_DESIGN_HEADING = "{}: the kit design's colors"

JsonNumber = Union[int, float]


@dataclass(frozen=True)
class Meaning:
    """What a swatch's color stands for. ``range``, ``units``, ``source`` (and ``step`` for rank
    layers) are set for ``class`` meanings only; ``range`` holds the numbers as displayed, None
    for an open end."""

    kind: str
    label: str
    range: Optional[Tuple[Optional[JsonNumber], Optional[JsonNumber]]] = None
    units: Optional[str] = None
    source: Optional[str] = None
    step: Optional[JsonNumber] = None

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"kind": self.kind, "label": self.label}
        if self.kind == "class":
            out["range"] = list(self.range) if self.range is not None else None
            out["units"] = self.units
            out["source"] = self.source
            if self.step is not None:
                out["step"] = self.step
        return out


@dataclass(frozen=True)
class Swatch:
    layer: str
    part_id: str
    color: str
    rgb: Tuple[int, int, int]
    lego_name: str
    meanings: Tuple[Meaning, ...]

    @property
    def label(self) -> str:
        """The swatch's printed text: its meanings joined with "; "."""
        return "; ".join(m.label for m in self.meanings)

    def to_dict(self) -> Dict[str, Any]:
        return {"layer": self.layer, "part_id": self.part_id, "color": self.color,
                "lego_name": self.lego_name, "rgb": [int(v) for v in self.rgb],
                "meanings": [m.to_dict() for m in self.meanings]}


@dataclass(frozen=True)
class LegendGroup:
    """One layer's swatches under its heading ("Land", "Ocean", or "Ocean: the kit design's
    colors" for the kit design grid)."""

    layer: str
    heading: str
    swatches: Tuple[Swatch, ...]


@dataclass(frozen=True)
class Legend:
    groups: Tuple[LegendGroup, ...]

    @property
    def swatches(self) -> Tuple[Swatch, ...]:
        return tuple(s for g in self.groups for s in g.swatches)

    def __iter__(self) -> Iterator[Swatch]:
        return iter(self.swatches)

    def __len__(self) -> int:
        return len(self.swatches)

    def group(self, layer: str) -> LegendGroup:
        for g in self.groups:
            if g.layer == layer:
                return g
        raise KeyError(layer)

    def to_list(self) -> List[Dict[str, Any]]:
        """The JSON summary's ``legend`` (contracts/sticker-files.md)."""
        return [s.to_dict() for s in self.swatches]


# --- labels -----------------------------------------------------------------------------------

def _units(layer: Layer) -> str:
    return layer.legend.units if layer.legend is not None else variable_units(layer)


def _data_units(layer: Layer, bounds: Sequence[float]) -> List[Decimal]:
    """Bounds in the units the legend prints: ``log10`` back in data units, then the
    ``[legend]`` factor (exact decimal product: 0.5 mm/day x 365 = 182.5 mm/yr)."""
    out = []
    for b in bounds:
        v = float(10 ** b) if layer.transform == "log10" else float(b)
        d = to_decimal(v)
        if layer.legend is not None:
            d = d * to_decimal(layer.legend.factor)
        out.append(d)
    return out


def _with_units(text: str, units: str) -> str:
    return f"{text} {units}" if units else text


def _bins_meanings(layer: Layer) -> List[Meaning]:
    units = _units(layer)
    b = _data_units(layer, layer.classification.bounds)
    shown = [format_number(v) for v in b]
    nums = [number_value(round_significant(v)) for v in b]
    n = len(layer.colors)
    out = []
    for i in range(n):
        if n == 1:  # one class: no inner bound to print, so its outer bounds stand
            label, rng = f"{shown[0]} to {_with_units(shown[1], units)}", (nums[0], nums[1])
        elif i == 0:
            label, rng = f"below {_with_units(shown[1], units)}", (None, nums[1])
        elif i == n - 1:
            label, rng = f"{_with_units(shown[i], units)} and above", (nums[i], None)
        else:
            label, rng = f"{shown[i]} to {_with_units(shown[i + 1], units)}", (nums[i], nums[i + 1])
        out.append(Meaning("class", label, range=rng, units=units, source=SOURCE_BINS))
    return out


def _rank_meanings(layer: Layer, classes: np.ndarray, mask: np.ndarray, fld) -> List[Meaning]:
    units = _units(layer)
    n = len(layer.colors)
    vals = np.where(mask, fld.values, np.nan)
    ok = mask & np.isfinite(vals)
    b = _data_units(layer, derived_bounds(vals[ok], classes[ok], n))
    step = display_step(b[0], b[-1])
    r = [round_to_step(v, step) for v in b]
    out = []
    for i in range(n):
        lo, hi = r[i], r[i + 1]
        if lo == hi:
            label = _with_units(format_number(lo, step), units)
        else:
            label = f"{format_number(lo, step)} to {_with_units(format_number(hi, step), units)}"
        out.append(Meaning("class", label, range=(number_value(lo), number_value(hi)), units=units,
                           source=SOURCE_BUILT, step=number_value(step)))
    return out


def _scale_meanings(layer: Layer, classes: np.ndarray, mask: np.ndarray, fld,
                    lego_names: Sequence[str]) -> List[Meaning]:
    if layer.role == "background":
        return [Meaning("background", label) for label in background_labels(layer)]
    method = layer.classification.method
    if method == "categorical":
        return [Meaning("category", name) for name in lego_names]
    if method == "bins":
        return _bins_meanings(layer)
    if method in RANK_METHODS:
        return _rank_meanings(layer, classes, mask, fld)
    raise ValueError(f"{layer.cls}: no legend for classification {method!r}")  # pragma: no cover


def _heading(layer: Layer) -> str:
    base = HEADINGS[layer.cls]
    if (layer.role == "data" and layer.classification.method == "categorical"
            and layer.dataset is not None and layer.dataset.format == "kit-design"):
        return KIT_DESIGN_HEADING.format(base)
    return base


# --- the legend -------------------------------------------------------------------------------

def _masks(result: MapResult) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Land, ocean and shadow studs of the build: the kit's land/sea mask as hung, or a non-kit
    template's land and ocean with the shadow on its ocean studs (feature 016)."""
    recipe, tpl = result.recipe, result.template
    if tpl is not None and not tpl.is_kit:
        land, ocean = np.array(tpl.land), np.array(tpl.ocean)
        shadow = (shadow_mask(land, recipe.shadow.direction, ocean=ocean) if recipe.shadow.enabled
                  else np.zeros_like(land))
        return land, ocean, shadow
    arrangement = result.arrangement or parse_arrangement(None)
    land = arrangement.roll(land_mask_array())
    shadow = (shadow_mask(land, recipe.shadow.direction) if recipe.shadow.enabled
              else np.zeros_like(land))
    return land, ~land, shadow


def map_legend(result: MapResult) -> Legend:
    """The legend of a built map (data-model.md Swatch order and Meaning rules)."""
    recipe = result.recipe
    land, ocean, shadow = _masks(result)
    table = load_part_colors()
    labels = dict((recipe.sticker.no_data if recipe.sticker is not None else None) or {})
    groups = []
    for layer in recipe.layers:
        part = layer.part_id
        mask = land if layer.cls == "land" else ocean & ~shadow
        classes = result.classes[layer.cls]
        names = [table.get(part, k).lego.name for k in layer.colors]
        entries: List[Tuple[str, Meaning]] = list(zip(
            layer.colors, _scale_meanings(layer, classes, mask, result.fields.get(layer.cls), names)))
        if layer.no_data is not None and bool((mask & (classes == NO_DATA_CLASS)).any()):
            entries.append((layer.no_data.color,
                            Meaning("no_data", labels.get(layer.cls) or NO_DATA_LABEL)))
        for i, o in enumerate(layer.overrides):
            if bool((mask & (classes == override_class(i))).any()):
                entries.append((o.color, Meaning("override", o.name)))
        if layer.cls == "ocean" and bool(shadow.any()):
            entries.append((recipe.shadow.color, Meaning("shadow", SHADOW_LABEL)))
        order: List[str] = []
        meanings: Dict[str, List[Meaning]] = {}
        for color, m in entries:
            if color not in meanings:
                order.append(color)
                meanings[color] = []
            meanings[color].append(m)
        swatches = []
        for color in order:
            c = table.get(part, color)
            swatches.append(Swatch(layer=layer.cls, part_id=part, color=color,
                                   rgb=tuple(int(v) for v in c.rgb), lego_name=c.lego.name,
                                   meanings=tuple(meanings[color])))
        groups.append(LegendGroup(layer=layer.cls, heading=_heading(layer), swatches=tuple(swatches)))
    return Legend(groups=tuple(groups))

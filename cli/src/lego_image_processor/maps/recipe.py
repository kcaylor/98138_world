"""Recipe files (TOML, format "1"): a land layer and an ocean layer (FR-001, FR-002).

Every rule is checked before any work, and an error names the key path and the rule
(contracts/recipe-format.md). Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import hashlib
import math
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from ..datasets.registry import DatasetEntry, load_registry
from ..kit.part_colors import load_part_colors
from ..layout.arrangement import Arrangement, ArrangementError, parse_arrangement, valid_values
from .margin import DEFAULT_MARGIN_COLOR, MarginTreatment, color_rule, ring_rule

FORMAT = "1"
DEFAULT_SEED = 31203
RECIPES_DIR = Path(__file__).resolve().parent / "recipes"
PART_FOR_CLASS = {"land": "6141", "ocean": "98138"}
ROLES = ("data", "background")
TRANSFORMS = ("none", "negate", "log10")
NO_DATA_RULES = ("unobserved", "share")
SAMPLINGS = ("mean", "bilinear")  # feature 013
_BOUND_KEYS = ("lat_min", "lat_max", "lon_min", "lon_max")
_OVERRIDE_KEYS = {"name", "color", "exclude", "dataset", "variable", "min_value", "unobserved_lat",
                  *_BOUND_KEYS}
_LEGEND_KEYS = {"units", "factor"}
METHODS = ("bins", "quantile", "rank", "rank-to-supply", "categorical")
RANK_METHODS = ("quantile", "rank", "rank-to-supply")
DATA_TEXTURES = ("none", "blend")
BACKGROUND_TEXTURES = ("none", "mix", "halo")
SHADOW_DIRECTIONS = ("east",)
DEFAULT_SHADOW_COLOR = "lego_earth_blue"
HALO_DEFAULTS = {"inner": 1.5, "outer": 3.0, "spacing": 2.0}
LOCAL_FORMATS = ("netcdf3", "npy", "dods")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")

_TOP_KEYS = {"format", "id", "title", "description", "seed", "arrangement", "land", "ocean", "shadow",
             "template", "margin"}  # feature 016: template, margin
_MARGIN_KEYS = {"color", "ring"}  # feature 016 (labels are feature 017)
_SHADOW_KEYS = {"enabled", "color", "direction"}
_DATA_KEYS = {"role", "colors", "dataset", "local", "variable", "transform", "classification", "texture",
              "no_data", "sampling", "override", "legend"}
_NO_DATA_KEYS = {"unobserved": {"color", "rule", "min_lat", "value", "sparse_lat", "min_steps"},
                 "share": {"color", "rule", "min_lat", "value", "min_share"}}
_BACKGROUND_KEYS = {"role", "colors", "weights", "texture"}
_CLASS_KEYS = {"bins": {"method", "bounds"}, "quantile": {"method"}, "rank": {"method", "shares"},
               "rank-to-supply": {"method"}, "categorical": {"method", "categories"}}
_TEXTURE_KEYS = {"none": {"kind"}, "blend": {"kind", "width"}, "mix": {"kind", "cluster"},
                 "halo": {"kind", "inner", "outer", "spacing"}}
_LOCAL_REQUIRED = ("path", "format", "sha256", "variable", "citation", "license")
_LOCAL_OPTIONAL = {"title", "lat", "lon", "fill", "split_at", "missing_is_land", "units"}


class RecipeError(ValueError):
    """A recipe breaks a rule. ``path`` is the key path (e.g. ``ocean.classification.bounds``)."""

    def __init__(self, path: str, rule: str, file: Optional[Path] = None):
        self.path, self.rule, self.file = path, rule, file
        super().__init__(f"{path}: {rule}")


@dataclass(frozen=True)
class Classification:
    method: str
    bounds: Tuple[float, ...] = ()
    shares: Tuple[float, ...] = ()
    categories: Dict[str, str] = field(default_factory=dict)

    @property
    def ordered(self) -> bool:
        return self.method != "categorical"


@dataclass(frozen=True)
class Texture:
    kind: str = "none"
    width: float = 0.0
    cluster: float = 0.0
    inner: float = 0.0     # halo: cells within this distance of land (studs) take the ring color
    outer: float = 0.0     # halo: cells up to this distance fade on an even Poisson-disk subset
    spacing: float = 0.0   # halo: minimum distance between ring-colored cells in the fade band


@dataclass(frozen=True)
class Shadow:
    """A one-stud drop shadow: ocean cells whose western neighbour is land (amendment FR-026)."""

    enabled: bool = True
    color: str = DEFAULT_SHADOW_COLOR
    direction: str = "east"

    def provenance(self, cells: int) -> Dict[str, Any]:
        return {"enabled": self.enabled, "color": self.color, "direction": self.direction,
                "cells": int(cells)}


@dataclass(frozen=True)
class NoData:
    """A data layer's no-data rule (feature 012, contracts/recipe-and-datasets.md).

    ``value``: class source pixels with no value take it (None: left missing). ``rule``
    ``"unobserved"``: cells with no valid source value poleward of ``min_lat``, plus cells poleward
    of ``sparse_lat`` whose best source pixel has fewer than ``min_steps`` valid steps; ``"share"``:
    cells where the share of class source pixels without a value and poleward of ``min_lat``
    exceeds ``min_share``. Those cells take ``color``."""

    color: str
    rule: str
    min_lat: float
    value: Optional[float] = None
    min_share: Optional[float] = None
    sparse_lat: Optional[float] = None
    min_steps: Optional[int] = None

    def provenance(self, cells: int) -> Dict[str, Any]:
        out: Dict[str, Any] = {"rule": self.rule, "color": self.color, "min_lat": self.min_lat}
        for k in ("min_share", "sparse_lat", "min_steps", "value"):
            v = getattr(self, k)
            if v is not None:
                out[k] = v
        out["cells"] = int(cells)
        return out


@dataclass(frozen=True)
class Region:
    """Cell-centre bounds (degrees, strict); None = unbounded (feature 013)."""

    lat_min: Optional[float] = None
    lat_max: Optional[float] = None
    lon_min: Optional[float] = None
    lon_max: Optional[float] = None

    def to_dict(self) -> Dict[str, float]:
        return {k: getattr(self, k) for k in _BOUND_KEYS if getattr(self, k) is not None}


@dataclass(frozen=True)
class Override:
    """A ``[[<layer>.override]]`` rule (feature 013, contracts/recipe-and-datasets.md): cells inside
    ``region`` (minus ``exclude``), or cells whose value of ``dataset``/``variable`` is at least
    ``min_value`` (plus cells with no value poleward of ``unobserved_lat``), take ``color``."""

    name: str
    color: str
    region: Optional[Region] = None
    exclude: Tuple[Region, ...] = ()
    dataset: Optional[DatasetEntry] = None
    variable: str = ""
    min_value: Optional[float] = None
    unobserved_lat: Optional[float] = None

    @property
    def kind(self) -> str:
        return "dataset" if self.dataset is not None else "region"

    def provenance(self, cells: int) -> Dict[str, Any]:
        out: Dict[str, Any] = {"name": self.name, "kind": self.kind, "color": self.color}
        if self.region is not None:
            out["region"] = self.region.to_dict()
            if self.exclude:
                out["exclude"] = [r.to_dict() for r in self.exclude]
        else:
            out.update(dataset=self.dataset.id, variable=self.variable, min_value=self.min_value)
            if self.unobserved_lat is not None:
                out["unobserved_lat"] = self.unobserved_lat
        out["cells"] = int(cells)
        return out


@dataclass(frozen=True)
class Legend:
    """Secondary legend units for a data layer's bins (feature 013): value x ``factor``."""

    units: str
    factor: float

    def to_dict(self) -> Dict[str, Any]:
        return {"units": self.units, "factor": self.factor}


@dataclass(frozen=True)
class Layer:
    cls: str
    role: str
    colors: Tuple[str, ...]
    weights: Tuple[float, ...] = ()
    dataset: Optional[DatasetEntry] = None
    variable: str = ""
    transform: str = "none"
    classification: Optional[Classification] = None
    texture: Texture = Texture()
    no_data: Optional[NoData] = None  # feature 012
    sampling: str = "mean"            # feature 013
    overrides: Tuple[Override, ...] = ()  # feature 013
    legend: Optional[Legend] = None   # feature 013

    @property
    def part_id(self) -> str:
        return PART_FOR_CLASS[self.cls]


@dataclass(frozen=True)
class Recipe:
    format: str
    id: str
    title: str
    land: Layer
    ocean: Layer
    sha256: str
    description: str = ""
    seed: int = DEFAULT_SEED
    path: Optional[Path] = None
    shadow: Shadow = Shadow()
    arrangement: Optional[Arrangement] = None  # feature 009: the recipe's default; None = key absent
    template: Optional[str] = None  # feature 016: a known template id; None = key absent (the kit)
    margin: Optional[MarginTreatment] = None  # feature 016: the [margin] table; None = table absent

    @property
    def layers(self) -> Tuple[Layer, Layer]:
        return (self.land, self.ocean)

    def datasets(self) -> Tuple[DatasetEntry, ...]:
        """Every dataset the recipe reads, including a ``land_from`` mask dataset (feature 012)."""
        out = []
        for layer in self.layers:
            entries = [layer.dataset] if layer.dataset is not None else []
            entries += [o.dataset for o in layer.overrides if o.dataset is not None]  # feature 013
            for e in entries:
                if e in out:
                    continue
                out.append(e)
                mask = e.mask_dataset_id
                if mask is not None:
                    entry = load_registry().get(mask)
                    if entry not in out:
                        out.append(entry)
        return tuple(out)


def _check_keys(table: Dict[str, Any], allowed, where: str) -> None:
    for k in table:
        if k not in allowed:
            raise RecipeError(f"{where}.{k}" if where else k,
                              f"unknown key (allowed: {', '.join(sorted(allowed))})")


def _number(v: Any, path: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise RecipeError(path, "must be a number")
    return float(v)


def _string(t: Dict[str, Any], key: str, where: str, required: bool = True) -> str:
    v = t.get(key)
    if v is None:
        if required:
            raise RecipeError(f"{where}.{key}" if where else key, "is required")
        return ""
    if not isinstance(v, str) or (required and not v.strip()):
        raise RecipeError(f"{where}.{key}" if where else key, "must be a non-empty string")
    return v


def _colors(layer: Dict[str, Any], cls: str, method: Optional[str]) -> Tuple[str, ...]:
    raw = layer.get("colors")
    where = f"{cls}.colors"
    if not isinstance(raw, list) or not raw:
        raise RecipeError(where, "must be a non-empty list of color keys")
    table = load_part_colors()
    part = PART_FOR_CLASS[cls]
    for i, key in enumerate(raw):
        if not isinstance(key, str):
            raise RecipeError(f"{where}[{i}]", "must be a color key string")
        c = table.get(part, key)
        if c is None:
            other = table.any_part(key)
            if other is None:
                raise RecipeError(f"{where}[{i}]", f"unknown color {key!r} (not in kit_colors.json or "
                                                   "part_colors.json)")
            raise RecipeError(f"{where}[{i}]", f"color {key!r} is not available for part {part} "
                                               f"(the {cls} part); see `kit part-colors --part {part}`")
        if method == "rank-to-supply" and not c.in_kit:
            raise RecipeError(f"{where}[{i}]", f"rank-to-supply needs kit colors; {key!r} is not in kit "
                                               f"31203 for part {part}")
    if len(set(raw)) != len(raw):
        raise RecipeError(where, "colors must not repeat")
    return tuple(raw)


def _classification(t: Any, n: int, colors: Tuple[str, ...], cls: str,
                    transform: str = "none") -> Classification:
    where = f"{cls}.classification"
    if not isinstance(t, dict):
        raise RecipeError(where, "is required for a data layer (a table with a method)")
    method = t.get("method")
    if method not in METHODS:
        raise RecipeError(f"{where}.method", f"must be one of {', '.join(METHODS)}")
    _check_keys(t, _CLASS_KEYS[method], where)
    if method == "bins":
        b = t.get("bounds")
        if not isinstance(b, list):
            raise RecipeError(f"{where}.bounds", "bins needs bounds (a list of numbers)")
        bounds = tuple(_number(v, f"{where}.bounds[{i}]") for i, v in enumerate(b))
        if len(bounds) != n + 1:
            raise RecipeError(f"{where}.bounds", f"needs {n + 1} bounds for {n} colors, found {len(bounds)}")
        if any(b2 <= b1 for b1, b2 in zip(bounds, bounds[1:])):
            raise RecipeError(f"{where}.bounds", "must be strictly increasing")
        if transform == "log10":
            # bounds stay in the variable's units in the recipe and are compared on log10 (012)
            for i, v in enumerate(bounds):
                if v <= 0:
                    raise RecipeError(f"{where}.bounds[{i}]", "must be > 0 with transform = \"log10\" "
                                                              "(bounds are in the variable's units)")
            bounds = tuple(math.log10(v) for v in bounds)
        return Classification(method=method, bounds=bounds)
    if method == "rank":
        s = t.get("shares")
        if not isinstance(s, list):
            raise RecipeError(f"{where}.shares", "rank needs shares (a list of positive numbers)")
        shares = tuple(_number(v, f"{where}.shares[{i}]") for i, v in enumerate(s))
        if len(shares) != n:
            raise RecipeError(f"{where}.shares", f"needs {n} shares for {n} colors, found {len(shares)}")
        for i, v in enumerate(shares):
            if v <= 0:
                raise RecipeError(f"{where}.shares[{i}]", "must be > 0")
        return Classification(method=method, shares=shares)
    if method == "categorical":
        cats = t.get("categories")
        if not isinstance(cats, dict) or not cats:
            raise RecipeError(f"{where}.categories", "categorical needs a categories table "
                                                     "(source category = color key)")
        for k, v in cats.items():
            if v not in colors:
                raise RecipeError(f"{where}.categories.{k}", f"{v!r} is not one of the layer's colors")
        return Classification(method=method, categories={str(k): v for k, v in cats.items()})
    return Classification(method=method)


def _texture(t: Any, cls: str, role: str, method: Optional[str], ncolors: int) -> Texture:
    where = f"{cls}.texture"
    if t is None:
        if role == "background" and ncolors > 1:
            raise RecipeError(where, "a background with more than one color needs kind = \"mix\" or "
                                     "\"halo\"")
        return Texture()
    if not isinstance(t, dict):
        raise RecipeError(where, "must be a table")
    kind = t.get("kind", "none")
    allowed = DATA_TEXTURES if role == "data" else BACKGROUND_TEXTURES
    if kind not in allowed:
        raise RecipeError(f"{where}.kind", f"a {role} layer's texture must be one of {', '.join(allowed)}")
    _check_keys(t, _TEXTURE_KEYS[kind], where)
    if kind == "blend":
        if method == "categorical":
            raise RecipeError(f"{where}.kind", "blend needs an ordered classification")
        if "width" not in t:
            raise RecipeError(f"{where}.width", "blend needs width (a fraction of a class, 0-0.5)")
        w = _number(t["width"], f"{where}.width")
        if not 0 < w <= 0.5:
            raise RecipeError(f"{where}.width", "must be > 0 and <= 0.5")
        return Texture(kind="blend", width=w)
    if kind == "halo":
        if cls != "ocean":
            raise RecipeError(f"{where}.kind", "halo is a coastal texture for the ocean background only")
        if ncolors != 2:
            raise RecipeError(f"{cls}.colors", "halo needs two colors: the offshore base, then the coast "
                                               "ring")
        v = {k: _number(t.get(k, d), f"{where}.{k}") for k, d in HALO_DEFAULTS.items()}
        if v["inner"] <= 0:
            raise RecipeError(f"{where}.inner", "must be > 0 (studs)")
        if v["outer"] < v["inner"]:
            raise RecipeError(f"{where}.outer", "must be >= inner")
        if v["spacing"] <= 0:
            raise RecipeError(f"{where}.spacing", "must be > 0 (studs)")
        return Texture(kind="halo", **v)
    if kind == "mix":
        c = _number(t.get("cluster", 0.0), f"{where}.cluster")
        if c < 0:
            raise RecipeError(f"{where}.cluster", "must be >= 0")
        return Texture(kind="mix", cluster=c)
    if role == "background" and ncolors > 1:
        raise RecipeError(where, "a background with more than one color needs kind = \"mix\" or \"halo\"")
    return Texture()


def _local_entry(t: Any, cls: str, base_dir: Path) -> DatasetEntry:
    where = f"{cls}.local"
    if not isinstance(t, dict):
        raise RecipeError(where, "must be a table")
    _check_keys(t, set(_LOCAL_REQUIRED) | _LOCAL_OPTIONAL, where)
    vals = {k: _string(t, k, where) for k in _LOCAL_REQUIRED}
    if vals["format"] not in LOCAL_FORMATS:
        raise RecipeError(f"{where}.format", f"must be one of {', '.join(LOCAL_FORMATS)}")
    if not re.match(r"^[0-9a-f]{64}$", vals["sha256"]):
        raise RecipeError(f"{where}.sha256", "must be 64 lowercase hex characters")
    grid: Dict[str, Any] = {}
    if vals["format"] == "npy":
        for key in ("lat", "lon"):
            v = t.get(key)
            if not (isinstance(v, list) and len(v) == 2):
                raise RecipeError(f"{where}.{key}", "npy files need [min, max] (cell edges, rows south "
                                                    "to north)")
            lo, hi = (_number(x, f"{where}.{key}") for x in v)
            if lo >= hi:
                raise RecipeError(f"{where}.{key}", "min must be below max")
            grid[key] = [lo, hi]
    if "fill" in t:
        grid["fill"] = _number(t["fill"], f"{where}.fill")
    rule: Dict[str, Any] = {}
    if "split_at" in t:
        rule["split_at"] = _number(t["split_at"], f"{where}.split_at")
    if t.get("missing_is_land"):
        if rule:
            raise RecipeError(f"{where}.missing_is_land", "use either split_at or missing_is_land")
        rule["missing_is_land"] = True
    path = Path(vals["path"])
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    stem = re.sub(r"[^a-z0-9.-]+", "-", path.stem.lower()).strip("-") or "file"
    return DatasetEntry(
        id=f"local-{stem}"[:64], version="local", kind="local",
        title=_string(t, "title", where, required=False) or path.name, publisher="(local file)",
        format=vals["format"], license=vals["license"], citation=vals["citation"],
        variables={vals["variable"]: {"units": str(t.get("units", ""))}}, class_rule=rule,
        sha256=vals["sha256"], filename=path.name, grid=grid, path=path,
    )


def _layer(t: Any, cls: str, base_dir: Path) -> Layer:
    if not isinstance(t, dict):
        raise RecipeError(cls, "layer table is required")
    role = t.get("role")
    if role not in ROLES:
        raise RecipeError(f"{cls}.role", f"must be one of {', '.join(ROLES)}")
    if role == "background":
        for k in ("dataset", "local", "variable", "transform", "classification", "no_data", "sampling",
                  "override", "legend"):
            if k in t:
                raise RecipeError(f"{cls}.{k}", "a background layer takes colors, weights and texture only")
        _check_keys(t, _BACKGROUND_KEYS, cls)
        colors = _colors(t, cls, None)
        tex = t.get("texture")
        if isinstance(tex, dict) and tex.get("kind") == "halo":
            texture = _texture(tex, cls, role, None, len(colors))
            if "weights" in t:
                raise RecipeError(f"{cls}.weights", "halo sets colors by distance from land; weights are "
                                                    "for mix")
            return Layer(cls=cls, role=role, colors=colors, weights=(), texture=texture)
        w = t.get("weights", [1] * len(colors))
        if not isinstance(w, list) or len(w) != len(colors):
            raise RecipeError(f"{cls}.weights", f"needs one weight per color ({len(colors)})")
        weights = tuple(_number(v, f"{cls}.weights[{i}]") for i, v in enumerate(w))
        for i, v in enumerate(weights):
            if v <= 0:
                raise RecipeError(f"{cls}.weights[{i}]", "must be > 0")
        texture = _texture(t.get("texture"), cls, role, None, len(colors))
        return Layer(cls=cls, role=role, colors=colors, weights=weights, texture=texture)

    if "weights" in t:
        raise RecipeError(f"{cls}.weights", "a data layer's colors come from its classification; "
                                            "weights are for background layers")
    _check_keys(t, _DATA_KEYS, cls)
    if "dataset" in t and "local" in t:
        raise RecipeError(f"{cls}.local", "use either dataset (a registry id) or a local table, not both")
    if "local" in t:
        if "variable" in t:
            raise RecipeError(f"{cls}.variable", "a local file names its variable inside the local table")
        entry = _local_entry(t["local"], cls, base_dir)
        variable = next(iter(entry.variables))
    else:
        did = _string(t, "dataset", cls)
        try:
            entry = load_registry().get(did)
        except KeyError:
            ids = ", ".join(e.id for e in load_registry().entries)
            raise RecipeError(f"{cls}.dataset", f"unknown dataset {did!r} (registry: {ids})")
        variable = _string(t, "variable", cls)
        if variable not in entry.variables:
            raise RecipeError(f"{cls}.variable", f"dataset {did} has no variable {variable!r} "
                                                 f"(has: {', '.join(entry.variables)})")
    transform = t.get("transform", "none")
    if transform not in TRANSFORMS:
        raise RecipeError(f"{cls}.transform", f"must be one of {', '.join(TRANSFORMS)}")
    ctab = t.get("classification")
    method = ctab.get("method") if isinstance(ctab, dict) else None
    if not isinstance(ctab, dict):
        raise RecipeError(f"{cls}.classification", "is required for a data layer (a table with a method)")
    colors = _colors(t, cls, method)
    classification = _classification(ctab, len(colors), colors, cls, transform)
    if entry.format == "kit-design" and classification.method != "categorical":
        raise RecipeError(f"{cls}.classification.method", f"dataset {entry.id} is categorical; use "
                                                          "method = \"categorical\"")
    texture = _texture(t.get("texture"), cls, role, classification.method, len(colors))
    no_data = _no_data(t.get("no_data"), cls, entry, variable, transform)
    sampling = t.get("sampling", "mean")
    if sampling not in SAMPLINGS:
        raise RecipeError(f"{cls}.sampling", f"must be one of {', '.join(SAMPLINGS)}")
    if sampling == "bilinear" and classification.method == "categorical":
        raise RecipeError(f"{cls}.sampling", "bilinear needs ordered (not categorical) data")
    overrides = _overrides(t.get("override"), cls)
    legend = _legend(t.get("legend"), cls)
    return Layer(cls=cls, role=role, colors=colors, dataset=entry, variable=variable,
                 transform=transform, classification=classification, texture=texture,
                 no_data=no_data, sampling=sampling, overrides=overrides, legend=legend)


def _region(t: Any, where: str, required: bool = True) -> Region:
    if not isinstance(t, dict):
        raise RecipeError(where, "must be a table of lat_min, lat_max, lon_min, lon_max")
    vals: Dict[str, float] = {}
    for k in _BOUND_KEYS:
        if k in t:
            v = _number(t[k], f"{where}.{k}")
            lim = 90.0 if k.startswith("lat") else 180.0
            if not -lim <= v <= lim:
                raise RecipeError(f"{where}.{k}", f"must be between {-lim:g} and {lim:g}")
            vals[k] = v
    if required and not vals:
        raise RecipeError(where, "needs at least one of lat_min, lat_max, lon_min, lon_max")
    for lo, hi in (("lat_min", "lat_max"), ("lon_min", "lon_max")):
        if lo in vals and hi in vals and vals[lo] >= vals[hi]:
            raise RecipeError(f"{where}.{lo}", f"must be below {hi}")
    return Region(**vals)


def _overrides(raw: Any, cls: str) -> Tuple[Override, ...]:
    """The optional ``[[<layer>.override]]`` tables of a data layer (feature 013)."""
    if raw is None:
        return ()
    where = f"{cls}.override"
    if not isinstance(raw, list) or not raw:
        raise RecipeError(where, "must be an array of tables ([[...override]])")
    out = []
    names = set()
    part = PART_FOR_CLASS[cls]
    for i, t in enumerate(raw):
        w = f"{where}[{i}]"
        if not isinstance(t, dict):
            raise RecipeError(w, "must be a table")
        _check_keys(t, _OVERRIDE_KEYS, w)
        name = _string(t, "name", w)
        if name in names:
            raise RecipeError(f"{w}.name", f"duplicate override name {name!r}")
        names.add(name)
        color = t.get("color")
        if not isinstance(color, str):
            raise RecipeError(f"{w}.color", "is required (a color key string)")
        if load_part_colors().get(part, color) is None:
            raise RecipeError(f"{w}.color", f"{color!r} is not a color of the {cls} part (part {part}); "
                                            f"see `kit part-colors --part {part}`")
        has_bounds = any(k in t for k in _BOUND_KEYS)
        has_data = any(k in t for k in ("dataset", "variable", "min_value", "unobserved_lat"))
        if has_bounds == has_data:
            raise RecipeError(w, "give either region bounds (lat_min, lat_max, lon_min, lon_max) or a "
                                 "dataset rule (dataset, variable, min_value), not both")
        if has_bounds:
            region = _region(t, w)
            ex = t.get("exclude", [])
            if not isinstance(ex, list):
                raise RecipeError(f"{w}.exclude", "must be a list of tables")
            exclude = tuple(_region(e, f"{w}.exclude[{j}]") for j, e in enumerate(ex))
            out.append(Override(name=name, color=color, region=region, exclude=exclude))
            continue
        if "exclude" in t:
            raise RecipeError(f"{w}.exclude", "is for region overrides only")
        did = _string(t, "dataset", w)
        try:
            entry = load_registry().get(did)
        except KeyError:
            ids = ", ".join(e.id for e in load_registry().entries)
            raise RecipeError(f"{w}.dataset", f"unknown dataset {did!r} (registry: {ids})")
        if entry.format == "kit-design":
            raise RecipeError(f"{w}.dataset", f"dataset {did} is categorical; an override needs values")
        variable = _string(t, "variable", w)
        if variable not in entry.variables:
            raise RecipeError(f"{w}.variable", f"dataset {did} has no variable {variable!r} "
                                               f"(has: {', '.join(entry.variables)})")
        if "min_value" not in t:
            raise RecipeError(f"{w}.min_value", "is required for a dataset override")
        min_value = _number(t["min_value"], f"{w}.min_value")
        ulat = None
        if "unobserved_lat" in t:
            ulat = _number(t["unobserved_lat"], f"{w}.unobserved_lat")
            if not 0 <= ulat <= 90:
                raise RecipeError(f"{w}.unobserved_lat", "must be between 0 and 90")
        out.append(Override(name=name, color=color, dataset=entry, variable=variable,
                            min_value=min_value, unobserved_lat=ulat))
    return tuple(out)


def _legend(t: Any, cls: str) -> Optional[Legend]:
    """The optional ``[<layer>.legend]`` table (feature 013)."""
    if t is None:
        return None
    where = f"{cls}.legend"
    if not isinstance(t, dict):
        raise RecipeError(where, "must be a table")
    _check_keys(t, _LEGEND_KEYS, where)
    units = _string(t, "units", where)
    if "factor" not in t:
        raise RecipeError(f"{where}.factor", "is required (a number > 0)")
    factor = _number(t["factor"], f"{where}.factor")
    if factor <= 0:
        raise RecipeError(f"{where}.factor", "must be > 0")
    return Legend(units=units, factor=factor)


def _no_data(t: Any, cls: str, entry: DatasetEntry, variable: str,
             transform: str = "none") -> Optional[NoData]:
    """The optional ``[<layer>.no_data]`` table of a data layer (feature 012)."""
    if t is None:
        return None
    where = f"{cls}.no_data"
    if not isinstance(t, dict):
        raise RecipeError(where, "must be a table")
    rule = t.get("rule")
    if rule not in NO_DATA_RULES:
        raise RecipeError(f"{where}.rule", f"must be one of {', '.join(NO_DATA_RULES)}")
    _check_keys(t, _NO_DATA_KEYS[rule], where)
    color = t.get("color")
    if color is None:
        raise RecipeError(f"{where}.color", "is required (the color of no-data cells)")
    if not isinstance(color, str):
        raise RecipeError(f"{where}.color", "must be a color key string")
    part = PART_FOR_CLASS[cls]
    if load_part_colors().get(part, color) is None:
        raise RecipeError(f"{where}.color", f"{color!r} is not a color of the {cls} part (part {part}); "
                                            f"see `kit part-colors --part {part}`")
    if "min_lat" not in t:
        raise RecipeError(f"{where}.min_lat", "is required (degrees of absolute latitude, 0-90)")
    min_lat = _number(t["min_lat"], f"{where}.min_lat")
    if not 0 <= min_lat <= 90:
        raise RecipeError(f"{where}.min_lat", "must be between 0 and 90")
    value = None
    if "value" in t:
        value = _number(t["value"], f"{where}.value")
        if transform == "log10" and value <= 0:
            raise RecipeError(f"{where}.value", "must be > 0 with transform = \"log10\" (it is in the "
                                                "variable's units and goes through the transform)")
        if entry.kind == "packaged" or not entry.splits_land:
            raise RecipeError(f"{where}.value", f"dataset {entry.id} does not tell land from ocean pixels "
                                                "(class_rule), so missing pixels of the layer's class are "
                                                "unknown")
    if rule == "share":
        if "min_share" not in t:
            raise RecipeError(f"{where}.min_share", "is required for rule = \"share\" (0 <= x < 1)")
        share = _number(t["min_share"], f"{where}.min_share")
        if not 0 <= share < 1:
            raise RecipeError(f"{where}.min_share", "must be >= 0 and < 1")
        return NoData(color=color, rule=rule, min_lat=min_lat, value=value, min_share=share)
    sparse_lat = min_steps = None
    if ("sparse_lat" in t) != ("min_steps" in t):
        missing = "min_steps" if "sparse_lat" in t else "sparse_lat"
        raise RecipeError(f"{where}.{missing}", "sparse_lat and min_steps go together")
    if "sparse_lat" in t:
        sparse_lat = _number(t["sparse_lat"], f"{where}.sparse_lat")
        if not min_lat <= sparse_lat <= 90:
            raise RecipeError(f"{where}.sparse_lat", "must be between min_lat and 90")
        ms = t["min_steps"]
        if isinstance(ms, bool) or not isinstance(ms, int) or ms < 1:
            raise RecipeError(f"{where}.min_steps", "must be an integer >= 1")
        if (entry.variables.get(variable) or {}).get("reduce") != "climatology-mean":
            raise RecipeError(f"{where}.min_steps", f"needs a dataset variable with reduce = "
                                                    f"\"climatology-mean\" ({entry.id} {variable} has none)")
        min_steps = ms
    return NoData(color=color, rule=rule, min_lat=min_lat, value=value, sparse_lat=sparse_lat,
                  min_steps=min_steps)


def parse_recipe(text: Union[str, bytes], *, path: Optional[Path] = None,
                 base_dir: Optional[Path] = None) -> Recipe:
    """Parse and validate recipe text. ``base_dir`` resolves relative local data paths."""
    raw = text.encode("utf-8") if isinstance(text, str) else bytes(text)
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise RecipeError("(file)", f"not valid TOML: {exc}", file=path)
    try:
        return _parse(data, raw, path, base_dir or (path.parent if path else Path.cwd()))
    except RecipeError as exc:
        exc.file = path
        raise


def _parse(data: Dict[str, Any], raw: bytes, path: Optional[Path], base_dir: Path) -> Recipe:
    _check_keys(data, _TOP_KEYS, "")
    fmt = data.get("format")
    if fmt != FORMAT:
        raise RecipeError("format", f"unsupported recipe format {fmt!r}; this tool reads format \"{FORMAT}\"")
    rid = _string(data, "id", "")
    if not _ID_RE.match(rid):
        raise RecipeError("id", f"must match {_ID_RE.pattern} (lowercase letters, digits, hyphens)")
    title = _string(data, "title", "")
    description = _string(data, "description", "", required=False)
    seed = data.get("seed", DEFAULT_SEED)
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise RecipeError("seed", "must be a non-negative integer")
    for cls in ("land", "ocean"):
        if cls not in data:
            raise RecipeError(cls, "layer table is required (a map has a land and an ocean layer)")
    land = _layer(data["land"], "land", base_dir)
    ocean = _layer(data["ocean"], "ocean", base_dir)
    shadow = _shadow(data.get("shadow"))
    arrangement = _arrangement(data.get("arrangement"))
    template = _template(data.get("template"))
    margin = _margin(data.get("margin"))
    return Recipe(format=fmt, id=rid, title=title, description=description, seed=seed, land=land,
                  ocean=ocean, sha256=hashlib.sha256(raw).hexdigest(), path=path, shadow=shadow,
                  arrangement=arrangement, template=template, margin=margin)


def _template(v: Any) -> Optional[str]:
    """The optional top-level ``template`` (feature 016, FR-006): a known template id. A template
    the owner has not confirmed parses but does not build (FR-004)."""
    if v is None:
        return None
    from ..templates import confirmed_text, template_ids

    if not isinstance(v, str) or not v:
        raise RecipeError("template", f"must be a template id string; confirmed templates: {confirmed_text()}")
    if v not in template_ids():
        raise RecipeError("template", f"unknown template {v!r}; confirmed templates: {confirmed_text()}")
    return v


def _margin(t: Any) -> Optional[MarginTreatment]:
    """The optional ``[margin]`` table (feature 016, research R12): ``color`` (a 3070b color, default
    Black) and an optional ``ring`` color that must differ from it. Used only on non-kit templates."""
    if t is None:
        return None
    if not isinstance(t, dict):
        raise RecipeError("margin", "must be a table with color and ring (1x1 square tile colors, part 3070b)")
    _check_keys(t, _MARGIN_KEYS, "margin")
    color = t.get("color", DEFAULT_MARGIN_COLOR)
    rule = color_rule(color)
    if rule is not None:
        raise RecipeError("margin.color", rule)
    ring = t.get("ring")
    if ring is not None:
        rule = color_rule(ring)
        if rule is not None:
            raise RecipeError("margin.ring", rule)
        if ring == color:
            raise RecipeError("margin.ring", ring_rule(ring, color))
    return MarginTreatment(color=color, ring=ring)


def _arrangement(v: Any) -> Optional[Arrangement]:
    """The optional top-level ``arrangement`` (feature 009): how the frames are hung by default."""
    if v is None:
        return None
    rule = f"must be one of {', '.join(valid_values())}"
    if not isinstance(v, str):
        raise RecipeError("arrangement", rule)
    try:
        return parse_arrangement(v)
    except ArrangementError:
        raise RecipeError("arrangement", rule)


def _shadow(t: Any) -> Shadow:
    """The top-level ``[shadow]`` table; absent means on, Earth Blue, cast east."""
    if t is None:
        return Shadow()
    if not isinstance(t, dict):
        raise RecipeError("shadow", "must be a table")
    _check_keys(t, _SHADOW_KEYS, "shadow")
    enabled = t.get("enabled", True)
    if not isinstance(enabled, bool):
        raise RecipeError("shadow.enabled", "must be true or false")
    direction = t.get("direction", "east")
    if direction not in SHADOW_DIRECTIONS:
        raise RecipeError("shadow.direction", f"must be one of {', '.join(SHADOW_DIRECTIONS)}")
    color = t.get("color", DEFAULT_SHADOW_COLOR)
    if not isinstance(color, str):
        raise RecipeError("shadow.color", "must be a color key string")
    if load_part_colors().get(PART_FOR_CLASS["ocean"], color) is None:
        raise RecipeError("shadow.color", f"{color!r} is not a color of the ocean tile (part "
                                          f"{PART_FOR_CLASS['ocean']}); see `kit part-colors --part 98138`")
    return Shadow(enabled=enabled, color=color, direction=direction)


def bundled_recipes(directory: Optional[Path] = None) -> Dict[str, Path]:
    """Bundled recipe ids and files; duplicate ids are an error (spec edge cases)."""
    directory = Path(directory) if directory else RECIPES_DIR
    out: Dict[str, Path] = {}
    for p in sorted(directory.glob("*.toml")):
        try:
            rid = tomllib.loads(p.read_text(encoding="utf-8")).get("id")
        except tomllib.TOMLDecodeError as exc:
            raise RecipeError("(file)", f"{p.name} is not valid TOML: {exc}", file=p)
        if rid in out:
            raise RecipeError("id", f"duplicate bundled recipe id {rid!r} ({out[rid].name}, {p.name})", file=p)
        out[rid] = p
    return out


def load_recipe(ref: Union[str, Path]) -> Recipe:
    """Load a recipe from a file path, or a bundled recipe by id."""
    p = Path(ref)
    if p.is_file():
        return parse_recipe(p.read_bytes(), path=p.resolve())
    bundled = bundled_recipes()
    if str(ref) in bundled:
        bp = bundled[str(ref)]
        return parse_recipe(bp.read_bytes(), path=bp)
    raise RecipeError("(file)", f"no recipe file {str(ref)!r} and no bundled recipe with that id "
                                f"(bundled: {', '.join(bundled)})")

"""Recipe files (TOML, format "1"): a land layer and an ocean layer (FR-001, FR-002).

Every rule is checked before any work, and an error names the key path and the rule
(contracts/recipe-format.md). Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import hashlib
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from ..datasets.registry import DatasetEntry, load_registry
from ..kit.part_colors import load_part_colors

FORMAT = "1"
DEFAULT_SEED = 31203
RECIPES_DIR = Path(__file__).resolve().parent / "recipes"
PART_FOR_CLASS = {"land": "6141", "ocean": "98138"}
ROLES = ("data", "background")
TRANSFORMS = ("none", "negate")
METHODS = ("bins", "quantile", "rank", "rank-to-supply", "categorical")
RANK_METHODS = ("quantile", "rank", "rank-to-supply")
DATA_TEXTURES = ("none", "blend")
BACKGROUND_TEXTURES = ("none", "mix", "halo")
SHADOW_DIRECTIONS = ("east",)
DEFAULT_SHADOW_COLOR = "lego_earth_blue"
HALO_DEFAULTS = {"inner": 1.5, "outer": 3.0, "spacing": 2.0}
LOCAL_FORMATS = ("netcdf3", "npy", "dods")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")

_TOP_KEYS = {"format", "id", "title", "description", "seed", "land", "ocean", "shadow"}
_SHADOW_KEYS = {"enabled", "color", "direction"}
_DATA_KEYS = {"role", "colors", "dataset", "local", "variable", "transform", "classification", "texture"}
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

    @property
    def layers(self) -> Tuple[Layer, Layer]:
        return (self.land, self.ocean)

    def datasets(self) -> Tuple[DatasetEntry, ...]:
        out = []
        for layer in self.layers:
            if layer.dataset is not None and layer.dataset not in out:
                out.append(layer.dataset)
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


def _classification(t: Any, n: int, colors: Tuple[str, ...], cls: str) -> Classification:
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
        for k in ("dataset", "local", "variable", "transform", "classification"):
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
    classification = _classification(ctab, len(colors), colors, cls)
    if entry.format == "kit-design" and classification.method != "categorical":
        raise RecipeError(f"{cls}.classification.method", f"dataset {entry.id} is categorical; use "
                                                          "method = \"categorical\"")
    texture = _texture(t.get("texture"), cls, role, classification.method, len(colors))
    return Layer(cls=cls, role=role, colors=colors, dataset=entry, variable=variable,
                 transform=transform, classification=classification, texture=texture)


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
    return Recipe(format=fmt, id=rid, title=title, description=description, seed=seed, land=land,
                  ocean=ocean, sha256=hashlib.sha256(raw).hexdigest(), path=path, shadow=shadow)


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

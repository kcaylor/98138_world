"""Ice-covered regions of the kit grid (feature 015, FR-003).

Two sets of kit cells, in kit (combination A) coordinates, packaged as ``kit_31203_ice.json`` and
rolled to the board as hung:

- **land ice**: land cells whose centre lies in a named region: Antarctica (south of 60° S) and
  Greenland (centre latitude above 59°, longitude between -75° and -10°, Iceland excluded:
  latitude below 67° and longitude east of -26°). The same regions as the ``013-rainfall``
  design's ``[[land.override]]`` tables; bounds are strict.
- **sea ice**: ocean cells (the shadow included) whose 1991-2020 warmest-month mean sea surface
  temperature (NOAA ERSST v5 long-term monthly means, the pinned ``ersst-v5-ltm-1991-2020`` file)
  is at or below -1.5 °C, i.e. near freezing all year, or that have no ERSST value and lie
  poleward of 60°.

The map pages' palette chooser uses them to show ice-covered regions as White ice or with the
map's data; maps and layouts never read them. The maintainer tool ``python -m kit31203 ice-mask``
regenerates the file and ``--check`` verifies it.

Feature 016 (FR-020a/b; research R18; contracts/template-file.md "Ice file"): a non-kit template
has its own ice regions, ``data/templates/<id>-ice.json`` beside its template file, made with the
same rules at the template's stud locations by ``python -m maptemplates ice-mask ID`` (board
coordinates; the template has one arrangement, A). ``load_template_ice(template)`` reads it for
``map cells`` and refuses a file made for another layout: its ``source.template_layout_sha256``
must equal the template's layout digest, which leaves the confirmation out, so confirming the
template keeps the file valid. For the kit it returns the packaged ``kit_31203_ice.json``.
Map builds never read either file. Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from ..datasets.grid import SourceGrid
from .projection import DATA_DIR, KitProjection, load_kit_projection
from .reproject import reproject_layer

ICE_PATH = DATA_DIR / "kit_31203_ice.json"
FORMAT_VERSION = "1"
DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."

LAND_ICE_REGIONS = (
    {"name": "Antarctica", "lat_max": -60.0},
    {"name": "Greenland", "lat_min": 59.0, "lon_min": -75.0, "lon_max": -10.0,
     "exclude": [{"name": "Iceland", "lat_max": 67.0, "lon_min": -26.0}]},
)
SEA_ICE_RULE = {"dataset": "ersst-v5-ltm-1991-2020", "variable": "sst", "reduce": "monthly-max",
                "max_value": -1.5, "unobserved_lat": 60.0}


def _inside(lat: float, lon: float, box: Dict[str, Any]) -> bool:
    return (lat > box.get("lat_min", -np.inf) and lat < box.get("lat_max", np.inf)
            and lon > box.get("lon_min", -np.inf) and lon < box.get("lon_max", np.inf))


def in_region(lat: float, lon: float, region: Dict[str, Any]) -> bool:
    """Whether a cell centre lies in ``region`` (strict bounds, minus its excluded boxes)."""
    return _inside(lat, lon, region) and not any(_inside(lat, lon, b) for b in region.get("exclude", ()))


def _centres(projection: KitProjection):
    H, W = projection.height, projection.width
    lat = np.empty((H, W))
    lon = np.empty((H, W))
    for r in range(H):
        for c in range(W):
            lat[r, c], lon[r, c] = projection.cell_center(r, c)
    return lat, lon


def land_ice_mask(land: np.ndarray, projection: Optional[KitProjection] = None) -> np.ndarray:
    """Land cells (kit coordinates) in one of ``LAND_ICE_REGIONS``."""
    projection = projection or load_kit_projection()
    land = np.asarray(land, dtype=bool)
    lat, lon = _centres(projection)
    out = np.zeros_like(land)
    for r, c in zip(*np.nonzero(land)):
        out[r, c] = any(in_region(lat[r, c], lon[r, c], reg) for reg in LAND_ICE_REGIONS)
    return out


def sea_ice_mask(warmest: SourceGrid, land: np.ndarray,
                 projection: Optional[KitProjection] = None) -> np.ndarray:
    """Ocean cells (kit coordinates) that ``SEA_ICE_RULE`` calls sea ice, from the warmest-month
    field ``warmest`` (cell mean of the source values, as the maps reproject)."""
    projection = projection or load_kit_projection()
    ocean = ~np.asarray(land, dtype=bool)
    fld = reproject_layer(warmest, projection, ocean, "ocean")
    lat, _ = _centres(projection)
    cold = ocean & ~fld.filled & (fld.values <= SEA_ICE_RULE["max_value"])
    unobserved = ocean & fld.filled & (np.abs(lat) >= SEA_ICE_RULE["unobserved_lat"])
    return cold | unobserved


@dataclass(frozen=True)
class IceRegions:
    land: np.ndarray          # 80 x 128 bool, land-ice cells
    sea: np.ndarray           # 80 x 128 bool, sea-ice cells
    source: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return id(self)

    def rolled(self, arrangement) -> "IceRegions":
        """The regions on the board as hung (``arrangement.roll``)."""
        return IceRegions(land=arrangement.roll(self.land), sea=arrangement.roll(self.sea),
                          source=self.source)


def derive_ice_regions(warmest: SourceGrid, *, land: Optional[np.ndarray] = None,
                       projection: Optional[KitProjection] = None) -> IceRegions:
    """Both regions from the rules (the maintainer tool's computation)."""
    from .build import land_mask_array

    projection = projection or load_kit_projection()
    land = land_mask_array() if land is None else np.asarray(land, dtype=bool)
    return IceRegions(land=land_ice_mask(land, projection), sea=sea_ice_mask(warmest, land, projection))


def _cells(mask: np.ndarray):
    return [int(i) for i in np.flatnonzero(mask.ravel())]


def ice_document(ice: IceRegions, source: Dict[str, Any]) -> Dict[str, Any]:
    """The JSON document for ``kit_31203_ice.json``."""
    return {"format_version": FORMAT_VERSION, "kit_id": "31203", "grid": {"width": 128, "height": 80,
            "coordinates": "kit (combination A), row-major cell index = row * 128 + column"},
            "source": source,
            "land_ice": {"count": int(ice.land.sum()), "cells": _cells(ice.land)},
            "sea_ice": {"count": int(ice.sea.sum()), "cells": _cells(ice.sea)}}


def parse_ice_regions(data: Dict[str, Any], filename: str = "kit_31203_ice.json") -> IceRegions:
    from .build import land_mask_array

    if data.get("format_version") != FORMAT_VERSION:
        raise ValueError(f"{filename}: format_version must be {FORMAT_VERSION!r}")
    src = data.get("source") or {}
    if src.get("disclaimer") != DISCLAIMER:
        raise ValueError(f"{filename}: source.disclaimer is required")
    land = land_mask_array()
    masks = {}
    for name, want_land in (("land_ice", True), ("sea_ice", False)):
        block = data.get(name) or {}
        cells = block.get("cells")
        if not isinstance(cells, list) or block.get("count") != len(cells):
            raise ValueError(f"{filename}: {name}.count must equal the number of cells")
        m = np.zeros(land.size, dtype=bool)
        idx = np.asarray(cells, dtype=int)
        if idx.size and (idx.min() < 0 or idx.max() >= land.size):
            raise ValueError(f"{filename}: {name} has a cell outside the grid")
        m[idx] = True
        m = m.reshape(land.shape)
        if (m & (land if not want_land else ~land)).any():
            raise ValueError(f"{filename}: {name} has cells on {'land' if not want_land else 'ocean'}")
        masks[name] = m
    return IceRegions(land=masks["land_ice"], sea=masks["sea_ice"], source=dict(src))


@lru_cache(maxsize=None)
def _load(path: Path) -> IceRegions:
    with open(path, "r", encoding="utf-8") as f:
        return parse_ice_regions(json.load(f), path.name)


def load_ice_regions(path: Optional[Path] = None) -> IceRegions:
    """The packaged ice regions (kit coordinates)."""
    return _load(Path(path) if path else ICE_PATH)


# --- Feature 016: a template's ice regions (data-model.md Template ice regions) -------------

TEMPLATE_ICE_SUFFIX = "-ice.json"
TEMPLATE_COORDINATES = "board, row-major index = row * {width} + column"


class TemplateIceError(ValueError):
    """A template's ice file is missing, broken or made for another layout (names the file)."""


def template_ice_path(template) -> Path:
    """``<id>-ice.json`` beside the template's file (``TEMPLATE_DIR`` for a template without one)."""
    if template.path is not None:
        return Path(template.path).with_name(f"{template.id}{TEMPLATE_ICE_SUFFIX}")
    from .. import templates

    return Path(templates.TEMPLATE_DIR) / f"{template.id}{TEMPLATE_ICE_SUFFIX}"


def _remake(template_id: str) -> str:
    return f"make it with: PYTHONPATH=tools python -m maptemplates ice-mask {template_id} (from cli/)"


def parse_template_ice(data: Dict[str, Any], template, filename: Optional[str] = None) -> IceRegions:
    """The ice regions of ``data`` (an ice file's JSON) on ``template``'s board. Raises
    ``TemplateIceError`` naming the file and the rule broken."""
    name = filename or f"{template.id}{TEMPLATE_ICE_SUFFIX}"

    def fail(message: str):
        raise TemplateIceError(f"{name}: {message}")

    if not isinstance(data, dict):
        fail("must be a JSON object")
    if data.get("format_version") != FORMAT_VERSION:
        fail(f"format_version must be {FORMAT_VERSION!r}")
    if data.get("template_id") != template.id:
        fail(f"template_id is {data.get('template_id')!r}, not the template {template.id!r}")
    src = data.get("source")
    if not isinstance(src, dict) or src.get("disclaimer") != DISCLAIMER:
        fail("source.disclaimer is required")
    recorded = src.get("template_layout_sha256")
    if recorded != template.layout_sha256:
        fail(f"source.template_layout_sha256 {recorded!r} is not the layout of template {template.id} "
             f"({template.layout_sha256}): the file was made for another layout; {_remake(template.id)}")
    grid = data.get("grid") or {}
    if (grid.get("width"), grid.get("height")) != (template.width, template.height):
        fail(f"grid must be {template.width} x {template.height}")
    size = template.width * template.height
    masks = {}
    for block, want, cls in (("land_ice", template.land, "land"), ("sea_ice", template.ocean, "ocean")):
        b = data.get(block) or {}
        cells = b.get("cells")
        if not isinstance(cells, list) or not all(isinstance(i, int) and not isinstance(i, bool) for i in cells):
            fail(f"{block}.cells must be a list of board indices")
        if b.get("count") != len(cells):
            fail(f"{block}.count must equal the number of cells")
        idx = np.asarray(cells, dtype=int)
        if idx.size and (idx.min() < 0 or idx.max() >= size):
            fail(f"{block} has a cell outside the {template.width} x {template.height} board")
        m = np.zeros(size, dtype=bool)
        m[idx] = True
        m = m.reshape(template.height, template.width)
        if (m & ~np.asarray(want, dtype=bool)).any():
            bad = int(np.flatnonzero((m & ~np.asarray(want, dtype=bool)).ravel())[0])
            fail(f"{block} has cells that are not {cls} studs of the template (first: row {bad // template.width}, "
                 f"column {bad % template.width})")
        masks[block] = m
    return IceRegions(land=masks["land_ice"], sea=masks["sea_ice"], source=dict(src))


@lru_cache(maxsize=16)
def _read_template_ice(path: str, mtime_ns: int, size: int) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_template_ice(template) -> IceRegions:
    """The ice regions of ``template`` (board coordinates): the packaged kit file for
    ``kit-31203``; for any other template its ``<id>-ice.json``, which must record the template's
    layout digest (``TemplateIceError`` otherwise, or when the file is missing or broken)."""
    if template.is_kit:
        return load_ice_regions()
    path = template_ice_path(template)
    try:
        st = path.stat()
    except OSError:
        raise TemplateIceError(f"{path.name}: template {template.id} has no ice regions file ({path}); "
                               f"{_remake(template.id)}") from None
    try:
        data = _read_template_ice(str(path), st.st_mtime_ns, st.st_size)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TemplateIceError(f"{path.name}: cannot read it ({exc})") from exc
    return parse_template_ice(data, template, path.name)

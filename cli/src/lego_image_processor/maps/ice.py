"""Ice-covered regions of the kit grid (feature 012, FR-003).

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
regenerates the file and ``--check`` verifies it. Not affiliated with or endorsed by The LEGO
Group.
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

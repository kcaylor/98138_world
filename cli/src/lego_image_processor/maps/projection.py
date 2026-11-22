"""The kit grid's projection, fitted to the kit's land/sea mask (FR-013; research R2).

Rule: ``row = floor(equator_row - rows_per_radian * radians(lat))`` and
``col = floor(((lon - left_edge_lon) mod 360) / deg_per_col)``. Rows outside 0..height-1 are -1.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PROJECTION_PATH = DATA_DIR / "kit_31203_projection.json"
MODELS = ("equirectangular",)


@dataclass(frozen=True)
class KitProjection:
    model: str
    width: int
    height: int
    left_edge_lon: float
    deg_per_col: float
    equator_row: float
    rows_per_radian: float
    agreement: Dict[str, float] = field(default_factory=dict)
    source: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash((self.model, self.left_edge_lon, self.equator_row, self.rows_per_radian))

    def rows_for_lat(self, lat: np.ndarray) -> np.ndarray:
        lat = np.asarray(lat, dtype=float)
        row = np.floor(self.equator_row - self.rows_per_radian * np.radians(lat))
        row = np.where(np.isfinite(row), row, -1).astype(int)
        return np.where((row >= 0) & (row < self.height), row, -1)

    def cols_for_lon(self, lon: np.ndarray) -> np.ndarray:
        lon = np.asarray(lon, dtype=float)
        col = np.floor(((lon - self.left_edge_lon) % 360.0) / self.deg_per_col).astype(int)
        return np.clip(col, 0, self.width - 1)

    def cell_center(self, row: int, col: int) -> Tuple[float, float]:
        lat = math.degrees((self.equator_row - (row + 0.5)) / self.rows_per_radian)
        lon = self.left_edge_lon + (col + 0.5) * self.deg_per_col
        lon = ((lon + 180.0) % 360.0) - 180.0
        return lat, lon

    def to_dict(self) -> Dict[str, Any]:
        return {"kit": "31203", "model": self.model, "width": self.width, "height": self.height,
                "left_edge_lon": self.left_edge_lon, "deg_per_col": self.deg_per_col,
                "equator_row": self.equator_row, "rows_per_radian": self.rows_per_radian,
                "agreement": dict(self.agreement), "source": dict(self.source)}


def parse_projection(data: Dict[str, Any], filename: str = "kit_31203_projection.json") -> KitProjection:
    if data.get("model") not in MODELS:
        raise ValueError(f"{filename}: model must be one of {MODELS}")
    try:
        p = KitProjection(model=data["model"], width=int(data["width"]), height=int(data["height"]),
                          left_edge_lon=float(data["left_edge_lon"]),
                          deg_per_col=float(data["deg_per_col"]),
                          equator_row=float(data["equator_row"]),
                          rows_per_radian=float(data["rows_per_radian"]),
                          agreement={k: float(v) for k, v in (data.get("agreement") or {}).items()},
                          source=dict(data.get("source") or {}))
    except KeyError as exc:
        raise ValueError(f"{filename}: missing field {exc}") from exc
    if (p.width, p.height) != (128, 80):
        raise ValueError(f"{filename}: the kit grid is 128x80")
    if abs(p.deg_per_col * p.width - 360.0) > 1e-9:
        raise ValueError(f"{filename}: columns must span 360 degrees")
    if not p.source.get("disclaimer"):
        raise ValueError(f"{filename}: source.disclaimer is required")
    return p


@lru_cache(maxsize=None)
def _load(path: Path) -> KitProjection:
    with open(path, "r", encoding="utf-8") as f:
        return parse_projection(json.load(f), path.name)


def load_kit_projection(path: Optional[Path] = None) -> KitProjection:
    """The shipped kit projection (package data)."""
    return _load(Path(path) if path else PROJECTION_PATH)

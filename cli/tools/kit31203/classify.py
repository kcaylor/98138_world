"""Stud colour classification for section images (research R6). Pure apart from file loading.

Each of the 16x16 cells is sampled as the median of a 5x5 patch at its centre (using the image's
own width and height), then classified by CIEDE2000 against fixed reference render colours.
A cell is ambiguous when nearest/second-nearest distance > RATIO_THRESHOLD or when the nearest
distance exceeds MAX_DELTA_E; ambiguous cells must be resolved in ``overrides.json``.
"""

from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np

from lego_image_processor.core.color_quantizer import delta_e_2000
from lego_image_processor.palette.converter import rgb_to_lab

TOOL_DIR = Path(__file__).resolve().parent
REFERENCE_PATH = TOOL_DIR / "reference_colors.json"
OVERRIDES_PATH = TOOL_DIR / "overrides.json"

CELLS = 16
PATCH = 5
RATIO_THRESHOLD = 0.6
MAX_DELTA_E = 12.0  # ΔE00; above the 99.9th percentile (11.5) of nearest distances in the PDF
METHOD = "median 5x5 at cell centre; CIEDE2000 to reference render colours"
REQUIRED_FIELDS = ("x", "y", "chosen", "reason", "decided_by", "decided_on")


class ClassificationError(Exception):
    """Unresolved ambiguous positions or invalid overrides."""

    exit_code = 7


def load_reference_colors(path: Path = REFERENCE_PATH) -> Tuple[Tuple[str, ...], np.ndarray]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    colors = data["colors"]
    return tuple(colors), np.array([colors[k] for k in colors], dtype=float)


def cell_centres(width: int, height: int) -> List[Tuple[int, int, int, int]]:
    """(i, j, cx, cy) for every cell: column i, row j, centre pixel."""
    return [(i, j, int((i + 0.5) * width / CELLS), int((j + 0.5) * height / CELLS))
            for j in range(CELLS) for i in range(CELLS)]


def sample_cells(image) -> np.ndarray:
    """(16, 16, 3) median RGB of the 5x5 patch at each cell centre."""
    arr = np.asarray(image.convert("RGB") if hasattr(image, "convert") else image, dtype=float)
    h, w = arr.shape[:2]
    half = PATCH // 2
    out = np.zeros((CELLS, CELLS, 3))
    for i, j, cx, cy in cell_centres(w, h):
        patch = arr[max(cy - half, 0):cy + half + 1, max(cx - half, 0):cx + half + 1]
        out[j, i] = np.median(patch.reshape(-1, 3), axis=0)
    return out


@dataclass
class Classification:
    keys: Tuple[str, ...]
    samples: np.ndarray   # (H, W, 3) RGB
    auto: np.ndarray      # (H, W) index of nearest reference
    second: np.ndarray    # (H, W) index of second nearest
    d1: np.ndarray        # ΔE00 to nearest
    d2: np.ndarray        # ΔE00 to second nearest
    ratio: np.ndarray     # d1 / d2
    flagged: np.ndarray   # (H, W) bool
    ratio_threshold: float
    max_delta_e: float

    def flagged_positions(self) -> List[Tuple[int, int]]:
        ys, xs = np.nonzero(self.flagged)
        return sorted(zip(xs.tolist(), ys.tolist()), key=lambda p: (p[1], p[0]))

    def describe(self, x: int, y: int) -> str:
        return (f"({x}, {y}) {self.keys[self.auto[y, x]]}/{self.keys[self.second[y, x]]} "
                f"ratio {self.ratio[y, x]:.2f}")


def classify(samples: np.ndarray, keys: Sequence[str], refs: np.ndarray,
             ratio_threshold: float = RATIO_THRESHOLD,
             max_delta_e: float = MAX_DELTA_E) -> Classification:
    samples = np.asarray(samples, dtype=float)
    lab = rgb_to_lab(samples)
    ref_lab = rgb_to_lab(np.asarray(refs, dtype=float))
    dist = delta_e_2000(lab[..., None, :], ref_lab.reshape((1,) * (lab.ndim - 1) + ref_lab.shape))
    order = np.argsort(dist, axis=-1, kind="stable")
    d1 = np.take_along_axis(dist, order[..., :1], -1)[..., 0]
    d2 = np.take_along_axis(dist, order[..., 1:2], -1)[..., 0]
    ratio = np.divide(d1, d2, out=np.ones_like(d1), where=d2 > 0)
    flagged = (ratio > ratio_threshold) | (d1 > max_delta_e)
    return Classification(keys=tuple(keys), samples=samples, auto=order[..., 0],
                          second=order[..., 1], d1=d1, d2=d2, ratio=ratio, flagged=flagged,
                          ratio_threshold=ratio_threshold, max_delta_e=max_delta_e)


def load_overrides(path: Path = OVERRIDES_PATH) -> List[Dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("overrides")
    if data.get("format_version") != "1" or not isinstance(rows, list):
        raise ClassificationError(f"{path.name}: expected format_version '1' and an overrides list")
    return rows


def _check_row(row: Dict[str, Any], keys: Sequence[str], shape) -> None:
    missing = [f for f in REQUIRED_FIELDS if f not in row]
    where = f"override ({row.get('x')}, {row.get('y')})"
    if missing:
        raise ClassificationError(f"{where}: missing fields {missing}")
    h, w = shape
    if not (isinstance(row["x"], int) and isinstance(row["y"], int)
            and 0 <= row["x"] < w and 0 <= row["y"] < h):
        raise ClassificationError(f"{where}: position outside the {w}x{h} grid")
    if row["chosen"] not in keys:
        raise ClassificationError(f"{where}: chosen '{row['chosen']}' is not a kit colour")
    for f in ("reason", "decided_by"):
        if not isinstance(row[f], str) or not row[f].strip():
            raise ClassificationError(f"{where}: '{f}' must be a non-empty string")
    try:
        _dt.date.fromisoformat(str(row["decided_on"]))
    except ValueError:
        raise ClassificationError(f"{where}: decided_on must be YYYY-MM-DD")


def apply_overrides(result: Classification,
                    overrides: Iterable[Dict[str, Any]]) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """Final index grid and the override records applied (data-model.md Override)."""
    keys = result.keys
    grid = result.auto.copy()
    applied, seen, conflicts = [], set(), []
    for row in overrides:
        _check_row(row, keys, grid.shape)
        x, y = row["x"], row["y"]
        if (x, y) in seen:
            raise ClassificationError(f"override ({x}, {y}): listed more than once")
        seen.add((x, y))
        auto = keys[result.auto[y, x]]
        if not result.flagged[y, x] and row["chosen"] != auto and not row.get("force"):
            conflicts.append(f"({x}, {y}) auto {auto} -> {row['chosen']}")
            continue
        grid[y, x] = keys.index(row["chosen"])
        applied.append({
            "x": x, "y": y, "auto": auto, "chosen": row["chosen"],
            "ratio": round(float(result.ratio[y, x]), 3), "reason": row["reason"],
            "decided_by": row["decided_by"], "decided_on": str(row["decided_on"]),
        })
    if conflicts:
        raise ClassificationError(
            f"{len(conflicts)} override(s) contradict a confident classification without "
            f"\"force\": true: " + "; ".join(conflicts[:20]))
    unresolved = [p for p in result.flagged_positions() if p not in seen]
    if unresolved:
        listed = "; ".join(result.describe(x, y) for x, y in unresolved[:20])
        raise ClassificationError(
            f"{len(unresolved)} ambiguous position(s) have no override in overrides.json: {listed}"
            f"{' ...' if len(unresolved) > 20 else ''}. Run `python -m kit31203 review` to "
            f"inspect them and add each to overrides.json.")
    applied.sort(key=lambda r: (r["y"], r["x"]))
    return grid, applied

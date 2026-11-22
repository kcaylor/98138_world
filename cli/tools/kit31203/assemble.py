"""Design, mask, change record and counts assembly; deterministic JSON and the all-or-nothing
writer used by ``extract`` (contracts/data-files.md shapes)."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

IGNORED_KEYS = frozenset({"generated_on"})
WIDTH, HEIGHT, CELLS = 128, 80, 16
DESIGN_FILE = "kit_31203_design.json"
MASK_FILE = "lego_world_map_land_sea_mask.json"
CHANGES_FILE = "kit_31203_mask_changes.json"
LAND_KEY = "lego_white"
_DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


class SupplyError(Exception):
    """A colour's used count exceeds the kit supply."""

    exit_code = 8


def place_sections(cells_by_slot: Mapping[Tuple[int, int], np.ndarray]) -> np.ndarray:
    """Assemble 8x5 sections of 16x16 cells into the 128x80 grid (``grid[y, x]``)."""
    slots = {(c, r) for c in range(WIDTH // CELLS) for r in range(HEIGHT // CELLS)}
    if set(cells_by_slot) != slots:
        raise ValueError(f"expected sections for all 40 slots; missing {sorted(slots - set(cells_by_slot))}")
    first = np.asarray(next(iter(cells_by_slot.values())))
    grid = np.zeros((HEIGHT, WIDTH) + first.shape[2:], dtype=first.dtype)
    for (c, r), cells in cells_by_slot.items():
        grid[r * CELLS:(r + 1) * CELLS, c * CELLS:(c + 1) * CELLS] = cells
    return grid


def encode_rows(index_grid: np.ndarray) -> List[str]:
    """One base-36 digit per position, indexing the palette."""
    return ["".join(_DIGITS[int(v)] for v in row) for row in np.asarray(index_grid)]


def decode_rows(rows: Sequence[str]) -> np.ndarray:
    return np.array([[_DIGITS.index(ch) for ch in row] for row in rows], dtype=int)


def color_counts(index_grid: np.ndarray, palette: Sequence[str],
                 supplied: Mapping[str, int]) -> List[Dict[str, Any]]:
    grid = np.asarray(index_grid)
    out = []
    for i, key in enumerate(palette):
        used = int((grid == i).sum())
        out.append({"key": key, "used": used, "supplied": int(supplied[key]),
                    "spare": int(supplied[key]) - used, "spare_note": "unexplained"})
    return out


def check_supply(counts: Sequence[Mapping[str, Any]]) -> None:
    over = [c for c in counts if c["used"] > c["supplied"]]
    if over:
        raise SupplyError("supply exceeded: " + "; ".join(
            f"{c['key']} used {c['used']}, supplied {c['supplied']}" for c in over))


def build_design(source: Dict[str, Any], palette: Sequence[str], index_grid: np.ndarray,
                 sections: Sequence[Dict[str, Any]], classification: Dict[str, Any],
                 overrides: Sequence[Dict[str, Any]], counts: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "format_version": "1",
        "source": source,
        "width": WIDTH, "height": HEIGHT, "coordinate_system": "top_left_origin",
        "palette": list(palette),
        "rows": encode_rows(index_grid),
        "sections": list(sections),
        "classification": classification,
        "overrides": list(overrides),
        "counts": list(counts),
    }


def build_mask(index_grid: np.ndarray, palette: Sequence[str], source: Dict[str, Any]) -> Dict[str, Any]:
    """Land/sea mask derived from the design: land = white cells. Existing keys are kept."""
    land = np.asarray(index_grid) == list(palette).index(LAND_KEY)
    coords = [[int(x), int(y)] for y in range(HEIGHT) for x in range(WIDTH) if land[y, x]]
    return {
        "description": "Land/sea mask of LEGO World Map 31203: land = white positions of the "
                       "official design (kit_31203_design.json)",
        "dimensions": {"width": WIDTH, "height": HEIGHT, "total_positions": WIDTH * HEIGHT},
        "land_positions": len(coords),
        "ocean_positions": WIDTH * HEIGHT - len(coords),
        "coordinate_system": "top_left_origin",
        "source": source,
        "derived_from": DESIGN_FILE,
        "land_coordinates": coords,
        "mask_2d": [[bool(v) for v in row] for row in land],
    }


def _land_set(mask: Mapping[str, Any]) -> set:
    return {(int(c[0]), int(c[1])) for c in mask.get("land_coordinates", [])}


def mask_changes(previous: Mapping[str, Any], new: Mapping[str, Any]) -> List[Dict[str, Any]]:
    old_land, new_land = _land_set(previous), _land_set(new)
    changed = sorted(old_land ^ new_land, key=lambda p: (p[1], p[0]))
    return [{"x": x, "y": y, "old": "land" if (x, y) in old_land else "ocean",
             "new": "land" if (x, y) in new_land else "ocean"} for x, y in changed]


def build_change_record(previous_mask: Mapping[str, Any], previous_sha256: str,
                        new_mask: Mapping[str, Any], source: Dict[str, Any],
                        previous_record: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Change record against the previous mask.

    Once the shipped mask is itself derived from the design and has not changed, the committed
    record is carried forward (it documents the change from the last mask not derived from the
    design), so regeneration is reproducible.
    """
    if (previous_record is not None and previous_mask.get("derived_from") == DESIGN_FILE
            and _land_set(previous_mask) == _land_set(new_mask)):
        sha = previous_record["previous_mask_sha256"]
        changes = list(previous_record["changes"])
    else:
        sha = previous_sha256
        changes = mask_changes(previous_mask, new_mask)
    return {"format_version": "1", "source": source, "previous_mask_sha256": sha,
            "count": len(changes), "changes": changes}


def dump_json(obj: Any) -> str:
    """2-space indent, UTF-8 characters kept, insertion order preserved, trailing newline."""
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


class AtomicWriter:
    """Collects outputs in a temp dir; moves them into ``out_dir`` only if the block succeeds."""

    def __init__(self, out_dir: Path):
        self.out_dir = Path(out_dir)
        self.written: List[Path] = []
        self._tmp: Path | None = None
        self._names: List[str] = []

    def __enter__(self) -> "AtomicWriter":
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self._tmp = Path(tempfile.mkdtemp(prefix=".kit31203-", dir=self.out_dir.parent))
        return self

    def write_json(self, name: str, obj: Any) -> None:
        assert self._tmp is not None, "use AtomicWriter as a context manager"
        (self._tmp / name).write_text(dump_json(obj), encoding="utf-8", newline="\n")
        if name not in self._names:
            self._names.append(name)

    def __exit__(self, exc_type, exc, tb) -> bool:
        try:
            if exc_type is None:
                for name in self._names:
                    os.replace(self._tmp / name, self.out_dir / name)
                    self.written.append(self.out_dir / name)
        finally:
            shutil.rmtree(self._tmp, ignore_errors=True)
        return False


def json_differences(old: Any, new: Any, path: str = "", limit: int = 50) -> List[str]:
    """Paths where two JSON values differ, ignoring ``generated_on`` keys."""
    diffs: List[str] = []

    def walk(a, b, p):
        if len(diffs) >= limit:
            return
        if isinstance(a, dict) and isinstance(b, dict):
            for k in list(a) + [k for k in b if k not in a]:
                if k in IGNORED_KEYS:
                    continue
                sub = f"{p}.{k}" if p else str(k)
                if k not in a or k not in b:
                    diffs.append(sub)
                else:
                    walk(a[k], b[k], sub)
        elif isinstance(a, list) and isinstance(b, list):
            for i in range(max(len(a), len(b))):
                sub = f"{p}[{i}]"
                if i >= len(a) or i >= len(b):
                    diffs.append(sub)
                else:
                    walk(a[i], b[i], sub)
        elif a != b or type(a) is not type(b):
            diffs.append(p)

    walk(old, new, path)
    return diffs

"""Pair page-159 count tokens with element IDs and join the curated part catalog (pure)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

PART_CATALOG_PATH = Path(__file__).resolve().parent / "part_catalog.json"
COUNT_RE = re.compile(r"^(\d+)x$")
ID_RE = re.compile(r"^\d{6,7}$")
MAX_DX = 3.0   # pt, same column
MAX_DY = 20.0  # pt, ID directly below its count
SOURCE_PAGE = 159


class PairingError(Exception):
    exit_code = 9


def pair_words(words: Iterable[Sequence]) -> List[Tuple[str, int]]:
    """(element_id, quantity) pairs in page order: column by column, top to bottom.

    ``words`` are ``(x, y, text)`` in PDF points with y growing upward. Each count token
    (``NNNx``) pairs with the element-ID token in the same column (|dx| < 3 pt) whose
    positive distance below it is smallest and under 20 pt.
    """
    counts, ids = [], []
    for x, y, text in ((float(w[0]), float(w[1]), str(w[2]).strip()) for w in words):
        if COUNT_RE.match(text):
            counts.append((x, y, text))
        elif ID_RE.match(text):
            ids.append((x, y, text))

    used: Dict[int, Tuple[float, float, str]] = {}
    pairs = []
    for cx, cy, ctext in counts:
        best, best_dy = None, None
        for i, (ix, iy, _) in enumerate(ids):
            dy = cy - iy
            if abs(ix - cx) < MAX_DX and 0 < dy < MAX_DY and (best_dy is None or dy < best_dy):
                best, best_dy = i, dy
        if best is None:
            raise PairingError(f"count token '{ctext}' at ({cx}, {cy}) has no element ID below it")
        if best in used:
            raise PairingError(
                f"element ID '{ids[best][2]}' is claimed by counts '{used[best][2]}' and '{ctext}'")
        used[best] = (cx, cy, ctext)
        pairs.append((cx, cy, ids[best][2], int(COUNT_RE.match(ctext).group(1))))
    orphans = [ids[i][2] for i in range(len(ids)) if i not in used]
    if orphans:
        raise PairingError(f"element ID tokens without a count: {', '.join(orphans)}")

    # Group into columns (x within MAX_DX), left to right; top to bottom within a column.
    columns: List[List[tuple]] = []
    for p in sorted(pairs, key=lambda p: p[0]):
        if columns and abs(columns[-1][0][0] - p[0]) < MAX_DX:
            columns[-1].append(p)
        else:
            columns.append([p])
    ordered = [p for col in columns for p in sorted(col, key=lambda p: -p[1])]
    return [(eid, qty) for _, _, eid, qty in ordered]


def load_part_catalog(path: Path = PART_CATALOG_PATH) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def join_catalog(pairs: List[Tuple[str, int]], catalog: Dict[str, Any],
                 color_keys: Dict[Tuple[str, str], str] | None = None) -> List[Dict[str, Any]]:
    """Inventory element rows for the pairs. ``color_keys`` maps (role, LEGO color name) to a
    kit color key for map elements."""
    by_id = {p["element_id"]: p for p in catalog["parts"]}
    missing = [eid for eid, _ in pairs if eid not in by_id]
    if missing:
        raise PairingError(f"part catalog has no entry for element(s): {', '.join(missing)}")
    rows = []
    for eid, qty in pairs:
        part = by_id[eid]
        key = None
        if part["role"] in ("land", "ocean") and color_keys is not None:
            key = color_keys.get((part["role"], part["color"]))
            if key is None:
                raise PairingError(f"element {eid}: no kit color for {part['role']} {part['color']}")
        rows.append({
            "element_id": eid,
            "quantity": qty,
            "source_page": SOURCE_PAGE,
            "design_id": part["design_id"],
            "part_ids": list(part["part_ids"]),
            "description": part["description"],
            "color": part["color"],
            "color_key": key,
            "role": part["role"],
            "metadata_verified": bool(part["verified"]),
            "citation": part["citation"],
        })
    return rows

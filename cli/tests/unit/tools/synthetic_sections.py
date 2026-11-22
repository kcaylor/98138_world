"""Synthetic 16x16 section images for offline tests (research R10: no LEGO artwork committed).

Each cell is drawn as a stud: a disc in the cell's reference render colour on a slightly darker
base, then Gaussian noise and JPEG compression are applied, at 154x154 or 154x153 px.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Mapping, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw

REFERENCE_PATH = Path(__file__).resolve().parents[3] / "tools" / "kit31203" / "reference_colors.json"


def reference_colors() -> dict:
    return json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))["colors"]


def render_section(
    grid: Sequence[Sequence],
    size: Tuple[int, int] = (154, 154),
    colors: Mapping[str, Sequence[int]] | None = None,
    noise: float = 2.0,
    quality: int = 85,
    seed: int = 0,
) -> Image.Image:
    """Render a 16x16 grid of colour keys (or RGB triples) as an RGB section image."""
    colors = colors or reference_colors()
    w, h = size
    img = Image.new("RGB", size, (20, 20, 20))
    draw = ImageDraw.Draw(img)
    for j in range(16):
        for i in range(16):
            value = grid[j][i]
            rgb = tuple(int(v) for v in (colors[value] if isinstance(value, str) else value))
            x0, x1 = i * w / 16, (i + 1) * w / 16
            y0, y1 = j * h / 16, (j + 1) * h / 16
            base = tuple(max(0, int(c * 0.85)) for c in rgb)
            draw.rectangle([x0, y0, x1, y1], fill=base)
            draw.ellipse([x0 + 0.6, y0 + 0.6, x1 - 0.6, y1 - 0.6], fill=rgb)
    arr = np.asarray(img).astype(float)
    if noise:
        arr += np.random.default_rng(seed).normal(0.0, noise, arr.shape)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def uniform_grid(key: str):
    return [[key] * 16 for _ in range(16)]


def patterned_grid(keys: Sequence[str], offset: int = 0):
    """A deterministic 16x16 grid cycling through ``keys``."""
    n = len(keys)
    return [[keys[(i * 7 + j * 3 + offset) % n] for i in range(16)] for j in range(16)]

"""Review sheet for ambiguous positions: each cell enlarged with its neighbours, its sample RGB,
the two candidate colours, plus a JSON stub for ``overrides.json``.

The sheet contains crops of LEGO instruction artwork. It is written outside the repository by
default and must never be committed. Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Tuple

from PIL import Image, ImageDraw

from kit31203 import assemble, classify

CELLS = classify.CELLS
ZOOM = 6
TILE_W, TILE_H = 330, 200


def _crop(img: Image.Image, i: int, j: int) -> Tuple[Image.Image, Tuple[int, int, int, int]]:
    """3x3-cell neighbourhood around cell (i, j), clipped to the section, and the cell's box."""
    w, h = img.size
    cw, ch = w / CELLS, h / CELLS
    x0, y0 = int(max(i - 1, 0) * cw), int(max(j - 1, 0) * ch)
    x1, y1 = int(min(i + 2, CELLS) * cw), int(min(j + 2, CELLS) * ch)
    crop = img.crop((x0, y0, x1, y1)).resize(((x1 - x0) * ZOOM, (y1 - y0) * ZOOM), Image.NEAREST)
    box = (int(i * cw - x0) * ZOOM, int(j * ch - y0) * ZOOM,
           int((i + 1) * cw - x0) * ZOOM, int((j + 1) * ch - y0) * ZOOM)
    return crop, box


def write_review(result: classify.Classification, images: Mapping[Tuple[int, int], Image.Image],
                 out: Path, existing: Mapping[Tuple[int, int], dict] | None = None) -> Tuple[Path, Path]:
    existing = existing or {}
    keys = result.keys
    _, refs = classify.load_reference_colors()
    flagged = result.flagged_positions()
    per_row = 4
    rows = max(1, (len(flagged) + per_row - 1) // per_row)
    sheet = Image.new("RGB", (TILE_W * per_row, TILE_H * rows), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    stub = []
    for n, (x, y) in enumerate(flagged):
        ox, oy = (n % per_row) * TILE_W, (n // per_row) * TILE_H
        img = images[(x // CELLS, y // CELLS)]
        crop, box = _crop(img, x % CELLS, y % CELLS)
        sheet.paste(crop, (ox + 4, oy + 4))
        draw.rectangle([ox + 4 + box[0], oy + 4 + box[1], ox + 4 + box[2], oy + 4 + box[3]],
                       outline=(255, 0, 0), width=2)
        a, b = int(result.auto[y, x]), int(result.second[y, x])
        rgb = tuple(int(v) for v in result.samples[y, x])
        tx = ox + 4 + crop.width + 8
        lines = [f"({x}, {y})", f"rgb {rgb}", f"ratio {result.ratio[y, x]:.2f}",
                 f"1: {keys[a][5:]}", f"   dE {result.d1[y, x]:.1f}",
                 f"2: {keys[b][5:]}", f"   dE {result.d2[y, x]:.1f}"]
        if (x, y) in existing:
            lines.append(f"set: {existing[(x, y)]['chosen'][5:]}")
        for k, line in enumerate(lines):
            draw.text((tx, oy + 6 + 14 * k), line, fill=(0, 0, 0))
        for k, idx in enumerate((a, b)):
            sx = tx + 40 * k
            draw.rectangle([sx, oy + 130, sx + 30, oy + 160], fill=tuple(int(v) for v in refs[idx]),
                           outline=(0, 0, 0))
        draw.rectangle([tx + 80, oy + 130, tx + 110, oy + 160], fill=rgb, outline=(0, 0, 0))
        stub.append({
            "x": x, "y": y, "chosen": existing.get((x, y), {}).get("chosen", keys[a]),
            "auto": keys[a], "second": keys[b], "ratio": round(float(result.ratio[y, x]), 3),
            "delta_e00": [round(float(result.d1[y, x]), 2), round(float(result.d2[y, x]), 2)],
            "sample_rgb": list(rgb),
            "reason": existing.get((x, y), {}).get("reason", ""),
            "decided_by": existing.get((x, y), {}).get("decided_by", ""),
            "decided_on": existing.get((x, y), {}).get("decided_on", ""),
        })
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    stub_path = out.with_name(out.stem + ".overrides-stub.json")
    stub_path.write_text(assemble.dump_json({"format_version": "1", "overrides": stub}), encoding="utf-8")
    return out, stub_path

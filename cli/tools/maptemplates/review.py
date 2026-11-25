"""Review sheet and flags list of a template layout (feature 016, FR-017; research R5).

``render_sheet`` draws every stud by class (land and ocean as round studs, margin as square tiles,
the outline ring in its own color), module lines every 16 studs, section names A1-H5 as hung in
combination A, row and column numbers (corrections are given as row, column, new class and
reason), the flagged studs and a legend; the disclaimer is the last line on the sheet. Water not
connected to the ocean is filled in its own color as well as marked, so inland seas stand out.

``flags_document`` / ``flags_text`` write the flags list (data-model.md ReviewFlag .row, .col,
.class, .land_share, .reason, .group_size), one flag per line, with a summary of the water
groups. Both go outside the repository. Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from lego_image_processor.templates import DISCLAIMER, SECTION_COLUMNS
from lego_image_processor.templates.board import MODULE, rim_cells

from .generate import FLAG_LAND_SHARE, FLAG_WATER, water_groups

COLORS = {
    "paper": (250, 250, 248),
    "board": (24, 24, 27),
    "land": (240, 240, 236),
    "ocean": (40, 112, 200),
    "inland_water": (0, 190, 175),
    "margin": (72, 72, 80),
    "ring": (214, 168, 56),
    "module": (150, 150, 158),
    "section": (255, 236, 120),
    "flag_land_share": (236, 40, 196),
    "flag_water": (255, 96, 0),
    "corrected": (60, 255, 80),
    "text": (24, 24, 24),
    "muted": (96, 96, 96),
}


def _font(size: int):
    for name in ("/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf", "DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


@dataclass
class SheetInfo:
    path: Path
    size: Tuple[int, int]
    origin: Tuple[int, int]     # top-left pixel of stud (0, 0)
    px: int                     # pixels per stud
    section_labels: List[str] = field(default_factory=list)
    text: List[str] = field(default_factory=list)   # every text line drawn, in order


def stud_centre(info: SheetInfo, row: int, col: int) -> Tuple[int, int]:
    x0, y0 = info.origin
    return x0 + col * info.px + info.px // 2, y0 + row * info.px + info.px // 2


def flag_counts(flags: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    """Flags by reason, the number of water groups and the largest one's size."""
    out = {FLAG_LAND_SHARE: 0, FLAG_WATER: 0}
    for f in flags:
        out[f["reason"]] = out.get(f["reason"], 0) + 1
    water = [f["group_size"] for f in flags if f["reason"] == FLAG_WATER]
    # a group of n studs contributes n flags of group_size n
    out["water groups"] = sum(water.count(n) // n for n in set(water))
    out["largest water group"] = max(water, default=0)
    return out


def legend_rows(flags: Sequence[Dict[str, Any]], corrected: bool) -> List[Tuple[str, str, str]]:
    """(color key, shape, label) for the legend."""
    rows = [("land", "round", "land (white 1x1 round plate, 6141)"),
            ("ocean", "round", "ocean (1x1 round tile, 98138)"),
            ("margin", "square", "margin, off the globe (1x1 square tile, 3070b)"),
            ("ring", "square", "outline ring (margin studs touching the globe)")]
    reasons = {f["reason"] for f in flags}
    if FLAG_LAND_SHARE in reasons:
        rows.append(("flag_land_share", "outline", f"flag: {FLAG_LAND_SHARE}"))
    if FLAG_WATER in reasons:
        rows.append(("inland_water", "flag_water", f"flag: {FLAG_WATER}"))
    if corrected:
        rows.append(("corrected", "outline", "hand correction recorded in the file"))
    return rows


def render_sheet(path, classes: np.ndarray, *, flags: Sequence[Dict[str, Any]] = (),
                 corrected: Iterable[Tuple[int, int]] = (), header: Sequence[str] = (), px: int = 16,
                 ticks: bool = True) -> SheetInfo:
    """Write the review sheet PNG of a classes array (height x width of ``L``/``O``/``M``)."""
    classes = np.asarray(classes)
    H, W = classes.shape
    on = classes != "M"
    ring = rim_cells(on)
    corrected = sorted({(int(r), int(c)) for r, c in corrected})
    by_stud: Dict[Tuple[int, int], set] = {}
    for f in flags:
        by_stud.setdefault((f["row"], f["col"]), set()).add(f["reason"])

    title_font, font = _font(max(14, px + 6)), _font(max(11, px - 2))
    small = _font(max(9, px - 5))
    line_h = max(14, px + 4)
    pad = max(12, px)
    left = pad + (3 * px if ticks else 0)
    top_text = pad + line_h * (len(header) + 1)
    top = top_text + (2 * px if ticks else pad // 2)
    legend = legend_rows(flags, bool(corrected))
    legend_h = line_h * ((len(legend) + 1) // 2) + pad
    width = left + W * px + pad + (2 * px if ticks else 0)
    height = top + H * px + pad + legend_h + line_h * 2 + pad
    img = Image.new("RGB", (width, height), COLORS["paper"])
    d = ImageDraw.Draw(img)
    text: List[str] = []

    def write(xy, s, fill="text", f=font):
        d.text(xy, s, fill=COLORS[fill], font=f)
        text.append(s)

    y = pad
    for i, line in enumerate(header):
        write((pad, y), line, "text" if i == 0 else "muted", title_font if i == 0 else font)
        y += line_h + (6 if i == 0 else 0)

    x0, y0 = left, top
    d.rectangle([x0, y0, x0 + W * px - 1, y0 + H * px - 1], fill=COLORS["board"])
    inset = max(1, px // 10)
    for r in range(H):
        for c in range(W):
            bx, by = x0 + c * px, y0 + r * px
            box = [bx + inset, by + inset, bx + px - 1 - inset, by + px - 1 - inset]
            reasons = by_stud.get((r, c), ())
            k = classes[r, c]
            if k == "M":
                d.rectangle(box, fill=COLORS["ring" if ring[r, c] else "margin"])
            else:
                fill = "land" if k == "L" else ("inland_water" if FLAG_WATER in reasons else "ocean")
                d.ellipse(box, fill=COLORS[fill])

    # module lines, then the flags and corrections on top, then section names (combination A)
    for c in range(0, W + 1, MODULE):
        d.line([(x0 + c * px, y0), (x0 + c * px, y0 + H * px - 1)], fill=COLORS["module"], width=1)
    for r in range(0, H + 1, MODULE):
        d.line([(x0, y0 + r * px), (x0 + W * px - 1, y0 + r * px)], fill=COLORS["module"], width=1)
    w = max(1, px // 8)
    for (r, c), reasons in by_stud.items():
        bx, by = x0 + c * px, y0 + r * px
        if FLAG_LAND_SHARE in reasons:
            d.rectangle([bx, by, bx + px - 1, by + px - 1], outline=COLORS["flag_land_share"], width=w)
        if FLAG_WATER in reasons:
            i2 = 2 * w
            d.rectangle([bx + i2, by + i2, bx + px - 1 - i2, by + px - 1 - i2], outline=COLORS["flag_water"],
                        width=max(1, w // 2 + (px >= 12)))
    for r, c in corrected:
        bx, by = x0 + c * px, y0 + r * px
        d.rectangle([bx, by, bx + px - 1, by + px - 1], outline=COLORS["corrected"], width=w)
    labels = []
    for mr in range(H // MODULE):
        for mc in range(W // MODULE):
            name = f"{SECTION_COLUMNS[mc]}{mr + 1}"
            labels.append(name)
            tx, ty = x0 + mc * MODULE * px + 3, y0 + mr * MODULE * px + 2
            bx0, by0, bx1, by1 = d.textbbox((tx, ty), name, font=small)
            d.rectangle([bx0 - 2, by0 - 1, bx1 + 2, by1 + 1], fill=COLORS["board"])   # legible on white land
            write((tx, ty), name, "section", small)

    if ticks:  # row and column numbers every 8 studs, tick marks every 4
        for c in range(0, W, 4):
            tx = x0 + c * px + px // 2
            d.line([(tx, y0 - (px // 2 if c % 8 else px)), (tx, y0 - 2)], fill=COLORS["muted"], width=1)
            if c % 8 == 0:
                d.text((tx - px // 2, y0 - 2 * px), str(c), fill=COLORS["text"], font=small)
        for r in range(0, H, 4):
            ty = y0 + r * px + px // 2
            d.line([(x0 - (px // 2 if r % 8 else px), ty), (x0 - 2, ty)], fill=COLORS["muted"], width=1)
            if r % 8 == 0:
                d.text((pad, ty - px // 2), str(r), fill=COLORS["text"], font=small)
        d.text((x0 + W * px + 4, y0 - 2 * px), "col", fill=COLORS["muted"], font=small)
        d.text((pad, y0 + H * px + 2), "row", fill=COLORS["muted"], font=small)

    # legend, two columns
    ly = y0 + H * px + pad
    sw = max(10, px)
    colw = (W * px) // 2
    for i, (key, shape, label) in enumerate(legend):
        lx = x0 + (i % 2) * colw
        yy = ly + (i // 2) * line_h
        box = [lx, yy, lx + sw - 1, yy + sw - 1]
        if shape == "round":
            d.rectangle(box, fill=COLORS["board"])
            d.ellipse([box[0] + 1, box[1] + 1, box[2] - 1, box[3] - 1], fill=COLORS[key])
        elif shape == "square":
            d.rectangle(box, fill=COLORS["board"])
            d.rectangle([box[0] + 1, box[1] + 1, box[2] - 1, box[3] - 1], fill=COLORS[key])
        elif shape == "flag_water":
            d.rectangle(box, fill=COLORS["board"])
            d.ellipse([box[0] + 1, box[1] + 1, box[2] - 1, box[3] - 1], fill=COLORS["inland_water"])
            d.rectangle([box[0] + 2, box[1] + 2, box[2] - 2, box[3] - 2], outline=COLORS["flag_water"], width=1)
        else:
            d.rectangle(box, outline=COLORS[key], width=2)
        write((lx + sw + 8, yy - 1), label)
    fy = ly + line_h * ((len(legend) + 1) // 2) + pad // 2
    write((x0, fy), DISCLAIMER, "text")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return SheetInfo(path=path, size=img.size, origin=(x0, y0), px=px, section_labels=labels, text=text)


# --- the flags list -----------------------------------------------------------------------

def _sections(rows: np.ndarray, cols: np.ndarray) -> List[str]:
    out = sorted({(int(c) // MODULE, int(r) // MODULE) for r, c in zip(rows, cols)})
    return [f"{SECTION_COLUMNS[mc]}{mr + 1}" for mc, mr in out]


def flags_document(template_id: str, flags: Sequence[Dict[str, Any]], *, classes: np.ndarray,
                   lat: Optional[np.ndarray] = None, lon: Optional[np.ndarray] = None, of: str,
                   generated_on: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The flags list: rules, counts by reason, the water groups (largest first, with their mean
    location and sections) and every flag (data-model.md ReviewFlag)."""
    from .generate import spherical_mean

    groups = []
    for g in water_groups(classes):
        rows, cols = g[:, 0], g[:, 1]
        entry: Dict[str, Any] = {"size": int(len(g)), "rows": [int(rows.min()), int(rows.max())],
                                 "cols": [int(cols.min()), int(cols.max())], "sections": _sections(rows, cols)}
        if lat is not None and lon is not None:
            la, lo = np.asarray(lat)[rows, cols], np.asarray(lon)[rows, cols]
            ok = np.isfinite(la) & np.isfinite(lo)
            if ok.any():
                mlat, mlon = spherical_mean(la[ok], lo[ok])
                entry["mean_location"] = {"lat": round(mlat, 2), "lon": round(mlon, 2)}
        groups.append(entry)
    doc: Dict[str, Any] = {
        "format_version": "1",
        "template_id": template_id,
        "of": of,
        "generated_on": generated_on,
        "rules": {FLAG_LAND_SHARE: ("on-globe studs whose share of on-globe subsamples above 0 m is from 0.4 "
                                    "to 0.6"),
                  FLAG_WATER: ("ocean studs in a 4-connected group other than the largest one, the main "
                               "ocean (below-sea-level basins)")},
        "counts": flag_counts(flags),
    }
    if extra:
        doc.update(extra)
    doc["groups"] = groups
    doc["flags"] = [dict(f) for f in flags]
    doc["disclaimer"] = DISCLAIMER
    return doc


def flags_text(doc: Dict[str, Any]) -> str:
    """Two-space JSON with one flag and one group per line."""
    lines = ["{"]
    keys = list(doc)
    for i, k in enumerate(keys):
        v = doc[k]
        end = "," if i < len(keys) - 1 else ""
        if k in ("flags", "groups") and isinstance(v, list) and v:
            rows = [f"    {json.dumps(x, ensure_ascii=False)}" for x in v]
            lines.append(f'  {json.dumps(k)}: [\n' + ",\n".join(rows) + f"\n  ]{end}")
        else:
            body = json.dumps(v, ensure_ascii=False, indent=2).replace("\n", "\n  ")
            lines.append(f"  {json.dumps(k)}: {body}{end}")
    lines.append("}")
    return "\n".join(lines) + "\n"

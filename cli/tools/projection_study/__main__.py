"""Projection study commands. Run from cli/: PYTHONPATH=tools python -m projection_study --help."""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import click
import numpy as np

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."


def _elevation(dataset_path, cache_dir):
    from lego_image_processor.datasets import get_entry, read_dataset, resolve, verify
    from lego_image_processor.datasets.cache import DatasetError

    from .raster import Elevation

    entry = get_entry("etopo2022-surface-10m")
    try:
        if dataset_path:
            verify(entry, dataset_path)
            path = dataset_path
        else:
            path = resolve(entry, cache_dir)
    except DatasetError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(getattr(exc, "exit_code", 1))
    g = read_dataset(entry, path, "z")
    return Elevation(g.values, g.lat, g.lon)


def _out_dir(out, cache_dir) -> Path:
    if out:
        d = Path(out)
    else:
        from lego_image_processor.datasets.cache import cache_root

        d = (Path(cache_dir) if cache_dir else cache_root()) / "projection-study"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _kit_counts():
    from lego_image_processor.maps.projection import PROJECTION_PATH

    inv = json.loads((PROJECTION_PATH.parent / "kit_31203_inventory.json").read_text(encoding="utf-8"))
    land = sum(e["quantity"] for e in inv["elements"] if e.get("role") == "land")
    ocean = sum(e["quantity"] for e in inv["elements"] if e.get("role") == "ocean")
    return land, ocean


_common = [
    click.option("--dataset", "dataset_path", type=click.Path(path_type=Path, dir_okay=False),
                 help="ETOPO 2022 10-arc-minute DODS file (default: the verified cached copy)."),
    click.option("--cache-dir", type=click.Path(path_type=Path), help="Cache root (default: per-user cache)."),
    click.option("--out", type=click.Path(path_type=Path, file_okay=False),
                 help="Output folder (default: <cache>/projection-study, outside the repository)."),
]


def common(f):
    for opt in reversed(_common):
        f = opt(f)
    return f


@click.group()
def main() -> None:
    """Rasterise world projections onto boards of 16×16 modules (maintainer research tool)."""
    warnings.filterwarnings("ignore", category=RuntimeWarning)


@main.command()
@common
def calibrate(dataset_path, cache_dir, out) -> None:
    """Classify the kit grid from ETOPO and compare it with the kit's land/sea mask."""
    from lego_image_processor.maps.build import land_mask_array

    from .raster import Proj, rasterise

    elev = _elevation(dataset_path, cache_dir)
    r = rasterise(Proj("kit", None, "cylindrical"), elev, 128, 80, ss=4)
    land = r.landfrac >= 0.5
    kit = land_mask_array()
    click.echo(f"data land {int(land.sum())}  kit land {int(kit.sum())}  agreement {(land == kit).mean():.3f}")
    click.echo(DISCLAIMER)


@main.command()
@common
def survey(dataset_path, cache_dir, out) -> None:
    """Fill, land and ocean counts for every surveyed projection on a dozen boards."""
    from .candidates import BOARDS, SURVEY
    from .raster import Proj, classify, rasterise

    elev = _elevation(dataset_path, cache_dir)
    results = []
    for pr in SURVEY:
        p = Proj(*pr)
        rows = []
        for mw, mh in ([(8, 5)] if pr.spec is None else BOARDS):
            W, H = mw * 16, mh * 16
            r = rasterise(p, elev, W, H, ss=2)
            on, land, ocean = classify(r.cover, r.landfrac)
            rows.append({"modules": [mw, mh], "W": W, "H": H, "on": int(on.sum()), "fill": float(on.mean()),
                         "land": int(land.sum()), "ocean": int(ocean.sum())})
        results.append({"name": pr.name, "spec": pr.spec, "family": pr.family, "clip": pr.clip,
                        "aspect": None if pr.spec is None else p.aspect, "boards": rows})
        click.echo(f"{pr.name:32s} aspect={'' if pr.spec is None else f'{p.aspect:.3f}'}")
        for b in rows:
            click.echo(f"    {b['modules']} {b['W']:3d}x{b['H']:3d} fill={b['fill']:.3f} "
                       f"land={b['land']:5d} ocean={b['ocean']:5d}")
    d = _out_dir(out, cache_dir)
    (d / "boards.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    click.echo(f"Wrote {d / 'boards.json'}")


@main.command()
@common
def candidates(dataset_path, cache_dir, out) -> None:
    """Detailed metrics and a preview image for each shortlisted projection and board."""
    import math

    from .candidates import CANDIDATES
    from .raster import Proj, classify, module_stats, rasterise, rim_cells
    from .render import render

    elev = _elevation(dataset_path, cache_dir)
    kit_land, kit_ocean = _kit_counts()
    d = _out_dir(out, cache_dir)
    recs = []
    for key, pr, (mw, mh) in CANDIDATES:
        p = Proj(*pr)
        W, H = mw * 16, mh * 16
        r = rasterise(p, elev, W, H, ss=4)
        on, land, ocean = classify(r.cover, r.landfrac)
        if pr.spec is None:
            on[:] = True
            land = r.landfrac >= 0.5
            ocean = ~land
        full, partial, empty = module_stats(on)
        a = r.area_km2[on & np.isfinite(r.area_km2)]
        p10, p50, p90 = np.percentile(a, [10, 50, 90]) if a.size else (np.nan,) * 3
        eq = None
        if pr.family != "square":
            if pr.spec is None:
                eq = W
            else:
                x0, x1, y0, y1 = p.extent
                row = int(math.floor(H / 2 - (0 - (y0 + y1) / 2) * r.scale))
                eq = int(on[min(max(row, 0), H - 1)].sum())
        rec = dict(key=key, name=pr.name, spec=pr.spec, family=pr.family, clip=pr.clip, modules=[mw, mh],
                   W=W, H=H, on=int(on.sum()), margin=int((~on).sum()), fill=float(on.mean()),
                   land=int(land.sum()), ocean=int(ocean.sum()), land_share=float(land.sum() / max(on.sum(), 1)),
                   rim=int(rim_cells(on).sum()), modules_full=full, modules_partial=partial,
                   modules_empty=empty, km2_p10=float(p10), km2_p50=float(p50), km2_p90=float(p90),
                   area_ratio=float(p90 / p10), equator_studs=eq,
                   aspect=None if pr.spec is None else p.aspect,
                   land_vs_kit=int(land.sum()) - kit_land, ocean_vs_kit=int(ocean.sum()) - kit_ocean)
        recs.append(rec)
        render(d / f"{key}.png", on, land, r.depth, px=7)
        click.echo(f"{key:18s} {W}x{H} fill={rec['fill']:.3f} land={rec['land']:5d} ocean={rec['ocean']:5d} "
                   f"margin={rec['margin']:5d} rim={rec['rim']:4d} modules={full}/{partial}/{empty} "
                   f"area p90/p10={rec['area_ratio']:.2f}")
    (d / "candidates.json").write_text(json.dumps(recs, indent=1), encoding="utf-8")
    click.echo(f"Wrote {d / 'candidates.json'} and previews")


@main.command("spilhaus-zoom")
@common
def spilhaus_zoom(dataset_path, cache_dir, out) -> None:
    """Land share of Spilhaus on 6×6 modules as the square is cropped tighter."""
    from .raster import Proj, classify, rasterise
    from .render import render

    elev = _elevation(dataset_path, cache_dir)
    d = _out_dir(out, cache_dir)
    p = Proj("Spilhaus", "+proj=spilhaus", "square")
    x0, x1, y0, y1 = p.extent
    for z in (1.0, 1.2, 1.4, 1.6):
        cx, cy, hw, hh = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 / z, (y1 - y0) / 2 / z
        p.extent = (cx - hw, cx + hw, cy - hh, cy + hh)
        r = rasterise(p, elev, 96, 96, ss=4)
        on, land, ocean = classify(r.cover, r.landfrac)
        click.echo(f"crop {z}: land={int(land.sum())} ocean={int(ocean.sum())} land share={land.sum() / on.sum():.2f}")
        if z == 1.4:
            render(d / "spilhaus-6x6-zoom.png", on, land, r.depth, px=7)
        p.extent = (x0, x1, y0, y1)


@main.command()
@common
@click.option("--key", default="winkel-kit", show_default=True, help="Candidate key.")
def corners(dataset_path, cache_dir, out, key) -> None:
    """Room for a corner plaque in the margin: the largest block of margin studs in each board quadrant."""
    from .candidates import candidate
    from .raster import Proj, classify, largest_rectangle, rasterise, rim_cells
    from .render import render

    elev = _elevation(dataset_path, cache_dir)
    d = _out_dir(out, cache_dir)
    c = candidate(key)
    mw, mh = c.modules
    W, H = mw * 16, mh * 16
    r = rasterise(Proj(*c.projection), elev, W, H, ss=4)
    on, land, _ = classify(r.cover, r.landfrac)
    rim = rim_cells(on)
    free = ~on & ~rim
    click.echo(f"{key}: margin {int((~on).sum())} studs, outline ring {int(rim.sum())}, inside the ring {int(free.sum())}")
    out_rects = {}
    for name, rs, cs in (("top-left", slice(0, H // 2), slice(0, W // 2)),
                         ("top-right", slice(0, H // 2), slice(W // 2, W)),
                         ("bottom-left", slice(H // 2, H), slice(0, W // 2)),
                         ("bottom-right", slice(H // 2, H), slice(W // 2, W))):
        row, col, h, w = largest_rectangle(free[rs, cs])
        out_rects[name] = {"row": row + rs.start, "col": col + cs.start, "height": h, "width": w}
        click.echo(f"  {name:12s} largest block {w:3d} x {h:2d} studs at row {row + rs.start}, col {col + cs.start}")
    (d / f"{key}-corners.json").write_text(json.dumps(out_rects, indent=1), encoding="utf-8")
    render(d / f"{key}-square-margin.png", on, land, r.depth, px=8, rim=rim, grid=False, square_margin=True)
    click.echo(f"Wrote {d / (key + '-corners.json')} and {d / (key + '-square-margin.png')}")


@main.command()
@common
def sheet(dataset_path, cache_dir, out) -> None:
    """Winkel tripel art treatment (outline ring) and a contact sheet of the main candidates."""
    from .candidates import WINKEL
    from .raster import Proj, classify, rasterise, rim_cells
    from .render import contact_sheet, render

    elev = _elevation(dataset_path, cache_dir)
    d = _out_dir(out, cache_dir)
    r = rasterise(Proj("Winkel tripel", WINKEL, "compromise"), elev, 128, 80, ss=4)
    on, land, _ = classify(r.cover, r.landfrac)
    rim = rim_cells(on)
    render(d / "winkel-kit-neatline.png", on, land, r.depth, px=8, rim=rim, grid=False)
    click.echo(f"outline studs {int(rim.sum())}, other margin studs {int((~on & ~rim).sum())}")
    recs_path = d / "candidates.json"
    if not recs_path.exists():
        click.echo("Run `candidates` first for the contact sheet.", err=True)
        sys.exit(1)
    recs = {x["key"]: x for x in json.loads(recs_path.read_text(encoding="utf-8"))}
    order = ["kit", "cea-kit", "mercator-kit", "winkel-kit", "robinson-8x4", "equal-earth-8x4",
             "mollweide-8x4", "goode-9x4", "spilhaus-6x6"]
    tiles = []
    for k in order:
        x = recs[k]
        title = "Kit grid (as built)" if k == "kit" else x["name"].split(" (")[0]
        sub = f"{x['modules'][0]}×{x['modules'][1]} modules · {x['W']}×{x['H']} · {100 * x['fill']:.0f}% on globe"
        tiles.append((d / f"{k}.png", title, sub, (x["W"], x["H"])))
    size = contact_sheet(d / "contact-sheet.png", tiles)
    click.echo(f"Wrote {d / 'contact-sheet.png'} {size}")


if __name__ == "__main__":
    main()

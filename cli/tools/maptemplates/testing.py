"""Test helpers for map templates (feature 016, T025): numpy only, no pyproj, no dataset.

Shared by the CLI tests (``pythonpath = ["tools"]``) and the web tests (``cli/tools`` on
``sys.path``, T084):

- ``write_synthetic_template(dir)`` writes a confirmed synthetic ``winkel-tripel`` template and its
  ice file. The template is 128 x 80, the size the loader requires. Its outline and check points
  come from ``lego_image_processor.templates.winkel`` (the run-time forward formula), its stud
  locations from a Newton inverse of that formula (``inverse``; the package has no inverse), its
  land from a fixed rule on the locations (not ETOPO), and it has a test confirmation. The ice file
  holds land ice on land studs south of 60° S and sea ice on ocean studs poleward of 75°, and
  records the template's layout digest. The committed copies are
  ``cli/tests/fixtures/templates/`` (regenerate with
  ``PYTHONPATH=tools python -m maptemplates.testing tests/fixtures/templates`` from ``cli/``).
- ``confirmed_copy(src_dir, dst_dir, date)`` copies a template (and its ice file, if any) with the
  test confirmation ``{"role": "project owner", "date": date}``; the layout digest leaves the
  confirmation out, so the copied ice file stays valid.
- ``use_template_dir(dir)`` points ``lego_image_processor.templates.TEMPLATE_DIR`` at ``dir``.

Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import contextlib
import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import numpy as np

from lego_image_processor.datasets import registry
from lego_image_processor.templates import winkel
from lego_image_processor.templates.board import board_counts
from lego_image_processor.templates.digest import layout_sha256
from lego_image_processor.templates.geometry import from_board

from .document import ice_to_text, round_location, to_text

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
TEMPLATE_ID = "winkel-tripel"
DATE = "2026-11-23"
WIDTH, HEIGHT, SUPERSAMPLE = 128, 80, 4
TEST_CONFIRMATION_ROLE = "project owner"
GENERATOR = "cli/tools/maptemplates"


# --- the inverse of the forward formula (tests only) ---------------------------------------

def inverse(x, y, lat_1: float = winkel.LAT_1, lon_0: float = winkel.LON_0,
            iterations: int = 60) -> Tuple[np.ndarray, np.ndarray]:
    """(lat, lon) in degrees of projected points inside the outline, by Newton iteration on
    ``winkel.forward_radians`` (central-difference Jacobian). Raises if a point does not converge
    to 1e-12."""
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    c1 = math.cos(math.radians(lat_1))
    lam = np.clip(2.0 * x / (1.0 + c1), -math.pi, math.pi)
    phi = np.clip(y, -math.pi / 2, math.pi / 2)
    h = 1e-7
    f = winkel.forward_radians
    for _ in range(iterations):
        fx, fy = f(lam, phi, c1)
        ex, ey = fx - x, fy - y
        if x.size == 0 or max(np.max(np.abs(ex)), np.max(np.abs(ey))) < 1e-15:
            break
        x1, y1 = f(lam + h, phi, c1)
        x2, y2 = f(lam - h, phi, c1)
        x3, y3 = f(lam, phi + h, c1)
        x4, y4 = f(lam, phi - h, c1)
        a, b = (x1 - x2) / (2 * h), (x3 - x4) / (2 * h)   # dx/dλ, dx/dφ
        c, d = (y1 - y2) / (2 * h), (y3 - y4) / (2 * h)   # dy/dλ, dy/dφ
        det = a * d - b * c
        lam = np.clip(lam - (ex * d - ey * b) / det, -math.pi, math.pi)
        phi = np.clip(phi - (ey * a - ex * c) / det, -math.pi / 2, math.pi / 2)
    fx, fy = f(lam, phi, c1)
    if x.size and max(np.max(np.abs(fx - x)), np.max(np.abs(fy - y))) > 1e-12:
        raise ValueError("inverse did not converge (is every point inside the outline?)")
    lon = (np.degrees(lam) + lon_0 + 180.0) % 360.0 - 180.0
    return np.degrees(phi), lon


def spherical_mean(lat: np.ndarray, lon: np.ndarray) -> Tuple[float, float]:
    """The normalised mean of unit vectors (degrees in and out; lon in -180..180)."""
    la, lo = np.radians(lat), np.radians(lon)
    v = np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)]).mean(axis=1)
    v /= np.linalg.norm(v)
    return float(np.degrees(np.arcsin(v[2]))), float(np.degrees(np.arctan2(v[1], v[0])))


# --- the synthetic template ----------------------------------------------------------------

def _land_rule(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """Synthetic land: everything south of 66° S, and wavy bands between 72° S and 72° N."""
    with np.errstate(invalid="ignore"):
        bands = np.sin(np.radians(2.0 * lon + 40.0)) * np.cos(np.radians(1.5 * lat)) > 0.45
        return (lat <= -66.0) | ((np.abs(lat) <= 72.0) & bands)


def _packaged_entry(dataset_id: str):
    return registry.load_registry(registry.DATA_DIR / "datasets.json").get(dataset_id)


def _dataset_block(dataset_id: str) -> Dict[str, Any]:
    e = _packaged_entry(dataset_id)
    return {"id": e.id, "version": e.version, "url": e.url, "sha256": e.sha256, "citation": e.citation,
            "license": e.license}


def synthetic_layout() -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Any]]:
    """(on_globe, lat, lon, fit) of the synthetic board: 4 x 4 subsamples per stud, on the globe
    when at least half lie inside the outline; locations are the inverse of the stud centre, or
    the spherical mean of the on-globe subsamples when the centre lies outside the outline."""
    W, H, ss = WIDTH, HEIGHT, SUPERSAMPLE
    fit = winkel.fit(W, H)
    off = (np.arange(ss) + 0.5) / ss
    sub_c = (np.arange(W)[:, None] + off[None, :]).ravel()
    sub_r = (np.arange(H)[:, None] + off[None, :]).ravel()
    X, Y = from_board(*np.meshgrid(sub_c, sub_r), fit, W, H)
    inside = winkel.outline_contains(X, Y)

    def block(a):
        return a.reshape(H, ss, W, ss).swapaxes(1, 2).reshape(H, W, ss * ss)

    on = block(inside).mean(axis=2) >= 0.5
    Xc, Yc = from_board(*np.meshgrid(np.arange(W) + 0.5, np.arange(H) + 0.5), fit, W, H)
    centre_in = winkel.outline_contains(Xc, Yc)
    lat = np.full((H, W), np.nan)
    lon = np.full((H, W), np.nan)
    sel = on & centre_in
    lat[sel], lon[sel] = inverse(Xc[sel], Yc[sel])
    bx, by, bin_ = block(X), block(Y), block(inside)
    for r, c in zip(*np.nonzero(on & ~centre_in)):
        k = bin_[r, c]
        la, lo = inverse(bx[r, c][k], by[r, c][k])
        lat[r, c], lon[r, c] = spherical_mean(la, lo)
    return on, lat, lon, fit


def synthetic_document(generated_on: str = DATE, confirmed_on: Optional[str] = DATE) -> Dict[str, Any]:
    """The synthetic ``winkel-tripel`` template document (see the module docstring)."""
    on, lat, lon, fit = synthetic_layout()
    lat_r = np.array([[np.nan if not on[r, c] else round_location(lat[r, c]) for c in range(WIDTH)]
                      for r in range(HEIGHT)], dtype=float)
    lon_r = np.array([[np.nan if not on[r, c] else round_location(lon[r, c]) for c in range(WIDTH)]
                      for r in range(HEIGHT)], dtype=float)
    land = on & _land_rule(lat_r, lon_r)
    classes = np.where(land, "L", np.where(on, "O", "M"))
    # One recorded correction, applied after generation: the first land stud in row-major order
    # between the equator and 30° N becomes ocean.
    cand = np.flatnonzero((classes == "L").ravel() & (lat_r.ravel() > 0) & (lat_r.ravel() < 30))
    r0, c0 = divmod(int(cand[0]), WIDTH)
    classes[r0, c0] = "O"
    corrections = [{"row": r0, "col": c0, "class": "ocean",
                    "reason": "synthetic test correction (tools/maptemplates/testing.py)"}]

    def rows(a):
        return [[None if not on[r, c] else float(a[r, c]) for c in range(WIDTH)] for r in range(HEIGHT)]

    class_rows = ["".join(row) for row in classes]
    return {
        "format_version": "1",
        "id": TEMPLATE_ID,
        "title": "Winkel tripel (synthetic test template)",
        "description": ("Synthetic test template for the test suite, not a map of the Earth: the Winkel tripel "
                        "outline and stud locations from the numpy forward formula and a Newton inverse, land "
                        "from a fixed rule on the locations instead of ETOPO 2022."),
        "projection": {"name": winkel.NAME, "proj": winkel.proj_string(), "lat_1": winkel.LAT_1,
                       "lon_0": winkel.LON_0, "citation": winkel.CITATION, "fit": fit,
                       "check_points": winkel.check_points()},
        "board": {"modules": [8, 5], "module": 16, "width": WIDTH, "height": HEIGHT, "pitch_mm": 8.0},
        "parts": {"land": "6141", "ocean": "98138", "margin": "3070b"},
        "frame": {"kit": "31203", "arrangements": ["A"], "source": "kit_31203_arrangements.json"},
        "classes": class_rows,
        "locations": {"lat": rows(lat_r), "lon": rows(lon_r)},
        "counts": board_counts(class_rows),
        "source": {
            "generator": GENERATOR + "/testing.py (synthetic test template)",
            "generated_on": generated_on,
            "dataset": _dataset_block("etopo2022-surface-10m"),
            "method": {"supersample": SUPERSAMPLE, "on_globe_share": 0.5, "land_share": 0.5,
                       "land_rule": ("synthetic: south of 66 S, or within 72 degrees of the equator where "
                                     "sin(2 lon + 40) cos(1.5 lat) > 0.45 (not ETOPO; the dataset entry only "
                                     "gives the file its contract shape)"),
                       "round_trip_tolerance": 1e-6,
                       "location_rule": ("inverse of the stud centre (Newton on the numpy forward formula); "
                                         "spherical mean of the on-globe subsamples when the centre lies outside "
                                         "the outline")},
            "software": {"pyproj": "not used (synthetic test template)",
                         "proj": "not used (synthetic test template)"},
            "disclaimer": DISCLAIMER,
        },
        "corrections": corrections,
        "confirmation": (None if confirmed_on is None else
                         {"role": TEST_CONFIRMATION_ROLE, "date": confirmed_on}),
        "disclaimer": DISCLAIMER,
    }


def synthetic_ice_document(doc: Dict[str, Any], generated_on: str = DATE) -> Dict[str, Any]:
    """Ice regions of a template document by the synthetic rules: land ice on L studs south of
    60° S, sea ice on O studs poleward of 75° (board coordinates, row-major)."""
    classes = np.array([list(r) for r in doc["classes"]])
    lat = np.array([[np.nan if v is None else v for v in row] for row in doc["locations"]["lat"]], dtype=float)
    with np.errstate(invalid="ignore"):
        land = (classes == "L") & (lat < -60.0)
        sea = (classes == "O") & (np.abs(lat) > 75.0)

    def cells(m):
        return [int(i) for i in np.flatnonzero(m.ravel())]

    return {
        "format_version": "1",
        "template_id": doc["id"],
        "grid": {"width": WIDTH, "height": HEIGHT, "coordinates": "board, row-major index = row * 128 + column"},
        "source": {
            "title": f"Ice-covered studs of the synthetic {doc['id']} test template (feature 016 test fixture)",
            "generator": GENERATOR + "/testing.py (synthetic test template)",
            "generated_on": generated_on,
            "template_layout_sha256": layout_sha256(doc),
            "land_ice": {"rule": "synthetic: land studs whose location lies south of 60 S"},
            "sea_ice": {"rule": ("synthetic: ocean studs whose location lies poleward of 75 degrees (not ERSST; the "
                                 "dataset entry only gives the file its contract shape)"),
                        "dataset": _dataset_block("ersst-v5-ltm-1991-2020")},
            "disclaimer": DISCLAIMER,
        },
        "land_ice": {"count": int(land.sum()), "cells": cells(land)},
        "sea_ice": {"count": int(sea.sum()), "cells": cells(sea)},
    }


def write_synthetic_template(directory, generated_on: str = DATE) -> List[Path]:
    """Write ``winkel-tripel.json`` and ``winkel-tripel-ice.json`` into ``directory``."""
    d = Path(directory)
    d.mkdir(parents=True, exist_ok=True)
    doc = synthetic_document(generated_on=generated_on)
    t = d / f"{TEMPLATE_ID}.json"
    i = d / f"{TEMPLATE_ID}-ice.json"
    t.write_text(to_text(doc), encoding="utf-8")
    i.write_text(ice_to_text(synthetic_ice_document(doc, generated_on)), encoding="utf-8")
    return [t, i]


# --- copies and the template directory -----------------------------------------------------

def confirmed_copy(src_dir, dst_dir, date: str, template_id: str = TEMPLATE_ID) -> Path:
    """Copy ``<template_id>.json`` (with the test confirmation) and ``<template_id>-ice.json`` (as
    is, when present) from ``src_dir`` to ``dst_dir``; return the copied template's path."""
    src, dst = Path(src_dir), Path(dst_dir)
    dst.mkdir(parents=True, exist_ok=True)
    doc = json.loads((src / f"{template_id}.json").read_text(encoding="utf-8"))
    doc["confirmation"] = {"role": TEST_CONFIRMATION_ROLE, "date": date}
    out = dst / f"{template_id}.json"
    out.write_text(to_text(doc), encoding="utf-8")
    ice = src / f"{template_id}-ice.json"
    if ice.exists():
        shutil.copyfile(ice, dst / ice.name)
    return out


def unconfirmed_copy(src_dir, dst_dir, template_id: str = TEMPLATE_ID) -> Path:
    """Copy ``<template_id>.json`` without its confirmation and ``<template_id>-ice.json`` (as is,
    when present) from ``src_dir`` to ``dst_dir``; return the copied template's path. Tests of the
    refusal to build on an unconfirmed template use it, since the package file is confirmed."""
    src, dst = Path(src_dir), Path(dst_dir)
    dst.mkdir(parents=True, exist_ok=True)
    doc = json.loads((src / f"{template_id}.json").read_text(encoding="utf-8"))
    doc["confirmation"] = None
    out = dst / f"{template_id}.json"
    out.write_text(to_text(doc), encoding="utf-8")
    ice = src / f"{template_id}-ice.json"
    if ice.exists():
        shutil.copyfile(ice, dst / ice.name)
    return out


@contextlib.contextmanager
def use_template_dir(directory) -> Iterator[Path]:
    """Point ``lego_image_processor.templates.TEMPLATE_DIR`` at ``directory`` for the block."""
    import lego_image_processor.templates as templates

    before = templates.TEMPLATE_DIR
    templates.TEMPLATE_DIR = Path(directory)
    try:
        yield Path(directory)
    finally:
        templates.TEMPLATE_DIR = before


if __name__ == "__main__":  # PYTHONPATH=tools python -m maptemplates.testing OUT_DIR
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests/fixtures/templates")
    for p in write_synthetic_template(out_dir):
        print(f"wrote {p}")
    print(DISCLAIMER)

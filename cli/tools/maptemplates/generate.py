"""Generate a template's layout from the pinned ETOPO 2022 file (feature 016, FR-017; research R2,
R4, R5).

Built on the projection study (``projection_study.raster``): ``Proj`` (pyproj forward and a
round-trip-checked inverse), ``rasterise`` and ``classify``, with the projection's exact extent from
``lego_image_processor.templates.winkel`` instead of the study's sampled one (research R2). The
method is the study's: 4 x 4 subsamples per stud, each inverse-projected and kept only if the
forward round trip returns within 1e-6 of the extent; a stud is on the globe when at least half its
subsamples are, and land when at least half of those have ETOPO elevation > 0 m (nearest cell of
the 10-arc-minute grid); the rest is margin.

Stud locations (``LOCATION_RULE``): the inverse of the stud centre; when the centre lies outside
the outline (its round trip fails), the spherical mean of the stud's on-globe subsamples. Every stud
with at least one on-globe subsample gets one, so a correction may turn such a margin stud into
land or ocean.

Review flags (data-model.md ReviewFlag .row, .col, .class, .land_share, .reason, .group_size):
on-globe studs with a land share from 40 % to 60 % (``FLAG_LAND_SHARE``), and ocean studs in a
4-connected group other than the largest, the main ocean (``FLAG_WATER``; below-sea-level basins
such as the Caspian Sea).

``build_document`` writes the template document (data-model.md Template.source: generator,
generated_on, dataset, method, software, disclaimer; TemplateCorrection .row, .col, .class,
.reason; Confirmation .role, .date). pyproj is imported only when a Winkel projection is built
(``winkel_proj``), so everything else here runs without it. Not affiliated with or endorsed by
The LEGO Group.
"""

from __future__ import annotations

import datetime as _dt
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy import ndimage

from lego_image_processor.templates import (BOARD, DISCLAIMER, FRAME, GENERATOR_PREFIX, TEMPLATE_PARTS,
                                            winkel)
from lego_image_processor.templates.board import board_counts
from projection_study.raster import Proj, classify, rasterise

from . import document

SUPERSAMPLE = 4
ON_GLOBE_SHARE = 0.5
LAND_SHARE = 0.5
ROUND_TRIP_TOLERANCE = 1e-6   # projection_study.raster.Proj.inverse: 1e-6 of the extent's size
LAND_RULE = "elevation > 0 m"
LOCATION_RULE = ("inverse of the stud centre; the spherical mean of the stud's on-globe subsamples "
                 "when the centre lies outside the outline")
GENERATOR = GENERATOR_PREFIX
FLAG_LAND_SHARE = "land share 40-60%"
FLAG_WATER = "water not connected to the ocean"
FLAG_LOW, FLAG_HIGH = 0.4, 0.6
CLASS_NAMES = {"L": "land", "O": "ocean", "M": "margin"}
PACKAGED_DATASET_ID = "etopo2022-surface-10m"


class ToolError(Exception):
    """A step the tool cannot take; ``exit_code`` follows contracts/template-file.md."""

    exit_code = 1


class DatasetUnavailable(ToolError):
    """The pinned dataset is missing or its checksum differs (exit 4)."""

    exit_code = 4


@dataclass(frozen=True)
class TemplateSpec:
    """What the tool knows about a template it can generate."""

    id: str
    title: str
    description: str
    projection: str       # templates.winkel.NAME
    lat_1: float
    lon_0: float
    dataset_id: str

    @property
    def proj(self) -> str:
        return winkel.proj_string(self.lat_1, self.lon_0)


SPECS: Dict[str, TemplateSpec] = {
    "winkel-tripel": TemplateSpec(
        id="winkel-tripel",
        title="Winkel tripel on the kit board",
        description=("The Winkel tripel projection (standard parallel 50.4598 degrees, central meridian "
                     "11.1 degrees E, the kit board's centre as hung in combination A) fitted inside the kit "
                     "31203 board of 8 x 5 modules (128 x 80 studs). Land and ocean studs come from ETOPO "
                     "2022 (elevation above 0 m is land); studs off the globe are a margin of 1 x 1 square "
                     "tiles. Its frames cannot be re-hung (arrangement A only)."),
        projection=winkel.NAME, lat_1=winkel.LAT_1, lon_0=winkel.LON_0, dataset_id=PACKAGED_DATASET_ID),
}


def get_spec(template_id: str) -> TemplateSpec:
    try:
        return SPECS[template_id]
    except KeyError:
        raise KeyError(f"no generator for template {template_id!r}; known: {', '.join(SPECS)}") from None


# --- the projection -----------------------------------------------------------------------

class ExactProj(Proj):
    """The study's ``Proj`` with a given extent (the exact, published one) instead of the extent
    sampled on a 0.25 degree grid. ``transformer`` stands in for pyproj's (tests)."""

    def __init__(self, name: str, spec: str, extent: Sequence[float], transformer: Any = None):
        self.name, self.spec, self.family, self.clip = name, spec, "template", None
        if transformer is None:
            from pyproj import Transformer

            transformer = Transformer.from_crs("+proj=longlat +R=1 +no_defs", spec + " +R=1", always_xy=True)
        self.fwd = transformer
        self.extent = tuple(float(v) for v in extent)


def winkel_proj(spec: TemplateSpec) -> ExactProj:
    """Winkel tripel through pyproj, fitted with the exact extent (needs pyproj)."""
    proj = spec.proj
    if not proj.endswith(" +R=1"):
        raise ValueError(f"unexpected PROJ string {proj!r}")
    return ExactProj(spec.id, proj[: -len(" +R=1")], winkel.extent(spec.lat_1))


def software_versions() -> Dict[str, str]:
    import pyproj

    return {"pyproj": pyproj.__version__, "proj": pyproj.proj_version_str}


def board_fit(extent: Sequence[float], width: int, height: int) -> Dict[str, Any]:
    """The ``contain`` fit of an extent on a board, as ``rasterise`` places it (and
    ``winkel.fit`` writes it): studs per projected unit and the extent's centre."""
    x0, x1, y0, y1 = (float(v) for v in extent)
    return {"mode": "contain", "extent": [x0, x1, y0, y1], "scale": min(width / (x1 - x0), height / (y1 - y0)),
            "centre": [(x0 + x1) / 2, (y0 + y1) / 2]}


# --- generation ---------------------------------------------------------------------------

@dataclass
class Candidate:
    """A generated layout before corrections (all arrays height x width)."""

    width: int
    height: int
    fit: Dict[str, Any]
    cover: np.ndarray          # share of subsamples on the globe
    land_share: np.ndarray     # share of on-globe subsamples above 0 m
    classes: np.ndarray        # "L" / "O" / "M"
    lat: np.ndarray            # location of every stud with an on-globe subsample (NaN elsewhere)
    lon: np.ndarray
    any_on_globe: np.ndarray   # at least one on-globe subsample
    check_points: List[List[float]]

    @property
    def on_globe(self) -> np.ndarray:
        return self.classes != "M"


def spherical_mean(lat: np.ndarray, lon: np.ndarray) -> Tuple[float, float]:
    """The normalised mean of unit vectors (degrees in and out; lon in -180..180)."""
    la, lo = np.radians(np.asarray(lat, dtype=float)), np.radians(np.asarray(lon, dtype=float))
    v = np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)]).mean(axis=1)
    v /= np.linalg.norm(v)
    return float(np.degrees(np.arcsin(v[2]))), float(np.degrees(np.arctan2(v[1], v[0])))


def _board_points(fit: Dict[str, Any], width: int, height: int, cols: np.ndarray, rows: np.ndarray):
    s = fit["scale"]
    cx, cy = fit["centre"]
    return np.meshgrid((cols - width / 2) / s + cx, (height / 2 - rows) / s + cy)


def stud_locations(proj: Proj, fit: Dict[str, Any], width: int, height: int,
                   ss: int = SUPERSAMPLE) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(lat, lon, any_on_globe) per stud by ``LOCATION_RULE`` (NaN where no subsample is on the
    globe). Subsamples sit where ``rasterise`` puts them."""
    W, H = width, height
    off = (np.arange(ss) + 0.5) / ss
    xs, ys = _board_points(fit, W, H, (np.arange(W)[:, None] + off[None, :]).ravel(),
                           (np.arange(H)[:, None] + off[None, :]).ravel())
    s_lat, s_lon, s_ok = (a.reshape(xs.shape) for a in proj.inverse(xs.ravel(), ys.ravel()))

    def block(a):
        return a.reshape(H, ss, W, ss).swapaxes(1, 2).reshape(H, W, ss * ss)

    b_lat, b_lon, b_ok = block(s_lat), block(s_lon), block(s_ok)
    any_on = b_ok.any(axis=2)
    cxs, cys = _board_points(fit, W, H, np.arange(W) + 0.5, np.arange(H) + 0.5)
    c_lat, c_lon, c_ok = (a.reshape(cxs.shape) for a in proj.inverse(cxs.ravel(), cys.ravel()))
    lat = np.where(c_ok, c_lat, np.nan)
    lon = np.where(c_ok, c_lon, np.nan)
    for r, c in zip(*np.nonzero(any_on & ~c_ok)):
        k = b_ok[r, c]
        lat[r, c], lon[r, c] = spherical_mean(b_lat[r, c][k], b_lon[r, c][k])
    lat = np.where(any_on, lat, np.nan)
    lon = np.where(any_on, lon, np.nan)
    return lat, lon, any_on


def generate(proj: Proj, elevation: Any, width: int = BOARD["width"], height: int = BOARD["height"],
             ss: int = SUPERSAMPLE, check_lonlat: Sequence[Tuple[float, float]] = winkel.CHECK_POINTS) -> Candidate:
    """Classify every stud and locate it (FR-017)."""
    fit = board_fit(proj.extent, width, height)
    with warnings.catch_warnings():   # the study's mean ocean depth is empty on land studs (unused)
        warnings.simplefilter("ignore", RuntimeWarning)
        r = rasterise(proj, elevation, width, height, ss=ss, fit="contain")
    on, land, _ = classify(r.cover, r.landfrac, ON_GLOBE_SHARE)  # one threshold for both shares
    classes = np.where(land, "L", np.where(on, "O", "M")).astype("U1")
    lat, lon, any_on = stud_locations(proj, fit, width, height, ss)
    if np.isnan(lat[on]).any():
        raise ToolError("an on-globe stud has no location")
    lons = np.array([p[0] for p in check_lonlat], dtype=float)
    lats = np.array([p[1] for p in check_lonlat], dtype=float)
    x, y = proj.forward(lons, lats)
    pts = [[float(a), float(b), float(c), float(d)] for a, b, c, d in zip(lons, lats, x, y)]
    return Candidate(width=width, height=height, fit=fit, cover=r.cover, land_share=r.landfrac,
                     classes=classes, lat=lat, lon=lon, any_on_globe=any_on, check_points=pts)


# --- the pinned dataset and regeneration ---------------------------------------------------

def packaged_entry(dataset_id: str):
    """The entry in the packaged registry (``data/datasets.json``), whatever registry is active."""
    from lego_image_processor.datasets import registry

    return registry.load_registry(registry.DATA_DIR / "datasets.json").get(dataset_id)


def dataset_block(entry) -> Dict[str, str]:
    """``source.dataset`` of a template file."""
    return {"id": entry.id, "version": entry.version, "url": entry.url, "sha256": entry.sha256,
            "citation": entry.citation, "license": entry.license}


def elevation(entry, dataset_path=None, cache_dir=None):
    """The verified ETOPO grid as the study's nearest-cell ``Elevation`` (raises
    ``DatasetUnavailable`` when the file is missing or its checksum differs)."""
    from lego_image_processor.datasets import read_dataset, resolve, verify
    from lego_image_processor.datasets.cache import DatasetError
    from projection_study.raster import Elevation

    try:
        if dataset_path:
            if not Path(dataset_path).is_file():
                raise DatasetUnavailable(f"dataset {entry.id}: file not found: {dataset_path}")
            verify(entry, dataset_path)
            path = dataset_path
        else:
            path = resolve(entry, cache_dir)
    except DatasetError as exc:
        raise DatasetUnavailable(f"dataset {entry.id}: {exc}") from exc
    g = read_dataset(entry, path, "z")
    return Elevation(g.values, g.lat, g.lon)


@dataclass
class Regenerated:
    candidate: Candidate
    dataset: Dict[str, str]
    software: Dict[str, str]


def regenerate(spec: TemplateSpec, dataset_path=None, cache_dir=None) -> Regenerated:
    """Generate ``spec`` from the pinned dataset (the dataset is checked before pyproj is needed)."""
    entry = packaged_entry(spec.dataset_id)
    elev = elevation(entry, dataset_path, cache_dir)
    try:
        proj = winkel_proj(spec)
        software = software_versions()
    except ImportError as exc:
        raise ToolError("pyproj is needed to generate templates: poetry install --with maintainer "
                        f"(pyproj >=3.7,<3.8) ({exc})") from exc
    return Regenerated(candidate=generate(proj, elev), dataset=dataset_block(entry), software=software)


# --- review flags -------------------------------------------------------------------------

def water_groups(classes: np.ndarray) -> List[np.ndarray]:
    """Ocean groups (4-connected) other than the largest one, the main ocean; largest first, each
    an array of (row, col) in row-major order."""
    lab, n = ndimage.label(np.asarray(classes) == "O")
    if n <= 1:
        return []
    sizes = np.bincount(lab.ravel())[1:]
    main = int(np.argmax(sizes)) + 1
    groups = [np.argwhere(lab == k) for k in range(1, n + 1) if k != main]
    return sorted(groups, key=lambda g: (-len(g), tuple(g[0])))


def review_flags(classes: np.ndarray, land_share: Optional[np.ndarray] = None) -> List[Dict[str, Any]]:
    """The review flags (data-model.md ReviewFlag): land share 40-60 % on on-globe studs (when
    ``land_share`` is given), then the water groups not connected to the ocean."""
    classes = np.asarray(classes)
    flags: List[Dict[str, Any]] = []
    if land_share is not None:
        share = np.asarray(land_share, dtype=float)
        near = (classes != "M") & (share >= FLAG_LOW) & (share <= FLAG_HIGH)
        for r, c in np.argwhere(near):
            flags.append({"row": int(r), "col": int(c), "class": CLASS_NAMES[classes[r, c]],
                          "land_share": round(float(share[r, c]), 4), "reason": FLAG_LAND_SHARE,
                          "group_size": None})
    for g in water_groups(classes):
        for r, c in g:
            flags.append({"row": int(r), "col": int(c), "class": CLASS_NAMES[classes[r, c]],
                          "land_share": None if land_share is None else round(float(land_share[r, c]), 4),
                          "reason": FLAG_WATER, "group_size": int(len(g))})
    return flags


# --- the template document ----------------------------------------------------------------

def build_document(spec: TemplateSpec, candidate: Candidate, *, dataset: Dict[str, str],
                   software: Dict[str, str], generated_on: Optional[str] = None,
                   corrections: Sequence[Dict[str, Any]] = (),
                   confirmation: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """The template document (contracts/template-file.md) with ``corrections`` applied in order
    (``document.CorrectionError`` if one is invalid). ``confirmation`` is written as given."""
    if (candidate.width, candidate.height) != (BOARD["width"], BOARD["height"]):
        raise ValueError(f"templates are {BOARD['width']} x {BOARD['height']} studs for now")
    corrections = [dict(c) for c in corrections]
    classes, lat, lon = document.apply_corrections(candidate.classes, candidate.lat, candidate.lon,
                                                   candidate.any_on_globe, corrections)
    class_rows = ["".join(row) for row in classes]
    return {
        "format_version": "1",
        "id": spec.id,
        "title": spec.title,
        "description": spec.description,
        "projection": {"name": spec.projection, "proj": spec.proj, "lat_1": spec.lat_1, "lon_0": spec.lon_0,
                       "citation": winkel.CITATION, "fit": dict(candidate.fit),
                       "check_points": [list(p) for p in candidate.check_points]},
        "board": dict(BOARD),
        "parts": dict(TEMPLATE_PARTS),
        "frame": {k: (list(v) if isinstance(v, list) else v) for k, v in FRAME.items()},
        "classes": class_rows,
        "locations": {"lat": document.location_rows(lat, classes), "lon": document.location_rows(lon, classes)},
        "counts": board_counts(class_rows),
        "source": {
            "generator": GENERATOR,
            "generated_on": generated_on or _dt.date.today().isoformat(),
            "dataset": dict(dataset),
            "method": {"supersample": SUPERSAMPLE, "on_globe_share": ON_GLOBE_SHARE, "land_share": LAND_SHARE,
                       "land_rule": LAND_RULE, "round_trip_tolerance": ROUND_TRIP_TOLERANCE,
                       "location_rule": LOCATION_RULE},
            "software": dict(software),
            "disclaimer": DISCLAIMER,
        },
        "corrections": corrections,
        "confirmation": None if confirmation is None else dict(confirmation),
        "disclaimer": DISCLAIMER,
    }

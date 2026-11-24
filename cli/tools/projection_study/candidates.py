"""Projections and boards examined in the 2026-11-22 study.

PROJ notes:
- Winkel tripel: PROJ's ``wintri`` defaults to ``lat_1 = 0`` (aspect 2.0). Winkel's own choice,
  and the common one, is ``lat_1 = arccos(2/π) = 50.4598°`` (aspect 1.637); set it explicitly.
- Spilhaus needs PROJ ≥ 9.6 (pyproj ≥ 3.8).
- Bertin 1953 has no inverse in PROJ, so it cannot be rasterised this way.
"""

from __future__ import annotations

import math
from typing import List, NamedTuple, Optional, Tuple

from .raster import kit_centre_lon

LON0 = kit_centre_lon()
KIT_ASPECT = 128 / 80
WINKEL = f"+proj=wintri +lat_1=50.4598 +lon_0={LON0}"

# Boards tried in the survey, as (modules across, modules down).
BOARDS = [(8, 5), (8, 4), (10, 5), (9, 5), (9, 4), (7, 4), (6, 6), (5, 5), (7, 7), (10, 6), (8, 6), (6, 4)]


def merc_y(phi: float) -> float:
    return math.log(math.tan(math.pi / 4 + math.radians(phi) / 2))


def merc_lat(y: float) -> float:
    return math.degrees(2 * math.atan(math.exp(y)) - math.pi / 2)


def mill_y(phi: float) -> float:
    return 1.25 * math.log(math.tan(math.pi / 4 + 0.4 * math.radians(phi)))


def mill_lat(y: float) -> float:
    return math.degrees((math.atan(math.exp(y / 1.25)) - math.pi / 4) / 0.4)


def cea_standard_parallel(aspect: float) -> float:
    """Standard parallel at which an equal-area cylindrical map has the given width/height."""
    return math.degrees(math.acos(math.sqrt(aspect / math.pi)))


# Southern limits that make Mercator (from 80° N) and Miller (from 86° N) exactly 1.6 : 1.
MERC_SOUTH = merc_lat(merc_y(80) - 2 * math.pi / KIT_ASPECT)
MILL_SOUTH = mill_lat(mill_y(86) - 2 * math.pi / KIT_ASPECT)


class Projection(NamedTuple):
    name: str
    spec: Optional[str]
    family: str
    clip: Optional[Tuple[float, float]] = None


SURVEY: List[Projection] = [
    Projection("Kit grid (equirectangular, fitted)", None, "cylindrical"),
    Projection("Plate carree", f"+proj=eqc +lon_0={LON0}", "cylindrical", (-82.3, 89.8)),
    Projection("Miller", f"+proj=mill +lon_0={LON0}", "cylindrical", (-82.3, 89.8)),
    Projection("Mercator", f"+proj=merc +lon_0={LON0}", "cylindrical", (-75, 84)),
    Projection("Gall stereographic", f"+proj=gall +lon_0={LON0}", "cylindrical", (-82.3, 89.8)),
    Projection("Patterson", f"+proj=patterson +lon_0={LON0}", "cylindrical", (-82.3, 89.8)),
    Projection("Gall-Peters (equal area)", f"+proj=cea +lat_ts=45 +lon_0={LON0}", "cylindrical"),
    Projection("Robinson", f"+proj=robin +lon_0={LON0}", "pseudocylindrical"),
    Projection("Equal Earth", f"+proj=eqearth +lon_0={LON0}", "pseudocylindrical"),
    Projection("Natural Earth", f"+proj=natearth +lon_0={LON0}", "pseudocylindrical"),
    Projection("Mollweide", f"+proj=moll +lon_0={LON0}", "pseudocylindrical"),
    Projection("Eckert IV", f"+proj=eck4 +lon_0={LON0}", "pseudocylindrical"),
    Projection("Wagner VI", f"+proj=wag6 +lon_0={LON0}", "pseudocylindrical"),
    Projection("Kavrayskiy VII", f"+proj=kav7 +lon_0={LON0}", "pseudocylindrical"),
    Projection("Winkel tripel", WINKEL, "compromise"),
    Projection("Hammer", f"+proj=hammer +lon_0={LON0}", "compromise"),
    Projection("Van der Grinten", f"+proj=vandg +lon_0={LON0}", "compromise", (-82.3, 85)),
    Projection("Goode homolosine (land)", "+proj=igh +lon_0=0", "interrupted"),
    Projection("Goode homolosine (ocean)", "+proj=igh_o +lon_0=-160", "interrupted"),
    Projection("Peirce quincuncial", f"+proj=peirce_q +lat_0=90 +lon_0={LON0} +shape=square", "square"),
    Projection("Adams world in a square II", f"+proj=adams_ws2 +lon_0={LON0}", "square"),
    Projection("Spilhaus", "+proj=spilhaus", "square"),
]


class Candidate(NamedTuple):
    key: str
    projection: Projection
    modules: Tuple[int, int]


def _c(key, name, spec, family, clip, modules) -> Candidate:
    return Candidate(key, Projection(name, spec, family, clip), modules)


CANDIDATES: List[Candidate] = [
    _c("kit", "Kit grid (equidistant cylindrical, standard parallels ±39°)", None, "cylindrical", None, (8, 5)),
    _c("cea-kit", f"Equal-area cylindrical, φs={cea_standard_parallel(KIT_ASPECT):.1f}° (≈ Gall–Peters)",
       f"+proj=cea +lat_ts={cea_standard_parallel(KIT_ASPECT):.3f} +lon_0={LON0}", "cylindrical", None, (8, 5)),
    _c("mercator-kit", f"Mercator, 80°N–{-MERC_SOUTH:.0f}°S", f"+proj=merc +lon_0={LON0}", "cylindrical",
       (MERC_SOUTH, 80), (8, 5)),
    _c("miller-kit", f"Miller, 86°N–{-MILL_SOUTH:.0f}°S", f"+proj=mill +lon_0={LON0}", "cylindrical",
       (MILL_SOUTH, 86), (8, 5)),
    _c("patterson-9x5", "Patterson", f"+proj=patterson +lon_0={LON0}", "cylindrical", None, (9, 5)),
    _c("hobo-dyer-8x4", f"Equal-area cylindrical, φs={cea_standard_parallel(2.0):.1f}° (≈ Hobo–Dyer)",
       f"+proj=cea +lat_ts={cea_standard_parallel(2.0):.3f} +lon_0={LON0}", "cylindrical", None, (8, 4)),
    _c("winkel-kit", "Winkel tripel", WINKEL, "compromise", None, (8, 5)),
    _c("kav7-kit", "Kavrayskiy VII", f"+proj=kav7 +lon_0={LON0}", "pseudocylindrical", None, (8, 5)),
    _c("robinson-8x4", "Robinson", f"+proj=robin +lon_0={LON0}", "pseudocylindrical", None, (8, 4)),
    _c("robinson-10x5", "Robinson (larger)", f"+proj=robin +lon_0={LON0}", "pseudocylindrical", None, (10, 5)),
    _c("equal-earth-8x4", "Equal Earth", f"+proj=eqearth +lon_0={LON0}", "pseudocylindrical", None, (8, 4)),
    _c("natural-earth-8x4", "Natural Earth", f"+proj=natearth +lon_0={LON0}", "pseudocylindrical", None, (8, 4)),
    _c("mollweide-8x4", "Mollweide", f"+proj=moll +lon_0={LON0}", "pseudocylindrical", None, (8, 4)),
    _c("goode-9x4", "Goode homolosine (interrupted)", "+proj=igh +lon_0=0", "interrupted", None, (9, 4)),
    _c("spilhaus-6x6", "Spilhaus (world ocean in a square)", "+proj=spilhaus", "square", None, (6, 6)),
    _c("peirce-6x6", "Peirce quincuncial", f"+proj=peirce_q +lat_0=90 +lon_0={LON0} +shape=square", "square",
       None, (6, 6)),
]


def candidate(key: str) -> Candidate:
    for c in CANDIDATES:
        if c.key == key:
            return c
    raise KeyError(key)

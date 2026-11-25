"""Map templates (feature 016): the canvas a map is built on (constitution Principle I).

A template is a projection, a board of whole 16 x 16 modules, a layout that puts every stud in
land (``L``), ocean (``O``) or margin (``M``, off the globe), one part per class and the kit's
frame (data-model.md Template.id, .projection, .board, .classes, .locations, .parts, .frame,
.counts, .source, .corrections, .confirmation).

- The kit template ``kit-31203`` (``KIT_TEMPLATE_ID``) is built in code from the kit's own files
  (land/sea mask, fitted projection, arrangements): 3,062 land and 7,178 ocean studs, no margin,
  arrangements A, B and C. It is the reference, the default and always buildable; it has no data
  file and no confirmation record.
- Other templates are package data, ``data/templates/<id>.json`` (contracts/template-file.md),
  written by the maintainer tool ``cli/tools/maptemplates``. The loader checks every rule of the
  contract and raises ``TemplateError`` (a ``ValueError``) naming the file and the rule. It
  derives the layout digest (``layout_sha256``, data-model.md TemplateLayoutDigest) and the
  dataset provenance (``dataset``, data-model.md TemplateDataset .id, .version, .title,
  .publisher, .license, .citation, .doi) from the packaged registry entry the file names. A
  template whose ``confirmation`` is null loads (for ``template list/show`` and the tool) but is
  not buildable (FR-004).

Stud lookups (FR-005): ``Template.stud_at(lat, lon)`` and ``Template.location(row, col)``; for
non-kit templates ``Template.grid_projection`` is a ``geometry.TemplateProjection`` (``cells_for``,
``locations``, ``abs_lat``), for the kit the ``maps.projection.KitProjection``. Margins use the
1x1 square tile ``MARGIN_PART_ID`` (3070b). ``Template.projection_title`` names the projection as
maps, pages and stickers show it ("Winkel tripel"; feature 017), from ``PROJECTION_TITLES``.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import copy
import datetime as _dt
import hashlib
import json
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

import numpy as np

from . import winkel
from .board import CLASS_CODES, board_counts, rim_cells
from .digest import layout_sha256
from .geometry import FORWARD, TemplateProjection

KIT_TEMPLATE_ID = "kit-31203"
MARGIN_PART_ID = "3070b"
LAND_PART_ID, OCEAN_PART_ID = "6141", "98138"
TEMPLATE_PARTS = {"land": LAND_PART_ID, "ocean": OCEAN_PART_ID, "margin": MARGIN_PART_ID}
KIT_PROJECTION = "kit-31203-equirectangular"
# The projections' names as maps, pages and stickers show them (feature 017, research R14), keyed by
# ``projection.name``: in code, not in the template files, whose SHA-256 every output records.
PROJECTION_TITLES = {winkel.NAME: winkel.TITLE, KIT_PROJECTION: "Equidistant cylindrical"}
FORMAT_VERSION = "1"
DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "data" / "templates"
PACKAGED_REGISTRY = Path(__file__).resolve().parent.parent / "data" / "datasets.json"

BOARD = {"modules": [8, 5], "module": 16, "width": 128, "height": 80, "pitch_mm": 8.0}
FRAME = {"kit": "31203", "arrangements": ["A"], "source": "kit_31203_arrangements.json"}
CONFIRMATION_ROLE = "project owner"
CLASS_NAMES = {"L": "land", "O": "ocean", "M": "margin"}
CLASS_CODE = {v: k for k, v in CLASS_NAMES.items()}
SECTION_COLUMNS = "ABCDEFGH"
GENERATOR_PREFIX = "cli/tools/maptemplates"
CHECK_POINT_COUNT = 24
CHECK_TOLERANCE = 1e-9
FIT_TOLERANCE = 1e-9
METHOD_KEYS = ("supersample", "on_globe_share", "land_share", "land_rule", "round_trip_tolerance",
               "location_rule")
DATASET_KEYS = ("id", "version", "url", "sha256", "citation", "license")
DATASET_MATCH = ("version", "sha256", "citation", "license")

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class TemplateError(ValueError):
    """A template file breaks a rule (``file`` and ``rule`` name where), or a template is unknown."""

    def __init__(self, message: str, file: Optional[str] = None, rule: Optional[str] = None):
        self.file, self.rule, self.detail = file, rule, message
        super().__init__(f"{file}: {rule}: {message}" if file else message)


class UnknownTemplateError(TemplateError):
    """No template has this id."""


@dataclass(frozen=True)
class TemplateCorrection:
    """A hand correction (data-model.md TemplateCorrection .row, .col, .class, .reason); ``class_``
    is ``land``, ``ocean`` or ``margin``. Corrections are already applied to the classes."""

    row: int
    col: int
    class_: str
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {"row": self.row, "col": self.col, "class": self.class_, "reason": self.reason}


@dataclass(frozen=True)
class Confirmation:
    """The owner's confirmation (data-model.md Confirmation .role, .date): a role, no name."""

    role: str
    date: str

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "date": self.date}


@dataclass(frozen=True)
class TemplateDataset:
    """The dataset that decided land and ocean (data-model.md TemplateDataset), from the packaged
    registry entry the template file names."""

    id: str
    version: str
    title: str
    publisher: str
    license: str
    citation: str
    doi: str

    def to_dict(self) -> Dict[str, str]:
        return {"id": self.id, "version": self.version, "title": self.title, "publisher": self.publisher,
                "license": self.license, "citation": self.citation, "doi": self.doi}


def _readonly(a: np.ndarray) -> np.ndarray:
    a = np.array(a)
    a.setflags(write=False)
    return a


class Template:
    """A loaded template (immutable; cached by the loader)."""

    def __init__(self, *, id: str, title: str, description: str, projection: Dict[str, Any],
                 board: Dict[str, Any], parts: Dict[str, str], frame: Dict[str, Any],
                 classes: Tuple[str, ...], lat: np.ndarray, lon: np.ndarray, counts: Dict[str, Any],
                 source: Dict[str, Any], corrections: Tuple[TemplateCorrection, ...],
                 confirmation: Optional[Confirmation], disclaimer: str, layout_sha256: str,
                 dataset: Optional[TemplateDataset], grid_projection: Any, path: Optional[Path] = None,
                 file_sha256: Optional[str] = None, document: Optional[Dict[str, Any]] = None):
        self.id, self.title, self.description = id, title, description
        self._projection, self._board, self._parts, self._frame = projection, board, parts, frame
        self.classes = tuple(classes)
        codes = np.array([list(r) for r in self.classes], dtype="U1")
        self._land = _readonly(codes == "L")
        self._ocean = _readonly(codes == "O")
        self._margin = _readonly(codes == "M")
        self._on = _readonly(codes != "M")
        self._ring = _readonly(rim_cells(codes != "M"))
        self._lat = _readonly(np.where(self._on, lat, np.nan))
        self._lon = _readonly(np.where(self._on, lon, np.nan))
        self._counts, self._source = counts, source
        self.corrections = tuple(corrections)
        self.confirmation = confirmation
        self.disclaimer = disclaimer
        self.layout_sha256 = layout_sha256
        self.dataset = dataset
        self.grid_projection = grid_projection
        self.path = path
        self.file_sha256 = file_sha256
        self._document = document

    def __repr__(self) -> str:
        return f"Template({self.id!r}, {self.status})"

    # --- identity and status ------------------------------------------------------------
    @property
    def is_kit(self) -> bool:
        return self.id == KIT_TEMPLATE_ID

    @property
    def status(self) -> str:
        """``reference`` (the kit), ``confirmed`` or ``unconfirmed``."""
        if self.is_kit:
            return "reference"
        return "confirmed" if self.confirmation is not None else "unconfirmed"

    @property
    def buildable(self) -> bool:
        """Maps can be built on it: the kit, or a template the owner confirmed (FR-004)."""
        return self.status != "unconfirmed"

    # --- the file's blocks (copies) -----------------------------------------------------
    @property
    def projection(self) -> Dict[str, Any]:
        return copy.deepcopy(self._projection)

    @property
    def board(self) -> Dict[str, Any]:
        return copy.deepcopy(self._board)

    @property
    def parts(self) -> Dict[str, str]:
        return dict(self._parts)

    @property
    def frame(self) -> Dict[str, Any]:
        return copy.deepcopy(self._frame)

    @property
    def counts(self) -> Dict[str, Any]:
        return copy.deepcopy(self._counts)

    @property
    def source(self) -> Dict[str, Any]:
        return copy.deepcopy(self._source)

    @property
    def projection_title(self) -> str:
        """The projection's name as maps, pages and stickers show it ("Winkel tripel"), from
        ``PROJECTION_TITLES`` by ``projection["name"]`` (feature 017)."""
        name = self._projection["name"]
        return PROJECTION_TITLES.get(name, name)

    @property
    def arrangements(self) -> Tuple[str, ...]:
        return tuple(self._frame["arrangements"])

    @property
    def width(self) -> int:
        return int(self._board["width"])

    @property
    def height(self) -> int:
        return int(self._board["height"])

    # --- masks (read-only, height x width) ----------------------------------------------
    @property
    def land(self) -> np.ndarray:
        return self._land

    @property
    def ocean(self) -> np.ndarray:
        return self._ocean

    @property
    def margin(self) -> np.ndarray:
        return self._margin

    @property
    def on_globe(self) -> np.ndarray:
        return self._on

    @property
    def ring(self) -> np.ndarray:
        """Margin studs with an on-globe 4-neighbour (the outline ring)."""
        return self._ring

    # --- studs and locations (FR-005) ---------------------------------------------------
    def _check(self, row: int, col: int) -> None:
        if not (0 <= row < self.height and 0 <= col < self.width):
            raise ValueError(f"stud ({row}, {col}) is outside the {self.height} x {self.width} board "
                             f"(rows 0-{self.height - 1}, columns 0-{self.width - 1})")

    def locations(self) -> Tuple[np.ndarray, np.ndarray]:
        """Latitude and longitude (degrees) of every stud; NaN on margin studs."""
        return self._lat.copy(), self._lon.copy()

    def location(self, row: int, col: int) -> Optional[Tuple[float, float]]:
        """(lat, lon) of an on-globe stud; None for a margin stud."""
        self._check(row, col)
        if not self._on[row, col]:
            return None
        return float(self._lat[row, col]), float(self._lon[row, col])

    def stud_at(self, lat: float, lon: float) -> Optional[Tuple[int, int]]:
        """(row, col) of the stud containing a location; None off the board or on a margin stud."""
        if self.is_kit:
            r = int(self.grid_projection.rows_for_lat(np.array([lat], dtype=float))[0])
            if r < 0:
                return None
            return r, int(self.grid_projection.cols_for_lon(np.array([lon], dtype=float))[0])
        idx = int(self.grid_projection.cells_for(np.array([lat], dtype=float), np.array([lon], dtype=float))[0])
        return None if idx < 0 else divmod(idx, self.width)

    def class_at(self, row: int, col: int) -> str:
        """``land``, ``ocean`` or ``margin``."""
        self._check(row, col)
        return CLASS_NAMES[self.classes[row][col]]

    def part_at(self, row: int, col: int) -> str:
        return self._parts[self.class_at(row, col)]

    def section_label(self, row: int, col: int) -> str:
        """The kit section (A1 ... H5) a stud lies in, as hung in combination A."""
        self._check(row, col)
        m = int(self._board["module"])
        return f"{SECTION_COLUMNS[col // m]}{row // m + 1}"

    def document(self) -> Dict[str, Any]:
        """The template as a document (the file's JSON; the kit's in-code equivalent)."""
        return copy.deepcopy(self._document)

    def _stud_counts(self) -> Dict[str, int]:
        return {k: int(self._counts[k]) for k in ("land", "ocean", "margin", "ring")}

    def layout_record(self) -> Dict[str, Any]:
        """``metadata.template`` of a layout built on this (non-kit) template (FR-010; research R11;
        contracts/recipe-and-outputs.md): id, title, projection, board, parts, stud counts, the
        dataset that decided land and ocean, and the file's SHA-256, layout digest and confirmation."""
        p = self._projection
        return {"id": self.id, "title": self.title,
                "projection": {"name": p["name"], "proj": p["proj"]},
                "board": {"modules": list(self._board["modules"]), "width": self.width, "height": self.height},
                "parts": dict(self._parts),
                "counts": self._stud_counts(),
                "dataset": None if self.dataset is None else self.dataset.to_dict(),
                "source": {"file": None if self.path is None else f"templates/{self.path.name}",
                           "sha256": self.file_sha256, "layout_sha256": self.layout_sha256,
                           "confirmation": None if self.confirmation is None else self.confirmation.to_dict()}}

    def report_record(self) -> Dict[str, Any]:
        """The suitability report's ``template`` block (FR-013): id, title, stud counts, dataset."""
        return {"id": self.id, "title": self.title, "counts": self._stud_counts(),
                "dataset": None if self.dataset is None else self.dataset.to_dict()}

    def summary(self) -> Dict[str, Any]:
        """What ``template show --format json`` prints (without the disclaimer)."""
        p = self._projection
        return {"id": self.id, "title": self.title, "description": self.description, "status": self.status,
                "projection": {k: copy.deepcopy(p.get(k)) for k in ("name", "proj", "lat_1", "lon_0", "citation",
                                                                    "fit")},
                "board": self.board, "parts": self.parts, "frame": self.frame, "counts": self.counts,
                "dataset": None if self.dataset is None else self.dataset.to_dict(),
                "corrections": len(self.corrections),
                "confirmation": None if self.confirmation is None else self.confirmation.to_dict(),
                "layout_sha256": self.layout_sha256,
                "file": None if self.path is None else self.path.name, "file_sha256": self.file_sha256}


# --- the kit template, in code ---------------------------------------------------------------

@lru_cache(maxsize=1)
def kit_template() -> Template:
    """``kit-31203`` from the kit's files: classes from the land/sea mask, locations from the
    fitted projection's cell centres, arrangements A, B, C (FR-002)."""
    from ..layout.arrangement import load_arrangements
    from ..layout.land_sea_mask import load_land_sea_mask
    from ..maps.projection import load_kit_projection

    p = load_kit_projection()
    mask = load_land_sea_mask()
    H, W = p.height, p.width
    classes = tuple("".join("L" if mask.is_land(x, y) else "O" for x in range(W)) for y in range(H))
    lat_row = np.array([p.cell_center(r, 0)[0] for r in range(H)])
    lon_col = np.array([p.cell_center(0, c)[1] for c in range(W)])
    lat = np.repeat(lat_row[:, None], W, axis=1)
    lon = np.repeat(lon_col[None, :], H, axis=0)
    projection = {"name": KIT_PROJECTION, "proj": None, "lat_1": None, "lon_0": None,
                  "citation": ("kit_31203_projection.json: the kit grid's equidistant cylindrical projection "
                               "fitted to the kit's land/sea mask (feature 004, research R2)"),
                  "fit": {"mode": "kit", "left_edge_lon": p.left_edge_lon, "deg_per_col": p.deg_per_col,
                          "equator_row": p.equator_row, "rows_per_radian": p.rows_per_radian},
                  "check_points": []}
    arr = [a.id for a in load_arrangements().arrangements]
    doc = {"format_version": FORMAT_VERSION, "id": KIT_TEMPLATE_ID, "title": "Kit 31203 grid",
           "description": ("The LEGO World Map kit 31203 as built: 128 x 80 studs, LEGO's land/sea mask "
                           "(3,062 land, 7,178 ocean, no margin), the kit's equidistant cylindrical projection "
                           "fitted to that mask, and its three frames hung A, B or C."),
           "projection": projection, "board": dict(BOARD), "parts": {"land": LAND_PART_ID, "ocean": OCEAN_PART_ID},
           "frame": {"kit": "31203", "arrangements": arr, "source": "kit_31203_arrangements.json"},
           "classes": list(classes),
           "locations": {"lat": lat.tolist(), "lon": lon.tolist()},
           "counts": board_counts(classes),
           "source": {"generator": "built in code (lego_image_processor.templates)",
                      "files": ["lego_world_map_land_sea_mask.json", "kit_31203_projection.json",
                                "kit_31203_arrangements.json", "kit_31203_inventory.json", "kit_31203_ice.json"],
                      "disclaimer": DISCLAIMER},
           "corrections": [], "confirmation": None, "disclaimer": DISCLAIMER}
    return Template(id=KIT_TEMPLATE_ID, title=doc["title"], description=doc["description"],
                    projection=projection, board=doc["board"], parts=doc["parts"], frame=doc["frame"],
                    classes=classes, lat=lat, lon=lon, counts=doc["counts"], source=doc["source"],
                    corrections=(), confirmation=None, disclaimer=DISCLAIMER, layout_sha256=layout_sha256(doc),
                    dataset=None, grid_projection=p, document=doc)


# --- file templates ------------------------------------------------------------------------

def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _is_text(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _is_date(v: Any) -> bool:
    if not isinstance(v, str) or not _DATE_RE.match(v):
        return False
    try:
        _dt.date.fromisoformat(v)
    except ValueError:
        return False
    return True


@lru_cache(maxsize=None)
def _packaged_registry():
    from ..datasets.registry import load_registry

    return load_registry(PACKAGED_REGISTRY)


def parse_template(doc: Any, filename: str, path: Optional[Path] = None,
                   file_sha256: Optional[str] = None) -> Template:
    """Check a template document against every rule of contracts/template-file.md."""

    def fail(rule: str, message: str):
        raise TemplateError(message, file=filename, rule=rule)

    if not isinstance(doc, dict):
        fail("json", "the file must hold a JSON object")
    if doc.get("format_version") != FORMAT_VERSION:
        fail("format_version", f"must be {FORMAT_VERSION!r}")

    # id, title, description
    tid = doc.get("id")
    stem = Path(filename).stem
    if not isinstance(tid, str) or not _ID_RE.match(tid):
        fail("id", f"{tid!r} must match {_ID_RE.pattern}")
    if tid == KIT_TEMPLATE_ID:
        fail("id", f"{KIT_TEMPLATE_ID} is the kit template, built in code; it has no data file")
    if tid.endswith("-ice"):
        fail("id", "ids ending in -ice are reserved for ice files (<id>-ice.json)")
    if tid != stem:
        fail("id", f"{tid!r} must equal the file name {stem!r}")
    for key in ("title", "description"):
        if not _is_text(doc.get(key)):
            fail(key, "must be a non-empty string")

    # board, parts, frame
    board = doc.get("board")
    if not isinstance(board, dict) or set(board) != set(BOARD):
        fail("board", f"must have exactly the keys {', '.join(BOARD)}")
    mods, module = board["modules"], board["module"]
    if not (isinstance(mods, list) and len(mods) == 2 and all(isinstance(m, int) and not isinstance(m, bool)
                                                               and m > 0 for m in mods)):
        fail("board", "modules must be [across, down], two positive integers")
    if module != BOARD["module"]:
        fail("board", f"module must be {BOARD['module']} (16 x 16 studs)")
    if board["width"] != mods[0] * module or board["height"] != mods[1] * module:
        fail("board", "width and height must be whole modules (modules x module)")
    if (board["width"], board["height"]) != (BOARD["width"], BOARD["height"]):
        fail("board", "the board must be 128 x 80 studs (8 x 5 modules) for now")
    if board["pitch_mm"] != BOARD["pitch_mm"]:
        fail("board", f"pitch_mm must be {BOARD['pitch_mm']}")
    W, H = int(board["width"]), int(board["height"])
    if doc.get("parts") != TEMPLATE_PARTS:
        fail("parts", f"must be exactly {json.dumps(TEMPLATE_PARTS)}")
    if doc.get("frame") != FRAME:
        fail("frame", f"must be {json.dumps(FRAME)} (the frames of a curved map cannot be re-hung)")

    # projection
    proj = doc.get("projection")
    if not isinstance(proj, dict):
        fail("projection", "must be an object")
    name = proj.get("name")
    if name not in FORWARD:
        fail("projection.name", f"{name!r} has no run-time formula; known: {', '.join(FORWARD)}")
    lat_1, lon_0 = proj.get("lat_1"), proj.get("lon_0")
    if not _is_number(lat_1) or not 0 < lat_1 < 90:
        fail("projection.lat_1", "must be a number of degrees between 0 and 90")
    if not _is_number(lon_0) or not -180 <= lon_0 <= 180:
        fail("projection.lon_0", "must be a number of degrees between -180 and 180")
    want = winkel.proj_string(lat_1, lon_0)
    if proj.get("proj") != want:
        fail("projection.proj", f"must be {want!r} for lat_1 {lat_1:g} and lon_0 {lon_0:g}")
    if not _is_text(proj.get("citation")):
        fail("projection.citation", "must be a non-empty string")
    fit = proj.get("fit")
    if not isinstance(fit, dict) or set(fit) != {"mode", "extent", "scale", "centre"}:
        fail("projection.fit", "must be {mode, extent, scale, centre}")
    if fit["mode"] != "contain":
        fail("projection.fit", "mode must be 'contain'")
    exact = winkel.fit(W, H, lat_1)
    ext, cen, scale = fit["extent"], fit["centre"], fit["scale"]
    if not (isinstance(ext, list) and len(ext) == 4 and all(_is_number(v) for v in ext)
            and all(abs(a - b) <= FIT_TOLERANCE for a, b in zip(ext, exact["extent"]))):
        fail("projection.fit", f"extent must be the exact extent {exact['extent']}")
    if not (_is_number(scale) and abs(scale - exact["scale"]) <= FIT_TOLERANCE * exact["scale"]):
        fail("projection.fit", f"scale must be {exact['scale']!r} studs per unit (contain)")
    if not (isinstance(cen, list) and len(cen) == 2 and all(_is_number(v) for v in cen)
            and all(abs(a - b) <= FIT_TOLERANCE for a, b in zip(cen, exact["centre"]))):
        fail("projection.fit", f"centre must be the extent's centre {exact['centre']}")
    pts = proj.get("check_points")
    if not (isinstance(pts, list) and len(pts) == CHECK_POINT_COUNT
            and all(isinstance(p, list) and len(p) == 4 and all(_is_number(v) for v in p) for p in pts)):
        fail("projection.check_points", f"must be {CHECK_POINT_COUNT} points [lon, lat, x, y]")
    a = np.array(pts, dtype=float)
    if (np.abs(a[:, 0]) > 180).any() or (np.abs(a[:, 1]) > 90).any():
        fail("projection.check_points", "lon must be in -180..180 and lat in -90..90")
    fx, fy = FORWARD[name](a[:, 0], a[:, 1], lat_1, lon_0)
    d = np.maximum(np.abs(fx - a[:, 2]), np.abs(fy - a[:, 3]))
    if not (np.isfinite(d).all() and (d < CHECK_TOLERANCE).all()):
        i = int(np.nanargmax(np.where(np.isfinite(d), d, np.inf)))
        fail("projection.check_points", f"point {i} ({a[i, 0]:g}, {a[i, 1]:g}) differs from the run-time "
             f"formula by {d[i]:.3g} (must be < {CHECK_TOLERANCE:g})")

    # classes and locations
    classes = doc.get("classes")
    if not (isinstance(classes, list) and len(classes) == H):
        fail("classes", f"must be {H} strings, one per board row")
    for r, row in enumerate(classes):
        if not isinstance(row, str) or len(row) != W or set(row) - set(CLASS_CODES):
            fail("classes", f"row {r} must be a string of {W} characters, each L, O or M")
    locs = doc.get("locations")
    if not isinstance(locs, dict) or set(locs) != {"lat", "lon"}:
        fail("locations", "must be {lat, lon}")
    arrays = {}
    for axis, limit in (("lat", 90.0), ("lon", 180.0)):
        rows = locs[axis]
        if not (isinstance(rows, list) and len(rows) == H and all(isinstance(x, list) and len(x) == W for x in rows)):
            fail("locations", f"{axis} must be {H} rows of {W} values")
        out = np.full((H, W), np.nan)
        for r, (row, cls) in enumerate(zip(rows, classes)):
            for c, (v, k) in enumerate(zip(row, cls)):
                if v is None:
                    if k != "M":
                        fail("locations", f"{axis} missing at row {r}, column {c} ({CLASS_NAMES[k]} stud)")
                    continue
                if k == "M":
                    fail("locations", f"{axis} given at row {r}, column {c}, a margin stud (must be null)")
                if not _is_number(v) or abs(v) > limit:
                    fail("locations", f"{axis} at row {r}, column {c} must be a number in "
                         f"{-limit:g}..{limit:g}, not {v!r}")
                out[r, c] = v
        arrays[axis] = out

    # counts
    counts = board_counts(classes)
    if doc.get("counts") != counts:
        fail("counts", f"must equal the counts derived from the classes: {json.dumps(counts)}")

    # source
    src = doc.get("source")
    if not isinstance(src, dict):
        fail("source", "must be an object")
    if not (isinstance(src.get("generator"), str) and src["generator"].startswith(GENERATOR_PREFIX)):
        fail("source.generator", f"must name {GENERATOR_PREFIX}")
    if not _is_date(src.get("generated_on")):
        fail("source.generated_on", "must be a date YYYY-MM-DD")
    ds = src.get("dataset")
    if not isinstance(ds, dict) or not all(isinstance(ds.get(k), str) and ds[k] for k in DATASET_KEYS):
        fail("source.dataset", f"must have {', '.join(DATASET_KEYS)}")
    try:
        entry = _packaged_registry().get(ds["id"])
    except KeyError:
        fail("source.dataset", f"{ds['id']!r} is not in the dataset registry (data/datasets.json)")
    for k in DATASET_MATCH:
        if ds[k] != getattr(entry, k):
            fail("source.dataset", f"{k} differs from the registry entry {entry.id}")
    method = src.get("method")
    if not isinstance(method, dict) or any(k not in method for k in METHOD_KEYS):
        fail("source.method", f"must have {', '.join(METHOD_KEYS)}")
    sw = src.get("software")
    if not isinstance(sw, dict) or not all(isinstance(sw.get(k), str) for k in ("pyproj", "proj")):
        fail("source.software", "must give the pyproj and proj versions")
    if src.get("disclaimer") != DISCLAIMER:
        fail("source.disclaimer", f"must be {DISCLAIMER!r}")

    # corrections
    raw = doc.get("corrections")
    if not isinstance(raw, list):
        fail("corrections", "must be a list")
    corrections, last = [], {}
    for i, c in enumerate(raw):
        if not isinstance(c, dict) or set(c) != {"row", "col", "class", "reason"}:
            fail("corrections", f"item {i} must be {{row, col, class, reason}}")
        r, col_, k, reason = c["row"], c["col"], c["class"], c["reason"]
        if not (isinstance(r, int) and not isinstance(r, bool) and 0 <= r < H and
                isinstance(col_, int) and not isinstance(col_, bool) and 0 <= col_ < W):
            fail("corrections", f"item {i}: row and col must be on the {H} x {W} board")
        if k not in CLASS_CODE:
            fail("corrections", f"item {i}: class must be land, ocean or margin, not {k!r}")
        if not _is_text(reason):
            fail("corrections", f"item {i}: reason must be a non-empty string")
        corrections.append(TemplateCorrection(row=r, col=col_, class_=k, reason=reason))
        last[(r, col_)] = (i, k)
    for (r, col_), (i, k) in last.items():
        if classes[r][col_] != CLASS_CODE[k]:
            fail("corrections", f"item {i} sets row {r}, column {col_} to {k}, but classes have "
                 f"{CLASS_NAMES[classes[r][col_]]} there")

    # confirmation, disclaimer
    if "confirmation" not in doc:
        fail("confirmation", "is required (null until the owner confirms)")
    conf = doc["confirmation"]
    confirmation = None
    if conf is not None:
        if not isinstance(conf, dict) or set(conf) != {"role", "date"}:
            fail("confirmation", "must be null or exactly {role, date} (no personal name)")
        if conf["role"] != CONFIRMATION_ROLE:
            fail("confirmation", f"role must be {CONFIRMATION_ROLE!r}")
        if not _is_date(conf["date"]):
            fail("confirmation", "date must be YYYY-MM-DD")
        confirmation = Confirmation(role=conf["role"], date=conf["date"])
    if doc.get("disclaimer") != DISCLAIMER:
        fail("disclaimer", f"must be {DISCLAIMER!r}")

    dataset = TemplateDataset(id=entry.id, version=entry.version, title=entry.title, publisher=entry.publisher,
                              license=entry.license, citation=entry.citation, doi=entry.doi)
    on = np.array([[k != "M" for k in row] for row in classes])
    grid = TemplateProjection(name=name, lat_1=lat_1, lon_0=lon_0, fit=fit, width=W, height=H, on_globe=on,
                              lat=arrays["lat"], lon=arrays["lon"])
    return Template(id=tid, title=doc["title"], description=doc["description"], projection=copy.deepcopy(proj),
                    board=copy.deepcopy(board), parts=dict(doc["parts"]), frame=copy.deepcopy(doc["frame"]),
                    classes=tuple(classes), lat=arrays["lat"], lon=arrays["lon"], counts=counts,
                    source=copy.deepcopy(src), corrections=tuple(corrections), confirmation=confirmation,
                    disclaimer=doc["disclaimer"], layout_sha256=layout_sha256(doc), dataset=dataset,
                    grid_projection=grid, path=path, file_sha256=file_sha256, document=copy.deepcopy(doc))


@lru_cache(maxsize=32)
def _load_file(path: str, mtime_ns: int, size: int) -> Template:
    p = Path(path)
    data = p.read_bytes()
    try:
        doc = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TemplateError(f"not valid UTF-8 JSON ({exc})", file=p.name, rule="json") from exc
    return parse_template(doc, p.name, path=p, file_sha256=hashlib.sha256(data).hexdigest())


def load_template_file(path) -> Template:
    """Load and check a template file (cached by path, modification time and size)."""
    p = Path(path).resolve()
    st = p.stat()
    return _load_file(str(p), st.st_mtime_ns, st.st_size)


def template_files() -> List[Path]:
    """The template files in ``TEMPLATE_DIR`` (``<id>.json``; ice and ``.source.json`` files left out)."""
    d = Path(TEMPLATE_DIR)
    if not d.is_dir():
        return []
    return sorted(p for p in d.glob("*.json") if _ID_RE.match(p.stem) and not p.stem.endswith("-ice"))


def template_ids() -> List[str]:
    """Every known template id (the kit first), without loading the files."""
    return [KIT_TEMPLATE_ID] + [p.stem for p in template_files() if p.stem != KIT_TEMPLATE_ID]


def load_template(template_id: str) -> Template:
    """The template with this id: the kit in code, others from ``TEMPLATE_DIR``."""
    if template_id == KIT_TEMPLATE_ID:
        return kit_template()
    path = Path(TEMPLATE_DIR) / f"{template_id}.json"
    if not (isinstance(template_id, str) and _ID_RE.match(template_id) and not template_id.endswith("-ice")
            and path.is_file()):
        raise UnknownTemplateError(f"unknown template {template_id!r}; known templates: "
                                   f"{', '.join(template_ids())}")
    return load_template_file(path)


def list_templates() -> Tuple[Template, ...]:
    """Every template: the kit first, then the files in ``TEMPLATE_DIR`` by id."""
    return (kit_template(),) + tuple(load_template_file(p) for p in template_files()
                                     if p.stem != KIT_TEMPLATE_ID)


def confirmed_templates() -> Tuple[Template, ...]:
    """The buildable templates: the kit and every confirmed template."""
    return tuple(t for t in list_templates() if t.buildable)


def confirmed_text() -> str:
    """``kit-31203, winkel-tripel``: the ids of the buildable templates, for error messages."""
    try:
        return ", ".join(t.id for t in confirmed_templates())
    except TemplateError:  # a broken template file: the kit is always buildable
        return KIT_TEMPLATE_ID


KIT_DESIGN_FORMAT = "kit-design"  # registry format of LEGO's design copied cell for cell (official-31203)
BATHYMETRY_RECIPE = "official-31203-bathymetry"
REHANG_RULE = "the frames of a curved map cannot be re-hung"
ARRANGEMENT_SOURCE_TEXT = {"option": "from --arrangement", "recipe": "from the recipe's arrangement key"}


def compatibility(recipe, template, arrangement=None) -> Optional[str]:
    """None when ``recipe`` can be built on ``template`` (a ``Template`` or an id), else the reason
    (FR-004, FR-011; research R6, R8; used by ``map build`` and the web prebuild).

    ``arrangement`` is an explicit arrangement (``--arrangement``); None means the recipe's own
    ``arrangement`` key, else A. The kit takes every recipe. A non-kit template must be confirmed,
    takes arrangement A only, and cannot sample a dataset whose registry entry has
    ``format == "kit-design"`` (``kit31203-design``, the official design on the kit grid)."""
    t = template if isinstance(template, Template) else load_template(template)
    if t.is_kit:
        return None
    if not t.buildable:
        return (f"template {t.id} is not confirmed by the project owner, so maps cannot be built on it yet; "
                f"confirmed templates: {confirmed_text()}")
    for entry in recipe.datasets():
        if entry.format == KIT_DESIGN_FORMAT:
            return (f"recipe {recipe.id} reads {entry.id}, LEGO's design copied cell for cell from the kit "
                    f"grid, which cannot be sampled on template {t.id}; build {BATHYMETRY_RECIPE} instead "
                    f"for the official look from data")
    if arrangement is not None:
        chosen, source = arrangement, "option"
    else:
        chosen, source = getattr(recipe, "arrangement", None), "recipe"
    if chosen is not None and chosen.id not in t.arrangements:
        hint = " (an explicit --arrangement A builds it)" if source == "recipe" else ""
        return (f"{REHANG_RULE}: template {t.id} takes arrangement {', '.join(t.arrangements)} only, and "
                f"arrangement {chosen.id} comes {ARRANGEMENT_SOURCE_TEXT[source]}{hint}")
    return None


__all__ = [
    "Template", "TemplateError", "UnknownTemplateError", "TemplateCorrection", "Confirmation", "TemplateDataset",
    "TemplateProjection", "KIT_TEMPLATE_ID", "MARGIN_PART_ID", "TEMPLATE_DIR", "TEMPLATE_PARTS", "DISCLAIMER",
    "load_template", "load_template_file", "list_templates", "confirmed_templates", "template_ids",
    "template_files", "kit_template", "parse_template", "winkel", "compatibility", "confirmed_text",
]

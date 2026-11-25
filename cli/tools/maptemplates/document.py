"""Template data file text (contracts/template-file.md): the writer the maintainer tool and the
test helper share.

``to_text(doc)`` writes UTF-8 JSON with the fields in the contract's order, two-space indent, and
``classes``, ``locations.lat``, ``locations.lon``, ``projection.check_points`` and
``corrections`` one row per line, so the file reads as a picture of the board and diffs by board
row. Locations are expected already rounded to 4 decimals (``round_location``, ``location_rows``).

Also here (T035): reading a template file or a corrections file, applying corrections
(data-model.md TemplateCorrection .row, .col, .class, .reason), the confirmation (data-model.md
Confirmation .role, .date: written only with ``write --confirmed-on``, kept while classes and
locations are unchanged, cleared otherwise) and the differences ``build --check`` lists (every
field but ``source.generated_on``; a class or location change names its stud). Not affiliated with
or endorsed by The LEGO Group.
"""

from __future__ import annotations

import datetime as _dt
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

FIELD_ORDER = ("format_version", "id", "title", "description", "projection", "board", "parts", "frame",
               "classes", "locations", "counts", "source", "corrections", "confirmation", "disclaimer")
PROJECTION_ORDER = ("name", "proj", "lat_1", "lon_0", "citation", "fit", "check_points")

# Paths written on one line, and paths whose items are written one per line.
_INLINE = {("projection", "fit"), ("board",), ("parts",), ("frame",), ("confirmation",)}
_ROWS = {("projection", "check_points"), ("classes",), ("locations", "lat"), ("locations", "lon"),
         ("corrections",)}
_COMPACT_ROWS = {("locations", "lat"), ("locations", "lon")}


def round_location(v: Optional[float]) -> Optional[float]:
    """A latitude or longitude as stored: 4 decimals, never -0.0, None for no location."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return round(float(v), 4) + 0.0


def _ordered(doc: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: doc[k] for k in FIELD_ORDER if k in doc}
    out.update({k: v for k, v in doc.items() if k not in out})
    if isinstance(out.get("projection"), dict):
        p = out["projection"]
        q = {k: p[k] for k in PROJECTION_ORDER if k in p}
        q.update({k: v for k, v in p.items() if k not in q})
        out["projection"] = q
    return out


def _inline(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, separators=(", ", ": "))


def _emit(v: Any, path: Tuple[str, ...], ind: int) -> str:
    pad = "  " * ind
    if path in _INLINE or not isinstance(v, (dict, list, tuple)):
        return _inline(v)
    if path in _ROWS:
        if not v:
            return "[]"
        sep = (",", ":") if path in _COMPACT_ROWS else (", ", ": ")
        rows = [pad + "  " + json.dumps(r, ensure_ascii=False, separators=sep) for r in v]
        return "[\n" + ",\n".join(rows) + "\n" + pad + "]"
    if isinstance(v, dict):
        if not v:
            return "{}"
        items = [pad + "  " + json.dumps(k, ensure_ascii=False) + ": " + _emit(val, path + (k,), ind + 1)
                 for k, val in v.items()]
        return "{\n" + ",\n".join(items) + "\n" + pad + "}"
    if not v:
        return "[]"
    items = [pad + "  " + _emit(val, path, ind + 1) for val in v]
    return "[\n" + ",\n".join(items) + "\n" + pad + "]"


def to_text(doc: Dict[str, Any]) -> str:
    """The template file's text (ends with a newline)."""
    return _emit(_ordered(doc), (), 0) + "\n"


def ice_to_text(doc: Dict[str, Any]) -> str:
    """An ice file's text: two-space indent, each ``cells`` list on one line."""
    def emit(v: Any, path: Tuple[str, ...], ind: int) -> str:
        pad = "  " * ind
        if path[-1:] == ("cells",) or not isinstance(v, (dict, list)):
            return _inline(v)
        if isinstance(v, dict):
            if not v:
                return "{}"
            items = [pad + "  " + json.dumps(k, ensure_ascii=False) + ": " + emit(val, path + (k,), ind + 1)
                     for k, val in v.items()]
            return "{\n" + ",\n".join(items) + "\n" + pad + "}"
        if not v:
            return "[]"
        items = [pad + "  " + emit(val, path, ind + 1) for val in v]
        return "[\n" + ",\n".join(items) + "\n" + pad + "]"

    return emit(doc, (), 0) + "\n"


# --- reading ---------------------------------------------------------------------------------

def read_document(path) -> Dict[str, Any]:
    """A template file as JSON (not checked: ``build --check`` compares even a broken file)."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def normalise(doc: Dict[str, Any]) -> Dict[str, Any]:
    """The document as it reads back from its file text (``to_text``)."""
    return json.loads(to_text(doc))


def location_rows(values: np.ndarray, classes: np.ndarray) -> List[List[Optional[float]]]:
    """Rows of rounded locations, ``None`` on margin studs (``M``) and where there is none."""
    values = np.asarray(values, dtype=float)
    classes = np.asarray(classes)
    return [[None if classes[r, c] == "M" else round_location(values[r, c]) for c in range(values.shape[1])]
            for r in range(values.shape[0])]


# --- corrections -----------------------------------------------------------------------------

CORRECTION_KEYS = ("row", "col", "class", "reason")
CLASS_CODE = {"land": "L", "ocean": "O", "margin": "M"}
CLASS_NAME = {v: k for k, v in CLASS_CODE.items()}


class CorrectionError(ValueError):
    """A correction that cannot be applied (names the correction, counted from 1)."""


def read_corrections(path) -> List[Dict[str, Any]]:
    """A corrections file: a JSON list of ``{row, col, class, reason}``, or an object with that
    list under ``corrections`` (as a template file has it)."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CorrectionError(f"{path}: cannot read the corrections ({exc})") from exc
    if isinstance(data, dict) and isinstance(data.get("corrections"), list):
        data = data["corrections"]
    if not isinstance(data, list):
        raise CorrectionError(f"{path}: must be a JSON list of {{row, col, class, reason}} "
                              "(or an object with a corrections list)")
    return data


def apply_corrections(classes: np.ndarray, lat: np.ndarray, lon: np.ndarray, any_on_globe: np.ndarray,
                      corrections: Sequence[Dict[str, Any]]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Apply corrections in order to generated classes; return new (classes, lat, lon) with
    locations only on land and ocean studs. ``lat``/``lon`` hold a location for every stud with an
    on-globe subsample (``any_on_globe``). Errors: not ``{row, col, class, reason}``, off the board,
    an unknown class, an empty reason, a stale correction (the stud already has that class), or
    margin to land/ocean on a stud without on-globe subsamples (it would have no location)."""
    out = np.array(classes, dtype="U1", copy=True)
    H, W = out.shape
    for i, c in enumerate(corrections, start=1):
        where = f"correction {i}"
        if not isinstance(c, dict) or set(c) != set(CORRECTION_KEYS):
            raise CorrectionError(f"{where}: must be exactly {{row, col, class, reason}}, not {c!r}")
        r, col, k, reason = c["row"], c["col"], c["class"], c["reason"]
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in (r, col)) or \
                not (0 <= r < H and 0 <= col < W):
            raise CorrectionError(f"{where}: row {r!r}, column {col!r} is outside the {H} x {W} board")
        if k not in CLASS_CODE:
            raise CorrectionError(f"{where}: class must be land, ocean or margin, not {k!r}")
        if not isinstance(reason, str) or not reason.strip():
            raise CorrectionError(f"{where}: the reason must be a non-empty string")
        code = CLASS_CODE[k]
        if out[r, col] == code:
            raise CorrectionError(f"{where}: stale: row {r}, column {col} is already {k}")
        if code != "M" and not bool(any_on_globe[r, col]):
            raise CorrectionError(f"{where}: row {r}, column {col} has no on-globe subsample, so it cannot "
                                  f"be {k} (it would have no location)")
        out[r, col] = code
    keep = out != "M"
    return out, np.where(keep, lat, np.nan), np.where(keep, lon, np.nan)


# --- the confirmation ------------------------------------------------------------------------

CONFIRMATION_ROLE = "project owner"
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def confirmation(date: str) -> Dict[str, str]:
    """``{"role": "project owner", "date": date}`` (no personal name); ``date`` is YYYY-MM-DD."""
    if not isinstance(date, str) or not _DATE.match(date):
        raise ValueError(f"the confirmation date must be YYYY-MM-DD, not {date!r}")
    _dt.date.fromisoformat(date)
    return {"role": CONFIRMATION_ROLE, "date": date}


def same_layout(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """Same classes and locations (as written)."""
    na, nb = normalise({k: a.get(k) for k in ("classes", "locations")}), \
        normalise({k: b.get(k) for k in ("classes", "locations")})
    return na == nb


def resolve_confirmation(doc: Dict[str, Any], committed: Optional[Dict[str, Any]],
                         confirmed_on: Optional[str]) -> Optional[Dict[str, str]]:
    """The confirmation to write: ``confirmed_on`` when given; else the committed file's, while
    classes and locations are unchanged; else none."""
    if confirmed_on is not None:
        return confirmation(confirmed_on)
    if not committed or not committed.get("confirmation"):
        return None
    if not same_layout(doc, committed):
        return None
    conf = committed["confirmation"]
    if not isinstance(conf, dict) or set(conf) != {"role", "date"} or conf["role"] != CONFIRMATION_ROLE:
        raise ValueError("the committed confirmation must be exactly {role: \"project owner\", date}")
    return confirmation(conf["date"])


# --- differences -----------------------------------------------------------------------------

IGNORED = {("source", "generated_on")}
_SECTION_COLUMNS = "ABCDEFGH"


def _stud(r: int, c: int) -> str:
    return f"row {r}, column {c} (section {_SECTION_COLUMNS[c // 16] if c // 16 < 8 else '?'}{r // 16 + 1})"


def _short(v: Any) -> str:
    s = json.dumps(v, ensure_ascii=False)
    return s if len(s) <= 80 else s[:77] + "..."


def _diff(a: Any, b: Any, path: Tuple[str, ...], out: List[str]) -> None:
    name = ".".join(path)
    if path in IGNORED or a == b:
        return
    if path == ("classes",) and isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for r, (ra, rb) in enumerate(zip(a, b)):
            if ra == rb:
                continue
            if not (isinstance(ra, str) and isinstance(rb, str) and len(ra) == len(rb)):
                out.append(f"classes: row {r}: committed {_short(ra)}, regenerated {_short(rb)}")
                continue
            for c, (ka, kb) in enumerate(zip(ra, rb)):
                if ka != kb:
                    out.append(f"classes: {_stud(r, c)}: committed {ka}, regenerated {kb}")
        return
    if path in (("locations", "lat"), ("locations", "lon")) and isinstance(a, list) and isinstance(b, list) \
            and len(a) == len(b) and all(isinstance(x, list) and isinstance(y, list) and len(x) == len(y)
                                         for x, y in zip(a, b)):
        for r, (ra, rb) in enumerate(zip(a, b)):
            for c, (va, vb) in enumerate(zip(ra, rb)):
                if va != vb:
                    out.append(f"{name}: {_stud(r, c)}: committed {va}, regenerated {vb}")
        return
    if isinstance(a, dict) and isinstance(b, dict):
        for k in list(a) + [k for k in b if k not in a]:
            if k not in a:
                out.append(f"{name}.{k}: missing in the committed file" if name else f"{k}: missing in the "
                           "committed file")
            elif k not in b:
                out.append(f"{name}.{k}: not regenerated" if name else f"{k}: not regenerated")
            else:
                _diff(a[k], b[k], path + (k,), out)
        return
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b) and \
            path in (("projection", "check_points"), ("corrections",)):
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                out.append(f"{name}[{i}]: committed {_short(x)}, regenerated {_short(y)}")
        return
    out.append(f"{name}: committed {_short(a)}, regenerated {_short(b)}")


def differences(committed: Dict[str, Any], regenerated: Dict[str, Any]) -> List[str]:
    """What differs between the committed file and the regenerated document, every field but
    ``source.generated_on`` (both as read back from JSON: ``normalise``)."""
    out: List[str] = []
    _diff(committed, regenerated, (), out)
    return out

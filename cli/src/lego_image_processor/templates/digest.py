"""The layout digest of a template (data-model.md TemplateLayoutDigest.layout_sha256).

``layout_sha256(doc)`` is the SHA-256 of the canonical JSON (UTF-8, keys sorted, no whitespace,
``separators=(",", ":")``, ``ensure_ascii=False``) of the part of a template document that decides
the layout: ``id``, ``board``, ``parts``, ``projection`` (``name``, ``proj``, ``lat_1``, ``lon_0``,
``fit``), ``classes`` and ``locations`` (contracts/template-file.md "Layout digest").

It identifies the layout, not the file: ``title``, ``description``, ``check_points``, ``counts``,
``source``, ``corrections``, ``confirmation`` and ``disclaimer`` are left out, and corrections
count only through ``classes``. Writing the owner's confirmation, or a test copy with a test
confirmation, leaves it unchanged; files that depend on the layout (the template's ice file)
record it. Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping

PROJECTION_KEYS = ("name", "proj", "lat_1", "lon_0", "fit")


def layout_document(doc: Mapping[str, Any]) -> Dict[str, Any]:
    """The object the digest is taken of (a new dict; ``doc`` is not changed)."""
    proj = doc["projection"]
    locations = doc["locations"]
    return {"id": doc["id"], "board": doc["board"], "parts": doc["parts"],
            "projection": {k: proj[k] for k in PROJECTION_KEYS},
            "classes": list(doc["classes"]),
            "locations": {"lat": locations["lat"], "lon": locations["lon"]}}


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def layout_sha256(doc: Mapping[str, Any]) -> str:
    """SHA-256 (hex) of the canonical JSON of the template's layout fields."""
    return hashlib.sha256(canonical_json(layout_document(doc)).encode("utf-8")).hexdigest()

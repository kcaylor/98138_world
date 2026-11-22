"""The built output as the service sees it: manifest load, start-up check, lookups (FR-018).

This module does not import ``lego_image_processor``: the running service only reads what the
build step wrote. Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import COMBINATIONS

FORMAT_VERSION = "1"
DOWNLOAD_KINDS = ("layout", "parts", "parts-1kit", "bricklink", "rebrickable", "bricklink-1kit",
                  "rebrickable-1kit", "sheets-letter", "sheets-a4")
IMAGE_KINDS = ("preview", "thumb")
KINDS = DOWNLOAD_KINDS + IMAGE_KINDS


class CatalogError(RuntimeError):
    """The output directory cannot be served."""


@dataclass(frozen=True)
class MapEntry:
    id: str
    title: str
    description: str
    data: Dict[str, Any]

    @property
    def default_combination(self) -> str:
        """The combination the recipe hangs by default (its ``arrangement`` key; feature 009)."""
        return self.data.get("default_combination") or "A"

    def variant(self, combination: str) -> Optional[Dict[str, Any]]:
        return self.data["variants"].get(combination)


class Catalog:
    def __init__(self, root: Path, manifest: Dict[str, Any], raw: bytes):
        self.root = root
        self.manifest = manifest
        self.raw = raw
        self.maps: List[MapEntry] = [MapEntry(m["id"], m["title"], m.get("description", ""), m)
                                     for m in manifest["maps"]]
        self._maps = {m.id: m for m in self.maps}
        self._arr = {a["id"]: a for a in manifest["arrangements"]}
        self._files: Dict[tuple, Path] = {}
        for m in self.maps:
            for c, v in m.data["variants"].items():
                for kind, f in v["files"].items():
                    self._files[(m.id, c, kind)] = root / f["path"]

    @property
    def variant_count(self) -> int:
        return sum(len(m.data["variants"]) for m in self.maps)

    def map(self, map_id: str) -> Optional[MapEntry]:
        return self._maps.get(map_id)

    def arrangement(self, combination: str) -> Optional[Dict[str, Any]]:
        return self._arr.get(combination)

    def file(self, map_id: str, combination: str, kind: str) -> Optional[Path]:
        return self._files.get((map_id, combination, kind))

    def file_entry(self, map_id: str, combination: str, kind: str) -> Optional[Dict[str, Any]]:
        m = self.map(map_id)
        v = m.variant(combination) if m else None
        return v["files"].get(kind) if v else None

    @classmethod
    def load(cls, root) -> "Catalog":
        root = Path(root).resolve()
        p = root / "manifest.json"
        try:
            raw = p.read_bytes()
        except OSError as exc:
            raise CatalogError(f"no manifest at {p} ({exc.strerror or exc}); run the build step: "
                               "python -m web98138.prebuild --out DIR") from exc
        try:
            manifest = json.loads(raw)
        except ValueError as exc:
            raise CatalogError(f"{p}: not JSON ({exc})") from exc
        if manifest.get("format_version") != FORMAT_VERSION:
            raise CatalogError(f"{p}: manifest format {manifest.get('format_version')!r}, expected "
                               f"{FORMAT_VERSION!r}")
        if not manifest.get("maps"):
            raise CatalogError(f"{p}: no maps")
        if sorted(a["id"] for a in manifest.get("arrangements", [])) != list(COMBINATIONS):
            raise CatalogError(f"{p}: arrangements must be {', '.join(COMBINATIONS)}")
        for m in manifest["maps"]:
            if sorted(m.get("variants", {})) != list(COMBINATIONS):
                raise CatalogError(f"{m.get('id')}: combinations {sorted(m.get('variants', {}))}, "
                                   f"expected {', '.join(COMBINATIONS)}")
            for c, v in m["variants"].items():
                for kind, f in v["files"].items():
                    if kind not in KINDS:
                        raise CatalogError(f"{m['id']} {c}: unknown file kind {kind!r}")
                    target = (root / f["path"]).resolve()
                    if root not in target.parents:
                        raise CatalogError(f"{m['id']} {c} {kind}: path {f['path']!r} is outside "
                                           f"{root}")
                    if not target.is_file():
                        raise CatalogError(f"{m['id']} {c} {kind}: missing file {target}")
                    if target.stat().st_size != f["bytes"]:
                        raise CatalogError(f"{m['id']} {c} {kind}: {target} has size "
                                           f"{target.stat().st_size}, manifest says {f['bytes']}")
        return cls(root, manifest, raw)

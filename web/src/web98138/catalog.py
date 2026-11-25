"""The built output as the service sees it: manifest load, start-up check, lookups (FR-018).

This module does not import ``lego_image_processor``: the running service only reads what the
build step wrote. Feature 016: a map may also have ``template_variants`` (one per map template,
keyed by the template's id, which is listed in the manifest's ``templates`` and is never A, B or C);
they are checked like kit variants. A map's ``stickers`` block (feature 017) is optional, so an
older manifest still serves. Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import COMBINATIONS

FORMAT_VERSION = "1"
DOWNLOAD_KINDS = ("layout", "parts", "parts-1kit", "bricklink", "rebrickable", "bricklink-1kit",
                  "rebrickable-1kit", "sheets-letter", "sheets-a4")
IMAGE_KINDS = ("preview", "thumb")
DATA_KINDS = ("cells",)   # feature 015: palette chooser data, served inline, never a download
KINDS = DOWNLOAD_KINDS + IMAGE_KINDS + DATA_KINDS
ESTIMATE_KINDS = ("full", "one_kit")
TEMPLATE_KEYS = ("id", "title", "projection", "board", "counts", "rehang", "description", "source")
# feature 017: one sticker set per map and template (contracts/web.md "Catalog check"). The kit
# template's id is lego_image_processor.templates.KIT_TEMPLATE_ID (feature 016); the service never
# imports the library, so it is spelled here and a web test checks that the two agree.
KIT_TEMPLATE_ID = "kit-31203"
STICKER_TEMPLATES = (KIT_TEMPLATE_ID,)
STICKER_KINDS = ("stickers-letter", "stickers-a4", "sticker-small", "sticker-large")
STICKER_IMAGES = ("sticker-small", "sticker-large")     # served inline for <img>, and downloads
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class CatalogError(RuntimeError):
    """The output directory cannot be served."""


def _get(d: Any, path: str) -> Any:
    for key in path.split("."):
        if not isinstance(d, dict) or key not in d:
            raise KeyError(path)
        d = d[key]
    return d


def _check(d: Any, path: str, ok, where: str, what: str) -> None:
    try:
        v = _get(d, path)
    except KeyError:
        raise CatalogError(f"{where}{path}: missing") from None
    if not ok(v):
        raise CatalogError(f"{where}{path}: must be {what}, found {v!r}")


def _is_int(v: Any) -> bool:
    return type(v) is int


def _is_bool(v: Any) -> bool:
    return type(v) is bool


def _is_text(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def all_variants(m: Dict[str, Any]):
    """(key, entry) of a manifest map row's kit variants, then its template variants (016)."""
    yield from m["variants"].items()
    yield from (m.get("template_variants") or {}).items()


def _check_file(root: Path, f: Any, where: str) -> None:
    """A listed file: inside the root, present, of the recorded size (``where`` names it)."""
    if not isinstance(f, dict) or not isinstance(f.get("path"), str) or not _is_int(f.get("bytes")):
        raise CatalogError(f"{where}: must be an object with path and bytes")
    target = (root / f["path"]).resolve()
    if root not in target.parents:
        raise CatalogError(f"{where}: path {f['path']!r} is outside {root}")
    if not target.is_file():
        raise CatalogError(f"{where}: missing file {target}")
    if target.stat().st_size != f["bytes"]:
        raise CatalogError(f"{where}: {target} has size {target.stat().st_size}, manifest says "
                           f"{f['bytes']}")


def _is_list(v: Any) -> bool:
    return isinstance(v, list) and bool(v)


def check_stickers(root: Path, m: Dict[str, Any]) -> None:
    """A map's optional ``stickers`` block (feature 017): known templates, the four sticker kinds,
    each file as a variant file, and the texts the map page shows."""
    if "stickers" not in m:
        return
    blocks = m["stickers"]
    if not isinstance(blocks, dict):
        raise CatalogError(f"{m['id']} stickers: must be an object, found {type(blocks).__name__}")
    for template_id, st in blocks.items():
        if template_id not in STICKER_TEMPLATES:
            raise CatalogError(f"{m['id']} stickers: unknown template {template_id!r} (known: "
                               f"{', '.join(STICKER_TEMPLATES)})")
        where = f"{m['id']} stickers {template_id}: "
        _check(st, "files", lambda v: isinstance(v, dict), where, "an object")
        for kind in st["files"]:
            if kind not in STICKER_KINDS:
                raise CatalogError(f"{where}unknown file kind {kind!r}")
        for kind in STICKER_KINDS:
            if kind not in st["files"]:
                raise CatalogError(f"{where}missing file kind {kind!r}")
            _check_file(root, st["files"][kind], f"{m['id']} stickers {template_id} {kind}")
        for path in ("title", "line", "alt.small", "alt.large", "notes.printed", "notes.colors"):
            _check(st, path, _is_text, where, "text")
        for path in ("legend", "credit", "plaques"):
            _check(st, path, _is_list, where, "a non-empty list")


def check_prices(manifest: Dict[str, Any]) -> None:
    """Price estimates (feature 011; contracts/web.md "Catalog check")."""
    prices = manifest.get("prices")
    if prices is None:
        for m in manifest["maps"]:
            for c, v in all_variants(m):
                if "estimates" in v:
                    raise CatalogError(f"{m['id']} {c}: estimates present but the manifest has no "
                                       "prices block")
        return
    _check(manifest, "prices.snapshot.sha256",
           lambda v: isinstance(v, str) and bool(_SHA256.match(v)), "", "64 hex digits")
    _check(manifest, "prices.snapshot.retrieved_on",
           lambda v: isinstance(v, str) and bool(re.match(r"^\d{4}-\d{2}-\d{2}$", v)), "",
           "a date")
    for path in ("prices.source.url", "prices.estimate_note", "prices.attribution"):
        _check(manifest, path, _is_text, "", "text")
    for m in manifest["maps"]:
        for c, v in all_variants(m):
            where = f"{m['id']} {c}: "
            for kind in ESTIMATE_KINDS:
                base = f"estimates.{kind}"
                _check(v, base, lambda e: isinstance(e, dict), where, "an object")
                for stat in ("average", "low", "high"):
                    _check(v, f"{base}.whole_dollars.{stat}", _is_int, where, "an integer")
                for flag in ("complete", "nothing_to_buy"):
                    _check(v, f"{base}.{flag}", _is_bool, where, "true or false")
                for n in ("pieces", "lots"):
                    _check(v, f"{base}.unpriced.{n}", _is_int, where, "an integer")


def check_templates(manifest: Dict[str, Any]) -> List[str]:
    """The manifest's ``templates`` list (feature 016; absent = none); returns the ids."""
    templates = manifest.get("templates", [])
    if not isinstance(templates, list):
        raise CatalogError(f"templates: must be a list, found {templates!r}")
    ids: List[str] = []
    for i, t in enumerate(templates):
        where = f"templates[{i}]."
        if not isinstance(t, dict):
            raise CatalogError(f"templates[{i}]: must be an object")
        for key in TEMPLATE_KEYS:
            if key not in t:
                raise CatalogError(f"{where}{key}: missing")
        for key in ("id", "title", "projection"):
            _check(t, key, _is_text, where, "text")
        _check(t, "rehang", _is_bool, where, "true or false")
        if t["id"] in COMBINATIONS:
            raise CatalogError(f"{where}id: a template id must not be A, B or C")
        if t["id"] in ids:
            raise CatalogError(f"{where}id: template {t['id']!r} listed twice")
        ids.append(t["id"])
    return ids


def _check_files(root: Path, where: str, files: Dict[str, Any]) -> None:
    """Every file of a variant: a known kind, inside the root, present, of the manifest's size."""
    for kind, f in files.items():
        if kind not in KINDS:
            raise CatalogError(f"{where}: unknown file kind {kind!r}")
        target = (root / f["path"]).resolve()
        if root not in target.parents:
            raise CatalogError(f"{where} {kind}: path {f['path']!r} is outside {root}")
        if not target.is_file():
            raise CatalogError(f"{where} {kind}: missing file {target}")
        if target.stat().st_size != f["bytes"]:
            raise CatalogError(f"{where} {kind}: {target} has size {target.stat().st_size}, "
                               f"manifest says {f['bytes']}")


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

    @property
    def template_ids(self) -> tuple:
        """The templates this map has a variant on (feature 016), in the manifest's order."""
        return tuple(self.data.get("template_variants") or ())

    def variant(self, key: str) -> Optional[Dict[str, Any]]:
        """A kit variant (``A``, ``B``, ``C``) or a template variant (a template id)."""
        v = self.data["variants"].get(key)
        if v is None:
            v = (self.data.get("template_variants") or {}).get(key)
        return v


class Catalog:
    def __init__(self, root: Path, manifest: Dict[str, Any], raw: bytes):
        self.root = root
        self.manifest = manifest
        self.raw = raw
        self.maps: List[MapEntry] = [MapEntry(m["id"], m["title"], m.get("description", ""), m)
                                     for m in manifest["maps"]]
        self._maps = {m.id: m for m in self.maps}
        self._arr = {a["id"]: a for a in manifest["arrangements"]}
        self.templates: List[Dict[str, Any]] = list(manifest.get("templates") or [])
        self._templates = {t["id"]: t for t in self.templates}
        self._files: Dict[tuple, Path] = {}
        self._stickers: Dict[tuple, Path] = {}
        for m in self.maps:
            for c, v in all_variants(m.data):
                for kind, f in v["files"].items():
                    self._files[(m.id, c, kind)] = root / f["path"]
            for template_id, st in m.data.get("stickers", {}).items():
                for kind, f in st["files"].items():
                    self._stickers[(m.id, template_id, kind)] = root / f["path"]

    @property
    def variant_count(self) -> int:
        """Kit and template variants."""
        return sum(len(m.data["variants"]) + len(m.template_ids) for m in self.maps)

    def template(self, template_id: str) -> Optional[Dict[str, Any]]:
        return self._templates.get(template_id)

    def map(self, map_id: str) -> Optional[MapEntry]:
        return self._maps.get(map_id)

    def arrangement(self, combination: str) -> Optional[Dict[str, Any]]:
        return self._arr.get(combination)

    def file(self, map_id: str, combination: str, kind: str) -> Optional[Path]:
        return self._files.get((map_id, combination, kind))

    def file_entry(self, map_id: str, combination: str, kind: str) -> Optional[Dict[str, Any]]:
        """The manifest entry of a kit (``A``-``C``) or template variant's file."""
        m = self.map(map_id)
        v = m.variant(combination) if m else None
        return v["files"].get(kind) if v else None

    def stickers(self, map_id: str, template_id: str) -> Optional[Dict[str, Any]]:
        """A map's sticker block for ``template_id`` (feature 017), or None."""
        m = self.map(map_id)
        return m.data.get("stickers", {}).get(template_id) if m else None

    def sticker_file(self, map_id: str, template_id: str, kind: str) -> Optional[Path]:
        return self._stickers.get((map_id, template_id, kind))

    def sticker_entry(self, map_id: str, template_id: str, kind: str) -> Optional[Dict[str, Any]]:
        st = self.stickers(map_id, template_id)
        return st["files"].get(kind) if st else None

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
        template_ids = check_templates(manifest)
        for m in manifest["maps"]:
            if sorted(m.get("variants", {})) != list(COMBINATIONS):
                raise CatalogError(f"{m.get('id')}: combinations {sorted(m.get('variants', {}))}, "
                                   f"expected {', '.join(COMBINATIONS)}")
            tv = m.get("template_variants", {})
            if not isinstance(tv, dict):
                raise CatalogError(f"{m['id']}: template_variants must be an object")
            for t, v in tv.items():
                if t in COMBINATIONS:
                    raise CatalogError(f"{m['id']} {t}: a template variant key must not be A, B or C")
                if t not in template_ids:
                    raise CatalogError(f"{m['id']} {t}: template not listed in templates")
                if v.get("template") != t:
                    raise CatalogError(f"{m['id']} {t}: template must be {t!r}, found {v.get('template')!r}")
            for c, v in all_variants(m):
                _check_files(root, f"{m['id']} {c}", v["files"])
            check_stickers(root, m)
        check_prices(manifest)
        return cls(root, manifest, raw)

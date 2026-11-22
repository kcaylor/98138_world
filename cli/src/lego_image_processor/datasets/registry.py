"""Registry of canonical datasets (``data/datasets.json``): pinned URL, size, SHA-256, citation.

Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REGISTRY_PATH = DATA_DIR / "datasets.json"

KINDS = ("download", "packaged", "local")
FORMATS = ("dods", "netcdf3", "npy", "kit-design")
CLASS_RULES = ("split_at", "missing_is_land", "kit_mask")
REDUCES = ("annual-mean",)
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{0,63}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class RegistryError(ValueError):
    """The registry file (or a local dataset declaration) breaks a rule."""


@dataclass(frozen=True)
class DatasetEntry:
    id: str
    version: str
    kind: str
    title: str
    publisher: str
    format: str
    license: str
    citation: str
    variables: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    class_rule: Dict[str, Any] = field(default_factory=dict)
    url: str = ""
    size: Optional[int] = None
    sha256: str = ""
    filename: str = ""
    doi: str = ""
    acknowledgement: str = ""
    notes: str = ""
    grid: Dict[str, Any] = field(default_factory=dict)
    path: Optional[Path] = None  # local entries only

    def __hash__(self) -> int:  # dict fields make the generated hash fail
        return hash((self.id, self.version, self.kind, self.sha256, str(self.path)))

    def provenance(self) -> Dict[str, Any]:
        """The fields written into layout metadata and reports (constitution IV)."""
        out = {"id": self.id, "version": self.version, "title": self.title,
               "publisher": self.publisher, "license": self.license, "citation": self.citation}
        if self.sha256:
            out["sha256"] = self.sha256
        if self.doi:
            out["doi"] = self.doi
        if self.acknowledgement:
            out["acknowledgement"] = self.acknowledgement
        if self.url:
            out["url"] = self.url
        if self.kind == "local" and self.path is not None:
            out["local_file"] = self.path.name
        return out


@dataclass(frozen=True)
class Registry:
    version: str
    entries: Tuple[DatasetEntry, ...]
    source: Dict[str, Any]

    def get(self, dataset_id: str) -> DatasetEntry:
        for e in self.entries:
            if e.id == dataset_id:
                return e
        raise KeyError(dataset_id)


def _str(row: Dict[str, Any], key: str, where: str, required: bool = True) -> str:
    v = row.get(key, "")
    if v is None:
        v = ""
    if not isinstance(v, str):
        raise RegistryError(f"{where}: {key} must be a string")
    if required and not v.strip():
        raise RegistryError(f"{where}: {key} is required")
    return v


def parse_entry(row: Dict[str, Any], where: str = "dataset") -> DatasetEntry:
    """Validate one registry row (data-model.md DatasetEntry rules)."""
    if not isinstance(row, dict):
        raise RegistryError(f"{where}: must be an object")
    did = _str(row, "id", where)
    if not _ID_RE.match(did):
        raise RegistryError(f"{where}: id {did!r} must match {_ID_RE.pattern}")
    where = f"dataset {did}"
    kind = row.get("kind")
    if kind not in KINDS:
        raise RegistryError(f"{where}: kind must be one of {KINDS}")
    fmt = row.get("format")
    if fmt not in FORMATS:
        raise RegistryError(f"{where}: format {fmt!r} must be one of {FORMATS}")
    for key in ("license", "citation"):
        _str(row, key, where)
    rule = row.get("class_rule") or {}
    if not isinstance(rule, dict) or any(k not in CLASS_RULES for k in rule) or len(rule) > 1:
        raise RegistryError(f"{where}: class_rule must be empty or one of {CLASS_RULES}")
    if "split_at" in rule and not isinstance(rule["split_at"], (int, float)):
        raise RegistryError(f"{where}: class_rule.split_at must be a number")
    variables = row.get("variables") or {}
    if not isinstance(variables, dict):
        raise RegistryError(f"{where}: variables must be an object")
    for name, spec in variables.items():
        if not isinstance(spec, dict):
            raise RegistryError(f"{where}: variables.{name} must be an object")
        if "reduce" in spec and spec["reduce"] not in REDUCES:
            raise RegistryError(f"{where}: variables.{name}.reduce must be one of {REDUCES}")
    size = row.get("size")
    sha = row.get("sha256", "") or ""
    if kind == "download":
        for key in ("url", "size", "sha256", "filename"):
            if row.get(key) in (None, ""):
                raise RegistryError(f"{where}: download entries need {key}")
        if not str(row["url"]).startswith("https://"):
            raise RegistryError(f"{where}: url must use https")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise RegistryError(f"{where}: size must be a positive integer (bytes)")
    if sha and not _SHA_RE.match(sha):
        raise RegistryError(f"{where}: sha256 must be 64 lowercase hex characters")
    if kind == "local" and not sha:
        raise RegistryError(f"{where}: local files need sha256")
    if fmt == "npy":
        grid = row.get("grid") or {}
        for key in ("lat", "lon"):
            v = grid.get(key)
            if not (isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v)
                    and v[0] < v[1]):
                raise RegistryError(f"{where}: npy entries need grid.{key} = [min, max]")
    path = row.get("path")
    return DatasetEntry(
        id=did, version=_str(row, "version", where), kind=kind, title=_str(row, "title", where),
        publisher=_str(row, "publisher", where, required=False), format=fmt,
        license=row["license"], citation=row["citation"], variables=dict(variables),
        class_rule=dict(rule), url=row.get("url", "") or "", size=size, sha256=sha,
        filename=row.get("filename", "") or "", doi=row.get("doi", "") or "",
        acknowledgement=row.get("acknowledgement", "") or "", notes=row.get("notes", "") or "",
        grid=dict(row.get("grid") or {}), path=Path(path) if path else None,
    )


def parse_registry(data: Dict[str, Any]) -> Registry:
    rows = data.get("datasets")
    if not isinstance(rows, list) or not rows:
        raise RegistryError("datasets.json: datasets must be a non-empty list")
    entries = [parse_entry(r, f"datasets[{i}]") for i, r in enumerate(rows)]
    ids = [e.id for e in entries]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        raise RegistryError(f"datasets.json: duplicate dataset ids {dup}")
    return Registry(version=str(data.get("registry_version", "")), entries=tuple(entries),
                    source=dict(data.get("source") or {}))


@lru_cache(maxsize=None)
def _load(path: Path) -> Registry:
    with open(path, "r", encoding="utf-8") as f:
        return parse_registry(json.load(f))


def load_registry(path: Optional[Path] = None) -> Registry:
    """The shipped registry (package data; no network)."""
    return _load(Path(path) if path else REGISTRY_PATH)


def get_entry(dataset_id: str) -> DatasetEntry:
    """A registry entry by id; ``KeyError`` if unknown."""
    return load_registry().get(dataset_id)

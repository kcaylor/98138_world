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
FORMATS = ("dods", "netcdf3", "npy", "kit-design", "geotiff", "netcdf4")
CLASS_RULES = ("split_at", "missing_is_land", "kit_mask", "land_from")
REDUCES = ("annual-mean", "climatology-mean")
GEOTIFF_VARIABLE_KEYS = ("scale_factor", "add_offset", "valid_min", "valid_max", "fill")
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
    content_sha256: str = ""     # feature 012: checksum of the decoded data (files built on request)
    http_only: str = ""          # feature 012: why the pinned URL is plain HTTP (needs sha256)
    files: Tuple["DatasetFile", ...] = ()  # feature 013: the pinned files of a multi-file entry

    def __hash__(self) -> int:  # dict fields make the generated hash fail
        return hash((self.id, self.version, self.kind, self.sha256, self.content_sha256, str(self.path),
                     self.files))

    @property
    def files_sha256(self) -> str:
        """SHA-256 of the multi-file manifest, lines ``"<sha256>  <name>\\n"`` in list order (013)."""
        import hashlib

        if not self.files:
            return ""
        return hashlib.sha256("".join(f"{f.sha256}  {f.name}\n" for f in self.files).encode()).hexdigest()

    @property
    def mask_dataset_id(self) -> Optional[str]:
        """The dataset a ``land_from`` class rule takes its land/ocean split from (feature 012)."""
        rule = (self.class_rule or {}).get("land_from")
        return rule.get("dataset") if isinstance(rule, dict) else None

    @property
    def splits_land(self) -> bool:
        """True when the entry's class rule tells land from ocean pixels."""
        return bool(self.class_rule) and "kit_mask" not in self.class_rule

    def provenance(self) -> Dict[str, Any]:
        """The fields written into layout metadata and reports (constitution IV)."""
        out = {"id": self.id, "version": self.version, "title": self.title,
               "publisher": self.publisher, "license": self.license, "citation": self.citation}
        if self.sha256:
            out["sha256"] = self.sha256
        if self.content_sha256:
            out["content_sha256"] = self.content_sha256
        if self.files:
            out["files"] = len(self.files)
            out["files_sha256"] = self.files_sha256
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
class DatasetFile:
    """One pinned file of a multi-file download entry (feature 013)."""

    url: str
    size: int
    sha256: str

    @property
    def name(self) -> str:
        return self.url.rstrip("/").rsplit("/", 1)[-1]


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
    if "land_from" in rule:
        lf = rule["land_from"]
        if (not isinstance(lf, dict) or set(lf) != {"dataset", "variable", "split_at"}
                or not isinstance(lf.get("dataset"), str) or not isinstance(lf.get("variable"), str)
                or isinstance(lf.get("split_at"), bool) or not isinstance(lf.get("split_at"), (int, float))):
            raise RegistryError(f"{where}: class_rule.land_from must be {{dataset, variable, split_at}} "
                                "(a registry id, its variable, and a number)")
        if lf["dataset"] == did:
            raise RegistryError(f"{where}: class_rule.land_from must name another dataset")
    variables = row.get("variables") or {}
    if not isinstance(variables, dict):
        raise RegistryError(f"{where}: variables must be an object")
    for name, spec in variables.items():
        if not isinstance(spec, dict):
            raise RegistryError(f"{where}: variables.{name} must be an object")
        if "reduce" in spec and spec["reduce"] not in REDUCES:
            raise RegistryError(f"{where}: variables.{name}.reduce must be one of {REDUCES}")
        if spec.get("reduce") == "climatology-mean" and fmt not in ("netcdf3", "netcdf4"):
            raise RegistryError(f"{where}: variables.{name}.reduce climatology-mean needs format netcdf3 "
                                "or netcdf4")
        for key in GEOTIFF_VARIABLE_KEYS:
            if key in spec and (isinstance(spec[key], bool) or not isinstance(spec[key], (int, float))):
                raise RegistryError(f"{where}: variables.{name}.{key} must be a number")
    if fmt == "geotiff":
        block = (row.get("grid") or {}).get("block", 1)
        if isinstance(block, bool) or not isinstance(block, int) or block < 1:
            raise RegistryError(f"{where}: grid.block must be an integer >= 1")
    size = row.get("size")
    sha = row.get("sha256", "") or ""
    content_sha = row.get("content_sha256", "") or ""
    http_only = row.get("http_only", "") or ""
    if not isinstance(http_only, str):
        raise RegistryError(f"{where}: http_only must be a string (the reason)")
    if content_sha and not _SHA_RE.match(content_sha):
        raise RegistryError(f"{where}: content_sha256 must be 64 lowercase hex characters")
    if content_sha and fmt != "netcdf3":
        raise RegistryError(f"{where}: content_sha256 is supported for netcdf3 files only")
    files = _files(row.get("files"), where, kind, http_only, sha or content_sha)
    if kind == "download":
        for key in ("url", "size") + (() if files else ("filename",)):
            if row.get(key) in (None, ""):
                raise RegistryError(f"{where}: download entries need {key}")
        if not files and bool(sha) == bool(content_sha):
            raise RegistryError(f"{where}: download entries need exactly one of sha256 and "
                                "content_sha256 (or a files list)")
        url = str(row["url"])
        if url.startswith("http://"):
            if not http_only.strip():
                raise RegistryError(f"{where}: url must use https (or give http_only, the reason the "
                                    "host serves plain HTTP only)")
            if not sha and not files:
                raise RegistryError(f"{where}: an http_only entry needs sha256 (the file checksum)")
        elif not url.startswith("https://"):
            raise RegistryError(f"{where}: url must use https")
        elif http_only and not any(f.url.startswith("http://") for f in files):
            raise RegistryError(f"{where}: http_only is only for http:// URLs")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise RegistryError(f"{where}: size must be a positive integer (bytes)")
        if files and size != sum(f.size for f in files):
            raise RegistryError(f"{where}: size must be the total of the files ({sum(f.size for f in files)})")
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
        content_sha256=content_sha, http_only=http_only, files=files,
    )


def _files(raw: Any, where: str, kind: str, http_only: str, checksum: str) -> Tuple[DatasetFile, ...]:
    """The optional ``files`` list of a multi-file download entry (feature 013)."""
    if raw is None:
        return ()
    if kind != "download":
        raise RegistryError(f"{where}: files is for download entries only")
    if checksum:
        raise RegistryError(f"{where}: a files list pins each file; leave out sha256 and content_sha256")
    if not isinstance(raw, list) or len(raw) < 2:
        raise RegistryError(f"{where}: files must be a list of at least 2 {{url, size, sha256}}")
    out = []
    for i, item in enumerate(raw):
        w = f"{where}: files[{i}]"
        if not isinstance(item, dict) or set(item) != {"url", "size", "sha256"}:
            raise RegistryError(f"{w} must be {{url, size, sha256}}")
        url, size, sha = item["url"], item["size"], item["sha256"]
        if not isinstance(url, str) or not (url.startswith("https://") or
                                            (url.startswith("http://") and http_only.strip())):
            raise RegistryError(f"{w}.url must use https")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise RegistryError(f"{w}.size must be a positive integer (bytes)")
        if not isinstance(sha, str) or not _SHA_RE.match(sha):
            raise RegistryError(f"{w}.sha256 must be 64 lowercase hex characters")
        out.append(DatasetFile(url=url, size=size, sha256=sha))
    names = [f.name for f in out]
    if len(set(names)) != len(names) or not all(names):
        raise RegistryError(f"{where}: file names (URL basenames) must be unique")
    return tuple(out)


def parse_registry(data: Dict[str, Any]) -> Registry:
    rows = data.get("datasets")
    if not isinstance(rows, list) or not rows:
        raise RegistryError("datasets.json: datasets must be a non-empty list")
    entries = [parse_entry(r, f"datasets[{i}]") for i, r in enumerate(rows)]
    ids = [e.id for e in entries]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        raise RegistryError(f"datasets.json: duplicate dataset ids {dup}")
    for e in entries:
        m = e.mask_dataset_id
        if m is not None:
            if m not in ids:
                raise RegistryError(f"dataset {e.id}: class_rule.land_from names unknown dataset {m!r}")
            target = entries[ids.index(m)]
            if target.mask_dataset_id is not None or target.format == "kit-design":
                raise RegistryError(f"dataset {e.id}: class_rule.land_from dataset {m} must be a plain "
                                    "gridded field")
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

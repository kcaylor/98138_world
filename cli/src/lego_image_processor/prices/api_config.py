"""BrickLink API reference data (``data/bricklink_api.json``; feature 011, research R3).

The base URL, the price-guide path, the item-type map, the OAuth method and the documented daily
limit live in this cited file, not in code (constitution VI, owner decision). ``checked`` stays
false until the owner has compared the values with the live documentation.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union
from urllib.parse import urlsplit

from ..kit.colors import DATA_DIR
from ..kit.source import DISCLAIMER

API_CONFIG_PATH = DATA_DIR / "bricklink_api.json"
FORMAT_VERSION = "1"
TOP_KEYS = ("format_version", "source", "base_url", "price_guide_path", "item_types", "oauth",
            "daily_request_limit")
SOURCE_KEYS = ("title", "documentation", "accessed", "checked", "note", "disclaimer")
SOURCE_REQUIRED = ("title", "documentation", "accessed", "checked", "disclaimer")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class ApiConfig:
    base_url: str
    price_guide_path: str
    item_types: Dict[str, str]
    oauth: Dict[str, str]
    daily_request_limit: int
    source: Dict[str, Any]

    @property
    def checked(self) -> bool:
        return bool(self.source["checked"])

    @property
    def endpoint(self) -> str:
        return f"GET {self.price_guide_path}"

    @property
    def realm(self) -> str:
        return self.oauth.get("realm", "")

    def price_guide_url(self, item_type: str, item_no: str) -> str:
        """``{base_url}/items/PART/98138/price`` for a 005 item type (``P``) and number."""
        return self.base_url + self.price_guide_path.format(type=self.item_types[item_type],
                                                            no=item_no)

    def snapshot_block(self) -> Dict[str, Any]:
        """The ``source.api`` block a fetched snapshot records."""
        return {"base_url": self.base_url, "endpoint": self.endpoint,
                "documentation": [dict(d) for d in self.source["documentation"]],
                "checked": self.checked}

    def fingerprint_block(self) -> Dict[str, Any]:
        """What a resumed fetch must share with the one it continues (R9)."""
        return {"base_url": self.base_url, "price_guide_path": self.price_guide_path,
                "item_types": dict(sorted(self.item_types.items())), "oauth": dict(sorted(self.oauth.items()))}


def _fail(where: str, rule: str):
    raise ValueError(f"bricklink_api.json: {where}: {rule}")


def _https_url(v: Any, where: str, *, base: bool) -> str:
    if not isinstance(v, str) or not v:
        _fail(where, "must be a non-empty string")
    parts = urlsplit(v)
    if parts.scheme != "https" or not parts.netloc:
        _fail(where, "must be an https:// URL")
    if base and (parts.query or parts.fragment or "?" in v):
        _fail(where, "must not have a query")
    if base and v.endswith("/"):
        _fail(where, "must not end with '/'")
    return v


def parse_api_config(data: Any) -> ApiConfig:
    """Validate the decoded file (contracts/price-snapshot-format.md §2); ``ValueError`` names the field."""
    if not isinstance(data, dict):
        _fail("(top level)", "must be an object")
    if data.get("format_version") != FORMAT_VERSION:
        _fail("format_version", f"must be {FORMAT_VERSION!r}")
    for k in data:
        if k not in TOP_KEYS:
            _fail(k, "unknown key")
    for k in TOP_KEYS:
        if k not in data:
            _fail(k, "is required")
    base_url = _https_url(data["base_url"], "base_url", base=True)
    path = data["price_guide_path"]
    if (not isinstance(path, str) or not path.startswith("/") or "{type}" not in path
            or "{no}" not in path):
        _fail("price_guide_path", "must start with '/' and contain {type} and {no}")
    types = data["item_types"]
    if not isinstance(types, dict) or types.get("P") != "PART":
        _fail("item_types", "must map 'P' to 'PART'")
    oauth = data["oauth"]
    if not isinstance(oauth, dict):
        _fail("oauth", "must be an object")
    if oauth.get("version") != "1.0":
        _fail("oauth.version", "must be '1.0'")
    if oauth.get("signature_method") != "HMAC-SHA1":
        _fail("oauth.signature_method", "must be 'HMAC-SHA1'")
    if not isinstance(oauth.get("realm", ""), str):
        _fail("oauth.realm", "must be a string")
    limit = data["daily_request_limit"]
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        _fail("daily_request_limit", "must be an integer > 0")
    source = data["source"]
    if not isinstance(source, dict):
        _fail("source", "must be an object")
    for k in source:
        if k not in SOURCE_KEYS:
            _fail(f"source.{k}", "unknown key")
    for k in SOURCE_REQUIRED:
        if k not in source:
            _fail(f"source.{k}", "is required")
    if not isinstance(source["title"], str) or not source["title"]:
        _fail("source.title", "must be a non-empty string")
    docs = source["documentation"]
    if not isinstance(docs, list) or not docs:
        _fail("source.documentation", "must be a non-empty list")
    for i, d in enumerate(docs):
        if not isinstance(d, dict) or set(d) != {"id", "title", "url"}:
            _fail(f"source.documentation[{i}]", "must have exactly id, title and url")
        for k in ("id", "title"):
            if not isinstance(d[k], str) or not d[k]:
                _fail(f"source.documentation[{i}].{k}", "must be a non-empty string")
        _https_url(d["url"], f"source.documentation[{i}].url", base=False)
    if not isinstance(source["accessed"], str) or not _DATE_RE.match(source["accessed"]):
        _fail("source.accessed", "must be a date YYYY-MM-DD")
    if not isinstance(source["checked"], bool):
        _fail("source.checked", "must be true or false")
    if source["disclaimer"] != DISCLAIMER:
        _fail("source.disclaimer", f"must be {DISCLAIMER!r}")
    return ApiConfig(base_url=base_url, price_guide_path=path, item_types=dict(types),
                     oauth=dict(oauth), daily_request_limit=limit, source=dict(source))


def load_api_config(path: Optional[Union[str, Path]] = None) -> ApiConfig:
    """Load and validate the packaged file (or ``path``)."""
    p = Path(path) if path is not None else API_CONFIG_PATH
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read {p}: {exc.strerror or exc}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"{p}: not JSON ({exc})") from None
    return parse_api_config(data)


__all__ = ["API_CONFIG_PATH", "ApiConfig", "load_api_config", "parse_api_config"]

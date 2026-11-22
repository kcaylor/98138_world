"""Provenance block (``source``) shared by every kit reference data file.

Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

PINNED_URL = "https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6372756.pdf"
PINNED_SHA256 = "b593e2f4befbc227c5b12fec9b58a1bd6141d19b54de5f5336dcc8cc9eb43c4c"
SOURCE_TITLE = "LEGO 31203 World Map building instructions"
DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _require(data: Dict[str, Any], key: str, what: str) -> Any:
    if not isinstance(data, dict) or key not in data:
        raise ValueError(f"{what}: missing required field '{key}'")
    return data[key]


@dataclass(frozen=True)
class Citation:
    """A non-PDF source (catalog page or file) that a reference row refers to by ``id``."""

    id: str
    title: str
    url: str
    accessed: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Citation":
        values = {k: _require(data, k, "citation") for k in ("id", "title", "url", "accessed")}
        for k, v in values.items():
            if not isinstance(v, str) or not v:
                raise ValueError(f"citation: field '{k}' must be a non-empty string")
        if not _DATE_RE.match(values["accessed"]):
            raise ValueError(f"citation '{values['id']}': accessed must be YYYY-MM-DD")
        return cls(**values)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "title": self.title, "url": self.url, "accessed": self.accessed}


@dataclass(frozen=True)
class SourceDocument:
    """Where a reference file's facts come from: the pinned PDF plus cited catalog sources."""

    title: str
    url: str
    sha256: str
    pages: List[int]
    generator: str
    generated_on: str
    citations: List[Citation] = field(default_factory=list)
    disclaimer: str = DISCLAIMER

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceDocument":
        what = "source"
        title = _require(data, "title", what)
        url = _require(data, "url", what)
        sha256 = _require(data, "sha256", what)
        pages = _require(data, "pages", what)
        generator = _require(data, "generator", what)
        generated_on = _require(data, "generated_on", what)
        citations = _require(data, "citations", what)
        disclaimer = _require(data, "disclaimer", what)

        if not isinstance(sha256, str) or not _SHA256_RE.match(sha256):
            raise ValueError("source: sha256 must be 64 lowercase hex characters")
        if sha256 != PINNED_SHA256:
            raise ValueError(
                f"source: sha256 {sha256} differs from the pinned instructions checksum {PINNED_SHA256}"
            )
        if url != PINNED_URL:
            raise ValueError(f"source: url {url!r} differs from the pinned URL {PINNED_URL!r}")
        if not isinstance(pages, list) or not pages or not all(
            isinstance(p, int) and not isinstance(p, bool) and p > 0 for p in pages
        ):
            raise ValueError("source: pages must be a non-empty list of positive integers")
        if not isinstance(generated_on, str) or not _DATE_RE.match(generated_on):
            raise ValueError("source: generated_on must be a date in YYYY-MM-DD form")
        if disclaimer != DISCLAIMER:
            raise ValueError(f"source: disclaimer must be {DISCLAIMER!r}")
        if not isinstance(citations, list):
            raise ValueError("source: citations must be a list")
        parsed = [Citation.from_dict(c) for c in citations]
        ids = [c.id for c in parsed]
        if len(ids) != len(set(ids)):
            raise ValueError("source: citation ids must be unique")
        return cls(
            title=title, url=url, sha256=sha256, pages=list(pages), generator=generator,
            generated_on=generated_on, citations=parsed, disclaimer=disclaimer,
        )

    def citation(self, citation_id: str) -> Citation:
        for c in self.citations:
            if c.id == citation_id:
                return c
        raise KeyError(citation_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "sha256": self.sha256,
            "pages": list(self.pages),
            "generator": self.generator,
            "generated_on": self.generated_on,
            "citations": [c.to_dict() for c in self.citations],
            "disclaimer": self.disclaimer,
        }

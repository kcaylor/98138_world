"""Download, cache and SHA-256 verification of the pinned instructions PDF (standard library)."""

from __future__ import annotations

import hashlib
import os
import urllib.request
from pathlib import Path
from typing import Callable, Mapping, Optional

from lego_image_processor.kit.source import PINNED_SHA256, PINNED_URL

DEFAULT_URL = PINNED_URL
DEFAULT_SHA256 = PINNED_SHA256
PDF_CACHE_NAME = "31203-instructions-6372756.pdf"
_CHUNK = 1 << 20


class SourceError(Exception):
    """Base error; ``exit_code`` follows contracts/maintainer-tool.md."""

    exit_code = 1


class DownloadError(SourceError):
    exit_code = 3


class ChecksumError(SourceError):
    exit_code = 4

    def __init__(self, path, expected: str, actual: str):
        self.path, self.expected, self.actual = path, expected, actual
        super().__init__(
            f"Checksum mismatch for {path}: expected {expected}, actual {actual}. "
            "The file is not the pinned 31203 instructions PDF."
        )


def cache_root(env: Optional[Mapping[str, str]] = None) -> Path:
    """``$LEGO_IMAGE_PROCESSOR_CACHE``, else ``$XDG_CACHE_HOME/lego-image-processor``,
    else ``~/.cache/lego-image-processor``."""
    env = os.environ if env is None else env
    if env.get("LEGO_IMAGE_PROCESSOR_CACHE"):
        return Path(env["LEGO_IMAGE_PROCESSOR_CACHE"])
    if env.get("XDG_CACHE_HOME"):
        return Path(env["XDG_CACHE_HOME"]) / "lego-image-processor"
    return Path.home() / ".cache" / "lego-image-processor"


def cached_pdf_path(root: Path) -> Path:
    return Path(root) / "sources" / PDF_CACHE_NAME


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(path: Path, expected: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise ChecksumError(path, expected, actual)


def download(url: str, dest: Path, expected_sha256: str,
             opener: Optional[Callable] = None, timeout: float = 60.0) -> Path:
    """Stream ``url`` to ``dest.part``, verify, then rename to ``dest``.

    A failed or interrupted download, or a checksum mismatch, removes the ``.part`` file so
    nothing is ever left looking complete.
    """
    opener = opener or urllib.request.urlopen
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    h = hashlib.sha256()
    try:
        with opener(url, timeout=timeout) as resp, open(part, "wb") as out:
            while True:
                chunk = resp.read(_CHUNK)
                if not chunk:
                    break
                h.update(chunk)
                out.write(chunk)
    except BaseException as exc:
        part.unlink(missing_ok=True)
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        raise DownloadError(f"Download of {url} failed: {exc}") from exc
    actual = h.hexdigest()
    if actual != expected_sha256:
        part.unlink(missing_ok=True)
        raise ChecksumError(url, expected_sha256, actual)
    os.replace(part, dest)
    return dest


def resolve_pdf(pdf: Optional[Path] = None, cache_dir: Optional[Path] = None,
                url: str = DEFAULT_URL, sha256: str = DEFAULT_SHA256,
                opener: Optional[Callable] = None) -> Path:
    """Return a checksum-verified PDF path: ``pdf`` if given, else the cache, else download."""
    if pdf is not None:
        pdf = Path(pdf)
        if not pdf.is_file():
            raise DownloadError(f"PDF not found: {pdf}")
        verify(pdf, sha256)
        return pdf
    cached = cached_pdf_path(Path(cache_dir) if cache_dir else cache_root())
    if cached.is_file():
        verify(cached, sha256)  # re-hashed on every use
        return cached
    return download(url, cached, sha256, opener=opener)

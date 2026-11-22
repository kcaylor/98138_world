"""Per-user cache for pinned datasets: paths, verification and the one function that downloads.

Layout: ``<root>/datasets/<id>/<version>/<filename>`` (research R12). ``fetch`` is the only
function in the package that opens the network; everything else reads verified local files.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import hashlib
import os
import time
import urllib.request
from pathlib import Path
from typing import Callable, Mapping, Optional, Tuple, Union

from .registry import DatasetEntry

_CHUNK = 1 << 20
PathLike = Union[str, Path]
USER_AGENT = "lego-image-processor (dataset fetch)"


class DatasetError(Exception):
    """Base error for dataset access; ``exit_code`` follows contracts/cli.md."""

    exit_code = 1


class DatasetNotCachedError(DatasetError):
    exit_code = 3

    def __init__(self, entry_id: str, path: Optional[Path] = None):
        self.entry_id, self.path = entry_id, path
        super().__init__(
            f"Dataset {entry_id} is not cached. Fetch it with: "
            f"lego-image-processor dataset fetch {entry_id} (or rerun map build with --fetch)"
        )


class ChecksumMismatchError(DatasetError):
    exit_code = 4

    def __init__(self, path: Path, expected: str, actual: str, what: str = "SHA-256",
                 entry_id: Optional[str] = None, hint: bool = True):
        self.path, self.expected, self.actual, self.what = path, expected, actual, what
        self.entry_id = entry_id
        msg = f"{what} mismatch for {path}: expected {expected}, actual {actual}."
        if hint and entry_id:
            msg += f" Fetch it again with: lego-image-processor dataset fetch {entry_id}"
        super().__init__(msg)


class FetchError(DatasetError):
    exit_code = 5


def cache_root(env: Optional[Mapping[str, str]] = None, override: Optional[PathLike] = None) -> Path:
    """``override``, else ``$LEGO_IMAGE_PROCESSOR_CACHE``, else
    ``$XDG_CACHE_HOME/lego-image-processor``, else ``~/.cache/lego-image-processor``."""
    if override:
        return Path(override)
    env = os.environ if env is None else env
    if env.get("LEGO_IMAGE_PROCESSOR_CACHE"):
        return Path(env["LEGO_IMAGE_PROCESSOR_CACHE"])
    if env.get("XDG_CACHE_HOME"):
        return Path(env["XDG_CACHE_HOME"]) / "lego-image-processor"
    return Path.home() / ".cache" / "lego-image-processor"


def sha256_file(path: PathLike) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def cached_path(entry: DatasetEntry, cache_dir: Optional[PathLike] = None) -> Path:
    """Where a downloaded entry lives in the cache (local entries: their declared path)."""
    if entry.kind == "local":
        return Path(entry.path)
    return cache_root(override=cache_dir) / "datasets" / entry.id / entry.version / entry.filename


def is_cached(entry: DatasetEntry, cache_dir: Optional[PathLike] = None) -> bool:
    """True when the file exists with the pinned size (full SHA-256 check happens on use)."""
    if entry.kind == "packaged":
        return True
    p = cached_path(entry, cache_dir)
    if not p.is_file():
        return False
    return entry.size is None or p.stat().st_size == entry.size


def verify(entry: DatasetEntry, path: PathLike, hint: bool = True) -> None:
    """Check size (when pinned) and SHA-256; raise ``ChecksumMismatchError`` otherwise."""
    path = Path(path)
    if entry.size is not None:
        actual_size = path.stat().st_size
        if actual_size != entry.size:
            raise ChecksumMismatchError(path, f"{entry.size} bytes", f"{actual_size} bytes",
                                        what="size", entry_id=entry.id, hint=hint and entry.kind != "local")
    actual = sha256_file(path)
    if actual != entry.sha256:
        raise ChecksumMismatchError(path, entry.sha256, actual, entry_id=entry.id,
                                    hint=hint and entry.kind != "local")


def resolve(entry: DatasetEntry, cache_dir: Optional[PathLike] = None) -> Path:
    """The verified local file for an entry. Never downloads."""
    if entry.kind == "packaged":
        raise ValueError(f"dataset {entry.id} is packaged; it has no cache file")
    p = cached_path(entry, cache_dir)
    if not p.is_file():
        if entry.kind == "local":
            raise DatasetError(f"Local data file not found: {p}")
        raise DatasetNotCachedError(entry.id, p)
    verify(entry, p)
    return p


resolve_entry = resolve


Opener = Callable[..., object]


# Server-side subsets (e.g. NOAA THREDDS/OPeNDAP) can take minutes before the first byte arrives.
FETCH_TIMEOUT_S = 300.0
FETCH_ATTEMPTS = 3


def _default_opener(url: str, timeout: float = FETCH_TIMEOUT_S):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(req, timeout=timeout)  # noqa: S310 (pinned https URL)


def fetch(entry: DatasetEntry, *, cache_dir: Optional[PathLike] = None,
          opener: Optional[Opener] = None, force: bool = False,
          attempts: Optional[int] = None, sleep: Optional[Callable[[float], None]] = None
          ) -> Tuple[Path, bool]:
    """Download ``entry`` into the cache, verified. Returns ``(path, downloaded)``.

    Network failures (``FetchError``) are retried up to ``attempts`` times with a growing pause;
    checksum or size mismatches are not retried.
    """
    attempts = FETCH_ATTEMPTS if attempts is None else max(1, attempts)
    sleep = sleep or time.sleep
    for attempt in range(1, attempts + 1):
        try:
            return _fetch_once(entry, cache_dir=cache_dir, opener=opener, force=force)
        except FetchError:
            if attempt >= attempts:
                raise
            sleep(10.0 * attempt)
    raise AssertionError("unreachable")


def _fetch_once(entry: DatasetEntry, *, cache_dir: Optional[PathLike] = None,
                opener: Optional[Opener] = None, force: bool = False) -> Tuple[Path, bool]:
    """One download attempt; see :func:`fetch`.

    Streams to ``<filename>.part``, checks size and SHA-256, then renames atomically. A mismatch
    or an interrupted download removes the part file. A valid cached file is not downloaded again.
    """
    if entry.kind != "download":
        raise DatasetError(f"dataset {entry.id} is {entry.kind}; nothing to fetch")
    final = cached_path(entry, cache_dir)
    if final.is_file() and not force:
        try:
            verify(entry, final)
            return final, False
        except ChecksumMismatchError:
            pass  # replaced below
    part = final.with_name(final.name + ".part")
    opener = opener or _default_opener
    try:
        final.parent.mkdir(parents=True, exist_ok=True)
        h = hashlib.sha256()
        size = 0
        with open(part, "wb") as out:
            try:
                response = opener(entry.url)
            except Exception as exc:  # urllib.error.URLError, socket errors, timeouts
                raise FetchError(f"Could not download {entry.id} from {entry.url}: {exc}") from exc
            try:
                while True:
                    try:
                        chunk = response.read(_CHUNK)
                    except Exception as exc:
                        raise FetchError(f"Download of {entry.id} was interrupted: {exc}") from exc
                    if not chunk:
                        break
                    size += len(chunk)
                    if entry.size is not None and size > entry.size:
                        raise ChecksumMismatchError(final, f"{entry.size} bytes",
                                                    f"more than {entry.size} bytes", what="size",
                                                    entry_id=entry.id, hint=False)
                    h.update(chunk)
                    out.write(chunk)
            finally:
                close = getattr(response, "close", None)
                if close:
                    close()
        if entry.size is not None and size != entry.size:
            raise ChecksumMismatchError(final, f"{entry.size} bytes", f"{size} bytes", what="size",
                                        entry_id=entry.id, hint=False)
        actual = h.hexdigest()
        if actual != entry.sha256:
            raise ChecksumMismatchError(final, entry.sha256, actual, entry_id=entry.id, hint=False)
        os.replace(part, final)
    except OSError as exc:
        _remove(part)
        raise FetchError(f"Could not write {final}: {exc}") from exc
    except BaseException:
        _remove(part)
        raise
    return final, True


def _remove(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass

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
    base = cache_root(override=cache_dir) / "datasets" / entry.id / entry.version
    if entry.files:  # feature 013: a multi-file entry lives in its version directory
        return base
    return base / entry.filename


def file_paths(entry: DatasetEntry, cache_dir: Optional[PathLike] = None):
    """``[(DatasetFile, path), ...]`` of a multi-file entry (feature 013)."""
    base = cached_path(entry, cache_dir)
    return [(f, base / f.name) for f in entry.files]


def is_cached(entry: DatasetEntry, cache_dir: Optional[PathLike] = None) -> bool:
    """True when the file exists with the pinned size (full SHA-256 check happens on use)."""
    if entry.kind == "packaged":
        return True
    if entry.files:
        return all(p.is_file() and p.stat().st_size == f.size for f, p in file_paths(entry, cache_dir))
    p = cached_path(entry, cache_dir)
    if not p.is_file():
        return False
    return entry.size is None or p.stat().st_size == entry.size


def verify(entry: DatasetEntry, path: PathLike, hint: bool = True) -> None:
    """Check size (when pinned) and SHA-256; raise ``ChecksumMismatchError`` otherwise."""
    path = Path(path)
    if entry.files:
        for f in entry.files:
            _verify_file(path / f.name, f.size, f.sha256, entry_id=entry.id, hint=hint)
        return
    if entry.size is not None:
        actual_size = path.stat().st_size
        if actual_size != entry.size:
            raise ChecksumMismatchError(path, f"{entry.size} bytes", f"{actual_size} bytes",
                                        what="size", entry_id=entry.id, hint=hint and entry.kind != "local")
    if entry.content_sha256 and not entry.sha256:
        _verify_content(entry, path, hint=hint)
        return
    actual = sha256_file(path)
    if actual != entry.sha256:
        raise ChecksumMismatchError(path, entry.sha256, actual, entry_id=entry.id,
                                    hint=hint and entry.kind != "local")


def _verify_file(path: Path, size: int, sha256: str, entry_id: str, hint: bool = True) -> None:
    """Size and SHA-256 of one file of a multi-file entry (feature 013)."""
    if not path.is_file():
        raise DatasetNotCachedError(entry_id, path)
    actual_size = path.stat().st_size
    if actual_size != size:
        raise ChecksumMismatchError(path, f"{size} bytes", f"{actual_size} bytes", what="size",
                                    entry_id=entry_id, hint=hint)
    actual = sha256_file(path)
    if actual != sha256:
        raise ChecksumMismatchError(path, sha256, actual, entry_id=entry_id, hint=hint)


def content_sha256(entry: DatasetEntry, path: PathLike) -> str:
    """The content checksum of ``path`` for ``entry`` (feature 012): SHA-256 over the decoded data
    of the entry's variable(s) and coordinates; see ``readers.netcdf3_content_sha256``."""
    from .readers import netcdf3_content_sha256

    h = hashlib.sha256()
    names = sorted(entry.variables) or []
    if len(names) == 1:
        return netcdf3_content_sha256(path, names[0])
    for name in names:
        h.update(netcdf3_content_sha256(path, name).encode())
    return h.hexdigest()


def _verify_content(entry: DatasetEntry, path: Path, hint: bool = True) -> None:
    try:
        actual = content_sha256(entry, path)
    except ValueError as exc:
        actual = f"unreadable ({exc})"
    if actual != entry.content_sha256:
        err = ChecksumMismatchError(path, entry.content_sha256, actual, what="content SHA-256",
                                    entry_id=entry.id, hint=hint and entry.kind != "local")
        err.args = (str(err) + " The server builds this file on request: if its data changed, "
                    "check it and pin a new version (content_sha256) in datasets.json.",)
        raise err


def resolve(entry: DatasetEntry, cache_dir: Optional[PathLike] = None) -> Path:
    """The verified local file for an entry. Never downloads."""
    if entry.kind == "packaged":
        raise ValueError(f"dataset {entry.id} is packaged; it has no cache file")
    p = cached_path(entry, cache_dir)
    if entry.files:
        for _, fp in file_paths(entry, cache_dir):
            if not fp.is_file():
                raise DatasetNotCachedError(entry.id, fp)
        verify(entry, p)
        return p
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
    # Pinned URL: https, or http for an entry that states http_only and pins its SHA-256 (012).
    return urllib.request.urlopen(req, timeout=timeout)  # noqa: S310


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
    if entry.files:  # feature 013: each missing or invalid file, verified one by one
        downloaded = False
        for f, fp in file_paths(entry, cache_dir):
            if fp.is_file() and not force:
                try:
                    _verify_file(fp, f.size, f.sha256, entry.id)
                    continue
                except ChecksumMismatchError:
                    pass  # replaced below
            _download(entry, f.url, f.size, f.sha256, fp, opener)
            downloaded = True
        return cached_path(entry, cache_dir), downloaded
    final = cached_path(entry, cache_dir)
    if final.is_file() and not force:
        try:
            verify(entry, final)
            return final, False
        except ChecksumMismatchError:
            pass  # replaced below
    _download(entry, entry.url, entry.size, entry.sha256, final, opener)
    return final, True


def _download(entry: DatasetEntry, url: str, expected_size: Optional[int], expected_sha: str,
              final: Path, opener: Optional[Opener]) -> None:
    """Stream ``url`` to ``final``.part, check size and SHA-256 (or the entry's content checksum
    when ``expected_sha`` is empty), then rename atomically."""
    part = final.with_name(final.name + ".part")
    opener = opener or _default_opener
    try:
        final.parent.mkdir(parents=True, exist_ok=True)
        h = hashlib.sha256()
        size = 0
        with open(part, "wb") as out:
            try:
                response = opener(url)
            except Exception as exc:  # urllib.error.URLError, socket errors, timeouts
                raise FetchError(f"Could not download {entry.id} from {url}: {exc}") from exc
            try:
                while True:
                    try:
                        chunk = response.read(_CHUNK)
                    except Exception as exc:
                        raise FetchError(f"Download of {entry.id} was interrupted: {exc}") from exc
                    if not chunk:
                        break
                    size += len(chunk)
                    if expected_size is not None and size > expected_size:
                        raise ChecksumMismatchError(final, f"{expected_size} bytes",
                                                    f"more than {expected_size} bytes", what="size",
                                                    entry_id=entry.id, hint=False)
                    h.update(chunk)
                    out.write(chunk)
            finally:
                close = getattr(response, "close", None)
                if close:
                    close()
        if expected_size is not None and size != expected_size:
            raise ChecksumMismatchError(final, f"{expected_size} bytes", f"{size} bytes", what="size",
                                        entry_id=entry.id, hint=False)
        if expected_sha:
            actual = h.hexdigest()
            if actual != expected_sha:
                raise ChecksumMismatchError(final, expected_sha, actual, entry_id=entry.id, hint=False)
        else:
            _verify_content(entry, part, hint=False)
        os.replace(part, final)
    except OSError as exc:
        _remove(part)
        raise FetchError(f"Could not write {final}: {exc}") from exc
    except BaseException:
        _remove(part)
        raise


def _remove(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass

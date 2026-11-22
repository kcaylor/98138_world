"""``fetch`` with an injected opener (FR-008; data-model.md CachedDataset state transitions)."""

import hashlib
import os
import stat

import pytest

from tests.conftest import FakeResponse
from lego_image_processor.datasets.cache import (ChecksumMismatchError, FetchError, cached_path, fetch,
                                                 is_cached)
from lego_image_processor.datasets.registry import DatasetEntry

DATA = b"0123456789" * 1000


def _entry(data=DATA, **kw):
    base = dict(id="demo", version="v1", kind="download", title="Demo", publisher="T",
                url="https://example.invalid/demo.nc", size=len(data),
                sha256=hashlib.sha256(data).hexdigest(), format="netcdf3", filename="demo.nc",
                license="Public domain", citation="C.")
    base.update(kw)
    return DatasetEntry(**base)


class Opener:
    def __init__(self, data=DATA, fail_after=None, error=None):
        self.calls, self.data, self.fail_after, self.error = [], data, fail_after, error

    def __call__(self, url, *a, **k):
        self.calls.append(url)
        if self.error:
            raise self.error
        return FakeResponse(self.data, self.fail_after)


def test_downloads_verifies_and_renames(tmp_path):
    e = _entry()
    op = Opener()
    path, downloaded = fetch(e, cache_dir=tmp_path, opener=op)
    assert downloaded and path == cached_path(e, tmp_path) and path.read_bytes() == DATA
    assert op.calls == [e.url]
    assert not path.with_name(path.name + ".part").exists()


def test_mismatch_deletes_part_and_reports(tmp_path):
    e = _entry()
    bad = DATA[:-1] + b"X"
    with pytest.raises(ChecksumMismatchError) as err:
        fetch(e, cache_dir=tmp_path, opener=Opener(bad))
    assert err.value.expected == e.sha256 and err.value.actual == hashlib.sha256(bad).hexdigest()
    folder = cached_path(e, tmp_path).parent
    assert list(folder.iterdir()) == []


def test_wrong_size(tmp_path):
    e = _entry()
    with pytest.raises(ChecksumMismatchError, match="size"):
        fetch(e, cache_dir=tmp_path, opener=Opener(DATA + b"extra"))
    assert not is_cached(e, tmp_path)


def test_interrupted_stream_leaves_nothing(tmp_path):
    e = _entry()
    with pytest.raises(FetchError, match="interrupted"):
        fetch(e, cache_dir=tmp_path, opener=Opener(fail_after=4000))
    assert list(cached_path(e, tmp_path).parent.iterdir()) == []


def test_network_error(tmp_path):
    with pytest.raises(FetchError, match="Could not download"):
        fetch(_entry(), cache_dir=tmp_path, opener=Opener(error=OSError("no route to host")))


def test_valid_cached_file_not_downloaded_again(tmp_path):
    e = _entry()
    fetch(e, cache_dir=tmp_path, opener=Opener())
    op = Opener()
    path, downloaded = fetch(e, cache_dir=tmp_path, opener=op)
    assert not downloaded and op.calls == []


def test_corrupt_cached_file_is_replaced(tmp_path):
    e = _entry()
    p = cached_path(e, tmp_path)
    p.parent.mkdir(parents=True)
    p.write_bytes(b"x" * len(DATA))
    path, downloaded = fetch(e, cache_dir=tmp_path, opener=Opener())
    assert downloaded and path.read_bytes() == DATA


@pytest.mark.skipif(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                    reason="needs POSIX permissions as a normal user")
def test_read_only_cache_fails_cleanly(tmp_path):
    ro = tmp_path / "ro"
    ro.mkdir()
    ro.chmod(stat.S_IRUSR | stat.S_IXUSR)
    try:
        with pytest.raises(FetchError, match="Could not write"):
            fetch(_entry(), cache_dir=ro, opener=Opener())
    finally:
        ro.chmod(stat.S_IRWXU)
    assert list(ro.rglob("*.part")) == []


def test_default_opener_is_blocked_in_tests(tmp_path):
    # the session offline guard turns any real download attempt into a FetchError
    with pytest.raises(FetchError):
        fetch(_entry(url="https://127.0.0.1:9/x"), cache_dir=tmp_path)

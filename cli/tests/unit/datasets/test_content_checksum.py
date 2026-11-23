"""Content checksums for files built on request, and HTTP-only pinned files (feature 012, FR-005,
research R2, R3)."""

import hashlib

import numpy as np
import pytest

from tests.conftest import FakeResponse
from tests.unit.datasets.test_readers import _write_erddap
from lego_image_processor.datasets.cache import (ChecksumMismatchError, cached_path, content_sha256,
                                                 fetch, resolve, verify)
from lego_image_processor.datasets.readers import netcdf3_content_sha256
from lego_image_processor.datasets.registry import DatasetEntry


def _data():
    d = np.full((3, 2, 2), 0.5)
    d[0, 0, 0] = np.nan
    return d


def _entry(path, **kw):
    base = dict(id="chl", version="v1", kind="download", title="Chl", publisher="T",
                url="https://example.invalid/chl.nc", size=path.stat().st_size, sha256="",
                content_sha256=netcdf3_content_sha256(path, "chlor_a"), format="netcdf3",
                filename="chl.nc", license="L", citation="C.",
                variables={"chlor_a": {"reduce": "climatology-mean"}})
    base.update(kw)
    return DatasetEntry(**base)


def test_verify_accepts_a_new_request_of_the_same_data(tmp_path):
    a = _write_erddap(tmp_path / "a.nc", _data(), history="2026-11-22T10:00:00Z")
    b = _write_erddap(tmp_path / "b.nc", _data(), history="2026-11-22T10:05:00Z")
    e = _entry(a)
    assert hashlib.sha256(a.read_bytes()).hexdigest() != hashlib.sha256(b.read_bytes()).hexdigest()
    verify(e, a)
    verify(e, b)
    assert content_sha256(e, b) == e.content_sha256


def test_verify_rejects_changed_data(tmp_path):
    a = _write_erddap(tmp_path / "a.nc", _data())
    d = _data()
    d[1, 1, 1] = 0.75
    b = _write_erddap(tmp_path / "b.nc", d)
    with pytest.raises(ChecksumMismatchError, match="content SHA-256 mismatch.*pin a new version"):
        verify(_entry(a), b)


def test_verify_rejects_unreadable_file(tmp_path):
    a = _write_erddap(tmp_path / "a.nc", _data())
    junk = tmp_path / "junk.nc"
    junk.write_bytes(b"x" * a.stat().st_size)
    with pytest.raises(ChecksumMismatchError, match="unreadable"):
        verify(_entry(a), junk)


def test_fetch_checks_content_then_caches(tmp_path):
    src = _write_erddap(tmp_path / "src.nc", _data(), history="first request")
    again = _write_erddap(tmp_path / "again.nc", _data(), history="later request")
    e = _entry(src)
    cache = tmp_path / "cache"
    path, downloaded = fetch(e, cache_dir=cache, opener=lambda url, *a, **k: FakeResponse(again.read_bytes()))
    assert downloaded and path == cached_path(e, cache)
    assert resolve(e, cache) == path


def test_fetch_removes_part_file_on_content_mismatch(tmp_path):
    src = _write_erddap(tmp_path / "src.nc", _data())
    d = _data()
    d[2, 0, 1] = 9.0
    other = _write_erddap(tmp_path / "other.nc", d)
    e = _entry(src)
    cache = tmp_path / "cache"
    with pytest.raises(ChecksumMismatchError, match="content SHA-256"):
        fetch(e, cache_dir=cache, opener=lambda url, *a, **k: FakeResponse(other.read_bytes()))
    final = cached_path(e, cache)
    assert not final.exists() and not final.with_name(final.name + ".part").exists()


def test_http_only_entry_fetches_with_sha256(tmp_path):
    data = b"geotiff bytes" * 10
    e = DatasetEntry(id="npp", version="v1", kind="download", title="NPP", publisher="T",
                     url="http://example.invalid/npp.tif", http_only="host serves HTTP only",
                     size=len(data), sha256=hashlib.sha256(data).hexdigest(), format="geotiff",
                     filename="npp.tif", license="L", citation="C.")
    seen = []

    def opener(url, *a, **k):
        seen.append(url)
        return FakeResponse(data)
    path, downloaded = fetch(e, cache_dir=tmp_path, opener=opener)
    assert downloaded and path.read_bytes() == data and seen == ["http://example.invalid/npp.tif"]
    bad = DatasetEntry(**{**e.__dict__, "sha256": "0" * 64})
    with pytest.raises(ChecksumMismatchError):
        fetch(bad, cache_dir=tmp_path / "b", opener=opener)

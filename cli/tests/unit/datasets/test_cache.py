"""Cache helper (research R12; data-model.md CachedDataset, DatasetEntry.sha256/size)."""

import hashlib
from pathlib import Path

import pytest

from lego_image_processor.datasets.cache import (
    ChecksumMismatchError, DatasetNotCachedError, cache_root, cached_path, is_cached, resolve,
    sha256_file, verify,
)
from lego_image_processor.datasets.registry import DatasetEntry


def _entry(data: bytes, **kw) -> DatasetEntry:
    base = dict(id="demo", version="v1", kind="download", title="Demo", publisher="Test",
                url="https://example.invalid/demo.bin", size=len(data),
                sha256=hashlib.sha256(data).hexdigest(), format="npy", filename="demo.npy",
                variables={"v": {"units": "m"}}, class_rule={}, license="Public domain",
                citation="Test data.")
    base.update(kw)
    return DatasetEntry(**base)


class TestCacheRoot:
    def test_env_override_first(self, tmp_path):
        env = {"LEGO_IMAGE_PROCESSOR_CACHE": str(tmp_path / "a"), "XDG_CACHE_HOME": str(tmp_path / "b")}
        assert cache_root(env) == tmp_path / "a"

    def test_xdg_second(self, tmp_path):
        assert cache_root({"XDG_CACHE_HOME": str(tmp_path)}) == tmp_path / "lego-image-processor"

    def test_home_default(self):
        assert cache_root({}) == Path.home() / ".cache" / "lego-image-processor"

    def test_explicit_override_wins(self, tmp_path):
        env = {"LEGO_IMAGE_PROCESSOR_CACHE": str(tmp_path / "a")}
        assert cache_root(env, override=tmp_path / "c") == tmp_path / "c"

    def test_tool_uses_the_same_definition(self):
        from kit31203 import source
        from lego_image_processor.datasets import cache
        assert source.cache_root is cache.cache_root


class TestPaths:
    def test_layout(self, tmp_path):
        e = _entry(b"x")
        assert cached_path(e, tmp_path) == tmp_path / "datasets" / "demo" / "v1" / "demo.npy"

    def test_not_cached(self, tmp_path):
        e = _entry(b"x")
        assert not is_cached(e, tmp_path)
        with pytest.raises(DatasetNotCachedError) as err:
            resolve(e, tmp_path)
        assert err.value.entry_id == "demo"
        assert "dataset fetch demo" in str(err.value)


class TestVerify:
    def test_good_file(self, tmp_path):
        data = b"hello world"
        e = _entry(data)
        p = cached_path(e, tmp_path)
        p.parent.mkdir(parents=True)
        p.write_bytes(data)
        assert is_cached(e, tmp_path)
        verify(e, p)
        assert resolve(e, tmp_path) == p
        assert sha256_file(p) == e.sha256

    def test_altered_file(self, tmp_path):
        data = b"hello world"
        e = _entry(data)
        p = cached_path(e, tmp_path)
        p.parent.mkdir(parents=True)
        p.write_bytes(b"hello World")
        with pytest.raises(ChecksumMismatchError) as err:
            resolve(e, tmp_path)
        assert err.value.expected == e.sha256
        assert err.value.actual == hashlib.sha256(b"hello World").hexdigest()
        assert e.sha256 in str(err.value) and err.value.actual in str(err.value)
        assert "dataset fetch demo" in str(err.value)

    def test_size_mismatch(self, tmp_path):
        e = _entry(b"abc")
        p = tmp_path / "f"
        p.write_bytes(b"abcd")
        with pytest.raises(ChecksumMismatchError) as err:
            verify(e, p)
        assert "size" in str(err.value)

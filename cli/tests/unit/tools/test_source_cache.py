"""Download, cache and checksum tests for the maintainer tool (no network)."""

import hashlib
import io
from pathlib import Path

import pytest

from kit31203 import source as src

PAYLOAD = b"%PDF-1.4 synthetic test payload\n" * 100
PAYLOAD_SHA = hashlib.sha256(PAYLOAD).hexdigest()


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


class InterruptedResponse(FakeResponse):
    """Returns some bytes, then fails like a dropped connection."""

    def read(self, n=-1):
        if self.tell() > 100:
            raise ConnectionResetError("connection reset by peer")
        return super().read(min(n, 64) if n and n > 0 else 64)


def opener_for(payload, cls=FakeResponse, calls=None):
    def opener(url, timeout=None):
        if calls is not None:
            calls.append(url)
        return cls(payload)
    return opener


class TestCacheRoot:
    def test_env_override_first(self, tmp_path):
        env = {"LEGO_IMAGE_PROCESSOR_CACHE": str(tmp_path / "a"), "XDG_CACHE_HOME": str(tmp_path / "b")}
        assert src.cache_root(env) == tmp_path / "a"

    def test_xdg_second(self, tmp_path):
        env = {"XDG_CACHE_HOME": str(tmp_path / "b")}
        assert src.cache_root(env) == tmp_path / "b" / "lego-image-processor"

    def test_home_default(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        assert src.cache_root({}) == tmp_path / ".cache" / "lego-image-processor"

    def test_cached_pdf_path(self, tmp_path):
        assert src.cached_pdf_path(tmp_path) == tmp_path / "sources" / "31203-instructions-6372756.pdf"


class TestDownload:
    def test_download_verifies_and_renames(self, tmp_path):
        dest = tmp_path / "sources" / "x.pdf"
        src.download("https://example.invalid/x.pdf", dest, PAYLOAD_SHA, opener=opener_for(PAYLOAD))
        assert dest.read_bytes() == PAYLOAD
        assert not dest.with_name(dest.name + ".part").exists()

    def test_interrupted_download_leaves_nothing_complete(self, tmp_path):
        dest = tmp_path / "x.pdf"
        with pytest.raises(src.DownloadError) as info:
            src.download("https://example.invalid/x.pdf", dest, PAYLOAD_SHA,
                         opener=opener_for(PAYLOAD, InterruptedResponse))
        assert info.value.exit_code == 3
        assert "https://example.invalid/x.pdf" in str(info.value)
        assert not dest.exists()
        assert not dest.with_name(dest.name + ".part").exists()

    def test_unreachable_url(self, tmp_path):
        def opener(url, timeout=None):
            raise OSError("name or service not known")
        with pytest.raises(src.DownloadError, match="name or service not known"):
            src.download("https://example.invalid/x.pdf", tmp_path / "x.pdf", PAYLOAD_SHA, opener=opener)

    def test_checksum_mismatch_deletes_part(self, tmp_path):
        dest = tmp_path / "x.pdf"
        with pytest.raises(src.ChecksumError) as info:
            src.download("https://example.invalid/x.pdf", dest, "0" * 64, opener=opener_for(PAYLOAD))
        err = info.value
        assert err.exit_code == 4
        assert "expected " + "0" * 64 in str(err)
        assert "actual " + PAYLOAD_SHA in str(err)
        assert not dest.exists()
        assert not dest.with_name(dest.name + ".part").exists()


class TestResolvePdf:
    def test_downloads_when_not_cached(self, tmp_path):
        calls = []
        path = src.resolve_pdf(cache_dir=tmp_path, sha256=PAYLOAD_SHA,
                               opener=opener_for(PAYLOAD, calls=calls))
        assert path == src.cached_pdf_path(tmp_path)
        assert path.read_bytes() == PAYLOAD
        assert len(calls) == 1

    def test_cached_file_rehashed_on_every_use(self, tmp_path, monkeypatch):
        cached = src.cached_pdf_path(tmp_path)
        cached.parent.mkdir(parents=True)
        cached.write_bytes(PAYLOAD)
        hashed = []
        real = src.sha256_file
        monkeypatch.setattr(src, "sha256_file", lambda p: hashed.append(p) or real(p))

        def no_network(url, timeout=None):
            raise AssertionError("must not download when cached")

        src.resolve_pdf(cache_dir=tmp_path, sha256=PAYLOAD_SHA, opener=no_network)
        src.resolve_pdf(cache_dir=tmp_path, sha256=PAYLOAD_SHA, opener=no_network)
        assert hashed == [cached, cached]

    def test_corrupted_cache_caught(self, tmp_path):
        cached = src.cached_pdf_path(tmp_path)
        cached.parent.mkdir(parents=True)
        cached.write_bytes(PAYLOAD + b"tampered")
        with pytest.raises(src.ChecksumError, match="expected " + PAYLOAD_SHA):
            src.resolve_pdf(cache_dir=tmp_path, sha256=PAYLOAD_SHA,
                            opener=opener_for(PAYLOAD))

    def test_local_pdf_is_verified(self, tmp_path):
        local = tmp_path / "mine.pdf"
        local.write_bytes(PAYLOAD)
        assert src.resolve_pdf(pdf=local, cache_dir=tmp_path, sha256=PAYLOAD_SHA) == local
        with pytest.raises(src.ChecksumError) as info:
            src.resolve_pdf(pdf=local, cache_dir=tmp_path, sha256="1" * 64)
        assert "actual " + PAYLOAD_SHA in str(info.value)

    def test_missing_local_pdf(self, tmp_path):
        with pytest.raises(src.DownloadError, match="not found"):
            src.resolve_pdf(pdf=tmp_path / "nope.pdf", cache_dir=tmp_path, sha256=PAYLOAD_SHA)

    def test_default_pins(self):
        from lego_image_processor.kit.source import PINNED_SHA256, PINNED_URL
        assert src.DEFAULT_URL == PINNED_URL
        assert src.DEFAULT_SHA256 == PINNED_SHA256

"""Suite-wide offline guard (SC-007, FR-022): no test may open a network connection.

Network sockets (IPv4/IPv6) raise on ``connect``/``connect_ex`` for the whole session. Local
AF_UNIX sockets are left alone.
"""

import socket

import pytest


class NetworkBlockedError(RuntimeError):
    """A test tried to open a network connection."""


_original_connect = socket.socket.connect
_original_connect_ex = socket.socket.connect_ex
_NETWORK_FAMILIES = {socket.AF_INET, socket.AF_INET6}


def _guard(original):
    def guarded(self, address, *args, **kwargs):
        if self.family in _NETWORK_FAMILIES:
            raise NetworkBlockedError(f"network access is blocked in tests (tried {address!r})")
        return original(self, address, *args, **kwargs)
    return guarded


@pytest.fixture(autouse=True, scope="session")
def _block_network():
    socket.socket.connect = _guard(_original_connect)
    socket.socket.connect_ex = _guard(_original_connect_ex)
    try:
        yield
    finally:
        socket.socket.connect = _original_connect
        socket.socket.connect_ex = _original_connect_ex


# --- Feature 004: registry pointed at the small derived dataset fixtures (FR-025) -------------

import hashlib  # noqa: E402
import json  # noqa: E402
import shutil  # noqa: E402
from pathlib import Path  # noqa: E402

FIXTURE_DATASETS = Path(__file__).resolve().parent / "fixtures" / "datasets"


class FixtureRegistry:
    """A registry whose download entries are the committed fixtures (same ids and versions)."""

    def __init__(self, root: Path):
        self.root = root
        self.cache_dir = root / "cache"
        self.registry_path = root / "datasets.json"
        self.files = {}

    def place(self, dataset_id: str) -> Path:
        """Copy the fixture into the cache as if it had been fetched."""
        from lego_image_processor.datasets import cached_path, get_entry

        e = get_entry(dataset_id)
        dest = cached_path(e, self.cache_dir)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.files[dataset_id], dest)
        return dest

    def place_all(self):
        for i in self.files:
            self.place(i)
        return self


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture
def fixture_registry(tmp_path, monkeypatch):
    from lego_image_processor.datasets import registry as reg

    data = json.loads(reg.REGISTRY_PATH.read_text(encoding="utf-8"))
    fr = FixtureRegistry(tmp_path)
    etopo = FIXTURE_DATASETS / "etopo2022_1deg.npy"
    ersst = FIXTURE_DATASETS / "ersst_v5_annual_2deg.nc"
    months = {"ersst-v5-1997-12": FIXTURE_DATASETS / "ersst_v5_199712_ssta.nc",  # feature 009
              "ersst-v5-1988-12": FIXTURE_DATASETS / "ersst_v5_198812_ssta.nc"}
    npp = FIXTURE_DATASETS / "mod17a3_npp_1deg.tif"       # feature 012
    chla = FIXTURE_DATASETS / "modis_chla_4deg_6mo.nc"    # feature 012
    for row in data["datasets"]:
        if row["id"] == "etopo2022-surface-10m":
            row.update(format="npy", filename=etopo.name, size=etopo.stat().st_size, sha256=_sha(etopo),
                       grid={"lat": [-90, 90], "lon": [-180, 180]})
            fr.files[row["id"]] = etopo
        elif row["id"] == "ersst-v5-ltm-1991-2020":
            row.update(filename=ersst.name, size=ersst.stat().st_size, sha256=_sha(ersst),
                       variables={"sst": {"units": "degC"}})
            fr.files[row["id"]] = ersst
        elif row["id"] in months:
            f = months[row["id"]]
            row.update(filename=f.name, size=f.stat().st_size, sha256=_sha(f))
            fr.files[row["id"]] = f
        elif row["id"] == "mod17a3-npp-mean-2000-2015":  # feature 012: 1 degree, read as 2x2 blocks
            row.update(filename=npp.name, size=npp.stat().st_size, sha256=_sha(npp),
                       grid={**row.get("grid", {}), "block": 2})
            fr.files[row["id"]] = npp
        elif row["id"] == "modis-aqua-chla-2013-2024":  # feature 012: content checksum of the fixture
            from lego_image_processor.datasets.readers import netcdf3_content_sha256
            row.update(filename=chla.name, size=chla.stat().st_size,
                       content_sha256=netcdf3_content_sha256(chla, "chlor_a"))
            fr.files[row["id"]] = chla
    fr.registry_path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(reg, "REGISTRY_PATH", fr.registry_path)
    monkeypatch.setenv("LEGO_IMAGE_PROCESSOR_CACHE", str(fr.cache_dir))
    return fr


class FakeResponse:
    """A file-like download response for the injected opener."""

    def __init__(self, data: bytes, fail_after=None):
        self._data, self._pos, self._fail_after = data, 0, fail_after

    def read(self, n=-1):
        if self._fail_after is not None and self._pos >= self._fail_after:
            raise ConnectionResetError("connection reset by peer")
        n = len(self._data) - self._pos if n < 0 else n
        if self._fail_after is not None:
            n = min(n, self._fail_after - self._pos) or n
        chunk = self._data[self._pos:self._pos + n]
        self._pos += len(chunk)
        return chunk

    def close(self):
        pass


@pytest.fixture(autouse=True)
def _no_fetch_retry_pause(monkeypatch):
    """Dataset downloads retry with a pause; tests never wait for it."""
    from lego_image_processor.datasets import cache
    monkeypatch.setattr(cache.time, "sleep", lambda s: None)

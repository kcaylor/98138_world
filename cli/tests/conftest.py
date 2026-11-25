"""Suite-wide offline guard (SC-007, FR-022): no test may open a network connection.

Network sockets (IPv4/IPv6) raise on ``connect``/``connect_ex`` for the whole session. Local
AF_UNIX sockets are left alone.
"""

import socket
from pathlib import Path

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
# The registry helper lives in tools/fixtures004/registry.py (feature 016, research R9) so the kit
# golden harness (`maptemplates kit-golden --fixtures`) places the same fixtures as the tests.

from fixtures004.registry import FIXTURE_DATASETS, FixtureRegistry, make_fixture_registry  # noqa: E402,F401


@pytest.fixture
def fixture_registry(tmp_path, monkeypatch):
    from lego_image_processor.datasets import registry as reg

    fr = make_fixture_registry(tmp_path)
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


# --- Feature 016: map templates (T030) --------------------------------------------------------
# Both fixtures use tools/maptemplates/testing.py (shared with the web tests, T084).

TEMPLATE_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "templates"
TEST_CONFIRMATION_DATE = "2026-11-23"  # test confirmation {"role": "project owner", "date": ...}


@pytest.fixture
def synthetic_template(tmp_path):
    """The committed synthetic, confirmed ``winkel-tripel`` fixture (tests/fixtures/templates),
    with ``templates.TEMPLATE_DIR`` pointed at a copy of it for the test."""
    from lego_image_processor.templates import load_template
    from maptemplates.testing import confirmed_copy, use_template_dir

    d = tmp_path / "templates-synthetic"
    confirmed_copy(TEMPLATE_FIXTURES, d, TEST_CONFIRMATION_DATE)
    with use_template_dir(d):
        yield load_template("winkel-tripel")


@pytest.fixture
def confirmed_winkel(tmp_path):
    """A buildable ``winkel-tripel``. The owner confirmed the package file on 2026-11-24 (T039 ->
    T081), so it is used as is; the other two cases are kept for a template not yet confirmed:

    - the package file is confirmed: it is used as is;
    - it exists but is unconfirmed: a ``confirmed_copy`` with the test confirmation, together with
      the package ice file ``winkel-tripel-ice.json`` (T076; the layout digest leaves the
      confirmation out, so the ice file stays valid for the copy);
    - it does not exist yet (before T037 and T076): the committed synthetic fixture template and
      its own ice file.
    """
    import json

    import lego_image_processor.templates as templates
    from maptemplates.testing import confirmed_copy, use_template_dir

    package = templates.TEMPLATE_DIR / "winkel-tripel.json"
    if package.exists() and json.loads(package.read_text(encoding="utf-8")).get("confirmation"):
        yield templates.load_template("winkel-tripel")
        return
    src = templates.TEMPLATE_DIR if package.exists() else TEMPLATE_FIXTURES
    d = tmp_path / "templates-confirmed"
    confirmed_copy(src, d, TEST_CONFIRMATION_DATE)
    with use_template_dir(d):
        yield templates.load_template("winkel-tripel")


@pytest.fixture
def unconfirmed_winkel(tmp_path):
    """The package ``winkel-tripel`` without its confirmation (and with its ice file), with
    ``templates.TEMPLATE_DIR`` pointed at the copy: the refusal to build on an unconfirmed template
    (FR-004) is tested on it, since the package file is confirmed (owner, 2026-11-24)."""
    import lego_image_processor.templates as templates
    from maptemplates.testing import unconfirmed_copy, use_template_dir

    d = tmp_path / "templates-unconfirmed"
    unconfirmed_copy(templates.TEMPLATE_DIR, d)
    with use_template_dir(d):
        t = templates.load_template("winkel-tripel")
        assert t.status == "unconfirmed" and not t.buildable
        yield t

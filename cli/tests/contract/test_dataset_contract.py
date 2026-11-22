"""Contract tests for the `dataset` CLI group (contracts/cli.md, Q2). Network is mocked."""

import json

import pytest
from click.testing import CliRunner

from tests.conftest import FakeResponse
from lego_image_processor.cli.main import cli
from lego_image_processor.datasets import cache as cache_mod

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."


@pytest.fixture
def runner():
    return CliRunner()


def _last(output):
    return output.rstrip("\n").splitlines()[-1]


def test_list_table(runner, tmp_path):
    r = runner.invoke(cli, ["dataset", "list", "--cache-dir", str(tmp_path)])
    assert r.exit_code == 0, r.output
    header = r.output.splitlines()[0].split()
    assert header[:5] == ["id", "version", "size", "license", "cached"]
    assert "etopo2022-surface-10m" in r.output and "9,357,398" in r.output
    assert "ersst-v5-ltm-1991-2020" in r.output
    assert _last(r.output) == DISCLAIMER


def test_list_json(runner, tmp_path):
    r = runner.invoke(cli, ["dataset", "list", "--format", "json", "--cache-dir", str(tmp_path)])
    assert r.exit_code == 0
    data = json.loads(r.output)
    assert data["disclaimer"] == DISCLAIMER
    rows = {d["id"]: d for d in data["datasets"]}
    assert rows["etopo2022-surface-10m"]["cached"] is False
    assert rows["kit31203-design"]["cached"] is True
    assert rows["ersst-v5-ltm-1991-2020"]["citation"]


def test_info(runner, tmp_path):
    r = runner.invoke(cli, ["dataset", "info", "etopo2022-surface-10m", "--cache-dir", str(tmp_path)])
    assert r.exit_code == 0, r.output
    for s in ("https://www.ngdc.noaa.gov/", "575c7a0c84f18b41430a723f26475fa41b1d787c94fa641f0d0705291e3991fd",
              "10.25921/fd45-gt74", "ETOPO 2022", "not cached"):
        assert s in r.output
    assert _last(r.output) == DISCLAIMER


def test_info_unknown(runner):
    r = runner.invoke(cli, ["dataset", "info", "nope"])
    assert r.exit_code == 1 and "nope" in r.output


def test_fetch_ok(runner, fixture_registry, monkeypatch):
    data = fixture_registry.files["ersst-v5-ltm-1991-2020"].read_bytes()
    monkeypatch.setattr(cache_mod, "_default_opener", lambda url, *a, **k: FakeResponse(data))
    r = runner.invoke(cli, ["dataset", "fetch", "ersst-v5-ltm-1991-2020"])
    assert r.exit_code == 0, r.output
    assert "Huang" in r.output and "Public domain" in r.output
    assert _last(r.output) == DISCLAIMER
    again = runner.invoke(cli, ["dataset", "fetch", "ersst-v5-ltm-1991-2020"])
    assert again.exit_code == 0 and "already cached" in again.output


def test_fetch_by_recipe(runner, fixture_registry, monkeypatch):
    files = {e: p.read_bytes() for e, p in fixture_registry.files.items()}
    by_url = {}
    from lego_image_processor.datasets import get_entry
    for i, b in files.items():
        by_url[get_entry(i).url] = b
    monkeypatch.setattr(cache_mod, "_default_opener", lambda url, *a, **k: FakeResponse(by_url[url]))
    r = runner.invoke(cli, ["dataset", "fetch", "--recipe", "official-31203-bathymetry"])
    assert r.exit_code == 0, r.output
    assert "Fetched etopo2022-surface-10m" in r.output and "ersst" not in r.output
    from lego_image_processor.datasets import is_cached
    assert is_cached(get_entry("etopo2022-surface-10m"), fixture_registry.cache_dir)


def test_fetch_checksum_mismatch_exit_4(runner, fixture_registry, monkeypatch):
    monkeypatch.setattr(cache_mod, "_default_opener", lambda url, *a, **k: FakeResponse(b"x" * 65480))
    r = runner.invoke(cli, ["dataset", "fetch", "ersst-v5-ltm-1991-2020"])
    assert r.exit_code == 4, r.output
    assert "expected" in r.output and "actual" in r.output


def test_fetch_network_error_exit_5(runner, fixture_registry, monkeypatch):
    def fail(url, *a, **k):
        raise OSError("no route to host")
    monkeypatch.setattr(cache_mod, "_default_opener", fail)
    r = runner.invoke(cli, ["dataset", "fetch", "ersst-v5-ltm-1991-2020"])
    assert r.exit_code == 5, r.output
    assert "no route to host" in r.output


def test_fetch_packaged_is_noop(runner):
    r = runner.invoke(cli, ["dataset", "fetch", "kit31203-design"])
    assert r.exit_code == 0 and "packaged" in r.output

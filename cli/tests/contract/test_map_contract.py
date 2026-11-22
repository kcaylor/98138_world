"""Contract tests for the `map` CLI group (contracts/cli.md, Q2)."""

import json
import time
from pathlib import Path

import numpy as np
import pytest
from click.testing import CliRunner

from tests.conftest import FakeResponse
from lego_image_processor.cli.main import cli
from lego_image_processor.datasets import cache as cache_mod

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
RECIPES = Path(__file__).resolve().parents[1] / "fixtures" / "recipes"
BUNDLED = ("official-31203", "official-31203-bathymetry", "ocean-sst", "land-elevation")


@pytest.fixture
def runner():
    return CliRunner()


def _last(output):
    return output.rstrip("\n").splitlines()[-1]


class TestRecipes:
    def test_lists_bundled(self, runner, tmp_path):
        r = runner.invoke(cli, ["map", "recipes", "--cache-dir", str(tmp_path)])
        assert r.exit_code == 0, r.output
        for rid in BUNDLED:
            assert rid in r.output
        assert "etopo2022-surface-10m" in r.output
        assert _last(r.output) == DISCLAIMER

    def test_copy(self, runner, tmp_path):
        dest = tmp_path / "mine.toml"
        r = runner.invoke(cli, ["map", "recipes", "--copy", "official-31203", str(dest)])
        assert r.exit_code == 0, r.output
        assert 'id = "official-31203"' in dest.read_text()
        again = runner.invoke(cli, ["map", "recipes", "--copy", "official-31203", str(dest)])
        assert again.exit_code == 1 and "--force" in again.output
        forced = runner.invoke(cli, ["map", "recipes", "--copy", "official-31203", str(dest), "--force"])
        assert forced.exit_code == 0

    def test_copy_unknown(self, runner, tmp_path):
        r = runner.invoke(cli, ["map", "recipes", "--copy", "nope", str(tmp_path / "x.toml")])
        assert r.exit_code == 1 and "nope" in r.output


class TestBuild:
    def test_official(self, runner, tmp_path):
        out = tmp_path / "official.json"
        preview = tmp_path / "official.png"
        report = tmp_path / "report.json"
        r = runner.invoke(cli, ["map", "build", "official-31203", "-o", str(out), "--preview", str(preview),
                                "--report", str(report), "--cache-dir", str(tmp_path / "empty")])
        assert r.exit_code == 0, r.output
        assert "10,240 / 10,240" in r.output
        assert _last(r.output) == DISCLAIMER
        assert json.loads(out.read_text())["metadata"]["map"]["recipe"]["id"] == "official-31203"
        assert preview.stat().st_size > 0
        rep = json.loads(report.read_text())
        assert rep["disclaimer"] == DISCLAIMER and rep["recipe_id"] == "official-31203"
        v = runner.invoke(cli, ["validate", str(out)])
        assert v.exit_code == 0 and "FULLY BUILDABLE" in v.output

    def test_quiet(self, runner, tmp_path):
        r = runner.invoke(cli, ["map", "build", "official-31203", "-o", str(tmp_path / "o.json"), "-q"])
        assert r.exit_code == 0 and r.output == ""

    @pytest.mark.parametrize("name,path,words", [
        ("bad_bounds.toml", "ocean.classification.bounds", ["strictly increasing"]),
        ("wrong_part_color.toml", "land.colors[0]", ["lego_medium_blue", "6141"]),
    ])
    def test_recipe_error_writes_nothing(self, runner, tmp_path, name, path, words):
        out = tmp_path / "x.json"
        r = runner.invoke(cli, ["map", "build", str(RECIPES / name), "-o", str(out)])
        assert r.exit_code == 1
        assert path in r.output
        for w in words:
            assert w in r.output
        assert not out.exists()

    def test_missing_dataset_exit_3_no_network(self, runner, tmp_path, monkeypatch):
        def boom(*a, **k):
            raise AssertionError("network used")
        monkeypatch.setattr(cache_mod, "_default_opener", boom)
        out = tmp_path / "x.json"
        t0 = time.monotonic()
        r = runner.invoke(cli, ["map", "build", "ocean-sst", "-o", str(out), "--cache-dir", str(tmp_path / "c")])
        assert time.monotonic() - t0 < 2
        assert r.exit_code == 3, r.output
        assert "dataset fetch ersst-v5-ltm-1991-2020" in r.output
        assert "--fetch" in r.output
        assert not out.exists()

    def test_fetch_downloads_then_builds(self, runner, tmp_path, fixture_registry, monkeypatch):
        data = fixture_registry.files["ersst-v5-ltm-1991-2020"].read_bytes()
        calls = []
        monkeypatch.setattr(cache_mod, "_default_opener", lambda url, *a, **k: calls.append(url) or FakeResponse(data))
        out = tmp_path / "sst.json"
        r = runner.invoke(cli, ["map", "build", "ocean-sst", "-o", str(out), "--fetch"])
        assert r.exit_code == 0, r.output
        assert len(calls) == 1 and "downloads.psl.noaa.gov" in calls[0]
        assert out.exists() and "Fetched ersst-v5-ltm-1991-2020" in r.output
        # second build: cached, no download
        r2 = runner.invoke(cli, ["map", "build", "ocean-sst", "-o", str(out), "--fetch"])
        assert r2.exit_code == 0 and len(calls) == 1

    def test_fetch_bad_checksum_exit_4(self, runner, tmp_path, fixture_registry, monkeypatch):
        data = fixture_registry.files["ersst-v5-ltm-1991-2020"].read_bytes()
        bad = data[:-1] + bytes([data[-1] ^ 0xFF])
        monkeypatch.setattr(cache_mod, "_default_opener", lambda url, *a, **k: FakeResponse(bad))
        out = tmp_path / "sst.json"
        r = runner.invoke(cli, ["map", "build", "ocean-sst", "-o", str(out), "--fetch"])
        assert r.exit_code == 4, r.output
        assert "expected" in r.output and "actual" in r.output
        assert not out.exists()

    def test_bathymetry_prints_agreement(self, runner, tmp_path, fixture_registry):
        fixture_registry.place_all()
        r = runner.invoke(cli, ["map", "build", "official-31203-bathymetry", "-o", str(tmp_path / "b.json")])
        assert r.exit_code == 0, r.output
        assert "ocean" in r.output and "agreement" in r.output.lower()
        assert "Citation" in r.output or "citation" in r.output


def _checker_recipe(tmp_path):
    lat = np.arange(-90 + 0.25, 90, 0.5)
    lon = np.arange(-180 + 0.25, 180, 0.5)
    field = ((np.floor(lat * 2)[:, None] + np.floor(lon * 2)[None, :]) % 2).astype(np.float32)
    np.save(tmp_path / "checker.npy", field)
    import hashlib
    sha = hashlib.sha256((tmp_path / "checker.npy").read_bytes()).hexdigest()
    text = f"""# Not affiliated with or endorsed by The LEGO Group.
format = "1"
id = "checker"
title = "Fine checkerboard"

[land]
role = "background"
colors = ["lego_white"]

[ocean]
role = "data"
colors = ["lego_earth_blue", "lego_medium_azur"]

[ocean.local]
path = "checker.npy"
format = "npy"
sha256 = "{sha}"
variable = "v"
lat = [-90, 90]
lon = [-180, 180]
citation = "Synthetic test field."
license = "CC0-1.0"

[ocean.classification]
method = "quantile"
"""
    p = tmp_path / "checker.toml"
    p.write_text(text)
    return p


class TestCheck:
    def test_detail_warning_and_report(self, runner, tmp_path):
        recipe = _checker_recipe(tmp_path)
        report = tmp_path / "check.json"
        r = runner.invoke(cli, ["map", "check", str(recipe), "--report", str(report)])
        assert r.exit_code == 0, r.output
        assert "finer than one grid cell" in r.output
        assert _last(r.output) == DISCLAIMER
        rep = json.loads(report.read_text())
        assert rep["recipe_id"] == "checker" and rep["disclaimer"] == DISCLAIMER
        assert rep["thresholds"]["variance_lost"] == 0.5
        assert rep["citations"][0]["license"] == "CC0-1.0"
        assert rep["citations"][0]["citation"] == "Synthetic test field."
        assert any(w["code"] == "detail_lost" for w in rep["warnings"])

    def test_smooth_no_warning(self, runner, tmp_path):
        r = runner.invoke(cli, ["map", "check", "official-31203"])
        assert r.exit_code == 0, r.output
        assert "No warnings" in r.output

    def test_missing_dataset(self, runner, tmp_path):
        r = runner.invoke(cli, ["map", "check", "ocean-sst", "--cache-dir", str(tmp_path)])
        assert r.exit_code == 3 and "dataset fetch ersst-v5-ltm-1991-2020" in r.output

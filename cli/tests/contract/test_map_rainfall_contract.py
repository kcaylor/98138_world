"""CLI contract for the rainfall map (feature 013; contracts/recipe-and-datasets.md). Offline, on
the derived fixtures."""

import json

import pytest
from click.testing import CliRunner

from tests.conftest import FakeResponse
from lego_image_processor.cli.main import cli
from lego_image_processor.datasets import cache as cache_mod
from lego_image_processor.datasets import get_entry

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."


def test_map_build_prints_overrides_and_two_unit_legends(fixture_registry, tmp_path):
    fixture_registry.place_all()
    out = tmp_path / "rain.json"
    r = CliRunner().invoke(cli, ["map", "build", "rainfall", "-o", str(out)])
    assert r.exit_code == 0, r.output
    text = r.output
    assert "Override Antarctica (region): " in text and "Override Greenland (region): " in text
    assert "Override sea ice (dataset): " in text and "cells of lego_white" in text
    assert "Legend (mm/day; mm/yr):" in text
    assert "below 0.5 (below 182.5 mm/yr)" in text and "0.5 to 1 (182.5 to 365 mm/yr)" in text
    assert "4 and above (1460 mm/yr and above)" in text and "3 to 5 (1095 to 1825 mm/yr)" in text
    for did in ("gpcp-v23-ltm-1991-2020", "nsidc-cdr-v6-seaice-minimum-1991-2020"):
        assert f"  - {did} (" in text
    assert text.rstrip().endswith(DISCLAIMER)
    layout = json.loads(out.read_text(encoding="utf-8"))
    assert layout["metadata"]["map"]["layers"][1]["overrides"][0]["name"] == "sea ice"


def test_map_build_fetch_downloads_every_file(fixture_registry, monkeypatch, tmp_path):
    by_url = {get_entry("gpcp-v23-ltm-1991-2020").url: fixture_registry.files["gpcp-v23-ltm-1991-2020"].read_bytes()}
    e = get_entry("nsidc-cdr-v6-seaice-minimum-1991-2020")
    for f, p in zip(e.files, fixture_registry.files[e.id]):
        by_url[f.url] = p.read_bytes()
    seen = []

    def opener(url, *a, **k):
        seen.append(url)
        return FakeResponse(by_url[url])

    monkeypatch.setattr(cache_mod, "_default_opener", opener)
    r = CliRunner().invoke(cli, ["map", "build", "rainfall", "--fetch", "-o", str(tmp_path / "r.json")])
    assert r.exit_code == 0, r.output
    assert sorted(seen) == sorted(by_url)


def test_map_build_without_data_exits_3(fixture_registry, tmp_path):
    r = CliRunner().invoke(cli, ["map", "build", "rainfall", "-o", str(tmp_path / "r.json")])
    assert r.exit_code == 3, r.output
    assert "dataset fetch" in r.output and DISCLAIMER in r.output


def test_map_recipes_lists_rainfall():
    r = CliRunner().invoke(cli, ["map", "recipes"])
    assert r.exit_code == 0 and "rainfall" in r.output

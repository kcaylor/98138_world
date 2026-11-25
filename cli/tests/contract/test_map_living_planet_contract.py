"""CLI contract for the living-planet map (feature 012; contracts/recipe-and-datasets.md "CLI
output"). Offline, on the derived fixtures."""

import json

import pytest
from click.testing import CliRunner

from lego_image_processor.cli.main import cli

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."


@pytest.fixture
def placed(fixture_registry):
    return fixture_registry.place_all()


def test_map_build_prints_no_data_and_legends(placed, tmp_path):
    out = tmp_path / "lp.json"
    r = CliRunner().invoke(cli, ["map", "build", "living-planet", "-o", str(out)])
    assert r.exit_code == 0, r.output
    text = r.output
    assert "No data (share): " in text and "cells of lego_white (min_lat 55, min_share 0.5, value 0)" in text
    assert "No data (unobserved): " in text and "(min_lat 60, sparse_lat 70, min_steps 12)" in text
    assert "Land shadow (cast east): " in text and "cells of lego_black" in text
    assert "Legend (mg m-3):" in text and "below 0.08" in text and "0.3 to 1" in text and "1 and above" in text
    assert "Legend (g C m-2 yr-1):" in text and "850 and above" in text and "+" not in text.split("Legend (g C")[1].split("Tiles")[0]
    for did in ("mod17a3-npp-mean-2000-2015", "etopo2022-surface-10m", "modis-aqua-chla-2013-2024"):
        assert f"  - {did} (" in text
    assert text.rstrip().endswith(DISCLAIMER)
    layout = json.loads(out.read_text(encoding="utf-8"))
    layers = layout["metadata"]["map"]["layers"]
    assert layers[0]["no_data"]["rule"] == "share" and layers[1]["transform"] == "log10"


def test_map_check_json_report(placed, tmp_path):
    p = tmp_path / "report.json"
    r = CliRunner().invoke(cli, ["map", "check", "living-planet", "--report", str(p)])
    assert r.exit_code == 0, r.output
    rep = json.loads(p.read_text(encoding="utf-8"))
    assert rep["layers"][1]["no_data"]["sparse_lat"] == 70
    assert rep["layers"][1]["class_bounds"][1] == pytest.approx(0.08)


def test_dataset_info_shows_content_checksum_and_http_reason(placed):
    r = CliRunner().invoke(cli, ["dataset", "info", "modis-aqua-chla-2013-2024"])
    assert r.exit_code == 0 and "content sha256:" in r.output
    r = CliRunner().invoke(cli, ["dataset", "info", "mod17a3-npp-mean-2000-2015"])
    assert r.exit_code == 0 and "http only:" in r.output and "land/ocean rule:" in r.output

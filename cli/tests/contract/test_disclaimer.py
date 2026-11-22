"""Disclaimer audit (FR-021, constitution VIII): every touched command and data file carries it."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from PIL import Image

from lego_image_processor.cli.main import cli
from lego_image_processor.kit import load_official_design
from lego_image_processor.kit.colors import DATA_DIR
from lego_image_processor.layout.grid import DISCLAIMER
from lego_image_processor.palette.loader import LegoPalette


def _last_line(output: str) -> str:
    return output.rstrip("\n").splitlines()[-1]


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def quantized_image(tmp_path):
    path = tmp_path / "q.png"
    Image.new("RGB", (128, 80), LegoPalette.load_default().get_by_name("White").rgb).save(path)
    return path


def test_layout_human_output_ends_with_disclaimer_and_json_carries_it(runner, quantized_image,
                                                                      tmp_path):
    out = tmp_path / "layout.json"
    result = runner.invoke(cli, ["layout", str(quantized_image), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert _last_line(result.output) == DISCLAIMER
    assert json.loads(out.read_text(encoding="utf-8"))["metadata"]["disclaimer"] == DISCLAIMER


def test_validate_human_output_ends_with_disclaimer_and_report_carries_it(runner, tmp_path):
    layout = tmp_path / "official.json"
    layout.write_text(load_official_design().to_layout().to_json(), encoding="utf-8")
    report = tmp_path / "report.json"
    result = runner.invoke(cli, ["validate", str(layout), "-o", str(report)])
    assert result.exit_code == 0, result.output
    assert _last_line(result.output) == DISCLAIMER
    assert json.loads(report.read_text(encoding="utf-8"))["disclaimer"] == DISCLAIMER


@pytest.mark.parametrize("command", [["kit", "inventory"], ["kit", "colors"]])
def test_kit_commands(runner, command):
    table = runner.invoke(cli, command)
    assert table.exit_code == 0, table.output
    assert _last_line(table.output) == DISCLAIMER
    as_json = runner.invoke(cli, command + ["--format", "json"])
    assert as_json.exit_code == 0
    assert json.loads(as_json.output)["source"]["disclaimer"] == DISCLAIMER


@pytest.mark.parametrize("path", sorted(DATA_DIR.glob("*.json")), ids=lambda p: p.name)
def test_every_data_file_source_has_disclaimer(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    assert data["source"]["disclaimer"] == DISCLAIMER

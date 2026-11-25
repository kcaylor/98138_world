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


# A stopped price fetch leaves `*.progress.json` in data/ (011 R9); it is not reference data.
@pytest.mark.parametrize("path", sorted(p for p in DATA_DIR.glob("*.json")
                                        if not p.name.endswith(".progress.json")),
                         ids=lambda p: p.name)
def test_every_data_file_source_has_disclaimer(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    assert data["source"]["disclaimer"] == DISCLAIMER


# --- Feature 004 commands (FR-023) ------------------------------------------------------------

@pytest.mark.parametrize("command", [
    ["map", "recipes"], ["map", "check", "official-31203"], ["dataset", "list"],
    ["dataset", "info", "ersst-v5-ltm-1991-2020"], ["dataset", "fetch", "kit31203-design"],
    ["kit", "part-colors"],
])
def test_feature_004_human_output(runner, command):
    result = runner.invoke(cli, command)
    assert result.exit_code == 0, result.output
    assert _last_line(result.output) == DISCLAIMER


def test_map_build_output_report_and_layout(runner, tmp_path):
    out, report = tmp_path / "o.json", tmp_path / "r.json"
    result = runner.invoke(cli, ["map", "build", "official-31203", "-o", str(out), "--report", str(report)])
    assert result.exit_code == 0, result.output
    assert _last_line(result.output) == DISCLAIMER
    meta = json.loads(out.read_text(encoding="utf-8"))["metadata"]
    assert meta["disclaimer"] == DISCLAIMER and meta["map"]["disclaimer"] == DISCLAIMER
    assert json.loads(report.read_text(encoding="utf-8"))["disclaimer"] == DISCLAIMER


@pytest.mark.parametrize("command", [["dataset", "list", "--format", "json"],
                                     ["kit", "part-colors", "--format", "json"]])
def test_feature_004_json(runner, command):
    result = runner.invoke(cli, command)
    assert result.exit_code == 0
    assert json.loads(result.output)["disclaimer"] == DISCLAIMER


def test_errors_end_with_disclaimer(runner, tmp_path):
    result = runner.invoke(cli, ["map", "build", "ocean-sst", "-o", str(tmp_path / "x.json"),
                                 "--cache-dir", str(tmp_path)])
    assert result.exit_code == 3
    assert _last_line(result.output) == DISCLAIMER


def test_bundled_recipes_carry_disclaimer():
    from lego_image_processor.maps.recipe import bundled_recipes
    for path in bundled_recipes().values():
        assert DISCLAIMER in path.read_text(encoding="utf-8")


# --- Feature 005 (T039, SC-007) -----------------------------------------------------------------

def test_parts_commands_end_with_disclaimer(runner, tmp_path):
    layout = tmp_path / "official.json"
    layout.write_text(load_official_design().to_layout().to_json(), encoding="utf-8")
    for command in (["parts", "list", str(layout)], ["parts", "list", str(layout), "--kits", "1"],
                    ["parts", "list", str(layout), "-o", str(tmp_path / "pl.json")],
                    ["parts", "export", str(layout), "--bricklink", str(tmp_path / "w.xml")],
                    ["parts", "export", str(layout), "--kits", "1", "--rebrickable", str(tmp_path / "r.csv")],
                    ["kit", "part-numbers"], ["kit", "part-colors"]):
        result = runner.invoke(cli, command)
        assert result.exit_code == 0, (command, result.output)
        assert _last_line(result.output) == DISCLAIMER, command
    assert json.loads((tmp_path / "pl.json").read_text(encoding="utf-8"))["disclaimer"] == DISCLAIMER
    as_json = runner.invoke(cli, ["parts", "list", str(layout), "--format", "json"])
    assert json.loads(as_json.output)["disclaimer"] == DISCLAIMER
    assert json.loads((DATA_DIR / "part_numbers.json").read_text(encoding="utf-8"))["source"]["disclaimer"] == DISCLAIMER


def test_readme_and_runbook_describe_the_enso_maps():
    """Feature 009, FR-017: README and runbook name both ENSO recipes and the `arrangement` key."""
    root = Path(__file__).resolve().parents[2]
    readme = (root / "README.md").read_text(encoding="utf-8")
    runbook = (root.parent / "docs" / "runbook.md").read_text(encoding="utf-8")
    for text in (readme, runbook):
        assert "ocean-el-nino" in text and "ocean-la-nina" in text
        assert "2026-27" in text
    assert 'arrangement = "B"' in readme
    assert DISCLAIMER in readme


# --- Feature 011 (T020, FR-018) -----------------------------------------------------------------

def test_parts_estimate_table_and_json_carry_the_disclaimer(runner, tmp_path):
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "prices" / "bricklink_price_guide.json"
    layout = tmp_path / "official.json"
    layout.write_text(load_official_design().to_layout().to_json(), encoding="utf-8")
    base = ["parts", "estimate", str(layout), "--prices", str(fixture), "--as-of", "2026-12-05"]
    for command in (base, base + ["--lines"], base + ["-o", str(tmp_path / "e.json")]):
        result = runner.invoke(cli, command)
        assert result.exit_code == 0, (command, result.output)
        assert _last_line(result.output) == DISCLAIMER, command
    as_json = runner.invoke(cli, base + ["--format", "json"])
    assert json.loads(as_json.output)["disclaimer"] == DISCLAIMER
    assert json.loads((tmp_path / "e.json").read_text(encoding="utf-8"))["disclaimer"] == DISCLAIMER


# --- Feature 017 (T037, FR-026): map stickers ---------------------------------------------------

def test_map_stickers_output_files_and_errors_carry_the_disclaimer(runner, tmp_path,
                                                                    fixture_registry):
    import io
    import xml.etree.ElementTree as ET

    from pypdf import PdfReader

    from lego_image_processor.maps.build import build_map
    from lego_image_processor.maps.recipe import load_recipe
    from lego_image_processor.stickers import print_sheet, sticker_set

    missing = runner.invoke(cli, ["map", "stickers", "ocean-sst", "-o", str(tmp_path / "x.pdf")])
    assert missing.exit_code == 3 and _last_line(missing.output) == DISCLAIMER
    unknown = runner.invoke(cli, ["map", "stickers", "nope", "-o", str(tmp_path / "x.pdf")])
    assert unknown.exit_code == 1 and _last_line(unknown.output) == DISCLAIMER

    fixture_registry.place_all()
    pdf, svg, summary = tmp_path / "s.pdf", tmp_path / "svg", tmp_path / "s.json"
    for out, fmt in ((pdf, "pdf"), (svg, "svg"), (summary, "json")):
        result = runner.invoke(cli, ["map", "stickers", "ocean-sst", "-o", str(out), "--format", fmt])
        assert result.exit_code == 0, result.output
        assert _last_line(result.output) == DISCLAIMER, fmt
    assert json.loads(summary.read_text(encoding="utf-8"))["disclaimer"] == DISCLAIMER
    for name in ("sticker-small.svg", "sticker-large.svg"):
        root = ET.fromstring((svg / name).read_bytes())
        assert root.find("{http://www.w3.org/2000/svg}desc").text == DISCLAIMER, name
    reader = PdfReader(io.BytesIO(pdf.read_bytes()))
    assert reader.metadata.subject.endswith(DISCLAIMER)
    assert DISCLAIMER in " ".join(reader.pages[0].extract_text().split())

    s = sticker_set(build_map(load_recipe("ocean-sst"), cache_dir=fixture_registry.cache_dir,
                              compare_official=False))
    for sticker in (s.small, s.large):
        assert " ".join(sticker.block("disclaimer").lines) == DISCLAIMER, sticker.size
    footer = [t for t in print_sheet(s, "letter").page.items if getattr(t, "tag", "") == "disclaimer"]
    assert footer[-1].text == DISCLAIMER

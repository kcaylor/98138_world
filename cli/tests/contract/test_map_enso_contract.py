"""CLI contract for the ENSO maps and the recipe key `arrangement` (feature 009;
contracts/recipe-arrangement.md, contracts/datasets.md). Offline, on the derived fixtures.
"""

import json
import re

import pytest
from click.testing import CliRunner

from tests.conftest import FakeResponse
from lego_image_processor.cli.main import cli
from lego_image_processor.datasets import cache as cache_mod
from lego_image_processor.maps.suitability import extra_tiles

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
B_LINE = "Arrangement: B (americas, frames 3·1·2, America in the centre) - from the recipe"
LEGEND = [("lego_earth_blue", "below -1.5"), ("lego_bright_bluish_green", "-1.5 to -0.5"),
          ("lego_medium_azur", "-0.5 to -0.25"), ("lego_bright_green", "-0.25 to -0.1"),
          ("lego_bright_yellowish_green", "-0.1 to +0.1"), ("lego_brick_yellow", "+0.1 to +0.3"),
          ("lego_flame_yellowish_orange", "+0.3 to +0.5"), ("lego_bright_orange", "+0.5 to +1"),
          ("lego_vibrant_coral", "+1 and above")]


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def enso(fixture_registry):
    return fixture_registry.place_all()


def _last(output):
    return output.rstrip("\n").splitlines()[-1]


def _legend_lines(output):
    lines = output.splitlines()
    i = next(n for n, line in enumerate(lines) if line.strip() == "Legend (°C):")
    return lines[i + 1:i + 1 + len(LEGEND)]


class TestBuild:
    def test_el_nino_from_recipe(self, runner, enso, tmp_path):
        out, rep = tmp_path / "x.json", tmp_path / "r.json"
        r = runner.invoke(cli, ["map", "build", "ocean-el-nino", "-o", str(out), "--report", str(rep)])
        assert r.exit_code == 0, r.output
        assert B_LINE in r.output
        assert json.loads(out.read_text())["metadata"]["arrangement"]["id"] == "B"
        report = json.loads(rep.read_text())
        assert report["arrangement_source"] == "recipe"
        # legend: 9 lines, cold to warm, with the cells of each class
        legend = _legend_lines(r.output)
        counts = {c["key"]: c["cells"] for c in report["layers"][1]["class_counts"]}
        for line, (key, text) in zip(legend, LEGEND):
            assert line.split()[0] == key and text in line, line
            assert line.split()[-1].replace(",", "") == str(counts[key])
        ocean = report["layers"][1]
        n = extra_tiles(ocean["supply"])
        assert f"  Tiles beyond one kit: {n:,}" in r.output.splitlines()
        assert "Tiles beyond one kit: 0" in r.output  # the land layer
        # citations, license, disclaimer (US1-5)
        assert "Huang" in r.output and "10.1175/JCLI-D-16-0836.1" in r.output
        assert "10.7289/V5T72FNM" in r.output
        assert "No constraints on data access or use" in r.output
        assert _last(r.output) == DISCLAIMER

    def test_option_wins(self, runner, enso, tmp_path):
        out, rep = tmp_path / "a.json", tmp_path / "r.json"
        r = runner.invoke(cli, ["map", "build", "ocean-el-nino", "--arrangement", "A", "-o", str(out),
                                "--report", str(rep)])
        assert r.exit_code == 0, r.output
        assert "Arrangement: A (europe-africa, frames 1·2·3, Europe and Africa in the centre) - from --arrangement" in r.output
        assert json.loads(out.read_text())["metadata"]["arrangement"]["id"] == "A"
        assert json.loads(rep.read_text())["arrangement_source"] == "option"

    def test_default_for_recipe_without_key(self, runner, enso, tmp_path):
        rep = tmp_path / "r.json"
        r = runner.invoke(cli, ["map", "build", "ocean-sst", "-o", str(tmp_path / "s.json"), "--report", str(rep)])
        assert r.exit_code == 0, r.output
        assert re.search(r"^Arrangement: A \(europe-africa.*\) - default$", r.output, re.M)
        assert json.loads(rep.read_text())["arrangement_source"] == "default"

    def test_bad_arrangement_exit_2(self, runner, enso, tmp_path):
        r = runner.invoke(cli, ["map", "build", "ocean-el-nino", "--arrangement", "D", "-o", str(tmp_path / "x.json")])
        assert r.exit_code == 2

    def test_not_cached_exit_3_no_network(self, runner, tmp_path, monkeypatch):
        def boom(*a, **k):
            raise AssertionError("network used")
        monkeypatch.setattr(cache_mod, "_default_opener", boom)
        r = runner.invoke(cli, ["map", "build", "ocean-el-nino", "-o", str(tmp_path / "x.json"),
                                "--cache-dir", str(tmp_path / "empty")])
        assert r.exit_code == 3, r.output
        assert "dataset fetch ersst-v5-1997-12" in r.output

    def test_fetch_wrong_bytes_exit_4(self, runner, fixture_registry, monkeypatch):
        data = fixture_registry.files["ersst-v5-1997-12"].read_bytes()
        bad = data[:-1] + bytes([data[-1] ^ 0xFF])
        monkeypatch.setattr(cache_mod, "_default_opener", lambda url, *a, **k: FakeResponse(bad))
        r = runner.invoke(cli, ["dataset", "fetch", "ersst-v5-1997-12"])
        assert r.exit_code == 4, r.output


class TestCheck:
    def test_check_shows_source_and_legend(self, runner, enso, tmp_path):
        rep = tmp_path / "r.json"
        r = runner.invoke(cli, ["map", "check", "ocean-el-nino", "--report", str(rep)])
        assert r.exit_code == 0, r.output
        assert B_LINE in r.output
        assert len(_legend_lines(r.output)) == 9
        assert json.loads(rep.read_text())["arrangement_source"] == "recipe"
        assert _last(r.output) == DISCLAIMER


class TestRecipes:
    def test_arrangement_column(self, runner, tmp_path):
        r = runner.invoke(cli, ["map", "recipes", "--cache-dir", str(tmp_path)])
        assert r.exit_code == 0, r.output
        lines = r.output.splitlines()
        assert lines[0].split()[:3] == ["id", "title", "arrangement"]
        col = lines[0].index("arrangement")
        rows = {line.split()[0]: line for line in lines[1:] if line.strip()}
        assert rows["ocean-el-nino"][col] == "B"
        assert rows["ocean-la-nina"][col] == "B"
        assert rows["ocean-sst"][col] == "A"


class TestPartsTopUp:
    """US3-2: one kit's top-up for an ENSO layout (FR-016)."""

    @pytest.fixture
    def layout(self, runner, enso, tmp_path):
        out, rep = tmp_path / "el-nino.json", tmp_path / "r.json"
        r = runner.invoke(cli, ["map", "build", "ocean-el-nino", "-o", str(out), "--report", str(rep)])
        assert r.exit_code == 0, r.output
        ocean = json.loads(rep.read_text())["layers"][1]
        short = {row["key"]: row["used"] - row["supplied"] for row in ocean["supply"]
                 if row["used"] > row["supplied"]}
        return out, short

    def test_parts_list_shows_shortfalls(self, runner, layout):
        out, short = layout
        r = runner.invoke(cli, ["parts", "list", str(out), "--kits", "1", "--format", "json"])
        assert r.exit_code == 0, r.output
        data = json.loads(r.output)
        lots = {l["color_key"]: l for l in data["lots"] if l["part_id"] == "98138" and l["to_buy"]}
        assert {k: l["to_buy"] for k, l in lots.items()} == short
        table = runner.invoke(cli, ["parts", "list", str(out), "--kits", "1"])
        assert table.exit_code == 0
        assert f"{sum(short.values()):,}" in table.output
        assert _last(table.output) == DISCLAIMER

    def test_bricklink_export_only_shortfalls(self, runner, layout, tmp_path):
        import xml.etree.ElementTree as ET

        out, short = layout
        xml = tmp_path / "wanted.xml"
        r = runner.invoke(cli, ["parts", "export", str(out), "--kits", "1", "--bricklink", str(xml)])
        assert r.exit_code == 0, r.output
        items = ET.fromstring(xml.read_text()).findall("ITEM")
        assert len(items) == len(short)
        assert all(i.findtext("ITEMID") == "98138" for i in items)
        assert sorted(int(i.findtext("MINQTY")) for i in items) == sorted(short.values())
        assert _last(r.output) == DISCLAIMER

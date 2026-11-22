"""Contract tests for the read-only `kit` CLI group (contracts/cli.md)."""

import json

import pytest
from click.testing import CliRunner

from lego_image_processor.cli.main import cli
from lego_image_processor.kit.colors import KIT_COLORS_PATH
from lego_image_processor.kit.inventory import INVENTORY_PATH
from lego_image_processor.kit.source import PINNED_SHA256, PINNED_URL

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."


@pytest.fixture
def runner():
    return CliRunner()


def _lines(output):
    return [l for l in output.strip().splitlines() if l.strip()]


class TestKitInventory:
    def test_table(self, runner):
        result = runner.invoke(cli, ["kit", "inventory"])
        assert result.exit_code == 0, result.output
        lines = _lines(result.output)
        header = lines[0].split()
        assert header == ["element", "part(s)", "description", "color", "qty", "role", "page"]
        assert "32 lines" in result.output
        assert "11,694 pieces" in result.output
        assert PINNED_URL in result.output
        assert PINNED_SHA256 in result.output
        assert lines[-1] == DISCLAIMER
        row = next(l for l in lines if l.startswith("614101"))
        assert "6141/4073" in row and "White" in row and "3064" in row and "land" in row and "159" in row

    def test_role_filter(self, runner):
        result = runner.invoke(cli, ["kit", "inventory", "--role", "land"])
        assert result.exit_code == 0, result.output
        rows = [l for l in _lines(result.output) if l[:1].isdigit()]
        assert len(rows) == 1 and rows[0].startswith("614101")
        assert _lines(result.output)[-1] == DISCLAIMER

    def test_role_filter_ocean(self, runner):
        result = runner.invoke(cli, ["kit", "inventory", "--role", "ocean"])
        rows = [l for l in _lines(result.output) if l[:1].isdigit()]
        assert len(rows) == 9

    def test_json_equals_package_file(self, runner):
        result = runner.invoke(cli, ["kit", "inventory", "--format", "json"])
        assert result.exit_code == 0
        assert result.output == INVENTORY_PATH.read_text(encoding="utf-8")
        assert json.loads(result.output)["source"]["disclaimer"] == DISCLAIMER

    def test_unsupported_kit(self, runner):
        result = runner.invoke(cli, ["kit", "inventory", "--kit", "999"])
        assert result.exit_code == 1
        assert ("Error: Kit ID '999' not supported. Currently only '31203' "
                "(LEGO World Map) is supported.") in result.output

    def test_bad_role_is_usage_error(self, runner):
        result = runner.invoke(cli, ["kit", "inventory", "--role", "roof"])
        assert result.exit_code == 2


class TestKitColors:
    def test_table(self, runner):
        result = runner.invoke(cli, ["kit", "colors"])
        assert result.exit_code == 0, result.output
        lines = _lines(result.output)
        assert lines[0].split() == ["key", "LEGO", "(id)", "BrickLink", "(id)", "Rebrickable",
                                    "(id)", "role", "element", "qty"]
        rows = [l for l in lines if l.startswith("lego_")]
        assert len(rows) == 10
        bbg = next(r for r in rows if r.startswith("lego_bright_bluish_green"))
        assert "Bright Bluish Green (107)" in bbg
        assert "Dark Turquoise (39)" in bbg
        assert "Dark Turquoise (3)" in bbg
        assert "6311437" in bbg and "1879" in bbg
        assert lines[-1] == DISCLAIMER

    def test_json_equals_package_file(self, runner):
        result = runner.invoke(cli, ["kit", "colors", "--format", "json"])
        assert result.exit_code == 0
        assert result.output == KIT_COLORS_PATH.read_text(encoding="utf-8")
        d = json.loads(result.output)
        assert len(d["colors"]) == 10
        assert sorted(c["role"] for c in d["colors"]).count("land") == 1

    def test_unsupported_kit(self, runner):
        result = runner.invoke(cli, ["kit", "colors", "--kit", "999"])
        assert result.exit_code == 1
        assert "Kit ID '999' not supported" in result.output


class TestKitPartColors:
    def test_table(self, runner):
        result = runner.invoke(cli, ["kit", "part-colors", "--part", "6141"])
        assert result.exit_code == 0, result.output
        lines = _lines(result.output)
        assert lines[-1] == DISCLAIMER
        white = next(l for l in lines if l.startswith("lego_white"))
        assert "White (1)" in white and "614101" in white and "yes" in white
        green = next(l for l in lines if l.startswith("lego_dark_green"))
        assert "Dark Green (28)" in green and "Green (6)" in green and "Green (2)" in green and "no" in green

    def test_both_parts_by_default(self, runner):
        result = runner.invoke(cli, ["kit", "part-colors"])
        assert result.exit_code == 0
        assert "6141" in result.output and "98138" in result.output

    def test_json(self, runner):
        result = runner.invoke(cli, ["kit", "part-colors", "--part", "98138", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["disclaimer"] == DISCLAIMER
        # 005 (Q3): every cited tile color, the kit's nine first
        assert len(data["colors"]) == 40 and sum(c["in_kit"] for c in data["colors"]) == 9
        assert all(c["in_kit"] for c in data["colors"][:9])
        assert {"lego", "bricklink", "rebrickable", "element_id"} <= set(data["colors"][0])

    def test_bad_part_is_usage_error(self, runner):
        assert runner.invoke(cli, ["kit", "part-colors", "--part", "3001"]).exit_code == 2

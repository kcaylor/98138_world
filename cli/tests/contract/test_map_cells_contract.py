"""Contract tests for `map cells` (feature 015, FR-002; contracts/cli.md)."""

import json

from click.testing import CliRunner

from lego_image_processor.cli.main import cli

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."


def test_writes_json(tmp_path):
    out = tmp_path / "cells.json"
    r = CliRunner().invoke(cli, ["map", "cells", "official-31203", "-o", str(out), "--arrangement", "C",
                                 "--cache-dir", str(tmp_path / "empty")])
    assert r.exit_code == 0, r.output
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["format_version"] == "1" and data["arrangement"] == "C"
    assert "Cells: " in r.output and str(out) in r.output
    assert "Preview only" in r.output
    assert r.output.rstrip("\n").splitlines()[-1] == DISCLAIMER


def test_summary_lists_layers_and_ice(tmp_path):
    out = tmp_path / "cells.json"
    r = CliRunner().invoke(cli, ["map", "cells", "official-31203", "-o", str(out)])
    assert r.exit_code == 0, r.output
    assert "Land layer: background" in r.output
    assert "Ocean layer: data, categorical" in r.output
    assert "Ice regions:" in r.output


def test_dataset_not_cached(tmp_path, fixture_registry):
    r = CliRunner().invoke(cli, ["map", "cells", "ocean-sst", "-o", str(tmp_path / "c.json")])
    assert r.exit_code != 0
    assert "ersst-v5-ltm-1991-2020" in r.output
    assert r.output.rstrip("\n").splitlines()[-1] == DISCLAIMER
    assert not (tmp_path / "c.json").exists()


def test_dataset_cached(tmp_path, fixture_registry):
    fixture_registry.place_all()
    out = tmp_path / "c.json"
    r = CliRunner().invoke(cli, ["map", "cells", "ocean-sst", "-o", str(out)])
    assert r.exit_code == 0, r.output
    assert "no source value" in r.output
    assert json.loads(out.read_text())["layers"]["ocean"]["units"] == "°C"


def test_unknown_recipe(tmp_path):
    r = CliRunner().invoke(cli, ["map", "cells", "nope", "-o", str(tmp_path / "c.json")])
    assert r.exit_code == 1
    assert r.output.rstrip("\n").splitlines()[-1] == DISCLAIMER

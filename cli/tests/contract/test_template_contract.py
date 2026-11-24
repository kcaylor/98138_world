"""Contract tests for the `template` command group (feature 016, T031; contracts/cli.md).

Every command prints the disclaimer last (JSON output carries it as its last key). Non-kit
templates come from the committed synthetic fixture (``synthetic_template``, T030).
"""

import json
from pathlib import Path

import numpy as np
import pytest
from click.testing import CliRunner

from lego_image_processor.cli.main import cli
from lego_image_processor.templates import KIT_TEMPLATE_ID, load_template

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "templates"


@pytest.fixture
def runner():
    return CliRunner()


def _last(output):
    return output.rstrip("\n").splitlines()[-1]


def _run(runner, args, code=0):
    r = runner.invoke(cli, ["template"] + args)
    assert r.exit_code == code, r.output
    return r


# --- template list ------------------------------------------------------------------------------

def test_list_table_kit_only(runner, tmp_path):
    from maptemplates.testing import use_template_dir

    with use_template_dir(tmp_path):
        r = _run(runner, ["list"])
    lines = [l for l in r.output.splitlines() if l.strip()]
    assert lines[0].split() == ["id", "title", "status", "land", "ocean", "margin", "arrangements"]
    kit = next(l for l in lines if l.startswith(KIT_TEMPLATE_ID))
    assert "reference" in kit and "3,062" in kit and "7,178" in kit and "A B C" in kit
    assert _last(r.output) == DISCLAIMER


def test_list_table_with_a_template(runner, synthetic_template):
    r = _run(runner, ["list"])
    row = next(l for l in r.output.splitlines() if l.startswith("winkel-tripel"))
    c = synthetic_template.counts
    assert "confirmed" in row and f"{c['land']:,}" in row and f"{c['ocean']:,}" in row
    assert f"{c['margin']:,}" in row and row.rstrip().endswith("A")
    assert _last(r.output) == DISCLAIMER


def test_list_json(runner, synthetic_template):
    r = _run(runner, ["list", "--format", "json"])
    doc = json.loads(r.output)
    assert list(doc)[-1] == "disclaimer" and doc["disclaimer"] == DISCLAIMER
    by_id = {t["id"]: t for t in doc["templates"]}
    assert list(by_id) == [KIT_TEMPLATE_ID, "winkel-tripel"]
    assert by_id[KIT_TEMPLATE_ID]["status"] == "reference"
    assert by_id[KIT_TEMPLATE_ID]["arrangements"] == ["A", "B", "C"]
    assert by_id[KIT_TEMPLATE_ID]["counts"]["land"] == 3062
    w = by_id["winkel-tripel"]
    assert set(w) == {"id", "title", "status", "counts", "arrangements"}
    assert w["status"] == "confirmed" and w["counts"] == synthetic_template.counts and w["arrangements"] == ["A"]


def test_list_broken_file_exit_1(runner, tmp_path):
    from maptemplates.testing import use_template_dir

    (tmp_path / "broken.json").write_text("{}", encoding="utf-8")
    with use_template_dir(tmp_path):
        r = _run(runner, ["list"], code=1)
    assert "Error: broken.json: format_version" in r.output
    assert _last(r.output) == DISCLAIMER


# --- template show ------------------------------------------------------------------------------

def test_show_table(runner, synthetic_template):
    t = synthetic_template
    r = _run(runner, ["show", "winkel-tripel"])
    out = r.output
    c = t.counts
    assert "winkel-tripel" in out and t.title in out
    assert "+proj=wintri +lat_1=50.4598 +lon_0=11.1 +R=1" in out
    assert "8 x 5 modules" in out and "128 x 80" in out and "8.0 mm" in out
    assert "6141" in out and "98138" in out and "3070b" in out
    assert f"{c['land']:,} land" in out and f"{c['ocean']:,} ocean" in out and f"{c['margin']:,} margin" in out
    assert f"ring {c['ring']:,}" in out
    m = c["modules"]
    assert f"{m['full']} full, {m['partial']} partial, {m['empty']} empty" in out
    tl = c["corners"]["top-left"]
    assert f"top-left {tl['width']} x {tl['height']}" in out
    assert "etopo2022-surface-10m" in out and t.dataset.version in out
    assert "Corrections: 1" in out
    assert "Confirmation: project owner, 2026-11-23" in out
    assert t.layout_sha256 in out
    assert _last(out) == DISCLAIMER


def test_show_json(runner, synthetic_template):
    t = synthetic_template
    doc = json.loads(_run(runner, ["show", "winkel-tripel", "--format", "json"]).output)
    assert list(doc)[-1] == "disclaimer" and doc["disclaimer"] == DISCLAIMER
    assert doc["id"] == "winkel-tripel" and doc["status"] == "confirmed"
    assert doc["projection"]["proj"] == "+proj=wintri +lat_1=50.4598 +lon_0=11.1 +R=1"
    assert doc["board"] == t.board and doc["parts"] == t.parts and doc["counts"] == t.counts
    assert doc["counts"]["ring"] == t.counts["ring"] and set(doc["counts"]["corners"]) == {
        "top-left", "top-right", "bottom-left", "bottom-right"}
    assert doc["dataset"]["id"] == "etopo2022-surface-10m"
    assert doc["corrections"] == 1
    assert doc["confirmation"] == {"role": "project owner", "date": "2026-11-23"}
    assert doc["layout_sha256"] == t.layout_sha256


def test_show_unconfirmed(runner, tmp_path):
    from maptemplates.testing import use_template_dir

    doc = json.loads((FIXTURES / "winkel-tripel.json").read_text(encoding="utf-8"))
    doc["confirmation"] = None
    (tmp_path / "winkel-tripel.json").write_text(json.dumps(doc), encoding="utf-8")
    with use_template_dir(tmp_path):
        r = _run(runner, ["show", "winkel-tripel"])
        assert "not confirmed by the project owner" in r.output
        row = next(l for l in _run(runner, ["list"]).output.splitlines() if l.startswith("winkel-tripel"))
        assert "unconfirmed" in row
        assert json.loads(_run(runner, ["show", "winkel-tripel", "--format", "json"]).output)["confirmation"] is None


def test_show_kit(runner):
    r = _run(runner, ["show", KIT_TEMPLATE_ID])
    assert "reference" in r.output and "3,062 land" in r.output and "7,178 ocean" in r.output
    assert "A, B, C" in r.output
    assert _last(r.output) == DISCLAIMER
    doc = json.loads(_run(runner, ["show", KIT_TEMPLATE_ID, "--format", "json"]).output)
    assert doc["status"] == "reference" and doc["dataset"] is None and doc["counts"]["margin"] == 0


def test_show_unknown_exit_1(runner):
    r = _run(runner, ["show", "nope"], code=1)
    assert "Error: unknown template 'nope'" in r.output and KIT_TEMPLATE_ID in r.output
    assert _last(r.output) == DISCLAIMER


# --- template locate ----------------------------------------------------------------------------

def test_locate_location(runner, synthetic_template):
    t = synthetic_template
    row, col = t.stud_at(51.5, -0.13)
    r = _run(runner, ["locate", "winkel-tripel", "51.5", "-0.13"])
    cls = t.class_at(row, col)
    assert f"row {row}, column {col}, section {t.section_label(row, col)}, {cls}" in r.output
    assert _last(r.output) == DISCLAIMER


def test_locate_negative_coordinates(runner, synthetic_template):
    t = synthetic_template
    row, col = t.stud_at(-33.9, -58.4)
    r = _run(runner, ["locate", "winkel-tripel", "-33.9", "-58.4"])
    assert f"row {row}, column {col}" in r.output


def test_locate_margin(runner, synthetic_template):
    t = synthetic_template
    lat = np.linspace(-89.5, 89.5, 359)
    hit = next(float(la) for la in lat if t.stud_at(float(la), -168.7) is None)
    r = _run(runner, ["locate", "winkel-tripel", repr(hit), "-168.7"])
    assert "off the globe (margin)" in r.output
    assert _last(r.output) == DISCLAIMER


def test_locate_stud(runner, synthetic_template):
    t = synthetic_template
    row, col = map(int, np.argwhere(t.land)[100])
    lat, lon = t.location(row, col)
    r = _run(runner, ["locate", "winkel-tripel", "--stud", str(row), str(col)])
    assert f"row {row}, column {col}, section {t.section_label(row, col)}, land (part 6141)" in r.output
    assert f"{lat:.4f}" in r.output and f"{lon:.4f}" in r.output
    assert _last(r.output) == DISCLAIMER


def test_locate_margin_stud(runner, synthetic_template):
    r = _run(runner, ["locate", "winkel-tripel", "--stud", "0", "0"])
    assert "margin (part 3070b)" in r.output and "off the globe (margin)" in r.output


def test_locate_kit(runner):
    kit = load_template(KIT_TEMPLATE_ID)
    row, col = kit.stud_at(0.0, 11.1)
    r = _run(runner, ["locate", KIT_TEMPLATE_ID, "0", "11.1"])
    assert f"row {row}, column {col}, section {kit.section_label(row, col)}" in r.output
    r = _run(runner, ["locate", KIT_TEMPLATE_ID, "-89", "0"])
    assert "outside the kit grid" in r.output


@pytest.mark.parametrize("args", [
    ["locate", KIT_TEMPLATE_ID, "91", "0"],
    ["locate", KIT_TEMPLATE_ID, "0", "180.5"],
    ["locate", KIT_TEMPLATE_ID, "--stud", "80", "0"],
    ["locate", KIT_TEMPLATE_ID, "--stud", "0", "-1"],
    ["locate", KIT_TEMPLATE_ID, "10"],
    ["locate", KIT_TEMPLATE_ID],
    ["locate", KIT_TEMPLATE_ID, "10", "20", "--stud", "1", "2"],
    ["locate", KIT_TEMPLATE_ID, "north", "east"],
])
def test_locate_bad_input_exit_2(runner, args):
    _run(runner, args, code=2)


def test_locate_unknown_template_exit_1(runner):
    r = _run(runner, ["locate", "nope", "0", "0"], code=1)
    assert "unknown template" in r.output and _last(r.output) == DISCLAIMER


def test_group_help(runner):
    r = _run(runner, ["--help"])
    for cmd in ("list", "show", "locate"):
        assert cmd in r.output

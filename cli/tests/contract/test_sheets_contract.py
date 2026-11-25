"""CLI contract for `sheets build` and `sheets counts` (006 T016, T023, T025; contracts/cli.md)."""

import io
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from click.testing import CliRunner
from pypdf import PdfReader

from lego_image_processor.cli.main import cli
from lego_image_processor.kit import load_official_design
from lego_image_processor.kit.source import DISCLAIMER

from ..unit.parts.layouts import SMALL, make_grid
from ..unit.sheets.layouts import FEW, full_grid

MM = 72 / 25.4
PRINT_LINE = "Print at 100% (no fit-to-page); check the 100 mm scale bar."


def _last(output: str) -> str:
    return output.rstrip("\n").splitlines()[-1]


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture(scope="module")
def layouts(tmp_path_factory):
    d = tmp_path_factory.mktemp("sheets")
    out = {}
    for name, grid in (("official", load_official_design().to_layout()), ("few", full_grid(FEW)),
                       ("small", make_grid(SMALL))):
        p = d / f"{name}.json"
        p.write_text(grid.to_json(), encoding="utf-8")
        out[name] = p
    bad = d / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    out["bad"] = bad
    return out


# --- sheets build: PDF --------------------------------------------------------------------------

def test_build_pdf_default(runner, layouts, tmp_path):
    out = tmp_path / "set.pdf"
    r = runner.invoke(cli, ["sheets", "build", str(layouts["official"]), "-o", str(out)])
    assert r.exit_code == 0, r.output
    reader = PdfReader(io.BytesIO(out.read_bytes()))
    assert len(reader.pages) == 42
    assert "42 pages (1 overview, 1 legend, 40 sections), Letter" in r.output
    assert "10 lots (10 verified)" in r.output
    assert PRINT_LINE in r.output
    assert _last(r.output) == DISCLAIMER


def test_output_required(runner, layouts):
    r = runner.invoke(cli, ["sheets", "build", str(layouts["few"])])
    assert r.exit_code == 2


@pytest.mark.parametrize("name", ["bad", "small", "missing"])
def test_bad_layout_exit_1_writes_nothing(runner, layouts, tmp_path, name):
    path = layouts.get(name, tmp_path / "missing.json")
    out = tmp_path / "x.pdf"
    r = runner.invoke(cli, ["sheets", "build", str(path), "-o", str(out)])
    assert r.exit_code == 1, r.output
    assert "Error:" in r.output and not out.exists()
    assert _last(r.output) == DISCLAIMER


def test_output_path_problems(runner, layouts, tmp_path):
    r = runner.invoke(cli, ["sheets", "build", str(layouts["few"]), "-o", str(tmp_path)])
    assert r.exit_code == 1 and "directory" in r.output
    r = runner.invoke(cli, ["sheets", "build", str(layouts["few"]), "-o",
                            str(tmp_path / "nope" / "x.pdf")])
    assert r.exit_code == 1 and "does not exist" in r.output


def test_overwrite_and_quiet(runner, layouts, tmp_path):
    out = tmp_path / "set.pdf"
    out.write_bytes(b"old")
    r = runner.invoke(cli, ["sheets", "build", str(layouts["few"]), "-o", str(out), "-q",
                            "--sections", "A1"])
    assert r.exit_code == 0 and r.output == ""
    assert out.read_bytes().startswith(b"%PDF")


def test_build_deterministic(runner, layouts, tmp_path):
    a, b = tmp_path / "a.pdf", tmp_path / "b.pdf"
    for p in (a, b):
        assert runner.invoke(cli, ["sheets", "build", str(layouts["few"]), "-o", str(p), "-q"]).exit_code == 0
    assert a.read_bytes() == b.read_bytes()


# --- subsets, paper, title (US4) ----------------------------------------------------------------

def test_sections_subset(runner, layouts, tmp_path):
    out = tmp_path / "two.pdf"
    r = runner.invoke(cli, ["sheets", "build", str(layouts["few"]), "-o", str(out),
                            "--sections", "C2,B2"])
    assert r.exit_code == 0, r.output
    reader = PdfReader(io.BytesIO(out.read_bytes()))
    assert len(reader.pages) == 4
    assert "Section B2" in reader.pages[2].extract_text()
    assert "Section C2" in reader.pages[3].extract_text()


def test_unknown_section(runner, layouts, tmp_path):
    out = tmp_path / "x.pdf"
    r = runner.invoke(cli, ["sheets", "build", str(layouts["few"]), "-o", str(out),
                            "--sections", "B2,J9"])
    assert r.exit_code == 1 and "J9" in r.output and "A1-H5" in r.output and not out.exists()


def test_a4(runner, layouts, tmp_path):
    out = tmp_path / "a4.pdf"
    r = runner.invoke(cli, ["sheets", "build", str(layouts["few"]), "-o", str(out), "--paper", "a4",
                            "--sections", "A1"])
    assert r.exit_code == 0 and ", A4" in r.output
    box = PdfReader(io.BytesIO(out.read_bytes())).pages[0].mediabox
    assert abs(float(box.width) - 210 * MM) < 0.01 and abs(float(box.height) - 297 * MM) < 0.01


def test_title(runner, layouts, tmp_path):
    out = tmp_path / "t.pdf"
    r = runner.invoke(cli, ["sheets", "build", str(layouts["few"]), "-o", str(out),
                            "--title", "Café map", "--sections", "A1"])
    assert r.exit_code == 0 and "Café map" in r.output
    assert "Café map" in PdfReader(io.BytesIO(out.read_bytes())).pages[0].extract_text()
    r = runner.invoke(cli, ["sheets", "build", str(layouts["few"]), "-o", str(tmp_path / "g.pdf"),
                            "--title", "Δ map"])
    assert r.exit_code == 1 and "Latin-1" in r.output and not (tmp_path / "g.pdf").exists()
    svg = tmp_path / "svg"
    r = runner.invoke(cli, ["sheets", "build", str(layouts["few"]), "-o", str(svg), "--format", "svg",
                            "--title", "Δ map", "--sections", "A1"])
    assert r.exit_code == 0, r.output
    assert "Δ map" in (svg / "page-01.svg").read_text(encoding="utf-8")


# --- sheets build: SVG (US3) --------------------------------------------------------------------

def test_build_svg(runner, layouts, tmp_path):
    out = tmp_path / "deep" / "svg"
    r = runner.invoke(cli, ["sheets", "build", str(layouts["official"]), "-o", str(out),
                            "--format", "svg"])
    assert r.exit_code == 0, r.output
    files = sorted(p.name for p in out.iterdir())
    assert files == [f"page-{i:02d}.svg" for i in range(1, 43)]
    root = ET.fromstring((out / "page-03.svg").read_text(encoding="utf-8"))
    studs = root.findall(".//{http://www.w3.org/2000/svg}circle[@class='stud']")
    assert len(studs) == 256
    assert _last(r.output) == DISCLAIMER and PRINT_LINE in r.output


def test_svg_output_is_a_file(runner, layouts, tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("x")
    r = runner.invoke(cli, ["sheets", "build", str(layouts["few"]), "-o", str(f), "--format", "svg"])
    assert r.exit_code == 1 and "not a directory" in r.output


# --- sheets counts (US3) ------------------------------------------------------------------------

def test_counts_table(runner, layouts):
    r = runner.invoke(cli, ["sheets", "counts", str(layouts["official"])])
    assert r.exit_code == 0, r.output
    lines = r.output.splitlines()
    a1 = next(l for l in lines if l.startswith("A1"))
    assert "x 0-15" in a1 and "y 0-15" in a1 and "total 256" in a1 and "#1:" in a1
    assert sum(1 for l in lines if l[:2] in {f"{c}{n}" for c in "ABCDEFGH" for n in range(1, 6)}
               and "total 256" in l) == 40
    assert "Legend" in r.output and "White" in r.output
    assert _last(r.output) == DISCLAIMER


def test_counts_json_stdout_and_file(runner, layouts, tmp_path):
    r = runner.invoke(cli, ["sheets", "counts", str(layouts["official"]), "--format", "json"])
    assert r.exit_code == 0
    d = json.loads(r.output)
    assert d["disclaimer"] == DISCLAIMER and len(d["sections"]) == 40
    assert d["layout"]["path"] == str(layouts["official"]) and len(d["layout"]["sha256"]) == 64
    out = tmp_path / "counts.json"
    r = runner.invoke(cli, ["sheets", "counts", str(layouts["official"]), "-o", str(out)])
    assert r.exit_code == 0 and _last(r.output) == DISCLAIMER
    assert json.loads(out.read_text(encoding="utf-8")) == d
    again = tmp_path / "again.json"
    runner.invoke(cli, ["sheets", "counts", str(layouts["official"]), "-o", str(again)])
    assert again.read_bytes() == out.read_bytes()


def test_counts_bad_layout(runner, layouts):
    r = runner.invoke(cli, ["sheets", "counts", str(layouts["bad"])])
    assert r.exit_code == 1 and _last(r.output) == DISCLAIMER


def test_legacy_schema_rejected(runner, tmp_path):
    """US1 scenario 7: a layout that is not schema 2.0 fails with the reason and writes nothing."""
    legacy = Path(__file__).resolve().parents[1] / "fixtures" / "layouts" / "legacy_v1_layout.json"
    out = tmp_path / "x.pdf"
    r = runner.invoke(cli, ["sheets", "build", str(legacy), "-o", str(out)])
    assert r.exit_code == 1 and "schema" in r.output.lower() and not out.exists()
    counts = tmp_path / "c.json"
    r = runner.invoke(cli, ["sheets", "counts", str(legacy), "-o", str(counts)])
    assert r.exit_code == 1 and not counts.exists()


def test_sheets_in_help(runner):
    r = runner.invoke(cli, ["sheets", "--help"])
    assert r.exit_code == 0 and "build" in r.output and "counts" in r.output


def test_svg_rebuild_removes_stale_pages_only(runner, layouts, tmp_path):
    out = tmp_path / "svg"
    r = runner.invoke(cli, ["sheets", "build", str(layouts["few"]), "-o", str(out), "--format", "svg"])
    assert r.exit_code == 0, r.output
    (out / "notes.txt").write_text("keep me", encoding="utf-8")
    (out / "page-cover.svg").write_text("<svg/>", encoding="utf-8")  # not one of our page names
    r = runner.invoke(cli, ["sheets", "build", str(layouts["few"]), "-o", str(out), "--format", "svg",
                            "--sections", "A1"])
    assert r.exit_code == 0, r.output
    pages = sorted(p.name for p in out.glob("page-*.svg") if p.name != "page-cover.svg")
    assert len(pages) < 42 and pages == [f"page-{i:02d}.svg" for i in range(1, len(pages) + 1)]
    assert (out / "notes.txt").exists() and (out / "page-cover.svg").exists()


# --- layouts on the Winkel tripel template (feature 016 T072; contracts/cli.md "Other commands") --

@pytest.fixture
def winkel_file(confirmed_winkel, tmp_path):
    from ..winkel_layouts import winkel_grid
    p = tmp_path / "winkel.json"
    p.write_text(winkel_grid(confirmed_winkel).to_json(), encoding="utf-8")
    return p


def test_build_winkel_pdf(runner, winkel_file, confirmed_winkel, tmp_path):
    out = tmp_path / "w.pdf"
    r = runner.invoke(cli, ["sheets", "build", str(winkel_file), "-o", str(out)])
    assert r.exit_code == 0, r.output
    assert (f"Template: winkel-tripel ({confirmed_winkel.title}); arrangement A only (the frames of a "
            "curved map cannot be re-hung)") in r.output
    assert "Arrangement:" not in r.output
    n = confirmed_winkel.counts["margin"]
    assert f"10,240 pieces, {n:,} of them square tiles (part 3070b)" in r.output
    assert _last(r.output) == DISCLAIMER
    reader = PdfReader(io.BytesIO(out.read_bytes()))
    assert len(reader.pages) == 42  # overview, one legend page (4 lots), 40 sections
    text = reader.pages[0].extract_text()
    assert "winkel-tripel" in text and "tiles 1x1 square" in text


def test_counts_winkel(runner, winkel_file, confirmed_winkel):
    r = runner.invoke(cli, ["sheets", "counts", str(winkel_file), "--format", "json"])
    assert r.exit_code == 0, r.output
    d = json.loads(r.output)
    assert d["template"] == {"id": "winkel-tripel", "title": confirmed_winkel.title}
    assert any(e["part_type"] == "square_tile" for e in d["legend"]) and list(d)[-1] == "disclaimer"
    r = runner.invoke(cli, ["sheets", "counts", str(winkel_file)])
    assert r.exit_code == 0, r.output
    n = confirmed_winkel.counts["margin"]
    assert f"Template winkel-tripel ({confirmed_winkel.title}): margin square tiles counted per section" in r.output
    assert any(l.startswith("#") and "tile 1x1 square  Black (lego_black)" in l and l.endswith(f"{n:,}")
               for l in r.output.splitlines())
    assert _last(r.output) == DISCLAIMER


def test_kit_sheets_output_has_no_template_wording(runner, layouts, tmp_path):
    r = runner.invoke(cli, ["sheets", "build", str(layouts["official"]), "-o", str(tmp_path / "o.pdf")])
    assert r.exit_code == 0
    assert "Template" not in r.output and "square" not in r.output
    assert "Arrangement: A (" in r.output
    r = runner.invoke(cli, ["sheets", "counts", str(layouts["official"])])
    assert "Template" not in r.output and "square" not in r.output

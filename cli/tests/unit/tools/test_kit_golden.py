"""Kit golden harness (feature 016, T004; research R9, SC-001): ``maptemplates kit-golden``.

The harness digests every kit 31203 output from the CLI commands themselves. These tests check the
digest rules on small inputs and one short run (official-31203, combinations A and B, from the
dataset fixtures). The full 8 recipes x A, B, C comparison with the committed golden is
tests/integration/test_kit_outputs_unchanged.py.
"""

from __future__ import annotations

import ast
import io
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner
from PIL import Image

from maptemplates import golden
from maptemplates.__main__ import main

CLI_DIR = Path(__file__).resolve().parents[3]
REPO = CLI_DIR.parent


def _png(pixels, compress_level):
    im = Image.new("RGB", (2, 1))
    im.putdata(pixels)
    buf = io.BytesIO()
    im.save(buf, format="PNG", compress_level=compress_level)
    return buf.getvalue()


class TestDigestRules:
    def test_png_records_pixel_and_byte_digests(self):
        a = _png([(1, 2, 3), (4, 5, 6)], 0)
        b = _png([(1, 2, 3), (4, 5, 6)], 9)
        c = _png([(1, 2, 3), (4, 5, 7)], 9)
        da, db, dc = golden.png_digest(a), golden.png_digest(b), golden.png_digest(c)
        assert set(da) == {"bytes", "sha256", "pixels", "size", "mode"}
        assert da["size"] == "2x1" and da["mode"] == "RGB"
        assert da["pixels"] == db["pixels"]          # same decoded pixels
        assert da["sha256"] != db["sha256"]          # different encoder settings show as bytes
        assert dc["pixels"] != db["pixels"]

    def test_blob_digest(self):
        assert golden.blob_digest(b"abc") == {
            "bytes": 3, "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"}

    def test_svg_pages_digest_depends_on_names_text_and_order(self):
        pages = [("page-01.svg", "<svg>1</svg>"), ("page-02.svg", "<svg>2</svg>")]
        d = golden.svg_pages_digest(pages)
        assert d["pages"] == 2 and d["bytes"] == 24
        assert golden.svg_pages_digest(pages) == d
        assert golden.svg_pages_digest(pages[::-1])["sha256"] != d["sha256"]
        assert golden.svg_pages_digest([pages[0], ("page-02.svg", "<svg>3</svg>")])["sha256"] != d["sha256"]

    def test_generated_at_is_fixed(self):
        text = '{\n  "a": 1,\n  "generated_at": "2026-11-23T10:11:12Z",\n  "b": 2\n}\n'
        out = golden.fix_generated_at(text)
        assert out == text.replace("2026-11-23T10:11:12Z", golden.FIXED_GENERATED_AT)
        with pytest.raises(golden.GoldenError):
            golden.fix_generated_at('{"x": 1}')

    def test_temporary_directory_is_replaced_by_a_placeholder(self, tmp_path):
        text = f"Layout: {tmp_path}/ocean-sst/A/layout.json\nPreview: {tmp_path.resolve()}/p.png\n"
        out = golden.normalise_text(text, tmp_path)
        assert str(tmp_path) not in out and str(tmp_path.resolve()) not in out
        assert out == (f"Layout: {golden.PLACEHOLDER}/ocean-sst/A/layout.json\n"
                       f"Preview: {golden.PLACEHOLDER}/p.png\n")

    def test_canonical_json_ignores_key_order(self):
        assert golden.canonical({"b": [1, {"d": 2, "c": 3}], "a": "é"}) == \
            golden.canonical({"a": "é", "b": [1, {"c": 3, "d": 2}]})


def _part_data(tmp_path, extra_part=False, change_kit=False):
    src = Path(golden.DATA_DIR)
    d = tmp_path / "data"
    d.mkdir()
    pc = json.loads((src / "part_colors.json").read_text(encoding="utf-8"))
    pn = json.loads((src / "part_numbers.json").read_text(encoding="utf-8"))
    if extra_part:  # a non-kit part and its citations are appended
        pc["parts"]["3070b"] = [dict(pc["parts"]["98138"][0], key="lego_black")]
        pc["source"]["citations"].append({"id": "bricklink-3070b", "title": "x", "url": "u", "accessed": "d"})
        pc["source"]["excluded"].append({"part": "3070b", "rebrickable_id": 1, "name": "n", "reason": "r"})
        pn["parts"]["3070b"] = dict(pn["parts"]["98138"])
        pn["source"]["pages"].append({"id": "bricklink-3070b", "title": "x", "url": "u", "sha256": "0" * 64,
                                      "accessed": "d"})
        pn["source"]["rules"].append("A new rule for parts not in the kit.")
    if change_kit:
        pc["parts"]["6141"][0]["notes"] = "changed"
    # key order and indentation do not matter (canonical JSON)
    (d / "part_colors.json").write_text(json.dumps(pc, sort_keys=True), encoding="utf-8")
    (d / "part_numbers.json").write_text(json.dumps(pn, indent=4), encoding="utf-8")
    return d


class TestReferenceDigests:
    def test_kit_blocks_and_citations(self):
        ref = golden.reference_digests()
        assert set(ref) == {"part_colors.json", "part_numbers.json"}
        assert set(ref["part_colors.json"]) == {"parts.6141", "parts.98138", "citations", "excluded"}
        assert set(ref["part_numbers.json"]) == {"parts.6141", "parts.98138", "citations"}
        assert all(len(v) == 64 for f in ref.values() for v in f.values())

    def test_appended_part_and_formatting_leave_kit_digests_unchanged(self, tmp_path):
        assert golden.reference_digests(_part_data(tmp_path, extra_part=True)) == golden.reference_digests()

    def test_a_changed_kit_row_changes_the_digest(self, tmp_path):
        ref = golden.reference_digests(_part_data(tmp_path, change_kit=True))
        assert ref["part_colors.json"]["parts.6141"] != golden.reference_digests()["part_colors.json"]["parts.6141"]


class TestCompare:
    def _doc(self):
        return {"format_version": "1", "inputs": {"datasets": "fixtures"}, "datasets": [],
                "reference_data": {"part_colors.json": {"parts.6141": "a"}},
                "variants": [{"recipe": "ocean-sst", "combination": "A",
                              "outputs": {"layout.json": {"bytes": 1, "sha256": "x"},
                                          "preview.png": {"bytes": 2, "sha256": "y", "pixels": "p"}}}]}

    def test_equal(self):
        assert golden.compare(self._doc(), self._doc()) == []

    def test_names_recipe_combination_and_output(self):
        a, b = self._doc(), self._doc()
        b["variants"][0]["outputs"]["preview.png"]["pixels"] = "q"
        del b["variants"][0]["outputs"]["layout.json"]
        b["reference_data"]["part_colors.json"]["parts.6141"] = "b"
        diffs = golden.compare(a, b)
        assert any("ocean-sst A: preview.png differs" in d for d in diffs)
        assert any("ocean-sst A: layout.json missing" in d for d in diffs)
        assert any("part_colors.json parts.6141 differs" in d for d in diffs)

    def test_missing_variant(self):
        b = self._doc()
        b["variants"] = []
        assert golden.compare(self._doc(), b) == ["ocean-sst A: variant missing"]


@pytest.fixture(scope="module")
def short_run(tmp_path_factory):
    keep = tmp_path_factory.mktemp("kit-golden")
    doc = golden.kit_golden(fixtures=True, recipes=["official-31203"], combinations=("A", "B"), keep=keep)
    return doc, keep


class TestShortRun:
    def test_deterministic(self, short_run, tmp_path):
        doc, _ = short_run
        again = golden.kit_golden(fixtures=True, recipes=["official-31203"], combinations=("A", "B"))
        assert golden.compare(doc, again) == []
        assert golden.to_text(doc) == golden.to_text(again)

    def test_entries_sorted_and_inputs_recorded(self, short_run):
        doc, _ = short_run
        assert [(v["recipe"], v["combination"]) for v in doc["variants"]] == \
            [("official-31203", "A"), ("official-31203", "B")]
        i = doc["inputs"]
        assert i["datasets"] == "fixtures" and i["generated_at"] == golden.FIXED_GENERATED_AT
        assert i["as_of"] == golden.AS_OF and i["prices"]["file"] == "bricklink_price_guide.json"
        assert doc["reference_data"] == golden.reference_digests()
        assert doc["disclaimer"] == "Not affiliated with or endorsed by The LEGO Group."

    def test_every_output_digested(self, short_run):
        doc, _ = short_run
        a, b = (v["outputs"] for v in doc["variants"])
        expected = {"map-build.txt", "layout.json", "report.json", "preview.png", "map-check.txt",
                    "cells.json", "map-cells.txt", "parts.json", "parts-1kit.json", "parts-list.txt",
                    "parts-list-1kit.txt", "parts-export.txt", "bricklink.xml", "rebrickable.csv",
                    "parts-export-1kit.txt", "bricklink-1kit.xml", "rebrickable-1kit.csv",
                    "estimate.json", "estimate.txt", "counts.json", "counts.txt",
                    "sheets-letter-svg.txt", "sheets-letter.svg", "sheets-letter-pdf.txt",
                    "sheets-letter.pdf"}
        assert set(a) == expected
        assert set(b) == expected - {"sheets-letter-pdf.txt", "sheets-letter.pdf"}   # PDF: A only
        assert set(a["preview.png"]) == {"bytes", "sha256", "pixels", "size", "mode"}
        assert a["sheets-letter.svg"]["pages"] == 43  # 40 sections + overview, legend, assembly (010)
        # one kit covers the official design: the top-up exports write nothing
        assert a["bricklink-1kit.xml"] is None and a["rebrickable-1kit.csv"] is None
        assert a["layout.json"] != b["layout.json"]

    def test_digests_are_of_the_files_written(self, short_run):
        doc, keep = short_run
        out = doc["variants"][0]["outputs"]
        d = keep / "official-31203" / "A"
        layout = (d / "layout.json").read_bytes()
        assert golden.blob_digest(layout) == out["layout.json"]
        meta = json.loads(layout)["metadata"]
        assert meta["generated_at"] == golden.FIXED_GENERATED_AT
        assert json.loads((d / "report.json").read_bytes())["generated_at"] == golden.FIXED_GENERATED_AT
        assert golden.png_digest((d / "preview.png").read_bytes()) == out["preview.png"]
        for name in ("map-build.txt", "map-check.txt", "estimate.txt"):
            text = (d / name).read_text(encoding="utf-8")
            assert golden.blob_digest(text.encode("utf-8")) == out[name]
            assert str(keep) not in text and str(keep.resolve()) not in text
        build = (d / "map-build.txt").read_text(encoding="utf-8")
        assert "Layout: official-31203/A/layout.json" in build
        assert build.rstrip("\n").splitlines()[-1] == "Not affiliated with or endorsed by The LEGO Group."
        assert json.loads((d / "estimate.json").read_bytes())["staleness"]["as_of"] == golden.AS_OF
        pdf = (d / "sheets-letter.pdf").read_bytes()
        assert pdf.startswith(b"%PDF") and golden.blob_digest(pdf) == out["sheets-letter.pdf"]


def test_cli_writes_the_digests(tmp_path, monkeypatch):
    calls = {}

    def fake(**kw):
        calls.update(kw)
        return {"format_version": "1", "inputs": {}, "datasets": [], "reference_data": {},
                "variants": [{"recipe": "r", "combination": "A", "outputs": {"x": {"bytes": 1, "sha256": "s"}}}],
                "disclaimer": golden.DISCLAIMER}

    monkeypatch.setattr(golden, "kit_golden", fake)
    out = tmp_path / "golden.json"
    res = CliRunner().invoke(main, ["kit-golden", "--fixtures", "--out", str(out)])
    assert res.exit_code == 0, res.output
    assert calls == {"cache_dir": None, "fixtures": True}
    assert json.loads(out.read_text(encoding="utf-8"))["variants"][0]["recipe"] == "r"
    assert res.output.rstrip("\n").splitlines()[-1] == golden.DISCLAIMER
    bad = CliRunner().invoke(main, ["kit-golden", "--fixtures", "--cache-dir", str(tmp_path), "--out", str(out)])
    assert bad.exit_code == 2


# The library modules the harness imports, all present at commit 6038d9c (main, the golden's base;
# also at af3ce57), so the same harness runs against a checkout of main (quickstart step 10).
BASE_COMMIT = "6038d9c"
BASE_MODULES = {"lego_image_processor.cli.main", "lego_image_processor.datasets.registry",
                "lego_image_processor.kit.source", "lego_image_processor.maps.recipe"}


def _library_imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("lego_image_processor"):
            found.add(node.module)
        elif isinstance(node, ast.Import):
            found |= {a.name for a in node.names if a.name.startswith("lego_image_processor")}
    return found


def test_harness_uses_only_library_modules_present_at_base():
    used = _library_imports(Path(golden.__file__))
    assert used <= BASE_MODULES, used - BASE_MODULES
    if shutil.which("git") is None or not (REPO / ".git").exists():
        pytest.skip("not a git checkout")
    git = lambda *a: subprocess.run(["git", *a], cwd=REPO, capture_output=True)  # noqa: E731
    if git("cat-file", "-e", f"{BASE_COMMIT}^{{commit}}").returncode != 0:
        pytest.skip(f"commit {BASE_COMMIT} is not in this clone")
    for m in sorted(used):
        rel = "cli/src/" + m.replace(".", "/") + ".py"
        assert git("cat-file", "-e", f"{BASE_COMMIT}:{rel}").returncode == 0, rel

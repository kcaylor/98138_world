"""Deterministic JSON and all-or-nothing writer tests for the maintainer tool."""

import json
from pathlib import Path

import pytest

from kit31203 import assemble


class TestDumpJson:
    def test_format(self):
        text = assemble.dump_json({"b": 1, "a": [1, 2], "c": "é"})
        assert text.endswith("}\n")
        assert "\n  \"b\": 1" in text
        assert "é" in text
        assert json.loads(text) == {"b": 1, "a": [1, 2], "c": "é"}

    def test_deterministic(self):
        obj = {"x": {"z": 1, "y": [3, 2]}, "w": None}
        assert assemble.dump_json(obj) == assemble.dump_json(json.loads(assemble.dump_json(obj)))


class TestAtomicWriter:
    def test_writes_only_on_success(self, tmp_path):
        out = tmp_path / "data"
        out.mkdir()
        (out / "keep.json").write_text("old\n")
        with assemble.AtomicWriter(out) as w:
            w.write_json("kit_a.json", {"a": 1})
            w.write_json("keep.json", {"new": True})
            assert not (out / "kit_a.json").exists()
        assert json.loads((out / "kit_a.json").read_text()) == {"a": 1}
        assert json.loads((out / "keep.json").read_text()) == {"new": True}

    def test_failure_writes_nothing(self, tmp_path):
        out = tmp_path / "data"
        out.mkdir()
        (out / "keep.json").write_text("old\n")
        with pytest.raises(RuntimeError):
            with assemble.AtomicWriter(out) as w:
                w.write_json("kit_a.json", {"a": 1})
                w.write_json("keep.json", {"new": True})
                raise RuntimeError("step failed")
        assert not (out / "kit_a.json").exists()
        assert (out / "keep.json").read_text() == "old\n"
        assert sorted(p.name for p in out.iterdir()) == ["keep.json"]

    def test_written_paths(self, tmp_path):
        with assemble.AtomicWriter(tmp_path) as w:
            w.write_json("a.json", {})
        assert w.written == [tmp_path / "a.json"]


class TestCompare:
    def test_ignores_generated_on(self):
        a = {"source": {"generated_on": "2026-11-21", "url": "u"}, "rows": ["01"]}
        b = {"source": {"generated_on": "2027-01-01", "url": "u"}, "rows": ["01"]}
        assert assemble.json_differences(a, b) == []

    def test_reports_paths(self):
        a = {"source": {"url": "u"}, "rows": ["01", "11"], "n": 1}
        b = {"source": {"url": "v"}, "rows": ["01", "10"]}
        diffs = assemble.json_differences(a, b)
        assert "source.url" in diffs
        assert "rows[1]" in diffs
        assert "n" in diffs


# --- Design, mask, change record and counts (feature 003 US2) -------------------------------

import numpy as np  # noqa: E402
from click.testing import CliRunner  # noqa: E402

from kit31203 import sections  # noqa: E402
from lego_image_processor.kit.design import parse_design  # noqa: E402
from lego_image_processor.kit.source import DISCLAIMER, PINNED_SHA256, PINNED_URL  # noqa: E402

from .synthetic_sections import render_section  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "kit31203"
PALETTE = [
    "lego_white", "lego_bright_bluish_green", "lego_medium_azur", "lego_bright_yellowish_green",
    "lego_brick_yellow", "lego_bright_green", "lego_bright_orange", "lego_vibrant_coral",
    "lego_flame_yellowish_orange", "lego_earth_blue",
]
SUPPLIED = dict(zip(PALETTE, [3064, 1879, 1607, 1060, 725, 601, 601, 601, 599, 393]))
SYNTHETIC_USE = dict(zip(PALETTE, [3000, 1850, 1600, 1050, 720, 600, 600, 520, 200, 100]))


def _source(pages=(22,)):
    return {"title": "LEGO 31203 World Map building instructions", "url": PINNED_URL,
            "sha256": PINNED_SHA256, "pages": list(pages), "generator": "test",
            "generated_on": "2026-11-21", "citations": [], "disclaimer": DISCLAIMER}


def _synthetic_index_grid(use=SYNTHETIC_USE, seed=7):
    flat = np.concatenate([np.full(n, PALETTE.index(k)) for k, n in use.items()])
    assert flat.size == 128 * 80
    np.random.default_rng(seed).shuffle(flat)
    return flat.reshape(80, 128)


class TestPlaceAndEncode:
    def test_forty_sections_assemble_into_128x80(self):
        cells = {(c, r): np.full((16, 16), c * 5 + r) for c in range(8) for r in range(5)}
        grid = assemble.place_sections(cells)
        assert grid.shape == (80, 128)
        assert grid[0, 0] == 0 and grid[79, 127] == 39
        assert grid[16 * 2 + 3, 16 * 5 + 9] == 5 * 5 + 2  # col 5, row 2
        assert grid[0, 16] == 5  # col 1, row 0

    def test_missing_section_fails(self):
        cells = {(c, r): np.zeros((16, 16)) for c in range(8) for r in range(5)}
        del cells[(3, 3)]
        with pytest.raises(ValueError):
            assemble.place_sections(cells)

    def test_rows_are_base36_palette_indices(self):
        grid = _synthetic_index_grid()
        rows = assemble.encode_rows(grid)
        assert len(rows) == 80 and all(len(r) == 128 for r in rows)
        assert all(int(rows[y][x], 36) == grid[y, x] for y in (0, 40, 79) for x in (0, 64, 127))
        assert assemble.decode_rows(rows).tolist() == grid.tolist()


class TestCounts:
    def test_used_supplied_spare(self):
        counts = assemble.color_counts(_synthetic_index_grid(), PALETTE, SUPPLIED)
        assert [c["key"] for c in counts] == PALETTE
        white = counts[0]
        assert white == {"key": "lego_white", "used": 3000, "supplied": 3064, "spare": 64,
                         "spare_note": "unexplained"}
        assert sum(c["used"] for c in counts) == 10240
        assemble.check_supply(counts)

    def test_over_supply_fails(self):
        use = dict(SYNTHETIC_USE, lego_earth_blue=400)
        use["lego_white"] =10240 - sum(v for k, v in use.items() if k != "lego_white")
        counts = assemble.color_counts(_synthetic_index_grid(use), PALETTE, SUPPLIED)
        with pytest.raises(assemble.SupplyError) as exc:
            assemble.check_supply(counts)
        assert exc.value.exit_code == 8
        msg = str(exc.value)
        assert "lego_earth_blue" in msg and "400" in msg and "393" in msg


class TestMask:
    def test_mask_from_white_cells(self):
        grid = _synthetic_index_grid()
        mask = assemble.build_mask(grid, PALETTE, _source())
        assert mask["land_positions"] == 3000
        assert mask["ocean_positions"] == 7240
        assert mask["dimensions"] == {"width": 128, "height": 80, "total_positions": 10240}
        assert mask["coordinate_system"] == "top_left_origin"
        assert mask["derived_from"] == "kit_31203_design.json"
        assert mask["source"]["sha256"] == PINNED_SHA256
        land = {(x, y) for x, y in mask["land_coordinates"]}
        assert land == {(x, y) for y in range(80) for x in range(128) if grid[y, x] == 0}
        assert mask["land_coordinates"] == sorted(mask["land_coordinates"], key=lambda c: (c[1], c[0]))
        assert len(mask["mask_2d"]) == 80 and mask["mask_2d"][3][5] == bool(grid[3, 5] == 0)

    def test_change_record_lists_differences(self):
        grid = _synthetic_index_grid()
        old = assemble.build_mask(grid, PALETTE, _source())
        land_xy = old["land_coordinates"][0]
        grid2 = grid.copy()
        grid2[land_xy[1], land_xy[0]] = 1           # land -> ocean
        ocean_xy = next((x, y) for y in range(80) for x in range(128) if grid[y, x] != 0)
        grid2[ocean_xy[1], ocean_xy[0]] = 0         # ocean -> land
        new = assemble.build_mask(grid2, PALETTE, _source())
        changes = assemble.mask_changes(old, new)
        assert {(c["x"], c["y"], c["old"], c["new"]) for c in changes} == {
            (land_xy[0], land_xy[1], "land", "ocean"), (ocean_xy[0], ocean_xy[1], "ocean", "land")}
        rec = assemble.build_change_record(old, "ab" * 32, new, _source())
        assert rec["count"] == 2 and rec["previous_mask_sha256"] == "ab" * 32
        assert set(rec) == {"format_version", "source", "previous_mask_sha256", "count", "changes"}

    def test_change_record_carried_forward_once_regenerated(self):
        grid = _synthetic_index_grid()
        mask = assemble.build_mask(grid, PALETTE, _source())
        earlier = {"format_version": "1", "source": _source(), "previous_mask_sha256": "cd" * 32,
                   "count": 1, "changes": [{"x": 1, "y": 2, "old": "ocean", "new": "land"}]}
        rec = assemble.build_change_record(mask, "ef" * 32, mask, _source(), previous_record=earlier)
        assert rec["previous_mask_sha256"] == "cd" * 32
        assert rec["changes"] == earlier["changes"] and rec["count"] == 1


# --- extract pipeline on synthetic inputs ----------------------------------------------------

def _placements():
    data = json.loads((FIXTURES / "placements.json").read_text())["synthetic"]
    return {int(p): [sections.Placement(page=int(p), **r) for r in rows] for p, rows in data.items()}


def _words():
    data = json.loads((FIXTURES / "page159_words.json").read_text())
    return [(w["x"], w["y"], w["text"]) for w in data["words"]]


def _images(index_grid):
    images = {}
    for k, page in enumerate(sections.SECTION_PAGES):
        col, row = k // 5, k % 5
        block = index_grid[row * 16:(row + 1) * 16, col * 16:(col + 1) * 16]
        grid = [[PALETTE[v] for v in line] for line in block.tolist()]
        images[page] = render_section(grid, size=(154, 153) if row == 2 else (154, 154), seed=k)
    return images


@pytest.fixture(scope="module")
def synthetic_images():
    return _images(_synthetic_index_grid())


@pytest.fixture
def tool(monkeypatch, tmp_path):
    from kit31203 import __main__ as tool_main

    def install(images):
        monkeypatch.setattr(tool_main, "read_pdf_inputs", lambda pdf, cache_dir: tool_main.PdfInputs(
            words=_words(), placements=_placements(), load_image=lambda p: images[p.page]))
        empty = tmp_path / "overrides.json"
        empty.write_text('{"format_version": "1", "overrides": []}\n')
        monkeypatch.setattr(tool_main, "OVERRIDES_PATH", empty)
        return tool_main
    return install


class TestExtractPipeline:
    FILES = {"kit_31203_inventory.json", "kit_31203_design.json",
             "lego_world_map_land_sea_mask.json", "kit_31203_mask_changes.json"}

    def test_writes_all_files(self, tool, tmp_path, synthetic_images):
        main = tool(synthetic_images).main
        out = tmp_path / "out"
        res = CliRunner().invoke(main, ["extract", "--out-dir", str(out), "--date", "2026-11-21"])
        assert res.exit_code == 0, res.output
        assert {p.name for p in out.iterdir()} == self.FILES
        design = json.loads((out / "kit_31203_design.json").read_text())
        parse_design(design)  # library validation passes
        assert design["palette"] == PALETTE
        assert assemble.decode_rows(design["rows"]).tolist() == _synthetic_index_grid().tolist()
        assert design["classification"]["flagged"] == 0
        assert "Sections: 40" in res.output
        assert "lego_white" in res.output and "3000" in res.output
        assert res.output.strip().endswith(DISCLAIMER)

    def test_check_ignores_generated_on_and_reports_differences(self, tool, tmp_path, synthetic_images):
        main = tool(synthetic_images).main
        out = tmp_path / "out"
        assert CliRunner().invoke(main, ["extract", "--out-dir", str(out), "--date", "2026-11-21"]).exit_code == 0
        res = CliRunner().invoke(main, ["extract", "--out-dir", str(out), "--check", "--date", "2027-01-01"])
        assert res.exit_code == 0, res.output
        assert "no differences" in res.output
        path = out / "kit_31203_design.json"
        design = json.loads(path.read_text())
        row = design["rows"][5]
        design["rows"][5] = ("1" if row[0] != "1" else "2") + row[1:]
        path.write_text(json.dumps(design, indent=2) + "\n")
        res = CliRunner().invoke(main, ["extract", "--out-dir", str(out), "--check"])
        assert res.exit_code == 1
        assert "kit_31203_design.json: rows[5]" in res.output

    def test_failing_step_writes_nothing(self, tool, tmp_path):
        use = dict(SYNTHETIC_USE, lego_earth_blue=400)
        use["lego_white"] = 10240 - sum(v for k, v in use.items() if k != "lego_white")
        main = tool(_images(_synthetic_index_grid(use))).main
        out = tmp_path / "out"
        out.mkdir()
        (out / "keep.json").write_text("old\n")
        res = CliRunner().invoke(main, ["extract", "--out-dir", str(out)])
        assert res.exit_code == 8, res.output
        assert "lego_earth_blue" in res.output
        assert sorted(p.name for p in out.iterdir()) == ["keep.json"]

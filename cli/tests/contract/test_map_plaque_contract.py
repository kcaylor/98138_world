"""Contract tests for the in-margin plaque on the command line (feature 017 T078; US3-1 to US3-6,
FR-021 - FR-024; contracts/cli.md "map build, map check, map cells" and contracts/in-margin-plaque.md).

``map build`` and ``map check`` print, after 016's ``Margin:`` line (which counts the margin tiles
placed), the ``Plaque:`` line; the ``Layout:`` line counts the pieces and the plaque tile. Every row
of the ``--plaque`` error table is checked with its exit code. ``parts list``, ``parts export``,
``parts estimate``, ``sheets build``, ``sheets counts`` and ``validate`` accept a plaque layout and
name the tile. The tile's label, part and color come from ``load_plaque_parts()`` and the rows and
columns from ``place_plaque`` on the loaded template, never from the example numbers. Offline, on
the dataset fixtures and ``confirmed_winkel``.
Not affiliated with or endorsed by The LEGO Group.
"""

import json

import pytest
from click.testing import CliRunner

from lego_image_processor.cli.main import cli
from lego_image_processor.cli.map import KIT_MARGIN_NOTE
from lego_image_processor.kit.plaque_parts import load_plaque_parts
from lego_image_processor.maps.margin import place_plaque
from lego_image_processor.maps.recipe import bundled_recipes

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
CORNERS = ("top-left", "top-right", "bottom-left", "bottom-right")
NEEDS = "needs 6 x 6 studs plus one stud from the outline ring"
PRICE_FIXTURES = __import__("pathlib").Path(__file__).parent.parent / "fixtures" / "prices"


@pytest.fixture
def tile():
    return load_plaque_parts().plaques["small"].tile


@pytest.fixture
def data(fixture_registry):
    return fixture_registry.place_all()


def _run(*args):
    return CliRunner().invoke(cli, [str(a) for a in args])


def _last(r):
    return r.output.rstrip("\n").splitlines()[-1]


def _label(tile):
    w, h = tile.studs
    return f"tile {w}x{h}"


def plaque_text(template, tile, corner):
    """``tile 6x6 (part 10202), Black, bottom-left, rows 73-78, columns 1-6`` from the loader and the
    loaded template."""
    st = place_plaque(template, corner).studs
    w, h = tile.studs
    return (f"{_label(tile)} (part {tile.part_id}), {tile.color.lego.name}, {corner}, rows "
            f"{st['row']}-{st['row'] + h - 1}, columns {st['col']}-{st['col'] + w - 1}")


def plaque_line(template, tile, corner, source):
    return f"Plaque: {plaque_text(template, tile, corner)} - {source}"


def _recipe(tmp_path, top="", tables=""):
    text = bundled_recipes()["ocean-sst"].read_text(encoding="utf-8")
    if top:
        text = text.replace("seed = 31203\n", f"seed = 31203\n{top}\n", 1)
    p = tmp_path / "ocean-sst.toml"
    p.write_text(text + ("\n" + tables if tables else ""), encoding="utf-8")
    return p


# --- map build and map check -------------------------------------------------------------------

class TestBuildOutput:
    def test_plaque_line_after_the_margin_line(self, data, confirmed_winkel, tile, tmp_path):
        t = confirmed_winkel
        out = tmp_path / "bl.json"
        r = _run("map", "build", "ocean-sst", "--template", "winkel-tripel", "--plaque", "bottom-left",
                 "-o", out, "--preview", tmp_path / "bl.png")
        assert r.exit_code == 0, r.output
        lines = r.output.splitlines()
        i = lines.index(f"Template: winkel-tripel ({t.title}) - from --template")
        assert lines[i + 1] == f"Margin: {t.counts['margin'] - 36:,} square tiles (part 3070b): lego_black; no ring"
        assert lines[i + 2] == plaque_line(t, tile, "bottom-left", "from --plaque")
        d = json.loads(out.read_text())
        assert len(d["positions"]) == 10204
        assert (f"Layout: {out} (10,204 positions, {t.counts['land']:,} land plates, {t.counts['ocean']:,} "
                f"ocean tiles, {t.counts['margin'] - 36:,} margin tiles, 1 plaque tile)") in lines
        assert _last(r) == DISCLAIMER

    def test_check(self, data, confirmed_winkel, tile):
        r = _run("map", "check", "ocean-sst", "--template", "winkel-tripel", "--plaque", "top-right")
        assert r.exit_code == 0, r.output
        lines = r.output.splitlines()
        i = lines.index(plaque_line(confirmed_winkel, tile, "top-right", "from --plaque"))
        assert lines[i - 1].startswith(f"Margin: {confirmed_winkel.counts['margin'] - 36:,} square tiles")
        assert _last(r) == DISCLAIMER

    def test_from_the_recipe(self, data, confirmed_winkel, tile, tmp_path):
        recipe = _recipe(tmp_path, top='template = "winkel-tripel"', tables='[margin]\nplaque = "top-left"\n')
        r = _run("map", "build", recipe, "-o", tmp_path / "w.json")
        assert r.exit_code == 0, r.output
        assert plaque_line(confirmed_winkel, tile, "top-left", "from the recipe") in r.output.splitlines()

    def test_with_a_ring(self, data, confirmed_winkel, tile, tmp_path):
        t = confirmed_winkel
        r = _run("map", "build", "ocean-sst", "--template", "winkel-tripel", "--plaque", "bottom-right",
                 "--ring-color", "lego_white", "-o", tmp_path / "w.json")
        assert r.exit_code == 0, r.output
        lines = r.output.splitlines()
        i = lines.index(plaque_line(t, tile, "bottom-right", "from --plaque"))
        assert lines[i - 1] == (f"Margin: {t.counts['margin'] - 36:,} square tiles (part 3070b): lego_black; "
                                f"ring {t.counts['ring']:,} lego_white")

    def test_without_a_plaque_unchanged(self, data, confirmed_winkel, tmp_path):
        t = confirmed_winkel
        out = tmp_path / "w.json"
        r = _run("map", "build", "ocean-sst", "--template", "winkel-tripel", "-o", out)
        assert r.exit_code == 0, r.output
        lines = r.output.splitlines()
        assert f"Margin: {t.counts['margin']:,} square tiles (part 3070b): lego_black; no ring" in lines
        assert "Plaque" not in r.output and "plaque tile" not in r.output and "6x6" not in r.output
        assert (f"Layout: {out} (10,240 positions, {t.counts['land']:,} land plates, {t.counts['ocean']:,} "
                f"ocean tiles, {t.counts['margin']:,} margin tiles)") in lines

    def test_kit_build_unchanged(self, data, tmp_path):
        out = tmp_path / "k.json"
        r = _run("map", "build", "ocean-sst", "-o", out, "--plaque", "none")
        assert r.exit_code == 0, r.output
        assert "Plaque" not in r.output and "Margin" not in r.output
        layout = next(line for line in r.output.splitlines() if line.startswith("Layout:"))
        assert layout.startswith(f"Layout: {out} (10,240 positions, ") and layout.endswith(" ocean tiles)")


# --- the --plaque error table (contracts/cli.md; US3-5) ------------------------------------------

class TestErrors:
    @pytest.mark.parametrize("cmd", ["build", "check", "cells"])
    def test_unknown_corner_exit_2(self, cmd, tmp_path):
        out = ["-o", tmp_path / "x.json"] if cmd != "check" else []
        r = _run("map", cmd, "ocean-sst", "--template", "winkel-tripel", "--plaque", "centre", *out)
        assert r.exit_code == 2
        assert all(c in r.output for c in CORNERS)

    @pytest.mark.parametrize("cmd", ["build", "check", "cells"])
    def test_on_the_kit_exit_1(self, cmd, data, confirmed_winkel, tmp_path):
        out = ["-o", tmp_path / "x.json"] if cmd != "check" else []
        r = _run("map", cmd, "ocean-sst", "--plaque", "bottom-left", *out)
        assert r.exit_code == 1, r.output
        assert "the kit template has no margin" in r.output and "winkel-tripel" in r.output
        assert _last(r) == DISCLAIMER and not (tmp_path / "x.json").exists()

    def test_recipe_corner_on_a_kit_build_exit_0(self, data, tmp_path):
        recipe = _recipe(tmp_path, tables='[margin]\nplaque = "bottom-left"\n')
        r = _run("map", "build", recipe, "-o", tmp_path / "k.json")
        assert r.exit_code == 0, r.output
        assert KIT_MARGIN_NOTE in r.output.splitlines() and "Plaque" not in r.output
        assert _last(r) == DISCLAIMER

    def test_the_tile_does_not_fit_exit_1(self, data, tmp_path):
        """A template copy whose bottom-left clear block is too small (an ocean stud near the corner)."""
        import lego_image_processor.templates as templates
        from lego_image_processor.templates.board import board_counts
        from maptemplates import document
        from maptemplates.testing import use_template_dir

        d = tmp_path / "templates-misfit"
        d.mkdir()
        doc = json.loads((templates.TEMPLATE_DIR / "winkel-tripel.json").read_text(encoding="utf-8"))
        assert doc.get("confirmation")
        rows = [list(r) for r in doc["classes"]]
        rows[75][7] = "O"
        doc["classes"] = ["".join(r) for r in rows]
        doc["locations"]["lat"][75][7] = -55.0
        doc["locations"]["lon"][75][7] = -170.0
        doc["counts"] = board_counts(doc["classes"])
        (d / "winkel-tripel.json").write_text(document.to_text(doc), encoding="utf-8")
        with use_template_dir(d):
            block = templates.load_template("winkel-tripel").counts["corners"]["bottom-left"]
            out = tmp_path / "m.json"
            r = _run("map", "build", "ocean-sst", "--template", "winkel-tripel", "--plaque", "bottom-left",
                     "-o", out)
            ok = _run("map", "check", "ocean-sst", "--template", "winkel-tripel", "--plaque", "top-left")
        assert r.exit_code == 1, r.output
        assert "Cannot build ocean-sst: --plaque:" in r.output and "bottom-left" in r.output
        assert NEEDS in r.output and f"{block['height']} x {block['width']} studs" in r.output
        assert _last(r) == DISCLAIMER and not out.exists()
        assert ok.exit_code == 0, ok.output  # the other corners still fit


# --- the layout commands accept a plaque layout and name the tile (US3-2, US3-3) ----------------

@pytest.fixture
def layouts(data, confirmed_winkel, tmp_path):
    out = {}
    for name, extra in (("plain", ()), ("plaque", ("--plaque", "bottom-left"))):
        p = tmp_path / f"{name}.json"
        r = _run("map", "build", "ocean-sst", "--template", "winkel-tripel", *extra, "-o", p, "-q")
        assert r.exit_code == 0, r.output
        out[name] = p
    return out


def _tile_text(tile):
    return f"1 {_label(tile)} (plaque, part {tile.part_id})"


class TestLayoutCommands:
    def test_parts_list(self, layouts, confirmed_winkel, tile):
        r = _run("parts", "list", layouts["plaque"], "--kits", "1")
        assert r.exit_code == 0, r.output
        lines = r.output.splitlines()
        assert lines[0] == (f"Parts list for {layouts['plaque']} (recipe ocean-sst; 10,204 positions and "
                            f"{_tile_text(tile)}; map pieces only)")
        assert (f"Template: winkel-tripel ({confirmed_winkel.title}); margin in 1x1 square tiles (part 3070b) "
                f"and the plaque {_label(tile)} (part {tile.part_id}), which kit 31203 does not have") in lines
        row = next(line for line in lines if line.startswith(_label(tile) + " "))
        assert f"{tile.numbers.bricklink_item_no} / {tile.color.bricklink.name} ({tile.color.bricklink.id})" in row
        assert _last(r) == DISCLAIMER

    def test_parts_list_without_a_plaque_unchanged(self, layouts, confirmed_winkel):
        r = _run("parts", "list", layouts["plain"])
        assert r.exit_code == 0, r.output
        lines = r.output.splitlines()
        assert lines[0] == f"Parts list for {layouts['plain']} (recipe ocean-sst; 10,240 positions; map pieces only)"
        assert (f"Template: winkel-tripel ({confirmed_winkel.title}); margin in 1x1 square tiles (part 3070b), "
                "which kit 31203 does not have") in lines
        assert "6x6" not in r.output and "10202" not in r.output

    def test_parts_export(self, layouts, tile, tmp_path):
        xml, csv = tmp_path / "w.xml", tmp_path / "w.csv"
        r = _run("parts", "export", layouts["plaque"], "--bricklink", xml, "--rebrickable", csv, "--kits", "1")
        assert r.exit_code == 0, r.output
        assert f"<ITEMID>{tile.numbers.bricklink_item_no}</ITEMID>" in xml.read_text()
        assert csv.read_text().splitlines()[-1] == f"{tile.numbers.rebrickable_part_num},{tile.color.rebrickable.id},1"
        assert (f"Plaque tile in the files: {_tile_text(tile)}; BrickLink {tile.numbers.bricklink_item_no} / "
                f"{tile.color.bricklink.name} ({tile.color.bricklink.id}); Rebrickable "
                f"{tile.numbers.rebrickable_part_num} / {tile.color.rebrickable.name} ({tile.color.rebrickable.id})"
                ) in r.output.splitlines()
        assert _last(r) == DISCLAIMER
        plain = _run("parts", "export", layouts["plain"], "--bricklink", tmp_path / "p.xml")
        assert plain.exit_code == 0 and "Plaque" not in plain.output and "6x6" not in plain.output

    def test_parts_estimate(self, layouts, confirmed_winkel, tile):
        r = _run("parts", "estimate", layouts["plaque"], "--prices",
                 PRICE_FIXTURES / "bricklink_price_guide_plaque.json", "--as-of", "2026-12-05")
        assert r.exit_code == 0, r.output
        lines = r.output.splitlines()
        assert lines[0] == (f"Price estimate for {layouts['plaque']} (recipe ocean-sst; 10,204 positions and "
                            f"{_tile_text(tile)}; map pieces only)")
        assert (f"Template: winkel-tripel ({confirmed_winkel.title}); margin in 1x1 square tiles (part 3070b) "
                f"and the plaque {_label(tile)} (part {tile.part_id}), which kit 31203 does not have") in lines
        assert "Incomplete" not in r.output
        assert _last(r) == DISCLAIMER

    def test_parts_estimate_without_the_tile_in_the_snapshot(self, layouts, tile):
        r = _run("parts", "estimate", layouts["plaque"], "--prices",
                 PRICE_FIXTURES / "bricklink_price_guide_3070b.json", "--as-of", "2026-12-05", "--lines")
        assert r.exit_code == 0, r.output
        assert "Incomplete: 1 piece in 1 color could not be priced:" in r.output
        assert f"--lot {tile.part_id}:{tile.color.lego.id}" in r.output
        assert (f"  Hint: fetch the plaque tile with: lego-image-processor parts prices fetch --lot "
                f"{tile.part_id}:{tile.color.lego.id}, plus a --lot for every other lot") in r.output
        assert "--all-colors does not fetch the plaque tile" in r.output
        assert "Hint: fetch every cited color with" not in r.output  # only the plaque tile is missing
        assert any(line.startswith(_label(tile) + " ") for line in r.output.splitlines())

    def test_sheets_build(self, layouts, confirmed_winkel, tile, tmp_path):
        t = confirmed_winkel
        r = _run("sheets", "build", layouts["plaque"], "-o", tmp_path / "s.pdf")
        assert r.exit_code == 0, r.output
        lots = next(line for line in r.output.splitlines() if line.startswith("Lots: "))
        assert lots.endswith(f"; 10,205 pieces, {t.counts['margin'] - 36:,} of them square tiles (part 3070b), "
                             f"{_tile_text(tile)} in section A5")
        assert _last(r) == DISCLAIMER
        plain = _run("sheets", "build", layouts["plain"], "-o", tmp_path / "p.pdf")
        lots = next(line for line in plain.output.splitlines() if line.startswith("Lots: "))
        assert lots.endswith(f"; 10,240 pieces, {t.counts['margin']:,} of them square tiles (part 3070b)")

    def test_sheets_counts(self, layouts, confirmed_winkel, tile, tmp_path):
        r = _run("sheets", "counts", layouts["plaque"])
        assert r.exit_code == 0, r.output
        lines = r.output.splitlines()
        assert f"Plaque: {plaque_text(confirmed_winkel, tile, 'bottom-left')}; counted in section A5" in lines
        row = next(line for line in lines if f"  {_label(tile)}  " in line)
        assert row.startswith("#") and row.endswith("  1")
        a5 = next(line for line in lines if line.startswith("A5 "))
        assert f"#{row.split()[0][1:]}:1" in a5 and a5.endswith(f"total {256 - 36 + 1}")
        assert _last(r) == DISCLAIMER
        out = tmp_path / "c.json"
        assert _run("sheets", "counts", layouts["plaque"], "-o", out).exit_code == 0
        d = json.loads(out.read_text())
        (lot,) = [x for x in d["legend"] if x["part_type"] == "plaque_tile"]
        assert next(s for s in d["sections"] if s["label"] == "A5")["counts"][str(lot["number"])] == 1
        plain = _run("sheets", "counts", layouts["plain"])
        assert "Plaque" not in plain.output and "6x6" not in plain.output

    def test_validate(self, layouts, confirmed_winkel, tile):
        r = _run("validate", layouts["plaque"])
        assert r.exit_code == 0, r.output
        lines = r.output.splitlines()
        assert "  Total positions: 10,204" in lines
        assert (f"  Plaque: {plaque_text(confirmed_winkel, tile, 'bottom-left')} (36 studs without a 1x1 "
                "piece)") in lines
        assert "✓ Plates on land, tiles on ocean and square tiles on the margin" in r.output
        assert _last(r) == DISCLAIMER
        plain = _run("validate", layouts["plain"])
        assert "  Total positions: 10,240" in plain.output.splitlines() and "Plaque" not in plain.output

    def test_validate_names_a_missing_stud(self, layouts, tmp_path):
        d = json.loads(layouts["plaque"].read_text())
        gone = next(p for p in d["positions"] if p["part_type"] == "tile")
        d["positions"].remove(gone)
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps(d), encoding="utf-8")
        r = _run("validate", bad)
        assert r.exit_code == 0, r.output
        assert f"    ({gone['x']}, {gone['y']}): no piece, template winkel-tripel expects tile" in r.output.splitlines()
        assert "None" not in r.output

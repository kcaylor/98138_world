"""Contract tests for `map stickers` (feature 017, T036; FR-001, FR-013, FR-015 - FR-017,
FR-026; contracts/cli.md "map stickers"; research R11, E1).

Maps are built from the dataset fixtures (``fixture_registry``), never downloaded (the socket
guard in tests/conftest.py stays on). Expected plaque IDs are read from ``load_plaque_parts()``,
never assumed equal to the part number.
Not affiliated with or endorsed by The LEGO Group.
"""

import io
import json
import os

import pytest
from click.testing import CliRunner
from pypdf import PdfReader

from lego_image_processor.cli.main import cli
from lego_image_processor.datasets import cache as cache_mod
from lego_image_processor.datasets import cached_path, get_entry
from lego_image_processor.kit.plaque_parts import load_plaque_parts
from lego_image_processor.maps.build import build_map
from lego_image_processor.maps.recipe import bundled_recipes, load_recipe
from lego_image_processor.stickers import (compose, render_sticker_json, render_sticker_pdf,
                                           render_sticker_svgs, sticker_set)
from lego_image_processor.stickers.compose import part_line
from lego_image_processor.stickers.credits import Credit

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
MM = 72 / 25.4

PLAIN = '''format = "1"
id = "plain-map"
title = "Plain map"
[land]
role = "background"
colors = ["lego_white"]
[ocean]
role = "data"
dataset = "etopo2022-surface-10m"
variable = "z"
transform = "negate"
colors = ["lego_medium_azur", "lego_bright_bluish_green", "lego_earth_blue"]
[ocean.classification]
method = "bins"
bounds = [-9000, 200, 4000, 12000]
'''


def last_line(output: str) -> str:
    return output.rstrip("\n").splitlines()[-1]


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def cached(fixture_registry):
    return fixture_registry.place_all()


@pytest.fixture
def recipes(tmp_path):
    """Recipe files in their own directory, apart from the outputs."""
    d = tmp_path / "recipes"
    d.mkdir()

    def write(name: str, text: str = None, data: bytes = None):
        p = d / name
        if data is not None:
            p.write_bytes(data)
        else:
            p.write_text(text, encoding="utf-8")
        return p
    return write


@pytest.fixture
def out_dir(tmp_path):
    d = tmp_path / "out"
    d.mkdir()
    return d


def stickers(runner, *args):
    return runner.invoke(cli, ["map", "stickers", *map(str, args)])


def library_set(recipe_ref, cache_dir):
    return sticker_set(build_map(load_recipe(recipe_ref), cache_dir=cache_dir,
                                 compare_official=False))


# --- options and files ---------------------------------------------------------------------------

class TestOptions:
    def test_help_lists_the_options_and_defaults(self, runner):
        r = runner.invoke(cli, ["map", "stickers", "--help"])
        assert r.exit_code == 0
        for want in ("RECIPE", "-o, --output", "--format [pdf|svg|json]", "--paper [letter|a4]",
                     "--cache-dir"):
            assert want in r.output, want
        assert "--arrangement" not in r.output

    def test_output_is_required(self, runner, cached):
        r = stickers(runner, "ocean-sst")
        assert r.exit_code == 2

    def test_unknown_format_or_paper(self, runner, cached, out_dir):
        assert stickers(runner, "ocean-sst", "-o", out_dir / "s.pdf", "--format", "png").exit_code == 2
        assert stickers(runner, "ocean-sst", "-o", out_dir / "s.pdf", "--paper", "legal").exit_code == 2
        assert list(out_dir.iterdir()) == []

    def test_pdf_is_the_default_on_letter(self, runner, cached, out_dir):
        out = out_dir / "stickers.pdf"
        r = stickers(runner, "ocean-sst", "-o", out)
        assert r.exit_code == 0, r.output
        pdf = out.read_bytes()
        assert pdf.startswith(b"%PDF")
        reader = PdfReader(io.BytesIO(pdf))
        assert len(reader.pages) == 1
        box = reader.pages[0].mediabox
        assert abs(float(box.width) - 215.9 * MM) < 0.01
        assert abs(float(box.height) - 279.4 * MM) < 0.01
        assert pdf == render_sticker_pdf(library_set("ocean-sst", cached.cache_dir), "letter")

    def test_paper_a4(self, runner, cached, out_dir):
        out = out_dir / "stickers-a4.pdf"
        r = stickers(runner, "ocean-sst", "-o", out, "--paper", "a4")
        assert r.exit_code == 0, r.output
        box = PdfReader(io.BytesIO(out.read_bytes())).pages[0].mediabox
        assert abs(float(box.width) - 210.0 * MM) < 0.01
        assert abs(float(box.height) - 297.0 * MM) < 0.01
        assert f"Stickers: {out} (A4, 1 page, " in r.output
        assert "--paper" not in r.output

    def test_svg_creates_the_directory_with_two_files(self, runner, cached, out_dir):
        out = out_dir / "new" / "svg"
        r = stickers(runner, "ocean-sst", "-o", out, "--format", "svg")
        assert r.exit_code == 0, r.output
        assert sorted(p.name for p in out.iterdir()) == ["sticker-large.svg", "sticker-small.svg"]
        want = dict(render_sticker_svgs(library_set("ocean-sst", cached.cache_dir)))
        for name, text in want.items():
            assert (out / name).read_bytes() == text.encode("utf-8")
        assert str(out / "sticker-small.svg") in r.output and str(out / "sticker-large.svg") in r.output

    def test_svg_replaces_only_its_two_names(self, runner, cached, out_dir):
        (out_dir / "sticker-small.svg").write_text("old", encoding="utf-8")
        (out_dir / "notes.txt").write_text("mine", encoding="utf-8")
        r = stickers(runner, "ocean-sst", "-o", out_dir, "--format", "svg")
        assert r.exit_code == 0, r.output
        assert sorted(p.name for p in out_dir.iterdir()) == ["notes.txt", "sticker-large.svg",
                                                            "sticker-small.svg"]
        assert (out_dir / "notes.txt").read_text(encoding="utf-8") == "mine"
        assert (out_dir / "sticker-small.svg").read_text(encoding="utf-8").startswith("<?xml")

    def test_svg_out_a_file_exits_1(self, runner, cached, out_dir):
        out = out_dir / "a-file"
        out.write_text("keep", encoding="utf-8")
        r = stickers(runner, "ocean-sst", "-o", out, "--format", "svg")
        assert r.exit_code == 1, r.output
        assert str(out) in r.output and "Error:" in r.output
        assert last_line(r.output) == DISCLAIMER
        assert out.read_text(encoding="utf-8") == "keep"
        assert sorted(p.name for p in out_dir.iterdir()) == ["a-file"]

    def test_json_writes_the_summary(self, runner, cached, out_dir):
        out = out_dir / "stickers.json"
        r = stickers(runner, "ocean-sst", "-o", out, "--format", "json")
        assert r.exit_code == 0, r.output
        text = out.read_text(encoding="utf-8")
        assert text == render_sticker_json(library_set("ocean-sst", cached.cache_dir))
        data = json.loads(text)
        assert data["format_version"] == "1" and data["template"] == {"id": "kit-31203"}
        assert data["disclaimer"] == DISCLAIMER
        assert str(out) in r.output

    @pytest.mark.parametrize("fmt", ["svg", "json"])
    def test_paper_with_svg_or_json_prints_a_note(self, runner, cached, out_dir, fmt):
        out = out_dir / ("svg" if fmt == "svg" else "s.json")
        r = stickers(runner, "ocean-sst", "-o", out, "--format", fmt, "--paper", "a4")
        assert r.exit_code == 0, r.output
        assert "Note: --paper" in r.output and "PDF" in r.output
        plain = stickers(runner, "ocean-sst", "-o", out, "--format", fmt)
        assert "Note: --paper" not in plain.output

    def test_cache_dir(self, runner, fixture_registry, out_dir):
        fixture_registry.place_all()
        r = stickers(runner, "ocean-sst", "-o", out_dir / "s.pdf", "--cache-dir",
                     fixture_registry.cache_dir)
        assert r.exit_code == 0, r.output

    def test_a_recipe_file(self, runner, cached, recipes, out_dir):
        # a copy of the bundled file, with its approved [sticker] table (T043)
        path = recipes("ocean-sst-copy.toml", data=bundled_recipes()["ocean-sst"].read_bytes())
        r = stickers(runner, path, "-o", out_dir / "s.json", "--format", "json")
        assert r.exit_code == 0, r.output
        data = json.loads((out_dir / "s.json").read_text(encoding="utf-8"))
        assert data["text"]["line_source"] == "sticker table"
        assert "Sticker line: " in r.output and "(sticker table)" in r.output


# --- the text output -----------------------------------------------------------------------------

class TestOutput:
    @pytest.fixture
    def run(self, runner, cached, out_dir):
        out = out_dir / "stickers.pdf"
        r = stickers(runner, "ocean-sst", "-o", out)
        assert r.exit_code == 0, r.output
        return r, out, library_set("ocean-sst", cached.cache_dir)

    def test_lines_in_the_contract_order(self, run):
        r, out, _ = run
        lines = r.output.rstrip("\n").splitlines()
        heads = ["Recipe: ", "Legend values from the build hung as ", "Sticker title: ",
                 "Sticker line: ", "Large sticker: ", "Small sticker: ",
                 "Parts for a standalone plaque", "  Large: ", "  Small: ", "Stickers: ",
                 "Printed colors only approximate the LEGO colors.",
                 "Data citations and licenses:"]
        at = [next(i for i, ln in enumerate(lines) if ln.startswith(h)) for h in heads]
        assert at == sorted(at), list(zip(heads, at))
        assert lines[-1] == DISCLAIMER

    def test_recipe_and_legend_source(self, run):
        r, _, s = run
        recipe = load_recipe("ocean-sst")
        assert (f"Recipe: ocean-sst - {recipe.title} (format {recipe.format}, SHA-256 "
                f"{recipe.sha256})") in r.output
        assert ("Legend values from the build hung as A (default); the stickers are the same "
                "for A, B, C, D and E.") in r.output

    def test_legend_source_from_the_recipe(self, runner, cached, out_dir):
        r = stickers(runner, "ocean-el-nino", "-o", out_dir / "n.pdf")
        assert r.exit_code == 0, r.output
        # the ENSO recipes hang as D since feature 010 (B before)
        assert "hung as D (from the recipe); the stickers are the same for A, B, C, D and E." in r.output

    def test_title_and_line_with_sources(self, run):
        r, _, s = run
        assert f"Sticker title: {s.text.title} ({s.text.title_source})" in r.output
        assert f"Sticker line: {s.text.line} ({s.text.line_source})" in r.output

    def test_sticker_sizes_and_text_sizes(self, run):
        r, _, s = run
        lo, hi = s.large.text_sizes
        groups = ", ".join(f"{g.layer} {len(g.swatches)}" for g in s.legend.groups)
        assert (f"Large sticker: 125.8 x 61.8 mm for a Black tile 8 x 16; {len(s.legend)} "
                f"swatches ({groups}); text {lo:g}-{hi:g} pt") in r.output
        assert "swatches (land 1, ocean 9)" in r.output
        lo, hi = s.small.text_sizes
        assert f"Small sticker: 45.8 x 45.8 mm for a Black tile 6 x 6; text {lo:g}-{hi:g} pt" in r.output

    def test_plaque_parts_with_cited_ids(self, run):
        r, _, _ = run
        lines = r.output.splitlines()
        table = load_plaque_parts()
        head = lines.index("Parts for a standalone plaque (the sticker is printed, not a LEGO part):")
        want = []
        for size in ("large", "small"):
            tile, plate = table.plaques[size].parts
            want += [f"  {size.capitalize()}: {part_line(tile)}", f"         {part_line(plate)}"]
        assert lines[head + 1:head + 5] == want
        for size in ("small", "large"):
            for part in table.plaques[size].parts:
                c, n = part.color, part.numbers
                text = "\n".join(want)
                assert f"LEGO element {c.element_id}" in text
                assert f"design {', '.join(n.lego_design_ids)}" in text
                assert f"BrickLink {n.bricklink_item_no}, {c.bricklink.name} ({c.bricklink.id})" in text
                assert (f"Rebrickable {n.rebrickable_part_num}, {c.rebrickable.name} "
                        f"({c.rebrickable.id})") in text
                assert c.lego.name == "Black" and c.bricklink.id == 11

    def test_files_written(self, run):
        r, out, _ = run
        assert f"Stickers: {out} (Letter, 1 page, {out.stat().st_size:,} bytes)" in r.output

    def test_citations(self, run):
        r, _, s = run
        for c in s.credits:
            line = f"  - {c.dataset} ({c.version}): {c.citation}"
            if c.doi:
                line += f" https://doi.org/{c.doi}"
            assert line in r.output
            assert f"    License: {c.license}" in r.output

    def test_rainfall_citations_and_ice(self, runner, cached, out_dir):
        r = stickers(runner, "rainfall", "-o", out_dir / "r.pdf")
        assert r.exit_code == 0, r.output
        assert "  - gpcp-v23-ltm-1991-2020 (" in r.output
        assert "  - nsidc-cdr-v6-seaice-minimum-1991-2020 (" in r.output


# --- errors (every row of the contract's table) -------------------------------------------------

class TestErrors:
    def test_unknown_recipe(self, runner, out_dir):
        r = stickers(runner, "no-such-recipe", "-o", out_dir / "s.pdf")
        assert r.exit_code == 1, r.output
        assert "Error:" in r.output and last_line(r.output) == DISCLAIMER
        assert list(out_dir.iterdir()) == []

    def test_dataset_not_cached_never_downloads(self, runner, fixture_registry, out_dir,
                                                monkeypatch):
        def boom(*a, **k):
            raise AssertionError("network used")
        monkeypatch.setattr(cache_mod, "_default_opener", boom)
        for fmt, name in (("pdf", "s.pdf"), ("svg", "svg"), ("json", "s.json")):
            r = stickers(runner, "ocean-sst", "-o", out_dir / name, "--format", fmt)
            assert r.exit_code == 3, r.output
            assert "ersst-v5-ltm-1991-2020" in r.output
            assert "dataset fetch ersst-v5-ltm-1991-2020" in r.output
            assert last_line(r.output) == DISCLAIMER
        assert list(out_dir.iterdir()) == []

    def test_checksum_mismatch(self, runner, cached, out_dir):
        path = cached_path(get_entry("ersst-v5-ltm-1991-2020"), cached.cache_dir)
        data = path.read_bytes()
        path.write_bytes(data[:-1] + bytes([data[-1] ^ 0xFF]))
        r = stickers(runner, "ocean-sst", "-o", out_dir / "s.pdf")
        assert r.exit_code == 4, r.output
        assert str(path) in r.output and last_line(r.output) == DISCLAIMER
        assert list(out_dir.iterdir()) == []

    def test_no_sticker_line(self, runner, cached, recipes, out_dir):
        path = recipes("plain.toml", PLAIN)
        r = stickers(runner, path, "-o", out_dir / "s.pdf")
        assert r.exit_code == 1, r.output
        assert "add a [sticker] line" in r.output and last_line(r.output) == DISCLAIMER
        assert list(out_dir.iterdir()) == []

    def test_text_that_does_not_fit(self, runner, cached, recipes, out_dir):
        title = " ".join(["Extraordinarily"] * 40)
        path = recipes("long.toml", PLAIN + f'[sticker]\ntitle = "{title}"\nline = "A short line."\n')
        r = stickers(runner, path, "-o", out_dir / "s.pdf")
        assert r.exit_code == 1, r.output
        assert "sticker: title does not fit at 5 pt" in r.output
        assert "mm available" in r.output and "needs " in r.output
        assert last_line(r.output) == DISCLAIMER
        assert list(out_dir.iterdir()) == []

    @pytest.mark.parametrize("paper,label", [("letter", "Letter"), ("a4", "A4")])
    def test_a_print_sheet_block_that_does_not_fit(self, runner, cached, out_dir, monkeypatch,
                                                   paper, label):
        huge = Credit(dataset="huge", version="1", text="Huge, Somebody", title="Huge",
                      doi=None, publisher="Somebody", citation=" ".join(["citation"] * 3000),
                      license="CC0")
        original = compose.credits_for
        monkeypatch.setattr(compose, "credits_for", lambda recipe, *a, **k: original(recipe) + (huge,))
        r = stickers(runner, "ocean-sst", "-o", out_dir / "s.pdf", "--paper", paper)
        assert r.exit_code == 1, r.output
        assert f"print sheet ({label})" in r.output and "data block does not fit" in r.output
        assert last_line(r.output) == DISCLAIMER
        assert list(out_dir.iterdir()) == []

    def test_pdf_with_text_outside_latin1(self, runner, cached, recipes, out_dir):
        path = recipes("arrow.toml", PLAIN + '[sticker]\nline = "Depth classes → three colors."\n')
        r = stickers(runner, path, "-o", out_dir / "s.pdf")
        assert r.exit_code == 1, r.output
        assert "line" in r.output and "use --format svg" in r.output
        assert last_line(r.output) == DISCLAIMER
        assert list(out_dir.iterdir()) == []
        svg = stickers(runner, path, "-o", out_dir / "svg", "--format", "svg")
        assert svg.exit_code == 0, svg.output
        assert "→" in (out_dir / "svg" / "sticker-large.svg").read_text(encoding="utf-8")

    @pytest.mark.parametrize("fmt", ["pdf", "json"])
    def test_cannot_write(self, runner, cached, out_dir, fmt):
        out = out_dir / "missing" / f"s.{fmt}"
        r = stickers(runner, "ocean-sst", "-o", out, "--format", fmt)
        assert r.exit_code == 1, r.output
        assert "Cannot write output" in r.output and last_line(r.output) == DISCLAIMER
        assert list(out_dir.iterdir()) == []

    def test_cannot_write_svg(self, runner, cached, out_dir):
        blocker = out_dir / "file"
        blocker.write_text("x", encoding="utf-8")
        r = stickers(runner, "ocean-sst", "-o", blocker / "svg", "--format", "svg")
        assert r.exit_code == 1, r.output
        assert "Cannot write output" in r.output and last_line(r.output) == DISCLAIMER


# --- FR-017: nothing but the stickers is written ------------------------------------------------

class TestWritesOnlyTheStickers:
    @pytest.mark.parametrize("fmt,name", [("pdf", "stickers.pdf"), ("json", "stickers.json"),
                                          ("svg", "svg")])
    def test_only_out(self, runner, cached, tmp_path, fmt, name):
        work = tmp_path / "work"
        work.mkdir()
        before = sorted(p.relative_to(cached.cache_dir) for p in cached.cache_dir.rglob("*"))
        cwd = os.getcwd()
        os.chdir(work)
        try:
            r = stickers(runner, "ocean-sst", "-o", name, "--format", fmt)
        finally:
            os.chdir(cwd)
        assert r.exit_code == 0, r.output
        assert [p.name for p in work.iterdir()] == [name]
        if fmt == "svg":
            assert sorted(p.name for p in (work / name).iterdir()) == ["sticker-large.svg",
                                                                       "sticker-small.svg"]
        after = sorted(p.relative_to(cached.cache_dir) for p in cached.cache_dir.rglob("*"))
        assert after == before
        for word in ("Layout:", "Preview:", "Report:", "Cells:", "Sheets:"):
            assert word not in r.output


# --- on a template (feature 016; T057: contracts/cli.md "--template", FR-001, FR-025) ----------

class TestTemplate:
    """``map stickers --template`` (016's ``TemplateType``) and the recipe ``template`` key, on
    016's ``confirmed_winkel``; texts and counts from the loaded template."""

    @staticmethod
    def winkel_set(cache_dir, recipe_ref="ocean-sst", template="winkel-tripel"):
        return sticker_set(build_map(load_recipe(recipe_ref), cache_dir=cache_dir,
                                     compare_official=False, template=template))

    @staticmethod
    def recipe_file(recipes, rid, top_line):
        text = bundled_recipes()[rid].read_text(encoding="utf-8")
        assert "seed = 31203\n" in text
        return recipes(f"{rid}-template.toml", text.replace("seed = 31203\n",
                                                            f"seed = 31203\n{top_line}\n", 1))

    def test_help_lists_template(self, runner):
        r = runner.invoke(cli, ["map", "stickers", "--help"])
        assert r.exit_code == 0 and "--template ID" in r.output
        for opt in ("--margin-color", "--ring-color", "--arrangement"):
            assert opt not in r.output

    @pytest.mark.parametrize("fmt,name", [("pdf", "w.pdf"), ("json", "w.json"), ("svg", "w-svg")])
    def test_files_are_the_template_set(self, runner, cached, confirmed_winkel, out_dir, fmt, name):
        out = out_dir / name
        r = stickers(runner, "ocean-sst", "--template", "winkel-tripel", "-o", out, "--format", fmt)
        assert r.exit_code == 0, r.output
        s = self.winkel_set(cached.cache_dir)
        if fmt == "pdf":
            assert out.read_bytes() == render_sticker_pdf(s, "letter")
        elif fmt == "json":
            assert out.read_text(encoding="utf-8") == render_sticker_json(s)
            t = confirmed_winkel
            assert json.loads(out.read_text(encoding="utf-8"))["template"] == {
                "id": t.id, "title": t.title, "projection": t.projection_title, "dataset": t.dataset.id}
        else:
            for n, text in render_sticker_svgs(s):
                assert (out / n).read_text(encoding="utf-8") == text
        assert s.text.line.endswith(" Winkel tripel projection.")

    def test_template_and_margin_lines_after_the_recipe_line(self, runner, cached, confirmed_winkel,
                                                             out_dir):
        t = confirmed_winkel
        r = stickers(runner, "ocean-sst", "--template", "winkel-tripel", "-o", out_dir / "w.pdf")
        assert r.exit_code == 0, r.output
        lines = r.output.rstrip("\n").splitlines()
        i = next(n for n, ln in enumerate(lines) if ln.startswith("Recipe: ocean-sst - "))
        assert lines[i + 1] == f"Template: winkel-tripel ({t.title}) - from --template"
        c = t.counts
        assert lines[i + 2] == (f"Margin: {c['margin']:,} square tiles (part 3070b): lego_black; "
                                "no ring")
        assert lines[i + 3] == ("Legend values from the build hung as A (default); the frames of "
                                "a curved map cannot be re-hung.")
        s = self.winkel_set(cached.cache_dir)
        assert f"Sticker line: {s.text.line} (sticker table)" in lines
        heads = ["Recipe: ", "Template: ", "Margin: ", "Legend values from the build hung as ",
                 "Sticker title: ", "Sticker line: ", "Large sticker: ", "Small sticker: ",
                 "Parts for a standalone plaque", "Stickers: ", "Data citations and licenses:"]
        at = [next(n for n, ln in enumerate(lines) if ln.startswith(h)) for h in heads]
        assert at == sorted(at), list(zip(heads, at))
        assert lines[-1] == DISCLAIMER

    def test_template_dataset_cited(self, runner, cached, confirmed_winkel, out_dir):
        r = stickers(runner, "ocean-sst", "--template", "winkel-tripel", "-o", out_dir / "w.pdf")
        assert r.exit_code == 0, r.output
        e = get_entry(confirmed_winkel.dataset.id)
        assert r.output.count(f"  - {e.id} ({e.version}): ") == 1
        assert "  - ersst-v5-ltm-1991-2020 (" in r.output

    def test_recipe_template_key(self, runner, cached, confirmed_winkel, recipes, out_dir):
        path = self.recipe_file(recipes, "ocean-sst", 'template = "winkel-tripel"')
        r = stickers(runner, path, "-o", out_dir / "w.json", "--format", "json")
        assert r.exit_code == 0, r.output
        assert f"Template: winkel-tripel ({confirmed_winkel.title}) - from the recipe" in r.output
        data = json.loads((out_dir / "w.json").read_text(encoding="utf-8"))
        assert data["template"]["id"] == "winkel-tripel"
        assert data["text"]["line"].endswith(" Winkel tripel projection.")

    def test_option_wins_over_the_recipe(self, runner, cached, confirmed_winkel, recipes, out_dir):
        path = self.recipe_file(recipes, "ocean-sst", 'template = "winkel-tripel"')
        r = stickers(runner, path, "--template", "kit-31203", "-o", out_dir / "k.json",
                     "--format", "json")
        assert r.exit_code == 0, r.output
        assert "Template:" not in r.output
        assert json.loads((out_dir / "k.json").read_text(encoding="utf-8"))["template"] == {
            "id": "kit-31203"}

    def test_explicit_kit_template_prints_and_writes_as_today(self, runner, cached, out_dir):
        plain = stickers(runner, "ocean-sst", "-o", out_dir / "a.pdf")
        kit = stickers(runner, "ocean-sst", "--template", "kit-31203", "-o", out_dir / "b.pdf")
        assert plain.exit_code == kit.exit_code == 0, kit.output
        assert (out_dir / "a.pdf").read_bytes() == (out_dir / "b.pdf").read_bytes()
        assert plain.output.replace("a.pdf", "b.pdf") == kit.output
        assert "Template:" not in kit.output and "Margin:" not in kit.output
        assert ("the stickers are the same for A, B, C, D and E." in kit.output)

    def test_unknown_template_exit_2(self, runner, cached, confirmed_winkel, out_dir):
        r = stickers(runner, "ocean-sst", "--template", "mercator", "-o", out_dir / "x.pdf")
        assert r.exit_code == 2
        assert "'mercator'" in r.output and "confirmed templates: kit-31203, winkel-tripel" in r.output
        assert list(out_dir.iterdir()) == []

    def test_unknown_recipe_template_exit_1(self, runner, cached, recipes, out_dir):
        path = self.recipe_file(recipes, "ocean-sst", 'template = "mercator"')
        r = stickers(runner, path, "-o", out_dir / "x.pdf")
        assert r.exit_code == 1
        assert "template: unknown template 'mercator'" in r.output
        assert "confirmed templates: kit-31203" in r.output
        assert last_line(r.output) == DISCLAIMER and list(out_dir.iterdir()) == []

    @pytest.mark.parametrize("recipe_ref,want", [
        ("official-31203", "kit31203-design"),
        ("ocean-el-nino", "the frames of a curved map cannot be re-hung"),
    ])
    def test_map_that_cannot_build_on_the_template(self, runner, cached, confirmed_winkel, out_dir,
                                                   recipe_ref, want):
        r = stickers(runner, recipe_ref, "--template", "winkel-tripel", "-o", out_dir / "x.pdf")
        assert r.exit_code == 1
        assert f"Cannot build {recipe_ref}: " in r.output and want in r.output
        assert last_line(r.output) == DISCLAIMER and list(out_dir.iterdir()) == []

    def test_unconfirmed_template_exit_1(self, runner, cached, unconfirmed_winkel, out_dir):
        r = stickers(runner, "ocean-sst", "--template", "winkel-tripel", "-o", out_dir / "x.pdf")
        assert r.exit_code == 1
        assert "not confirmed by the project owner" in r.output
        assert last_line(r.output) == DISCLAIMER and list(out_dir.iterdir()) == []

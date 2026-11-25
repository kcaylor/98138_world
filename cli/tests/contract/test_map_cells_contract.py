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


# --- Feature 016 (T079): `map cells` on a template (contracts/cli.md; FR-020a) ----------------

class TestTemplateOptions:
    def test_help_lists_the_template_options(self):
        r = CliRunner().invoke(cli, ["map", "cells", "--help"])
        assert r.exit_code == 0
        for opt in ("--template", "--margin-color", "--ring-color"):
            assert opt in r.output

    def test_winkel_cells(self, tmp_path, fixture_registry, confirmed_winkel):
        fixture_registry.place_all()
        t = confirmed_winkel
        out = tmp_path / "w.json"
        r = CliRunner().invoke(cli, ["map", "cells", "ocean-sst", "--template", "winkel-tripel", "-o", str(out)])
        assert r.exit_code == 0, r.output
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["cells"].count("M") == t.counts["margin"]
        assert data["template"]["id"] == "winkel-tripel"
        assert data["margin"] == {"part_id": "3070b", "color": "lego_black", "ring": None}
        assert list(data["palette"]) == ["6141", "98138", "3070b"]
        lines = r.output.splitlines()
        assert f"Template: winkel-tripel ({t.title}) - from --template" in lines
        assert f"Margin: {t.counts['margin']:,} square tiles (part 3070b): lego_black; no ring" in lines
        ice = next(line for line in lines if line.startswith("Ice regions:"))
        assert ice == (f"Ice regions: {len(data['ice']['land']):,} land-ice cells, "
                       f"{len(data['ice']['sea']):,} sea-ice cells (winkel-tripel-ice.json)")
        assert "Preview only" in r.output and r.output.rstrip("\n").splitlines()[-1] == DISCLAIMER

    def test_margin_and_ring_colors(self, tmp_path, fixture_registry, confirmed_winkel):
        fixture_registry.place_all()
        out = tmp_path / "w.json"
        r = CliRunner().invoke(cli, ["map", "cells", "ocean-sst", "--template", "winkel-tripel", "-o", str(out),
                                     "--margin-color", "lego_white", "--ring-color", "lego_bright_yellow"])
        assert r.exit_code == 0, r.output
        m = json.loads(out.read_text(encoding="utf-8"))["margin"]
        assert m["color"] == "lego_white" and m["ring"]["color"] == "lego_bright_yellow"
        assert len(m["ring"]["cells"]) == confirmed_winkel.counts["ring"]

    def test_bad_margin_color(self, tmp_path, fixture_registry, confirmed_winkel):
        fixture_registry.place_all()
        out = tmp_path / "w.json"
        r = CliRunner().invoke(cli, ["map", "cells", "ocean-sst", "--template", "winkel-tripel", "-o", str(out),
                                     "--margin-color", "lego_nope"])
        assert r.exit_code == 1
        assert "--margin-color" in r.output and "kit part-colors --part 3070b" in r.output
        assert r.output.rstrip("\n").splitlines()[-1] == DISCLAIMER
        assert not out.exists()

    def test_unknown_template(self, tmp_path):
        r = CliRunner().invoke(cli, ["map", "cells", "ocean-sst", "--template", "mollweide",
                                     "-o", str(tmp_path / "c.json")])
        assert r.exit_code == 2

    def test_unconfirmed_template(self, tmp_path, fixture_registry, synthetic_template):
        import lego_image_processor.templates as templates
        from maptemplates import document

        fixture_registry.place_all()
        path = templates.TEMPLATE_DIR / "winkel-tripel.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["confirmation"] = None
        path.write_text(document.to_text(doc), encoding="utf-8")
        r = CliRunner().invoke(cli, ["map", "cells", "ocean-sst", "--template", "winkel-tripel",
                                     "-o", str(tmp_path / "c.json")])
        assert r.exit_code == 1
        assert "not confirmed by the project owner" in r.output
        assert r.output.rstrip("\n").splitlines()[-1] == DISCLAIMER

    def test_missing_ice_file(self, tmp_path, fixture_registry, synthetic_template):
        import lego_image_processor.templates as templates

        fixture_registry.place_all()
        (templates.TEMPLATE_DIR / "winkel-tripel-ice.json").unlink()
        out = tmp_path / "c.json"
        r = CliRunner().invoke(cli, ["map", "cells", "ocean-sst", "--template", "winkel-tripel", "-o", str(out)])
        assert r.exit_code == 1
        assert "winkel-tripel-ice.json" in r.output and "ice-mask winkel-tripel" in r.output
        assert r.output.rstrip("\n").splitlines()[-1] == DISCLAIMER
        assert not out.exists()

    def test_kit_with_margin_options_prints_the_note(self, tmp_path):
        out = tmp_path / "c.json"
        plain = tmp_path / "plain.json"
        r = CliRunner().invoke(cli, ["map", "cells", "official-31203", "-o", str(out),
                                     "--margin-color", "lego_white"])
        assert r.exit_code == 0, r.output
        assert "margin settings are not used on the kit template" in r.output
        assert CliRunner().invoke(cli, ["map", "cells", "official-31203", "-o", str(plain)]).exit_code == 0
        assert out.read_bytes() == plain.read_bytes()
        assert "template" not in json.loads(out.read_text(encoding="utf-8"))


# --- Feature 017 (T076): `map cells ... --plaque` (contracts/in-margin-plaque.md "cells.json") ------

class TestPlaque:
    def test_plaque_cells(self, tmp_path, fixture_registry, confirmed_winkel):
        from lego_image_processor.kit.plaque_parts import load_plaque_parts
        from lego_image_processor.maps.margin import place_plaque

        fixture_registry.place_all()
        t = confirmed_winkel
        tile = load_plaque_parts().plaques["small"].tile
        out = tmp_path / "p.json"
        r = CliRunner().invoke(cli, ["map", "cells", "ocean-sst", "--template", "winkel-tripel",
                                     "--plaque", "bottom-left", "-o", str(out)])
        assert r.exit_code == 0, r.output
        data = json.loads(out.read_text(encoding="utf-8"))
        studs = place_plaque(t, "bottom-left").studs
        cells = sorted(y * 128 + x for y in range(studs["row"], studs["row"] + studs["height"])
                       for x in range(studs["col"], studs["col"] + studs["width"]))
        assert data["plaque"] == {"part_id": tile.part_id, "color": tile.color.key,
                                  "rgb": list(tile.color.rgb), "corner": "bottom-left", "cells": cells}
        assert data["cells"].count("P") == 36 and data["cells"].count("M") == t.counts["margin"] - 36
        assert all(data["cells"][i] == "P" for i in cells)
        lines = r.output.splitlines()
        margin = lines.index(f"Margin: {t.counts['margin'] - 36:,} square tiles (part 3070b): lego_black; no ring")
        w, h = tile.studs
        assert lines[margin + 1] == (
            f"Plaque: tile {w}x{h} (part {tile.part_id}), {tile.color.lego.name}, bottom-left, rows "
            f"{studs['row']}-{studs['row'] + h - 1}, columns {studs['col']}-{studs['col'] + w - 1} - from --plaque")
        assert r.output.rstrip("\n").splitlines()[-1] == DISCLAIMER

    def test_without_a_plaque(self, tmp_path, fixture_registry, confirmed_winkel):
        fixture_registry.place_all()
        out = tmp_path / "w.json"
        r = CliRunner().invoke(cli, ["map", "cells", "ocean-sst", "--template", "winkel-tripel", "-o", str(out)])
        assert r.exit_code == 0, r.output
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "plaque" not in data and "P" not in data["cells"]
        assert "Plaque" not in r.output

"""Template variants in the build step (feature 016, US3; FR-019, SC-006; contracts/web.md).

The session builds on a confirmed ``winkel-tripel`` (conftest ``confirmed_template_dir``, T084), so
the small site has one template variant, ocean-sst on Winkel tripel; official-31203 (LEGO's design
on the kit grid) and ocean-el-nino (hung B) have none. Not affiliated with or endorsed by The LEGO
Group.
"""

from __future__ import annotations

import hashlib
import json

import pytest

import kit_golden
from conftest import PRICES, TODAY

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
TID = "winkel-tripel"
ELIGIBLE = ("official-31203-bathymetry", "ocean-sst", "land-elevation", "living-planet", "rainfall")
KIT_LABELS = {"6141": "plate 1x1 round", "98138": "tile 1x1 round"}
KINDS_ALWAYS = {"layout", "parts", "parts-1kit", "bricklink", "rebrickable", "sheets-letter",
                "sheets-a4", "preview", "thumb", "cells"}


@pytest.fixture(scope="module")
def template():
    from lego_image_processor.templates import load_template

    return load_template(TID)


def _row(manifest, map_id):
    return next(m for m in manifest["maps"] if m["id"] == map_id)


def _golden_part_labels(site="small"):
    doc = json.loads(kit_golden.GOLDEN_PATH.read_text(encoding="utf-8"))
    return next(s for s in doc["sites"] if s["site"] == site)["part_labels"]


# --- manifest ------------------------------------------------------------------------------

def test_templates_list(manifest, template):
    assert [t["id"] for t in manifest["templates"]] == [TID]
    t = manifest["templates"][0]
    assert list(t) == ["id", "title", "projection", "board", "counts", "rehang", "description", "source"]
    assert t["title"] == template.title and t["description"] == template.description
    assert t["projection"] == "Winkel tripel" == template.projection_title   # the library's (017)
    assert t["board"] == {"modules": [8, 5], "width": 128, "height": 80}
    assert t["counts"] == {k: template.counts[k] for k in ("land", "ocean", "margin", "ring")}
    assert t["rehang"] is False
    assert t["source"] == {"sha256": template.file_sha256,
                           "confirmation": template.confirmation.to_dict()}
    assert t["source"]["confirmation"]["role"] == "project owner"


def test_template_variants_only_for_eligible_maps(manifest):
    for m in manifest["maps"]:
        assert set(m["variants"]) == {"A", "B", "C", "D", "E"}   # kit variants stay exactly A-E (010)
    assert set(_row(manifest, "ocean-sst")["template_variants"]) == {TID}
    assert "template_variants" not in _row(manifest, "official-31203")
    assert "template_variants" not in _row(manifest, "ocean-el-nino")


def test_template_variant_files(site_dir, manifest):
    v = _row(manifest, "ocean-sst")["template_variants"][TID]
    assert v["template"] == TID
    assert KINDS_ALWAYS <= set(v["files"])
    from web98138.prebuild import KINDS

    kit = _row(manifest, "ocean-sst")["variants"]["A"]
    assert set(kit["files"]) <= set(v["files"]) == set(KINDS)   # the kit variant's kinds, and the
    assert v["nothing_to_buy_with_kit"] is False                 # top-up: one kit has no 3070b
    for kind, f in v["files"].items():
        data = (site_dir / f["path"]).read_bytes()
        assert f["path"].startswith(f"maps/ocean-sst/{TID}/")
        assert len(data) == f["bytes"] and hashlib.sha256(data).hexdigest() == f["sha256"]
        stem, ext = f["path"].rsplit("/", 1)[1].rsplit(".", 1)
        assert f["filename"] == f"98138-world_ocean-sst_{TID}_{stem}.{ext}"
        assert f["media_type"] == KINDS[kind][1]


def test_template_variant_is_the_library_build(site_dir, manifest, template):
    v = _row(manifest, "ocean-sst")["template_variants"][TID]
    layout = json.loads((site_dir / v["files"]["layout"]["path"]).read_text(encoding="utf-8"))
    md = layout["metadata"]
    assert md["template"]["id"] == TID and md["margin_positions"] == template.counts["margin"]
    assert md["template"]["source"]["sha256"] == template.file_sha256
    s = v["summary"]
    assert s["pieces"] == 10240
    square = [lot for lot in v["lots"] if lot["part_id"] == "3070b"]
    assert len(square) == 1 and square[0]["needed"] == template.counts["margin"]
    assert square[0]["kit_supply"] == 0 and square[0]["part_type"] == "square_tile"
    assert {r["part_id"] for r in v["leftovers"]} == {"6141", "98138"}   # kit elements only
    assert v["margin"]["part_id"] == "3070b" and v["margin"]["color"] == "lego_black"
    assert v["margin"]["cells"]["margin"] == template.counts["margin"]
    cells = json.loads((site_dir / v["files"]["cells"]["path"]).read_text(encoding="utf-8"))
    assert cells["template"]["id"] == TID and cells["cells"].count("M") == template.counts["margin"]
    assert cells["disclaimer"] == DISCLAIMER


def test_template_variant_layers_and_citations_from_its_report(manifest, template):
    v = _row(manifest, "ocean-sst")["template_variants"][TID]
    land = next(layer for layer in v["layers"] if layer["class"] == "land")
    assert land["cells"] == template.counts["land"]
    ids = [c["id"] for c in v["citations"]]
    assert ids[-1] == template.dataset.id == "etopo2022-surface-10m"    # the template's dataset
    assert ids[:-1] == [c["id"] for c in _row(manifest, "ocean-sst")["citations"]]


def test_template_default_rendering_equals_layout(site_dir, manifest):
    v = _row(manifest, "ocean-sst")["template_variants"][TID]
    cells = json.loads((site_dir / v["files"]["cells"]["path"]).read_text(encoding="utf-8"))
    layout = json.loads((site_dir / v["files"]["layout"]["path"]).read_text(encoding="utf-8"))
    want = {(p["x"], p["y"]): p["color_id"] for p in layout["positions"]}
    ring = set((cells["margin"]["ring"] or {}).get("cells", ()))
    W = cells["width"]
    for i, k in enumerate(cells["cells"]):
        if k == "M":
            got = cells["margin"]["ring"]["color"] if i in ring else cells["margin"]["color"]
        elif k == "S":
            got = cells["shadow"]["color"]
        else:
            layer = cells["layers"]["land" if k == "L" else "ocean"]
            got = layer["colors"][layer["classes"][i]]
        assert got == want[(i % W, i // W)], i


def test_part_labels_add_the_square_tile(manifest):
    assert manifest["part_labels"] == {**KIT_LABELS, "3070b": "tile 1x1 square"}


def test_winkel_estimate_incomplete_with_the_fixture_snapshot(manifest, template):
    """The fixture snapshot has no 3070b rows: the square tiles are unpriced (T109 is the owner's)."""
    v = _row(manifest, "ocean-sst")["template_variants"][TID]
    for kind in ("full", "one_kit"):
        e = v["estimates"][kind]
        assert e["complete"] is False
        assert e["unpriced"] == {"lots": 1, "pieces": template.counts["margin"]}
    kit = _row(manifest, "ocean-sst")["variants"]["A"]["estimates"]["full"]
    assert kit["complete"] is True


def test_counts_and_total_include_template_variants(manifest):
    files = [f for m in manifest["maps"]
             for v in list(m["variants"].values()) + list(m.get("template_variants", {}).values())
             for f in v["files"].values()]
    files += [f for m in manifest["maps"] for st in m.get("stickers", {}).values()   # feature 017
              for f in st["files"].values()]
    assert manifest["total_bytes"] == sum(f["bytes"] for f in files)


# --- eligibility (US3-1, SC-006) ------------------------------------------------------------

def test_eligibility_is_exactly_the_five_maps(template):
    from lego_image_processor.maps.recipe import load_recipe
    from lego_image_processor.templates import compatibility

    from web98138 import MAP_IDS, TEMPLATES
    from web98138.prebuild import template_reason

    assert TID in TEMPLATES and isinstance(TEMPLATES, tuple)   # ids only; names from the library
    ok = [m for m in MAP_IDS if compatibility(load_recipe(m), template) is None]
    assert tuple(ok) == ELIGIBLE
    for m in MAP_IDS:   # the prebuild asks the library, nothing else
        assert template_reason(load_recipe(m), template) == compatibility(load_recipe(m), template)


# --- options ---------------------------------------------------------------------------------

def _build(tmp_path, fixture_datasets, name, **kw):
    from web98138.prebuild import build_site

    lines = []
    m = build_site(tmp_path / name, maps=["ocean-sst"], combinations=["A"], cache_dir=fixture_datasets,
                   echo=lines.append, prices_path=PRICES, today=TODAY, **kw)
    return m, "\n".join(map(str, lines))


def test_templates_none_builds_kit_variants_only(tmp_path, fixture_datasets):
    m, text = _build(tmp_path, fixture_datasets, "none", templates=[])
    assert "templates" not in m
    assert "template_variants" not in m["maps"][0]
    assert m["part_labels"] == _golden_part_labels() == KIT_LABELS
    assert not (tmp_path / "none" / "maps" / "ocean-sst" / TID).exists()
    assert "Built 1 variants" in text


def test_named_template_builds_its_variant(tmp_path, fixture_datasets):
    m, text = _build(tmp_path, fixture_datasets, "w", templates=[TID])
    assert set(m["maps"][0]["template_variants"]) == {TID}
    assert f"ocean-sst {TID}:" in text and "Built 2 variants" in text
    assert text.rstrip().endswith(DISCLAIMER)


def test_unconfirmed_template_gives_no_variants(tmp_path, fixture_datasets, unconfirmed_template_dir):
    from maptemplates.testing import use_template_dir

    with use_template_dir(unconfirmed_template_dir):
        m, text = _build(tmp_path, fixture_datasets, "default")          # default: confirmed only
        m2, text2 = _build(tmp_path, fixture_datasets, "named", templates=[TID])
    for mm, t in ((m, text), (m2, text2)):
        assert "templates" not in mm and "template_variants" not in mm["maps"][0]
        assert mm["part_labels"] == KIT_LABELS
        assert f"{TID}: not confirmed by the project owner" in t
        assert "no template variants" in t


def test_ineligible_map_is_skipped_with_the_reason(tmp_path, fixture_datasets):
    from web98138.prebuild import build_site

    lines = []
    m = build_site(tmp_path / "o", maps=["official-31203"], combinations=["A"],
                   cache_dir=fixture_datasets, echo=lines.append, prices_path=PRICES, today=TODAY)
    assert "templates" not in m and "template_variants" not in m["maps"][0]
    text = "\n".join(lines)
    assert f"official-31203 {TID}: skipped" in text and "kit31203-design" in text


def test_cli_templates_option(tmp_path, fixture_datasets, capsys):
    from web98138.prebuild import main

    base = ["--maps", "ocean-sst", "--combinations", "A", "--cache-dir", str(fixture_datasets),
            "--prices", str(PRICES), "-q"]
    assert main(["--out", str(tmp_path / "n"), "--templates", "none"] + base) == 0
    assert "templates" not in json.loads((tmp_path / "n" / "manifest.json").read_text())
    assert main(["--out", str(tmp_path / "w"), "--templates", TID] + base) == 0
    m = json.loads((tmp_path / "w" / "manifest.json").read_text())
    assert [t["id"] for t in m["templates"]] == [TID]
    capsys.readouterr()
    for bad in ("nope", "kit-31203", f"{TID},none", ""):
        assert main(["--out", str(tmp_path / "x"), "--templates", bad] + base) == 2, bad
        err = capsys.readouterr().err
        assert "template" in err and DISCLAIMER in err

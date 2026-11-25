"""The build step (FR-014-FR-016, FR-006, FR-011, FR-013)."""

from __future__ import annotations

import hashlib
import json

import pytest
from PIL import Image

from conftest import SMALL_MAPS

KINDS_ALWAYS = {"layout", "parts", "parts-1kit", "bricklink", "rebrickable", "sheets-letter",
                "sheets-a4", "preview", "thumb"}


def test_manifest_top_level(manifest):
    assert manifest["format_version"] == "1"
    assert manifest["disclaimer"] == "Not affiliated with or endorsed by The LEGO Group."
    tools = manifest["tools"]
    assert tools["lego_image_processor"] and tools["web98138"] and tools["python"].startswith("3.11")
    assert "git_commit" in tools
    assert manifest["generated_at"].endswith("Z")
    assert [a["id"] for a in manifest["arrangements"]] == ["A", "B", "C", "D", "E"]  # feature 010
    b = manifest["arrangements"][1]
    assert b["frame_order"] == [3, 1, 2] and b["centre"] == "America"
    assert manifest["arrangement_source"]["pages"] == [7, 8]
    assert "Rebrickable" in manifest["acknowledgement"]
    assert [m["id"] for m in manifest["maps"]] == list(SMALL_MAPS)


def test_every_variant_has_files_matching_checksums(site_dir, manifest):
    for m in manifest["maps"]:
        assert set(m["variants"]) == {"A", "B", "C", "D", "E"}
        for c, v in m["variants"].items():
            assert KINDS_ALWAYS <= set(v["files"])
            for kind, f in v["files"].items():
                p = site_dir / f["path"]
                data = p.read_bytes()
                assert len(data) == f["bytes"]
                assert hashlib.sha256(data).hexdigest() == f["sha256"]
                assert f["path"] == f"maps/{m['id']}/{c}/{p.name}"
                if kind not in ("preview", "thumb"):
                    assert f["filename"].startswith(f"98138-world_{m['id']}_{c}_")


def test_preview_sizes(site_dir, manifest):
    v = manifest["maps"][0]["variants"]["A"]
    assert Image.open(site_dir / v["files"]["preview"]["path"]).size == (1280, 800)
    assert Image.open(site_dir / v["files"]["thumb"]["path"]).size == (384, 240)


def test_official_design_layout_is_the_library_build(site_dir, manifest):
    """The layout file is what `map build official-31203 --arrangement B` writes."""
    from lego_image_processor.layout.arrangement import parse_arrangement
    from lego_image_processor.maps.build import build_map
    from lego_image_processor.maps.recipe import load_recipe

    v = manifest["maps"][0]["variants"]["B"]
    ours = json.loads((site_dir / v["files"]["layout"]["path"]).read_text())
    lib = json.loads(build_map(load_recipe("official-31203"),
                               arrangement=parse_arrangement("B")).layout.to_json())
    assert ours["positions"] == lib["positions"]
    assert ours["metadata"]["arrangement"]["id"] == "B"


def test_summary_from_parts_lists(manifest):
    off = manifest["maps"][0]
    s = off["variants"]["A"]["summary"]
    assert s == {"lots": 10, "pieces": 10240, "one_kit_covers": 10240, "to_buy_with_kit": 0,
                 "lots_to_buy_with_kit": 0, "unverified_lots": 0}
    lot = off["variants"]["A"]["lots"][0]
    assert {"lego", "bricklink", "rebrickable", "needed", "kit_supply", "to_buy", "rgb"} <= set(lot)


def test_nothing_to_buy_has_no_topup_export(manifest):
    v = manifest["maps"][0]["variants"]["A"]   # one kit builds the official design
    assert "bricklink-1kit" not in v["files"] and "rebrickable-1kit" not in v["files"]
    assert v["nothing_to_buy_with_kit"] is True


def test_map_page_data(manifest):
    off, sst, nino = manifest["maps"]
    assert off["default_combination"] == "A" and nino["default_combination"] == "D"  # feature 010
    assert off["title"] and off["description"]
    assert off["datasets"] == [] and off["citations"]          # kit design source
    assert [l["class"] for l in sst["layers"]] == ["land", "ocean"]
    assert sst["layers"][1]["role"] == "data"
    assert sst["datasets"][0]["id"] == "ersst-v5-ltm-1991-2020"
    assert sst["datasets"][0]["sha256"]
    cit = sst["citations"][0]
    assert cit["license"] and cit["citation"]
    assert isinstance(sst["variants"]["A"]["warnings"], list)
    assert sst["recipe"]["sha256"]


def test_missing_dataset_without_fetch_is_an_error(tmp_path, fixture_datasets):
    from web98138.prebuild import PrebuildError, build_site

    with pytest.raises(PrebuildError, match="--fetch"):
        build_site(tmp_path / "out", maps=["ocean-sst"], combinations=["A"],
                   cache_dir=tmp_path / "empty-cache", echo=lambda *a: None)


def test_cli_usage_errors(tmp_path, capsys):
    from web98138.prebuild import main

    assert main(["--out", str(tmp_path / "o"), "--maps", "nope"]) == 2
    assert main(["--out", str(tmp_path / "o"), "--combinations", "F"]) == 2
    assert "Not affiliated" in capsys.readouterr().err


def test_cli_builds_subset(tmp_path, fixture_datasets, capsys):
    from web98138.prebuild import main

    out = tmp_path / "o"
    assert main(["--out", str(out), "--maps", "official-31203", "--combinations", "a,C",
                 "--cache-dir", str(fixture_datasets)]) == 0
    m = json.loads((out / "manifest.json").read_text())
    assert set(m["maps"][0]["variants"]) == {"A", "C"}
    text = capsys.readouterr().out
    assert "official-31203 C" in text and "Not affiliated" in text


def test_png_xml_csv_reproducible(tmp_path, site_dir, manifest, fixture_datasets):
    from web98138.prebuild import build_site

    again = build_site(tmp_path / "again", maps=["ocean-sst"], combinations=["B"],
                       cache_dir=fixture_datasets, echo=lambda *a: None)
    old = manifest["maps"][1]["variants"]["B"]["files"]
    new = again["maps"][0]["variants"]["B"]["files"]
    for kind in ("preview", "thumb", "bricklink", "rebrickable"):
        assert new[kind]["sha256"] == old[kind]["sha256"], kind

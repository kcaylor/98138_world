"""The build step (FR-014-FR-016, FR-006, FR-011, FR-013)."""

from __future__ import annotations

import hashlib
import json

import pytest
from PIL import Image

from conftest import PRICES, SMALL_MAPS, TODAY

KINDS_ALWAYS = {"layout", "parts", "parts-1kit", "bricklink", "rebrickable", "sheets-letter",
                "sheets-a4", "preview", "thumb"}


def test_manifest_top_level(manifest):
    assert manifest["format_version"] == "1"
    assert manifest["disclaimer"] == "Not affiliated with or endorsed by The LEGO Group."
    tools = manifest["tools"]
    assert tools["lego_image_processor"] and tools["web98138"] and tools["python"].startswith("3.11")
    assert "git_commit" in tools
    assert manifest["generated_at"].endswith("Z")
    assert [a["id"] for a in manifest["arrangements"]] == ["A", "B", "C"]
    b = manifest["arrangements"][1]
    assert b["frame_order"] == [3, 1, 2] and b["centre"] == "America"
    assert manifest["arrangement_source"]["pages"] == [7, 8]
    assert "Rebrickable" in manifest["acknowledgement"]
    assert [m["id"] for m in manifest["maps"]] == list(SMALL_MAPS)


def test_every_variant_has_files_matching_checksums(site_dir, manifest):
    for m in manifest["maps"]:
        assert set(m["variants"]) == {"A", "B", "C"}
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
    assert off["default_combination"] == "A" and nino["default_combination"] == "B"
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
                   cache_dir=tmp_path / "empty-cache", echo=lambda *a: None,
                   prices_path=PRICES, today=TODAY)


def test_cli_usage_errors(tmp_path, capsys):
    from web98138.prebuild import main

    assert main(["--out", str(tmp_path / "o"), "--maps", "nope"]) == 2
    assert main(["--out", str(tmp_path / "o"), "--combinations", "D"]) == 2
    assert "Not affiliated" in capsys.readouterr().err


def test_cli_builds_subset(tmp_path, fixture_datasets, capsys):
    from web98138.prebuild import main

    out = tmp_path / "o"
    assert main(["--out", str(out), "--maps", "official-31203", "--combinations", "a,C",
                 "--cache-dir", str(fixture_datasets), "--prices", str(PRICES)]) == 0
    m = json.loads((out / "manifest.json").read_text())
    assert set(m["maps"][0]["variants"]) == {"A", "C"}
    text = capsys.readouterr().out
    assert "official-31203 C" in text and "Not affiliated" in text


def test_png_xml_csv_reproducible(tmp_path, site_dir, manifest, fixture_datasets):
    from web98138.prebuild import build_site

    again = build_site(tmp_path / "again", maps=["ocean-sst"], combinations=["B"],
                       cache_dir=fixture_datasets, echo=lambda *a: None,
                       prices_path=PRICES, today=TODAY)
    old = manifest["maps"][1]["variants"]["B"]["files"]
    new = again["maps"][0]["variants"]["B"]["files"]
    for kind in ("preview", "thumb", "bricklink", "rebrickable"):
        assert new[kind]["sha256"] == old[kind]["sha256"], kind


# --- feature 011: price estimates ---------------------------------------------------------

ESTIMATE_KEYS = {"label", "totals", "whole_dollars", "pieces", "complete", "nothing_to_buy",
                 "unpriced", "stock"}


def _small_build(tmp_path, fixture_datasets, name="o", **kw):
    from web98138.prebuild import build_site

    kw.setdefault("prices_path", PRICES)
    kw.setdefault("today", TODAY)
    return build_site(tmp_path / name, maps=["official-31203"], combinations=["A"],
                      cache_dir=fixture_datasets, echo=lambda *a: None, **kw)


def test_every_variant_has_both_estimates(site_dir, manifest):
    """US3-1: the estimates are the library's, on the same parts lists as the downloads."""
    from lego_image_processor.parts import OwnedInputs, build_parts_list
    from lego_image_processor.parts.partslist import read_layout
    from lego_image_processor.prices import estimate_parts_lists, load_snapshot

    snap = load_snapshot(PRICES)
    for m in manifest["maps"]:
        for c, v in m["variants"].items():
            assert set(v["estimates"]) == {"full", "one_kit"}
            path = site_dir / v["files"]["layout"]["path"]
            raw = path.read_bytes()
            layout = read_layout(path).grid
            sha = hashlib.sha256(raw).hexdigest()
            full = build_parts_list(layout, layout_path="layout.json", layout_sha256=sha)
            one = build_parts_list(layout, layout_path="layout.json", layout_sha256=sha,
                                   owned=OwnedInputs(kits=1))
            r = estimate_parts_lists(full, one, snap, as_of=TODAY)
            for kind in ("full", "one_kit"):
                assert set(v["estimates"][kind]) == ESTIMATE_KEYS
                assert v["estimates"][kind] == r.manifest_entry(kind), (m["id"], c, kind)
    p = manifest["prices"]
    assert p == r.prices_block()
    assert p["snapshot"]["sha256"] == hashlib.sha256(PRICES.read_bytes()).hexdigest()
    assert p["staleness"]["stale"] is False and p["staleness"]["as_of"] == "2026-12-05"
    off = manifest["maps"][0]["variants"]["A"]["estimates"]
    assert off["full"]["pieces"] == 10240 and off["one_kit"]["nothing_to_buy"] is True


def test_default_needs_the_packaged_snapshot(tmp_path, fixture_datasets, monkeypatch):
    from lego_image_processor.prices import wording
    from web98138.prebuild import PrebuildError

    monkeypatch.setattr(wording, "PACKAGED_SNAPSHOT_PATH", tmp_path / "absent.json")
    with pytest.raises(PrebuildError, match=r"no price snapshot is packaged \(lego_image_processor/"
                                            r"data/bricklink_price_guide.json\); run `parts prices "
                                            r"fetch` and commit it, or build with --no-prices"):
        _small_build(tmp_path, fixture_datasets, prices_path=None)
    assert not (tmp_path / "o" / "manifest.json").exists()


def test_invalid_snapshot(tmp_path, fixture_datasets):
    from web98138.prebuild import PrebuildError

    bad = tmp_path / "bad.json"
    data = json.loads(PRICES.read_text())
    data["format_version"] = "9"
    bad.write_text(json.dumps(data))
    with pytest.raises(PrebuildError, match="bad.json.*format_version"):
        _small_build(tmp_path, fixture_datasets, prices_path=bad)
    bad.write_text("{not json")
    with pytest.raises(PrebuildError, match="not JSON"):
        _small_build(tmp_path, fixture_datasets, prices_path=bad)


def _partial(tmp_path):
    p = tmp_path / "partial.json"
    data = json.loads(PRICES.read_text())
    data["complete"] = False
    data["lot_set"]["count"] = len(data["lots"]) + 1
    p.write_text(json.dumps(data))
    return p


def test_partial_snapshot_refused_unless_allowed(tmp_path, fixture_datasets, capsys):
    from web98138.prebuild import PrebuildError, main

    part = _partial(tmp_path)
    with pytest.raises(PrebuildError, match="partial.*--allow-partial-prices"):
        _small_build(tmp_path, fixture_datasets, prices_path=part)
    m = _small_build(tmp_path, fixture_datasets, "ok", prices_path=part, allow_partial_prices=True)
    assert m["prices"]["snapshot"]["complete"] is False
    args = ["--out", str(tmp_path / "cli"), "--maps", "official-31203", "--combinations", "A",
            "--cache-dir", str(fixture_datasets), "--prices", str(part), "-q"]
    assert main(args) == 1
    assert "partial" in capsys.readouterr().err
    assert main(args + ["--allow-partial-prices"]) == 0


def test_no_prices(tmp_path, fixture_datasets):
    from web98138.prebuild import main

    m = _small_build(tmp_path, fixture_datasets, prices_path=None, with_prices=False)
    assert "prices" not in m
    assert all("estimates" not in v for v in m["maps"][0]["variants"].values())
    out = tmp_path / "cli"
    assert main(["--out", str(out), "--maps", "official-31203", "--combinations", "A",
                 "--cache-dir", str(fixture_datasets), "--no-prices", "-q"]) == 0
    assert "prices" not in json.loads((out / "manifest.json").read_text())


def test_prices_and_no_prices_conflict(tmp_path, capsys):
    from web98138.prebuild import main

    with pytest.raises(SystemExit) as exc:
        main(["--out", str(tmp_path / "o"), "--prices", str(PRICES), "--no-prices"])
    assert exc.value.code == 2


def test_stale_at_build_time(tmp_path, fixture_datasets):
    from datetime import date

    m = _small_build(tmp_path, fixture_datasets, today=date(2027, 6, 1))
    st = m["prices"]["staleness"]
    assert st["stale"] is True and st["age_days"] == 182 and st["threshold_days"] == 90


def test_prices_open_no_socket(tmp_path, fixture_datasets, monkeypatch):
    import socket

    def refuse(*a, **k):
        raise AssertionError("the prebuild opened a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    m = _small_build(tmp_path, fixture_datasets)
    assert m["prices"]["snapshot"]["complete"] is True

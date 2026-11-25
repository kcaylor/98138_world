"""Start-up check of the built output (FR-018, FR-021)."""

from __future__ import annotations

import json
import shutil

import pytest

from web98138.catalog import Catalog, CatalogError


@pytest.fixture()
def copy(site_dir, tmp_path):
    dst = tmp_path / "site"
    shutil.copytree(site_dir, dst)
    return dst


def _edit(site, fn):
    p = site / "manifest.json"
    m = json.loads(p.read_text())
    fn(m)
    p.write_text(json.dumps(m))


def test_load_ok(site_dir):
    cat = Catalog.load(site_dir)
    assert [m.id for m in cat.maps] == ["official-31203", "ocean-sst", "ocean-el-nino"]
    assert cat.variant_count == 9
    assert cat.map("ocean-sst").title == "Ocean temperature"
    assert cat.map("nope") is None
    assert cat.file("ocean-sst", "B", "bricklink").name == "bricklink.xml"
    assert cat.file("ocean-sst", "D", "bricklink") is None
    assert cat.file("ocean-sst", "B", "../../manifest") is None
    assert cat.arrangement("C")["centre"] == "Asia and Australia"


def test_missing_dir(tmp_path):
    with pytest.raises(CatalogError, match="manifest"):
        Catalog.load(tmp_path / "nothing")


def test_wrong_format(copy):
    _edit(copy, lambda m: m.update(format_version="9"))
    with pytest.raises(CatalogError, match="format"):
        Catalog.load(copy)


def test_missing_file(copy):
    (copy / "maps" / "ocean-sst" / "A" / "sheets-a4.pdf").unlink()
    with pytest.raises(CatalogError, match="sheets-a4.pdf"):
        Catalog.load(copy)


def test_wrong_size(copy):
    p = copy / "maps" / "ocean-sst" / "A" / "rebrickable.csv"
    p.write_text(p.read_text() + "x")
    with pytest.raises(CatalogError, match="size"):
        Catalog.load(copy)


def test_path_outside_output(copy):
    def bad(m):
        m["maps"][0]["variants"]["A"]["files"]["layout"]["path"] = "../../etc/passwd"
    _edit(copy, bad)
    with pytest.raises(CatalogError, match="outside"):
        Catalog.load(copy)


def test_missing_combination(copy):
    _edit(copy, lambda m: m["maps"][0]["variants"].pop("C"))
    with pytest.raises(CatalogError, match="combinations"):
        Catalog.load(copy)


def test_unknown_kind(copy):
    def bad(m):
        f = m["maps"][0]["variants"]["A"]["files"]
        f["evil"] = f["layout"]
    _edit(copy, bad)
    with pytest.raises(CatalogError, match="kind"):
        Catalog.load(copy)


# --- feature 011: price estimates ---------------------------------------------------------

def test_loads_with_prices(site_dir):
    cat = Catalog.load(site_dir)
    assert cat.manifest["prices"]["snapshot"]["retrieved_on"] == "2026-12-01"
    assert set(cat.map("ocean-sst").variant("B")["estimates"]) == {"full", "one_kit"}


@pytest.mark.parametrize("edit, match", [
    (lambda m: m["maps"][1]["variants"]["B"]["estimates"].pop("one_kit"),
     r"ocean-sst B: estimates\.one_kit"),
    (lambda m: m["maps"][0]["variants"]["C"]["estimates"]["full"]["whole_dollars"].update(low="12"),
     r"official-31203 C: estimates\.full\.whole_dollars\.low"),
    (lambda m: m["maps"][0]["variants"]["A"]["estimates"]["full"]["whole_dollars"].update(high=True),
     r"official-31203 A: estimates\.full\.whole_dollars\.high"),
    (lambda m: m["maps"][0]["variants"]["A"]["estimates"]["one_kit"].update(complete="yes"),
     r"official-31203 A: estimates\.one_kit\.complete"),
    (lambda m: m["maps"][0]["variants"]["A"]["estimates"]["one_kit"]["unpriced"].pop("pieces"),
     r"official-31203 A: estimates\.one_kit\.unpriced\.pieces"),
    (lambda m: m["maps"][2]["variants"]["A"].pop("estimates"), r"ocean-el-nino A: estimates"),
    (lambda m: m["prices"]["snapshot"].update(sha256="xyz"), r"prices\.snapshot\.sha256"),
    (lambda m: m["prices"]["snapshot"].pop("retrieved_on"), r"prices\.snapshot\.retrieved_on"),
    (lambda m: m["prices"]["source"].pop("url"), r"prices\.source\.url"),
    (lambda m: m["prices"].pop("attribution"), r"prices\.attribution"),
    (lambda m: m["prices"].update(estimate_note=""), r"prices\.estimate_note"),
])
def test_bad_estimates(copy, edit, match):
    _edit(copy, edit)
    with pytest.raises(CatalogError, match=match):
        Catalog.load(copy)


def test_estimates_without_prices(copy):
    _edit(copy, lambda m: m.pop("prices"))
    with pytest.raises(CatalogError, match="estimates.*no prices block"):
        Catalog.load(copy)


def test_no_prices_at_all_loads(copy):
    def strip(m):
        m.pop("prices")
        for mp in m["maps"]:
            for v in mp["variants"].values():
                v.pop("estimates")
    _edit(copy, strip)
    assert "prices" not in Catalog.load(copy).manifest


# --- feature 017: map stickers (contracts/web.md "Catalog check") ----------------------------

KIT = "kit-31203"


def test_loads_stickers(site_dir):
    cat = Catalog.load(site_dir)
    p = cat.sticker_file("ocean-sst", KIT, "sticker-large")
    assert p is not None and p.name == "sticker-large.svg" and p.is_file()
    assert cat.sticker_entry("ocean-sst", KIT, "stickers-a4")["media_type"] == "application/pdf"
    assert cat.stickers("ocean-sst", KIT)["title"] == "Ocean temperature"
    assert cat.sticker_file("ocean-sst", "winkel-tripel", "sticker-large") is None
    assert cat.sticker_file("ocean-sst", KIT, "layout") is None
    assert cat.sticker_file("nope", KIT, "sticker-large") is None
    assert cat.sticker_entry("ocean-sst", KIT, "../../manifest") is None
    assert cat.stickers("nope", KIT) is None


def test_stickers_are_optional(copy):
    """An older manifest (no sticker blocks, no sticker files) still serves."""
    def strip(m):
        for mp in m["maps"]:
            mp.pop("stickers")
    _edit(copy, strip)
    shutil.rmtree(copy / "maps" / "ocean-sst" / "stickers")
    cat = Catalog.load(copy)
    assert cat.stickers("ocean-sst", KIT) is None and cat.sticker_file("ocean-sst", KIT, "sticker-small") is None


def _sticker_files(m, i=1):
    return m["maps"][i]["stickers"][KIT]["files"]


@pytest.mark.parametrize("edit, match", [
    (lambda m: m["maps"][1]["stickers"].update({"winkel-tripel": m["maps"][1]["stickers"][KIT]}),
     r"ocean-sst stickers: unknown template 'winkel-tripel'"),
    (lambda m: m["maps"][1].update(stickers=[]), r"ocean-sst stickers: must be an object"),
    (lambda m: _sticker_files(m).update({"sticker-huge": _sticker_files(m)["sticker-large"]}),
     r"ocean-sst stickers kit-31203: unknown file kind 'sticker-huge'"),
    (lambda m: _sticker_files(m).pop("stickers-a4"),
     r"ocean-sst stickers kit-31203: missing file kind 'stickers-a4'"),
    (lambda m: _sticker_files(m)["sticker-small"].update(path="../../etc/passwd"),
     r"ocean-sst stickers kit-31203 sticker-small: path .* is outside"),
    (lambda m: _sticker_files(m)["stickers-letter"].update(bytes=1),
     r"ocean-sst stickers kit-31203 stickers-letter: .* has size"),
    (lambda m: m["maps"][1]["stickers"][KIT].pop("alt"), r"ocean-sst stickers kit-31203: alt"),
    (lambda m: m["maps"][1]["stickers"][KIT].update(title=""), r"ocean-sst stickers kit-31203: title"),
    (lambda m: m["maps"][1]["stickers"][KIT].update(legend={}), r"ocean-sst stickers kit-31203: legend"),
    (lambda m: m["maps"][1]["stickers"][KIT].pop("plaques"), r"ocean-sst stickers kit-31203: plaques"),
    (lambda m: m["maps"][1]["stickers"][KIT]["notes"].pop("colors"),
     r"ocean-sst stickers kit-31203: notes\.colors"),
])
def test_bad_stickers(copy, edit, match):
    _edit(copy, edit)
    with pytest.raises(CatalogError, match=match):
        Catalog.load(copy)


def test_missing_sticker_file(copy):
    (copy / "maps" / "ocean-sst" / "stickers" / KIT / "sticker-large.svg").unlink()
    with pytest.raises(CatalogError, match=r"ocean-sst stickers kit-31203 sticker-large: missing file"):
        Catalog.load(copy)

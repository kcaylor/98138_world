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
    assert cat.variant_count == 16  # 3 maps x 5 combinations (010) + ocean-sst on Winkel tripel (016)
    assert cat.map("ocean-sst").title == "Ocean temperature"
    assert cat.map("nope") is None
    assert cat.file("ocean-sst", "B", "bricklink").name == "bricklink.xml"
    assert cat.file("ocean-sst", "F", "bricklink") is None
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
            for v in list(mp["variants"].values()) + list(mp.get("template_variants", {}).values()):
                v.pop("estimates")
    _edit(copy, strip)
    assert "prices" not in Catalog.load(copy).manifest


# --- feature 016: template variants (contracts/web.md "Catalog check") ---------------------

TID = "winkel-tripel"


def _tv(m, map_i=1):
    return m["maps"][map_i]["template_variants"][TID]


def test_template_variants_load(site_dir):
    cat = Catalog.load(site_dir)
    assert cat.variant_count == 16                       # 15 kit variants (A-E, 010) and ocean-sst on Winkel
    sst = cat.map("ocean-sst")
    assert sst.template_ids == (TID,) and cat.map("official-31203").template_ids == ()
    assert sst.variant(TID)["template"] == TID
    assert sst.variant("A") is sst.data["variants"]["A"]
    assert cat.template(TID)["projection"] == "Winkel tripel" and cat.template("nope") is None
    assert [t["id"] for t in cat.templates] == [TID]
    assert cat.file("ocean-sst", TID, "bricklink").as_posix().endswith(f"ocean-sst/{TID}/bricklink.xml")
    assert cat.file_entry("ocean-sst", TID, "layout")["filename"].startswith(f"98138-world_ocean-sst_{TID}_")
    assert cat.file("official-31203", TID, "layout") is None
    assert cat.file_entry("ocean-el-nino", TID, "layout") is None


def test_template_variant_key_must_be_listed(copy):
    _edit(copy, lambda m: m.update(templates=[]))
    with pytest.raises(CatalogError, match=f"ocean-sst {TID}: template not listed in templates"):
        Catalog.load(copy)


@pytest.mark.parametrize("key", ["A", "B", "C"])
def test_template_variant_key_is_not_a_combination(copy, key):
    def bad(m):
        m["maps"][1]["template_variants"][key] = m["maps"][1]["template_variants"].pop(TID)
        m["templates"][0]["id"] = key
    _edit(copy, bad)
    with pytest.raises(CatalogError, match="must not be A, B or C"):
        Catalog.load(copy)


def test_template_variant_records_its_template(copy):
    _edit(copy, lambda m: _tv(m).update(template="other"))
    with pytest.raises(CatalogError, match=f"ocean-sst {TID}: template"):
        Catalog.load(copy)


def test_template_variant_missing_file(copy):
    (copy / "maps" / "ocean-sst" / TID / "sheets-letter.pdf").unlink()
    with pytest.raises(CatalogError, match=f"ocean-sst {TID} sheets-letter: missing file"):
        Catalog.load(copy)


def test_template_variant_wrong_size(copy):
    p = copy / "maps" / "ocean-sst" / TID / "cells.json"
    p.write_bytes(p.read_bytes() + b" ")
    with pytest.raises(CatalogError, match=f"ocean-sst {TID} cells: .*size"):
        Catalog.load(copy)


def test_template_variant_path_outside(copy):
    _edit(copy, lambda m: _tv(m)["files"]["layout"].update(path="../../etc/passwd"))
    with pytest.raises(CatalogError, match="outside"):
        Catalog.load(copy)


def test_template_variant_unknown_kind(copy):
    _edit(copy, lambda m: _tv(m)["files"].update(evil=_tv(m)["files"]["layout"]))
    with pytest.raises(CatalogError, match=f"ocean-sst {TID}: unknown file kind"):
        Catalog.load(copy)


@pytest.mark.parametrize("edit, match", [
    (lambda m: _tv(m)["estimates"].pop("one_kit"), rf"ocean-sst {TID}: estimates\.one_kit"),
    (lambda m: _tv(m)["estimates"]["full"]["whole_dollars"].update(low=1.5),
     rf"ocean-sst {TID}: estimates\.full\.whole_dollars\.low"),
    (lambda m: _tv(m)["estimates"]["full"]["unpriced"].pop("lots"),
     rf"ocean-sst {TID}: estimates\.full\.unpriced\.lots"),
])
def test_template_variant_estimates_checked(copy, edit, match):
    _edit(copy, edit)
    with pytest.raises(CatalogError, match=match):
        Catalog.load(copy)


def test_template_variant_estimates_need_prices(copy):
    def strip(m):
        m.pop("prices")
        for mp in m["maps"]:
            for v in mp["variants"].values():
                v.pop("estimates")
    _edit(copy, strip)
    with pytest.raises(CatalogError, match=f"ocean-sst {TID}: estimates present"):
        Catalog.load(copy)


@pytest.mark.parametrize("edit, match", [
    (lambda m: m["templates"].append(dict(m["templates"][0])), "listed twice"),
    (lambda m: m["templates"][0].pop("projection"), r"templates\[0\]\.projection"),
    (lambda m: m.update(templates={"id": TID}), "templates: must be a list"),
])
def test_bad_templates_list(copy, edit, match):
    _edit(copy, edit)
    with pytest.raises(CatalogError, match=match):
        Catalog.load(copy)


def test_kit_only_output_loads(copy):
    """A build without template variants (``--templates none``, or before feature 016) loads."""
    def strip(m):
        m.pop("templates")
        for mp in m["maps"]:
            mp.pop("template_variants", None)
    _edit(copy, strip)
    cat = Catalog.load(copy)
    assert cat.variant_count == 15 and cat.templates == [] and cat.map("ocean-sst").template_ids == ()

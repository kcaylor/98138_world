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
    assert cat.variant_count == 15  # 3 maps x 5 combinations (feature 010)
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
